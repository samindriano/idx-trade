"""One-shot official-KSEI acquisition for the seven gate-priority CA events.

NISP is tested through the strict registered-security static CA table for the
already accepted security-to-currency Voluntary Conversion semantic. The other
six selected events use only explicit official KSEI schedule documents and the
existing regular-market transition parser.

Raw provider bytes are append-only and external. Record/Distribution dates are
linkage fields only, never transition fallbacks.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

# Direct scripts in this repository use a src layout. Bootstrap only the local
# package root; this does not alter scientific semantics.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import pandas as pd

import run_v4_ca_schedule_acquisition as base
from idx_trade.v4_ca_event_windows import ACCEPTED_SCHEDULE_SEMANTICS
from idx_trade.v4_ca_schedule_semantics import clean, parse_ksei_schedule_transition
from idx_trade.v4_ca_targeted_schedule_evidence import (
    NISP_EVENT_ID,
    resolve_nisp_static_cash_evidence,
)
from idx_trade.v4_ksei_ca_history import parse_ksei_security_history


SELECTED_SHA256 = "f6650daf7256196f976b0a9d161dbf0cf896d0d349306be4fe4c76b1d2168529"
OFFICIAL_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_SELECTED = {
    "10e24d3621e0f5e65833655b2e11938fc53d64e68c03e6c87658eb74bb2ae26b": ("NISP", "Voluntary Conversion", "2024-09-06"),
    "1285d019c8831fae39ad2909e699680df9071d5ebc38701a71a5a5dba951c60d": ("ISAT", "Mandatory Conversion", "2024-10-11|2024-10-15|2024-10-16"),
    "41c1e8493213d0151799837330c0dc7d8fea633d458c03e40b61ea0247bb9e58": ("ADRO", "Right Distribution", "2024-11-29|2024-12-02"),
    "82e09144ecfe0d4375a9260156fe75dd74ed01a2cd72262f55e14cd85ce6ebc7": ("PANI", "Right Distribution", "2025-12-10|2025-12-11"),
    "072cf4b8b2f7f86f3c7a55a1128c85f338cbe7b41307b57a3240ad94dba0afae": ("RAJA", "Mandatory Conversion", "2026-07-15|2026-07-17|2026-07-20"),
    "9b21df59be9d68e088059e2dae04d2d0bd8832d9d1cb5e9dd5a300f05f369610": ("PTRO", "Mandatory Conversion", "2025-01-02|2025-01-06|2025-01-07"),
    "6df97832e47c00fc5653e90659f525a5c8258752f9fc2245803498bdeb30b45e": ("CUAN", "Mandatory Conversion", "2025-07-14|2025-07-16|2025-07-17"),
}
MECHANICAL_IDS = frozenset(set(EXPECTED_SELECTED) - {NISP_EVENT_ID})
KSEI_HOME = "https://web.ksei.co.id/"
KSEI_SECURITY_NISP = "https://web.ksei.co.id/services/registered-securities/shares/lc/NISP?setLocale=en-US"
MONTH_OFFSETS = (-2, -1, 0, 1, 2)
INTER_REQUEST_SLEEP = 0.15


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def validate_selected(path: Path) -> pd.DataFrame:
    if not path.is_file() or sha256(path) != SELECTED_SHA256:
        raise RuntimeError("SELECTED_SUBSET_SHA_MISMATCH_OR_MISSING")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {"event_id", "ticker", "source_type", "source_dates"}
    if required - set(frame.columns):
        raise RuntimeError("SELECTED_SUBSET_COLUMNS_MISSING")
    if len(frame) != 7 or frame["event_id"].nunique() != 7:
        raise RuntimeError("SELECTED_SUBSET_CARDINALITY_CHANGED")
    actual: dict[str, tuple[str, str, str]] = {}
    for row in frame.to_dict("records"):
        actual[clean(row["event_id"])] = (
            clean(row["ticker"]).upper(),
            clean(row["source_type"]),
            clean(row["source_dates"]),
        )
    if actual != EXPECTED_SELECTED:
        raise RuntimeError("SELECTED_SUBSET_IDENTITY_CHANGED")
    return frame


def validate_calendar(path: Path) -> tuple[pd.DataFrame, set[str]]:
    if not path.is_file() or sha256(path) != OFFICIAL_CALENDAR_SHA256:
        raise RuntimeError("OFFICIAL_CALENDAR_SHA_MISMATCH_OR_MISSING")
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError("OFFICIAL_CALENDAR_DATE_COLUMN_MISSING")
    dates = pd.to_datetime(frame["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    if dates.duplicated().any():
        raise RuntimeError("OFFICIAL_CALENDAR_DUPLICATE_DATE")
    return frame, {value.date().isoformat() for value in dates}


def add_month(year: int, month: int, offset: int) -> tuple[int, int]:
    ordinal = year * 12 + (month - 1) + offset
    return ordinal // 12, ordinal % 12 + 1


def query_months(source_dates_text: str) -> list[tuple[int, int]]:
    months: set[tuple[int, int]] = set()
    for token in source_dates_text.split("|"):
        value = pd.Timestamp(token)
        for offset in MONTH_OFFSETS:
            months.add(add_month(value.year, value.month, offset))
    return sorted(months)


def source_date_set(row: dict[str, str]) -> set[str]:
    return {token for token in clean(row.get("source_dates")).split("|") if token}


def exact_source_date_link(row: dict[str, str], parsed_row: dict[str, Any]) -> bool:
    identity = {
        clean(parsed_row.get("record_date")),
        clean(parsed_row.get("distribution_date")),
    } - {""}
    return bool(source_date_set(row) & identity)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-subset", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    if args.timeout_seconds <= 0:
        raise RuntimeError("INVALID_TIMEOUT")

    selected = validate_selected(args.selected_subset)
    _, official_sessions = validate_calendar(args.official_calendar)
    # Dependency/runtime preflight occurs before output-root creation.
    session = base.make_session()

    args.output_dir.mkdir(parents=True)
    raw_root = args.output_dir / "raw"
    raw_root.mkdir()
    request_records: list[dict[str, Any]] = []

    # Warm exact KSEI origin once. A failed warmup is recorded and fail-closed.
    home_payload, home_attempts = base.capture_request(
        session,
        url=KSEI_HOME,
        raw_path_prefix=raw_root / "home" / "ksei_home",
        timeout_seconds=args.timeout_seconds,
        request_kind="KSEI_HOME_WARMUP",
        request_key="KSEI_HOME",
    )
    request_records.extend(home_attempts)
    if home_payload is None:
        raise RuntimeError("KSEI_HOME_WARMUP_FAILED")

    evidence_rows: list[dict[str, Any]] = []
    linkage_rows: list[dict[str, Any]] = []

    # NISP: exact static security-to-currency evidence only.
    nisp_selected = selected.loc[selected["event_id"].eq(NISP_EVENT_ID)].iloc[0].to_dict()
    nisp_payload, nisp_attempts = base.capture_request(
        session,
        url=KSEI_SECURITY_NISP,
        raw_path_prefix=raw_root / "static" / "NISP",
        timeout_seconds=args.timeout_seconds,
        request_kind="REGISTERED_SECURITY_STATIC",
        request_key="NISP",
    )
    request_records.extend(nisp_attempts)
    if nisp_payload is None:
        nisp_evidence = {
            "event_id": NISP_EVENT_ID,
            "ticker": "NISP",
            "event_source_type": "Voluntary Conversion",
            "linkage_status": "UNRESOLVED_PROVIDER",
            "evidence_kind": "VOLUNTARY_CASH_STATIC_SECURITY_TO_CURRENCY",
            "transition_semantic": "",
            "transition_date": "",
            "ksei_reference": "STATIC_REGISTERED_SECURITY_PAGE",
            "document_date": "",
            "source_url": "",
            "source_sha256": "",
            "linkage_basis": "NISP_STATIC_PROVIDER_FAILED",
            "ratio_raw": "",
            "ratio_left_security": "",
            "ratio_right_security": "",
            "identity_date": "2024-09-06",
            "diagnostics": "PROVIDER_FAILED",
        }
    else:
        successful = next(
            (record for record in reversed(nisp_attempts) if int(record.get("status_code") or 0) == 200 and record.get("sha256")),
            None,
        )
        if successful is None:
            raise RuntimeError("NISP_SUCCESS_CAPTURE_RECORD_MISSING")
        try:
            parsed = parse_ksei_security_history(
                nisp_payload,
                expected_ticker="NISP",
                source_url=clean(successful.get("final_url") or KSEI_SECURITY_NISP),
                source_sha256=clean(successful.get("sha256")),
            )
            nisp_evidence = resolve_nisp_static_cash_evidence(nisp_selected, parsed.rows)
        except Exception as exc:
            nisp_evidence = {
                "event_id": NISP_EVENT_ID,
                "ticker": "NISP",
                "event_source_type": "Voluntary Conversion",
                "linkage_status": "UNRESOLVED_PARSE",
                "evidence_kind": "VOLUNTARY_CASH_STATIC_SECURITY_TO_CURRENCY",
                "transition_semantic": "",
                "transition_date": "",
                "ksei_reference": "STATIC_REGISTERED_SECURITY_PAGE",
                "document_date": "",
                "source_url": clean(successful.get("final_url") or KSEI_SECURITY_NISP),
                "source_sha256": clean(successful.get("sha256")),
                "linkage_basis": "NISP_STATIC_PARSE_OR_LINKAGE_FAILED",
                "ratio_raw": "",
                "ratio_left_security": "",
                "ratio_right_security": "",
                "identity_date": "2024-09-06",
                "diagnostics": f"{type(exc).__name__}:{exc}",
            }
    if nisp_evidence["linkage_status"].startswith("EXACT_"):
        evidence_rows.append(nisp_evidence)
    linkage_rows.append(
        {
            "event_id": NISP_EVENT_ID,
            "ticker": "NISP",
            "source_type": "Voluntary Conversion",
            "source_dates": "2024-09-06",
            "candidate_document_count": 1 if nisp_payload is not None else 0,
            "transition_dates": "",
            "linkage_status": nisp_evidence["linkage_status"],
            "evidence_kind": nisp_evidence["evidence_kind"],
            "diagnostics": nisp_evidence.get("diagnostics", ""),
        }
    )

    # Six mechanical events: index discovery and explicit schedule transitions.
    mechanical = selected[selected["event_id"].isin(MECHANICAL_IDS)].copy()
    index_cache: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    event_candidate_urls: dict[str, set[str]] = {event_id: set() for event_id in MECHANICAL_IDS}
    document_meta: dict[str, dict[str, Any]] = {}

    for event in mechanical.to_dict("records"):
        event_id = clean(event["event_id"])
        ticker = clean(event["ticker"]).upper()
        for slug in base.source_slugs(clean(event["source_type"])):
            for year, month in query_months(clean(event["source_dates"])):
                key = (slug, year, month)
                if key not in index_cache:
                    url = base.INDEX_TEMPLATE.format(slug=slug, month=month, year=year)
                    prefix = raw_root / "index" / f"{slug}_{year}{month:02d}"
                    payload, attempts = base.capture_request(
                        session,
                        url=url,
                        raw_path_prefix=prefix,
                        timeout_seconds=args.timeout_seconds,
                        request_kind="SCHEDULE_INDEX",
                        request_key=f"{slug}:{year}-{month:02d}",
                    )
                    request_records.extend(attempts)
                    if payload is None:
                        index_cache[key] = []
                    else:
                        try:
                            index_cache[key] = base.parse_index(
                                payload,
                                requested_month=month,
                                requested_year=year,
                            )
                        except Exception as exc:
                            index_cache[key] = []
                            request_records.append(
                                {
                                    "request_kind": "SCHEDULE_INDEX_PARSE",
                                    "request_key": f"{slug}:{year}-{month:02d}",
                                    "attempt": 0,
                                    "requested_url": url,
                                    "accessed_at_utc": utc_now(),
                                    "status_code": 200,
                                    "bytes": len(payload),
                                    "sha256": hashlib.sha256(payload).hexdigest(),
                                    "path": str(prefix),
                                    "error": f"{type(exc).__name__}:{exc}",
                                }
                            )
                    time.sleep(INTER_REQUEST_SLEEP)
                for item in index_cache[key]:
                    doc_url = clean(item.get("document_url"))
                    if not doc_url or not base.ticker_in_subject(ticker, clean(item.get("subject"))):
                        continue
                    event_candidate_urls[event_id].add(doc_url)
                    document_meta[doc_url] = {**item, "slug": slug}

    parsed_documents: dict[str, dict[str, Any]] = {}
    for index, url in enumerate(sorted(document_meta), start=1):
        meta = document_meta[url]
        reference_safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", clean(meta.get("reference")) or f"doc_{index}")
        payload, attempts = base.capture_request(
            session,
            url=url,
            raw_path_prefix=raw_root / "documents" / reference_safe,
            timeout_seconds=args.timeout_seconds,
            request_kind="SCHEDULE_DOCUMENT",
            request_key=clean(meta.get("reference")) or url,
        )
        request_records.extend(attempts)
        if payload is None:
            parsed_documents[url] = {
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
            continue
        digest = hashlib.sha256(payload).hexdigest()
        try:
            text = base.document_text(payload)
            parsed = parse_ksei_schedule_transition(text)
            parsed_documents[url] = {
                **meta,
                **asdict(parsed),
                "diagnostics": "|".join(parsed.diagnostics),
                "source_url": url,
                "source_sha256": digest,
            }
        except Exception as exc:
            parsed_documents[url] = {
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
        time.sleep(INTER_REQUEST_SLEEP)

    for event in mechanical.to_dict("records"):
        event_id = clean(event["event_id"])
        ticker = clean(event["ticker"]).upper()
        candidates: list[dict[str, Any]] = []
        for url in sorted(event_candidate_urls[event_id]):
            row = parsed_documents[url]
            if clean(row.get("parse_status")) != "PARSED_EXACT_TRANSITION":
                continue
            if clean(row.get("ticker")).upper() != ticker:
                continue
            if not base.compatible_family(clean(event["source_type"]), clean(row.get("event_family"))):
                continue
            if not exact_source_date_link(event, row):
                continue
            transition = clean(row.get("transition_date"))
            semantic = clean(row.get("transition_semantic"))
            if transition not in official_sessions or semantic not in ACCEPTED_SCHEDULE_SEMANTICS:
                continue
            if not clean(row.get("source_sha256")) or not clean(row.get("ksei_reference") or row.get("reference")):
                continue
            candidates.append(row)

        transitions = {clean(row.get("transition_date")) for row in candidates if clean(row.get("transition_date"))}
        semantics = {clean(row.get("transition_semantic")) for row in candidates if clean(row.get("transition_semantic"))}
        if len(transitions) == 1 and len(semantics) == 1:
            transition = next(iter(transitions))
            semantic = next(iter(semantics))
            exact_rows = [row for row in candidates if clean(row.get("transition_date")) == transition and clean(row.get("transition_semantic")) == semantic]
            for row in exact_rows:
                evidence_rows.append(
                    {
                        "event_id": event_id,
                        "ticker": ticker,
                        "event_source_type": clean(event["source_type"]),
                        "linkage_status": "EXACT",
                        "evidence_kind": "EXACT_TRANSITION",
                        "transition_semantic": semantic,
                        "transition_date": transition,
                        "ksei_reference": clean(row.get("ksei_reference") or row.get("reference")),
                        "document_date": clean(row.get("document_date")),
                        "source_url": clean(row.get("source_url")),
                        "source_sha256": clean(row.get("source_sha256")),
                        "linkage_basis": "EXACT_TICKER_FAMILY_SOURCE_DATE_AND_EXPLICIT_REGULAR_MARKET_TRANSITION",
                        "ratio_raw": "",
                        "ratio_left_security": "",
                        "ratio_right_security": "",
                        "identity_date": "",
                        "diagnostics": clean(row.get("diagnostics")),
                    }
                )
            status = "EXACT"
        elif len(transitions) > 1 or len(semantics) > 1:
            status = "CONFLICTING_EXACT_TRANSITIONS"
        else:
            status = "NO_EXACT_LINKED_TRANSITION"
        linkage_rows.append(
            {
                "event_id": event_id,
                "ticker": ticker,
                "source_type": clean(event["source_type"]),
                "source_dates": clean(event["source_dates"]),
                "candidate_document_count": len(event_candidate_urls[event_id]),
                "transition_dates": "|".join(sorted(transitions)),
                "linkage_status": status,
                "evidence_kind": "EXACT_TRANSITION",
                "diagnostics": "",
            }
        )

    evidence = pd.DataFrame(evidence_rows)
    evidence_columns = [
        "event_id", "ticker", "event_source_type", "linkage_status", "evidence_kind",
        "transition_semantic", "transition_date", "ksei_reference", "document_date",
        "source_url", "source_sha256", "linkage_basis", "ratio_raw",
        "ratio_left_security", "ratio_right_security", "identity_date", "diagnostics",
    ]
    if evidence.empty:
        evidence = pd.DataFrame(columns=evidence_columns)
    else:
        evidence = evidence[evidence_columns].drop_duplicates().sort_values(
            ["ticker", "event_id", "transition_date", "ksei_reference"], kind="mergesort"
        ).reset_index(drop=True)
    linkage = pd.DataFrame(linkage_rows).sort_values(["ticker", "event_id"], kind="mergesort").reset_index(drop=True)
    parse_frame = pd.DataFrame(list(parsed_documents.values()))

    evidence_path = args.output_dir / "targeted_evidence.csv"
    linkage_path = args.output_dir / "targeted_event_linkage_audit.csv"
    parse_path = args.output_dir / "targeted_schedule_document_parse_audit.csv"
    requests_path = args.output_dir / "request_records.jsonl"
    evidence.to_csv(evidence_path, index=False, lineterminator="\n")
    linkage.to_csv(linkage_path, index=False, lineterminator="\n")
    parse_frame.to_csv(parse_path, index=False, lineterminator="\n")
    write_jsonl(requests_path, request_records)

    exact_static = int(linkage["linkage_status"].eq("EXACT_NON_BLOCKING_STATIC_SECURITY_TO_CURRENCY").sum())
    exact_schedule = int(linkage["linkage_status"].eq("EXACT").sum())
    unresolved = 7 - exact_static - exact_schedule
    summary = {
        "schema_version": "v4_ca_targeted_schedule_evidence_v1",
        "status": "V4_CA_TARGETED_SEVEN_EVENT_EVIDENCE_COMPLETE",
        "outcome_blind": True,
        "provider_calls": True,
        "source_substitution": False,
        "selected_event_count": 7,
        "mechanical_schedule_target_count": 6,
        "nisp_static_target_count": 1,
        "exact_static_nonblocking_events": exact_static,
        "exact_schedule_transition_events": exact_schedule,
        "unresolved_selected_events": unresolved,
        "resolved_event_ids": sorted(set(evidence["event_id"])) if len(evidence) else [],
        "unresolved_event_ids": sorted(set(EXPECTED_SELECTED) - set(evidence["event_id"])) if len(evidence) else sorted(EXPECTED_SELECTED),
        "index_pages_requested": len(index_cache),
        "candidate_documents": len(document_meta),
        "provider_request_attempt_records": len(request_records),
        "policy": {
            "selected_subset_sha256": SELECTED_SHA256,
            "official_calendar_sha256": OFFICIAL_CALENDAR_SHA256,
            "month_offsets": list(MONTH_OFFSETS),
            "record_distribution_linkage_only": True,
            "record_distribution_transition_fallback": False,
            "price_inference": False,
            "source_substitution": False,
            "nisp_static_rule_scope": "EXACT_SELECTED_NISP_EVENT_ONLY",
        },
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "input_hashes": {
            "selected_subset": sha256(args.selected_subset),
            "official_calendar": sha256(args.official_calendar),
        },
        "output_hashes": {},
    }
    summary_path = args.output_dir / "summary.json"
    summary["output_hashes"] = {
        "targeted_evidence": sha256(evidence_path),
        "targeted_event_linkage_audit": sha256(linkage_path),
        "targeted_schedule_document_parse_audit": sha256(parse_path),
        "request_records": sha256(requests_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ca_targeted_schedule_evidence_manifest_v1",
        "status": summary["status"],
        "outcome_blind": True,
        "provider_calls": True,
        "input_hashes": summary["input_hashes"],
        "summary_sha256": sha256(summary_path),
        "output_hashes": summary["output_hashes"],
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "manifest_sha256": sha256(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
