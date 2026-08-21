from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from .provenance import sha256_file
from .security_master import normalise_ticker
from .tier2_open_audit import redact_secrets


STOCKBIT_CHART_ENDPOINT = "https://api.zpi.web.id/v1/finance:stockbit/chart"
JAKARTA = ZoneInfo("Asia/Jakarta")
# Official IDX Stock Summary is not reliably populated at the exchange close.
# Keep the recurring capture after the canonical EOD availability cutoff.
DEFAULT_CAPTURE_AFTER = "18:00"
DEFAULT_MAX_REQUESTS = 500
MAX_ATTEMPTS = 3
MAX_RETRY_AFTER_SECONDS = 30.0
REQUEST_DELAY_SECONDS = 0.05


@dataclass(frozen=True)
class CaptureConfig:
    expected_date: date
    capture_after: dt_time
    allow_partial_session: bool
    max_requests: int


def _write_json(value: object, path: Path) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n")


def _safe_headers(response: Any) -> dict[str, Any]:
    headers = {str(k).casefold(): v for k, v in (getattr(response, "headers", {}) or {}).items()}
    return {
        "http_status": int(getattr(response, "status_code", 0)),
        "rate_limit_minute": headers.get("x-ratelimit-limit-minute"),
        "remaining_minute": headers.get("x-ratelimit-remaining-minute"),
        "rate_limit_month": headers.get("x-ratelimit-limit-month"),
        "remaining_month": headers.get("x-ratelimit-remaining-month"),
        "retry_after": headers.get("retry-after"),
        "plan_expired_present": "x-plan-expired" in headers,
    }


def _parse_hhmm(value: str) -> dt_time:
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError as error:
        raise ValueError(f"invalid HH:MM time: {value}") from error
    return parsed.time()


def _now_jakarta() -> datetime:
    return datetime.now(tz=JAKARTA)


def _parse_expected_date(value: str | None, *, now: datetime | None = None) -> date:
    if value:
        return date.fromisoformat(value)
    current = now or _now_jakarta()
    return current.astimezone(JAKARTA).date()


def _split_ticker_text(text: str) -> list[str]:
    tokens = [part.strip() for part in re.split(r"[\s,;]+", text) if part.strip()]
    return tokens


def load_tickers(
    inline: Iterable[str] | None = None,
    tickers_file: Path | None = None,
) -> list[str]:
    raw: list[str] = []
    for value in inline or ():
        raw.extend(_split_ticker_text(str(value)))

    if tickers_file is not None:
        text = tickers_file.read_text(encoding="utf-8-sig")
        if tickers_file.suffix.casefold() == ".csv":
            try:
                frame = pd.read_csv(tickers_file)
            except Exception:
                frame = pd.DataFrame()
            selected = None
            for candidate in ("ticker", "symbol", "code"):
                if candidate in frame.columns:
                    selected = frame[candidate]
                    break
            if selected is not None:
                raw.extend(str(value) for value in selected.dropna().tolist())
            else:
                raw.extend(_split_ticker_text(text))
        else:
            raw.extend(_split_ticker_text(text))

    cleaned: list[str] = []
    seen: set[str] = set()
    ignored_headers = {"TICKER", "SYMBOL", "CODE"}
    for value in raw:
        ticker = normalise_ticker(str(value)).upper()
        if not ticker or ticker in ignored_headers or ticker in seen:
            continue
        seen.add(ticker)
        cleaned.append(ticker)
    return cleaned


def _unwrap_payload(payload: object) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    if "symbol" in payload and "items" in payload:
        return payload
    for key in ("data", "content", "result"):
        candidate = payload.get(key)
        if isinstance(candidate, dict) and "symbol" in candidate and "items" in candidate:
            return candidate
    return None


def _parse_provider_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).date()


