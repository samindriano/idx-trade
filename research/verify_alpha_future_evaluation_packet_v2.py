"""Fail-closed, outcome-blind verifier for Future Evaluation Packet V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd


FORBIDDEN_MARKERS = ("outcome", "target", "forward", "vault", "counter")
EXPECTED_CANDIDATES = {"C1", "C2", "C3", "C4"}
EXPECTED_SOURCE_NAMES = {
    "panel",
    "financial",
    "official_sessions",
    "tradability_anchors",
    "guarded_features",
    "stage_manifest",
}


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


def resolve(repo: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo / path


def git_status(repo: Path) -> tuple[str, str]:
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return head, status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    packet_text = args.packet.read_text(encoding="utf-8")
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    checks["contract_id"] = contract.get("contract_id") == "ALPHA_FUTURE_EVALUATION_PACKET_V2"
    checks["specification_only"] = contract.get("status") == "SPECIFICATION_ONLY / BLOCKED_BY_DATA_ADMISSION"
    checks["scope_flags_false"] = all(
        contract.get(key) is False
        for key in ("outcome_accessed", "provider_accessed", "target_accessed", "cloud_accessed")
    )
    checks["candidate_budget_exact"] = set(contract.get("protected_candidate_budget", [])) == EXPECTED_CANDIDATES
    candidates = contract.get("candidate_contract", {})
    checks["candidate_contract_exact"] = set(candidates) == EXPECTED_CANDIDATES
    checks["c3_fail_closed"] = (
        candidates.get("C3", {}).get("execution_gate") == "BLOCKED_C3_PIT_COVERAGE"
        and candidates.get("C3", {}).get("execute") is False
    )
    ranking = contract.get("ranking_contract", {})
    checks["ranking_contract"] = (
        ranking.get("eligible_mask_first") is True
        and ranking.get("candidate_rank_method") == "average"
        and ranking.get("candidate_rank_percentile") is True
        and ranking.get("top_k") == 30
        and ranking.get("top_k_tie_break") == "score descending, ticker ascending, stable mergesort"
        and ranking.get("no_candidate_specific_population") is True
    )
    evaluation = contract.get("evaluation_contract", {})
    checks["one_shot_contract"] = (
        evaluation.get("one_shot_per_candidate") is True
        and evaluation.get("no_rescue_refit_variant_sweep") is True
        and evaluation.get("folds") == 6
        and evaluation.get("purge_sessions") == 10
        and evaluation.get("bootstrap_repetitions") == 2000
    )
    preconditions = contract.get("admission_preconditions", [])
    checks["admission_preconditions_nonempty"] = len(preconditions) >= 9

    required_packet_phrases = [
        "Alpha Future Evaluation Packet V2",
        "BLOCKED_C3_PIT_COVERAGE",
        "min_periods=window",
        "method=\"average\", pct=True",
        "score descending, ticker ascending",
        "No substitute target",
        "No shorter fallback",
        "research/alpha_future_evaluation_packet_v2_contract.json",
        "NO-GO FOR RE-ENTRY / BLOCKED_BY_DATA_ADMISSION",
    ]
    checks["packet_required_clauses"] = all(phrase in packet_text for phrase in required_packet_phrases)
    checks["packet_has_no_protected_payload"] = not any(
        marker in packet_text.lower() for marker in ("realized_return_value", "outcome_vault_payload", "h5_values", "h10_values")
    )

    source_bindings = contract.get("source_bindings", {})
    checks["source_binding_names_exact"] = set(source_bindings) == EXPECTED_SOURCE_NAMES
    source_results: dict[str, object] = {}
    for name, binding in source_bindings.items():
        path = Path(binding["path"])
        forbidden = any(marker in str(path).lower() for marker in FORBIDDEN_MARKERS)
        exists = path.is_file()
        actual = sha256_file(path) if exists else None
        matches = exists and actual == binding.get("sha256") and not forbidden
        checks[f"source:{name}"] = bool(matches)
        source_results[name] = {
            "path": str(path),
            "exists": exists,
            "forbidden_marker": forbidden,
            "declared_sha256": binding.get("sha256"),
            "actual_sha256": actual,
        }
    details["sources"] = source_results

    implementation = contract.get("implementation_bindings", {})
    implementation_results: dict[str, object] = {}
    for name, binding in implementation.items():
        path = resolve(repo, binding["path"])
        exists = path.is_file()
        actual = sha256_file(path) if exists else None
        matches = exists and actual == binding.get("sha256")
        checks[f"implementation:{name}"] = bool(matches)
        implementation_results[name] = {
            "path": str(path),
            "exists": exists,
            "declared_sha256": binding.get("sha256"),
            "actual_sha256": actual,
        }
    details["implementations"] = implementation_results

    evidence_results: dict[str, object] = {}
    for index, evidence in enumerate(contract.get("robustness_evidence", [])):
        path = resolve(repo, evidence["path"])
        exists = path.is_file()
        actual = sha256_file(path) if exists else None
        matches = exists and actual == evidence.get("sha256")
        checks[f"robustness:{index}"] = bool(matches)
        evidence_results[str(index)] = {
            "path": str(path),
            "exists": exists,
            "declared_sha256": evidence.get("sha256"),
            "actual_sha256": actual,
        }
    checks["robustness_evidence_nonempty"] = len(evidence_results) >= 6
    details["robustness_evidence"] = evidence_results

    feature_binding = source_bindings["guarded_features"]
    panel_binding = source_bindings["panel"]
    features = pd.read_parquet(Path(feature_binding["path"]), columns=["ticker", "date"])
    panel = pd.read_parquet(Path(panel_binding["path"]), columns=["ticker", "date"])
    panel_digest = key_digest(panel)
    feature_digest = key_digest(features)
    key_contract = contract.get("key_contract", {})
    checks["panel_row_count"] = len(panel) == key_contract.get("panel_rows")
    checks["feature_row_count"] = len(features) == key_contract.get("feature_rows")
    checks["panel_key_digest"] = panel_digest == key_contract.get("panel_key_digest")
    checks["feature_key_digest"] = feature_digest == key_contract.get("feature_key_digest")
    checks["key_sets_equal"] = set(zip(panel["ticker"].astype(str), pd.to_datetime(panel["date"]).dt.normalize())) == set(
        zip(features["ticker"].astype(str), pd.to_datetime(features["date"]).dt.normalize())
    )
    details["keys"] = {
        "panel_rows": len(panel),
        "feature_rows": len(features),
        "panel_key_digest": panel_digest,
        "feature_key_digest": feature_digest,
    }

    manifest = json.loads(Path(source_bindings["stage_manifest"]["path"]).read_text(encoding="utf-8"))
    manifest_binding = contract.get("manifest_binding", {})
    checks["manifest_implementation"] = manifest.get("implementation") == manifest_binding.get("implementation")
    checks["manifest_stage"] = manifest.get("stage") == manifest_binding.get("stage")
    checks["manifest_code_hash"] = manifest.get("code_sha256") == manifest_binding.get("manifest_code_sha256")
    checks["manifest_feature_hash"] = manifest.get("files", {}).get("alpha_stage_a_v3_features.parquet") == manifest_binding.get("manifest_feature_sha256")

    head, dirty = git_status(repo)
    checks["worktree_clean"] = dirty == ""
    details["repo"] = {"head": head, "dirty": dirty}

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verification_type": "independent_static_contract_and_source_hash_audit",
        "contract_sha256": sha256_file(args.contract),
        "packet_sha256": sha256_file(args.packet),
        "verifier_code_sha256": sha256_file(Path(__file__)),
        "checks": checks,
        "details": details,
        "scope": {
            "outcome_accessed": False,
            "provider_accessed": False,
            "target_accessed": False,
            "cloud_accessed": False,
            "canonical_mutation": False,
        },
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
