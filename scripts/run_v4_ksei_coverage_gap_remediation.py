"""Targeted official-KSEI recovery for the exact 43 V4 CA history gaps.

The parent 610-ticker census remains immutable.  This runner verifies its exact
bytes, diagnoses the prior request failures, then contacts only the frozen 43
unresolved registered-security URLs.  It uses the unchanged strict KSEI
history parser and emits an append-only logical overlay plus merged census view.

No return, target, model, prediction, performance, or protected-forward data is
loaded or produced.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Mapping

import pandas as pd

from idx_trade.v4_ksei_ca_history import (
    KseiHistoryParseError,
    MECHANICAL_FAMILIES,
    is_active_status,
    parse_ksei_security_history,
    row_dates,
)
from idx_trade.v4_ksei_coverage_gap import (
    merge_coverage,
    merge_history,
    parent_failure_summary,
    read_jsonl,
    sha256_bytes,
    sha256_file,
    ticker_identity_sha256,
    validate_parent_coverage,
    write_jsonl,
)


DEFAULT_CONFIG = Path("config/v4_ksei_coverage_gap_remediation_v1.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"CONFIG_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "v4_ksei_coverage_gap_remediation_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if value.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    return value


def verify_file(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise RuntimeError(f"REQUIRED_PARENT_FILE_MISSING:{label}:{path}")
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"PARENT_HASH_MISMATCH:{label}:{actual}")
    return actual


def make_session(config: Mapping[str, Any]) -> Any:
    try:
        from curl_cffi import requests as curl_requests
    except ImportError as exc:  # pragma: no cover - local provider runtime
        raise RuntimeError("CURL_CFFI_REQUIRED_FOR_FROZEN_KSEI_TRANSPORT") from exc
    session = curl_requests.Session(impersonate=str(config["impersonate"]))
    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": str(config["home"]),
            "User-Agent": "Mozilla/5.0",
        }
    )
    return session


def capture_response(
    response: Any,
    *,
    path: Path,
    ticker: str,
    request_kind: str,
    attempt: int,
    requested_url: str,
) -> dict[str, Any]:
    payload = bytes(getattr(response, "content", b"") or b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "ticker": ticker,
        "request_kind": request_kind,
        "attempt": attempt,
        "requested_url": requested_url,
        "final_url": str(getattr(response, "url", requested_url)),
        "accessed_at_utc": utc_now(),
        "status_code": int(getattr(response, "status_code", 0) or 0),
        "content_type": str(getattr(response, "headers", {}).get("content-type", "")),
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
        "path": str(path),
    }


def error_record(
    *,
    ticker: str,
    request_kind: str,
    attempt: int,
    requested_url: str,
    exc: Exception,
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "request_kind": request_kind,
        "attempt": attempt,
        "requested_url": requested_url,
        "final_url": requested_url,
        "accessed_at_utc": utc_now(),
        "status_code": 0,
        "content_type": "",
        "bytes": 0,
        "sha256": None,
        "path": None,
        "error": f"{type(exc).__name__}:{exc}",
    }


def date_bounds(rows: tuple[dict[str, Any], ...]) -> tuple[str | None, str | None]:
    dates = sorted(date for row in rows for date in row_dates(row))
    return (dates[0], dates[-1]) if dates else (None, None)


def failure_class(records: list[dict[str, Any]]) -> str:
    errors = " | ".join(str(row.get("error") or "") for row in records).casefold()
    statuses = [int(row.get("status_code") or 0) for row in records]
    sizes = [int(row.get("bytes") or 0) for row in records]
    if "short-code identity mismatch" in errors:
        return "PARSE_IDENTITY_MISMATCH"
    if "corporate action table" in errors or "malformed corporate action row" in errors:
        return "PARSE_TABLE_STRUCTURE"
    if "invalid ksei html" in errors:
        return "PARSE_INVALID_HTML"
    if any(status not in {0, 200} for status in statuses) or any(
        status == 200 and size <= 0 for status, size in zip(statuses, sizes)
    ):
        return "HTTP_NON_200_OR_EMPTY"
    if statuses and all(status == 0 for status in statuses):
        return "NETWORK_OR_TRANSPORT"
    return "OTHER_UNRESOLVED"


def recover_ticker(
    *,
    ticker: str,
    provider: Mapping[str, Any],
    raw_root: Path,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], tuple[dict[str, Any], ...]]:
    session = make_session(provider)
    records: list[dict[str, Any]] = []
    security_url = str(provider["security_url_template"]).format(ticker=ticker)
    timeout = float(provider["timeout_seconds"])
    try:
        # A fresh session and exact-origin warmup are the only transport change
        # relative to the original 610-ticker census.  No alternate URL/source.
        try:
            home = session.get(str(provider["home"]), timeout=timeout)
            home_record = capture_response(
                home,
                path=raw_root / ticker / "home_attempt_01.html",
                ticker=ticker,
                request_kind="HOME_WARMUP",
                attempt=1,
                requested_url=str(provider["home"]),
            )
            records.append(home_record)
            if home_record["status_code"] != 200 or home_record["bytes"] <= 0:
                home_record["error"] = (
                    f"HTTP_OR_EMPTY:{home_record['status_code']}:{home_record['bytes']}"
                )
                return None, records, tuple()
        except Exception as exc:
            records.append(
                error_record(
                    ticker=ticker,
                    request_kind="HOME_WARMUP",
                    attempt=1,
                    requested_url=str(provider["home"]),
                    exc=exc,
                )
            )
            return None, records, tuple()

        max_attempts = int(provider["max_security_attempts_per_ticker"])
        backoff = [float(value) for value in provider.get("backoff_seconds", [])]
        for attempt in range(1, max_attempts + 1):
            try:
                response = session.get(security_url, timeout=timeout)
                record = capture_response(
                    response,
                    path=raw_root / ticker / f"security_attempt_{attempt:02d}.html",
                    ticker=ticker,
                    request_kind="SECURITY_HISTORY",
                    attempt=attempt,
                    requested_url=security_url,
                )
                records.append(record)
                if record["status_code"] != 200 or record["bytes"] <= 0:
                    raise RuntimeError(
                        f"HTTP_OR_EMPTY:{record['status_code']}:{record['bytes']}"
                    )
                parsed = parse_ksei_security_history(
                    response.content,
                    expected_ticker=ticker,
                    source_url=record["final_url"],
                    source_sha256=record["sha256"],
                )
                return record, records, parsed.rows
            except Exception as exc:
                if records and records[-1].get("request_kind") == "SECURITY_HISTORY" and records[-1].get("attempt") == attempt:
                    records[-1]["error"] = f"{type(exc).__name__}:{exc}"
                else:
                    records.append(
                        error_record(
                            ticker=ticker,
                            request_kind="SECURITY_HISTORY",
                            attempt=attempt,
                            requested_url=security_url,
                            exc=exc,
                        )
                    )
                if attempt < max_attempts and backoff:
                    time.sleep(backoff[min(attempt - 1, len(backoff) - 1)])
        return None, records, tuple()
    finally:
        close = getattr(session, "close", None)
        if callable(close):
            close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-census-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    config = load_config(args.config)
    parent_cfg = config["parent_census"]
    provider = config["provider"]
    gap_tickers = [str(value).upper() for value in config["gap_tickers"]]
    if len(gap_tickers) != 43 or len(set(gap_tickers)) != 43:
        raise RuntimeError("FROZEN_GAP_TICKER_COUNT_CHANGED")
    if ticker_identity_sha256(gap_tickers) != config["gap_ticker_identity_sha256"]:
        raise RuntimeError("FROZEN_GAP_TICKER_IDENTITY_HASH_CHANGED")
    if provider.get("source_substitution") is not False or provider.get("parser_relaxation") is not False:
        raise RuntimeError("PROVIDER_POLICY_NOT_FAIL_CLOSED")
    if provider.get("fresh_session_per_ticker") is not True or provider.get("home_warmup_per_ticker") is not True:
        raise RuntimeError("TRANSPORT_REMEDIATION_POLICY_CHANGED")

    parent_paths = {
        "manifest": args.parent_census_root / "MANIFEST.json",
        "summary": args.parent_census_root / "summary.json",
        "ticker_coverage": args.parent_census_root / "ticker_coverage.csv",
        "ksei_ca_history": args.parent_census_root / "ksei_ca_history.jsonl",
        "request_records": args.parent_census_root / "request_records.jsonl",
    }
    expected_hashes = {
        "manifest": parent_cfg["manifest_sha256"],
        "summary": parent_cfg["summary_sha256"],
        "ticker_coverage": parent_cfg["ticker_coverage_sha256"],
        "ksei_ca_history": parent_cfg["ksei_ca_history_sha256"],
        "request_records": parent_cfg["request_records_sha256"],
    }
    parent_hashes = {
        label: verify_file(path, expected_hashes[label], label)
        for label, path in parent_paths.items()
    }

    parent_coverage = validate_parent_coverage(
        pd.read_csv(parent_paths["ticker_coverage"]),
        gap_tickers=gap_tickers,
        expected_tickers=int(parent_cfg["expected_tickers"]),
        expected_certified=int(parent_cfg["expected_certified"]),
        expected_unresolved=int(parent_cfg["expected_unresolved"]),
    )
    parent_history = read_jsonl(parent_paths["ksei_ca_history"])
    parent_requests = read_jsonl(parent_paths["request_records"])
    parent_diag = parent_failure_summary(parent_requests, gap_tickers=gap_tickers)

    # Only after every immutable parent assertion passes do we consume the
    # one-shot fresh output root and begin provider work.
    args.output_dir.mkdir(parents=True)
    raw_root = args.output_dir / "raw"
    raw_root.mkdir()
    parent_diag_path = args.output_dir / "parent_failure_diagnostic.csv"
    parent_diag.to_csv(parent_diag_path, index=False, lineterminator="\n")

    request_delta: list[dict[str, Any]] = []
    recovered_history: list[dict[str, Any]] = []
    coverage_delta_rows: list[dict[str, Any]] = []
    recovery_result_rows: list[dict[str, Any]] = []
    parent_by_ticker = parent_coverage.set_index("ticker", drop=False)

    for index, ticker in enumerate(gap_tickers, start=1):
        success, records, parsed_rows = recover_ticker(
            ticker=ticker,
            provider=provider,
            raw_root=raw_root,
        )
        request_delta.extend(records)
        parent_row = parent_by_ticker.loc[ticker].to_dict()
        security_records = [row for row in records if row.get("request_kind") == "SECURITY_HISTORY"]
        earliest, latest = date_bounds(parsed_rows)
        active_rows = [row for row in parsed_rows if is_active_status(row["status"])]
        active_mechanical = [row for row in active_rows if row["event_family"] in MECHANICAL_FAMILIES]
        active_unknown = [row for row in active_rows if row["event_family"] == "UNKNOWN"]

        if success is not None:
            logical = dict(parent_row)
            logical.update(
                {
                    "coverage_status": "COVERAGE_CERTIFIED",
                    "coverage_certified": True,
                    "attempt_count": len(security_records),
                    "final_http_status": int(success["status_code"]),
                    "source_url": success["final_url"],
                    "source_sha256": success["sha256"],
                    "ca_rows": len(parsed_rows),
                    "active_ca_rows": len(active_rows),
                    "active_mechanical_rows": len(active_mechanical),
                    "active_unknown_rows": len(active_unknown),
                    "earliest_ca_date": earliest,
                    "latest_ca_date": latest,
                    "failure_reason": "",
                }
            )
            recovered_history.extend(parsed_rows)
            recovery_status = "RECOVERED_STRICT_PARSE"
            final_failure_class = ""
        else:
            logical = dict(parent_row)
            recovery_status = "STILL_UNRESOLVED"
            final_failure_class = failure_class(records)

        coverage_delta_rows.append(logical)
        parent_diag_row = parent_diag[parent_diag["ticker"].eq(ticker)].iloc[0]
        recovery_result_rows.append(
            {
                "ticker": ticker,
                "parent_dominant_failure_class": parent_diag_row["parent_dominant_failure_class"],
                "recovery_status": recovery_status,
                "recovery_failure_class": final_failure_class,
                "home_attempts": sum(row.get("request_kind") == "HOME_WARMUP" for row in records),
                "security_attempts": len(security_records),
                "final_http_status": int(success["status_code"]) if success else int(security_records[-1].get("status_code") or 0) if security_records else 0,
                "ca_rows": len(parsed_rows),
                "active_mechanical_rows": len(active_mechanical),
                "active_unknown_rows": len(active_unknown),
                "source_sha256": success["sha256"] if success else "",
            }
        )
        print(f"[{index:02d}/43] {ticker}: {recovery_status}", flush=True)
        if index < len(gap_tickers) and float(provider["inter_ticker_sleep_seconds"]) > 0:
            time.sleep(float(provider["inter_ticker_sleep_seconds"]))

    coverage_delta = pd.DataFrame(coverage_delta_rows, columns=parent_coverage.columns)
    coverage_delta["coverage_certified"] = coverage_delta["coverage_certified"].astype(bool)
    merged_coverage = merge_coverage(parent_coverage, coverage_delta, gap_tickers=gap_tickers)
    merged_history = merge_history(parent_history, recovered_history, gap_tickers=gap_tickers)

    recovery_results = pd.DataFrame(recovery_result_rows).sort_values("ticker", kind="mergesort")
    recovered_tickers = sorted(recovery_results.loc[recovery_results["recovery_status"].eq("RECOVERED_STRICT_PARSE"), "ticker"])
    remaining_tickers = sorted(set(gap_tickers) - set(recovered_tickers))
    if int(merged_coverage["coverage_certified"].sum()) != 567 + len(recovered_tickers):
        raise RuntimeError("MERGED_COVERAGE_CERTIFIED_COUNT_INCONSISTENT")

    recovery_path = args.output_dir / "coverage_gap_results.csv"
    coverage_delta_path = args.output_dir / "coverage_gap_logical_rows.csv"
    request_delta_path = args.output_dir / "request_records_delta.jsonl"
    recovered_history_path = args.output_dir / "recovered_history_delta.jsonl"
    merged_coverage_path = args.output_dir / "ticker_coverage.csv"
    merged_history_path = args.output_dir / "ksei_ca_history.jsonl"
    recovery_results.to_csv(recovery_path, index=False, lineterminator="\n")
    coverage_delta.to_csv(coverage_delta_path, index=False, lineterminator="\n")
    write_jsonl(request_delta_path, request_delta)
    write_jsonl(recovered_history_path, recovered_history)
    merged_coverage.to_csv(merged_coverage_path, index=False, lineterminator="\n")
    write_jsonl(merged_history_path, merged_history)

    merged_history_frame = pd.DataFrame(merged_history)
    if merged_history_frame.empty:
        active_mechanical_or_unknown = pd.DataFrame()
    else:
        active = merged_history_frame[
            merged_history_frame["status"].astype(str).str.strip().str.casefold().eq("active")
        ]
        active_mechanical_or_unknown = active[
            active["event_family"].isin(MECHANICAL_FAMILIES)
            | active["event_family"].eq("UNKNOWN")
        ].copy()
    active_path = args.output_dir / "active_mechanical_or_unknown_events.csv"
    active_mechanical_or_unknown.to_csv(active_path, index=False, lineterminator="\n")

    status = (
        "V4_KSEI_COVERAGE_GAP_REMEDIATION_COMPLETE_ALL_43_RECOVERED"
        if not remaining_tickers
        else "V4_KSEI_COVERAGE_GAP_REMEDIATION_COMPLETE_WITH_REMAINING_GAPS"
    )
    output_hashes = {
        "parent_failure_diagnostic": sha256_file(parent_diag_path),
        "coverage_gap_results": sha256_file(recovery_path),
        "coverage_gap_logical_rows": sha256_file(coverage_delta_path),
        "request_records_delta": sha256_file(request_delta_path),
        "recovered_history_delta": sha256_file(recovered_history_path),
        "ticker_coverage": sha256_file(merged_coverage_path),
        "ksei_ca_history": sha256_file(merged_history_path),
        "active_mechanical_or_unknown_events": sha256_file(active_path),
    }
    summary = {
        "schema_version": "v4_ksei_coverage_gap_remediation_v1",
        "status": status,
        "policy_id": config["policy_id"],
        "outcome_blind": True,
        "provider": provider["name"],
        "provider_calls": True,
        "source_substitution": False,
        "parser_relaxation": False,
        "full_610_recrawl": False,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "parent_hashes": parent_hashes,
        "config_sha256": sha256_file(args.config),
        "gap_ticker_count": 43,
        "gap_ticker_identity_sha256": config["gap_ticker_identity_sha256"],
        "recovered_tickers": recovered_tickers,
        "recovered_ticker_count": len(recovered_tickers),
        "remaining_unresolved_tickers": remaining_tickers,
        "remaining_unresolved_ticker_count": len(remaining_tickers),
        "merged_coverage_certified_tickers": int(merged_coverage["coverage_certified"].sum()),
        "merged_coverage_unresolved_tickers": int((~merged_coverage["coverage_certified"]).sum()),
        "parent_history_rows": len(parent_history),
        "recovered_history_rows": len(recovered_history),
        "merged_history_rows": len(merged_history),
        "recovered_active_mechanical_or_unknown_rows": int(
            sum(
                is_active_status(row.get("status"))
                and row.get("event_family") in (MECHANICAL_FAMILIES | {"UNKNOWN"})
                for row in recovered_history
            )
        ),
        "output_hashes": output_hashes,
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ksei_coverage_gap_remediation_manifest_v1",
        "created_at_utc": utc_now(),
        "status": status,
        "outcome_blind": True,
        "provider_calls": True,
        "parent_hashes": parent_hashes,
        "config_sha256": sha256_file(args.config),
        "summary_sha256": sha256_file(summary_path),
        "output_hashes": output_hashes,
        "raw_capture_count": sum(1 for path in raw_root.rglob("*.html") if path.is_file()),
        "raw_capture_bytes": sum(path.stat().st_size for path in raw_root.rglob("*.html") if path.is_file()),
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": status,
                "recovered": len(recovered_tickers),
                "remaining": len(remaining_tickers),
                "new_active_mechanical_or_unknown": summary["recovered_active_mechanical_or_unknown_rows"],
                "manifest_sha256": sha256_file(manifest_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
