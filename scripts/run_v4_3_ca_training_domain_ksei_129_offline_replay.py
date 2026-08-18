"""Offline V4-3 CA training-domain replay with the accepted KSEI 129 delta.

This runner never calls a provider.  It verifies the exact accepted 93/129
KSEI acquisition manifest, appends all 129 coverage rows in memory to the
immutable final 611-ticker CA census, keeps the 36 acquisition failures
explicitly unresolved, appends only certified normalized history rows, and
replays the unchanged V4-3 combined target-support gate.

No return, target rank, model fit, prediction, performance metric, or protected
forward outcome is read or produced.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = Path(__file__).resolve().parent
for value in (SRC_ROOT, SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import run_v4_3_ca_training_domain_gate as gate  # noqa: E402
import run_v4_ca_fren_ksei_exact_replay as fren_final  # noqa: E402

from idx_trade.ranking_v4_3_ca_training_domain import (  # noqa: E402
    attach_continuity,
    build_training_date_sets,
    build_window_skeleton,
    combine_target_support,
    validate_frozen_tail,
)
from idx_trade.ranking_v4_3_ca_training_ksei_overlay import (  # noqa: E402
    merge_coverage_and_history,
)
from idx_trade.v4_ca_event_windows import window_continuity  # noqa: E402
from idx_trade.v4_ca_fren_ksei_schedule_semantics import (  # noqa: E402
    EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256,
    synthetic_fren_rights_event_ksei,
)
from idx_trade.v4_ksei_coverage_gap import sha256_file  # noqa: E402


DEFAULT_CONFIG = Path("config/v4_3_ca_training_domain_ksei_129_v1.json")


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RuntimeError(f"JSONL_MISSING:{path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError(f"JSONL_ROW_NOT_OBJECT:{path}:{line_number}")
            rows.append(value)
    return rows


def load_config(path: Path) -> dict[str, Any]:
    config = read_json(path, "CONFIG")
    if config.get("schema_version") != "v4_3_ca_training_domain_ksei_129_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    if not isinstance(config.get("accepted_delta"), dict):
        raise RuntimeError("ACCEPTED_DELTA_NOT_PINNED")
    hard = config.get("hard_boundaries") or {}
    for key in (
        "full_parent_recrawl",
        "alternate_provider",
        "alternate_ksei_security_identity",
        "parser_or_semantic_relaxation",
        "target_or_rank_materialization",
        "model_fit",
        "prediction",
        "performance",
        "protected_forward_access",
    ):
        if hard.get(key) is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")
    return config


def verify_delta_root(
    root: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    accepted = config["accepted_delta"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    coverage_path = root / "ticker_coverage_delta_129.csv"
    history_path = root / "ksei_ca_history_delta_129.jsonl"
    request_path = root / "request_records_delta_129.jsonl"
    results_path = root / "recovery_results_129.csv"

    actual_manifest = sha256_file(manifest_path)
    expected_manifest = str(accepted["manifest_sha256"])
    if actual_manifest != expected_manifest:
        raise RuntimeError(
            f"KSEI_129_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected_manifest}"
        )
    manifest = read_json(manifest_path, "KSEI_129_MANIFEST")
    summary = read_json(summary_path, "KSEI_129_SUMMARY")
    expected_status = str(accepted["status"])
    if manifest.get("status") != expected_status or summary.get("status") != expected_status:
        raise RuntimeError("KSEI_129_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("KSEI_129_NOT_OUTCOME_BLIND")

    expected_identity = str(
        config["blocked_training_gate"]["missing_ticker_identity_sha256"]
    )
    if manifest.get("ticker_identity_sha256") != expected_identity:
        raise RuntimeError("KSEI_129_TICKER_IDENTITY_CHANGED")
    if int(manifest.get("ticker_count") or -1) != int(accepted["ticker_count"]):
        raise RuntimeError("KSEI_129_TICKER_COUNT_CHANGED")

    guardrails = manifest.get("guardrails") or {}
    for key in (
        "target_or_rank_materialized",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
        "scientific_config_changed",
        "source_substitution",
        "parser_relaxation",
    ):
        if guardrails.get(key) is not False:
            raise RuntimeError(f"KSEI_129_GUARDRAIL_CHANGED:{key}")

    outputs = manifest.get("output_hashes") or {}
    expected_paths = {
        "ticker_coverage_delta_129": coverage_path,
        "ksei_ca_history_delta_129": history_path,
        "request_records_delta_129": request_path,
        "recovery_results_129": results_path,
        "summary": summary_path,
    }
    child_hashes: dict[str, str] = {}
    for key, path in expected_paths.items():
        expected = str(outputs.get(key) or "")
        if not expected:
            raise RuntimeError(f"KSEI_129_CHILD_HASH_MISSING:{key}")
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"KSEI_129_CHILD_SHA_MISMATCH:{key}:{actual}!={expected}")
        child_hashes[key] = actual

    for key in (
        "target_or_rank_materialized",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
        "scientific_config_changed",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"KSEI_129_SUMMARY_GUARDRAIL_CHANGED:{key}")
    if int(summary.get("coverage_certified_tickers") or -1) != int(
        accepted["coverage_certified_tickers"]
    ):
        raise RuntimeError("KSEI_129_CERTIFIED_COUNT_CHANGED")
    if int(summary.get("coverage_unresolved_tickers") or -1) != int(
        accepted["coverage_unresolved_tickers"]
    ):
        raise RuntimeError("KSEI_129_UNRESOLVED_COUNT_CHANGED")
    if int(summary.get("history_rows") or -1) != int(accepted["history_rows"]):
        raise RuntimeError("KSEI_129_HISTORY_ROW_COUNT_CHANGED")
    if summary.get("failure_class_counts") != accepted.get("failure_class_counts"):
        raise RuntimeError("KSEI_129_FAILURE_CLASS_COUNTS_CHANGED")

    coverage = pd.read_csv(coverage_path)
    history = read_jsonl(history_path)
    return coverage, history, {
        "manifest_sha256": actual_manifest,
        "child_hashes": child_hashes,
        "status": expected_status,
        "ticker_count": int(accepted["ticker_count"]),
        "coverage_certified_tickers": int(accepted["coverage_certified_tickers"]),
        "coverage_unresolved_tickers": int(accepted["coverage_unresolved_tickers"]),
        "history_rows": int(accepted["history_rows"]),
        "unresolved_tickers": list(summary.get("coverage_unresolved_ticker_list") or []),
    }


def build_expanded_ca_continuity(
    *,
    args: argparse.Namespace,
    lineage: dict[str, Any],
    calendar: pd.DataFrame,
    windows: pd.DataFrame,
    delta_coverage: pd.DataFrame,
    delta_history: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    parent = fren_final.base.verify_parent_roots(args.material_six_root, args.adro_root)
    material_summary = read_json(parent["material_summary"], "MATERIAL_SIX_SUMMARY")
    fren_merger_sha = str(
        (material_summary.get("fren_official_evidence") or {}).get("source_sha256") or ""
    )
    mega_sha = str(
        (material_summary.get("mega_official_evidence") or {}).get("source_sha256") or ""
    )
    if not fren_merger_sha or not mega_sha:
        raise RuntimeError("TRAINING_DOMAIN_SYNTHETIC_EVENT_SOURCE_SHA_MISSING")
    adro_evidence = fren_final.base.verify_adro_official_documents(
        parent["adro_prospectus"].read_bytes(), parent["adro_egms"].read_bytes()
    )

    census_root = Path(lineage["census_root"])
    parent_coverage = pd.read_csv(census_root / "ticker_coverage.csv")
    parent_history = read_jsonl(census_root / "ksei_ca_history.jsonl")
    coverage, history, overlay_diag = merge_coverage_and_history(
        parent_coverage=parent_coverage,
        parent_history=parent_history,
        delta_coverage=delta_coverage,
        delta_history=delta_history,
        expected_delta_tickers=129,
        expected_delta_certified=93,
        expected_delta_unresolved=36,
    )
    coverage_map = dict(zip(coverage["ticker"], coverage["coverage_certified"]))

    schedule = pd.read_csv(parent["schedule"]).to_dict("records")
    prior = pd.read_csv(args.prior_event_evidence)
    prior["ticker"] = (
        prior["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    prior["candidate_date"] = (
        pd.to_datetime(prior["candidate_date"], errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    if prior["candidate_date"].isna().any():
        raise RuntimeError("TRAINING_DOMAIN_PRIOR_EVENT_DATE_INVALID")

    period_start = pd.to_datetime(windows["entry_date"]).min()
    period_end = pd.to_datetime(windows["terminal_date"]).max()

    frozen = fren_final.base.frozen
    original_classifier = frozen.classify_event
    try:
        frozen.classify_event = fren_final.base.make_classifier(adro_evidence, fren_merger_sha)
        prior_tickers = set(
            frozen.prior_candidate_tickers(
                prior, period_start=period_start, period_end=period_end
            )
        )
        if "SCMA" in prior_tickers:
            fren_final.base.material_base.validate_scma_halo_only(
                prior, max_terminal=pd.Timestamp(period_end)
            )
            prior_tickers.remove("SCMA")
        events_by_ticker, audit = frozen.build_events(
            history,
            official_sessions=calendar["date"].tolist(),
            schedule=schedule,
            period_start=period_start,
            period_end=period_end,
        )
    finally:
        frozen.classify_event = original_classifier

    rows = audit.to_dict("records")
    rights_event = synthetic_fren_rights_event_ksei(EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256)
    additions = (
        (fren_final.base.material_base.synthetic_mega_event(mega_sha), "MEGA_ISSUER_OFFICIAL"),
        (fren_final.base.material_base.synthetic_fren_event(fren_merger_sha), "FREN_ISSUER_OFFICIAL_MERGER"),
        (rights_event, "FREN_KSEI_OFFICIAL_PMHETD_V_EX_RIGHT"),
    )
    for event, marker in additions:
        events_by_ticker.setdefault(event.ticker, []).append(event)
        rows.append(
            {
                "event_id": event.event_id,
                "ticker": event.ticker,
                "source_type": event.source_type,
                "family": event.family,
                "semantic_class": event.semantic_class,
                "transition_date": (
                    event.transition_date.date().isoformat()
                    if event.transition_date is not None
                    else ""
                ),
                "transition_source": event.transition_source or "",
                "reason": event.reason,
                "source_dates": "|".join(
                    value.date().isoformat() for value in event.source_dates
                ),
                "material_six_source_marker": marker,
            }
        )
    audit = pd.DataFrame(rows).fillna("").sort_values(
        ["ticker", "source_dates", "source_type", "event_id"], kind="mergesort"
    ).reset_index(drop=True)

    represented = {
        ticker
        for ticker, events in events_by_ticker.items()
        if any(event.semantic_class != "NON_BLOCKING" for event in events)
    }
    cross_source_conflicts = prior_tickers - represented

    continuity_rows: list[dict[str, Any]] = []
    missing_coverage_rows = 0
    for row in windows.itertuples(index=False):
        ticker = str(row.ticker)
        covered = bool(coverage_map.get(ticker, False))
        if ticker not in coverage_map:
            missing_coverage_rows += 1
        result = window_continuity(
            coverage_certified=covered,
            cross_source_conflict=ticker in cross_source_conflicts,
            events=events_by_ticker.get(ticker, []),
            entry_date=row.entry_date,
            terminal_date=row.terminal_date,
        )
        continuity_rows.append(
            {
                "ticker": ticker,
                "signal_date": pd.Timestamp(row.signal_date),
                "signal_session_index": int(row.signal_session_index),
                "horizon": int(row.horizon),
                "entry_date": pd.Timestamp(row.entry_date),
                "terminal_date": pd.Timestamp(row.terminal_date),
                "continuity_status": result.status,
                "continuity_reason": result.reason,
                "blocking_event_ids": "|".join(result.blocking_event_ids),
                "blocking_transition_dates": "|".join(result.blocking_transition_dates),
                "policy_id": "V4_CA_EVENT_WINDOW_SEMANTICS_V1",
            }
        )
    continuity = pd.DataFrame(continuity_rows)
    decision_tickers = set(windows["ticker"].astype(str))
    missing_tickers = sorted(decision_tickers - set(coverage_map))
    unresolved_in_decision = sorted(
        ticker
        for ticker in decision_tickers
        if ticker in coverage_map and not bool(coverage_map[ticker])
    )
    diagnostics = {
        "period_start": pd.Timestamp(period_start).date().isoformat(),
        "period_end": pd.Timestamp(period_end).date().isoformat(),
        "decision_tickers": len(decision_tickers),
        "coverage_census_tickers": len(coverage_map),
        "coverage_certified_tickers_total": int(sum(bool(value) for value in coverage_map.values())),
        "coverage_unresolved_tickers_total": int(sum(not bool(value) for value in coverage_map.values())),
        "coverage_unresolved_decision_tickers": len(unresolved_in_decision),
        "coverage_unresolved_decision_ticker_list": unresolved_in_decision,
        "coverage_missing_historical_tickers": len(missing_tickers),
        "coverage_missing_historical_ticker_list": missing_tickers,
        "coverage_missing_window_rows": int(missing_coverage_rows),
        "cross_source_conflict_tickers": sorted(cross_source_conflicts),
        "event_semantic_counts": dict(Counter(audit["semantic_class"].astype(str))),
        "overlay_merge": overlay_diag,
    }
    return continuity, audit, diagnostics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--open-derivative-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--pit-support-root", type=Path, required=True)
    parser.add_argument("--material-six-root", type=Path, required=True)
    parser.add_argument("--adro-root", type=Path, required=True)
    parser.add_argument("--fren-final-root", type=Path, required=True)
    parser.add_argument("--admission-root", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--ksei-129-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    if not args.prior_event_evidence.is_file():
        raise RuntimeError(f"PRIOR_EVENT_EVIDENCE_MISSING:{args.prior_event_evidence}")

    config = load_config(args.config)
    delta_coverage, delta_history, delta_diag = verify_delta_root(args.ksei_129_root, config)
    lineage = gate.verify_pretarget_lineage(args)
    paths = gate.verify_support_inputs(args)
    folds = pd.read_csv(lineage["folds_path"])
    folds["date"] = pd.to_datetime(folds["date"], errors="coerce").dt.normalize()
    if len(folds) != 600 or folds["date"].isna().any():
        raise RuntimeError("TRAINING_DOMAIN_FROZEN_FOLDS_INVALID")

    calendar, decision_support, support_diagnostics = gate.rebuild_decision_support(paths, folds)
    max_signal = int(folds["session_index"].max())
    windows = build_window_skeleton(
        decision_support,
        calendar["date"],
        max_signal_session_index=max_signal,
    )
    continuity, event_audit, ca_diagnostics = build_expanded_ca_continuity(
        args=args,
        lineage=lineage,
        calendar=calendar,
        windows=windows,
        delta_coverage=delta_coverage,
        delta_history=delta_history,
    )
    continuity = attach_continuity(windows, continuity)
    combined_rows, per_date = combine_target_support(decision_support, continuity)
    training_dates = build_training_date_sets(per_date, folds)
    frozen_check = validate_frozen_tail(per_date, folds)

    if training_dates.empty:
        fold_counts = pd.DataFrame(columns=["fold", "head", "training_dates"])
    else:
        fold_counts = (
            training_dates.groupby(["fold", "head"], sort=True)
            .size()
            .rename("training_dates")
            .reset_index()
        )
    expected_pairs = {(fold, head) for fold in range(1, 7) for head in ("H5", "H10")}
    observed_pairs = set(zip(fold_counts["fold"], fold_counts["head"]))
    all_training_sets_nonempty = observed_pairs == expected_pairs and bool(
        len(fold_counts) and fold_counts["training_dates"].gt(0).all()
    )

    pass_gate = bool(
        frozen_check["all_frozen_600_full_target_eligible"]
        and frozen_check["tail_600_identity_unchanged"]
        and int(frozen_check["eligible_sessions_after_frozen_end"]) == 0
        and all_training_sets_nonempty
    )
    status = (
        "V4_3_CA_TRAINING_DOMAIN_KSEI_129_OFFLINE_REPLAY_PASS_READY_FOR_HISTORICAL_EXECUTION_PIN"
        if pass_gate
        else "V4_3_CA_TRAINING_DOMAIN_KSEI_129_OFFLINE_REPLAY_BLOCKED_REVIEW_REQUIRED"
    )

    args.output_dir.mkdir(parents=True)
    outputs = {
        "continuity": args.output_dir / "v4_3_ca_training_domain_ksei129_continuity.csv",
        "combined": args.output_dir / "v4_3_full_target_support_rows_ksei129.csv",
        "per_date": args.output_dir / "v4_3_full_target_support_per_date_ksei129.csv",
        "training_dates": args.output_dir / "v4_3_training_date_sets_ksei129.csv",
        "event_audit": args.output_dir / "v4_3_ca_training_event_semantics_ksei129.csv",
        "summary": args.output_dir / "summary.json",
        "manifest": args.output_dir / "MANIFEST.json",
    }
    continuity.to_csv(outputs["continuity"], index=False, lineterminator="\n")
    combined_rows.to_csv(outputs["combined"], index=False, lineterminator="\n")
    per_date.to_csv(outputs["per_date"], index=False, lineterminator="\n")
    training_dates.to_csv(outputs["training_dates"], index=False, lineterminator="\n")
    event_audit.to_csv(outputs["event_audit"], index=False, lineterminator="\n")

    summary = {
        "schema_version": "ranking_v4_3_ca_training_domain_ksei_129_offline_replay_v1",
        "status": status,
        "outcome_blind": True,
        "provider_calls": False,
        "network_calls": False,
        "historical_target_loaded": False,
        "historical_target_rank_materialized": False,
        "historical_model_fit": False,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "protected_forward_accessed": False,
        "scientific_config_changed": False,
        "price_inference": False,
        "record_date_inference": False,
        "excl_price_stitching": False,
        "ksei_129_delta": delta_diag,
        "decision_rows_through_frozen_end": int(len(decision_support)),
        "decision_dates_through_frozen_end": int(decision_support["date"].nunique()),
        "decision_tickers_through_frozen_end": int(decision_support["ticker"].nunique()),
        "continuity_window_rows": int(len(continuity)),
        "full_eligible_sessions": {
            "h5": int(per_date["h5_eligible"].sum()),
            "h10": int(per_date["h10_eligible"].sum()),
            "consensus": int(per_date["consensus_eligible"].sum()),
        },
        "frozen_validation": frozen_check,
        "training_date_counts": fold_counts.to_dict("records"),
        "all_fold_head_training_sets_nonempty": all_training_sets_nonempty,
        "support_diagnostics": support_diagnostics,
        "ca_diagnostics": ca_diagnostics,
        "parent_admission_manifest_sha256": gate.EXPECTED_ADMISSION_MANIFEST,
        "parent_pit_support_manifest_sha256": gate.EXPECTED_PIT_SUPPORT_MANIFEST,
        "parent_final_ca_manifest_sha256": gate.EXPECTED_FINAL_CA_MANIFEST,
        "parent_ksei_129_manifest_sha256": config["accepted_delta"]["manifest_sha256"],
        "next": (
            "PIN_KSEI_129_OFFLINE_REPLAY_IN_FINAL_HISTORICAL_EXECUTION_RUNNER"
            if pass_gate
            else "REVIEW_RESIDUAL_CA_BLOCKERS_WITHOUT_TARGET_ACCESS"
        ),
    }
    outputs["summary"].write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output_hashes = {
        key: sha256_file(path)
        for key, path in outputs.items()
        if key != "manifest"
    }
    manifest = {
        "schema_version": "ranking_v4_3_ca_training_domain_ksei_129_offline_manifest_v1",
        "status": status,
        "outcome_blind": True,
        "immutable_inputs": {
            "admission_manifest": gate.EXPECTED_ADMISSION_MANIFEST,
            "pit_support_manifest": gate.EXPECTED_PIT_SUPPORT_MANIFEST,
            "final_ca_manifest": gate.EXPECTED_FINAL_CA_MANIFEST,
            "ksei_129_manifest": config["accepted_delta"]["manifest_sha256"],
            "validation_folds": gate.EXPECTED_VALIDATION_FOLDS,
        },
        "output_hashes": output_hashes,
        "guardrails": {
            "provider_calls": False,
            "network_calls": False,
            "historical_target_loaded": False,
            "historical_target_rank_materialized": False,
            "historical_model_fit": False,
            "historical_prediction_generated": False,
            "historical_performance_computed": False,
            "protected_forward_accessed": False,
            "scientific_config_changed": False,
        },
    }
    outputs["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "status": status,
                "manifest": str(outputs["manifest"]),
                "manifest_sha256": sha256_file(outputs["manifest"]),
                "ksei_129_certified": delta_diag["coverage_certified_tickers"],
                "ksei_129_unresolved": delta_diag["coverage_unresolved_tickers"],
                "coverage_census_tickers": ca_diagnostics["coverage_census_tickers"],
                "coverage_certified_tickers_total": ca_diagnostics[
                    "coverage_certified_tickers_total"
                ],
                "coverage_unresolved_decision_tickers": ca_diagnostics[
                    "coverage_unresolved_decision_tickers"
                ],
                "coverage_missing_historical_tickers": ca_diagnostics[
                    "coverage_missing_historical_tickers"
                ],
                "cross_source_conflict_tickers": ca_diagnostics[
                    "cross_source_conflict_tickers"
                ],
                "full_eligible_sessions": summary["full_eligible_sessions"],
                "frozen_validation": frozen_check,
                "training_date_counts": summary["training_date_counts"],
                "historical_target_loaded": False,
                "historical_model_fit": False,
                "historical_performance_computed": False,
                "next": summary["next"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
