"""Offline semantic adjudication for the frozen V4-3 schedule-80 KSEI corpus.

This runner consumes only the immutable one-shot KSEI acquisition artifact. It
never contacts a provider. Candidate event-document identity comes exclusively
from the frozen acquisition mapping. Record/Distribution dates may link an
official document to a frozen event, but are never promoted to market transition
dates. Exact mechanical admission still requires an explicit Regular-Market
transition on an official IDX session. Voluntary cash/tender documents may be
classified NON_BLOCKING only under exact ticker + cash-date linkage.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
from typing import Any

from lxml import html
import pandas as pd
from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.ranking_v4_3_ca_schedule_reuse import event_inventory_identity  # noqa: E402
from idx_trade.v4_ca_residual_document_semantics import (  # noqa: E402
    ParsedResidualDocument,
    parse_residual_document,
    resolve_event_document_evidence,
)

DEFAULT_CONFIG = Path("config/v4_3_ca_training_domain_schedule_80_adjudication_v1.json")


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


def normalize_ticker(value: object) -> str:
    return str(value or "").strip().upper().replace(".JK", "")


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "v4_3_ca_training_domain_schedule_80_adjudication_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    hard = config.get("hard_boundaries") or {}
    for key in (
        "network_calls",
        "provider_calls",
        "source_substitution",
        "new_document_discovery",
        "fuzzy_event_matching",
        "price_inference",
        "record_or_distribution_date_as_transition",
        "pass_preserving_subset_selection",
        "target_or_rank_materialization",
        "historical_target_loaded",
        "model_fit",
        "prediction",
        "performance",
        "protected_forward_access",
    ):
        if hard.get(key) is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")


def verify_acquisition_root(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]], dict[str, str]]:
    expected = config["acquisition_parent"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    scope_path = root / "frozen_schedule_event_scope_80.csv"
    candidate_path = root / "event_candidate_documents.csv"
    parse_path = root / "document_parse_diagnostics.csv"
    request_path = root / "request_records.jsonl"
    query_path = root / "frozen_index_query_scope.csv"

    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(
            f"ACQUISITION_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = read_json(manifest_path, "ACQUISITION_MANIFEST")
    summary = read_json(summary_path, "ACQUISITION_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("ACQUISITION_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("ACQUISITION_NOT_OUTCOME_BLIND")
    if summary.get("semantic_admission_performed") is not False:
        raise RuntimeError("ACQUISITION_ALREADY_ADMITTED_SEMANTICS")

    scalar_keys = (
        "schedule_event_count",
        "index_query_count",
        "failed_index_queries",
        "index_parse_failures",
        "events_with_candidate_documents",
        "events_without_candidate_documents",
        "candidate_documents",
        "document_parse_exact_transition_diagnostics",
        "provider_failed_documents",
    )
    for key in scalar_keys:
        value = summary.get(key)
        if value is None or int(value) != int(expected[key]):
            raise RuntimeError(f"ACQUISITION_SCALAR_CHANGED:{key}:{value}!={expected[key]}")
    if summary.get("schedule_event_identity_sha256") != expected["schedule_event_identity_sha256"]:
        raise RuntimeError("ACQUISITION_EVENT_IDENTITY_CHANGED")
    if summary.get("successful_raw_response_identity_sha256") != expected["successful_raw_response_identity_sha256"]:
        raise RuntimeError("ACQUISITION_RAW_IDENTITY_CHANGED")

    for key in (
        "target_or_rank_materialized",
        "historical_target_loaded",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
        "scientific_config_changed",
        "source_substitution",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"ACQUISITION_GUARDRAIL_CHANGED:{key}")

    outputs = manifest.get("output_hashes") or {}
    paths = {
        "frozen_event_scope": scope_path,
        "frozen_index_query_scope": query_path,
        "event_candidate_documents": candidate_path,
        "document_parse_diagnostics": parse_path,
        "request_records": request_path,
        "summary": summary_path,
    }
    child_hashes: dict[str, str] = {}
    for key, path in paths.items():
        expected_sha = clean(outputs.get(key))
        actual_sha = sha256_file(path)
        if not expected_sha or actual_sha != expected_sha:
            raise RuntimeError(f"ACQUISITION_CHILD_SHA_MISMATCH:{key}:{actual_sha}!={expected_sha}")
        child_hashes[key] = actual_sha

    scope = pd.read_csv(scope_path, dtype=str, keep_default_na=False)
    candidates = pd.read_csv(candidate_path, dtype=str, keep_default_na=False)
    requests = read_jsonl(request_path)
    if len(scope) != int(expected["schedule_event_count"]):
        raise RuntimeError("ACQUISITION_SCOPE_COUNT_CHANGED")
    identity = event_inventory_identity(scope[["event_id", "ticker"]])
    if identity != expected["schedule_event_identity_sha256"]:
        raise RuntimeError(f"ACQUISITION_SCOPE_IDENTITY_CHANGED:{identity}")
    return scope, candidates, requests, {
        "manifest": actual_manifest,
        **child_hashes,
    }


def verify_calendar(artifact_root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    cfg = config["official_calendar"]
    path = artifact_root / str(cfg["filename"])
    actual = sha256_file(path)
    if actual != cfg["sha256"]:
        raise RuntimeError(f"OFFICIAL_CALENDAR_SHA_MISMATCH:{actual}!={cfg['sha256']}")
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError("OFFICIAL_CALENDAR_DATE_COLUMN_MISSING")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if frame["date"].duplicated().any():
        raise RuntimeError("OFFICIAL_CALENDAR_DUPLICATED_DATE")
    return frame, actual


def document_text(payload: bytes) -> tuple[str, str]:
    if payload.startswith(b"%PDF"):
        reader = PdfReader(BytesIO(payload))
        plain_parts: list[str] = []
        layout_parts: list[str] = []
        for page in reader.pages:
            plain_parts.append(page.extract_text() or "")
            try:
                layout_parts.append(page.extract_text(extraction_mode="layout") or "")
            except (TypeError, ValueError, NotImplementedError):
                layout_parts.append(page.extract_text() or "")
        return "\n".join(plain_parts), "\n".join(layout_parts)
    document = html.fromstring(payload)
    text = "\n".join(
        " ".join(str(value).split())
        for value in document.xpath("//body//text()")
        if " ".join(str(value).split())
    )
    return text, text


def successful_documents(root: Path, requests: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for row in requests:
        if clean(row.get("request_kind")) != "SCHEDULE_DOCUMENT":
            continue
        if int(row.get("status_code") or 0) != 200 or int(row.get("bytes") or 0) <= 0:
            continue
        raw_path = Path(str(row.get("path") or ""))
        if not raw_path.is_file():
            candidate = root / "raw" / "documents" / raw_path.name
            if candidate.is_file():
                raw_path = candidate
            else:
                raise RuntimeError(f"RAW_DOCUMENT_PATH_MISSING:{raw_path}")
        recorded_sha = clean(row.get("sha256"))
        actual_sha = sha256_file(raw_path)
        if not recorded_sha or recorded_sha != actual_sha:
            raise RuntimeError(f"RAW_DOCUMENT_SHA_MISMATCH:{raw_path}:{actual_sha}!={recorded_sha}")
        payload = raw_path.read_bytes()
        plain, layout = document_text(payload)
        urls = {
            clean(row.get("requested_url")),
            clean(row.get("final_url")),
        }
        urls.discard("")
        value = {
            "reference": clean(row.get("request_key")),
            "source_url": clean(row.get("final_url") or row.get("requested_url")),
            "source_sha256": actual_sha,
            "raw_path": str(raw_path),
            "plain_text": plain,
            "layout_text": layout,
        }
        for url in urls:
            existing = documents.get(url)
            if existing and existing["source_sha256"] != actual_sha:
                raise RuntimeError(f"DOCUMENT_URL_SHA_CONFLICT:{url}")
            documents[url] = value
    return documents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acquisition-root", type=Path, required=True)
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
    scope, candidate_links, request_rows, acquisition_hashes = verify_acquisition_root(
        args.acquisition_root, config
    )
    calendar, calendar_sha = verify_calendar(args.artifact_root, config)
    documents_by_url = successful_documents(args.acquisition_root, request_rows)

    # Candidate links themselves are immutable acquisition output. No new
    # document discovery or fuzzy matching is performed here.
    if not candidate_links.empty:
        candidate_links["ticker"] = candidate_links["ticker"].map(normalize_ticker)
        candidate_links["event_id"] = candidate_links["event_id"].map(clean)
        candidate_links["document_url"] = candidate_links["document_url"].map(clean)
    scope["ticker"] = scope["ticker"].map(normalize_ticker)
    scope["event_id"] = scope["event_id"].map(clean)

    event_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    missing_raw_candidate_links = 0
    for event in scope.to_dict("records"):
        event_id = clean(event["event_id"])
        ticker = normalize_ticker(event["ticker"])
        links = candidate_links[
            candidate_links["event_id"].eq(event_id) & candidate_links["ticker"].eq(ticker)
        ].copy()
        candidates: list[dict[str, Any]] = []
        for link in links.to_dict("records"):
            url = clean(link.get("document_url"))
            raw = documents_by_url.get(url)
            if raw is None:
                missing_raw_candidate_links += 1
                audit_rows.append(
                    {
                        "event_id": event_id,
                        "ticker": ticker,
                        "event_source_type": clean(event.get("source_type")),
                        "reference": clean(link.get("reference")),
                        "source_url": url,
                        "source_sha256": "",
                        "raw_available": False,
                        "document_class": "",
                        "event_family": "",
                        "record_date": "",
                        "distribution_date": "",
                        "transition_date": "",
                        "transition_semantic": "",
                        "diagnostics": "FROZEN_CANDIDATE_RAW_DOCUMENT_NOT_AVAILABLE",
                    }
                )
                continue
            parsed: ParsedResidualDocument = parse_residual_document(
                raw["plain_text"],
                expected_ticker=ticker,
                index_subject=clean(link.get("subject")),
                layout_text=raw["layout_text"],
            )
            candidate = {
                **raw,
                "reference": clean(link.get("reference") or raw["reference"]),
                "index_subject": clean(link.get("subject")),
                "parsed": parsed,
            }
            candidates.append(candidate)
            audit_rows.append(
                {
                    "event_id": event_id,
                    "ticker": ticker,
                    "event_source_type": clean(event.get("source_type")),
                    "reference": candidate["reference"],
                    "source_url": raw["source_url"],
                    "source_sha256": raw["source_sha256"],
                    "raw_available": True,
                    "document_class": parsed.document_class,
                    "event_family": parsed.event_family,
                    "payment_dates": "|".join(parsed.payment_dates),
                    "settlement_dates": "|".join(parsed.settlement_dates),
                    "cash_purchase_dates": "|".join(parsed.cash_purchase_dates),
                    "record_date": parsed.record_date or "",
                    "distribution_date": parsed.distribution_date or "",
                    "transition_date": parsed.transition_date or "",
                    "transition_semantic": parsed.transition_semantic or "",
                    "diagnostics": "|".join(parsed.diagnostics),
                }
            )

        evidence = resolve_event_document_evidence(
            event,
            candidates,
            official_sessions=calendar["date"].tolist(),
        )
        value = asdict(evidence)
        event_rows.append(
            {
                **{
                    key: field
                    for key, field in value.items()
                    if key not in {"ksei_references", "source_urls", "source_sha256s", "diagnostics"}
                },
                "ksei_reference": "|".join(evidence.ksei_references),
                "source_url": "|".join(evidence.source_urls),
                "source_sha256": "|".join(evidence.source_sha256s),
                "diagnostics": "|".join(evidence.diagnostics),
                "frozen_candidate_document_count": int(len(links)),
                "parsed_candidate_document_count": int(len(candidates)),
            }
        )

    evidence = pd.DataFrame(event_rows).sort_values(
        ["ticker", "event_source_type", "event_id"], kind="mergesort"
    ).reset_index(drop=True)
    if len(evidence) != 80 or evidence["event_id"].nunique() != 80:
        raise RuntimeError("ADJUDICATION_EVENT_IDENTITY_CHANGED")
    audit = pd.DataFrame(audit_rows)
    if not audit.empty:
        audit = audit.sort_values(
            ["ticker", "event_id", "source_url", "source_sha256"], kind="mergesort"
        ).reset_index(drop=True)

    exact_transition = int(evidence["linkage_status"].eq("EXACT").sum())
    exact_nonblocking = int(evidence["linkage_status"].eq("EXACT_NON_BLOCKING").sum())
    conflicts = int(evidence["linkage_status"].eq("CONFLICT").sum())
    unresolved = int(evidence["linkage_status"].eq("UNRESOLVED").sum())
    resolved = exact_transition + exact_nonblocking
    if resolved + conflicts + unresolved != 80:
        raise RuntimeError("ADJUDICATION_STATUS_PARTITION_INVALID")

    args.output_dir.mkdir(parents=True)
    evidence_path = args.output_dir / "schedule_80_event_document_evidence.csv"
    audit_path = args.output_dir / "schedule_80_document_adjudication_audit.csv"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"
    evidence.to_csv(evidence_path, index=False, lineterminator="\n")
    audit.to_csv(audit_path, index=False, lineterminator="\n")

    status = "V4_3_CA_SCHEDULE_80_OFFLINE_ADJUDICATION_COMPLETE"
    summary = {
        "schema_version": "v4_3_ca_training_domain_schedule_80_adjudication_result_v1",
        "status": status,
        "outcome_blind": True,
        "network_calls": False,
        "provider_calls": False,
        "source_substitution": False,
        "new_document_discovery": False,
        "price_inference": False,
        "record_or_distribution_date_as_transition": False,
        "pass_preserving_subset_selection": False,
        "target_or_rank_materialized": False,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "schedule_event_count": 80,
        "schedule_event_identity_sha256": config["acquisition_parent"]["schedule_event_identity_sha256"],
        "verified_successful_raw_documents": int(len({row["source_sha256"] for row in documents_by_url.values()})),
        "frozen_candidate_links": int(len(candidate_links)),
        "missing_raw_candidate_links": int(missing_raw_candidate_links),
        "exact_transition_events": exact_transition,
        "exact_nonblocking_events": exact_nonblocking,
        "resolved_events": resolved,
        "conflict_events": conflicts,
        "unresolved_events": unresolved,
        "linkage_status_counts": {
            str(key): int(value)
            for key, value in sorted(evidence["linkage_status"].value_counts().to_dict().items())
        },
        "parent_acquisition_manifest_sha256": acquisition_hashes["manifest"],
        "official_calendar_sha256": calendar_sha,
        "next": "FREEZE_ADJUDICATION_AND_REPLAY_FULL_TRAINING_DOMAIN_CONTINUITY",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_hashes = {
        "event_document_evidence": sha256_file(evidence_path),
        "document_adjudication_audit": sha256_file(audit_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_schedule_80_adjudication_manifest_v1",
        "status": status,
        "outcome_blind": True,
        "immutable_inputs": {
            **acquisition_hashes,
            "official_calendar": calendar_sha,
            "schedule_event_identity_sha256": config["acquisition_parent"]["schedule_event_identity_sha256"],
        },
        "output_hashes": output_hashes,
        "guardrails": {
            "network_calls": False,
            "provider_calls": False,
            "source_substitution": False,
            "new_document_discovery": False,
            "price_inference": False,
            "record_or_distribution_date_as_transition": False,
            "pass_preserving_subset_selection": False,
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
                "status": status,
                "schedule_event_count": 80,
                "verified_successful_raw_documents": summary["verified_successful_raw_documents"],
                "frozen_candidate_links": summary["frozen_candidate_links"],
                "missing_raw_candidate_links": summary["missing_raw_candidate_links"],
                "exact_transition_events": exact_transition,
                "exact_nonblocking_events": exact_nonblocking,
                "resolved_events": resolved,
                "conflict_events": conflicts,
                "unresolved_events": unresolved,
                "historical_target_loaded": False,
                "model_fit": False,
                "performance_computed": False,
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "next": summary["next"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
