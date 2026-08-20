"""Materialize immutable Open price-basis remediation V1.

No model fit/scoring/tuning, target access, protected-forward access, provider
calls, or parent-panel overwrite occurs.  The output is a separate Open overlay
for later cross-lane consolidation.
"""
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

from idx_trade.price_basis_open_remediation import (  # noqa: E402
    fail_closed_view,
    materialize_open_candidate,
    overlay_view,
)

PROJECT = Path(r"D:\Documents\Project")
DEFAULT_ADJ_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_open_residual_adjudication_v1_20260820"
DEFAULT_HLC_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_remediation_v1_20260820"
DEFAULT_OUTPUT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_open_remediation_v1_20260820"
ADJ_MANIFEST_SHA256 = "29b44a549a438189f3efbc2d24a1d7dac9ac4512e4458c70938a8cad193e0949"
HLC_MANIFEST_SHA256 = "2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278"
EXPECTED_ADJ_STATUS = "OPEN_BASIS_RESIDUALS_CLASSIFIED_SEPARATE_REMEDIATION_PREREG_READY"
EXPECTED_ROWS = 1657
EXPECTED_TICKERS = 12
EXPECTED_OFFICIAL_PRIMARY = 1216
EXPECTED_FACTOR_FALLBACK = 439
EXPECTED_UNRESOLVED = 2
EXPECTED_DISAGREEMENTS = 2


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_EXPECTED:{path}")
    return value


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--adjudication-root", type=Path, default=DEFAULT_ADJ_ROOT)
    p.add_argument("--hlc-remediation-root", type=Path, default=DEFAULT_HLC_ROOT)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    adj = args.adjudication_root.resolve()
    hlc = args.hlc_remediation_root.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    if sha256_file(adj / "MANIFEST.json") != ADJ_MANIFEST_SHA256:
        raise RuntimeError("OPEN_ADJUDICATION_MANIFEST_SHA_MISMATCH")
    if sha256_file(hlc / "MANIFEST.json") != HLC_MANIFEST_SHA256:
        raise RuntimeError("HLC_REMEDIATION_MANIFEST_SHA_MISMATCH")

    adj_manifest = read_json(adj / "MANIFEST.json")
    adj_summary = read_json(adj / "summary.json")
    if adj_manifest.get("status") != EXPECTED_ADJ_STATUS or adj_summary.get("status") != EXPECTED_ADJ_STATUS:
        raise RuntimeError("OPEN_ADJUDICATION_STATUS_CHANGED")
    if adj_summary.get("repair_authorized") is not False or adj_summary.get("clean_refit_authorized") is not False:
        raise RuntimeError("OPEN_ADJUDICATION_GUARD_CHANGED")

    coverage = adj_summary.get("candidate_coverage") or {}
    expected_coverage = {
        "official_primary_rows": EXPECTED_OFFICIAL_PRIMARY,
        "factor_fallback_rows": EXPECTED_FACTOR_FALLBACK,
        "candidate_rows_total": EXPECTED_OFFICIAL_PRIMARY + EXPECTED_FACTOR_FALLBACK,
        "unresolved_rows": EXPECTED_UNRESOLVED,
    }
    for key, expected in expected_coverage.items():
        if int(coverage.get(key, -1)) != expected:
            raise RuntimeError(f"OPEN_ADJUDICATION_COVERAGE_CHANGED:{key}:{coverage.get(key)}!={expected}")
    adjudication = adj_summary.get("adjudication") or {}
    if int(adjudication.get("official_factor_disagreements", -1)) != EXPECTED_DISAGREEMENTS:
        raise RuntimeError("OPEN_ADJUDICATION_DISAGREEMENTS_CHANGED")

    hashes = adj_manifest.get("output_hashes") or {}
    rows_path = adj / "open_basis_residual_adjudication_rows.csv"
    expected_rows_sha = str(hashes.get("rows") or "")
    if not expected_rows_sha or sha256_file(rows_path) != expected_rows_sha:
        raise RuntimeError("OPEN_ADJUDICATION_ROWS_SHA_MISMATCH")
    rows = pd.read_csv(rows_path, low_memory=False)
    if len(rows) != EXPECTED_ROWS or rows["ticker"].astype(str).nunique() != EXPECTED_TICKERS:
        raise RuntimeError("OPEN_ADJUDICATION_POPULATION_CHANGED")

    remediated, diagnostics = materialize_open_candidate(rows)
    expected_diag = {
        "rows": EXPECTED_ROWS,
        "official_primary_rows": EXPECTED_OFFICIAL_PRIMARY,
        "factor_fallback_rows": EXPECTED_FACTOR_FALLBACK,
        "unresolved_fail_closed_rows": EXPECTED_UNRESOLVED,
        "admitted_rows": EXPECTED_OFFICIAL_PRIMARY + EXPECTED_FACTOR_FALLBACK,
        "admitted_within_corrected_hlc_rows": EXPECTED_OFFICIAL_PRIMARY + EXPECTED_FACTOR_FALLBACK,
        "official_factor_disagreement_rows": EXPECTED_DISAGREEMENTS,
    }
    if diagnostics != expected_diag:
        raise RuntimeError(f"OPEN_REMEDIATION_DIAGNOSTICS_CHANGED:{diagnostics}!={expected_diag}")

    overlay = overlay_view(remediated)
    fail_closed = fail_closed_view(remediated)
    if len(overlay) != 1655 or len(fail_closed) != 2:
        raise RuntimeError("OPEN_REMEDIATION_OUTPUT_COUNTS_CHANGED")
    if overlay.duplicated(["ticker", "date"]).any() or fail_closed.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OPEN_REMEDIATION_DUPLICATE_IDENTITY")

    output.mkdir(parents=True, exist_ok=True)
    all_rows_path = output / "open_price_basis_remediation_rows_v1.csv"
    overlay_csv = output / "open_price_basis_overlay_v1.csv"
    overlay_parquet = output / "open_price_basis_overlay_v1.parquet"
    fail_closed_path = output / "open_price_basis_fail_closed_rows_v1.csv"
    remediated.to_csv(all_rows_path, index=False, lineterminator="\n")
    overlay.to_csv(overlay_csv, index=False, lineterminator="\n")
    overlay.to_parquet(overlay_parquet, index=False)
    fail_closed.to_csv(fail_closed_path, index=False, lineterminator="\n")

    result = {
        "schema_version": "price_basis_open_remediation_v1",
        "status": "OPEN_PRICE_BASIS_REMEDIATION_MATERIALIZED_CROSS_LANE_CONSOLIDATION_REQUIRED_BEFORE_REFIT",
        "policy": "IDX_OPENPRICE_PRIMARY_CA_FACTOR_FALLBACK_FAIL_CLOSED_V1",
        "population": {"rows": EXPECTED_ROWS, "tickers": EXPECTED_TICKERS},
        "diagnostics": diagnostics,
        "overlay_rows": int(len(overlay)),
        "fail_closed_rows": int(len(fail_closed)),
        "candidate_open_coverage_rate": float(len(overlay) / EXPECTED_ROWS),
        "parent_adjudication_manifest_sha256": ADJ_MANIFEST_SHA256,
        "parent_hlc_remediation_manifest_sha256": HLC_MANIFEST_SHA256,
        "model_refit_authorized": False,
        "cross_lane_consolidation_required": True,
        "guardrails": {
            "parent_panel_overwritten": False,
            "model_fit": False,
            "model_scoring": False,
            "model_tuning": False,
            "target_values_accessed": False,
            "protected_forward_accessed": False,
            "provider_calls": False,
            "unsupported_open_synthesized": False,
        },
        "next": "FREEZE_AS_IMMUTABLE_OPEN_CANDIDATE_AND_WAIT_FOR_CROSS_LANE_DATA_CONSOLIDATION_BEFORE_ANY_V2_V4_X_REPLAY_OR_REFIT",
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs = {
        "all_rows": all_rows_path,
        "overlay_csv": overlay_csv,
        "overlay_parquet": overlay_parquet,
        "fail_closed": fail_closed_path,
        "summary": summary_path,
    }
    manifest = {
        "schema_version": "price_basis_open_remediation_manifest_v1",
        "status": result["status"],
        "policy": result["policy"],
        "parents": {
            "adjudication_manifest_sha256": ADJ_MANIFEST_SHA256,
            "hlc_remediation_manifest_sha256": HLC_MANIFEST_SHA256,
        },
        "guardrails": result["guardrails"],
        "output_hashes": {key: sha256_file(path) for key, path in outputs.items()},
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**result, "manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
