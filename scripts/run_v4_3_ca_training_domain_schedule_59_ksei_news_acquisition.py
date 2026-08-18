"""Secondary official-KSEI discovery for all 59 unresolved V4-3 CA events.

This provider stage is outcome-blind and non-admissive. It uses only KSEI's
own `/search/results/` surface to discover KSEI News pages, captures those pages
and official KSEI attachments, and freezes raw bytes/diagnostics for a later
offline semantic adjudication. No target, rank, model, prediction, performance,
or price inference is accessed here.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.parse import urlparse

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
for value in (SRC_ROOT, SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import run_v4_ca_schedule_acquisition as base  # noqa: E402
from idx_trade.ranking_v4_3_ca_schedule_reuse import event_inventory_identity  # noqa: E402
from idx_trade.v4_3_ca_schedule59_ksei_news import (  # noqa: E402
    build_event_queries,
    clean,
    encode_search_url,
    exact_ticker_token,
    is_ksei_attachment_url,
    is_ksei_news_url,
    is_ksei_search_url,
    normalize_ticker,
    parse_news_page,
    parse_pipe_dates,
    parse_search_page,
    request_identity,
)


DEFAULT_CONFIG = Path("config/v4_3_ca_training_domain_schedule_59_ksei_news_v1.json")


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnosis-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def require_int(mapping: dict[str, Any], key: str, label: str) -> int:
    value = mapping.get(key)
    if value is None:
        raise RuntimeError(f"{label}_MISSING:{key}")
    return int(value)


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "v4_3_ca_training_domain_schedule_59_ksei_news_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    provider = config.get("provider") or {}
    if provider.get("name") != "KSEI_PUBLIC_SITE_SEARCH_AND_NEWS":
        raise RuntimeError("PROVIDER_CHANGED")
    if clean(provider.get("base_url")) != base.KSEI_BASE:
        raise RuntimeError("PROVIDER_BASE_URL_CHANGED")
    if provider.get("source_substitution") is not False:
        raise RuntimeError("SOURCE_SUBSTITUTION_ENABLED")
    if provider.get("external_search_engine") is not False:
        raise RuntimeError("EXTERNAL_SEARCH_ENGINE_ENABLED")
    if require_int(provider, "max_attempts", "PROVIDER") != int(base.MAX_ATTEMPTS):
        raise RuntimeError("MAX_ATTEMPTS_CHANGED")
    if tuple(float(x) for x in provider.get("backoff_seconds") or []) != tuple(
        float(x) for x in base.BACKOFF_SECONDS
    ):
        raise RuntimeError("BACKOFF_CHANGED")
    if float(provider.get("inter_request_sleep_seconds")) != float(base.INTER_REQUEST_SLEEP):
        raise RuntimeError("INTER_REQUEST_SLEEP_CHANGED")
    if require_int(provider, "max_pages_per_query", "PROVIDER") <= 0:
        raise RuntimeError("MAX_PAGES_INVALID")
    hard = config.get("hard_boundaries") or {}
    for key in (
        "pass_preserving_subset_selection",
        "event_impact_ranking_for_discovery",
        "price_inference",
        "record_or_distribution_date_as_transition",
        "source_date_inference",
        "source_substitution",
        "external_search_engine",
        "parser_or_semantic_relaxation_after_provider_result",
        "semantic_admission_during_acquisition",
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
        raise RuntimeError(
            f"DIAGNOSIS_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = read_json(manifest_path, "DIAGNOSIS_MANIFEST")
    summary = read_json(summary_path, "DIAGNOSIS_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("DIAGNOSIS_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("DIAGNOSIS_NOT_OUTCOME_BLIND")
    if require_int(summary, "residual_events", "DIAGNOSIS_SUMMARY") != int(expected["residual_events"]):
        raise RuntimeError("DIAGNOSIS_EVENT_COUNT_CHANGED")
    if summary.get("residual_event_identity_sha256") != expected["residual_event_identity_sha256"]:
        raise RuntimeError("DIAGNOSIS_EVENT_IDENTITY_CHANGED")
    if summary.get("failure_mode_counts") != expected["failure_mode_counts"]:
        raise RuntimeError("DIAGNOSIS_FAILURE_MODE_COUNTS_CHANGED")
    if summary.get("remediation_class_counts") != expected["remediation_class_counts"]:
        raise RuntimeError("DIAGNOSIS_REMEDIATION_COUNTS_CHANGED")
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
    outputs = manifest.get("output_hashes") or {}
    expected_census = clean(outputs.get("failure_mode_census"))
    expected_summary = clean(outputs.get("summary"))
    actual_census = sha256_file(census_path)
    actual_summary = sha256_file(summary_path)
    if not expected_census or actual_census != expected_census:
        raise RuntimeError("DIAGNOSIS_CENSUS_SHA_CHANGED")
    if not expected_summary or actual_summary != expected_summary:
        raise RuntimeError("DIAGNOSIS_SUMMARY_SHA_CHANGED")
    census = pd.read_csv(census_path, dtype=str, keep_default_na=False)
    required = {
        "event_id",
        "ticker",
        "source_type",
        "family",
        "source_dates",
        "failure_mode",
        "remediation_class",
    }
    missing = required - set(census.columns)
    if missing:
        raise RuntimeError(f"DIAGNOSIS_CENSUS_COLUMNS_MISSING:{sorted(missing)}")
    if len(census) != int(expected["residual_events"]):
        raise RuntimeError("DIAGNOSIS_CENSUS_COUNT_CHANGED")
    census["event_id"] = census["event_id"].map(clean)
    census["ticker"] = census["ticker"].map(normalize_ticker)
    identity = event_inventory_identity(census[["event_id", "ticker"]])
    if identity != expected["residual_event_identity_sha256"]:
        raise RuntimeError(f"DIAGNOSIS_CENSUS_IDENTITY_CHANGED:{identity}")
    return census, {
        "diagnosis_manifest": actual_manifest,
        "diagnosis_summary": actual_summary,
        "diagnosis_failure_mode_census": actual_census,
    }


def build_query_scope(census: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, set[tuple[str, str]]]]:
    contract = config["query_contract"]
    query_to_events: dict[str, set[tuple[str, str]]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    for event in census.to_dict("records"):
        dates = parse_pipe_dates(event["source_dates"])
        queries = build_event_queries(
            ticker=event["ticker"],
            source_type=event["source_type"],
            source_dates=dates,
            contract=contract,
        )
        if not queries:
            raise RuntimeError(f"EVENT_QUERY_SCOPE_EMPTY:{event['event_id']}:{event['ticker']}")
        for query in queries:
            query_to_events[query].add((event["event_id"], event["ticker"]))
            rows.append(
                {
                    "event_id": event["event_id"],
                    "ticker": event["ticker"],
                    "source_type": event["source_type"],
                    "family": event["family"],
                    "source_dates": "|".join(dates),
                    "failure_mode": event["failure_mode"],
                    "remediation_class": event["remediation_class"],
                    "query_text": query,
                    "search_url": encode_search_url(config["provider"]["base_url"], query),
                }
            )
    frame = pd.DataFrame(rows).drop_duplicates().sort_values(
        ["ticker", "event_id", "query_text"], kind="mergesort"
    ).reset_index(drop=True)
    covered = set(zip(frame["event_id"], frame["ticker"]))
    expected = set(zip(census["event_id"], census["ticker"]))
    if covered != expected:
        raise RuntimeError("QUERY_SCOPE_EVENT_COVERAGE_CHANGED")
    return frame, query_to_events


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.")
    return value[:120] or "item"


def article_id(url: str) -> str:
    match = re.search(r"/ksei_news/read/(\d+)", urlparse(url).path, flags=re.IGNORECASE)
    return match.group(1) if match else hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    config = read_json(args.config, "CONFIG")
    verify_config(config)
    census, diagnosis_hashes = verify_diagnosis(args.diagnosis_root, config)
    query_scope, query_to_events = build_query_scope(census, config)

    # Freeze all acquisition scope before creating output or making a request.
    event_identity = event_inventory_identity(census[["event_id", "ticker"]])
    if event_identity != config["diagnosis_parent"]["residual_event_identity_sha256"]:
        raise RuntimeError("PREPROVIDER_EVENT_IDENTITY_CHANGED")
    if len(set(zip(census["event_id"], census["ticker"]))) != 59:
        raise RuntimeError("PREPROVIDER_EVENT_COUNT_CHANGED")

    args.output_dir.mkdir(parents=True)
    raw_root = args.output_dir / "raw"
    search_raw = raw_root / "search"
    news_raw = raw_root / "news"
    attachment_raw = raw_root / "attachments"
    for path in (search_raw, news_raw, attachment_raw):
        path.mkdir(parents=True)

    scope_path = args.output_dir / "frozen_residual_59_scope.csv"
    query_path = args.output_dir / "frozen_ksei_search_query_scope.csv"
    search_results_path = args.output_dir / "ksei_search_news_results.csv"
    event_news_path = args.output_dir / "event_news_candidate_links.csv"
    article_path = args.output_dir / "news_article_inventory.csv"
    event_attachment_path = args.output_dir / "event_attachment_candidate_links.csv"
    attachment_path = args.output_dir / "news_attachment_inventory.csv"
    request_path = args.output_dir / "request_records.jsonl"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"

    census.sort_values(["ticker", "event_id"], kind="mergesort").to_csv(
        scope_path, index=False, lineterminator="\n"
    )
    query_scope.to_csv(query_path, index=False, lineterminator="\n")

    provider = config["provider"]
    timeout = float(provider["timeout_seconds"])
    max_pages = int(provider["max_pages_per_query"])
    session = base.make_session()
    request_records: list[dict[str, Any]] = []

    search_rows: list[dict[str, Any]] = []
    event_news_rows: list[dict[str, Any]] = []
    article_to_events: dict[str, set[tuple[str, str]]] = defaultdict(set)
    failed_search_queries = 0
    search_parse_failures = 0
    search_pagination_truncated = 0
    search_pagination_cycles = 0

    for query in sorted(query_to_events, key=lambda value: (value.casefold(), value)):
        query_id = hashlib.sha256(query.encode("utf-8")).hexdigest()[:20]
        current_url = encode_search_url(provider["base_url"], query)
        seen_pages: set[str] = set()
        ended = False
        for page_number in range(1, max_pages + 1):
            if current_url in seen_pages:
                search_pagination_cycles += 1
                ended = True
                break
            seen_pages.add(current_url)
            prefix = search_raw / f"{query_id}_page_{page_number:02d}"
            payload, attempts = base.capture_request(
                session,
                url=current_url,
                raw_path_prefix=prefix,
                timeout_seconds=timeout,
                request_kind="KSEI_SITE_SEARCH",
                request_key=f"{query_id}:page:{page_number}",
            )
            for row in attempts:
                row["query_text"] = query
                row["page_number"] = page_number
            request_records.extend(attempts)
            if payload is None:
                failed_search_queries += 1
                ended = True
                break
            try:
                results, next_url = parse_search_page(payload, base_url=provider["base_url"])
            except Exception as exc:
                search_parse_failures += 1
                request_records.append(
                    {
                        "request_kind": "KSEI_SITE_SEARCH_PARSE",
                        "request_key": f"{query_id}:page:{page_number}",
                        "attempt": 0,
                        "requested_url": current_url,
                        "accessed_at_utc": base.utc_now(),
                        "status_code": 200,
                        "bytes": len(payload),
                        "sha256": base.sha256_bytes(payload),
                        "path": "",
                        "error": f"{type(exc).__name__}:{exc}",
                        "query_text": query,
                        "page_number": page_number,
                    }
                )
                ended = True
                break

            for result in results:
                if not is_ksei_news_url(result.url):
                    raise RuntimeError(f"NON_KSEI_NEWS_RESULT_ADMITTED:{result.url}")
                search_rows.append(
                    {
                        "query_text": query,
                        "query_id": query_id,
                        "page_number": page_number,
                        "search_url": current_url,
                        "news_url": result.url,
                        "title": result.title,
                        "snippet": result.snippet,
                    }
                )
                for event_id, ticker in sorted(query_to_events[query]):
                    article_to_events[result.url].add((event_id, ticker))
                    event = census[
                        census["event_id"].eq(event_id) & census["ticker"].eq(ticker)
                    ].iloc[0]
                    event_news_rows.append(
                        {
                            "event_id": event_id,
                            "ticker": ticker,
                            "source_type": event["source_type"],
                            "failure_mode": event["failure_mode"],
                            "remediation_class": event["remediation_class"],
                            "query_text": query,
                            "news_url": result.url,
                            "search_result_title": result.title,
                            "search_result_snippet": result.snippet,
                        }
                    )

            if next_url is None:
                ended = True
                break
            if not is_ksei_search_url(next_url):
                raise RuntimeError(f"NON_KSEI_SEARCH_NEXT_URL:{next_url}")
            current_url = next_url
            time.sleep(base.INTER_REQUEST_SLEEP)

        if not ended:
            search_pagination_truncated += 1

    search_frame = pd.DataFrame(search_rows)
    if search_frame.empty:
        search_frame = pd.DataFrame(
            columns=["query_text", "query_id", "page_number", "search_url", "news_url", "title", "snippet"]
        )
    else:
        search_frame = search_frame.drop_duplicates().sort_values(
            ["query_text", "page_number", "news_url"], kind="mergesort"
        ).reset_index(drop=True)
    search_frame.to_csv(search_results_path, index=False, lineterminator="\n")

    event_news_frame = pd.DataFrame(event_news_rows)
    if event_news_frame.empty:
        event_news_frame = pd.DataFrame(
            columns=[
                "event_id", "ticker", "source_type", "failure_mode", "remediation_class",
                "query_text", "news_url", "search_result_title", "search_result_snippet"
            ]
        )
    else:
        event_news_frame = event_news_frame.drop_duplicates().sort_values(
            ["ticker", "event_id", "news_url", "query_text"], kind="mergesort"
        ).reset_index(drop=True)
    event_news_frame.to_csv(event_news_path, index=False, lineterminator="\n")

    # Capture each discovered official KSEI News page once. No semantic
    # admission occurs; exact ticker hits are diagnostics only.
    article_rows: list[dict[str, Any]] = []
    event_attachment_rows: list[dict[str, Any]] = []
    attachment_to_events: dict[str, set[tuple[str, str]]] = defaultdict(set)
    provider_failed_articles = 0
    news_parse_failures = 0
    for news_url in sorted(article_to_events):
        aid = article_id(news_url)
        prefix = news_raw / f"news_{safe_name(aid)}"
        payload, attempts = base.capture_request(
            session,
            url=news_url,
            raw_path_prefix=prefix,
            timeout_seconds=timeout,
            request_kind="KSEI_NEWS_ARTICLE",
            request_key=aid,
        )
        for row in attempts:
            row["linked_event_keys"] = "|".join(
                f"{event_id}:{ticker}" for event_id, ticker in sorted(article_to_events[news_url])
            )
        request_records.extend(attempts)
        if payload is None:
            provider_failed_articles += 1
            article_rows.append(
                {
                    "news_url": news_url,
                    "article_id": aid,
                    "source_sha256": "",
                    "parse_status": "UNRESOLVED_PROVIDER",
                    "title": "",
                    "linked_event_count": len(article_to_events[news_url]),
                    "linked_event_keys": "|".join(
                        f"{event_id}:{ticker}" for event_id, ticker in sorted(article_to_events[news_url])
                    ),
                    "exact_ticker_hits": "",
                    "attachment_count": 0,
                    "diagnostics": "PROVIDER_FAILED",
                }
            )
            continue
        digest = base.sha256_bytes(payload)
        try:
            title, body, attachments = parse_news_page(payload, page_url=news_url)
            hits = sorted(
                ticker
                for _, ticker in article_to_events[news_url]
                if exact_ticker_token(f"{title}\n{body}", ticker)
            )
            article_rows.append(
                {
                    "news_url": news_url,
                    "article_id": aid,
                    "source_sha256": digest,
                    "parse_status": "PARSED",
                    "title": title,
                    "linked_event_count": len(article_to_events[news_url]),
                    "linked_event_keys": "|".join(
                        f"{event_id}:{ticker}" for event_id, ticker in sorted(article_to_events[news_url])
                    ),
                    "exact_ticker_hits": "|".join(sorted(set(hits))),
                    "attachment_count": len(attachments),
                    "diagnostics": "",
                }
            )
            for attachment_url in attachments:
                if not is_ksei_attachment_url(attachment_url):
                    raise RuntimeError(f"NON_KSEI_ATTACHMENT_DISCOVERED:{attachment_url}")
                for event_key in article_to_events[news_url]:
                    attachment_to_events[attachment_url].add(event_key)
                    event_attachment_rows.append(
                        {
                            "event_id": event_key[0],
                            "ticker": event_key[1],
                            "news_url": news_url,
                            "attachment_url": attachment_url,
                        }
                    )
        except Exception as exc:
            news_parse_failures += 1
            article_rows.append(
                {
                    "news_url": news_url,
                    "article_id": aid,
                    "source_sha256": digest,
                    "parse_status": "UNRESOLVED_PARSE",
                    "title": "",
                    "linked_event_count": len(article_to_events[news_url]),
                    "linked_event_keys": "|".join(
                        f"{event_id}:{ticker}" for event_id, ticker in sorted(article_to_events[news_url])
                    ),
                    "exact_ticker_hits": "",
                    "attachment_count": 0,
                    "diagnostics": f"{type(exc).__name__}:{exc}",
                }
            )
        time.sleep(base.INTER_REQUEST_SLEEP)

    article_frame = pd.DataFrame(article_rows)
    if article_frame.empty:
        article_frame = pd.DataFrame(
            columns=[
                "news_url", "article_id", "source_sha256", "parse_status", "title",
                "linked_event_count", "linked_event_keys", "exact_ticker_hits",
                "attachment_count", "diagnostics"
            ]
        )
    else:
        article_frame = article_frame.drop_duplicates().sort_values(
            ["news_url", "source_sha256"], kind="mergesort"
        ).reset_index(drop=True)
    article_frame.to_csv(article_path, index=False, lineterminator="\n")

    event_attachment_frame = pd.DataFrame(event_attachment_rows)
    if event_attachment_frame.empty:
        event_attachment_frame = pd.DataFrame(
            columns=["event_id", "ticker", "news_url", "attachment_url"]
        )
    else:
        event_attachment_frame = event_attachment_frame.drop_duplicates().sort_values(
            ["ticker", "event_id", "attachment_url", "news_url"], kind="mergesort"
        ).reset_index(drop=True)
    event_attachment_frame.to_csv(event_attachment_path, index=False, lineterminator="\n")

    attachment_rows: list[dict[str, Any]] = []
    provider_failed_attachments = 0
    for index, attachment_url in enumerate(sorted(attachment_to_events), start=1):
        parsed = urlparse(attachment_url)
        filename = Path(parsed.path).name or f"attachment_{index}"
        prefix = attachment_raw / f"{index:04d}_{safe_name(filename)}"
        payload, attempts = base.capture_request(
            session,
            url=attachment_url,
            raw_path_prefix=prefix,
            timeout_seconds=timeout,
            request_kind="KSEI_NEWS_ATTACHMENT",
            request_key=hashlib.sha256(attachment_url.encode("utf-8")).hexdigest()[:20],
        )
        for row in attempts:
            row["linked_event_keys"] = "|".join(
                f"{event_id}:{ticker}" for event_id, ticker in sorted(attachment_to_events[attachment_url])
            )
        request_records.extend(attempts)
        if payload is None:
            provider_failed_attachments += 1
            attachment_rows.append(
                {
                    "attachment_url": attachment_url,
                    "source_sha256": "",
                    "bytes": 0,
                    "linked_event_count": len(attachment_to_events[attachment_url]),
                    "linked_event_keys": "|".join(
                        f"{event_id}:{ticker}" for event_id, ticker in sorted(attachment_to_events[attachment_url])
                    ),
                    "status": "UNRESOLVED_PROVIDER",
                }
            )
        else:
            attachment_rows.append(
                {
                    "attachment_url": attachment_url,
                    "source_sha256": base.sha256_bytes(payload),
                    "bytes": len(payload),
                    "linked_event_count": len(attachment_to_events[attachment_url]),
                    "linked_event_keys": "|".join(
                        f"{event_id}:{ticker}" for event_id, ticker in sorted(attachment_to_events[attachment_url])
                    ),
                    "status": "CAPTURED",
                }
            )
        time.sleep(base.INTER_REQUEST_SLEEP)

    attachment_frame = pd.DataFrame(attachment_rows)
    if attachment_frame.empty:
        attachment_frame = pd.DataFrame(
            columns=["attachment_url", "source_sha256", "bytes", "linked_event_count", "linked_event_keys", "status"]
        )
    else:
        attachment_frame = attachment_frame.sort_values("attachment_url", kind="mergesort").reset_index(drop=True)
    attachment_frame.to_csv(attachment_path, index=False, lineterminator="\n")
    write_jsonl(request_path, request_records)

    events_with_news = set(zip(event_news_frame["event_id"], event_news_frame["ticker"])) if len(event_news_frame) else set()
    events_with_ticker_evidenced_news: set[tuple[str, str]] = set()
    if len(article_frame):
        for row in article_frame.itertuples(index=False):
            hits = set(clean(row.exact_ticker_hits).split("|")) if clean(row.exact_ticker_hits) else set()
            for event_id, ticker in article_to_events.get(str(row.news_url), set()):
                if ticker in hits:
                    events_with_ticker_evidenced_news.add((event_id, ticker))

    raw_identity = request_identity(request_records)
    status = "V4_3_CA_SCHEDULE_59_KSEI_NEWS_ACQUISITION_COMPLETE"
    summary = {
        "schema_version": "v4_3_ca_training_domain_schedule_59_ksei_news_result_v1",
        "status": status,
        "outcome_blind": True,
        "provider_calls": True,
        "network_calls": True,
        "provider": provider["name"],
        "source_substitution": False,
        "external_search_engine": False,
        "semantic_admission_performed": False,
        "pass_preserving_subset_selection": False,
        "target_or_rank_materialized": False,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "scientific_config_changed": False,
        "residual_events": 59,
        "residual_event_identity_sha256": event_identity,
        "search_queries": int(len(query_to_events)),
        "search_query_event_links": int(len(query_scope)),
        "failed_search_queries": int(failed_search_queries),
        "search_parse_failures": int(search_parse_failures),
        "search_pagination_truncated_queries": int(search_pagination_truncated),
        "search_pagination_cycles": int(search_pagination_cycles),
        "unique_ksei_news_results": int(search_frame["news_url"].nunique()) if len(search_frame) else 0,
        "events_with_ksei_news_candidate": int(len(events_with_news)),
        "events_without_ksei_news_candidate": int(59 - len(events_with_news)),
        "events_with_ticker_evidenced_news": int(len(events_with_ticker_evidenced_news)),
        "unique_news_articles_requested": int(len(article_to_events)),
        "provider_failed_news_articles": int(provider_failed_articles),
        "news_parse_failures": int(news_parse_failures),
        "unique_news_attachments_requested": int(len(attachment_to_events)),
        "provider_failed_news_attachments": int(provider_failed_attachments),
        "successful_raw_response_identity_sha256": raw_identity,
        "next": "FREEZE_RAW_KSEI_NEWS_CORPUS_AND_RUN_OFFLINE_SEMANTIC_ADJUDICATION",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_hashes = {
        "frozen_residual_scope": sha256_file(scope_path),
        "frozen_search_query_scope": sha256_file(query_path),
        "search_news_results": sha256_file(search_results_path),
        "event_news_candidate_links": sha256_file(event_news_path),
        "news_article_inventory": sha256_file(article_path),
        "event_attachment_candidate_links": sha256_file(event_attachment_path),
        "news_attachment_inventory": sha256_file(attachment_path),
        "request_records": sha256_file(request_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_schedule_59_ksei_news_manifest_v1",
        "status": status,
        "outcome_blind": True,
        "immutable_inputs": {
            **diagnosis_hashes,
            "residual_event_identity_sha256": event_identity,
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
                "residual_event_identity_sha256": event_identity,
                "search_queries": summary["search_queries"],
                "failed_search_queries": failed_search_queries,
                "search_parse_failures": search_parse_failures,
                "search_pagination_truncated_queries": search_pagination_truncated,
                "unique_ksei_news_results": summary["unique_ksei_news_results"],
                "events_with_ksei_news_candidate": summary["events_with_ksei_news_candidate"],
                "events_without_ksei_news_candidate": summary["events_without_ksei_news_candidate"],
                "events_with_ticker_evidenced_news": summary["events_with_ticker_evidenced_news"],
                "unique_news_articles_requested": summary["unique_news_articles_requested"],
                "provider_failed_news_articles": provider_failed_articles,
                "news_parse_failures": news_parse_failures,
                "unique_news_attachments_requested": summary["unique_news_attachments_requested"],
                "provider_failed_news_attachments": provider_failed_attachments,
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
