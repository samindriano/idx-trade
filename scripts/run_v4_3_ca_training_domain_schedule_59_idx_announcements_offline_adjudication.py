"""Offline semantic adjudication for frozen IDX announcement attachments.

The runner is deliberately provider-free. It verifies the exact acquisition
manifest supplied on the CLI, replays only the frozen event-to-attachment links,
and applies the already frozen hardened residual-document semantics. No new
document discovery, parser relaxation, target access, model fit, prediction, or
performance evaluation occurs here.
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
    resolve_event_document_evidence,
)
from idx_trade.v4_ca_residual_document_semantics_hardened import (  # noqa: E402
    parse_residual_document_hardened,
)

DEFAULT_CONFIG = Path("config/v4_3_ca_training_domain_schedule_59_idx_adjudication_v1.json")


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def normalize_ticker(value: object) -> str:
    return clean(value).upper().replace(".JK", "")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acquisition-root", type=Path, required=True)
    parser.add_argument("--expected-acquisition-manifest-sha", required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "v4_3_ca_training_domain_schedule_59_idx_adjudication_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    if config.get("acquisition_manifest_sha_required_via_cli") is not True:
        raise RuntimeError("ACQUISITION_SHA_BINDING_DISABLED")
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
        "parser_or_semantic_relaxation_after_observed_corpus",
        "target_or_rank_materialization",
        "historical_target_loaded",
        "model_fit",
        "prediction",
        "performance",
        "protected_forward_access",
    ):
        if hard.get(key) is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")


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


def verify_acquisition_root(
    root: Path,
    expected_manifest_sha: str,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]], dict[str, str]]:
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    scope_path = root / "frozen_residual_59_scope.csv"
    links_path = root / "event_idx_attachment_candidate_links.csv"
    attachment_inventory_path = root / "idx_attachment_inventory.csv"
    request_path = root / "request_records.jsonl"

    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != clean(expected_manifest_sha):
        raise RuntimeError(
            f"ACQUISITION_MANIFEST_SHA_MISMATCH:{actual_manifest}!={clean(expected_manifest_sha)}"
        )
    manifest = read_json(manifest_path, "ACQUISITION_MANIFEST")
    summary = read_json(summary_path, "ACQUISITION_SUMMARY")
    if manifest.get("status") != config["acquisition_status"]:
        raise RuntimeError("ACQUISITION_MANIFEST_STATUS_CHANGED")
    if summary.get("status") != config["acquisition_status"]:
        raise RuntimeError("ACQUISITION_SUMMARY_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("ACQUISITION_NOT_OUTCOME_BLIND")
    if int(summary.get("residual_events") or -1) != int(config["residual_events"]):
        raise RuntimeError("ACQUISITION_EVENT_COUNT_CHANGED")
    if summary.get("residual_event_identity_sha256") != config["residual_event_identity_sha256"]:
        raise RuntimeError("ACQUISITION_EVENT_IDENTITY_CHANGED")
    for key in (
        "semantic_admission_performed",
        "source_substitution",
        "external_search_engine",
        "pass_preserving_subset_selection",
        "target_or_rank_materialized",
        "historical_target_loaded",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
        "scientific_config_changed",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"ACQUISITION_GUARDRAIL_CHANGED:{key}")

    outputs = manifest.get("output_hashes") or {}
    paths = {
        "frozen_residual_scope": scope_path,
        "event_attachment_candidate_links": links_path,
        "attachment_inventory": attachment_inventory_path,
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
    links = pd.read_csv(links_path, dtype=str, keep_default_na=False)
    requests = read_jsonl(request_path)
    if len(scope) != int(config["residual_events"]):
        raise RuntimeError("ACQUISITION_SCOPE_COUNT_CHANGED")
    scope["event_id"] = scope["event_id"].map(clean)
    scope["ticker"] = scope["ticker"].map(normalize_ticker)
    identity = event_inventory_identity(scope[["event_id", "ticker"]])
    if identity != config["residual_event_identity_sha256"]:
        raise RuntimeError(f"ACQUISITION_SCOPE_IDENTITY_CHANGED:{identity}")
    return scope, links, requests, {"manifest": actual_manifest, **child_hashes}


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
    try:
        document = html.fromstring(payload)
    except Exception as exc:
        raise RuntimeError("IDX_ATTACHMENT_UNSUPPORTED_OR_INVALID_DOCUMENT") from exc
    text = "\n".join(
        " ".join(str(value).split())
        for value in document.xpath("//body//text()")
        if " ".join(str(value).split())
    )
    return text, text


def successful_documents(
    root: Path,
    requests: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    documents: dict[str, dict[str, Any]] = {}
    parse_failures: list[dict[str, str]] = []
    for row in requests:
        if clean(row.get("request_kind")) != "IDX_ANNOUNCEMENT_ATTACHMENT":
            continue
        if int(row.get("status_code") or 0) != 200 or int(row.get("bytes") or 0) <= 0:
            continue
        raw_path = Path(str(row.get("path") or ""))
        if not raw_path.is_file():
            candidate = root / "raw" / "attachments" / raw_path.name
            if candidate.is_file():
                raw_path = candidate
            else:
                raise RuntimeError(f"RAW_ATTACHMENT_PATH_MISSING:{raw_path}")
        recorded_sha = clean(row.get("sha256"))
        actual_sha = sha256_file(raw_path)
        if not recorded_sha or recorded_sha != actual_sha:
            raise RuntimeError(f"RAW_ATTACHMENT_SHA_MISMATCH:{raw_path}:{actual_sha}!={recorded_sha}")
        payload = raw_path.read_bytes()
        try:
            plain, layout = document_text(payload)
        except Exception as exc:
            parse_failures.append(
                {
                    "source_url": clean(row.get("final_url") or row.get("requested_url")),
                    "source_sha256": actual_sha,
                    "diagnostic": f"{type(exc).__name__}:{exc}",
                }
            )
            continue
        urls = {clean(row.get("requested_url")), clean(row.get("final_url"))}
        urls.discard("")
        value = {
            "reference": f"IDX_ATTACHMENT_{clean(row.get('request_key'))}",
            "source_url": clean(row.get("final_url") or row.get("requested_url")),
            "source_sha256": actual_sha,
            "plain_text": plain,
            "layout_text": layout,
        }
        for url in urls:
            existing = documents.get(url)
            if existing and existing["source_sha256"] != actual_sha:
                raise RuntimeError(f"ATTACHMENT_URL_SHA_CONFLICT:{url}")
            documents[url] = value
    return documents, parse_failures


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    config = read_json(args.config, "CONFIG")
    verify_config(config)
    scope, links, request_rows, acquisition_hashes = verify_acquisition_root(
        args.acquisition_root,
        args.expected_acquisition_manifest_sha,
        config,
    )
    calendar, calendar_sha = verify_calendar(args.artifact_root, config)
    documents_by_url, document_parse_failures = successful_documents(
        args.acquisition_root,
        request_rows,
    )

    if not links.empty:
        links["event_id"] = links["event_id"].map(clean)
        links["ticker"] = links["ticker"].map(normalize_ticker)
        links["attachment_url"] = links["attachment_url"].map(clean)
    scope_lookup = {
        (clean(row["event_id"]), normalize_ticker(row["ticker"])): row
        for row in scope.to_dict("records")
    }

    event_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    missing_raw_candidate_links = 0
    parsed_candidate_links = 0

    for key, event in sorted(scope_lookup.items(), key=lambda item: (item[0][1], item[0][0])):
        event_id, ticker = key
        event_links = links[
            links["event_id"].eq(event_id) & links["ticker"].eq(ticker)
        ].copy() if not links.empty else pd.DataFrame()
        candidates: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for link in event_links.to_dict("records") if not event_links.empty else []:
            url = clean(link.get("attachment_url"))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            raw = documents_by_url.get(url)
            if raw is None:
                missing_raw_candidate_links += 1
                audit_rows.append(
                    {
                        "event_id": event_id,
                        "ticker": ticker,
                        "event_source_type": clean(event.get("source_type")),
                        "announcement_no": clean(link.get("announcement_no")),
                        "attachment_url": url,
                        "source_sha256": "",
                        "raw_available": False,
                        "document_class": "",
                        "event_family": "",
                        "payment_dates": "",
                        "settlement_dates": "",
                        "cash_purchase_dates": "",
                        "record_date": "",
                        "distribution_date": "",
                        "transition_date": "",
                        "transition_semantic": "",
                        "diagnostics": "FROZEN_IDX_ATTACHMENT_RAW_NOT_AVAILABLE_OR_UNSUPPORTED",
                    }
                )
                continue

            index_subject = clean(f"{link.get('title', '')} {link.get('subject', '')}")
            parsed: ParsedResidualDocument = parse_residual_document_hardened(
                raw["plain_text"],
                expected_ticker=ticker,
                index_subject=index_subject,
                layout_text=raw["layout_text"],
            )
            parsed_candidate_links += 1
            candidate = {
                **raw,
                "reference": clean(link.get("announcement_no")) or raw["reference"],
                "parsed": parsed,
            }
            candidates.append(candidate)
            audit_rows.append(
                {
                    "event_id": event_id,
                    "ticker": ticker,
                    "event_source_type": clean(event.get("source_type")),
                    "announcement_no": clean(link.get("announcement_no")),
                    "attachment_url": url,
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
                    field: content
                    for field, content in value.items()
                    if field not in {"ksei_references", "source_urls", "source_sha256s", "diagnostics"}
                },
                "official_reference": "|".join(evidence.ksei_references),
                "source_url": "|".join(evidence.source_urls),
                "source_sha256": "|".join(evidence.source_sha256s),
                "diagnostics": "|".join(evidence.diagnostics),
                "frozen_candidate_attachment_count": int(len(seen_urls)),
                "parsed_candidate_attachment_count": int(len(candidates)),
            }
        )

    evidence = pd.DataFrame(event_rows).sort_values(
        ["ticker", "event_source_type", "event_id"], kind="mergesort"
    ).reset_index(drop=True)
    if len(evidence) != 59 or evidence.duplicated(["event_id", "ticker"]).any():
        raise RuntimeError("ADJUDICATION_EVENT_IDENTITY_CHANGED")
    identity = event_inventory_identity(evidence[["event_id", "ticker"]])
    if identity != config["residual_event_identity_sha256"]:
        raise RuntimeError(f"ADJUDICATION_EVENT_IDENTITY_HASH_CHANGED:{identity}")

    audit = pd.DataFrame(audit_rows)
    if audit.empty:
        audit = pd.DataFrame(columns=[
            "event_id", "ticker", "event_source_type", "announcement_no", "attachment_url",
            "source_sha256", "raw_available", "document_class", "event_family", "payment_dates",
            "settlement_dates", "cash_purchase_dates", "record_date", "distribution_date",
            "transition_date", "transition_semantic", "diagnostics",
        ])
    else:
        audit = audit.sort_values(
            ["ticker", "event_id", "announcement_no", "attachment_url"], kind="mergesort"
        ).reset_index(drop=True)

    parse_failure_frame = pd.DataFrame(document_parse_failures)
    if parse_failure_frame.empty:
        parse_failure_frame = pd.DataFrame(columns=["source_url", "source_sha256", "diagnostic"])

    exact_transition = int(evidence["linkage_status"].eq("EXACT").sum())
    exact_nonblocking = int(evidence["linkage_status"].eq("EXACT_NON_BLOCKING").sum())
    conflicts = int(evidence["linkage_status"].eq("CONFLICT").sum())
    unresolved = int(evidence["linkage_status"].eq("UNRESOLVED").sum())
    resolved = exact_transition + exact_nonblocking
    if resolved + conflicts + unresolved != 59:
        raise RuntimeError("ADJUDICATION_STATUS_PARTITION_INVALID")

    args.output_dir.mkdir(parents=True)
    evidence_path = args.output_dir / "schedule_59_idx_event_evidence.csv"
    audit_path = args.output_dir / "schedule_59_idx_adjudication_audit.csv"
    parse_failure_path = args.output_dir / "idx_attachment_parse_failures.csv"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"
    evidence.to_csv(evidence_path, index=False, lineterminator="\n")
    audit.to_csv(audit_path, index=False, lineterminator="\n")
    parse_failure_frame.to_csv(parse_failure_path, index=False, lineterminator="\n")

    status = "V4_3_CA_SCHEDULE_59_IDX_OFFLINE_ADJUDICATION_COMPLETE"
    summary = {
        "schema_version": "v4_3_ca_training_domain_schedule_59_idx_adjudication_result_v1",
        "status": status,
        "outcome_blind": True,
        "network_calls": False,
        "provider_calls": False,
        "source_substitution": False,
        "new_document_discovery": False,
        "target_or_rank_materialized": False,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "residual_events": 59,
        "residual_event_identity_sha256": identity,
        "verified_successful_raw_attachments": int(len({row["source_sha256"] for row in documents_by_url.values()})),
        "frozen_event_attachment_links": int(len(links)),
        "parsed_unique_event_attachment_links": int(parsed_candidate_links),
        "missing_raw_candidate_links": int(missing_raw_candidate_links),
        "unsupported_or_parse_failed_attachments": int(len(parse_failure_frame)),
        "exact_transition_events": exact_transition,
        "exact_nonblocking_events": exact_nonblocking,
        "resolved_events": resolved,
        "conflict_events": conflicts,
        "unresolved_events": unresolved,
        "next": "REVIEW_IDX_SEMANTIC_YIELD_AND_DECIDE_REPLAY_OR_STOP_RULE",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_hashes = {
        "event_evidence": sha256_file(evidence_path),
        "adjudication_audit": sha256_file(audit_path),
        "attachment_parse_failures": sha256_file(parse_failure_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_schedule_59_idx_adjudication_manifest_v1",
        "status": status,
        "outcome_blind": True,
        "immutable_inputs": {
            **acquisition_hashes,
            "official_calendar": calendar_sha,
            "residual_event_identity_sha256": identity,
        },
        "output_hashes": output_hashes,
        "guardrails": {
            "network_calls": False,
            "provider_calls": False,
            "source_substitution": False,
            "new_document_discovery": False,
            "fuzzy_event_matching": False,
            "price_inference": False,
            "record_or_distribution_date_as_transition": False,
            "pass_preserving_subset_selection": False,
            "parser_or_semantic_relaxation_after_observed_corpus": False,
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
                "residual_events": 59,
                "verified_successful_raw_attachments": summary["verified_successful_raw_attachments"],
                "frozen_event_attachment_links": summary["frozen_event_attachment_links"],
                "parsed_unique_event_attachment_links": parsed_candidate_links,
                "missing_raw_candidate_links": missing_raw_candidate_links,
                "unsupported_or_parse_failed_attachments": summary["unsupported_or_parse_failed_attachments"],
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
