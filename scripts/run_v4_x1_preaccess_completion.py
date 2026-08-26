"""Safe operator CLI for V4-X1 pre-access artifact completion.

Default/real modes remain outcome-blind.  The synthetic rehearsal intentionally
exercises the real producer path but uses only generated score/operational data
and a synthetic target attestation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.prospective_evaluation_gate_v1 import validate_preflight_bundle
from idx_trade.prospective_preaccess_adapters_v1 import (
    adapt_code_pins,
    build_production_readiness,
    discover_score_inventory,
    load_official_schedule,
    sha256_file,
)
from idx_trade.prospective_preaccess_completion_v1 import (
    CANONICAL_REAL_ACCESS_ROOT_ID,
    COMPLETION_SCHEMA,
    SAFE_SESSION_AUDIT_SCHEMA,
    CompletionArtifactError,
    _atomic_immutable_bytes,
    _atomic_json,
    assert_isolated_staging_root,
    build_admitted_inventory,
    build_local_composite_benchmark,
    build_prior_access_audit,
    finalize_canonical_admitted_inventory,
    project_verified_score_session,
    produce_paper_attestation_from_safe_audit,
    reconcile_runtime_counter,
    sha256_bytes,
    write_preflight_bundle,
    write_synthetic_attestations,
    write_synthetic_score_session,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V4-X1 outcome-blind pre-access completion")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--audit-only", action="store_true")
    modes.add_argument("--project-scores", action="store_true")
    modes.add_argument("--assemble-partial", action="store_true")
    modes.add_argument("--synthetic-rehearsal", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--source-model-runs-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--as-of-session", default="2026-08-26")
    parser.add_argument("--canonical-evaluation-output-root", type=Path)
    parser.add_argument("--canonical-evaluation-root-id")
    parser.add_argument("--session-audit-bridge", type=Path)
    parser.add_argument("--session-audit-evidence-root", type=Path)
    parser.add_argument("--paper-predecessor-session")
    return parser


def _previous_official_session(schedule: list[str], first: str) -> str | None:
    try:
        index = schedule.index(first)
    except ValueError:
        return None
    return schedule[index - 1] if index > 0 else None


def _overall_state(*, readiness: dict[str, object], counter: dict[str, object], prior: dict[str, object]) -> str:
    statuses: list[str] = []
    for value in (readiness, counter, prior):
        status = str(value.get("status") or "") if isinstance(value, dict) else ""
        statuses.append(status)
    if any(status in {"IMPLEMENTATION_DEFECT", "ACCESS_CONTAMINATED"} for status in statuses):
        return "IMPLEMENTATION_DEFECT"
    if any(status == "PROVENANCE_INVALID" for status in statuses):
        return "PROVENANCE_INVALID"
    return "ACCUMULATING_OUTCOME_BLIND"


def _audit_local_index_archive(root: Path, sessions: list[str]) -> dict[str, object]:
    available: list[str] = []
    missing: list[str] = []
    base = root / "forward_monitoring" / "sessions"
    for session in sessions:
        path = base / session / "idx_index_summary.csv"
        (available if path.is_file() else missing).append(session)
    return {
        "calendar_archive_session_count": len(sessions),
        "calendar_archive_available_count": len(available),
        "calendar_archive_missing_sessions": missing,
    }


def _real_audit(args: argparse.Namespace, *, project: bool) -> dict[str, object]:
    repo = args.repo_root.resolve()
    data_root = (args.data_root or Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v")).resolve()
    monitoring = data_root / "forward_monitoring"
    model_runs = (args.source_model_runs_root or monitoring / "model_runs").resolve()
    output = args.output_dir.resolve()
    if project:
        assert_isolated_staging_root(
            output,
            source_roots=(model_runs,),
            forbidden_roots=(repo, data_root, monitoring),
        )
        output.mkdir(parents=True, exist_ok=True)

    calendar_path = monitoring / "calendar" / "exchange_sessions.csv"
    sessions, schedule = load_official_schedule(calendar_path)
    raw_inventory, source = discover_score_inventory(model_runs, official_sessions=sessions, data_root=data_root)

    projected: list[dict[str, object]] = []
    admitted = pd.DataFrame()
    admitted_manifest: dict[str, object] = {
        "canonical_admitted_gate_inventory_sha256": "NOT_AVAILABLE",
        "partial_admitted_gate_shape_sha256": "NOT_AVAILABLE",
    }
    if project:
        for row in raw_inventory.sort_values("session_date").itertuples(index=False):
            projected.append(
                project_verified_score_session(
                    row.score_manifest_path,
                    source_root=model_runs,
                    output_root=output,
                    expected_session=str(row.session_date),
                )
            )
        admitted, admitted_manifest = build_admitted_inventory(
            projected, official_sessions=sessions, output_root=output
        )

    counter_path = monitoring / "eod_automation" / "v4_x1_pipeline" / "latest.json"
    counter = (
        reconcile_runtime_counter(counter_path, admitted)
        if project and not admitted.empty
        else {"status": "NOT_AVAILABLE", "runtime_counter_changed": False}
    )
    readiness = build_production_readiness(repo_root=repo, data_root=data_root, as_of_session=args.as_of_session)

    prospective_dates = admitted["session_date"].astype(str).tolist() if not admitted.empty else raw_inventory["session_date"].astype(str).tolist()
    predecessor = args.paper_predecessor_session or (
        _previous_official_session(sessions, prospective_dates[0]) if prospective_dates else None
    )
    if predecessor and prospective_dates:
        benchmark = build_local_composite_benchmark(
            data_root,
            sessions=prospective_dates,
            predecessor_session_date=predecessor,
            output_root=output if project else Path.cwd() / ".unused-preaccess-audit-output",
        )
    else:
        benchmark = {
            "status": "NOT_AVAILABLE",
            "reason": "BENCHMARK_EVALUATION_BOUNDARY_PREDECESSOR_UNRESOLVED",
            "gate_ready": False,
        }
    benchmark_archive = _audit_local_index_archive(data_root, sessions)

    prior = build_prior_access_audit(
        args.canonical_evaluation_output_root,
        output_path=(output / "prior_access_audit.json") if project and args.canonical_evaluation_output_root else None,
        canonical_root_id=args.canonical_evaluation_root_id,
    )

    paper: dict[str, object]
    if project and args.session_audit_bridge and predecessor and prospective_dates:
        paper = produce_paper_attestation_from_safe_audit(
            args.session_audit_bridge,
            output_path=output / "paper_attestation.json",
            expected_sessions=prospective_dates,
            predecessor_session_date=predecessor,
            evidence_root=args.session_audit_evidence_root,
        )
    else:
        paper = {"status": "NOT_AVAILABLE", "reason": "SESSION_AUDIT_BRIDGE_NOT_CONFIGURED"}

    current_readiness = readiness["readiness"]
    overall = _overall_state(readiness=current_readiness, counter=counter, prior=prior)
    report = {
        "schema_version": "v4_x1_preaccess_artifact_completion_report_v2",
        "mode": "PROJECT_SCORES" if project else "AUDIT_ONLY",
        "outcome_blind": True,
        "provider_calls": False,
        "protected_outcome_accessed": False,
        "target_values_loaded": False,
        "calendar": schedule,
        "production_sessions": len(raw_inventory),
        "raw_production_score_admission": source["score_gate_admission"],
        "rolling_partial_inventory_sha256": current_readiness["inventory"].get("rolling_partial_inventory_sha256"),
        "production_source_gate_shape_sha256": current_readiness["inventory"].get("production_source_gate_shape_sha256"),
        "canonical_admitted_gate_inventory_sha256": admitted_manifest.get("canonical_admitted_gate_inventory_sha256", "NOT_AVAILABLE"),
        "projected_sessions": projected,
        "admitted_inventory": admitted_manifest,
        "counter": counter,
        "benchmark_evaluation_boundary": benchmark,
        "benchmark_archive_diagnostic": benchmark_archive,
        "paper_state": paper,
        "prior_access": prior,
        "code_pins": adapt_code_pins(repo),
        "target_attestation": {"status": "NOT_AVAILABLE", "reason": "SEALED_TARGET_PRODUCER_NOT_RUN"},
        "current_readiness": current_readiness,
        "overall_status": overall,
        "real_preflight_status": "PRE_FLIGHT_BLOCKED",
    }
    if project:
        _atomic_json(output / "completion_report.json", report)
    return report


def _snapshot_payload(session: str, parent_path: Path, parent_sha: str, parent_session: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "idx_trade_forward_dividend_runtime_state_v1_1",
        "session_date": session,
        "state": {"operational_metadata_only": True},
        "hashes": {},
        "previous_snapshot": {
            "path": str(parent_path.resolve()),
            "sha256": parent_sha,
            "session_date": parent_session,
        },
    }
    payload["snapshot_payload_sha256"] = sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    return payload


def _write_synthetic_session_audit_chain(root: Path, dates: list[str], predecessor: str) -> Path:
    evidence = root / "paper-evidence"
    predecessor_path = evidence / "paperstate" / f"{predecessor}.json"
    predecessor_sha = _atomic_json(
        predecessor_path,
        {
            "schema_version": "idx_trade_forward_dividend_runtime_state_v1_1",
            "session_date": predecessor,
            "state": {"operational_metadata_only": True},
            "hashes": {},
            "previous_snapshot": None,
            "snapshot_payload_sha256": "SYNTHETIC_PREDECESSOR_NOT_CONSUMED_AS_CHILD",
        },
    )
    refs: list[dict[str, object]] = []
    parent_path, parent_sha, parent_session = predecessor_path, predecessor_sha, predecessor
    for position, session in enumerate(dates, start=1):
        paper_path = evidence / "paperstate" / f"{session}.json"
        paper_sha = _atomic_json(paper_path, _snapshot_payload(session, parent_path, parent_sha, parent_session))
        execution_path = evidence / "executions" / f"{session}.json"
        execution_sha = _atomic_json(
            execution_path,
            {
                "schema_version": "idx_trade_e2e_paper_execution_v1",
                "status": "EXECUTION_COMPLETE",
                "execution_session_date": session,
                "runtime_snapshot_path": str(paper_path.resolve()),
                "runtime_snapshot_sha256": paper_sha,
            },
        )
        stages = [
            {
                "stage": "official_open_evidence",
                "status": "PASS",
                "artifact_path": None,
                "artifact_sha256": None,
                "observed": {},
            },
            {
                "stage": "paper_execution",
                "status": "PASS",
                "artifact_path": str(execution_path.resolve()),
                "artifact_sha256": execution_sha,
                "observed": {},
            },
            {
                "stage": "paperstate_continuity",
                "status": "PASS",
                "artifact_path": str(paper_path.resolve()),
                "artifact_sha256": paper_sha,
                "observed": {},
            },
        ]
        ledger_path = evidence / "audit" / f"{session}.json"
        ledger_sha = _atomic_json(
            ledger_path,
            {
                "schema": "idx_trade_forward_session_audit_v1",
                "ledger_anchor": "execution_session_date",
                "session_date": session,
                "execution_session_date": session,
                "decision_session_date": parent_session,
                "overall_status": "SESSION_HEALTHY",
                "runtime_identity": {},
                "stages": stages,
                "blockers": [],
                "guards": {
                    "protected_outcomes_accessed": False,
                    "real_protected_loader_called": False,
                    "real_outcome_access_marker_written": False,
                    "provider_capture_triggered": False,
                    "model_changed": False,
                    "forward_counter_changed": False,
                },
                "reported_at_utc": "2026-01-01T00:00:00+00:00",
            },
        )
        refs.append(
            {
                "session_date": session,
                "forward_position": position,
                "audit_path": str(ledger_path.resolve()),
                "audit_sha256": ledger_sha,
            }
        )
        parent_path, parent_sha, parent_session = paper_path, paper_sha, session
    bridge = evidence / "safe_bridge.json"
    _atomic_json(
        bridge,
        {
            "schema_version": SAFE_SESSION_AUDIT_SCHEMA,
            "outcome_blind": True,
            "predecessor_session_date": predecessor,
            "predecessor_paperstate_path": str(predecessor_path.resolve()),
            "predecessor_paperstate_sha256": predecessor_sha,
            "session_ledgers": refs,
        },
    )
    return bridge


def _write_synthetic_benchmark_source(root: Path, dates: list[str]) -> None:
    for session in dates:
        destination = root / "forward_monitoring" / "sessions" / session / "idx_index_summary.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {
                    "session_date": session,
                    "index_code": "COMPOSITE",
                    "close": 7000.0 + len(session),
                    "source": "IDX_SYNTHETIC_REHEARSAL",
                    "source_ref": f"synthetic:{session}",
                    "source_sha256": hashlib.sha256(session.encode("utf-8")).hexdigest(),
                    "source_retrieved_at": f"{session}T16:00:00+07:00",
                }
            ]
        ).to_csv(destination, index=False)


def _synthetic(args: argparse.Namespace) -> dict[str, object]:
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    repo = args.repo_root.resolve()
    source = root / "source-scores"
    staging = root / "staging"
    benchmark_source = root / "benchmark-source"
    clean_access_root = root / "clean-real-access-root-analogue"
    clean_access_root.mkdir(parents=True, exist_ok=True)
    assert_isolated_staging_root(staging, source_roots=(source, benchmark_source), forbidden_roots=(repo,))
    staging.mkdir(parents=True, exist_ok=True)

    contract_source = repo / "config" / "v4_x1_prospective_evaluation_contract_v1.json"
    contract = staging / "contract.json"
    if not contract.exists():
        contract.write_bytes(contract_source.read_bytes())
    contract_payload = json.loads(contract.read_text(encoding="utf-8"))
    spec_name = str(contract_payload["target_identity"]["target_spec_path"])
    spec_source = repo / "config" / spec_name
    (staging / Path(spec_name).name).write_bytes(spec_source.read_bytes())
    construction = (staging / str(contract_payload["target_identity"]["construction_code"]["path"])).resolve()
    construction.parent.mkdir(parents=True, exist_ok=True)
    construction.write_bytes((repo / "src" / "idx_trade" / "v4_x1_canonical_target_v1.py").read_bytes())

    dates = [value.date().isoformat() for value in pd.bdate_range("2026-01-02", periods=100)]
    predecessor = (pd.Timestamp(dates[0]) - pd.offsets.BDay(1)).date().isoformat()
    projections: list[dict[str, object]] = []
    for index, session in enumerate(dates, start=1):
        source_item = write_synthetic_score_session(source, session, row_count=3, session_index=index, production_shape=True)
        projections.append(
            project_verified_score_session(
                source_item["projected_manifest_path"],
                source_root=source,
                output_root=staging,
                expected_session=session,
            )
        )
    inventory, partial_manifest = build_admitted_inventory(projections, official_sessions=dates, output_root=staging)
    canonical = finalize_canonical_admitted_inventory(inventory, output_root=staging)

    counter_status = staging / "synthetic_runtime_counter.json"
    counter_status.write_text(
        json.dumps({"x1_counter": {"completed": 100, "target": 100, "remaining": 0, "sessions": dates}}, sort_keys=True),
        encoding="utf-8",
    )
    counter = reconcile_runtime_counter(
        counter_status,
        inventory,
        canonical_inventory=canonical,
        attestation_path=staging / "counter_attestation.json",
    )

    bridge = _write_synthetic_session_audit_chain(root, dates, predecessor)
    paper = produce_paper_attestation_from_safe_audit(
        bridge,
        output_path=staging / "paper_attestation.json",
        expected_sessions=dates,
        predecessor_session_date=predecessor,
        evidence_root=root / "paper-evidence",
    )

    prior = build_prior_access_audit(
        clean_access_root,
        output_path=staging / "access_audit.json",
        canonical_root_id=CANONICAL_REAL_ACCESS_ROOT_ID,
    )
    if prior.get("status") != "READY":
        raise CompletionArtifactError(f"SYNTHETIC_PRIOR_ACCESS_NOT_READY:{prior}")

    _write_synthetic_benchmark_source(benchmark_source, [predecessor, *dates])
    benchmark = build_local_composite_benchmark(
        benchmark_source,
        sessions=dates,
        predecessor_session_date=predecessor,
        output_root=staging,
    )
    if benchmark.get("status") != "READY_FOR_FINAL_GATE_REVALIDATION":
        raise CompletionArtifactError(f"SYNTHETIC_BENCHMARK_NOT_READY:{benchmark}")

    target = write_synthetic_attestations(
        staging,
        inventory=inventory,
        predecessor_session_date=predecessor,
        contract_path=contract,
    )["target"]

    candidate = staging / ".preflight_bundle.candidate.json"
    candidate_path, candidate_sha = write_preflight_bundle(
        candidate,
        fixture_root=staging,
        inventory=inventory,
        counter=(counter["attestation_path"], counter["attestation_sha256"]),
        target=target,
        paper=(paper["paper_attestation_path"], paper["paper_attestation_sha256"]),
        benchmark=(benchmark["attestation_path"], benchmark["attestation_sha256"]),
        access_audit=(prior["path"], prior["sha256"]),
    )
    contract_sha = sha256_file(contract)
    validate_preflight_bundle(candidate_path, candidate_sha, contract_path=contract, contract_sha256=contract_sha)
    candidate_bytes = Path(candidate_path).read_bytes()
    Path(candidate_path).unlink()
    bundle = staging / "preflight_bundle.json"
    bundle_sha = _atomic_immutable_bytes(bundle, candidate_bytes)
    validate_preflight_bundle(bundle, bundle_sha, contract_path=contract, contract_sha256=contract_sha)

    evaluator = repo / "tools" / "evaluate_prospective_v4_x1.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(evaluator),
            "--preflight-only",
            "--contract",
            str(contract),
            "--contract-sha256",
            contract_sha,
            "--preflight-bundle",
            str(bundle),
            "--preflight-bundle-sha256",
            bundle_sha,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    evaluator_result = json.loads(completed.stdout)
    if evaluator_result.get("status") != "PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT":
        raise CompletionArtifactError(f"SYNTHETIC_EVALUATOR_NOT_READY:{evaluator_result}")

    report = {
        "schema_version": COMPLETION_SCHEMA,
        "mode": "SYNTHETIC_PRODUCER_PATH_REHEARSAL",
        "session_count": len(inventory),
        "partial_inventory_sha256": partial_manifest["partial_admitted_gate_shape_sha256"],
        "canonical_inventory_sha256": canonical["canonical_admitted_gate_inventory_sha256"],
        "counter_attestation_sha256": counter["attestation_sha256"],
        "paper_attestation_sha256": paper["paper_attestation_sha256"],
        "benchmark_attestation_sha256": benchmark["attestation_sha256"],
        "access_audit_sha256": prior["sha256"],
        "preflight_bundle_path": str(bundle),
        "preflight_bundle_sha256": bundle_sha,
        "contract_path": str(contract),
        "contract_sha256": contract_sha,
        "evaluator_status": evaluator_result["status"],
        "status": "PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT",
        "protected_outcome_accessed": False,
        "real_protected_loader_called": False,
        "real_outcome_access_marker_written": False,
        "provider_calls": False,
        "runtime_counter_changed": False,
        "paper_state_changed": False,
    }
    _atomic_json(staging / "synthetic_rehearsal_report.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.synthetic_rehearsal:
            report = _synthetic(args)
        elif args.audit_only:
            report = _real_audit(args, project=False)
        elif args.project_scores or args.assemble_partial:
            report = _real_audit(args, project=True)
        else:
            raise CompletionArtifactError("EXPLICIT_MODE_REQUIRED")
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True, indent=2))
        return 1
    print(json.dumps(report, sort_keys=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
