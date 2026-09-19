"""Fail-closed, outcome-blind verifier for Future Evaluation Packet V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
EXPECTED_METRICS = [
    "daily cross-sectional Spearman IC",
    "six-fold median IC",
    "six-fold q25 IC",
    "ICIR",
    "positive-session/fold fraction",
    "Top-30 target percentile",
    "Top-30 minus Bottom-30 spread",
    "H5 and H10 separately",
    "fixed block bootstrap lower bound",
]
EXPECTED_GATES = {
    "median_fold_ic": {"operator": ">=", "threshold": 0.025},
    "q25_fold_ic": {"operator": ">=", "threshold": 0.01},
    "positive_folds": {"operator": ">=", "threshold": 5},
    "top30_target_percentile": {"operator": ">=", "threshold": 0.52},
    "top30_minus_bottom30_spread": {"operator": ">=", "threshold": 0.04},
    "bootstrap_lower_bound": {"operator": ">", "threshold": 0.0},
    "paired_mean_ic_delta": {"operator": ">=", "threshold": 0.005},
    "paired_spread_delta": {"operator": ">=", "threshold": 0.01},
    "paired_top30_delta": {"operator": ">=", "threshold": 0.005},
    "paired_q25_delta": {"operator": ">=", "threshold": 0.0},
    "positive_fold_deltas": {"operator": ">=", "threshold": 4},
    "both_horizons_present": {"operator": "==", "threshold": True},
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
    parser.add_argument("--firewall", type=Path, required=True)
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

    packet_binding = contract.get("packet_binding", {})
    packet_actual_sha256 = sha256_file(args.packet)
    packet_relative = str(args.packet.resolve().relative_to(repo)).replace("\\", "/")
    checks["packet_hash_binding"] = (
        packet_binding.get("path") == packet_relative
        and packet_actual_sha256 == packet_binding.get("sha256")
    )

    eligibility_contract = contract.get("eligibility_contract", {})
    expected_eligibility = {
        "status": "BLOCKED_POLICY_CONFLICT",
        "resolution_required": True,
        "current_implementation_population_rows": 310761,
        "literal_minimum_20_population_rows": 348765,
        "difference_rows": 38004,
        "no_population_choice": True,
    }
    checks["eligibility_contract_fail_closed"] = all(
        eligibility_contract.get(key) == value for key, value in expected_eligibility.items()
    )
    guard_binding = eligibility_contract.get("consistency_guard", {})
    guard_path = Path(guard_binding.get("path", "__missing_eligibility_guard__"))
    guard_exists = guard_path.is_file()
    guard_payload: dict[str, object] = {}
    if guard_exists:
        guard_payload = json.loads(guard_path.read_text(encoding="utf-8"))
    checks["eligibility_guard_binding"] = (
        guard_binding.get("status") == "BLOCKED_POLICY_CONFLICT"
        and guard_exists
        and sha256_file(guard_path) == guard_binding.get("sha256")
        and guard_payload.get("status") == "BLOCKED_POLICY_CONFLICT"
        and guard_payload.get("checks", {}).get("contract_conflict_detected") is True
    )
    details["eligibility_contract"] = {
        "contract": eligibility_contract,
        "guard_exists": guard_exists,
        "guard_path": str(guard_path),
        "guard_status": guard_payload.get("status"),
    }

    producer = contract.get("producer_binding", {})
    manifest_binding = contract.get("manifest_binding", {})
    producer_commit = producer.get("producer_commit")
    checks["producer_manifest_head_binding"] = (
        producer.get("require_manifest_head_equals_producer") is True
        and manifest_binding.get("manifest_repo_head") == producer_commit
    )

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
        "ELIGIBILITY_CONTRACT_STATUS: BLOCKED_POLICY_CONFLICT",
    ]
    checks["packet_required_clauses"] = all(phrase in packet_text for phrase in required_packet_phrases)
    checks["packet_has_no_protected_payload"] = not any(
        marker in packet_text.lower() for marker in ("realized_return_value", "h5_values", "h10_values")
    )

    checks["evaluation_population"] = evaluation.get("population") == "V4_PRIMARY_LIQUID_CAUSAL_V1"
    checks["evaluation_target_formula"] = evaluation.get("target_formula") == "Close_(t+h) / Open_(t+1) - 1"
    checks["evaluation_target_horizons"] = evaluation.get("target_horizons") == [5, 10]
    checks["evaluation_target_missingness"] = evaluation.get("target_missingness") == "missing horizons remain missing; never zero-filled"
    checks["evaluation_target_consensus"] = evaluation.get("target_consensus") == "equal-weight average of ascending average-tie ranks"
    checks["evaluation_fold_structure"] = evaluation.get("fold_structure") == "chronological non-overlapping validation folds"
    checks["evaluation_observability"] = evaluation.get("observability_rule") == "preserve predeclared observability rules; no metric may be added after outcomes are visible"
    checks["evaluation_stopping"] = (
        evaluation.get("unknown_gate_stops_run") is True
        and evaluation.get("queue_unchanged_on_unknown") is True
        and evaluation.get("no_target_substitution") is True
    )
    metric_contract = contract.get("metric_contract", {})
    checks["metric_names_exact"] = metric_contract.get("metrics") == EXPECTED_METRICS
    checks["metric_gates_exact"] = metric_contract.get("gates") == EXPECTED_GATES

    control_bindings = contract.get("control_document_bindings", {})
    control_results: dict[str, object] = {}
    for name, binding in control_bindings.items():
        path = resolve(repo, binding["path"])
        exists = path.is_file()
        text = path.read_text(encoding="utf-8") if exists else ""
        actual = sha256_file(path) if exists else None
        binding_ok = exists and actual == binding.get("sha256")
        item: dict[str, object] = {
            "path": str(path),
            "exists": exists,
            "declared_sha256": binding.get("sha256"),
            "actual_sha256": actual,
            "hash_match": binding_ok,
        }
        if name == "candidate_registry":
            expected_status = binding.get("candidate_status", {})
            registry_ids = set(re.findall(r"^\|\s*(C\d+)\s*\|", text, re.MULTILINE))
            ids_ok = registry_ids == EXPECTED_CANDIDATES
            status_ok = all(
                re.search(
                    rf"^\|\s*{candidate}\s*\|.*\|\s*`{re.escape(status)}`\s*\|",
                    text,
                    re.MULTILINE,
                )
                for candidate, status in expected_status.items()
            )
            checks["control:candidate_registry_hash"] = bool(binding_ok)
            checks["control:candidate_registry_ids"] = ids_ok
            checks["control:candidate_registry_status"] = bool(status_ok)
            item.update(
                {
                    "candidate_ids": sorted(registry_ids),
                    "candidate_ids_exact": ids_ok,
                    "candidate_status_exact": bool(status_ok),
                }
            )
        else:
            clauses = binding.get("required_clauses", [])
            clauses_ok = all(clause in text for clause in clauses)
            checks[f"control:{name}:hash"] = bool(binding_ok)
            checks[f"control:{name}:clauses"] = bool(clauses_ok)
            item["required_clauses"] = clauses
            item["clauses_present"] = clauses_ok
        control_results[name] = item
    checks["control_bindings_exact"] = set(control_bindings) == {
        "candidate_registry",
        "reentry_queue",
        "phase_matrix",
    }
    details["control_documents"] = control_results

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

    head, dirty = git_status(repo)
    manifest = json.loads(Path(source_bindings["stage_manifest"]["path"]).read_text(encoding="utf-8"))
    manifest_binding = contract.get("manifest_binding", {})
    checks["manifest_implementation"] = manifest.get("implementation") == manifest_binding.get("implementation")
    checks["manifest_stage"] = manifest.get("stage") == manifest_binding.get("stage")
    checks["manifest_code_hash"] = manifest.get("code_sha256") == manifest_binding.get("manifest_code_sha256")
    checks["manifest_feature_hash"] = manifest.get("files", {}).get("alpha_stage_a_v3_features.parquet") == manifest_binding.get("manifest_feature_sha256")
    manifest_repo_head = manifest.get("repo_head") or manifest.get("git_head") or manifest.get("repository_head")
    checks["manifest_producer_head"] = manifest_repo_head == producer_commit

    ancestor_ok = False
    if producer_commit and head:
        ancestor_ok = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", producer_commit, head],
            capture_output=True,
        ).returncode == 0
    checks["producer_ancestor_of_current_head"] = (
        ancestor_ok if producer.get("require_producer_ancestor_of_current_head") else True
    )

    firewall_binding = contract.get("firewall_expectations", {})
    firewall_path = Path(firewall_binding.get("path", ""))
    checks["firewall_argument_bound"] = args.firewall.resolve() == firewall_path.resolve()
    firewall_exists = firewall_path.is_file()
    firewall_payload = json.loads(firewall_path.read_text(encoding="utf-8")) if firewall_exists else {}
    firewall_records = firewall_payload.get("records", {}) if isinstance(firewall_payload, dict) else {}
    expected_groups = set(firewall_binding.get("required_record_groups", []))
    checks["firewall_status"] = firewall_exists and firewall_payload.get("status") == firewall_binding.get("status")
    checks["firewall_record_groups"] = firewall_exists and expected_groups.issubset(set(firewall_records)) and all(
        bool(firewall_records.get(group)) for group in expected_groups
    )
    firewall_paths = {
        Path(path).resolve()
        for group in firewall_records.values()
        if isinstance(group, dict)
        for path in group
    }
    expected_firewall_paths = {
        resolve(repo, path).resolve() for path in firewall_binding.get("required_paths", [])
    }
    checks["firewall_required_paths"] = expected_firewall_paths.issubset(firewall_paths)
    details["firewall"] = {
        "path": str(firewall_path),
        "exists": firewall_exists,
        "status": firewall_payload.get("status"),
        "record_groups": sorted(firewall_records),
        "required_paths_present": checks["firewall_required_paths"],
    }

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
