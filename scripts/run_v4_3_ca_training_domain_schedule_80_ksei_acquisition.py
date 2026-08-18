"""Acquire official KSEI documents for the frozen 80 V4-3 schedule events.

This is an outcome-blind provider stage.  Event identity comes only from the
accepted schedule-80 reuse result; query months come only from exact source_dates
in the immutable blocked training-domain replay event audit.  The run captures
raw KSEI index/document bytes and fixed parser diagnostics, but intentionally
performs no event admission.  Semantic adjudication is a later offline step.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
for value in (SRC_ROOT, SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import run_v4_ca_schedule_acquisition as base  # noqa: E402
from idx_trade.ranking_v4_3_ca_schedule_reuse import (  # noqa: E402
    event_inventory_identity,
)
from idx_trade.v4_ca_schedule_semantics import clean, parse_ksei_schedule_transition  # noqa: E402


DEFAULT_CONFIG = Path("config/v4_3_ca_training_domain_schedule_80_ksei_v1.json")


@dataclass(frozen=True)
class ScopedEvent:
    event_id: str
    ticker: str
    source_type: str
    family: str
    semantic_class: str
    source_dates: tuple[pd.Timestamp, ...]


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


def normalize_ticker(value: Any) -> str:
    return str(value or "").strip().upper().replace(".JK", "")


def parse_source_dates(value: Any, *, event_id: str) -> tuple[pd.Timestamp, ...]:
    raw = [part.strip() for part in str(value or "").split("|") if part.strip()]
    if not raw:
        raise RuntimeError(f"SCHEDULE_EVENT_SOURCE_DATES_MISSING:{event_id}")
    parsed: list[pd.Timestamp] = []
    for item in raw:
        stamp = pd.to_datetime(item, errors="coerce")
        if pd.isna(stamp):
            raise RuntimeError(f"SCHEDULE_EVENT_SOURCE_DATE_INVALID:{event_id}:{item}")
        parsed.append(pd.Timestamp(stamp).tz_localize(None).normalize())
    unique = tuple(sorted(set(parsed)))
    if not unique:
        raise RuntimeError(f"SCHEDULE_EVENT_SOURCE_DATES_MISSING:{event_id}")
    return unique


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-root", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "v4_3_ca_training_domain_schedule_80_ksei_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    provider = config.get("provider") or {}
    if provider.get("name") != "KSEI_PUBLIC_CORPORATE_ACTION_SCHEDULES":
        raise RuntimeError("PROVIDER_CHANGED")
    if provider.get("source_substitution") is not False:
        raise RuntimeError("SOURCE_SUBSTITUTION_ENABLED")
    if tuple(provider.get("month_offsets") or []) != tuple(base.MONTH_OFFSETS):
        raise RuntimeError("MONTH_OFFSETS_CHANGED")
    if int(provider.get("max_attempts") or -1) != int(base.MAX_ATTEMPTS):
        raise RuntimeError("MAX_ATTEMPTS_CHANGED")
    if tuple(float(x) for x in provider.get("backoff_seconds") or []) != tuple(
        float(x) for x in base.BACKOFF_SECONDS
    ):
        raise RuntimeError("BACKOFF_CHANGED")
    if float(provider.get("inter_request_sleep_seconds") or -1) != float(base.INTER_REQUEST_SLEEP):
        raise RuntimeError("INTER_REQUEST_SLEEP_CHANGED")
    hard = config.get("hard_boundaries") or {}
    for key in (
        "pass_preserving_subset_selection",
        "price_inference",
        "record_or_distribution_date_as_transition",
        "source_date_inference",
        "source_substitution",
        "parser_or_semantic_relaxation_after_provider_result",
        "target_or_rank_materialization",
        "historical_target_loaded",
        "model_fit",
        "prediction",
        "performance",
        "protected_forward_access",
    ):
        if hard.get(key) is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")


def verify_reuse_root(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    expected = config["reuse_parent"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    residual_path = root / "schedule_80_residual_events_for_acquisition.csv"
    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(
            f"REUSE_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = read_json(manifest_path, "REUSE_MANIFEST")
    summary = read_json(summary_path, "REUSE_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("REUSE_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("REUSE_NOT_OUTCOME_BLIND")
    if int(summary.get("schedule_event_count") or -1) != int(expected["event_count"]):
        raise RuntimeError("REUSE_EVENT_COUNT_CHANGED")
    if int(summary.get("residual_events_for_acquisition") or -1) != int(expected["event_count"]):
        raise RuntimeError("REUSE_RESIDUAL_COUNT_CHANGED")
    if int(summary.get("resolved_existing_evidence_events") or -1) != int(
        expected["resolved_existing_evidence_events"]
    ):
        raise RuntimeError("REUSE_RESOLVED_COUNT_CHANGED")
    if summary.get("schedule_event_identity_sha256") != expected["event_identity_sha256"]:
        raise RuntimeError("REUSE_EVENT_IDENTITY_CHANGED")
    if summary.get("residual_event_identity_sha256") != expected["event_identity_sha256"]:
        raise RuntimeError("REUSE_RESIDUAL_IDENTITY_CHANGED")
    for key in (
        "historical_target_loaded",
        "model_fit",
        "performance_computed",
        "protected_forward_accessed",
        "target_or_rank_materialized",
    ):
        if key in summary and summary.get(key) is not False:
            raise RuntimeError(f"REUSE_GUARDRAIL_CHANGED:{key}")
    outputs = manifest.get("output_hashes") or {}
    expected_residual_hash = str(outputs.get("residual_events") or "")
    actual_residual_hash = sha256_file(residual_path)
    if not expected_residual_hash or actual_residual_hash != expected_residual_hash:
        raise RuntimeError("REUSE_RESIDUAL_CHILD_SHA_MISMATCH")
    residual = pd.read_csv(residual_path, keep_default_na=False)
    if len(residual) != int(expected["event_count"]):
        raise RuntimeError("REUSE_RESIDUAL_FILE_COUNT_CHANGED")
    identity = event_inventory_identity(residual[["event_id", "ticker"]])
    if identity != expected["event_identity_sha256"]:
        raise RuntimeError(f"REUSE_RESIDUAL_FILE_IDENTITY_CHANGED:{identity}")
    return residual, {
        "reuse_manifest": actual_manifest,
        "reuse_summary": sha256_file(summary_path),
        "reuse_residual_events": actual_residual_hash,
    }


def verify_replay_root(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    expected = config["replay_parent"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    event_audit_path = root / str(expected["event_audit_filename"])
    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(
            f"REPLAY_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = read_json(manifest_path, "REPLAY_MANIFEST")
    summary = read_json(summary_path, "REPLAY_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("REPLAY_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("REPLAY_NOT_OUTCOME_BLIND")
    for key in (
        "historical_target_loaded",
        "historical_target_rank_materialized",
        "historical_model_fit",
        "historical_prediction_generated",
        "historical_performance_computed",
        "protected_forward_accessed",
        "provider_calls",
        "network_calls",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"REPLAY_GUARDRAIL_CHANGED:{key}")
    outputs = manifest.get("output_hashes") or {}
    expected_audit_hash = str(outputs.get("event_audit") or "")
    actual_audit_hash = sha256_file(event_audit_path)
    if not expected_audit_hash or actual_audit_hash != expected_audit_hash:
        raise RuntimeError("REPLAY_EVENT_AUDIT_CHILD_SHA_MISMATCH")
    audit = pd.read_csv(event_audit_path, keep_default_na=False)
    return audit, {
        "replay_manifest": actual_manifest,
        "replay_summary": sha256_file(summary_path),
        "replay_event_audit": actual_audit_hash,
    }


def build_scope(residual: pd.DataFrame, audit: pd.DataFrame, config: dict[str, Any]) -> list[ScopedEvent]:
    required_residual = {"event_id", "ticker", "source_type", "family"}
    missing = required_residual - set(residual.columns)
    if missing:
        raise RuntimeError(f"REUSE_RESIDUAL_COLUMNS_MISSING:{sorted(missing)}")
    required_audit = {
        "event_id", "ticker", "source_type", "family", "semantic_class", "source_dates"
    }
    missing = required_audit - set(audit.columns)
    if missing:
        raise RuntimeError(f"REPLAY_EVENT_AUDIT_COLUMNS_MISSING:{sorted(missing)}")

    audit = audit.copy()
    audit["event_id"] = audit["event_id"].astype(str).str.strip()
    audit["ticker"] = audit["ticker"].map(normalize_ticker)
    scope: list[ScopedEvent] = []
    for row in residual.itertuples(index=False):
        event_id = str(row.event_id).strip()
        ticker = normalize_ticker(row.ticker)
        matches = audit[audit["event_id"].eq(event_id) & audit["ticker"].eq(ticker)].copy()
        canonical_cols = ["event_id", "ticker", "source_type", "family", "semantic_class", "source_dates"]
        matches = matches[canonical_cols].drop_duplicates()
        if len(matches) != 1:
            raise RuntimeError(f"REPLAY_EVENT_METADATA_CARDINALITY:{event_id}:{ticker}:{len(matches)}")
        meta = matches.iloc[0]
        if clean(meta["semantic_class"]) != "SCHEDULE_REQUIRED":
            raise RuntimeError(f"REPLAY_EVENT_NOT_SCHEDULE_REQUIRED:{event_id}:{ticker}")
        residual_source_type = clean(getattr(row, "source_type", ""))
        residual_family = clean(getattr(row, "family", ""))
        if residual_source_type and residual_source_type != clean(meta["source_type"]):
            raise RuntimeError(f"REPLAY_EVENT_SOURCE_TYPE_CHANGED:{event_id}:{ticker}")
        if residual_family and residual_family != clean(meta["family"]):
            raise RuntimeError(f"REPLAY_EVENT_FAMILY_CHANGED:{event_id}:{ticker}")
        source_dates = parse_source_dates(meta["source_dates"], event_id=event_id)
        scope.append(
            ScopedEvent(
                event_id=event_id,
                ticker=ticker,
                source_type=clean(meta["source_type"]),
                family=clean(meta["family"]),
                semantic_class="SCHEDULE_REQUIRED",
                source_dates=source_dates,
            )
        )
    if len(scope) != int(config["reuse_parent"]["event_count"]):
        raise RuntimeError("SCHEDULE_SCOPE_COUNT_CHANGED")
    identity_frame = pd.DataFrame(
        {"event_id": [event.event_id for event in scope], "ticker": [event.ticker for event in scope]}
    )
    identity = event_inventory_identity(identity_frame)
    expected_identity = str(config["reuse_parent"]["event_identity_sha256"])
    if identity != expected_identity:
        raise RuntimeError(f"SCHEDULE_SCOPE_IDENTITY_CHANGED:{identity}!={expected_identity}")
    return sorted(scope, key=lambda event: (event.ticker, event.event_id))


def event_months(event: ScopedEvent) -> list[tuple[int, int]]:
    values: set[tuple[int, int]] = set()
    for stamp in event.source_dates:
        for offset in base.MONTH_OFFSETS:
            values.add(base.add_month(int(stamp.year), int(stamp.month), int(offset)))
    return sorted(values)


def raw_inventory_identity(records: list[dict[str, Any]]) -> str:
    rows = sorted(
        {
            f"{clean(row.get('request_kind'))}|{clean(row.get('request_key'))}|"
            f"{clean(row.get('requested_url'))}|{clean(row.get('sha256'))}|{clean(row.get('path'))}"
            for row in records
            if int(row.get("status_code") or 0) == 200 and clean(row.get("sha256"))
        }
    )
    return hashlib.sha256(("\n".join(rows) + ("\n" if rows else "")).encode("utf-8")).hexdigest()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    config = read_json(args.config, "CONFIG")
    verify_config(config)
    residual, reuse_hashes = verify_reuse_root(args.reuse_root, config)
    audit, replay_hashes = verify_replay_root(args.replay_root, config)
    scope = build_scope(residual, audit, config)

    # Complete pre-provider scope before output creation or any network call.
    query_to_events: dict[tuple[str, int, int], set[tuple[str, str]]] = {}
    for event in scope:
        for slug in base.source_slugs(event.source_type):
            for year, month in event_months(event):
                query_to_events.setdefault((slug, year, month), set()).add((event.event_id, event.ticker))
    if not query_to_events:
        raise RuntimeError("SCHEDULE_INDEX_QUERY_SCOPE_EMPTY")

    args.output_dir.mkdir(parents=True)
    raw_root = args.output_dir / "raw"
    raw_root.mkdir(parents=True)
    scope_path = args.output_dir / "frozen_schedule_event_scope_80.csv"
    query_path = args.output_dir / "frozen_index_query_scope.csv"
    candidate_path = args.output_dir / "event_candidate_documents.csv"
    parse_path = args.output_dir / "document_parse_diagnostics.csv"
    request_path = args.output_dir / "request_records.jsonl"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"

    scope_frame = pd.DataFrame(
        [
            {
                "event_id": event.event_id,
                "ticker": event.ticker,
                "source_type": event.source_type,
                "family": event.family,
                "semantic_class": event.semantic_class,
                "source_dates": "|".join(stamp.date().isoformat() for stamp in event.source_dates),
            }
            for event in scope
        ]
    )
    scope_frame.to_csv(scope_path, index=False, lineterminator="\n")
    query_frame = pd.DataFrame(
        [
            {
                "slug": slug,
                "year": year,
                "month": month,
                "event_count": len(events),
                "event_keys": "|".join(f"{event_id}:{ticker}" for event_id, ticker in sorted(events)),
            }
            for (slug, year, month), events in sorted(query_to_events.items())
        ]
    )
    query_frame.to_csv(query_path, index=False, lineterminator="\n")

    timeout_seconds = float(config["provider"]["timeout_seconds"])
    session = base.make_session()
    request_records: list[dict[str, Any]] = []
    index_rows: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    index_parse_failures = 0

    for slug, year, month in sorted(query_to_events):
        url = base.INDEX_TEMPLATE.format(slug=slug, month=month, year=year)
        prefix = raw_root / "index" / f"{slug}_{year}{month:02d}"
        payload, attempts = base.capture_request(
            session,
            url=url,
            raw_path_prefix=prefix,
            timeout_seconds=timeout_seconds,
            request_kind="SCHEDULE_INDEX",
            request_key=f"{slug}:{year}-{month:02d}",
        )
        request_records.extend(attempts)
        if payload is None:
            index_rows[(slug, year, month)] = []
        else:
            try:
                index_rows[(slug, year, month)] = base.parse_index(
                    payload, requested_month=month, requested_year=year
                )
            except Exception as exc:
                index_parse_failures += 1
                index_rows[(slug, year, month)] = []
                request_records.append(
                    {
                        "request_kind": "SCHEDULE_INDEX_PARSE",
                        "request_key": f"{slug}:{year}-{month:02d}",
                        "attempt": 0,
                        "requested_url": url,
                        "accessed_at_utc": base.utc_now(),
                        "status_code": 200,
                        "bytes": len(payload),
                        "sha256": base.sha256_bytes(payload),
                        "path": "",
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )
        time.sleep(base.INTER_REQUEST_SLEEP)

    event_by_key = {(event.event_id, event.ticker): event for event in scope}
    candidate_links: list[dict[str, Any]] = []
    unique_documents: dict[str, dict[str, Any]] = {}
    for query, event_keys in sorted(query_to_events.items()):
        slug, year, month = query
        for item in index_rows.get(query, []):
            url = clean(item.get("document_url"))
            if not url:
                continue
            subject = clean(item.get("subject"))
            for event_key in sorted(event_keys):
                event = event_by_key[event_key]
                if not base.ticker_in_subject(event.ticker, subject):
                    continue
                candidate_links.append(
                    {
                        "event_id": event.event_id,
                        "ticker": event.ticker,
                        "source_type": event.source_type,
                        "family": event.family,
                        "source_dates": "|".join(stamp.date().isoformat() for stamp in event.source_dates),
                        "query_slug": slug,
                        "query_year": year,
                        "query_month": month,
                        "reference": clean(item.get("reference")),
                        "subject": subject,
                        "document_date": clean(item.get("document_date")),
                        "document_url": url,
                    }
                )
                unique_documents[url] = {
                    "reference": clean(item.get("reference")),
                    "subject": subject,
                    "document_date": clean(item.get("document_date")),
                }

    candidate_frame = pd.DataFrame(candidate_links)
    if candidate_frame.empty:
        candidate_frame = pd.DataFrame(
            columns=[
                "event_id", "ticker", "source_type", "family", "source_dates",
                "query_slug", "query_year", "query_month", "reference", "subject",
                "document_date", "document_url"
            ]
        )
    else:
        candidate_frame = candidate_frame.drop_duplicates().sort_values(
            ["ticker", "event_id", "document_url"], kind="mergesort"
        ).reset_index(drop=True)
    candidate_frame.to_csv(candidate_path, index=False, lineterminator="\n")

    parse_rows: list[dict[str, Any]] = []
    for index, (url, meta) in enumerate(sorted(unique_documents.items()), start=1):
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", meta["reference"] or f"doc_{index}")
        prefix = raw_root / "documents" / safe
        payload, attempts = base.capture_request(
            session,
            url=url,
            raw_path_prefix=prefix,
            timeout_seconds=timeout_seconds,
            request_kind="SCHEDULE_DOCUMENT",
            request_key=meta["reference"] or url,
        )
        request_records.extend(attempts)
        if payload is None:
            parse_rows.append(
                {
                    **meta,
                    "source_url": url,
                    "source_sha256": "",
                    "parse_status": "UNRESOLVED_PROVIDER",
                    "ticker": "",
                    "event_family": "UNKNOWN",
                    "record_date": "",
                    "distribution_date": "",
                    "transition_date": "",
                    "transition_semantic": "",
                    "diagnostics": "PROVIDER_FAILED",
                }
            )
            continue
        digest = base.sha256_bytes(payload)
        try:
            text = base.document_text(payload)
            parsed = parse_ksei_schedule_transition(text)
            parse_rows.append(
                {
                    **meta,
                    **asdict(parsed),
                    "diagnostics": "|".join(parsed.diagnostics),
                    "source_url": url,
                    "source_sha256": digest,
                }
            )
        except Exception as exc:
            parse_rows.append(
                {
                    **meta,
                    "source_url": url,
                    "source_sha256": digest,
                    "parse_status": "UNRESOLVED_PARSE",
                    "ticker": "",
                    "event_family": "UNKNOWN",
                    "record_date": "",
                    "distribution_date": "",
                    "transition_date": "",
                    "transition_semantic": "",
                    "diagnostics": f"{type(exc).__name__}:{exc}",
                }
            )
        time.sleep(base.INTER_REQUEST_SLEEP)

    parse_frame = pd.DataFrame(parse_rows)
    if parse_frame.empty:
        parse_frame = pd.DataFrame(
            columns=[
                "reference", "subject", "document_date", "source_url", "source_sha256",
                "parse_status", "ticker", "event_family", "record_date",
                "distribution_date", "transition_date", "transition_semantic", "diagnostics"
            ]
        )
    parse_frame.to_csv(parse_path, index=False, lineterminator="\n")
    base.write_jsonl(request_path, request_records)

    events_with_candidates = int(candidate_frame["event_id"].nunique()) if len(candidate_frame) else 0
    exact_parse_docs = int(parse_frame["parse_status"].eq("PARSED_EXACT_TRANSITION").sum()) if len(parse_frame) else 0
    provider_failed_docs = int(parse_frame["parse_status"].eq("UNRESOLVED_PROVIDER").sum()) if len(parse_frame) else 0
    failed_index_queries = sum(
        1
        for slug, year, month in query_to_events
        if not any(
            row.get("request_kind") == "SCHEDULE_INDEX"
            and row.get("request_key") == f"{slug}:{year}-{month:02d}"
            and int(row.get("status_code") or 0) == 200
            and int(row.get("bytes") or 0) > 0
            for row in request_records
        )
    )
    raw_identity = raw_inventory_identity(request_records)
    summary = {
        "schema_version": "v4_3_ca_training_domain_schedule_80_ksei_result_v1",
        "status": "V4_3_CA_SCHEDULE_80_KSEI_ACQUISITION_COMPLETE",
        "outcome_blind": True,
        "provider_calls": True,
        "network_calls": True,
        "source_substitution": False,
        "semantic_admission_performed": False,
        "parse_diagnostics_are_non_admissive": True,
        "target_or_rank_materialized": False,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "scientific_config_changed": False,
        "schedule_event_count": len(scope),
        "schedule_event_identity_sha256": config["reuse_parent"]["event_identity_sha256"],
        "index_query_count": len(query_to_events),
        "failed_index_queries": int(failed_index_queries),
        "index_parse_failures": int(index_parse_failures),
        "event_candidate_links": int(len(candidate_frame)),
        "events_with_candidate_documents": events_with_candidates,
        "events_without_candidate_documents": int(len(scope) - events_with_candidates),
        "candidate_documents": int(len(unique_documents)),
        "document_parse_exact_transition_diagnostics": exact_parse_docs,
        "provider_failed_documents": provider_failed_docs,
        "successful_raw_response_identity_sha256": raw_identity,
        "next": "FREEZE_RAW_CORPUS_AND_RUN_OFFLINE_SEMANTIC_ADJUDICATION",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_hashes = {
        "frozen_event_scope": sha256_file(scope_path),
        "frozen_index_query_scope": sha256_file(query_path),
        "event_candidate_documents": sha256_file(candidate_path),
        "document_parse_diagnostics": sha256_file(parse_path),
        "request_records": sha256_file(request_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_schedule_80_ksei_manifest_v1",
        "status": summary["status"],
        "outcome_blind": True,
        "immutable_inputs": {
            **reuse_hashes,
            **replay_hashes,
            "schedule_event_identity_sha256": config["reuse_parent"]["event_identity_sha256"],
        },
        "output_hashes": output_hashes,
        "successful_raw_response_identity_sha256": raw_identity,
        "guardrails": {
            "provider_calls": True,
            "network_calls": True,
            "source_substitution": False,
            "semantic_admission_performed": False,
            "pass_preserving_subset_selection": False,
            "price_inference": False,
            "record_or_distribution_date_as_transition": False,
            "source_date_inference": False,
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
                "schedule_event_count": len(scope),
                "schedule_event_identity_sha256": summary["schedule_event_identity_sha256"],
                "index_query_count": summary["index_query_count"],
                "failed_index_queries": summary["failed_index_queries"],
                "index_parse_failures": summary["index_parse_failures"],
                "events_with_candidate_documents": summary["events_with_candidate_documents"],
                "events_without_candidate_documents": summary["events_without_candidate_documents"],
                "candidate_documents": summary["candidate_documents"],
                "document_parse_exact_transition_diagnostics": summary[
                    "document_parse_exact_transition_diagnostics"
                ],
                "provider_failed_documents": summary["provider_failed_documents"],
                "semantic_admission_performed": False,
                "historical_target_loaded": False,
                "model_fit": False,
                "performance_computed": False,
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "successful_raw_response_identity_sha256": raw_identity,
                "next": summary["next"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
