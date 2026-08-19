"""Bounded audit of volume/value basis on the frozen 1,657 HLC-remediation rows.

No repair, model fit/scoring, target-value access, protected-forward access, or
provider/network calls are performed.
"""
from __future__ import annotations

import argparse
import hashlib
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

from idx_trade.price_basis_volume_value_audit import (  # noqa: E402
    class_summary,
    classify_frame,
    normalize_date,
    normalize_ticker,
    numeric_series,
    repeated_nonunit_ratio_evidence,
    ticker_factor_evidence,
)

PROJECT = Path(r"D:\Documents\Project")
DEFAULT_REMEDIATION_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_remediation_v1_20260820"
DEFAULT_STOCK_SUMMARY_ROOT = PROJECT / "idx-trade-foreign-flow-historical-20260814-v1"
DEFAULT_OUTPUT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_volume_value_audit_v1_20260820"
REMEDIATION_MANIFEST_SHA256 = "2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278"
EXPECTED_ROWS = 1657
EXPECTED_TICKERS = 12


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"JSON_OBJECT_EXPECTED:{path}")
    return obj


def _stock_rows(value: object) -> list[dict[str, Any]] | None:
    if isinstance(value, list):
        dicts = [row for row in value if isinstance(row, dict)]
        if dicts and any("StockCode" in row for row in dicts):
            return dicts
        for item in value:
            found = _stock_rows(item)
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


