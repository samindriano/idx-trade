"""Acquire an outcome-blind KSEI Corporate Action history census for V4.

The ticker population is derived only from the hash-pinned blocked V4 CA
continuity ledger.  The runner contacts public KSEI registered-security pages
and stores append-only raw HTML plus normalized CA history.  It never loads or
materializes V4 returns, ranks, predictions, models, or performance.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import pandas as pd

from idx_trade.v4_ksei_ca_history import (
    KseiHistoryParseError,
    MECHANICAL_FAMILIES,
    is_active_status,
    parse_ksei_security_history,
    row_dates,
)


PINNED_CONTINUITY_LEDGER_SHA256 = (
    "52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb"
)
EXPECTED_FROZEN_TICKERS = 610
KSEI_HOME = "https://web.ksei.co.id/"
KSEI_SECURITY = (
    "https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}"
    "?setLocale=en-US"
)
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 3.0)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_tickers(values: pd.Series) -> pd.Series:
    return (
        values.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def load_frozen_tickers(continuity_ledger: Path) -> list[str]:
    if not continuity_ledger.is_file():
        raise RuntimeError(f"CONTINUITY_LEDGER_MISSING:{continuity_ledger}")
    digest = sha256_file(continuity_ledger)
    if digest != PINNED_CONTINUITY_LEDGER_SHA256:
        raise RuntimeError(f"CONTINUITY_LEDGER_SHA_MISMATCH:{digest}")
    frame = pd.read_csv(continuity_ledger, usecols=["ticker"])
    frame["ticker"] = normalize_tickers(frame["ticker"])
    tickers = sorted(frame["ticker"].drop_duplicates().tolist())
    if len(tickers) != EXPECTED_FROZEN_TICKERS:
        raise RuntimeError(f"FROZEN_TICKER_COUNT_CHANGED:{len(tickers)}")
    if any(len(ticker) != 4 for ticker in tickers):
        raise RuntimeError("FROZEN_TICKER_IDENTITY_INVALID")
    return tickers


def make_session() -> Any:
    try:
        from curl_cffi import requests as curl_requests
    except ImportError as exc:  # pragma: no cover - local provider runtime
        raise RuntimeError(
            "CURL_CFFI_REQUIRED_FOR_FROZEN_KSEI_TRANSPORT"
        ) from exc
    session = curl_requests.Session(impersonate="chrome110")
    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": KSEI_HOME,
            "User-Agent": "Mozilla/5.0",
        }
    )
    return session


def capture_response(
    response: Any,
    *,
    path: Path,
    requested_url: str,
    ticker: str,
    attempt: int,
) -> dict[str, Any]:
    payload = bytes(getattr(response, "content", b"") or b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    digest = sha256_bytes(payload)
    return {
        "ticker": ticker,
        "attempt": attempt,
        "requested_url": requested_url,
        "final_url": str(getattr(response, "url", requested_url)),
        "accessed_at_utc": utc_now(),
        "status_code": int(getattr(response, "status_code", 0) or 0),
        "content_type": str(getattr(response, "headers", {}).get("content-type", "")),
        "bytes": len(payload),
        "sha256": digest,
        "path": str(path),
    }


def request_page(
    session: Any,
    *,
    url: str,
    ticker: str,
    raw_root: Path,
    timeout: float,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], tuple[dict[str, Any], ...]]:
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.get(url, timeout=timeout)
            raw_path = raw_root / ticker / f"attempt_{attempt:02d}.html"
            capture = capture_response(
                response,
                path=raw_path,
                requested_url=url,
                ticker=ticker,
                attempt=attempt,
            )
            attempts.append(capture)
            if capture["status_code"] != 200 or not capture["bytes"]:
                raise RuntimeError(
                    f"HTTP_OR_EMPTY:{capture['status_code']}:{capture['bytes']}"
                )
            parsed = parse_ksei_security_history(
                response.content,
                expected_ticker=ticker,
                source_url=capture["final_url"],
                source_sha256=capture["sha256"],
            )
            return capture, attempts, parsed.rows
        except (KseiHistoryParseError, RuntimeError, Exception) as exc:
            # Network/library exceptions are recorded as strings.  There is no
            # source substitution; retries use the same KSEI URL and transport.
            if attempts and "error" not in attempts[-1]:
                attempts[-1]["error"] = f"{type(exc).__name__}:{exc}"
            elif not attempts or attempts[-1].get("attempt") != attempt:
                attempts.append(
                    {
                        "ticker": ticker,
                        "attempt": attempt,
                        "requested_url": url,
                        "accessed_at_utc": utc_now(),
                        "status_code": 0,
                        "bytes": 0,
                        "sha256": None,
                        "path": None,
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS[attempt - 1])
    return None, attempts, tuple()


def date_bounds(rows: tuple[dict[str, Any], ...]) -> tuple[str | None, str | None]:
    dates = sorted(date for row in rows for date in row_dates(row))
    if not dates:
        return None, None
    return dates[0], dates[-1]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    if args.timeout_seconds <= 0 or args.sleep_seconds < 0:
        raise RuntimeError("INVALID_RUNTIME_TIMING_ARGUMENT")
    args.output_dir.mkdir(parents=True)
    raw_root = args.output_dir / "raw"
    raw_root.mkdir()

    tickers = load_frozen_tickers(args.continuity_ledger)
    session = make_session()
    request_records: list[dict[str, Any]] = []

    # Warm the exact public KSEI origin once before the per-security sequence.
    try:
        home = session.get(KSEI_HOME, timeout=args.timeout_seconds)
        home_path = raw_root / "_home" / "attempt_01.html"
        request_records.append(
            capture_response(
                home,
                path=home_path,
                requested_url=KSEI_HOME,
                ticker="_HOME",
                attempt=1,
            )
        )
        if request_records[-1]["status_code"] != 200:
            raise RuntimeError(
                f"KSEI_HOME_HTTP_{request_records[-1]['status_code']}"
            )
    except Exception as exc:
        raise RuntimeError(f"KSEI_HOME_WARMUP_FAILED:{exc}") from exc

    coverage_rows: list[dict[str, Any]] = []
    history_rows: list[dict[str, Any]] = []
    for index, ticker in enumerate(tickers, start=1):
        url = KSEI_SECURITY.format(ticker=ticker)
        success, attempts, parsed_rows = request_page(
            session,
            url=url,
            ticker=ticker,
            raw_root=raw_root,
            timeout=args.timeout_seconds,
        )
        request_records.extend(attempts)
        earliest, latest = date_bounds(parsed_rows)
        active_rows = [row for row in parsed_rows if is_active_status(row["status"])]
        active_mechanical = [
            row
            for row in active_rows
            if row["event_family"] in MECHANICAL_FAMILIES
        ]
        active_unknown = [
            row for row in active_rows if row["event_family"] == "UNKNOWN"
        ]
        coverage_rows.append(
            {
                "ticker": ticker,
                "coverage_status": (
                    "COVERAGE_CERTIFIED" if success is not None else "COVERAGE_UNRESOLVED"
                ),
                "coverage_certified": success is not None,
                "attempt_count": len(attempts),
                "final_http_status": int(success["status_code"]) if success else 0,
                "source_url": success["final_url"] if success else url,
                "source_sha256": success["sha256"] if success else None,
                "ca_rows": len(parsed_rows),
                "active_ca_rows": len(active_rows),
                "active_mechanical_rows": len(active_mechanical),
                "active_unknown_rows": len(active_unknown),
                "earliest_ca_date": earliest,
                "latest_ca_date": latest,
                "failure_reason": "" if success else "ALL_THREE_ATTEMPTS_FAILED_OR_UNPARSABLE",
            }
        )
        history_rows.extend(parsed_rows)
        if index < len(tickers) and args.sleep_seconds:
            time.sleep(args.sleep_seconds)

    coverage = pd.DataFrame(coverage_rows).sort_values("ticker", kind="mergesort")
    coverage_path = args.output_dir / "ticker_coverage.csv"
    coverage.to_csv(coverage_path, index=False, lineterminator="\n")

    history_path = args.output_dir / "ksei_ca_history.jsonl"
    write_jsonl(history_path, history_rows)

    history = pd.DataFrame(history_rows)
    if history.empty:
        mechanical = pd.DataFrame(
            columns=[
                "ticker",
                "event_family_source",
                "event_family",
                "cum_date",
                "record_date",
                "distribution_date",
                "status",
                "source_url",
                "source_sha256",
            ]
        )
    else:
        active = history[history["status"].astype(str).str.casefold().eq("active")]
        mechanical = active[
            active["event_family"].isin(MECHANICAL_FAMILIES)
            | active["event_family"].eq("UNKNOWN")
        ].copy()
    mechanical_path = args.output_dir / "active_mechanical_or_unknown_events.csv"
    mechanical.to_csv(mechanical_path, index=False, lineterminator="\n")

    request_manifest_path = args.output_dir / "request_records.jsonl"
    write_jsonl(request_manifest_path, request_records)

    summary = {
        "schema_version": "v4_ksei_ca_history_census_v1",
        "status": (
            "KSEI_610_HISTORY_CENSUS_COMPLETE"
            if bool(coverage["coverage_certified"].all())
            else "KSEI_610_HISTORY_CENSUS_COMPLETE_WITH_COVERAGE_GAPS"
        ),
        "outcome_blind": True,
        "provider": "KSEI_PUBLIC_REGISTERED_SECURITY_HISTORY",
        "provider_calls": True,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "ticker_count": len(tickers),
        "ticker_identity_sha256": sha256_bytes(
            ("\n".join(tickers) + "\n").encode("utf-8")
        ),
        "coverage_certified_tickers": int(coverage["coverage_certified"].sum()),
        "coverage_unresolved_tickers": int((~coverage["coverage_certified"]).sum()),
        "history_rows": len(history_rows),
        "active_mechanical_or_unknown_rows": int(len(mechanical)),
        "active_unknown_rows": int(
            mechanical["event_family"].eq("UNKNOWN").sum()
        ) if not mechanical.empty else 0,
        "transport": {
            "library": "curl_cffi",
            "impersonate": "chrome110",
            "max_attempts_per_ticker": MAX_ATTEMPTS,
            "backoff_seconds": list(BACKOFF_SECONDS),
            "timeout_seconds": args.timeout_seconds,
            "inter_ticker_sleep_seconds": args.sleep_seconds,
            "source_substitution": False,
        },
        "input": {
            "continuity_ledger_sha256": sha256_file(args.continuity_ledger),
        },
        "output_hashes": {
            "ticker_coverage": sha256_file(coverage_path),
            "ksei_ca_history": sha256_file(history_path),
            "active_mechanical_or_unknown_events": sha256_file(mechanical_path),
            "request_records": sha256_file(request_manifest_path),
        },
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": "v4_ksei_ca_history_census_manifest_v1",
        "created_at_utc": utc_now(),
        "status": summary["status"],
        "outcome_blind": True,
        "summary_sha256": sha256_file(summary_path),
        "input_hashes": summary["input"],
        "output_hashes": summary["output_hashes"],
        "raw_capture_count": sum(
            1 for path in raw_root.rglob("*.html") if path.is_file()
        ),
        "raw_capture_bytes": sum(
            path.stat().st_size for path in raw_root.rglob("*.html") if path.is_file()
        ),
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({**summary, "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
