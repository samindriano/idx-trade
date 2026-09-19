"""Independent, outcome-blind verification of the Stage A artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED_COLUMNS = [
    "ticker",
    "date",
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C4_path_efficiency_reversal_20_v1",
    "source_panel_row_present",
    "C3_financial_quality_growth_v1",
]
OUTCOME_TOKENS = ("return", "target", "label", "outcome", "pnl", "nav", "sharpe")
CANDIDATES = [column for column in EXPECTED_COLUMNS if column.startswith("C")]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--stage-code", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--financial", type=Path, required=True)
    args = parser.parse_args()

    features_path = args.stage_dir / "alpha_stage_a_features.parquet"
    audit_path = args.stage_dir / "alpha_stage_a_audit.json"
    manifest_path = args.stage_dir / "manifest.json"
    features = pd.read_parquet(features_path)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    checks: dict[str, bool] = {}
    checks["schema_exact"] = list(features.columns) == EXPECTED_COLUMNS
    checks["duplicate_keys_zero"] = int(features.duplicated(["ticker", "date"]).sum()) == 0
    checks["ticker_non_null"] = bool(features["ticker"].notna().all())
    checks["date_non_null"] = bool(features["date"].notna().all())
    checks["outcome_named_columns_absent"] = not any(
        any(token in column.lower() for token in OUTCOME_TOKENS) for column in features.columns
    )
    checks["row_count_matches_audit"] = len(features) == int(audit["row_count"])
    checks["code_hash_matches_audit"] = sha256_file(args.stage_code) == audit["feature_code_sha256"]
    checks["panel_hash_matches_audit"] = sha256_file(args.panel) == audit["source_hashes"]["panel"]
    checks["financial_hash_matches_audit"] = sha256_file(args.financial) == audit["source_hashes"]["financial"]

    finite_counts = {}
    for column in CANDIDATES:
        finite = np.isfinite(pd.to_numeric(features[column], errors="coerce"))
        finite_counts[column] = int(finite.sum())
        checks[f"finite_count_{column}"] = finite_counts[column] == int(
            audit["candidate_coverage"][column]["finite_rows"]
        )

    checks["feature_hash_matches_manifest"] = sha256_file(features_path) == manifest["files"][features_path.name]
    checks["audit_hash_matches_manifest"] = sha256_file(audit_path) == manifest["files"][audit_path.name]
    checks["manifest_protocol_matches"] = manifest["protocol"] == audit["protocol"]

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "row_count": int(len(features)),
        "duplicate_key_count": int(features.duplicated(["ticker", "date"]).sum()),
        "finite_counts": finite_counts,
        "artifact_hashes": {
            "features": sha256_file(features_path),
            "audit": sha256_file(audit_path),
            "manifest": sha256_file(manifest_path),
        },
    }
    output_path = args.stage_dir / "independent_audit.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["independent_audit_sha256"] = sha256_file(output_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