def load_official_idx_volume_value(root: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    paths = sorted(root.rglob("stock_summary.raw.json"))
    if not paths:
        raise RuntimeError(f"OFFICIAL_IDX_STOCK_SUMMARY_NOT_FOUND:{root}")
    parts: list[pd.DataFrame] = []
    files_with_volume = 0
    files_with_value = 0
    files_with_both = 0
    parsed_files = 0
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
        parsed_files += 1
        has_volume = "Volume" in frame.columns
        has_value = "Value" in frame.columns
        files_with_volume += int(has_volume)
        files_with_value += int(has_value)
        files_with_both += int(has_volume and has_value)
        out = pd.DataFrame({
            "ticker": normalize_ticker(frame["StockCode"]),
            "date": day,
            "idx_volume": numeric_series(frame["Volume"]) if has_volume else np.nan,
            "idx_value": numeric_series(frame["Value"]) if has_value else np.nan,
        })
        parts.append(out)
    if not parts:
        raise RuntimeError("OFFICIAL_IDX_STOCK_SUMMARY_NO_PARSEABLE_ROWS")
    result = pd.concat(parts, ignore_index=True)
    if result.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OFFICIAL_IDX_VOLUME_VALUE_DUPLICATE_IDENTITY")
    return result.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True), {
        "stock_summary_files": int(len(paths)),
        "parsed_files": int(parsed_files),
        "files_with_volume": int(files_with_volume),
        "files_with_value": int(files_with_value),
        "files_with_both": int(files_with_both),
        "rows": int(len(result)),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--remediation-root", type=Path, default=DEFAULT_REMEDIATION_ROOT)
    p.add_argument("--stock-summary-root", type=Path, default=DEFAULT_STOCK_SUMMARY_ROOT)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    remediation = args.remediation_root.resolve()
    stock_summary = args.stock_summary_root.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    manifest_path = remediation / "MANIFEST.json"
    if sha256_file(manifest_path) != REMEDIATION_MANIFEST_SHA256:
        raise RuntimeError("PRICE_BASIS_REMEDIATION_MANIFEST_SHA_MISMATCH")
    manifest = read_json(manifest_path)
    summary = read_json(remediation / "summary.json")
    if summary.get("status") != "PRICE_BASIS_HLC_REMEDIATION_MATERIALIZED_REFIT_NOT_AUTHORIZED":
        raise RuntimeError("PRICE_BASIS_REMEDIATION_STATUS_CHANGED")
    hashes = manifest.get("output_hashes") or {}
    for name, filename in (
        ("overlay", "price_basis_hlc_overlay_v1.csv"),
        ("corrected_panel", "model_safe_signal_research_panel_1260_price_basis_remediated_v1.parquet"),
        ("certification_snapshot", "price_basis_certification_snapshot.csv"),
    ):
        expected = str(hashes.get(name) or "")
        if not expected or sha256_file(remediation / filename) != expected:
            raise RuntimeError(f"REMEDIATION_OUTPUT_SHA_MISMATCH:{name}")

    overlay = pd.read_csv(remediation / "price_basis_hlc_overlay_v1.csv")
    overlay["ticker"] = normalize_ticker(overlay["ticker"])
    overlay["date"] = normalize_date(overlay["date"], "overlay")
    if len(overlay) != EXPECTED_ROWS or overlay["ticker"].nunique() != EXPECTED_TICKERS:
        raise RuntimeError("FROZEN_REPAIR_POPULATION_CHANGED")
    required_overlay = {"ticker", "date", "expected_factor", "parent_price_provenance"}
    if not required_overlay.issubset(overlay.columns):
        raise RuntimeError(f"OVERLAY_COLUMNS_MISSING:{sorted(required_overlay - set(overlay.columns))}")
    if not overlay["parent_price_provenance"].astype(str).eq("YAHOO_RAW").all():
        raise RuntimeError("OVERLAY_PARENT_PROVENANCE_CHANGED")

    panel = pd.read_parquet(remediation / "model_safe_signal_research_panel_1260_price_basis_remediated_v1.parquet")
    panel["ticker"] = normalize_ticker(panel["ticker"])
    panel["date"] = normalize_date(panel["date"], "panel")
    required_panel = {"ticker", "date", "volume", "regular_market_value"}
    if not required_panel.issubset(panel.columns):
        raise RuntimeError(f"PANEL_VOLUME_VALUE_COLUMNS_MISSING:{sorted(required_panel - set(panel.columns))}")
    panel_view = panel[["ticker", "date", "volume", "regular_market_value"]].rename(columns={
        "volume": "panel_volume",
        "regular_market_value": "panel_regular_market_value",
    })
    evidence = overlay[["ticker", "date", "expected_factor"]].merge(
        panel_view, on=["ticker", "date"], how="left", validate="one_to_one"
    )
    if evidence[["panel_volume", "panel_regular_market_value"]].isna().any().any():
        raise RuntimeError("PANEL_VOLUME_VALUE_MISSING_ON_FROZEN_REPAIR_ROWS")

    official, archive_stats = load_official_idx_volume_value(stock_summary)
    evidence = evidence.merge(official, on=["ticker", "date"], how="left", validate="one_to_one")
    evidence = classify_frame(
        evidence,
        panel_column="panel_volume",
        official_column="idx_volume",
        output_prefix="volume",
    )
    evidence = classify_frame(
        evidence,
        panel_column="panel_regular_market_value",
        official_column="idx_value",
        output_prefix="value",
    )

    volume_summary = class_summary(evidence, "volume_basis_class")
    value_summary = class_summary(evidence, "value_basis_class")
    volume_factor = ticker_factor_evidence(evidence, class_column="volume_basis_class")
    value_factor = ticker_factor_evidence(evidence, class_column="value_basis_class")
    volume_repeat = repeated_nonunit_ratio_evidence(evidence, ratio_column="volume_panel_over_idx_ratio")
    value_repeat = repeated_nonunit_ratio_evidence(evidence, ratio_column="value_panel_over_idx_ratio")

    full_volume_support = volume_summary["invalid_or_missing_rows"] == 0
    full_value_support = value_summary["invalid_or_missing_rows"] == 0
    volume_factor_block = bool(len(volume_factor) and volume_factor["requires_basis_remediation"].astype(bool).any())
    value_factor_block = bool(len(value_factor) and value_factor["requires_basis_remediation"].astype(bool).any())
    volume_repeat_block = bool(len(volume_repeat) and volume_repeat["requires_basis_review"].astype(bool).any())
    value_repeat_block = bool(len(value_repeat) and value_repeat["requires_basis_review"].astype(bool).any())

    if not full_volume_support or not full_value_support:
        verdict = "VOLUME_VALUE_BASIS_AUDIT_INCOMPLETE_OFFICIAL_SUPPORT"
        refit_review_ready = False
    elif volume_factor_block or value_factor_block or volume_repeat_block or value_repeat_block:
        verdict = "VOLUME_VALUE_BASIS_SCALE_EVIDENCE_FOUND_REMEDIATION_REVIEW_REQUIRED"
        refit_review_ready = False
    else:
        verdict = "NO_REPEATED_VOLUME_VALUE_BASIS_SCALE_EVIDENCE_REFIT_REVIEW_READY"
        refit_review_ready = True

    output.mkdir(parents=True, exist_ok=True)
    evidence_path = output / "volume_value_basis_rows.csv"
    volume_factor_path = output / "volume_ca_factor_evidence.csv"
    value_factor_path = output / "value_ca_factor_evidence.csv"
    volume_repeat_path = output / "volume_repeated_nonunit_ratio_evidence.csv"
    value_repeat_path = output / "value_repeated_nonunit_ratio_evidence.csv"
    evidence.to_csv(evidence_path, index=False, lineterminator="\n")
    volume_factor.to_csv(volume_factor_path, index=False, lineterminator="\n")
    value_factor.to_csv(value_factor_path, index=False, lineterminator="\n")
    volume_repeat.to_csv(volume_repeat_path, index=False, lineterminator="\n")
    value_repeat.to_csv(value_repeat_path, index=False, lineterminator="\n")

    result = {
        "schema_version": "price_basis_volume_value_audit_v1",
        "status": verdict,
        "population": {"rows": int(len(evidence)), "tickers": int(evidence["ticker"].nunique())},
        "official_archive": archive_stats,
        "volume": {
            **volume_summary,
            "factor_evidence_tickers": int(volume_factor["requires_basis_remediation"].sum()) if len(volume_factor) else 0,
            "repeated_nonunit_ratio_groups": int(volume_repeat["requires_basis_review"].sum()) if len(volume_repeat) else 0,
        },
        "value": {
            **value_summary,
            "factor_evidence_tickers": int(value_factor["requires_basis_remediation"].sum()) if len(value_factor) else 0,
            "repeated_nonunit_ratio_groups": int(value_repeat["requires_basis_review"].sum()) if len(value_repeat) else 0,
        },
        "refit_review_ready": refit_review_ready,
        "guardrails": {
            "repair_performed": False,
            "model_fit": False,
            "model_scoring": False,
            "target_values_accessed": False,
            "protected_forward_accessed": False,
            "provider_calls": False,
        },
        "next": (
            "DESIGN_FIELD_LEVEL_VOLUME_VALUE_REMEDIATION_BEFORE_CLEAN_REFIT"
            if verdict == "VOLUME_VALUE_BASIS_SCALE_EVIDENCE_FOUND_REMEDIATION_REVIEW_REQUIRED"
            else "RESOLVE_OFFICIAL_SUPPORT_BEFORE_CLEAN_REFIT"
            if verdict == "VOLUME_VALUE_BASIS_AUDIT_INCOMPLETE_OFFICIAL_SUPPORT"
            else "INDEPENDENT_REVIEW_THEN_DETERMINISTIC_CLEAN_REFIT_PROTOCOL"
        ),
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs = {
        "evidence": evidence_path,
        "volume_factor": volume_factor_path,
        "value_factor": value_factor_path,
        "volume_repeat": volume_repeat_path,
        "value_repeat": value_repeat_path,
        "summary": summary_path,
    }
    out_manifest = {
        "schema_version": "price_basis_volume_value_audit_manifest_v1",
        "status": verdict,
        "parent_remediation_manifest_sha256": REMEDIATION_MANIFEST_SHA256,
        "guardrails": result["guardrails"],
        "output_hashes": {name: sha256_file(path) for name, path in outputs.items()},
    }
    out_manifest_path = output / "MANIFEST.json"
    out_manifest_path.write_text(json.dumps(out_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**result, "manifest": str(out_manifest_path), "manifest_sha256": sha256_file(out_manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
