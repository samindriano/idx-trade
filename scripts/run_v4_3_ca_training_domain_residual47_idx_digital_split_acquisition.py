"""Acquire frozen official IDX Digital Statistic stock-split evidence for residual 47 CA events.

Outcome-blind provider stage only.  It never admits event semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.ranking_v4_3_ca_schedule_reuse import event_inventory_identity  # noqa: E402
from idx_trade.v4_3_ca_residual47_idx_digital_split import (  # noqa: E402
    clean,
    month_scope,
    normalize_split_row,
    parse_source_dates,
    ticker,
)

DEFAULT_CONFIG = REPO_ROOT / "config" / "v4_3_ca_training_domain_residual47_idx_digital_split_v1.json"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--combined-replay-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "v4_3_ca_training_domain_residual47_idx_digital_split_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    hard = config.get("hard_boundaries") or {}
    for key, value in hard.items():
        if value is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")


def verify_parent(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    expected = config["parent_combined_replay"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    audit_path = root / "v4_3_ca_training_event_semantics_idx_combined.csv"
    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(f"PARENT_MANIFEST_SHA_MISMATCH:{actual_manifest}")
    manifest = read_json(manifest_path, "PARENT_MANIFEST")
    summary = read_json(summary_path, "PARENT_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("PARENT_STATUS_CHANGED")
    if summary.get("historical_target_loaded") is not False or summary.get("model_fit") is not False:
        raise RuntimeError("PARENT_OUTCOME_GUARD_CHANGED")
    if int(summary.get("combined_remaining_schedule_events", -1)) != int(expected["remaining_schedule_events"]):
        raise RuntimeError("PARENT_RESIDUAL_COUNT_CHANGED")
    outputs = manifest.get("output_hashes") or {}
    expected_audit = clean(outputs.get("event_audit"))
    expected_summary = clean(outputs.get("summary"))
    if sha256_file(audit_path) != expected_audit:
        raise RuntimeError("PARENT_EVENT_AUDIT_SHA_CHANGED")
    if sha256_file(summary_path) != expected_summary:
        raise RuntimeError("PARENT_SUMMARY_SHA_CHANGED")
    audit = pd.read_csv(audit_path, dtype=str, keep_default_na=False)
    residual = audit[audit["semantic_class"].astype(str).eq("SCHEDULE_REQUIRED")].copy()
    if len(residual) != int(expected["remaining_schedule_events"]):
        raise RuntimeError(f"PARENT_RESIDUAL_SCOPE_CHANGED:{len(residual)}")
    residual["event_id"] = residual["event_id"].map(clean)
    residual["ticker"] = residual["ticker"].map(ticker)
    residual = residual.sort_values(["ticker", "event_id"], kind="mergesort").reset_index(drop=True)
    if residual.duplicated(["event_id", "ticker"]).any():
        raise RuntimeError("PARENT_RESIDUAL_IDENTITY_DUPLICATED")
    return residual, {
        "parent_manifest": actual_manifest,
        "parent_event_audit": sha256_file(audit_path),
        "parent_summary": sha256_file(summary_path),
    }


def make_session(config: dict[str, Any]) -> Any:
    try:
        from curl_cffi import requests as curl_requests
    except ImportError as exc:
        raise RuntimeError("CURL_CFFI_REQUIRED") from exc
    provider = config["provider"]
    session = curl_requests.Session(impersonate=provider["impersonate"])
    session.headers.update({"Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"})
    timeout = float(provider["timeout_seconds"])
    for url in provider["warmup_urls"]:
        try:
            session.get(url, timeout=timeout)
        except Exception:
            pass
    return session


def capture_json(
    session: Any,
    *,
    endpoint: str,
    params: dict[str, Any],
    raw_prefix: Path,
    config: dict[str, Any],
    request_key: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    provider = config["provider"]
    records: list[dict[str, Any]] = []
    for attempt in range(1, int(provider["max_attempts"]) + 1):
        row: dict[str, Any] = {
            "request_kind": "IDX_DIGITAL_STATISTIC_STOCK_SPLIT",
            "request_key": request_key,
            "attempt": attempt,
            "accessed_at_utc": pd.Timestamp.utcnow().isoformat(),
        }
        try:
            response = session.get(endpoint, params=params, timeout=float(provider["timeout_seconds"]))
            payload = bytes(getattr(response, "content", b"") or b"")
            path = Path(str(raw_prefix) + f"_attempt_{attempt:02d}.bin")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            row.update({
                "status_code": int(getattr(response, "status_code", 0) or 0),
                "content_type": clean(getattr(response, "headers", {}).get("content-type", "")),
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "path": str(path),
                "final_url": str(getattr(response, "url", endpoint)),
            })
            records.append(row)
            if row["status_code"] == 200 and payload:
                try:
                    parsed = json.loads(payload.decode("utf-8-sig"))
                except Exception:
                    row["error"] = "JSON_PARSE_FAILURE"
                else:
                    if isinstance(parsed, dict) and isinstance(parsed.get("data"), list):
                        return parsed, records
                    row["error"] = "JSON_SHAPE_INVALID"
            else:
                row["error"] = "HTTP_NON_200_OR_EMPTY"
        except Exception as exc:
            row.update({"status_code": 0, "bytes": 0, "sha256": "", "path": "", "error": f"{type(exc).__name__}:{exc}"})
            records.append(row)
        if attempt < int(provider["max_attempts"]):
            time.sleep(float(provider["backoff_seconds"][attempt - 1]))
    return None, records


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    config = read_json(args.config, "CONFIG")
    verify_config(config)
    residual, parent_hashes = verify_parent(args.combined_replay_root, config)

    radius = int(config["provider"]["month_radius"])
    event_months: dict[tuple[str, str], set[tuple[int, int]]] = {}
    query_months: set[tuple[int, int]] = set()
    for row in residual.to_dict("records"):
        dates = parse_source_dates(row.get("source_dates"))
        months = set(month_scope(dates, radius=radius))
        event_months[(row["event_id"], row["ticker"])] = months
        query_months.update(months)

    args.output_dir.mkdir(parents=True)
    raw_root = args.output_dir / "raw"
    raw_root.mkdir(parents=True)
    scope_path = args.output_dir / "frozen_residual_47_scope.csv"
    query_path = args.output_dir / "frozen_month_query_scope.csv"
    inventory_path = args.output_dir / "idx_digital_split_inventory.csv"
    links_path = args.output_dir / "event_idx_digital_split_candidate_links.csv"
    requests_path = args.output_dir / "request_records.jsonl"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"

    residual.to_csv(scope_path, index=False, lineterminator="\n")
    query_frame = pd.DataFrame([{"year": y, "month": m} for y, m in sorted(query_months)])
    query_frame.to_csv(query_path, index=False, lineterminator="\n")

    provider = config["provider"]
    session = make_session(config)
    endpoint = provider["base_url"].rstrip("/") + provider["endpoint"]
    request_records: list[dict[str, Any]] = []
    inventory_rows: list[dict[str, Any]] = []
    failed_queries = 0
    pages_requested = 0

    for year, month in sorted(query_months):
        for page in range(1, int(provider["max_pages_per_month"]) + 1):
            params = {
                "urlName": provider["url_name"],
                "periodYear": year,
                "periodMonth": month,
                "periodType": provider["period_type"],
                "isPrint": "False",
                "cumulative": "false",
                "pageSize": int(provider["page_size"]),
                "pageNumber": page,
            }
            parsed, records = capture_json(
                session,
                endpoint=endpoint,
                params=params,
                raw_prefix=raw_root / f"{year}_{month:02d}_p{page:02d}",
                config=config,
                request_key=f"{year}-{month:02d}:page:{page}",
            )
            request_records.extend(records)
            pages_requested += 1
            if parsed is None:
                failed_queries += 1
                break
            data = parsed.get("data") or []
            successful = next((r for r in reversed(records) if int(r.get("status_code") or 0) == 200 and not r.get("error")), None)
            source_sha = clean(successful.get("sha256")) if successful else ""
            source_url = clean(successful.get("final_url")) if successful else ""
            for item in data:
                if not isinstance(item, dict):
                    continue
                normalized = normalize_split_row(item)
                inventory_rows.append({
                    **normalized,
                    "period_year": year,
                    "period_month": month,
                    "source_sha256": source_sha,
                    "source_url": source_url,
                })
            total = parsed.get("recordsTotal")
            try:
                total_int = int(total)
            except Exception:
                total_int = len(data)
            if not data or page * int(provider["page_size"]) >= total_int:
                break
            time.sleep(float(provider["inter_request_sleep_seconds"]))
        time.sleep(float(provider["inter_request_sleep_seconds"]))

    inventory = pd.DataFrame(inventory_rows)
    if inventory.empty:
        inventory = pd.DataFrame(columns=[
            "ticker", "issuer_name", "action_type", "listing_date", "ratio", "old_nominal",
            "new_nominal", "listed_shares", "additional_shares", "row_identity_sha256",
            "period_year", "period_month", "source_sha256", "source_url",
        ])
    else:
        inventory = inventory.drop_duplicates(["row_identity_sha256", "source_sha256"]).sort_values(
            ["ticker", "listing_date", "row_identity_sha256"], kind="mergesort"
        ).reset_index(drop=True)
    inventory.to_csv(inventory_path, index=False, lineterminator="\n")

    link_rows: list[dict[str, Any]] = []
    for event in residual.to_dict("records"):
        event_key = (event["event_id"], event["ticker"])
        months = event_months[event_key]
        if inventory.empty:
            continue
        candidates = inventory[inventory["ticker"].eq(event["ticker"])].copy()
        candidates = candidates[candidates.apply(lambda r: (int(r["period_year"]), int(r["period_month"])) in months, axis=1)]
        for candidate in candidates.to_dict("records"):
            link_rows.append({
                "event_id": event["event_id"],
                "ticker": event["ticker"],
                "event_source_type": event.get("source_type", ""),
                "event_source_dates": event.get("source_dates", ""),
                **candidate,
            })
    links = pd.DataFrame(link_rows)
    if links.empty:
        links = pd.DataFrame(columns=[
            "event_id", "ticker", "event_source_type", "event_source_dates", "issuer_name",
            "action_type", "listing_date", "ratio", "old_nominal", "new_nominal", "listed_shares",
            "additional_shares", "row_identity_sha256", "period_year", "period_month",
            "source_sha256", "source_url",
        ])
    else:
        links = links.drop_duplicates(["event_id", "ticker", "row_identity_sha256", "source_sha256"]).sort_values(
            ["ticker", "event_id", "listing_date", "row_identity_sha256"], kind="mergesort"
        ).reset_index(drop=True)
    links.to_csv(links_path, index=False, lineterminator="\n")
    write_jsonl(requests_path, request_records)

    identity = event_inventory_identity(residual[["event_id", "ticker"]])
    event_candidates = set(zip(links["event_id"], links["ticker"])) if len(links) else set()
    summary = {
        "schema_version": "v4_3_ca_training_domain_residual47_idx_digital_split_acquisition_result_v1",
        "status": "V4_3_CA_RESIDUAL47_IDX_DIGITAL_SPLIT_ACQUISITION_COMPLETE",
        "outcome_blind": True,
        "network_calls": True,
        "provider_calls": True,
        "semantic_admission_performed": False,
        "residual_events": 47,
        "residual_event_identity_sha256": identity,
        "query_months": int(len(query_months)),
        "pages_requested": int(pages_requested),
        "failed_queries": int(failed_queries),
        "inventory_rows": int(len(inventory)),
        "candidate_links": int(len(links)),
        "events_with_candidate_rows": int(len(event_candidates)),
        "events_without_candidate_rows": int(47 - len(event_candidates)),
        "historical_target_loaded": False,
        "model_fit": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "next": "FREEZE_DIGITAL_SPLIT_CORPUS_AND_RUN_OFFLINE_ADJUDICATION",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_hashes = {
        "frozen_residual_scope": sha256_file(scope_path),
        "frozen_query_scope": sha256_file(query_path),
        "inventory": sha256_file(inventory_path),
        "candidate_links": sha256_file(links_path),
        "request_records": sha256_file(requests_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_residual47_idx_digital_split_acquisition_manifest_v1",
        "status": summary["status"],
        "outcome_blind": True,
        "immutable_inputs": {**parent_hashes, "residual_event_identity_sha256": identity},
        "output_hashes": output_hashes,
        "guardrails": config["hard_boundaries"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": summary["status"],
        "residual_events": 47,
        "query_months": summary["query_months"],
        "pages_requested": pages_requested,
        "failed_queries": failed_queries,
        "inventory_rows": summary["inventory_rows"],
        "candidate_links": summary["candidate_links"],
        "events_with_candidate_rows": summary["events_with_candidate_rows"],
        "events_without_candidate_rows": summary["events_without_candidate_rows"],
        "semantic_admission_performed": False,
        "historical_target_loaded": False,
        "model_fit": False,
        "performance_computed": False,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "next": summary["next"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
