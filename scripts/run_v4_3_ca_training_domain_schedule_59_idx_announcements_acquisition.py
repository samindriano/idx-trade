"""Acquire official IDX announcement evidence for all residual V4-3 CA events.

This is an outcome-blind, non-admissive provider stage. It consumes the frozen
59-event diagnosis and the zero-yield KSEI News adjudication, queries the
official IDX ListedCompany/GetAnnouncement endpoint in deterministic date
windows derived only from frozen source dates, and captures deterministic
candidate IDX-hosted attachments. Semantic adjudication is a later offline
stage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.parse import urlencode

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.ranking_v4_3_ca_schedule_reuse import event_inventory_identity  # noqa: E402
from idx_trade.v4_3_ca_schedule59_idx_announcements import (  # noqa: E402
    announcement_is_candidate,
    clean,
    date_window,
    normalize_ticker,
    official_idx_attachment_url,
    parse_pipe_dates,
    request_identity,
)

DEFAULT_CONFIG = Path("config/v4_3_ca_training_domain_schedule_59_idx_announcements_v1.json")


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", clean(value)).strip("_.")
    return value[:140] or "item"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnosis-root", type=Path, required=True)
    parser.add_argument("--news-adjudication-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "v4_3_ca_training_domain_schedule_59_idx_announcements_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    provider = config.get("provider") or {}
    if provider.get("name") != "IDX_OFFICIAL_LISTED_COMPANY_ANNOUNCEMENTS":
        raise RuntimeError("PROVIDER_CHANGED")
    if clean(provider.get("base_url")) != "https://www.idx.co.id":
        raise RuntimeError("IDX_BASE_URL_CHANGED")
    if clean(provider.get("endpoint")) != "/primary/ListedCompany/GetAnnouncement":
        raise RuntimeError("IDX_ENDPOINT_CHANGED")
    if int(provider.get("page_size") or 0) <= 0:
        raise RuntimeError("PAGE_SIZE_INVALID")
    if int(provider.get("max_pages_per_ticker_window") or 0) <= 0:
        raise RuntimeError("MAX_PAGES_INVALID")
    if int(provider.get("max_attempts") or 0) != 3:
        raise RuntimeError("MAX_ATTEMPTS_CHANGED")
    if tuple(float(x) for x in provider.get("backoff_seconds") or []) != (1.0, 3.0):
        raise RuntimeError("BACKOFF_CHANGED")
    hard = config.get("hard_boundaries") or {}
    for key in (
        "pass_preserving_subset_selection",
        "event_impact_ranking_for_discovery",
        "price_inference",
        "record_or_distribution_date_as_transition",
        "source_date_inference",
        "source_substitution",
        "external_search_engine",
        "semantic_admission_during_acquisition",
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


def verify_diagnosis(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    expected = config["diagnosis_parent"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    census_path = root / "residual_59_failure_mode_census.csv"
    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(f"DIAGNOSIS_MANIFEST_SHA_MISMATCH:{actual_manifest}")
    manifest = read_json(manifest_path, "DIAGNOSIS_MANIFEST")
    summary = read_json(summary_path, "DIAGNOSIS_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("DIAGNOSIS_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("DIAGNOSIS_NOT_OUTCOME_BLIND")
    if int(summary.get("residual_events") or -1) != int(expected["residual_events"]):
        raise RuntimeError("DIAGNOSIS_EVENT_COUNT_CHANGED")
    if summary.get("residual_event_identity_sha256") != expected["residual_event_identity_sha256"]:
        raise RuntimeError("DIAGNOSIS_EVENT_IDENTITY_CHANGED")
    outputs = manifest.get("output_hashes") or {}
    expected_census = clean(outputs.get("failure_mode_census"))
    expected_summary = clean(outputs.get("summary"))
    actual_census = sha256_file(census_path)
    actual_summary = sha256_file(summary_path)
    if not expected_census or actual_census != expected_census:
        raise RuntimeError("DIAGNOSIS_CENSUS_SHA_CHANGED")
    if not expected_summary or actual_summary != expected_summary:
        raise RuntimeError("DIAGNOSIS_SUMMARY_SHA_CHANGED")
    for key in (
        "network_calls",
        "provider_calls",
        "new_document_discovery",
        "parser_relaxation",
        "pass_preserving_subset_selection",
        "target_or_rank_materialized",
        "historical_target_loaded",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"DIAGNOSIS_GUARDRAIL_CHANGED:{key}")
    census = pd.read_csv(census_path, dtype=str, keep_default_na=False)
    required = {
        "event_id", "ticker", "source_type", "family", "source_dates",
        "failure_mode", "remediation_class",
    }
    missing = required - set(census.columns)
    if missing:
        raise RuntimeError(f"DIAGNOSIS_COLUMNS_MISSING:{sorted(missing)}")
    census["event_id"] = census["event_id"].map(clean)
    census["ticker"] = census["ticker"].map(normalize_ticker)
    if len(census) != 59 or census.duplicated(["event_id", "ticker"]).any():
        raise RuntimeError("DIAGNOSIS_SCOPE_IDENTITY_INVALID")
    identity = event_inventory_identity(census[["event_id", "ticker"]])
    if identity != expected["residual_event_identity_sha256"]:
        raise RuntimeError("DIAGNOSIS_SCOPE_IDENTITY_HASH_CHANGED")
    return census, {
        "diagnosis_manifest": actual_manifest,
        "diagnosis_summary": actual_summary,
        "diagnosis_census": actual_census,
    }


def verify_prior_news(root: Path, config: dict[str, Any]) -> dict[str, str]:
    expected = config["prior_news_adjudication"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    evidence_path = root / "schedule_59_ksei_news_event_evidence.csv"
    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(f"NEWS_ADJUDICATION_MANIFEST_SHA_MISMATCH:{actual_manifest}")
    manifest = read_json(manifest_path, "NEWS_ADJUDICATION_MANIFEST")
    summary = read_json(summary_path, "NEWS_ADJUDICATION_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("NEWS_ADJUDICATION_STATUS_CHANGED")
    for key in ("resolved_events", "unresolved_events", "conflict_events"):
        if int(summary.get(key, -1)) != int(expected[key]):
            raise RuntimeError(f"NEWS_ADJUDICATION_RESULT_CHANGED:{key}")
    if summary.get("historical_target_loaded") is not False or summary.get("model_fit") is not False:
        raise RuntimeError("NEWS_ADJUDICATION_OUTCOME_GUARD_CHANGED")
    outputs = manifest.get("output_hashes") or {}
    expected_summary_sha = clean(outputs.get("summary"))
    expected_evidence_sha = clean(outputs.get("event_evidence"))
    actual_summary_sha = sha256_file(summary_path)
    actual_evidence_sha = sha256_file(evidence_path)
    if not expected_summary_sha or expected_summary_sha != actual_summary_sha:
        raise RuntimeError("NEWS_ADJUDICATION_SUMMARY_SHA_CHANGED")
    if not expected_evidence_sha or expected_evidence_sha != actual_evidence_sha:
        raise RuntimeError("NEWS_ADJUDICATION_EVIDENCE_SHA_CHANGED")
    return {
        "news_adjudication_manifest": actual_manifest,
        "news_adjudication_summary": actual_summary_sha,
        "news_adjudication_evidence": actual_evidence_sha,
    }


def make_session(config: dict[str, Any]) -> Any:
    try:
        from curl_cffi import requests as curl_requests
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("CURL_CFFI_REQUIRED") from exc
    provider = config["provider"]
    session = curl_requests.Session(impersonate="chrome110")
    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": provider["referer"],
            "User-Agent": "Mozilla/5.0",
        }
    )
    return session


def capture_request(
    session: Any,
    *,
    url: str,
    params: dict[str, Any] | None,
    raw_path_prefix: Path,
    config: dict[str, Any],
    request_kind: str,
    request_key: str,
) -> tuple[bytes | None, list[dict[str, Any]]]:
    provider = config["provider"]
    attempts: list[dict[str, Any]] = []
    max_attempts = int(provider["max_attempts"])
    backoff = tuple(float(x) for x in provider["backoff_seconds"])
    timeout = float(provider["timeout_seconds"])
    requested_url = url
    if params:
        requested_url = f"{url}?{urlencode(params, doseq=True)}"
    for attempt in range(1, max_attempts + 1):
        row: dict[str, Any] = {
            "request_kind": request_kind,
            "request_key": request_key,
            "attempt": attempt,
            "requested_url": requested_url,
            "accessed_at_utc": pd.Timestamp.utcnow().isoformat(),
        }
        try:
            response = session.get(url, params=params, timeout=timeout)
            payload = bytes(getattr(response, "content", b"") or b"")
            content_type = clean(getattr(response, "headers", {}).get("content-type", ""))
            suffix = ".json" if "json" in content_type.casefold() else (
                ".pdf" if payload.startswith(b"%PDF") else ".bin"
            )
            raw_path = Path(str(raw_path_prefix) + f"_attempt_{attempt:02d}{suffix}")
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(payload)
            row.update(
                {
                    "final_url": str(getattr(response, "url", requested_url)),
                    "status_code": int(getattr(response, "status_code", 0) or 0),
                    "content_type": content_type,
                    "bytes": len(payload),
                    "sha256": sha256_bytes(payload),
                    "path": str(raw_path),
                }
            )
            attempts.append(row)
            if row["status_code"] == 200 and payload:
                return payload, attempts
            row["error"] = "HTTP_NON_200_OR_EMPTY"
        except Exception as exc:  # pragma: no cover - transport dependent
            row.update(
                {
                    "status_code": 0,
                    "bytes": 0,
                    "sha256": "",
                    "path": "",
                    "error": f"{type(exc).__name__}:{exc}",
                }
            )
            attempts.append(row)
        if attempt < max_attempts:
            time.sleep(backoff[attempt - 1])
    return None, attempts


def parse_api_payload(payload: bytes) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8-sig"))
    except Exception as exc:
        raise RuntimeError("IDX_ANNOUNCEMENT_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise RuntimeError("IDX_ANNOUNCEMENT_JSON_NOT_OBJECT")
    replies = value.get("Replies")
    if replies is None:
        replies = []
    if not isinstance(replies, list):
        raise RuntimeError("IDX_ANNOUNCEMENT_REPLIES_NOT_LIST")
    return value


def announcement_identity(item: dict[str, Any]) -> tuple[str, str, str]:
    p = item.get("pengumuman") or {}
    if not isinstance(p, dict):
        p = {}
    return (
        clean(p.get("NoPengumuman")),
        normalize_ticker(p.get("Kode_Emiten")),
        clean(p.get("TglPengumuman")),
    )


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    config = read_json(args.config, "CONFIG")
    verify_config(config)
    census, diagnosis_hashes = verify_diagnosis(args.diagnosis_root, config)
    prior_news_hashes = verify_prior_news(args.news_adjudication_root, config)

    provider = config["provider"]
    base_url = provider["base_url"].rstrip("/")
    endpoint_url = base_url + provider["endpoint"]
    page_size = int(provider["page_size"])
    max_pages = int(provider["max_pages_per_ticker_window"])
    before_days = int(provider["date_window_days_before"])
    after_days = int(provider["date_window_days_after"])

    # Freeze complete event/query scope before output creation or provider access.
    scope_rows: list[dict[str, Any]] = []
    query_to_events: dict[tuple[str, str, str], set[tuple[str, str]]] = {}
    for event in census.to_dict("records"):
        source_dates = parse_pipe_dates(event["source_dates"])
        date_from, date_to = date_window(
            source_dates,
            before_days=before_days,
            after_days=after_days,
        )
        key = (event["ticker"], date_from, date_to)
        query_to_events.setdefault(key, set()).add((event["event_id"], event["ticker"]))
        scope_rows.append(
            {
                "event_id": event["event_id"],
                "ticker": event["ticker"],
                "source_type": event["source_type"],
                "family": event["family"],
                "source_dates": event["source_dates"],
                "failure_mode": event["failure_mode"],
                "remediation_class": event["remediation_class"],
                "date_from": date_from,
                "date_to": date_to,
            }
        )
    scope = pd.DataFrame(scope_rows).sort_values(["ticker", "event_id"], kind="mergesort")
    if len(scope) != 59:
        raise RuntimeError("PREPROVIDER_SCOPE_COUNT_CHANGED")
    identity = event_inventory_identity(scope[["event_id", "ticker"]])
    if identity != config["diagnosis_parent"]["residual_event_identity_sha256"]:
        raise RuntimeError("PREPROVIDER_SCOPE_IDENTITY_CHANGED")

    args.output_dir.mkdir(parents=True)
    raw_root = args.output_dir / "raw"
    api_raw = raw_root / "api"
    attachment_raw = raw_root / "attachments"
    api_raw.mkdir(parents=True)
    attachment_raw.mkdir(parents=True)

    scope_path = args.output_dir / "frozen_residual_59_scope.csv"
    query_path = args.output_dir / "frozen_idx_announcement_query_scope.csv"
    inventory_path = args.output_dir / "idx_announcement_inventory.csv"
    event_announcement_path = args.output_dir / "event_idx_announcement_candidate_links.csv"
    event_attachment_path = args.output_dir / "event_idx_attachment_candidate_links.csv"
    attachment_inventory_path = args.output_dir / "idx_attachment_inventory.csv"
    request_path = args.output_dir / "request_records.jsonl"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"

    scope.to_csv(scope_path, index=False, lineterminator="\n")
    query_frame = pd.DataFrame(
        [
            {
                "ticker": ticker,
                "date_from": date_from,
                "date_to": date_to,
                "event_count": len(events),
                "event_keys": "|".join(f"{eid}:{eticker}" for eid, eticker in sorted(events)),
            }
            for (ticker, date_from, date_to), events in sorted(query_to_events.items())
        ]
    )
    query_frame.to_csv(query_path, index=False, lineterminator="\n")

    session = make_session(config)
    request_records: list[dict[str, Any]] = []
    query_items: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    failed_api_queries = 0
    api_parse_failures = 0
    pagination_truncated_windows = 0
    api_pages_requested = 0

    for q_index, ((ticker, date_from, date_to), event_keys) in enumerate(sorted(query_to_events.items()), start=1):
        collected: dict[tuple[str, str, str], dict[str, Any]] = {}
        total_count: int | None = None
        ended = False
        for page_index in range(max_pages):
            index_from = page_index * page_size
            params = {
                "pageSize": page_size,
                "indexFrom": index_from,
                "language": provider["language"],
                "kodeEmiten": ticker,
                "emitenType": provider["emiten_type"],
                "dateFrom": date_from,
                "dateTo": date_to,
            }
            prefix = api_raw / f"q{q_index:03d}_{safe_name(ticker)}_{date_from}_{date_to}_p{page_index:02d}"
            payload, attempts = capture_request(
                session,
                url=endpoint_url,
                params=params,
                raw_path_prefix=prefix,
                config=config,
                request_kind="IDX_GET_ANNOUNCEMENT",
                request_key=f"{ticker}:{date_from}:{date_to}:index:{index_from}",
            )
            request_records.extend(attempts)
            api_pages_requested += 1
            if payload is None:
                failed_api_queries += 1
                ended = True
                break
            try:
                parsed = parse_api_payload(payload)
            except Exception as exc:
                api_parse_failures += 1
                request_records.append(
                    {
                        "request_kind": "IDX_GET_ANNOUNCEMENT_PARSE",
                        "request_key": f"{ticker}:{date_from}:{date_to}:index:{index_from}",
                        "attempt": 0,
                        "requested_url": endpoint_url,
                        "accessed_at_utc": pd.Timestamp.utcnow().isoformat(),
                        "status_code": 200,
                        "bytes": len(payload),
                        "sha256": sha256_bytes(payload),
                        "path": "",
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )
                ended = True
                break
            replies = parsed.get("Replies") or []
            if total_count is None:
                raw_total = parsed.get("ResultCount")
                try:
                    total_count = int(raw_total) if raw_total is not None else None
                except Exception:
                    total_count = None
            for item in replies:
                if not isinstance(item, dict):
                    continue
                key = announcement_identity(item)
                if not key[0] and not key[2]:
                    key = (hashlib.sha256(json.dumps(item, sort_keys=True, default=str).encode()).hexdigest(), ticker, "")
                collected[key] = item
            if not replies:
                ended = True
                break
            if total_count is not None and len(collected) >= total_count:
                ended = True
                break
            if len(replies) < page_size:
                ended = True
                break
            time.sleep(float(provider["inter_request_sleep_seconds"]))
        if not ended:
            pagination_truncated_windows += 1
        query_items[(ticker, date_from, date_to)] = list(collected.values())
        time.sleep(float(provider["inter_request_sleep_seconds"]))

    inventory_rows: list[dict[str, Any]] = []
    event_announcement_rows: list[dict[str, Any]] = []
    event_attachment_rows: list[dict[str, Any]] = []
    attachment_to_events: dict[str, set[tuple[str, str]]] = {}
    attachment_meta: dict[str, dict[str, Any]] = {}

    event_lookup = {(row["event_id"], row["ticker"]): row for row in scope.to_dict("records")}
    seen_inventory: set[tuple[str, str, str, str]] = set()
    for query_key, event_keys in sorted(query_to_events.items()):
        ticker, date_from, date_to = query_key
        for item in query_items.get(query_key, []):
            p = item.get("pengumuman") or {}
            if not isinstance(p, dict):
                p = {}
            item_ticker = normalize_ticker(p.get("Kode_Emiten"))
            if item_ticker and item_ticker != ticker:
                raise RuntimeError(f"IDX_ANNOUNCEMENT_TICKER_FILTER_BROKEN:{ticker}:{item_ticker}")
            ann_no = clean(p.get("NoPengumuman"))
            ann_date = clean(p.get("TglPengumuman"))
            title = clean(p.get("JudulPengumuman"))
            subject = clean(p.get("PerihalPengumuman"))
            inv_key = (ticker, ann_no, ann_date, title)
            if inv_key not in seen_inventory:
                seen_inventory.add(inv_key)
                inventory_rows.append(
                    {
                        "ticker": ticker,
                        "announcement_no": ann_no,
                        "announcement_date": ann_date,
                        "title": title,
                        "subject": subject,
                        "announcement_type": clean(p.get("JenisPengumuman")),
                        "form_id": clean(p.get("Form_Id")),
                        "attachment_count": len(item.get("attachments") or []),
                    }
                )
            for event_key in sorted(event_keys):
                event = event_lookup[event_key]
                if not announcement_is_candidate(
                    title,
                    subject,
                    source_type=event["source_type"],
                    config=config,
                ):
                    continue
                event_announcement_rows.append(
                    {
                        "event_id": event["event_id"],
                        "ticker": event["ticker"],
                        "source_type": event["source_type"],
                        "source_dates": event["source_dates"],
                        "date_from": date_from,
                        "date_to": date_to,
                        "announcement_no": ann_no,
                        "announcement_date": ann_date,
                        "title": title,
                        "subject": subject,
                    }
                )
                attachments = item.get("attachments") or []
                if not isinstance(attachments, list):
                    attachments = []
                for attachment in attachments:
                    if not isinstance(attachment, dict):
                        continue
                    raw_locator = clean(
                        attachment.get("FullSavePath")
                        or attachment.get("fullSavePath")
                        or attachment.get("DownloadPath")
                        or attachment.get("downloadPath")
                        or attachment.get("FilePath")
                        or attachment.get("filePath")
                        or attachment.get("Url")
                        or attachment.get("url")
                    )
                    url = official_idx_attachment_url(
                        raw_locator,
                        base_url=base_url,
                        allowed_hosts=config["allowed_attachment_hosts"],
                    )
                    if not url:
                        continue
                    filename = clean(
                        attachment.get("OriginalFilename")
                        or attachment.get("PDFFilename")
                        or Path(raw_locator).name
                    )
                    attachment_to_events.setdefault(url, set()).add(event_key)
                    attachment_meta[url] = {
                        "announcement_no": ann_no,
                        "announcement_date": ann_date,
                        "title": title,
                        "subject": subject,
                        "filename": filename,
                    }
                    event_attachment_rows.append(
                        {
                            "event_id": event["event_id"],
                            "ticker": event["ticker"],
                            "source_type": event["source_type"],
                            "announcement_no": ann_no,
                            "announcement_date": ann_date,
                            "title": title,
                            "subject": subject,
                            "attachment_url": url,
                            "attachment_filename": filename,
                        }
                    )

    inventory = pd.DataFrame(inventory_rows)
    if inventory.empty:
        inventory = pd.DataFrame(columns=[
            "ticker", "announcement_no", "announcement_date", "title", "subject",
            "announcement_type", "form_id", "attachment_count",
        ])
    else:
        inventory = inventory.drop_duplicates().sort_values(
            ["ticker", "announcement_date", "announcement_no", "title"], kind="mergesort"
        ).reset_index(drop=True)
    inventory.to_csv(inventory_path, index=False, lineterminator="\n")

    event_ann = pd.DataFrame(event_announcement_rows)
    if event_ann.empty:
        event_ann = pd.DataFrame(columns=[
            "event_id", "ticker", "source_type", "source_dates", "date_from", "date_to",
            "announcement_no", "announcement_date", "title", "subject",
        ])
    else:
        event_ann = event_ann.drop_duplicates().sort_values(
            ["ticker", "event_id", "announcement_date", "announcement_no"], kind="mergesort"
        ).reset_index(drop=True)
    event_ann.to_csv(event_announcement_path, index=False, lineterminator="\n")

    event_att = pd.DataFrame(event_attachment_rows)
    if event_att.empty:
        event_att = pd.DataFrame(columns=[
            "event_id", "ticker", "source_type", "announcement_no", "announcement_date",
            "title", "subject", "attachment_url", "attachment_filename",
        ])
    else:
        event_att = event_att.drop_duplicates().sort_values(
            ["ticker", "event_id", "announcement_date", "attachment_url"], kind="mergesort"
        ).reset_index(drop=True)
    event_att.to_csv(event_attachment_path, index=False, lineterminator="\n")

    attachment_rows: list[dict[str, Any]] = []
    provider_failed_attachments = 0
    for index, url in enumerate(sorted(attachment_to_events), start=1):
        meta = attachment_meta[url]
        filename = meta.get("filename") or f"attachment_{index}"
        prefix = attachment_raw / f"{index:04d}_{safe_name(filename)}"
        payload, attempts = capture_request(
            session,
            url=url,
            params=None,
            raw_path_prefix=prefix,
            config=config,
            request_kind="IDX_ANNOUNCEMENT_ATTACHMENT",
            request_key=hashlib.sha256(url.encode("utf-8")).hexdigest()[:20],
        )
        for row in attempts:
            row["linked_event_keys"] = "|".join(
                f"{eid}:{ticker}" for eid, ticker in sorted(attachment_to_events[url])
            )
        request_records.extend(attempts)
        if payload is None:
            provider_failed_attachments += 1
            attachment_rows.append(
                {
                    "attachment_url": url,
                    "attachment_filename": filename,
                    "announcement_no": meta["announcement_no"],
                    "source_sha256": "",
                    "bytes": 0,
                    "linked_event_count": len(attachment_to_events[url]),
                    "linked_event_keys": "|".join(
                        f"{eid}:{ticker}" for eid, ticker in sorted(attachment_to_events[url])
                    ),
                    "status": "UNRESOLVED_PROVIDER",
                }
            )
        else:
            attachment_rows.append(
                {
                    "attachment_url": url,
                    "attachment_filename": filename,
                    "announcement_no": meta["announcement_no"],
                    "source_sha256": sha256_bytes(payload),
                    "bytes": len(payload),
                    "linked_event_count": len(attachment_to_events[url]),
                    "linked_event_keys": "|".join(
                        f"{eid}:{ticker}" for eid, ticker in sorted(attachment_to_events[url])
                    ),
                    "status": "CAPTURED",
                }
            )
        time.sleep(float(provider["inter_request_sleep_seconds"]))

    attachments = pd.DataFrame(attachment_rows)
    if attachments.empty:
        attachments = pd.DataFrame(columns=[
            "attachment_url", "attachment_filename", "announcement_no", "source_sha256",
            "bytes", "linked_event_count", "linked_event_keys", "status",
        ])
    else:
        attachments = attachments.sort_values("attachment_url", kind="mergesort").reset_index(drop=True)
    attachments.to_csv(attachment_inventory_path, index=False, lineterminator="\n")
    write_jsonl(request_path, request_records)

    candidate_event_keys = set(zip(event_ann["event_id"], event_ann["ticker"])) if len(event_ann) else set()
    attachment_event_keys = set(zip(event_att["event_id"], event_att["ticker"])) if len(event_att) else set()
    successful_attachment_urls = set(
        attachments.loc[attachments["status"].eq("CAPTURED"), "attachment_url"].astype(str)
    ) if len(attachments) else set()
    successful_attachment_event_keys: set[tuple[str, str]] = set()
    if successful_attachment_urls and len(event_att):
        good_links = event_att[event_att["attachment_url"].isin(successful_attachment_urls)]
        successful_attachment_event_keys = set(zip(good_links["event_id"], good_links["ticker"]))

    raw_identity = request_identity(request_records)
    status = "V4_3_CA_SCHEDULE_59_IDX_ANNOUNCEMENTS_ACQUISITION_COMPLETE"
    summary = {
        "schema_version": "v4_3_ca_training_domain_schedule_59_idx_announcements_result_v1",
        "status": status,
        "outcome_blind": True,
        "provider_calls": True,
        "network_calls": True,
        "provider": provider["name"],
        "semantic_admission_performed": False,
        "source_substitution": False,
        "external_search_engine": False,
        "pass_preserving_subset_selection": False,
        "target_or_rank_materialized": False,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "scientific_config_changed": False,
        "residual_events": 59,
        "residual_event_identity_sha256": identity,
        "query_windows": int(len(query_to_events)),
        "api_pages_requested": int(api_pages_requested),
        "failed_api_queries": int(failed_api_queries),
        "api_parse_failures": int(api_parse_failures),
        "pagination_truncated_windows": int(pagination_truncated_windows),
        "announcements_seen": int(len(inventory)),
        "candidate_announcements": int(len(event_ann)),
        "events_with_candidate_announcements": int(len(candidate_event_keys)),
        "events_without_candidate_announcements": int(59 - len(candidate_event_keys)),
        "candidate_attachment_links": int(len(event_att)),
        "events_with_candidate_attachments": int(len(attachment_event_keys)),
        "unique_attachments_requested": int(len(attachment_to_events)),
        "provider_failed_attachments": int(provider_failed_attachments),
        "events_with_successful_attachments": int(len(successful_attachment_event_keys)),
        "successful_raw_response_identity_sha256": raw_identity,
        "next": "FREEZE_IDX_ANNOUNCEMENT_CORPUS_AND_RUN_OFFLINE_SEMANTIC_ADJUDICATION",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_hashes = {
        "frozen_residual_scope": sha256_file(scope_path),
        "frozen_query_scope": sha256_file(query_path),
        "announcement_inventory": sha256_file(inventory_path),
        "event_announcement_candidate_links": sha256_file(event_announcement_path),
        "event_attachment_candidate_links": sha256_file(event_attachment_path),
        "attachment_inventory": sha256_file(attachment_inventory_path),
        "request_records": sha256_file(request_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_schedule_59_idx_announcements_manifest_v1",
        "status": status,
        "outcome_blind": True,
        "immutable_inputs": {
            **diagnosis_hashes,
            **prior_news_hashes,
            "residual_event_identity_sha256": identity,
        },
        "output_hashes": output_hashes,
        "successful_raw_response_identity_sha256": raw_identity,
        "guardrails": {
            "provider_calls": True,
            "network_calls": True,
            "source_substitution": False,
            "external_search_engine": False,
            "semantic_admission_performed": False,
            "pass_preserving_subset_selection": False,
            "event_impact_ranking_for_discovery": False,
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
                "status": status,
                "residual_events": 59,
                "query_windows": summary["query_windows"],
                "api_pages_requested": api_pages_requested,
                "failed_api_queries": failed_api_queries,
                "api_parse_failures": api_parse_failures,
                "pagination_truncated_windows": pagination_truncated_windows,
                "announcements_seen": summary["announcements_seen"],
                "candidate_announcements": summary["candidate_announcements"],
                "events_with_candidate_announcements": summary["events_with_candidate_announcements"],
                "events_without_candidate_announcements": summary["events_without_candidate_announcements"],
                "candidate_attachment_links": summary["candidate_attachment_links"],
                "events_with_candidate_attachments": summary["events_with_candidate_attachments"],
                "unique_attachments_requested": summary["unique_attachments_requested"],
                "provider_failed_attachments": provider_failed_attachments,
                "events_with_successful_attachments": summary["events_with_successful_attachments"],
                "semantic_admission_performed": False,
                "historical_target_loaded": False,
                "model_fit": False,
                "performance_computed": False,
                "successful_raw_response_identity_sha256": raw_identity,
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
