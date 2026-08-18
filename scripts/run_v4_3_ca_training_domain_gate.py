"""Outcome-blind V4-3 Corporate Action training-domain gate.

The accepted V4-3 CA admission replay certified the frozen 600 validation
sessions.  Walk-forward fitting, however, also uses earlier target-eligible
training dates.  This runner closes that pre-target gap without materializing
returns or ranks:

1. rebuild the frozen PIT-safe primary-liquid decision universe;
2. rebuild only boolean market/Open/Close support, never future return values;
3. replay the accepted final CA event semantics over every decision window up
   to the frozen validation end;
4. fail closed for historical-only tickers absent from the accepted CA census;
5. combine price-observability and CA continuity at the frozen 90% date gate;
6. freeze the exact H5/H10 training-date identities available to each fold;
7. prove that the original 600 validation dates remain the unchanged tail-600.

No provider call, model fit, prediction, target/rank materialization, return
calculation, performance metric, or protected-forward access occurs here.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = Path(__file__).resolve().parent
for value in (SRC_ROOT, SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import run_v4_3_pit_support_refresh as pit  # noqa: E402
import run_v4_ca_fren_ksei_exact_replay as fren_final  # noqa: E402

from idx_trade.ranking_v4_3_ca_training_domain import (  # noqa: E402
    attach_continuity,
    build_training_date_sets,
    build_window_skeleton,
    combine_target_support,
    validate_frozen_tail,
)
from idx_trade.ranking_v4_3_features import build_v4_control_feature_table  # noqa: E402
from idx_trade.v4_ca_event_windows import window_continuity  # noqa: E402
from idx_trade.v4_ca_fren_ksei_schedule_semantics import (  # noqa: E402
    EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256,
    synthetic_fren_rights_event_ksei,
)
from idx_trade.v4_ksei_coverage_gap import sha256_file  # noqa: E402


EXPECTED_ADMISSION_MANIFEST = "b0e29702d0f284c050472d6bfe05a45477082ae6b2df30866bb3e66bb2888345"
EXPECTED_PIT_SUPPORT_MANIFEST = "7a15008ccd565678ae85c8a78ce50aac696304b9ddfaca554a35cd38e929cf0b"
EXPECTED_FINAL_CA_MANIFEST = "6cb1e660c6baa2d9b7a7aca5cece66691d5cd9564378104b618eed2cfce610ab"
EXPECTED_FINAL_CA_CENSUS = {
    "MANIFEST.json": "adefbc35a56e05a555b681acbd780fb9c5fad30621f8fa8ba04afd5efd836df8",
    "summary.json": "9c0db804fe8158a11136b44f9be57c7c17800987b5cb475c7d387c2de9cba54f",
    "ticker_coverage.csv": "954a270be85722a408c41c535077df0ab58dfadb656d4fa86b7dc9df370788ed",
    "ksei_ca_history.jsonl": "4dcdd9e44cc40e348079c1447aa3e1e20427b000247be5be91b6622fb03e997d",
}
EXPECTED_VALIDATION_FOLDS = "91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915"
VALIDATION_FOLDS_REPO_PATH = Path(
    "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_validation_folds.csv"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def verify_sha(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label}_SHA_MISMATCH:{actual}!={expected}")
    return actual


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def verify_pretarget_lineage(args: argparse.Namespace) -> dict[str, Any]:
    admission_path = args.admission_root / "v4_3_ca_admission_manifest.json"
    verify_sha(admission_path, EXPECTED_ADMISSION_MANIFEST, "CA_ADMISSION_MANIFEST")
    admission = read_json(admission_path, "CA_ADMISSION_MANIFEST")
    if admission.get("status") != "V4_3_CA_ADMISSION_PASS_HISTORICAL_EXECUTION_AUTHORIZED":
        raise RuntimeError("CA_ADMISSION_STATUS_CHANGED")
    for key in (
        "historical_target_loaded",
        "historical_model_fit",
        "historical_performance_computed",
        "protected_forward_accessed",
        "provider_calls",
    ):
        if admission.get(key) is not False:
            raise RuntimeError(f"CA_ADMISSION_PRETARGET_GUARDRAIL_CHANGED:{key}")

    pit_manifest_path = args.pit_support_root / "manifest.json"
    verify_sha(pit_manifest_path, EXPECTED_PIT_SUPPORT_MANIFEST, "PIT_SUPPORT_MANIFEST")
    pit_manifest = read_json(pit_manifest_path, "PIT_SUPPORT_MANIFEST")

    ca_manifest_path = args.fren_final_root / "MANIFEST.json"
    verify_sha(ca_manifest_path, EXPECTED_FINAL_CA_MANIFEST, "FINAL_CA_MANIFEST")
    ca_manifest = read_json(ca_manifest_path, "FINAL_CA_MANIFEST")
    if ca_manifest.get("status") != "V4_CA_FREN_KSEI_EXACT_REPLAY_COMPLETE":
        raise RuntimeError("FINAL_CA_STATUS_CHANGED")

    census_root = args.fren_final_root / "fren_ksei_exact_census_611"
    for name, expected in EXPECTED_FINAL_CA_CENSUS.items():
        verify_sha(census_root / name, expected, f"FINAL_CA_CENSUS_{name}")

    folds_path = REPO_ROOT / VALIDATION_FOLDS_REPO_PATH
    if not folds_path.is_file():
        raise RuntimeError(f"VALIDATION_FOLDS_MISSING:{folds_path}")
    canonical = sha256_bytes(
        fren_final.base.frozen.REPO_ROOT.joinpath(VALIDATION_FOLDS_REPO_PATH).read_bytes()
        if False
        else subprocess_git_show(VALIDATION_FOLDS_REPO_PATH)
    )
    if canonical != EXPECTED_VALIDATION_FOLDS:
        raise RuntimeError(f"VALIDATION_FOLDS_CANONICAL_SHA_CHANGED:{canonical}")
    if sha256_file(folds_path) != EXPECTED_VALIDATION_FOLDS:
        raise RuntimeError("VALIDATION_FOLDS_WORKTREE_CHANGED")

    return {
        "admission_manifest": admission_path,
        "pit_manifest": pit_manifest_path,
        "pit_manifest_payload": pit_manifest,
        "ca_manifest": ca_manifest_path,
        "census_root": census_root,
        "folds_path": folds_path,
    }


def subprocess_git_show(relative: Path) -> bytes:
    import subprocess

    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"HEAD:{relative.as_posix()}"],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def verify_support_inputs(args: argparse.Namespace) -> dict[str, Path]:
    paths = {
        "calendar": args.artifact_root / "official_exchange_sessions_1260.csv",
        "panel": (
            args.artifact_root
            / "unknown_state_diagnostic_1260_20260809"
            / "model_safe_signal_research_panel_1260.parquet"
        ),
        "anchors": args.artifact_root / "tradability_anchors_1260.csv",
        "intervals": args.artifact_root / "tradability_intervals_1260.csv",
        "open_derivative_panel": (
            args.open_derivative_root
            / "execution_open_candidate_panel_yahoo_tradingview.parquet"
        ),
        "open_derivative_manifest": args.open_derivative_root / "artifact_manifest.json",
        "overlay_parquet": args.overlay_root / "open_recovery_overlay.parquet",
        "overlay_manifest": args.overlay_root / "manifest.json",
        "security_master": args.security_master,
    }
    for name, path in paths.items():
        if not path.is_file():
            raise RuntimeError(f"TRAINING_DOMAIN_INPUT_MISSING:{name}:{path}")
        actual = sha256_file(path)
        expected = pit.PINNED[name]
        if actual != expected:
            raise RuntimeError(
                f"TRAINING_DOMAIN_INPUT_SHA_MISMATCH:{name}:{actual}!={expected}"
            )
    return paths


def rebuild_decision_support(
    paths: dict[str, Path], validation_folds: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    calendar = pd.read_csv(paths["calendar"])
    calendar["date"] = (
        pd.to_datetime(calendar["date"], errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    if calendar["date"].isna().any() or calendar["date"].duplicated().any():
        raise RuntimeError("TRAINING_DOMAIN_CALENDAR_INVALID")
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)
    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))

    panel = pit.normalize_identity(pd.read_parquet(paths["panel"]))
    if panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("TRAINING_DOMAIN_PANEL_DUPLICATE_IDENTITY")
    panel["session_index"] = panel["date"].map(date_to_index)
    if panel["session_index"].isna().any():
        raise RuntimeError("TRAINING_DOMAIN_PANEL_DATE_OUTSIDE_CALENDAR")
    panel["session_index"] = panel["session_index"].astype(int)
    panel["close_valid"] = pd.to_numeric(panel["close"], errors="coerce").gt(0.0)

    derivative = pd.read_parquet(paths["open_derivative_panel"])
    overlay = pd.read_parquet(paths["overlay_parquet"])
    open_stats = pit.attach_open_support(panel, derivative, overlay)

    security_master = pd.read_csv(paths["security_master"])
    features, diagnostics = build_v4_control_feature_table(
        panel, calendar["date"], security_master
    )
    decision = features[
        features["universe_primary_liquid"].astype(bool)
    ][["ticker", "date", "session_index"]].copy()
    if decision.duplicated(["ticker", "date"]).any():
        raise RuntimeError("TRAINING_DOMAIN_PRIMARY_DUPLICATE_IDENTITY")

    anchors = pd.read_csv(paths["anchors"])
    anchors["market"] = anchors["market"].astype(str).str.upper()
    anchors["state"] = anchors["state"].astype(str).str.upper()
    intervals = pd.read_csv(paths["intervals"])
    intervals["market"] = intervals["market"].astype(str).str.upper()
    intervals["state"] = intervals["state"].astype(str).str.upper()
    states, state_conflicts = pit.state_map_from_inputs(anchors, intervals, calendar)

    support_lookup = {
        (ticker, int(index)): (bool(open_support), bool(close_valid))
        for ticker, index, open_support, close_valid in panel[
            ["ticker", "session_index", "open_support", "close_valid"]
        ].itertuples(index=False)
    }

    max_signal_index = int(validation_folds["session_index"].max())
    decision = decision[decision["session_index"].le(max_signal_index)].copy()

    entry_ok: list[bool] = []
    h5_ok: list[bool] = []
    h10_ok: list[bool] = []
    for ticker, index in decision[["ticker", "session_index"]].itertuples(index=False):
        index = int(index)
        entry_state = states.get((ticker, index + 1), "UNKNOWN")
        h5_state = states.get((ticker, index + 5), "UNKNOWN")
        h10_state = states.get((ticker, index + 10), "UNKNOWN")
        entry_open, _ = support_lookup.get((ticker, index + 1), (False, False))
        _, close5 = support_lookup.get((ticker, index + 5), (False, False))
        _, close10 = support_lookup.get((ticker, index + 10), (False, False))
        entry_ok.append(entry_state == "ACTIVE" and entry_open)
        h5_ok.append(h5_state == "ACTIVE" and close5)
        h10_ok.append(h10_state == "ACTIVE" and close10)
    decision["entry_open_support"] = entry_ok
    decision["h5_close_support"] = h5_ok
    decision["h10_close_support"] = h10_ok

    diagnostics_payload = {
        "pit_feature_diagnostics": diagnostics.__dict__,
        "open_lineage": open_stats,
        "state_conflict_keys": int(state_conflicts),
    }
    return calendar, decision, diagnostics_payload


def build_final_ca_continuity(
    *,
    args: argparse.Namespace,
    lineage: dict[str, Any],
    calendar: pd.DataFrame,
    windows: pd.DataFrame,
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
    coverage = pd.read_csv(census_root / "ticker_coverage.csv")
    coverage["ticker"] = (
        coverage["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    coverage["coverage_certified"] = (
        coverage["coverage_certified"]
        .astype(str)
        .str.casefold()
        .map({"true": True, "false": False})
    )
    if coverage["coverage_certified"].isna().any() or coverage["ticker"].duplicated().any():
        raise RuntimeError("TRAINING_DOMAIN_FINAL_CA_COVERAGE_INVALID")
    coverage_map = dict(zip(coverage["ticker"], coverage["coverage_certified"]))

    history = read_jsonl(census_root / "ksei_ca_history.jsonl")
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
    rights_event = synthetic_fren_rights_event_ksei(
        EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256
    )
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
        covered = bool(coverage_map.get(str(row.ticker), False))
        if str(row.ticker) not in coverage_map:
            missing_coverage_rows += 1
        result = window_continuity(
            coverage_certified=covered,
            cross_source_conflict=str(row.ticker) in cross_source_conflicts,
            events=events_by_ticker.get(str(row.ticker), []),
            entry_date=row.entry_date,
            terminal_date=row.terminal_date,
        )
        continuity_rows.append(
            {
                "ticker": str(row.ticker),
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
    diagnostics = {
        "period_start": pd.Timestamp(period_start).date().isoformat(),
        "period_end": pd.Timestamp(period_end).date().isoformat(),
        "decision_tickers": len(decision_tickers),
        "coverage_census_tickers": len(coverage_map),
        "coverage_missing_historical_tickers": len(missing_tickers),
        "coverage_missing_historical_ticker_list": missing_tickers,
        "coverage_missing_window_rows": int(missing_coverage_rows),
        "cross_source_conflict_tickers": sorted(cross_source_conflicts),
        "event_semantic_counts": dict(Counter(audit["semantic_class"].astype(str))),
    }
    return continuity, audit, diagnostics


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    if not args.prior_event_evidence.is_file():
        raise RuntimeError(f"PRIOR_EVENT_EVIDENCE_MISSING:{args.prior_event_evidence}")

    lineage = verify_pretarget_lineage(args)
    paths = verify_support_inputs(args)
    folds = pd.read_csv(lineage["folds_path"])
    folds["date"] = pd.to_datetime(folds["date"], errors="coerce").dt.normalize()
    if len(folds) != 600 or folds["date"].isna().any():
        raise RuntimeError("TRAINING_DOMAIN_FROZEN_FOLDS_INVALID")

    calendar, decision_support, support_diagnostics = rebuild_decision_support(
        paths, folds
    )
    max_signal = int(folds["session_index"].max())
    windows = build_window_skeleton(
        decision_support,
        calendar["date"],
        max_signal_session_index=max_signal,
    )
    continuity, event_audit, ca_diagnostics = build_final_ca_continuity(
        args=args,
        lineage=lineage,
        calendar=calendar,
        windows=windows,
    )
    continuity = attach_continuity(windows, continuity)
    combined_rows, per_date = combine_target_support(
        decision_support, continuity
    )
    training_dates = build_training_date_sets(per_date, folds)
    frozen_check = validate_frozen_tail(per_date, folds)

    fold_counts = (
        training_dates.groupby(["fold", "head"], sort=True)
        .size()
        .rename("training_dates")
        .reset_index()
    )
    expected_pairs = {(fold, head) for fold in range(1, 7) for head in ("H5", "H10")}
    observed_pairs = set(zip(fold_counts["fold"], fold_counts["head"]))
    all_training_sets_nonempty = observed_pairs == expected_pairs and bool(
        fold_counts["training_dates"].gt(0).all()
    )

    pass_gate = bool(
        frozen_check["all_frozen_600_full_target_eligible"]
        and frozen_check["tail_600_identity_unchanged"]
        and int(frozen_check["eligible_sessions_after_frozen_end"]) == 0
        and all_training_sets_nonempty
    )
    status = (
        "V4_3_CA_TRAINING_DOMAIN_PASS_READY_FOR_HISTORICAL_EXECUTION_PIN"
        if pass_gate
        else "V4_3_CA_TRAINING_DOMAIN_BLOCKED_REVIEW_REQUIRED"
    )

    args.output_dir.mkdir(parents=True)
    paths_out = {
        "continuity": args.output_dir / "v4_3_ca_training_domain_continuity.csv",
        "combined": args.output_dir / "v4_3_full_target_support_rows.csv",
        "per_date": args.output_dir / "v4_3_full_target_support_per_date.csv",
        "training_dates": args.output_dir / "v4_3_training_date_sets.csv",
        "event_audit": args.output_dir / "v4_3_ca_training_event_semantics.csv",
        "summary": args.output_dir / "summary.json",
        "manifest": args.output_dir / "MANIFEST.json",
    }
    continuity.to_csv(paths_out["continuity"], index=False, lineterminator="\n")
    combined_rows.to_csv(paths_out["combined"], index=False, lineterminator="\n")
    per_date.to_csv(paths_out["per_date"], index=False, lineterminator="\n")
    training_dates.to_csv(paths_out["training_dates"], index=False, lineterminator="\n")
    event_audit.to_csv(paths_out["event_audit"], index=False, lineterminator="\n")

    basic_manifest = lineage["pit_manifest_payload"]
    summary = {
        "schema_version": "ranking_v4_3_ca_training_domain_gate_v1",
        "status": status,
        "outcome_blind": True,
        "historical_target_loaded": False,
        "historical_target_rank_materialized": False,
        "historical_model_fit": False,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "protected_forward_accessed": False,
        "provider_calls": False,
        "network_calls": False,
        "scientific_config_changed": False,
        "price_inference": False,
        "record_date_inference": False,
        "excl_price_stitching": False,
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
        "parent_basic_support_status": basic_manifest.get("status"),
        "parent_admission_manifest_sha256": EXPECTED_ADMISSION_MANIFEST,
        "parent_pit_support_manifest_sha256": EXPECTED_PIT_SUPPORT_MANIFEST,
        "parent_final_ca_manifest_sha256": EXPECTED_FINAL_CA_MANIFEST,
        "next": (
            "PIN_TRAINING_DOMAIN_MANIFEST_IN_FINAL_HISTORICAL_EXECUTION_RUNNER"
            if pass_gate
            else "REVIEW_CA_TRAINING_DOMAIN_BLOCKERS_BEFORE_TARGET_ACCESS"
        ),
    }
    paths_out["summary"].write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output_hashes = {
        key: sha256_file(path)
        for key, path in paths_out.items()
        if key not in {"manifest"}
    }
    manifest = {
        "schema_version": "ranking_v4_3_ca_training_domain_manifest_v1",
        "status": status,
        "outcome_blind": True,
        "immutable_inputs": {
            "admission_manifest": EXPECTED_ADMISSION_MANIFEST,
            "pit_support_manifest": EXPECTED_PIT_SUPPORT_MANIFEST,
            "final_ca_manifest": EXPECTED_FINAL_CA_MANIFEST,
            "validation_folds": EXPECTED_VALIDATION_FOLDS,
            "canonical_calendar": pit.PINNED["calendar"],
            "canonical_signal_panel": pit.PINNED["panel"],
            "security_master": pit.PINNED["security_master"],
            "open_derivative_panel": pit.PINNED["open_derivative_panel"],
            "open_overlay": pit.PINNED["overlay_parquet"],
        },
        "output_hashes": output_hashes,
        "guardrails": {
            "historical_target_loaded": False,
            "historical_target_rank_materialized": False,
            "historical_model_fit": False,
            "historical_prediction_generated": False,
            "historical_performance_computed": False,
            "protected_forward_accessed": False,
            "provider_calls": False,
            "network_calls": False,
            "scientific_config_changed": False,
        },
    }
    paths_out["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "status": status,
                "manifest": str(paths_out["manifest"]),
                "manifest_sha256": sha256_file(paths_out["manifest"]),
                "full_eligible_sessions": summary["full_eligible_sessions"],
                "frozen_validation": frozen_check,
                "training_date_counts": summary["training_date_counts"],
                "coverage_missing_historical_tickers": ca_diagnostics[
                    "coverage_missing_historical_tickers"
                ],
                "cross_source_conflict_tickers": ca_diagnostics[
                    "cross_source_conflict_tickers"
                ],
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
