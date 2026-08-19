"""Outcome-blind Open-vs-corrected-HLC recertification for Price-Basis Remediation V1.

This runner is intentionally independent of the Volume/Regular-Market-Value audit.
It verifies only that the immutable H/L/C remediation did not invalidate the Open
lineage consumed by V4-X. It performs no repair, model fitting/scoring, target
access, protected-forward access, or provider call.
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
    normalize_date,
    normalize_ticker,
    open_hlc_audit,
)

PROJECT = Path(r"D:\Documents\Project")
DEFAULT_PROJECT_ROOT = PROJECT
DEFAULT_REMEDIATION_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_remediation_v1_20260820"
DEFAULT_OUTPUT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_open_hlc_recertification_v1_20260820"
REMEDIATION_MANIFEST_SHA256 = "2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278"
EXPECTED_REPAIR_ROWS = 1657
EXPECTED_REPAIR_TICKERS = 12
PASS_STATUS = "POST_REMEDIATION_OPEN_HLC_RECERTIFIED"
FAIL_STATUS = "POST_REMEDIATION_OPEN_HLC_INCONSISTENCY_FOUND"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--remediation-root", type=Path, default=DEFAULT_REMEDIATION_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def _changed_range_rows(overlay: pd.DataFrame) -> int:
    original_low = pd.to_numeric(overlay["original_low"], errors="coerce").to_numpy(float)
    original_high = pd.to_numeric(overlay["original_high"], errors="coerce").to_numpy(float)
    corrected_low = pd.to_numeric(overlay["remediated_low"], errors="coerce").to_numpy(float)
    corrected_high = pd.to_numeric(overlay["remediated_high"], errors="coerce").to_numpy(float)
    same_low = np.isclose(original_low, corrected_low, rtol=0.0, atol=0.0, equal_nan=True)
    same_high = np.isclose(original_high, corrected_high, rtol=0.0, atol=0.0, equal_nan=True)
    return int((~(same_low & same_high)).sum())


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    project_root = args.project_root.resolve()
    remediation = args.remediation_root.resolve()
    output = args.output_dir.resolve()

    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    manifest_path = remediation / "MANIFEST.json"
    if sha256_file(manifest_path) != REMEDIATION_MANIFEST_SHA256:
        raise RuntimeError("REMEDIATION_MANIFEST_SHA_MISMATCH")
    remediation_manifest = read_json(manifest_path)
    remediation_summary = read_json(remediation / "summary.json")
    if remediation_summary.get("status") != "PRICE_BASIS_HLC_REMEDIATION_MATERIALIZED_REFIT_NOT_AUTHORIZED":
        raise RuntimeError("REMEDIATION_STATUS_CHANGED")

    hashes = remediation_manifest.get("output_hashes") or {}
    corrected_path = remediation / "model_safe_signal_research_panel_1260_price_basis_remediated_v1.parquet"
    overlay_path = remediation / "price_basis_hlc_overlay_v1.csv"
    for key, path in (("corrected_panel", corrected_path), ("overlay", overlay_path)):
        expected = str(hashes.get(key) or "")
        if not expected or sha256_file(path) != expected:
            raise RuntimeError(f"REMEDIATION_OUTPUT_SHA_MISMATCH:{key}")

    corrected = pd.read_parquet(corrected_path)
    corrected["ticker"] = normalize_ticker(corrected["ticker"])
    corrected["date"] = normalize_date(corrected["date"], label="corrected panel")
    if corrected.duplicated(["ticker", "date"]).any():
        raise RuntimeError("CORRECTED_PANEL_DUPLICATE_IDENTITY")

    overlay = pd.read_csv(overlay_path)
    overlay["ticker"] = normalize_ticker(overlay["ticker"])
    overlay["date"] = normalize_date(overlay["date"], label="HLC overlay")
    if overlay.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OVERLAY_DUPLICATE_IDENTITY")
    if len(overlay) != EXPECTED_REPAIR_ROWS or overlay["ticker"].nunique() != EXPECTED_REPAIR_TICKERS:
        raise RuntimeError("REPAIR_POPULATION_CHANGED")

    repair_hlc = overlay[["ticker", "date", "remediated_low", "remediated_high"]].rename(
        columns={"remediated_low": "low", "remediated_high": "high"}
    )

    # Reconstruct the exact accepted Open lineage used by V4-X target entry:
    # derivative Open, with the immutable recovery overlay as fallback, using
    # the same historical price-evidence builder. No targets are loaded here.
    lineage = import_script(
        repo_root / "scripts" / "run_training_price_basis_impact_audit_v1.py",
        "price_basis_open_hlc_lineage",
    )
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
        corrected,
        calendar,
        derivative,
        open_overlay,
        anchors,
        intervals,
    )

    accepted = price_evidence[["ticker", "date", "accepted_open", "open_admitted"]].copy()
    accepted["ticker"] = normalize_ticker(accepted["ticker"])
    accepted["date"] = normalize_date(accepted["date"], label="accepted open")
    if accepted.duplicated(["ticker", "date"]).any():
        raise RuntimeError("ACCEPTED_OPEN_DUPLICATE_IDENTITY")

    accepted_rows = repair_hlc.merge(
        accepted,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    admitted = accepted_rows["open_admitted"].fillna(False).astype(bool)
    accepted_rows.loc[~admitted, "accepted_open"] = np.nan
    accepted_audit, accepted_summary = open_hlc_audit(
        accepted_rows,
        open_column="accepted_open",
    )

    # Also recertify the corrected panel's own Open column. The remediation
    # contract leaves Open byte/semantic values unchanged while H/L changes.
    panel_open_summary: dict[str, int] | None = None
    panel_open_audit = pd.DataFrame()
    if "open" in corrected.columns:
        panel_open_rows = repair_hlc.merge(
            corrected[["ticker", "date", "open"]],
            on=["ticker", "date"],
            how="left",
            validate="one_to_one",
        )
        panel_open_audit, panel_open_summary = open_hlc_audit(
            panel_open_rows,
            open_column="open",
        )

    accepted_pass = (
        accepted_summary["invalid_hlc_rows"] == 0
        and accepted_summary["open_range_violation_rows"] == 0
    )
    panel_pass = panel_open_summary is None or (
        panel_open_summary["invalid_hlc_rows"] == 0
        and panel_open_summary["open_range_violation_rows"] == 0
    )
    status = PASS_STATUS if accepted_pass and panel_pass else FAIL_STATUS

    output.mkdir(parents=True, exist_ok=True)
    accepted_output = output / "accepted_open_vs_corrected_hlc_repaired_rows.csv"
    panel_output = output / "panel_open_vs_corrected_hlc_repaired_rows.csv"
    violation_output = output / "open_hlc_violation_rows.csv"
    accepted_audit.to_csv(accepted_output, index=False, lineterminator="\n")
    panel_open_audit.to_csv(panel_output, index=False, lineterminator="\n")

    violation_parts: list[pd.DataFrame] = []
    accepted_violations = accepted_audit.loc[
        accepted_audit["open_available"].astype(bool)
        & ~accepted_audit["open_within_corrected_hlc"].fillna(False).astype(bool)
    ].copy()
    if not accepted_violations.empty:
        accepted_violations.insert(0, "audit_lineage", "accepted_open")
        violation_parts.append(accepted_violations)
    if not panel_open_audit.empty:
        panel_violations = panel_open_audit.loc[
            panel_open_audit["open_available"].astype(bool)
            & ~panel_open_audit["open_within_corrected_hlc"].fillna(False).astype(bool)
        ].copy()
        if not panel_violations.empty:
            panel_violations.insert(0, "audit_lineage", "panel_open")
            violation_parts.append(panel_violations)
    violations = pd.concat(violation_parts, ignore_index=True) if violation_parts else pd.DataFrame()
    violations.to_csv(violation_output, index=False, lineterminator="\n")

    result = {
        "schema_version": "price_basis_open_hlc_recertification_v1",
        "status": status,
        "open_hlc_recertified": status == PASS_STATUS,
        "parent_remediation_manifest_sha256": REMEDIATION_MANIFEST_SHA256,
        "repair_population": {
            "rows": int(len(overlay)),
            "tickers": int(overlay["ticker"].nunique()),
            "range_changed_rows": _changed_range_rows(overlay),
        },
        "accepted_open": accepted_summary,
        "accepted_open_price_evidence": price_stats,
        "panel_open": panel_open_summary,
        "violation_rows": int(len(violations)),
        "guardrails": {
            "repair_performed": False,
            "model_fit": False,
            "model_scoring": False,
            "model_tuning": False,
            "target_values_accessed": False,
            "protected_forward_accessed": False,
            "provider_calls": False,
            "parent_panel_overwritten": False,
            "volume_or_value_audited": False,
            "volume_or_value_repaired": False,
        },
        "next": (
            "OPEN_HLC_GATE_CLOSED_WAIT_FOR_OTHER_POST_REMEDIATION_GUARDS"
            if status == PASS_STATUS
            else "STOP_REVIEW_OPEN_HLC_VIOLATIONS_NO_REFIT"
        ),
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    outputs = {
        "accepted_open_audit": accepted_output,
        "panel_open_audit": panel_output,
        "violations": violation_output,
        "summary": summary_path,
    }
    manifest = {
        "schema_version": "price_basis_open_hlc_recertification_manifest_v1",
        "status": status,
        "inputs": {
            "remediation_manifest": {
                "path": str(manifest_path),
                "sha256": REMEDIATION_MANIFEST_SHA256,
            },
            "corrected_panel": {
                "path": str(corrected_path),
                "sha256": sha256_file(corrected_path),
            },
            "hlc_overlay": {
                "path": str(overlay_path),
                "sha256": sha256_file(overlay_path),
            },
        },
        "guardrails": result["guardrails"],
        "output_hashes": {name: sha256_file(path) for name, path in outputs.items()},
    }
    out_manifest = output / "MANIFEST.json"
    out_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                **result,
                "manifest": str(out_manifest),
                "manifest_sha256": sha256_file(out_manifest),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == PASS_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
