"""Materialize Price-Basis Remediation V1 without model fitting or scoring."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.price_basis_remediation import (  # noqa: E402
    apply_hlc_overlay,
    build_hlc_overlay,
    non_hlc_parity,
    select_certified_repairs,
)

PROJECT = Path(r"D:\Documents\Project")
ARTIFACT_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "research_feasibility_1260_20260809"
DEFAULT_AUDIT_V11 = PROJECT / "idx-trade-data-gate-20260808v" / "tradingview_v2_1_training_basis_impact_v1_1_20260820"
DEFAULT_AUDIT_V12 = PROJECT / "idx-trade-data-gate-20260808v" / "tradingview_v2_1_training_basis_impact_v1_2_20260820"
DEFAULT_OUTPUT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_remediation_v1_20260820"
PANEL_PATH = ARTIFACT_ROOT / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet"
PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
AUDIT_V11_MANIFEST_SHA256 = "62562fa3f1d949c3e4f9e225aae13b116a5e2c00dffcceab6240ebb07ea422d6"
AUDIT_V12_MANIFEST_SHA256 = "620fbd1f98924365e623919d3339f005abd7960f66631213631b845dcd7061f5"
EXPECTED_REPAIR_ROWS = 1657
EXPECTED_REPAIR_TICKERS = 12


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require_sha(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label}_SHA_MISMATCH:{actual}!={expected}:{path}")


def read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"JSON_OBJECT_EXPECTED:{path}")
    return obj


def strict_bool(s: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(s.dtype):
        return s.astype(bool)
    x = s.astype(str).str.strip().str.lower()
    if not set(x.unique()).issubset({"true", "false"}):
        raise RuntimeError("INVALID_BOOLEAN_COLUMN")
    return x.eq("true")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--audit-v1-1-root", type=Path, default=DEFAULT_AUDIT_V11)
    p.add_argument("--audit-v1-2-root", type=Path, default=DEFAULT_AUDIT_V12)
    p.add_argument("--panel", type=Path, default=PANEL_PATH)
    p.add_argument("--certification", type=Path, default=REPO_ROOT / "config" / "price_basis_remediation_v1.csv")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    v11 = args.audit_v1_1_root.resolve()
    v12 = args.audit_v1_2_root.resolve()
    panel_path = args.panel.resolve()
    cert_path = args.certification.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    require_sha(v11 / "artifact_manifest.json", AUDIT_V11_MANIFEST_SHA256, "AUDIT_V11_MANIFEST")
    require_sha(v12 / "artifact_manifest.json", AUDIT_V12_MANIFEST_SHA256, "AUDIT_V12_MANIFEST")
    require_sha(panel_path, PANEL_SHA256, "FROZEN_PANEL")

    v11_summary = read_json(v11 / "training_basis_impact_summary.json")
    v12_summary = read_json(v12 / "training_basis_impact_v1_2_summary.json")
    if v11_summary.get("status") != "FROZEN_TRAINING_PANEL_BASIS_IMPACT_FOUND":
        raise RuntimeError("AUDIT_V11_STATUS_CHANGED")
    status12 = (v12_summary.get("adjudication") or {}).get("training_lineage_status")
    if status12 != "PRICE_BASIS_CONTAMINATION_CONFIRMED_IN_FROZEN_MODEL_REPRESENTATIONS":
        raise RuntimeError("AUDIT_V12_STATUS_CHANGED")

    basis = pd.read_csv(v11 / "panel_vs_idx_basis_rows.csv", low_memory=False)
    cert = pd.read_csv(cert_path)
    selected, selection = select_certified_repairs(basis, cert)
    if selection["stable_rows"] != EXPECTED_REPAIR_ROWS or selection["stable_tickers"] != EXPECTED_REPAIR_TICKERS:
        raise RuntimeError(f"PARENT_STABLE_POPULATION_CHANGED:{selection}")
    if selection["certified_rows"] != EXPECTED_REPAIR_ROWS or selection["certified_tickers"] != EXPECTED_REPAIR_TICKERS:
        raise RuntimeError(f"NOT_ALL_PARENT_STABLE_ROWS_CERTIFIED:{selection}")
    for key in ("missing_cert_rows", "factor_fail_rows", "provenance_fail_rows", "post_or_on_record_date_rows"):
        if selection[key] != 0:
            raise RuntimeError(f"CERTIFICATION_GATE_FAILED:{key}:{selection[key]}")

    overlay = build_hlc_overlay(selected)
    parent_counterfactual = pd.read_csv(v11 / "counterfactual_hlc_rows.csv")
    for frame in (overlay, parent_counterfactual):
        frame["ticker"] = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    expected = parent_counterfactual[["ticker", "date", "high", "low", "close"]].rename(columns={
        "high": "remediated_high", "low": "remediated_low", "close": "remediated_close"
    })
    parity = overlay[["ticker", "date", "remediated_high", "remediated_low", "remediated_close"]].merge(
        expected, on=["ticker", "date"], how="outer", suffixes=("_new", "_audit"), validate="one_to_one", indicator=True
    )
    if not parity["_merge"].eq("both").all():
        raise RuntimeError("REMEDIATION_COUNTERFACTUAL_IDENTITY_MISMATCH")
    for field in ("high", "low", "close"):
        if not parity[f"remediated_{field}_new"].eq(parity[f"remediated_{field}_audit"]).all():
            raise RuntimeError(f"REMEDIATION_COUNTERFACTUAL_VALUE_MISMATCH:{field}")

    parent = pd.read_parquet(panel_path)
    corrected = apply_hlc_overlay(parent, overlay)
    parity_non_hlc = non_hlc_parity(parent, corrected)
    if parity_non_hlc != {"identity_equal": True, "non_hlc_equal": True, "compared_columns": len(parent.columns) - 3}:
        raise RuntimeError(f"NON_HLC_PARITY_FAILED:{parity_non_hlc}")

    # Audit residuals are retained, not silently repaired. This includes
    # scale-consistent mismatches that did not satisfy the frozen stable-run gate.
    row_scale = strict_bool(basis["panel_idx_row_scale_consistent"])
    stable = strict_bool(basis["panel_idx_stable_run_member"])
    residual_scale = basis.loc[row_scale & ~stable].copy()

    output.mkdir(parents=True, exist_ok=True)
    overlay_path = output / "price_basis_hlc_overlay_v1.csv"
    corrected_path = output / "model_safe_signal_research_panel_1260_price_basis_remediated_v1.parquet"
    residual_path = output / "unresolved_nonstable_scale_basis_rows.csv"
    cert_snapshot = output / "price_basis_certification_snapshot.csv"
    overlay.to_csv(overlay_path, index=False, lineterminator="\n")
    corrected.to_parquet(corrected_path, index=False)
    residual_scale.to_csv(residual_path, index=False, lineterminator="\n")
    cert.to_csv(cert_snapshot, index=False, lineterminator="\n")

    old_exact = int(strict_bool(basis["panel_idx_hlc_exact"]).sum())
    post_exact = old_exact + len(overlay)
    summary = {
        "schema_version": "price_basis_remediation_v1",
        "status": "PRICE_BASIS_HLC_REMEDIATION_MATERIALIZED_REFIT_NOT_AUTHORIZED",
        "policy": "STABLE_SCALE_YAHOO_RAW_KSEI_FACTOR_PRE_RECORD_V1",
        "parent_panel_sha256": PANEL_SHA256,
        "parent_audit_v1_1_manifest_sha256": AUDIT_V11_MANIFEST_SHA256,
        "parent_audit_v1_2_manifest_sha256": AUDIT_V12_MANIFEST_SHA256,
        "selection": selection,
        "repair_rows": int(len(overlay)),
        "repair_tickers": int(overlay["ticker"].nunique()),
        "repair_ticker_names": sorted(overlay["ticker"].unique().tolist()),
        "counterfactual_parity_rows": int(len(parity)),
        "non_hlc_parity": parity_non_hlc,
        "official_idx_hlc_exact_before": {"rows": old_exact, "total": int(len(basis)), "rate": old_exact / len(basis)},
        "official_idx_hlc_exact_after_certified_overlay": {"rows": post_exact, "total": int(len(basis)), "rate": post_exact / len(basis)},
        "unresolved_nonstable_scale_rows": int(len(residual_scale)),
        "known_training_representation_impact_from_parent_audit": {
            "v2_changed_rows": int((((v12_summary.get("v2_clean_prepared_representation") or {}).get("changed_rows")) or 0)),
            "v4_x1_exact_union_changed_rows": int(((((v12_summary.get("v4_x1_exact_fit_scope") or {}).get("UNION") or {}).get("changed_rows")) or 0)),
        },
        "guardrails": {
            "model_fit": False,
            "model_scoring": False,
            "target_values_accessed": False,
            "protected_forward_accessed": False,
            "provider_calls": False,
            "parent_panel_overwritten": False,
            "volume_or_value_repaired": False,
        },
        "next": "INDEPENDENT_REVIEW_THEN_BOUNDED_VOLUME_VALUE_BASIS_AUDIT_BEFORE_ANY_CLEAN_REFIT",
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs = {
        "overlay": overlay_path,
        "corrected_panel": corrected_path,
        "residual_scale": residual_path,
        "certification_snapshot": cert_snapshot,
        "summary": summary_path,
    }
    manifest = {
        "schema_version": "price_basis_remediation_manifest_v1",
        "status": summary["status"],
        "inputs": {
            "parent_panel": {"path": str(panel_path), "sha256": PANEL_SHA256},
            "audit_v1_1_manifest_sha256": AUDIT_V11_MANIFEST_SHA256,
            "audit_v1_2_manifest_sha256": AUDIT_V12_MANIFEST_SHA256,
            "certification_repo_path": str(cert_path),
            "certification_sha256": sha256_file(cert_path),
        },
        "guardrails": summary["guardrails"],
        "output_hashes": {name: sha256_file(path) for name, path in outputs.items()},
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
