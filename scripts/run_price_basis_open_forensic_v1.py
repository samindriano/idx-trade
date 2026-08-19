"""Post-remediation Open price-basis forensic V1.

This is diagnostic only.  It does not repair Open/HLC, fit or score a model,
access target values/protected outcomes, or call providers.  It is triggered by
the immutable post-remediation guard failure on all 1,657 repaired HLC rows.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.price_basis_open_forensic import classify_open_basis, summary as basis_summary  # noqa: E402

PROJECT = Path(r"D:\Documents\Project")
DEFAULT_PROJECT_ROOT = PROJECT
DEFAULT_REMEDIATION_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_remediation_v1_20260820"
DEFAULT_GUARD_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_post_remediation_guard_v1_20260820"
DEFAULT_STOCK_SUMMARY_ROOT = PROJECT / "idx-trade-foreign-flow-historical-20260814-v1"
DEFAULT_OUTPUT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_open_forensic_v1_20260820"
REMEDIATION_MANIFEST_SHA256 = "2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278"
POST_GUARD_MANIFEST_SHA256 = "d96fa15d5ae31fc1b50f765283df3dc7f244836e70bf4662f0bf045d6bc40bce"
EXPECTED_ROWS = 1657
EXPECTED_TICKERS = 12
EXPECTED_GUARD_STATUS = "POST_REMEDIATION_GUARDS_BLOCKED_OPEN_HLC_INCONSISTENCY"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_EXPECTED:{path}")
    return value


def import_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"SCRIPT_IMPORT_FAILED:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def normalize_ticker(series: pd.Series) -> pd.Series:
    return series.astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()


def normalize_date(series: pd.Series, label: str) -> pd.Series:
    out = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if out.isna().any():
        raise RuntimeError(f"INVALID_DATE:{label}")
    return out


def numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series.dtype):
        return pd.to_numeric(series, errors="coerce").astype(float)
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce").astype(float)


def _stock_rows(value: object) -> list[dict[str, Any]] | None:
    if isinstance(value, list):
        rows = [item for item in value if isinstance(item, dict)]
        if rows and any("StockCode" in row for row in rows):
            return rows
        for child in value:
            found = _stock_rows(child)
            if found is not None:
                return found
    elif isinstance(value, dict):
        if "StockCode" in value:
            return [value]
        for child in value.values():
            found = _stock_rows(child)
            if found is not None:
                return found
    return None


def load_official_open(root: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    paths = sorted(root.rglob("stock_summary.raw.json"))
    if not paths:
        raise RuntimeError(f"OFFICIAL_STOCK_SUMMARY_NOT_FOUND:{root}")
    parts: list[pd.DataFrame] = []
    parsed = 0
    with_open_field = 0
    for path in paths:
        try:
            day = pd.Timestamp(path.parent.name).normalize()
        except Exception:
            continue
        raw = read_json(path)
        rows = _stock_rows(raw)
        if not rows:
            continue
        frame = pd.DataFrame(rows)
        if "StockCode" not in frame.columns:
            continue
        parsed += 1
        has_open = "OpenPrice" in frame.columns
        with_open_field += int(has_open)
        parts.append(
            pd.DataFrame(
                {
                    "ticker": normalize_ticker(frame["StockCode"]),
                    "date": day,
                    "official_open": numeric(frame["OpenPrice"]) if has_open else np.nan,
                }
            )
        )
    if not parts:
        raise RuntimeError("OFFICIAL_STOCK_SUMMARY_NO_PARSEABLE_ROWS")
    result = pd.concat(parts, ignore_index=True)
    if result.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OFFICIAL_OPEN_DUPLICATE_IDENTITY")
    return result.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True), {
        "stock_summary_files": int(len(paths)),
        "parsed_files": int(parsed),
        "files_with_open_field": int(with_open_field),
        "rows": int(len(result)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--remediation-root", type=Path, default=DEFAULT_REMEDIATION_ROOT)
    parser.add_argument("--guard-root", type=Path, default=DEFAULT_GUARD_ROOT)
    parser.add_argument("--stock-summary-root", type=Path, default=DEFAULT_STOCK_SUMMARY_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    project_root = args.project_root.resolve()
    remediation = args.remediation_root.resolve()
    guard_root = args.guard_root.resolve()
    stock_summary_root = args.stock_summary_root.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    if sha256_file(remediation / "MANIFEST.json") != REMEDIATION_MANIFEST_SHA256:
        raise RuntimeError("REMEDIATION_MANIFEST_SHA_MISMATCH")
    if sha256_file(guard_root / "MANIFEST.json") != POST_GUARD_MANIFEST_SHA256:
        raise RuntimeError("POST_GUARD_MANIFEST_SHA_MISMATCH")
    guard = read_json(guard_root / "summary.json")
    if guard.get("status") != EXPECTED_GUARD_STATUS:
        raise RuntimeError("POST_GUARD_STATUS_CHANGED")
    accepted_guard = ((guard.get("open_hlc") or {}).get("accepted_open") or {})
    if int(accepted_guard.get("open_range_violation_rows", -1)) != EXPECTED_ROWS:
        raise RuntimeError("POST_GUARD_FAILURE_POPULATION_CHANGED")

    rem_manifest = read_json(remediation / "MANIFEST.json")
    hashes = rem_manifest.get("output_hashes") or {}
    corrected_path = remediation / "model_safe_signal_research_panel_1260_price_basis_remediated_v1.parquet"
    overlay_path = remediation / "price_basis_hlc_overlay_v1.csv"
    for key, path in (("corrected_panel", corrected_path), ("overlay", overlay_path)):
        expected = str(hashes.get(key) or "")
        if not expected or sha256_file(path) != expected:
            raise RuntimeError(f"REMEDIATION_OUTPUT_SHA_MISMATCH:{key}")

    corrected = pd.read_parquet(corrected_path)
    corrected["ticker"] = normalize_ticker(corrected["ticker"])
    corrected["date"] = normalize_date(corrected["date"], "corrected")
    overlay = pd.read_csv(overlay_path)
    overlay["ticker"] = normalize_ticker(overlay["ticker"])
    overlay["date"] = normalize_date(overlay["date"], "overlay")
    if len(overlay) != EXPECTED_ROWS or overlay["ticker"].nunique() != EXPECTED_TICKERS:
        raise RuntimeError("REPAIR_POPULATION_CHANGED")

    base = overlay[["ticker", "date", "expected_factor", "parent_price_provenance"]].merge(
        corrected[["ticker", "date", "low", "high"]], on=["ticker", "date"], how="left", validate="one_to_one"
    )
    if base[["low", "high"]].isna().any().any():
        raise RuntimeError("CORRECTED_HLC_MISSING")

    lineage = import_script(repo_root / "scripts" / "run_training_price_basis_impact_audit_v1.py", "open_forensic_lineage")
    cfg = read_json(repo_root / "config" / "ranking_v4_x1_final_refit_v1.json")
    v4_paths = lineage.discover_v4_inputs(project_root, cfg)
    hist = lineage.import_hist_runner(repo_root)
    calendar = lineage.load_calendar(v4_paths["calendar"])
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)
    derivative = pd.read_parquet(v4_paths["open_derivative_panel"])
    derivative["ticker"] = normalize_ticker(derivative["ticker"])
    derivative["date"] = normalize_date(derivative["date"], "derivative")
    recovery = pd.read_parquet(v4_paths["overlay_parquet"])
    recovery["ticker"] = normalize_ticker(recovery["ticker"])
    recovery["date"] = normalize_date(recovery["date"], "recovery")
    anchors = pd.read_csv(v4_paths["anchors"])
    intervals = pd.read_csv(v4_paths["intervals"])
    price, price_stats = hist.build_price_evidence(corrected, calendar, derivative, recovery, anchors, intervals)
    price["ticker"] = normalize_ticker(price["ticker"])
    price["date"] = normalize_date(price["date"], "price evidence")

    derivative_view = derivative[["ticker", "date", "open"]].rename(columns={"open": "derivative_open"})
    recovery_view = recovery[["ticker", "date", "recovered_open"]].copy()
    evidence = base.merge(price[["ticker", "date", "accepted_open", "open_admitted"]], on=["ticker", "date"], how="left", validate="one_to_one")
    evidence = evidence.merge(derivative_view, on=["ticker", "date"], how="left", validate="one_to_one")
    evidence = evidence.merge(recovery_view, on=["ticker", "date"], how="left", validate="one_to_one")
    d = numeric(evidence["derivative_open"])
    r = numeric(evidence["recovered_open"])
    d_valid = np.isfinite(d) & d.gt(0.0)
    r_valid = np.isfinite(r) & r.gt(0.0)
    evidence["accepted_open_source"] = np.where(d_valid, "DERIVATIVE_OPEN", np.where(r_valid, "RECOVERY_OVERLAY", "MISSING"))

    official, archive_stats = load_official_open(stock_summary_root)
    evidence = evidence.merge(official, on=["ticker", "date"], how="left", validate="one_to_one")
    classified = classify_open_basis(evidence)
    totals = basis_summary(classified)

    by_ticker = []
    for ticker, block in classified.groupby("ticker", sort=True):
        row = {"ticker": str(ticker), **basis_summary(block)}
        row["accepted_source_set"] = "|".join(sorted(set(block["accepted_open_source"].astype(str))))
        row["expected_factor"] = float(pd.to_numeric(block["expected_factor"], errors="raise").iloc[0])
        by_ticker.append(row)
    by_ticker_frame = pd.DataFrame(by_ticker)

    full_official = totals["official_open_positive"] == EXPECTED_ROWS and totals["official_open_within_corrected_hlc"] == EXPECTED_ROWS
    factor_full_range = totals["factor_up_within_corrected_hlc"] == EXPECTED_ROWS
    factor_exact_official = totals["factor_up_equals_official"] == EXPECTED_ROWS
    if full_official and factor_exact_official:
        verdict = "OPEN_BASIS_FORENSIC_OFFICIAL_IDX_FULL_SUPPORT_FACTOR_MECHANISM_CONFIRMED_SEPARATE_REMEDIATION_PREREG_READY"
    elif full_official:
        verdict = "OPEN_BASIS_FORENSIC_OFFICIAL_IDX_FULL_SUPPORT_SEPARATE_REMEDIATION_PREREG_READY"
    elif factor_full_range:
        verdict = "OPEN_BASIS_FORENSIC_CA_FACTOR_FULL_RANGE_RECOVERY_OFFICIAL_SUPPORT_PARTIAL_REMEDIATION_DESIGN_REQUIRED"
    else:
        verdict = "OPEN_BASIS_FORENSIC_UNRESOLVED_REFIT_BLOCKED"

    output.mkdir(parents=True, exist_ok=True)
    rows_path = output / "open_basis_forensic_rows.csv"
    ticker_path = output / "open_basis_forensic_by_ticker.csv"
    classified.to_csv(rows_path, index=False, lineterminator="\n")
    by_ticker_frame.to_csv(ticker_path, index=False, lineterminator="\n")
    result = {
        "schema_version": "price_basis_open_forensic_v1",
        "status": verdict,
        "population": {"rows": int(len(classified)), "tickers": int(classified["ticker"].nunique())},
        "official_archive": archive_stats,
        "accepted_open_price_evidence": price_stats,
        "totals": totals,
        "accepted_open_sources": {str(k): int(v) for k, v in classified["accepted_open_source"].value_counts().to_dict().items()},
        "repair_authorized": False,
        "clean_refit_authorized": False,
        "guardrails": {
            "repair_performed": False,
            "model_fit": False,
            "model_scoring": False,
            "model_tuning": False,
            "target_values_accessed": False,
            "protected_forward_accessed": False,
            "provider_calls": False,
            "parent_panel_overwritten": False,
        },
        "next": "FREEZE_SEPARATE_OPEN_REMEDIATION_CONTRACT_IF_FORENSIC_SUPPORTS_IT; OTHERWISE_KEEP_REFIT_BLOCKED",
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs = {"rows": rows_path, "by_ticker": ticker_path, "summary": summary_path}
    manifest = {
        "schema_version": "price_basis_open_forensic_manifest_v1",
        "status": verdict,
        "parents": {
            "remediation_manifest_sha256": REMEDIATION_MANIFEST_SHA256,
            "post_guard_manifest_sha256": POST_GUARD_MANIFEST_SHA256,
        },
        "guardrails": result["guardrails"],
        "output_hashes": {name: sha256_file(path) for name, path in outputs.items()},
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**result, "manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