def _float_or_nan(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def parse_chart_payload(
    ticker: str,
    payload: object,
    *,
    expected_date: date,
    capture_state: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    body = _unwrap_payload(payload)
    base_status: dict[str, Any] = {
        "ticker": ticker,
        "status": "IDENTITY_OR_PAYLOAD_ERROR",
        "provider_session_date": None,
        "points": 0,
        "earliest_timestamp": None,
        "latest_timestamp": None,
        "duplicate_exact_rows_dropped": 0,
    }
    if body is None:
        return pd.DataFrame(), base_status

    symbol = str(body.get("symbol") or "").strip().upper()
    provider = str(body.get("provider") or "").strip().casefold()
    interval = str(body.get("interval") or "").strip().casefold()
    timeframe = str(body.get("timeframe") or "").strip().casefold()
    if symbol != ticker or provider != "stockbit" or interval != "intraday" or timeframe != "today":
        base_status.update(
            {
                "observed_symbol": symbol,
                "observed_provider": provider,
                "observed_interval": interval,
                "observed_timeframe": timeframe,
            }
        )
        return pd.DataFrame(), base_status

    items = body.get("items")
    if not isinstance(items, list) or not items:
        base_status["status"] = "EMPTY_SESSION"
        return pd.DataFrame(), base_status

    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        timestamp = pd.to_datetime(item.get("time"), errors="coerce")
        price = _float_or_nan(item.get("price"))
        if pd.isna(timestamp) or not math.isfinite(price) or price <= 0:
            continue
        ts = pd.Timestamp(timestamp)
        if ts.tzinfo is None:
            ts = ts.tz_localize(JAKARTA)
        else:
            ts = ts.tz_convert(JAKARTA)
        rows.append(
            {
                "ticker": ticker,
                "timestamp": ts.isoformat(),
                "session_date": ts.date().isoformat(),
                "price": price,
                "change": _float_or_nan(item.get("change")),
                "change_percent": _float_or_nan(item.get("changePercent")),
                "previous_close": _float_or_nan(body.get("previousClose")),
                "provider": "stockbit",
                "interval": "intraday",
                "timeframe": "today",
                "capture_state": capture_state,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        base_status["status"] = "NO_VALID_POINTS"
        return frame, base_status

    exact_cols = ["ticker", "timestamp", "price", "change", "change_percent"]
    before = len(frame)
    frame = frame.drop_duplicates(subset=exact_cols, keep="first").copy()
    duplicate_exact = before - len(frame)

    timestamp_counts = frame.groupby("timestamp", dropna=False).size()
    if bool((timestamp_counts > 1).any()):
        base_status.update(
            {
                "status": "DUPLICATE_TIMESTAMP_CONFLICT",
                "duplicate_exact_rows_dropped": duplicate_exact,
            }
        )
        return pd.DataFrame(), base_status

    observed_dates = sorted(set(frame["session_date"].astype(str)))
    if len(observed_dates) != 1:
        base_status.update(
            {
                "status": "MULTI_SESSION_PAYLOAD",
                "observed_session_dates": observed_dates,
                "duplicate_exact_rows_dropped": duplicate_exact,
            }
        )
        return pd.DataFrame(), base_status

    item_date = date.fromisoformat(observed_dates[0])
    metadata_date = _parse_provider_date(body.get("tradingDate"))
    if metadata_date is not None and metadata_date != item_date:
        base_status.update(
            {
                "status": "TRADING_DATE_METADATA_MISMATCH",
                "provider_session_date": item_date.isoformat(),
                "metadata_trading_date": metadata_date.isoformat(),
                "duplicate_exact_rows_dropped": duplicate_exact,
            }
        )
        return pd.DataFrame(), base_status

    if item_date != expected_date:
        base_status.update(
            {
                "status": "NON_CURRENT_SESSION",
                "provider_session_date": item_date.isoformat(),
                "metadata_trading_date": metadata_date.isoformat() if metadata_date else None,
                "duplicate_exact_rows_dropped": duplicate_exact,
                "points": len(frame),
            }
        )
        return pd.DataFrame(), base_status

    frame = frame.sort_values("timestamp", kind="stable").reset_index(drop=True)
    status = "PARTIAL_SESSION" if capture_state == "PARTIAL_SESSION" else "SUCCESS"
    return frame, {
        "ticker": ticker,
        "status": status,
        "provider_session_date": item_date.isoformat(),
        "metadata_trading_date": metadata_date.isoformat() if metadata_date else None,
        "points": len(frame),
        "earliest_timestamp": frame["timestamp"].iloc[0],
        "latest_timestamp": frame["timestamp"].iloc[-1],
        "duplicate_exact_rows_dropped": duplicate_exact,
    }


def _request_chart(
    session: requests.Session,
    ticker: str,
    api_key: str,
) -> tuple[object | None, dict[str, Any]]:
    errors: list[str] = []
    retries = 0
    rate_limits = 0
    safe_headers: dict[str, Any] = {}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.get(
                STOCKBIT_CHART_ENDPOINT,
                params={"symbol": ticker},
                headers={"x-api-key": api_key},
                timeout=30,
            )
        except Exception as error:
            errors.append(str(redact_secrets(f"{type(error).__name__}: {error}", (api_key,))))
            if attempt < MAX_ATTEMPTS:
                retries += 1
                time.sleep(1.0)
                continue
            return None, {
                "attempts": attempt,
                "retries": retries,
                "rate_limit_events": rate_limits,
                "errors": errors,
                "safe_headers": safe_headers,
            }

        safe_headers = _safe_headers(response)
        if response.status_code == 429:
            rate_limits += 1
            try:
                body = response.json()
            except Exception:
                body = {}
            window = str(body.get("window") or "unknown").casefold() if isinstance(body, dict) else "unknown"
            if window == "month" or attempt >= MAX_ATTEMPTS:
                errors.append(f"HTTP_429:{window}")
                return None, {
                    "attempts": attempt,
                    "retries": retries,
                    "rate_limit_events": rate_limits,
                    "errors": errors,
                    "safe_headers": safe_headers,
                    "rate_limit_window": window,
                }
            try:
                wait = float(safe_headers.get("retry_after") or 2.0)
            except (TypeError, ValueError):
                wait = 2.0
            if wait > MAX_RETRY_AFTER_SECONDS:
                errors.append("HTTP_429:WAIT_EXCEEDS_BOUND")
                return None, {
                    "attempts": attempt,
                    "retries": retries,
                    "rate_limit_events": rate_limits,
                    "errors": errors,
                    "safe_headers": safe_headers,
                    "rate_limit_window": window,
                }
            retries += 1
            time.sleep(max(wait, 1.0))
            continue

        if response.status_code >= 500 and attempt < MAX_ATTEMPTS:
            retries += 1
            errors.append(f"HTTP_{response.status_code}")
            time.sleep(1.0)
            continue
        if response.status_code != 200:
            errors.append(f"HTTP_{response.status_code}")
            return None, {
                "attempts": attempt,
                "retries": retries,
                "rate_limit_events": rate_limits,
                "errors": errors,
                "safe_headers": safe_headers,
            }
        try:
            return response.json(), {
                "attempts": attempt,
                "retries": retries,
                "rate_limit_events": rate_limits,
                "errors": errors,
                "safe_headers": safe_headers,
            }
        except Exception as error:
            errors.append(str(redact_secrets(f"JSONDecodeError: {error}", (api_key,))))
            return None, {
                "attempts": attempt,
                "retries": retries,
                "rate_limit_events": rate_limits,
                "errors": errors,
                "safe_headers": safe_headers,
            }

    raise AssertionError("unreachable")


def capture_state(now: datetime, capture_after: dt_time, allow_partial: bool) -> str:
    local = now.astimezone(JAKARTA)
    if local.time().replace(tzinfo=None) >= capture_after:
        return "SESSION_COMPLETE_WINDOW"
    if allow_partial:
        return "PARTIAL_SESSION"
    return "BLOCKED_BEFORE_CLOSE"


def validate_request_budget(tickers: list[str], max_requests: int) -> None:
    if max_requests <= 0:
        raise ValueError("max_requests must be positive")
    if len(tickers) > max_requests:
        raise ValueError(f"ticker count {len(tickers)} exceeds max_requests={max_requests}")


def _prepare_output_root(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise FileExistsError(f"output root exists and is not a directory: {path}")
        if any(path.iterdir()):
            raise FileExistsError(f"refusing to overwrite non-empty artifact root: {path}")
    else:
        path.mkdir(parents=True, exist_ok=False)


def _manifest(output_root: Path, paths: list[Path]) -> dict[str, Any]:
    files = {path.name: sha256_file(path) for path in paths}
    manifest = {"files": files}
    manifest_path = output_root / "artifact_manifest.json"
    _write_json(manifest, manifest_path)
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest


def run_capture(
    tickers: list[str],
    output_root: Path,
    *,
    config: CaptureConfig,
    api_key: str,
    now: datetime | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    validate_request_budget(tickers, config.max_requests)
    if not tickers:
        raise ValueError("no tickers supplied")
    current = now or _now_jakarta()
    state = capture_state(current, config.capture_after, config.allow_partial_session)
    if state == "BLOCKED_BEFORE_CLOSE":
        raise RuntimeError(
            f"capture blocked before {config.capture_after.strftime('%H:%M')} Asia/Jakarta; "
            "use --allow-partial-session only for an explicitly partial pilot"
        )

    _prepare_output_root(output_root)
    raw_path = output_root / "stockbit_intraday_raw_responses.jsonl"
    rows_path = output_root / "stockbit_intraday_rows.csv"
    status_path = output_root / "stockbit_intraday_ticker_status.csv"
    summary_path = output_root / "run_summary.json"

    statuses: list[dict[str, Any]] = []
    normalized_frames: list[pd.DataFrame] = []
    requests_made = retries = rate_limits = provider_errors = 0
    first_quota: dict[str, Any] | None = None
    last_quota: dict[str, Any] | None = None
    http = session or requests.Session()

    with raw_path.open("x", encoding="utf-8", newline="\n") as raw_handle:
        for index, ticker in enumerate(tickers):
            payload, meta = _request_chart(http, ticker, api_key)
            requests_made += int(meta.get("attempts") or 0)
            retries += int(meta.get("retries") or 0)
            rate_limits += int(meta.get("rate_limit_events") or 0)
            headers = dict(meta.get("safe_headers") or {})
            if headers:
                if first_quota is None:
                    first_quota = headers
                last_quota = headers

            if payload is None:
                provider_errors += 1
                statuses.append(
                    {
                        "ticker": ticker,
                        "status": "REQUEST_ERROR",
                        "points": 0,
                        "errors": " | ".join(str(value) for value in meta.get("errors") or []),
                        "attempts": meta.get("attempts"),
                        "retries": meta.get("retries"),
                        "rate_limit_events": meta.get("rate_limit_events"),
                    }
                )
            else:
                raw_handle.write(
                    json.dumps(
                        {
                            "ticker": ticker,
                            "captured_at": current.isoformat(),
                            "expected_date": config.expected_date.isoformat(),
                            "capture_state": state,
                            "payload": payload,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        default=str,
                    )
                    + "\n"
                )
                frame, status = parse_chart_payload(
                    ticker,
                    payload,
                    expected_date=config.expected_date,
                    capture_state=state,
                )
                status.update(
                    {
                        "attempts": meta.get("attempts"),
                        "retries": meta.get("retries"),
                        "rate_limit_events": meta.get("rate_limit_events"),
                    }
                )
                statuses.append(status)
                if not frame.empty:
                    normalized_frames.append(frame)

            if index + 1 < len(tickers):
                time.sleep(REQUEST_DELAY_SECONDS)

    rows = pd.concat(normalized_frames, ignore_index=True) if normalized_frames else pd.DataFrame(
        columns=[
            "ticker",
            "timestamp",
            "session_date",
            "price",
            "change",
            "change_percent",
            "previous_close",
            "provider",
            "interval",
            "timeframe",
            "capture_state",
        ]
    )
    status_frame = pd.DataFrame(statuses)
    _write_csv(rows, rows_path)
    _write_csv(status_frame, status_path)

    good_statuses = {"SUCCESS", "PARTIAL_SESSION"}
    earliest = rows["timestamp"].min() if not rows.empty else None
    latest = rows["timestamp"].max() if not rows.empty else None
    summary: dict[str, Any] = {
        "provider": "stockbit",
        "endpoint": STOCKBIT_CHART_ENDPOINT,
        "captured_at": current.isoformat(),
        "expected_date": config.expected_date.isoformat(),
        "capture_after": config.capture_after.strftime("%H:%M"),
        "capture_state": state,
        "requested_tickers": len(tickers),
        "successful_tickers": int(status_frame["status"].isin(good_statuses).sum()) if not status_frame.empty else 0,
        "non_current_session_tickers": int(status_frame["status"].eq("NON_CURRENT_SESSION").sum()) if not status_frame.empty else 0,
        "partial_session_tickers": int(status_frame["status"].eq("PARTIAL_SESSION").sum()) if not status_frame.empty else 0,
        "request_error_tickers": int(status_frame["status"].eq("REQUEST_ERROR").sum()) if not status_frame.empty else 0,
        "requests": requests_made,
        "retries": retries,
        "http_429_events": rate_limits,
        "provider_errors": provider_errors,
        "normalized_points": len(rows),
        "earliest_timestamp": earliest,
        "latest_timestamp": latest,
        "quota_first_response": first_quota,
        "quota_last_response": last_quota,
        "synthetic_fill_used": False,
        "minute_volume_available": False,
    }
    _write_json(summary, summary_path)
    manifest = _manifest(output_root, [raw_path, rows_path, status_path, summary_path])
    summary["artifact_manifest_sha256"] = manifest["manifest_sha256"]
    return summary


def _dry_run_report(
    tickers: list[str],
    *,
    config: CaptureConfig,
    now: datetime,
    output_root: Path,
) -> dict[str, Any]:
    validate_request_budget(tickers, config.max_requests)
    state = capture_state(now, config.capture_after, config.allow_partial_session)
    return {
        "mode": "DRY_RUN",
        "ticker_count": len(tickers),
        "estimated_billable_chart_calls": len(tickers),
        "expected_date": config.expected_date.isoformat(),
        "capture_after": config.capture_after.strftime("%H:%M"),
        "capture_state_now": state,
        "output_root": str(output_root),
        "would_execute": state != "BLOCKED_BEFORE_CLOSE",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Forward-capture Stockbit intraday price paths via Zapi")
    parser.add_argument("--tickers", nargs="*", default=[], help="Tickers, space/comma separated")
    parser.add_argument("--tickers-file", type=Path, default=None, help="Text/CSV file with ticker/symbol/code")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-date", default=None, help="YYYY-MM-DD; defaults to current Asia/Jakarta date")
    parser.add_argument("--capture-after", default=DEFAULT_CAPTURE_AFTER, help="Asia/Jakarta HH:MM close gate")
    parser.add_argument("--allow-partial-session", action="store_true")
    parser.add_argument("--max-requests", type=int, default=DEFAULT_MAX_REQUESTS)
    parser.add_argument("--execute", action="store_true", help="Perform billable requests; default is dry-run")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    now = _now_jakarta()
    tickers = load_tickers(args.tickers, args.tickers_file)
    expected_date = _parse_expected_date(args.expected_date, now=now)
    config = CaptureConfig(
        expected_date=expected_date,
        capture_after=_parse_hhmm(args.capture_after),
        allow_partial_session=bool(args.allow_partial_session),
        max_requests=int(args.max_requests),
    )

    if not args.execute:
        print(json.dumps(_dry_run_report(tickers, config=config, now=now, output_root=args.output_root), indent=2))
        return 0

    api_key = os.environ.get("ZAPI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ZAPI_API_KEY is required for --execute")
    summary = run_capture(tickers, args.output_root, config=config, api_key=api_key, now=now)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
