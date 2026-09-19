"""Independent integrity and mask-order verifier for corrected Stage A."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


SCORES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C3_financial_quality_growth_v1",
    "C4_path_efficiency_reversal_20_v1",
]
RANKS = [f"rank_{column}" for column in SCORES]
EXPECTED = [
    "ticker",
    "date",
    "eligible_decision_universe",
    *SCORES,
    "financial_pit_valid",
    "source_panel_row_present",
    *RANKS,
]
EXPECTED_SESSIONS_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_ANCHORS_SHA256 = "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def key_digest(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date"]].copy()
    keys["ticker"] = keys["ticker"].astype("string")
    keys["date"] = pd.to_datetime(keys["date"], errors="raise").dt.strftime("%Y-%m-%d")
    payload = keys.sort_values(["ticker", "date"], kind="mergesort").to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--financial", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    args = parser.parse_args()

    feature_path = args.stage_dir / "alpha_stage_a_v3_features.parquet"
    audit_path = args.stage_dir / "alpha_stage_a_v3_audit.json"
    manifest_path = args.stage_dir / "alpha_stage_a_v3_manifest.json"
    robustness_path = args.stage_dir / "alpha_stage_a_v3_robustness.json"
    features = pd.read_parquet(feature_path)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    robustness = json.loads(robustness_path.read_text(encoding="utf-8"))
    source_keys = pd.read_parquet(args.panel, columns=["ticker", "date"])
    source_keys["date"] = pd.to_datetime(source_keys["date"], errors="raise").dt.normalize()
    code_text = args.code.read_text(encoding="utf-8")

    checks: dict[str, bool] = {}
    checks["schema_exact"] = list(features.columns) == EXPECTED
    checks["duplicate_keys_zero"] = int(features.duplicated(["ticker", "date"]).sum()) == 0
    checks["source_rows_all_present"] = bool(features["source_panel_row_present"].all())
    checks["date_non_null"] = bool(features["date"].notna().all())
    checks["outcome_named_columns_absent"] = not any(
        token in column.lower()
        for column in features.columns
        for token in ("return", "target", "label", "outcome", "pnl", "nav", "sharpe")
    )
    checks["no_score_outside_eligible_mask"] = all(
        bool((~np.isfinite(pd.to_numeric(features[column], errors="coerce")) | features["eligible_decision_universe"]).all())
        for column in SCORES
    )
    checks["no_rank_outside_score"] = all(
        bool((~np.isfinite(pd.to_numeric(features[rank], errors="coerce")) | np.isfinite(pd.to_numeric(features[score], errors="coerce"))).all())
        for score, rank in zip(SCORES, RANKS)
    )
    checks["rank_values_bounded"] = all(
        bool(
            pd.to_numeric(features[rank], errors="coerce")
            .dropna()
            .between(0.0, 1.0, inclusive="both")
            .all()
        )
        for rank in RANKS
    )
    checks["row_count_matches_audit"] = len(features) == int(audit["row_count"])
    checks["source_row_count_matches_audit"] = len(source_keys) == int(audit["source_panel_row_count"])
    checks["source_key_digest_matches"] = (
        key_digest(source_keys) == audit["source_panel_key_digest"] == audit["feature_key_digest"] == key_digest(features)
    )
    checks["source_key_duplicates_zero"] = int(source_keys.duplicated(["ticker", "date"]).sum()) == 0
    checks["eligible_count_matches_audit"] = int(features["eligible_decision_universe"].sum()) == int(audit["eligible_rows"])
    checks["code_hash_matches_audit"] = sha256_file(args.code) == audit["code_sha256"]
    checks["panel_hash_matches_audit"] = sha256_file(args.panel) == audit["source_hashes"]["panel"]
    checks["financial_hash_matches_audit"] = sha256_file(args.financial) == audit["source_hashes"]["financial"]
    checks["sessions_hash_matches_audit"] = sha256_file(args.sessions) == audit["source_hashes"]["official_sessions"]
    checks["anchors_hash_matches_audit"] = sha256_file(args.anchors) == audit["source_hashes"]["tradability_anchors"]
    checks["canonical_session_hash"] = audit["source_hashes"]["official_sessions"] == EXPECTED_SESSIONS_SHA256
    checks["canonical_anchor_hash"] = audit["source_hashes"]["tradability_anchors"] == EXPECTED_ANCHORS_SHA256
    checks["audit_hash_matches_manifest"] = sha256_file(audit_path) == manifest["files"][audit_path.name]
    checks["features_hash_matches_manifest"] = sha256_file(feature_path) == manifest["files"][feature_path.name]
    checks["robustness_features_match"] = sha256_file(feature_path) == robustness["features_sha256"]
    checks["robustness_is_frozen_600"] = robustness["frozen_session_count"] == 600
    checks["outcome_accessed_false"] = audit["outcome_accessed"] is False and robustness["outcome_accessed"] is False
    checks["no_network_imports"] = not bool(
        re.search(r"(?:^|\n)\s*(?:import|from)\s+(?:requests|urllib|httpx|socket)\b", code_text)
    )
    checks["no_provider_http_calls"] = not bool(re.search(r"(?:requests\.|urllib\.|httpx\.|socket\.)", code_text))

    finite_counts = {}
    for score in SCORES:
        finite_counts[score] = int(np.isfinite(pd.to_numeric(features[score], errors="coerce")).sum())
        checks[f"finite_count_{score}"] = finite_counts[score] == int(audit["candidate_coverage"][score]["finite_rows"])

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "row_count": int(len(features)),
        "eligible_rows": int(features["eligible_decision_universe"].sum()),
        "finite_counts": finite_counts,
        "artifact_hashes": {
            "features": sha256_file(feature_path),
            "audit": sha256_file(audit_path),
            "manifest": sha256_file(manifest_path),
            "robustness": sha256_file(robustness_path),
        },
    }
    output = args.stage_dir / "alpha_stage_a_v3_independent_audit.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["independent_audit_sha256"] = sha256_file(output)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
