"""Safe operator CLI for V4-X1 pre-access artifact completion.

Modes are explicit and outcome-blind.  No mode calls a provider, protected
loader, target producer, scorer, runtime counter writer, or scheduler.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.prospective_evaluation_gate_v1 import validate_preflight_bundle, validate_session_inventory
from idx_trade.prospective_preaccess_adapters_v1 import (
    adapt_code_pins,
    build_production_readiness,
    discover_named_component,
    discover_score_inventory,
    load_official_schedule,
    sha256_file,
)
from idx_trade.prospective_preaccess_completion_v1 import (
    COMPLETION_SCHEMA,
    CompletionArtifactError,
    _atomic_json,
    build_admitted_inventory,
    project_verified_score_session,
    reconcile_runtime_counter,
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
    return parser


def _audit_local_index(root: Path, sessions: list[str], output: Path) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    missing: list[str] = []
    base = root / "forward_monitoring" / "sessions"
    for session in sessions:
        path = base / session / "idx_index_summary.csv"
        if not path.is_file():
            missing.append(session)
            continue
        frame = pd.read_csv(path)
        required = {"session_date", "index_code", "close", "source", "source_ref", "source_sha256", "source_retrieved_at", "pit_timing_status"}
        if not required.issubset(frame.columns):
            raise CompletionArtifactError(f"BENCHMARK_SOURCE_SCHEMA_INVALID:{session}")
        selected = frame[frame["index_code"].astype(str).str.upper().eq("COMPOSITE")].copy()
        if len(selected) != 1 or str(selected.iloc[0]["session_date"]) != session:
            raise CompletionArtifactError(f"BENCHMARK_COMPOSITE_IDENTITY_INVALID:{session}")
        row = selected.iloc[0]
        rows.append(
            {
                "session_date": session,
                "benchmark_close": float(row["close"]),
                "source": str(row["source"]),
                "source_ref": str(row["source_ref"]),
                "source_sha256": str(row["source_sha256"]),
                "captured_csv_sha256": sha256_file(path),
                "source_retrieved_at": str(row["source_retrieved_at"]),
                "pit_timing_status": str(row["pit_timing_status"]),
            }
        )
    result = {
        "status": "PARTIAL_NOT_GATE_READY" if missing else "READY_FOR_FINAL_GATE_REVALIDATION",
        "source_identity": "IDX_OFFICIAL_INDEX_SUMMARY_COMPOSITE",
        "session_count": len(rows),
        "requested_session_count": len(sessions),
        "missing_sessions": missing,
        "publication_time_claim": "NONE",
        "rows": rows,
    }
    _atomic_json(output / "benchmark_source_audit.json", result)
    return result


def _real_audit(args: argparse.Namespace, *, project: bool) -> dict[str, object]:
    repo = args.repo_root.resolve()
    data_root = (args.data_root or Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v")).resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    monitoring = data_root / "forward_monitoring"
    calendar_path = monitoring / "calendar" / "exchange_sessions.csv"
    sessions, schedule = load_official_schedule(calendar_path)
    model_runs = (args.source_model_runs_root or monitoring / "model_runs").resolve()
    raw_inventory, source = discover_score_inventory(
        model_runs, official_sessions=sessions, data_root=data_root
    )
    projected: list[dict[str, object]] = []
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
    else:
        admitted = pd.DataFrame()
        admitted_manifest = {
            "canonical_admitted_gate_inventory_sha256": "NOT_AVAILABLE",
            "partial_admitted_gate_shape_sha256": "NOT_AVAILABLE",
        }
    counter_path = monitoring / "eod_automation" / "v4_x1_pipeline" / "latest.json"
    counter = (
        reconcile_runtime_counter(counter_path, admitted)
        if project and not admitted.empty
        else {"status": "NOT_AVAILABLE", "runtime_counter_changed": False}
    )
    readiness = build_production_readiness(
        repo_root=repo, data_root=data_root, as_of_session=args.as_of_session
    )
    benchmark = _audit_local_index(data_root, sessions, output)
    report = {
        "schema_version": "v4_x1_preaccess_artifact_completion_report_v1",
        "mode": "PROJECT_SCORES" if project else "AUDIT_ONLY",
        "outcome_blind": True,
        "provider_calls": False,
        "protected_outcome_accessed": False,
        "target_values_loaded": False,
        "calendar": schedule,
        "production_sessions": len(raw_inventory),
        "raw_production_score_admission": source["score_gate_admission"],
        "rolling_partial_inventory_sha256": readiness["readiness"]["inventory"].get("rolling_partial_inventory_sha256"),
        "production_source_gate_shape_sha256": readiness["readiness"]["inventory"].get("production_source_gate_shape_sha256"),
        "canonical_admitted_gate_inventory_sha256": admitted_manifest.get("canonical_admitted_gate_inventory_sha256", "NOT_AVAILABLE"),
        "projected_sessions": projected,
        "admitted_inventory": admitted_manifest,
        "counter": counter,
        "benchmark": benchmark,
        "paper_state": readiness["sources"].get("paper_discovery"),
        "prior_access": readiness["sources"].get("prior_access_discovery"),
        "code_pins": adapt_code_pins(repo),
        "current_readiness": readiness["readiness"],
        "verdict": "V4_X1_PREACCESS_ARTIFACT_COMPLETION_V1_REVIEW_READY",
    }
    _atomic_json(output / "completion_report.json", report)
    return report


def _synthetic(args: argparse.Namespace) -> dict[str, object]:
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    repo = args.repo_root.resolve()
    contract_source = repo / "config" / "v4_x1_prospective_evaluation_contract_v1.json"
    contract = root / "contract.json"
    if not contract.exists():
        contract.write_bytes(contract_source.read_bytes())
    contract_payload = json.loads(contract.read_text(encoding="utf-8"))
    spec_name = str(contract_payload["target_identity"]["target_spec_path"])
    spec_source = repo / "config" / spec_name
    (root / Path(spec_name).name).write_bytes(spec_source.read_bytes())
    construction = (root / str(contract_payload["target_identity"]["construction_code"]["path"])).resolve()
    construction.parent.mkdir(parents=True, exist_ok=True)
    construction.write_bytes((repo / "src" / "idx_trade" / "v4_x1_canonical_target_v1.py").read_bytes())
    dates = [value.date().isoformat() for value in pd.date_range("2026-01-01", periods=100, freq="D")]
    projections = [
        write_synthetic_score_session(root, date, row_count=3, session_index=index)
        for index, date in enumerate(dates, 1)
    ]
    inventory, inventory_manifest = build_admitted_inventory(
        projections, official_sessions=dates, output_root=root
    )
    validate_session_inventory(inventory, fixture_root=root)
    status = root / "synthetic_runtime_counter.json"
    status.write_text(
        json.dumps({"x1_counter": {"completed": 100, "target": 100, "remaining": 0, "sessions": dates}}, sort_keys=True),
        encoding="utf-8",
    )
    counter = reconcile_runtime_counter(status, inventory, attestation_path=root / "counter_attestation.json")
    attestations = write_synthetic_attestations(
        root, inventory=inventory, predecessor_session_date="2025-12-31", contract_path=contract
    )
    bundle_path, bundle_sha = write_preflight_bundle(
        root / "preflight_bundle.json",
        fixture_root=root,
        inventory=inventory,
        counter=(counter["attestation_path"], counter["attestation_sha256"]),
        target=attestations["target"],
        paper=attestations["paper"],
        benchmark=attestations["benchmark"],
        access_audit=attestations["access_audit"],
    )
    contract_sha = sha256_file(contract)
    validate_preflight_bundle(bundle_path, bundle_sha, contract_path=contract, contract_sha256=contract_sha)
    report = {
        "schema_version": COMPLETION_SCHEMA,
        "mode": "SYNTHETIC_REHEARSAL",
        "session_count": len(inventory),
        "inventory_sha256": inventory_manifest["canonical_admitted_gate_inventory_sha256"],
        "counter_attestation_sha256": counter["attestation_sha256"],
        "preflight_bundle_path": bundle_path,
        "preflight_bundle_sha256": bundle_sha,
        "contract_path": str(contract),
        "contract_sha256": contract_sha,
        "status": "SYNTHETIC_PREACCESS_VALIDATORS_PASS",
        "protected_outcome_accessed": False,
        "provider_calls": False,
    }
    _atomic_json(root / "synthetic_rehearsal_report.json", report)
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
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
