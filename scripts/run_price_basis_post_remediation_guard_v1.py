"""Final outcome-blind data guards before deterministic clean V2/V4-X refit.

This runner performs no repairs, model fitting/scoring, target-value access,
protected-forward access, or provider calls. It verifies post-remediation Open
inside corrected H/L on repaired rows and performs a broad official-IDX
Volume/Regular-Market-Value basis audit across the corrected panel.
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

from idx_trade.price_basis_post_remediation_guard import (  # noqa: E402
    apply_official_volume_value,
    denominator_summary,
    liquidity_feature_delta,
    liquidity_source_features,
    normalize_date,
    normalize_ticker,
    open_hlc_audit,
    provenance_seams,
    volume_value_exact_comparison,
    year_provenance_summary,
)

PROJECT = Path(r"D:\Documents\Project")
DEFAULT_PROJECT_ROOT = PROJECT
DEFAULT_REMEDIATION_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_remediation_v1_20260820"
DEFAULT_VOLUME_VALUE_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_volume_value_audit_v1_20260820"
DEFAULT_STOCK_SUMMARY_ROOT = PROJECT / "idx-trade-foreign-flow-historical-20260814-v1"
DEFAULT_OUTPUT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_post_remediation_guard_v1_20260820"
REMEDIATION_MANIFEST_SHA256 = "2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278"
VOLUME_VALUE_MANIFEST_SHA256 = "317c5cad8170b34b69c87eb43763b9afe4a368cbd9a3afaf94c5297aebeeb38f"
EXPECTED_REPAIR_ROWS = 1657
EXPECTED_REPAIR_TICKERS = 12
PASS_VOLUME_STATUS = "NO_REPEATED_VOLUME_VALUE_BASIS_SCALE_EVIDENCE_REFIT_REVIEW_READY"
PASS_STATUS = "POST_REMEDIATION_GUARDS_PASS_CLEAN_REFIT_PROTOCOL_READY"


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


def grouped_basis_summary(rows: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["ticker"] + (["price_provenance"] if "price_provenance" in rows.columns else [])
    records: list[dict[str, Any]] = []
    for keys, block in rows.groupby(group_cols, sort=True, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = {column: value for column, value in zip(group_cols, keys, strict=True)}
        record.update(denominator_summary(block))
        volume_ratio = pd.to_numeric(block["volume_ratio"], errors="coerce")
        value_ratio = pd.to_numeric(block["value_ratio"], errors="coerce")
        record["volume_ratio_median"] = float(volume_ratio.median()) if volume_ratio.notna().any() else None
        record["value_ratio_median"] = float(value_ratio.median()) if value_ratio.notna().any() else None
        records.append(record)
    return pd.DataFrame(records)


def ca_boundary_rows(comparison: pd.DataFrame, certification: pd.DataFrame, radius: int = 5) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    cert = certification.copy()
    cert["ticker"] = normalize_ticker(cert["ticker"])
    cert["record_date"] = normalize_date(cert["record_date"], label="certification record_date")
    for row in cert.itertuples(index=False):
        block = comparison[comparison["ticker"].eq(row.ticker)].sort_values("date", kind="mergesort").reset_index(drop=True)
        if block.empty:
            continue
        positions = np.flatnonzero(block["date"].ge(row.record_date).to_numpy())
        center = int(positions[0]) if len(positions) else len(block) - 1
        start = max(0, center - radius)
        end = min(len(block), center + radius + 1)
        window = block.iloc[start:end].copy()
        window["ca_record_date"] = row.record_date
        window["ca_type"] = getattr(row, "ca_type", "")
        window["ca_expected_factor"] = getattr(row, "expected_factor", np.nan)
        records.append(window)
    if not records:
        return pd.DataFrame()
    return pd.concat(records, ignore_index=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--remediation-root", type=Path, default=DEFAULT_REMEDIATION_ROOT)
    parser.add_argument("--volume-value-root", type=Path, default=DEFAULT_VOLUME_VALUE_ROOT)
    parser.add_argument("--stock-summary-root", type=Path, default=DEFAULT_STOCK_SUMMARY_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    project_root = args.project_root.resolve()
    remediation = args.remediation_root.resolve()
    vv_root = args.volume_value_root.resolve()
    stock_summary_root = args.stock_summary_root.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    if sha256_file(remediation / "MANIFEST.json") != REMEDIATION_MANIFEST_SHA256:
        raise RuntimeError("REMEDIATION_MANIFEST_SHA_MISMATCH")
    if sha256_file(vv_root / "MANIFEST.json") != VOLUME_VALUE_MANIFEST_SHA256:
        raise RuntimeError("VOLUME_VALUE_MANIFEST_SHA_MISMATCH")
    remediation_manifest = read_json(remediation / "MANIFEST.json")
    remediation_summary = read_json(remediation / "summary.json")
    vv_summary = read_json(vv_root / "summary.json")
    if remediation_summary.get("status") != "PRICE_BASIS_HLC_REMEDIATION_MATERIALIZED_REFIT_NOT_AUTHORIZED":
        raise RuntimeError("REMEDIATION_STATUS_CHANGED")
    if vv_summary.get("status") != PASS_VOLUME_STATUS or vv_summary.get("refit_review_ready") is not True:
        raise RuntimeError("BOUNDED_VOLUME_VALUE_AUDIT_NOT_PASS")

    hashes = remediation_manifest.get("output_hashes") or {}
    corrected_path = remediation / "model_safe_signal_research_panel_1260_price_basis_remediated_v1.parquet"
    overlay_path = remediation / "price_basis_hlc_overlay_v1.csv"
    cert_path = remediation / "price_basis_certification_snapshot.csv"
    for key, path in (("corrected_panel", corrected_path), ("overlay", overlay_path), ("certification_snapshot", cert_path)):
        expected = str(hashes.get(key) or "")
        if not expected or sha256_file(path) != expected:
            raise RuntimeError(f"REMEDIATION_OUTPUT_SHA_MISMATCH:{key}")

    corrected = pd.read_parquet(corrected_path)
    corrected["ticker"] = normalize_ticker(corrected["ticker"])
    corrected["date"] = normalize_date(corrected["date"], label="corrected panel")
    overlay = pd.read_csv(overlay_path)
    overlay["ticker"] = normalize_ticker(overlay["ticker"])
    overlay["date"] = normalize_date(overlay["date"], label="HLC overlay")
    certification = pd.read_csv(cert_path)
    if len(overlay) != EXPECTED_REPAIR_ROWS or overlay["ticker"].nunique() != EXPECTED_REPAIR_TICKERS:
        raise RuntimeError("REPAIR_POPULATION_CHANGED")

    repair_hlc = overlay[["ticker", "date", "remediated_low", "remediated_high"]].rename(columns={
        "remediated_low": "low", "remediated_high": "high"
    })

    # Actual V4-X accepted Open lineage: derivative Open with immutable recovery overlay fallback.
    lineage = import_script(repo_root / "scripts" / "run_training_price_basis_impact_audit_v1.py", "price_basis_guard_lineage")
    cfg = read_json(repo_root / "config" / "ranking_v4_x1_final_refit_v1.json")
    v4_paths = lineage.discover_v4_inputs(project_root, cfg)
    hist = lineage.import_hist_runner(repo_root)
    calendar = lineage.load_calendar(v4_paths["calendar"])
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)
    derivative = pd.read_parquet(v4_paths["open_derivative_panel"])
    open_overlay = pd.read_parquet(v4_paths["overlay_parquet"])
    anchors = pd.read_csv(v4_paths["anchors"])
    intervals = pd.read_csv(v4_paths["intervals"])
    price_evidence, price_stats = hist.build_price_evidence(
        corrected, calendar, derivative, open_overlay, anchors, intervals
    )
    accepted = price_evidence[["ticker", "date", "accepted_open", "open_admitted"]].copy()
    accepted["ticker"] = normalize_ticker(accepted["ticker"])
    accepted["date"] = normalize_date(accepted["date"], label="accepted open")
    accepted_rows = repair_hlc.merge(accepted, on=["ticker", "date"], how="left", validate="one_to_one")
    admitted = accepted_rows["open_admitted"].fillna(False).astype(bool)
    accepted_rows.loc[~admitted, "accepted_open"] = np.nan
    accepted_audit, accepted_summary = open_hlc_audit(accepted_rows, open_column="accepted_open")

    panel_open_summary: dict[str, Any] | None = None
    panel_open_audit = pd.DataFrame()
    if "open" in corrected.columns:
        panel_open_rows = repair_hlc.merge(corrected[["ticker", "date", "open"]], on=["ticker", "date"], how="left", validate="one_to_one")
        panel_open_audit, panel_open_summary = open_hlc_audit(panel_open_rows, open_column="open")

    # Broad official Volume/Regular-Market-Value basis audit over the entire corrected panel.
    vv_module = import_script(repo_root / "scripts" / "run_price_basis_volume_value_audit_v1.py", "price_basis_guard_vv_loader")
    official, official_archive = vv_module.load_official_idx_volume_value(stock_summary_root)
    comparison = volume_value_exact_comparison(corrected, official)
    denominator = denominator_summary(comparison)
    by_year_provenance = year_provenance_summary(comparison)
    by_ticker_provenance = grouped_basis_summary(comparison)
    seams = provenance_seams(comparison)
    ca_rows = ca_boundary_rows(comparison, certification)

    full_support = (
        denominator["official_identity_overlap_rows"] == denominator["panel_rows"]
        and denominator["official_volume_supported_rows"] == denominator["panel_rows"]
        and denominator["official_value_supported_rows"] == denominator["panel_rows"]
    )
    exact_volume = denominator["volume_mismatch_rows"] == 0
    exact_value = denominator["value_mismatch_rows"] == 0

    official_counterfactual = apply_official_volume_value(corrected, comparison)
    original_liquidity = liquidity_source_features(corrected, calendar["date"])
    counter_liquidity = liquidity_source_features(official_counterfactual, calendar["date"])
    liquidity_delta = liquidity_feature_delta(original_liquidity, counter_liquidity)
    no_liquidity_delta = all(value == 0 for value in liquidity_delta.values())

    accepted_open_pass = accepted_summary["invalid_hlc_rows"] == 0 and accepted_summary["open_range_violation_rows"] == 0
    panel_open_pass = panel_open_summary is None or (
        panel_open_summary["invalid_hlc_rows"] == 0 and panel_open_summary["open_range_violation_rows"] == 0
    )

    if not full_support:
        status = "POST_REMEDIATION_GUARDS_BLOCKED_OFFICIAL_VOLUME_VALUE_SUPPORT_INCOMPLETE"
    elif not exact_volume or not exact_value or not no_liquidity_delta:
        status = "POST_REMEDIATION_GUARDS_BLOCKED_VOLUME_VALUE_DISCREPANCY"
    elif not accepted_open_pass or not panel_open_pass:
        status = "POST_REMEDIATION_GUARDS_BLOCKED_OPEN_HLC_INCONSISTENCY"
    else:
        status = PASS_STATUS

    output.mkdir(parents=True, exist_ok=True)
    accepted_path = output / "accepted_open_vs_corrected_hlc_repaired_rows.csv"
    panel_open_path = output / "panel_open_vs_corrected_hlc_repaired_rows.csv"
    year_path = output / "volume_value_by_year_provenance.csv"
    ticker_path = output / "volume_value_by_ticker_provenance.csv"
    seam_path = output / "volume_value_provenance_seams.csv"
    ca_path = output / "volume_value_ca_boundary_rows.csv"
    mismatch_path = output / "volume_value_mismatch_rows.csv"
    accepted_audit.to_csv(accepted_path, index=False, lineterminator="\n")
    panel_open_audit.to_csv(panel_open_path, index=False, lineterminator="\n")
    by_year_provenance.to_csv(year_path, index=False, lineterminator="\n")
    by_ticker_provenance.to_csv(ticker_path, index=False, lineterminator="\n")
    seams.to_csv(seam_path, index=False, lineterminator="\n")
    ca_rows.to_csv(ca_path, index=False, lineterminator="\n")
    comparison.loc[(~comparison["volume_same_basis"]) | (~comparison["value_same_basis"]) | comparison["official_support"].ne("both")].to_csv(
        mismatch_path, index=False, lineterminator="\n"
    )

    result = {
        "schema_version": "price_basis_post_remediation_guard_v1",
        "status": status,
        "refit_protocol_ready": status == PASS_STATUS,
        "parents": {
            "remediation_manifest_sha256": REMEDIATION_MANIFEST_SHA256,
            "bounded_volume_value_manifest_sha256": VOLUME_VALUE_MANIFEST_SHA256,
        },
        "repair_population": {"rows": int(len(overlay)), "tickers": int(overlay["ticker"].nunique())},
        "open_hlc": {
            "accepted_open": accepted_summary,
            "accepted_open_price_evidence": price_stats,
            "panel_open": panel_open_summary,
        },
        "broad_volume_value": {
            "official_archive": official_archive,
            "denominator": denominator,
            "year_provenance_groups": int(len(by_year_provenance)),
            "ticker_provenance_groups": int(len(by_ticker_provenance)),
            "provenance_seams": int(len(seams)),
            "provenance_seam_volume_mismatches": int((~seams["volume_same_basis"].astype(bool)).sum()) if len(seams) else 0,
            "provenance_seam_value_mismatches": int((~seams["value_same_basis"].astype(bool)).sum()) if len(seams) else 0,
            "ca_boundary_rows": int(len(ca_rows)),
            "liquidity_feature_counterfactual_delta": liquidity_delta,
        },
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
        "next": (
            "FREEZE_DETERMINISTIC_CLEAN_V2_V4_X_REPLAY_REFIT_PROTOCOL_BEFORE_ANY_MODEL_FIT"
            if status == PASS_STATUS
            else "STOP_FOR_FORENSIC_REVIEW_NO_CLEAN_REFIT"
        ),
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs = {
        "accepted_open": accepted_path,
        "panel_open": panel_open_path,
        "year_provenance": year_path,
        "ticker_provenance": ticker_path,
        "seams": seam_path,
        "ca_boundary": ca_path,
        "mismatches": mismatch_path,
        "summary": summary_path,
    }
    manifest = {
        "schema_version": "price_basis_post_remediation_guard_manifest_v1",
        "status": status,
        "parents": result["parents"],
        "guardrails": result["guardrails"],
        "output_hashes": {key: sha256_file(path) for key, path in outputs.items()},
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**result, "manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
