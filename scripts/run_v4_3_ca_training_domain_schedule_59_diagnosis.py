"""Outcome-blind failure-mode census for the residual 59 V4-3 CA schedule events.

This runner performs no provider call and no new document discovery.  It reads
only the immutable schedule-80 adjudication and its blocked full-domain replay,
then mirrors the already-frozen adjudication contract to explain why each of the
59 remaining SCHEDULE_REQUIRED events failed closed.

The census is descriptive only.  It must not select a minimum subset required
to cross the 90% gate; every residual event remains in scope for any subsequent
acquisition/remediation lane.
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
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.ranking_v4_3_ca_schedule_reuse import event_inventory_identity  # noqa: E402
from idx_trade.v4_ca_event_windows import ACCEPTED_SCHEDULE_SEMANTICS  # noqa: E402
from idx_trade.v4_ca_residual_document_semantics import (  # noqa: E402
    CASH_DOCUMENT_CLASSES,
    compatible_family,
)


DEFAULT_CONFIG = Path("config/v4_3_ca_training_domain_schedule_59_diagnosis_v1.json")


REMEDIATION_CLASS = {
    "NO_FROZEN_CANDIDATE_DOCUMENT": "SECONDARY_OFFICIAL_DOCUMENT_DISCOVERY",
    "CANDIDATE_TICKER_NOT_EVIDENCED": "SECONDARY_OFFICIAL_DOCUMENT_DISCOVERY",
    "VOLUNTARY_NO_RECOGNIZED_CASH_DOCUMENT": "SECONDARY_OFFICIAL_CASH_DOCUMENT_DISCOVERY",
    "VOLUNTARY_NO_LAYOUT_BOUND_CASH_DATE": "SECONDARY_OFFICIAL_CASH_SCHEDULE_DISCOVERY",
    "VOLUNTARY_CASH_DATE_NOT_LINKED_TO_SOURCE_DATE": "SECONDARY_OFFICIAL_EVENT_LINKAGE_DISCOVERY",
    "MECHANICAL_NO_COMPATIBLE_FAMILY_DOCUMENT": "SECONDARY_OFFICIAL_FAMILY_SPECIFIC_SCHEDULE_DISCOVERY",
    "MECHANICAL_SOURCE_DATE_NOT_LINKED_TO_LAYOUT_BOUND_RECORD_DISTRIBUTION": "SECONDARY_OFFICIAL_EVENT_LINKAGE_DISCOVERY",
    "MECHANICAL_NO_EXPLICIT_REGULAR_MARKET_TRANSITION": "SECONDARY_OFFICIAL_EX_OR_NEW_BASIS_SCHEDULE_DISCOVERY",
    "MECHANICAL_TRANSITION_NOT_OFFICIAL_SESSION": "OFFICIAL_SESSION_SEMANTIC_REVIEW_FAIL_CLOSED",
    "OTHER_UNRESOLVED_FAIL_CLOSED": "MANUAL_OFFICIAL_EVIDENCE_REVIEW_FAIL_CLOSED",
}


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def ticker(value: object) -> str:
    return clean(value).upper().replace(".JK", "")


def parse_pipe(value: object) -> tuple[str, ...]:
    return tuple(sorted({clean(token) for token in str(value or "").split("|") if clean(token)}))


def date_set(value: object) -> set[str]:
    result: set[str] = set()
    for token in parse_pipe(value):
        parsed = pd.to_datetime(token, errors="coerce")
        if pd.isna(parsed):
            continue
        result.add(pd.Timestamp(parsed).normalize().date().isoformat())
    return result


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    normalized = clean(value).casefold()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0", ""}:
        return False
    raise RuntimeError(f"BOOLEAN_VALUE_INVALID:{value}")


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "v4_3_ca_training_domain_schedule_59_diagnosis_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    hard = config.get("hard_boundaries") or {}
    for key in (
        "network_calls",
        "provider_calls",
        "source_substitution",
        "new_document_discovery",
        "parser_relaxation",
        "fuzzy_event_matching",
        "price_inference",
        "record_or_distribution_date_as_transition",
        "pass_preserving_subset_selection",
        "threshold_change",
        "target_or_rank_materialization",
        "historical_target_loaded",
        "model_fit",
        "prediction",
        "performance",
        "protected_forward_access",
    ):
        if hard.get(key) is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")


def verify_manifest_child(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if not expected or actual != expected:
        raise RuntimeError(f"{label}_SHA_MISMATCH:{actual}!={expected}")
    return actual


def verify_replay(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], dict[str, str]]:
    expected = config["parent_replay"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    event_path = root / "v4_3_ca_training_event_semantics_schedule80.csv"

    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(
            f"REPLAY_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = read_json(manifest_path, "REPLAY_MANIFEST")
    summary = read_json(summary_path, "REPLAY_SUMMARY")
    if manifest.get("status") != expected["required_status"] or summary.get("status") != expected["required_status"]:
        raise RuntimeError("REPLAY_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("REPLAY_NOT_OUTCOME_BLIND")
    for key in (
        "provider_calls",
        "network_calls",
        "target_or_rank_materialized",
        "historical_target_loaded",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
        "scientific_config_changed",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"REPLAY_GUARDRAIL_CHANGED:{key}")
    counts = summary.get("replayed_event_semantic_counts") or {}
    if int(counts.get("SCHEDULE_REQUIRED") or -1) != int(expected["required_schedule_required_events"]):
        raise RuntimeError("REPLAY_RESIDUAL_EVENT_COUNT_CHANGED")
    if int(summary.get("coverage_unresolved_decision_tickers") or -1) != int(
        expected["required_coverage_unresolved_decision_tickers"]
    ):
        raise RuntimeError("REPLAY_COVERAGE_UNRESOLVED_COUNT_CHANGED")

    outputs = manifest.get("output_hashes") or {}
    event_sha = verify_manifest_child(event_path, clean(outputs.get("event_audit")), "REPLAY_EVENT_AUDIT")
    summary_sha = verify_manifest_child(summary_path, clean(outputs.get("summary")), "REPLAY_SUMMARY")
    frame = pd.read_csv(event_path, dtype=str, keep_default_na=False)
    frame["ticker"] = frame["ticker"].map(ticker)
    frame["event_id"] = frame["event_id"].map(clean)
    return frame, summary, {
        "manifest": actual_manifest,
        "event_audit": event_sha,
        "summary": summary_sha,
    }


def verify_adjudication(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, str]]:
    expected = config["adjudication_parent"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    evidence_path = root / "schedule_80_event_document_evidence.csv"
    audit_path = root / "schedule_80_document_adjudication_audit.csv"

    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(
            f"ADJUDICATION_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = read_json(manifest_path, "ADJUDICATION_MANIFEST")
    summary = read_json(summary_path, "ADJUDICATION_SUMMARY")
    if manifest.get("status") != expected["required_status"] or summary.get("status") != expected["required_status"]:
        raise RuntimeError("ADJUDICATION_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("ADJUDICATION_NOT_OUTCOME_BLIND")
    for key in (
        "schedule_event_count",
        "resolved_events",
        "exact_transition_events",
        "exact_nonblocking_events",
        "conflict_events",
        "unresolved_events",
    ):
        if int(summary.get(key, -1)) != int(expected[key]):
            raise RuntimeError(f"ADJUDICATION_COUNT_CHANGED:{key}")
    for key in (
        "provider_calls",
        "network_calls",
        "target_or_rank_materialized",
        "historical_target_loaded",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
    ):
        if key in summary and summary.get(key) is not False:
            raise RuntimeError(f"ADJUDICATION_GUARDRAIL_CHANGED:{key}")

    outputs = manifest.get("output_hashes") or {}
    evidence_sha = verify_manifest_child(
        evidence_path, clean(outputs.get("event_document_evidence")), "ADJUDICATION_EVIDENCE"
    )
    audit_sha = verify_manifest_child(
        audit_path, clean(outputs.get("document_adjudication_audit")), "ADJUDICATION_AUDIT"
    )
    summary_sha = verify_manifest_child(summary_path, clean(outputs.get("summary")), "ADJUDICATION_SUMMARY")
    evidence = pd.read_csv(evidence_path, dtype=str, keep_default_na=False)
    audit = pd.read_csv(audit_path, dtype=str, keep_default_na=False)
    for frame in (evidence, audit):
        if len(frame):
            frame["ticker"] = frame["ticker"].map(ticker)
            frame["event_id"] = frame["event_id"].map(clean)
    return evidence, audit, summary, {
        "manifest": actual_manifest,
        "evidence": evidence_sha,
        "audit": audit_sha,
        "summary": summary_sha,
    }


def verify_calendar(artifact_root: Path, config: dict[str, Any]) -> tuple[set[str], str]:
    cfg = config["official_calendar"]
    path = artifact_root / cfg["filename"]
    actual = sha256_file(path)
    if actual != cfg["sha256"]:
        raise RuntimeError(f"OFFICIAL_CALENDAR_SHA_MISMATCH:{actual}!={cfg['sha256']}")
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError("OFFICIAL_CALENDAR_DATE_COLUMN_MISSING")
    dates = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if dates.duplicated().any():
        raise RuntimeError("OFFICIAL_CALENDAR_DUPLICATED_DATE")
    return {value.date().isoformat() for value in dates}, actual


def ticker_evidenced(row: pd.Series) -> bool:
    return "EXPECTED_TICKER_NOT_EVIDENCED" not in set(parse_pipe(row.get("diagnostics", "")))


def row_cash_dates(row: pd.Series) -> set[str]:
    result: set[str] = set()
    for column in ("payment_dates", "settlement_dates", "cash_purchase_dates"):
        result |= date_set(row.get(column, ""))
    return result


def row_mechanical_dates(row: pd.Series) -> set[str]:
    result: set[str] = set()
    for column in ("record_date", "distribution_date"):
        result |= date_set(row.get(column, ""))
    return result


def diagnose_event(event: pd.Series, evidence: pd.Series, audit: pd.DataFrame, official_sessions: set[str]) -> dict[str, Any]:
    event_id = clean(event["event_id"])
    event_ticker = ticker(event["ticker"])
    source_type = clean(event.get("source_type", ""))
    source_dates = date_set(event.get("source_dates", ""))
    event_audit = audit[audit["event_id"].eq(event_id) & audit["ticker"].eq(event_ticker)].copy()

    frozen_candidates = int(evidence.get("frozen_candidate_document_count") or 0)
    parsed_candidates = int(evidence.get("parsed_candidate_document_count") or 0)
    if frozen_candidates == 0:
        reason = "NO_FROZEN_CANDIDATE_DOCUMENT"
        qualifying_rows = 0
    else:
        if event_audit.empty:
            raise RuntimeError(f"RESIDUAL_EVENT_AUDIT_MISSING:{event_id}:{event_ticker}")
        available = event_audit[
            event_audit["raw_available"].map(bool_value)
        ].copy()
        evidenced = available[available.apply(ticker_evidenced, axis=1)].copy()
        if evidenced.empty:
            reason = "CANDIDATE_TICKER_NOT_EVIDENCED"
            qualifying_rows = 0
        elif source_type.casefold() == "voluntary conversion":
            cash = evidenced[evidenced["document_class"].isin(CASH_DOCUMENT_CLASSES)].copy()
            if cash.empty:
                reason = "VOLUNTARY_NO_RECOGNIZED_CASH_DOCUMENT"
                qualifying_rows = 0
            else:
                with_cash_date = cash[cash.apply(lambda row: bool(row_cash_dates(row)), axis=1)].copy()
                if with_cash_date.empty:
                    reason = "VOLUNTARY_NO_LAYOUT_BOUND_CASH_DATE"
                    qualifying_rows = 0
                else:
                    linked = with_cash_date[
                        with_cash_date.apply(lambda row: bool(source_dates & row_cash_dates(row)), axis=1)
                    ].copy()
                    if linked.empty:
                        reason = "VOLUNTARY_CASH_DATE_NOT_LINKED_TO_SOURCE_DATE"
                        qualifying_rows = 0
                    else:
                        reason = "OTHER_UNRESOLVED_FAIL_CLOSED"
                        qualifying_rows = int(len(linked))
        else:
            compatible = evidenced[
                evidenced.apply(
                    lambda row: compatible_family(source_type, clean(row.get("event_family", ""))),
                    axis=1,
                )
            ].copy()
            if compatible.empty:
                reason = "MECHANICAL_NO_COMPATIBLE_FAMILY_DOCUMENT"
                qualifying_rows = 0
            else:
                linked = compatible[
                    compatible.apply(
                        lambda row: bool(source_dates & row_mechanical_dates(row)), axis=1
                    )
                ].copy()
                if linked.empty:
                    reason = "MECHANICAL_SOURCE_DATE_NOT_LINKED_TO_LAYOUT_BOUND_RECORD_DISTRIBUTION"
                    qualifying_rows = 0
                else:
                    transition = linked[
                        linked["transition_semantic"].isin(ACCEPTED_SCHEDULE_SEMANTICS)
                        & linked["transition_date"].astype(str).str.strip().ne("")
                    ].copy()
                    if transition.empty:
                        reason = "MECHANICAL_NO_EXPLICIT_REGULAR_MARKET_TRANSITION"
                        qualifying_rows = 0
                    else:
                        official = transition[
                            transition["transition_date"].map(
                                lambda value: next(iter(date_set(value)), "") in official_sessions
                            )
                        ].copy()
                        if official.empty:
                            reason = "MECHANICAL_TRANSITION_NOT_OFFICIAL_SESSION"
                            qualifying_rows = 0
                        else:
                            reason = "OTHER_UNRESOLVED_FAIL_CLOSED"
                            qualifying_rows = int(len(official))

    diagnostics: Counter[str] = Counter()
    if not event_audit.empty:
        for raw in event_audit.get("diagnostics", pd.Series(dtype=str)).astype(str):
            diagnostics.update(parse_pipe(raw))
    return {
        "event_id": event_id,
        "ticker": event_ticker,
        "source_type": source_type,
        "family": clean(event.get("family", "")),
        "source_dates": "|".join(sorted(source_dates)),
        "failure_mode": reason,
        "remediation_class": REMEDIATION_CLASS[reason],
        "frozen_candidate_document_count": frozen_candidates,
        "parsed_candidate_document_count": parsed_candidates,
        "audit_candidate_rows": int(len(event_audit)),
        "qualifying_rows_after_diagnosis": int(qualifying_rows),
        "diagnostic_tokens": "|".join(sorted(diagnostics)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule-replay-root", type=Path, required=True)
    parser.add_argument("--adjudication-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    config = read_json(args.config, "CONFIG")
    verify_config(config)
    replay_audit, replay_summary, replay_hashes = verify_replay(args.schedule_replay_root, config)
    evidence, adjudication_audit, adjudication_summary, adjudication_hashes = verify_adjudication(
        args.adjudication_root, config
    )
    official_sessions, calendar_sha = verify_calendar(args.artifact_root, config)

    residual = replay_audit[replay_audit["semantic_class"].eq("SCHEDULE_REQUIRED")].copy()
    if len(residual) != 59 or residual["event_id"].nunique() != 59:
        raise RuntimeError(f"RESIDUAL_59_IDENTITY_CHANGED:{len(residual)}:{residual['event_id'].nunique()}")
    unresolved_evidence = evidence[evidence["linkage_status"].eq("UNRESOLVED")].copy()
    if len(unresolved_evidence) != 59 or unresolved_evidence["event_id"].nunique() != 59:
        raise RuntimeError("ADJUDICATION_UNRESOLVED_59_IDENTITY_CHANGED")

    residual_keys = set(zip(residual["event_id"], residual["ticker"]))
    evidence_keys = set(zip(unresolved_evidence["event_id"], unresolved_evidence["ticker"]))
    if residual_keys != evidence_keys:
        raise RuntimeError("REPLAY_ADJUDICATION_RESIDUAL_IDENTITY_MISMATCH")
    residual_identity_sha = event_inventory_identity(residual[["event_id", "ticker"]])

    evidence_by_key = {
        (row.event_id, row.ticker): pd.Series(row._asdict())
        for row in unresolved_evidence.itertuples(index=False)
    }
    rows: list[dict[str, Any]] = []
    for event in residual.sort_values(["ticker", "event_id"], kind="mergesort").itertuples(index=False):
        event_series = pd.Series(event._asdict())
        key = (clean(event.event_id), ticker(event.ticker))
        rows.append(
            diagnose_event(
                event_series,
                evidence_by_key[key],
                adjudication_audit,
                official_sessions,
            )
        )
    census = pd.DataFrame(rows).sort_values(["failure_mode", "ticker", "event_id"], kind="mergesort")
    if len(census) != 59 or census["event_id"].nunique() != 59:
        raise RuntimeError("DIAGNOSIS_OUTPUT_IDENTITY_CHANGED")

    failure_counts = (
        census.groupby(["failure_mode", "remediation_class"], sort=True)
        .size()
        .rename("events")
        .reset_index()
    )
    source_counts = (
        census.groupby(["source_type", "failure_mode"], sort=True)
        .size()
        .rename("events")
        .reset_index()
    )
    token_counter: Counter[str] = Counter()
    for raw in census["diagnostic_tokens"].astype(str):
        token_counter.update(parse_pipe(raw))
    token_counts = pd.DataFrame(
        [{"diagnostic_token": key, "events_or_rows": int(value)} for key, value in sorted(token_counter.items())]
    )
    if token_counts.empty:
        token_counts = pd.DataFrame(columns=["diagnostic_token", "events_or_rows"])

    args.output_dir.mkdir(parents=True)
    census_path = args.output_dir / "residual_59_failure_mode_census.csv"
    failure_path = args.output_dir / "residual_59_failure_mode_counts.csv"
    source_path = args.output_dir / "residual_59_source_type_failure_counts.csv"
    token_path = args.output_dir / "residual_59_diagnostic_token_counts.csv"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"
    census.to_csv(census_path, index=False, lineterminator="\n")
    failure_counts.to_csv(failure_path, index=False, lineterminator="\n")
    source_counts.to_csv(source_path, index=False, lineterminator="\n")
    token_counts.to_csv(token_path, index=False, lineterminator="\n")

    summary = {
        "schema_version": "v4_3_ca_training_domain_schedule_59_diagnosis_result_v1",
        "status": "V4_3_CA_SCHEDULE_59_FAILURE_MODE_CENSUS_COMPLETE",
        "outcome_blind": True,
        "network_calls": False,
        "provider_calls": False,
        "new_document_discovery": False,
        "parser_relaxation": False,
        "pass_preserving_subset_selection": False,
        "target_or_rank_materialized": False,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "residual_events": 59,
        "residual_event_identity_sha256": residual_identity_sha,
        "failure_mode_counts": {
            row.failure_mode: int(row.events)
            for row in failure_counts.itertuples(index=False)
        },
        "remediation_class_counts": {
            key: int(value)
            for key, value in sorted(Counter(census["remediation_class"].astype(str)).items())
        },
        "events_without_frozen_candidate_document": int(
            census["failure_mode"].eq("NO_FROZEN_CANDIDATE_DOCUMENT").sum()
        ),
        "events_with_frozen_candidate_but_unresolved": int(
            census["frozen_candidate_document_count"].gt(0).sum()
        ),
        "parent_schedule_replay_manifest_sha256": replay_hashes["manifest"],
        "parent_adjudication_manifest_sha256": adjudication_hashes["manifest"],
        "official_calendar_sha256": calendar_sha,
        "next": "FREEZE_ALL_59_AND_PREREGISTER_SECONDARY_OFFICIAL_DISCOVERY_BY_DIAGNOSIS_CLASS",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_hashes = {
        "failure_mode_census": sha256_file(census_path),
        "failure_mode_counts": sha256_file(failure_path),
        "source_type_failure_counts": sha256_file(source_path),
        "diagnostic_token_counts": sha256_file(token_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_schedule_59_diagnosis_manifest_v1",
        "status": summary["status"],
        "outcome_blind": True,
        "immutable_inputs": {
            "schedule_replay_manifest": replay_hashes["manifest"],
            "adjudication_manifest": adjudication_hashes["manifest"],
            "official_calendar": calendar_sha,
            "residual_event_identity_sha256": residual_identity_sha,
        },
        "input_child_hashes": {
            "schedule_replay": replay_hashes,
            "adjudication": adjudication_hashes,
        },
        "output_hashes": output_hashes,
        "guardrails": {
            "network_calls": False,
            "provider_calls": False,
            "source_substitution": False,
            "new_document_discovery": False,
            "parser_relaxation": False,
            "fuzzy_event_matching": False,
            "price_inference": False,
            "record_or_distribution_date_as_transition": False,
            "pass_preserving_subset_selection": False,
            "threshold_change": False,
            "target_or_rank_materialized": False,
            "historical_target_loaded": False,
            "model_fit": False,
            "prediction_generated": False,
            "performance_computed": False,
            "protected_forward_accessed": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": summary["status"],
                "residual_events": 59,
                "residual_event_identity_sha256": residual_identity_sha,
                "failure_mode_counts": summary["failure_mode_counts"],
                "remediation_class_counts": summary["remediation_class_counts"],
                "events_without_frozen_candidate_document": summary[
                    "events_without_frozen_candidate_document"
                ],
                "events_with_frozen_candidate_but_unresolved": summary[
                    "events_with_frozen_candidate_but_unresolved"
                ],
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "historical_target_loaded": False,
                "model_fit": False,
                "performance_computed": False,
                "next": summary["next"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
