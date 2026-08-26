from __future__ import annotations

import hashlib
import io
import json
import math
import re
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, time as dt_time
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from .provenance import sha256_file
from .security_master import normalise_ticker
from .stockbit_intraday_recovery import (
    NO_CHART_404,
    QUOTA_EXHAUSTED,
    REQUEST_ERROR,
    REQUEST_TERMINAL_ERROR,
    SKIPPED_IDX_NO_ACTIVITY,
    SUCCESS,
    build_recovery_plan,
    completion_state,
)


STOCKBIT_CHART_ENDPOINT = "https://api.zpi.web.id/v1/finance:stockbit/chart"
JAKARTA = ZoneInfo("Asia/Jakarta")
DEFAULT_CAPTURE_AFTER = "18:00"
DEFAULT_MONTHLY_QUOTA_RESERVE = 3_000
MAX_ATTEMPTS = 3
MAX_RETRY_AFTER_SECONDS = 30.0
REQUEST_DELAY_SECONDS = 0.05
_ATTEMPT_NAME = re.compile(r"^attempt-(\d{4})$")


@dataclass(frozen=True)
class ParsedChart:
    rows: pd.DataFrame
    status: dict[str, Any]


@dataclass(frozen=True)
class BatchResult:
    attempted: tuple[str, ...]
    stop_reason: str
    request_attempts: int
    retries: int
    rate_limit_events: int
    remaining_month: int | None
    summary: dict[str, Any]


def _now_jakarta() -> datetime:
    return datetime.now(tz=JAKARTA)


def _parse_hhmm(value: str) -> dt_time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as error:
        raise ValueError(f"invalid HH:MM time: {value}") from error


def validate_capture_window(
    *,
    expected_date: date,
    now: datetime | None = None,
    capture_after: str = DEFAULT_CAPTURE_AFTER,
) -> datetime:
    current = (now or _now_jakarta()).astimezone(JAKARTA)
    if current.date() != expected_date:
        raise ValueError("Stockbit timeframe=today requires expected_date == current Asia/Jakarta date")
    if current.time().replace(tzinfo=None) < _parse_hhmm(capture_after):
        raise RuntimeError(f"Stockbit intraday capture blocked before {capture_after} Asia/Jakarta")
    return current


def _safe_headers(response: Any) -> dict[str, Any]:
    headers = {str(key).casefold(): value for key, value in (getattr(response, "headers", {}) or {}).items()}
    return {
        "http_status": int(getattr(response, "status_code", 0)),
        "rate_limit_minute": headers.get("x-ratelimit-limit-minute"),
        "remaining_minute": headers.get("x-ratelimit-remaining-minute"),
        "rate_limit_month": headers.get("x-ratelimit-limit-month"),
        "remaining_month": headers.get("x-ratelimit-remaining-month"),
        "retry_after": headers.get("retry-after"),
        "plan_expired_present": "x-plan-expired" in headers,
    }


def _redact(value: object, secrets: tuple[str, ...]) -> str:
    text = str(value)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    return text


def _float_or_nan(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def _provider_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).date()


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


def parse_chart_payload(ticker: str, payload: object, *, expected_date: date) -> ParsedChart:
    ticker = normalise_ticker(ticker).upper()
    base: dict[str, Any] = {
        "ticker": ticker,
        "status": "IDENTITY_OR_PAYLOAD_ERROR",
        "provider_session_date": None,
        "points": 0,
        "earliest_timestamp": None,
        "latest_timestamp": None,
        "last_price": None,
        "duplicate_exact_rows_dropped": 0,
        "coverage_claim": "NONE",
    }
    body = _unwrap_payload(payload)
    if body is None:
        return ParsedChart(pd.DataFrame(), base)

    symbol = normalise_ticker(str(body.get("symbol") or "")).upper()
    provider = str(body.get("provider") or "").strip().casefold()
    interval = str(body.get("interval") or "").strip().casefold()
    timeframe = str(body.get("timeframe") or "").strip().casefold()
    if symbol != ticker or provider != "stockbit" or interval != "intraday" or timeframe != "today":
        base.update(
            {
                "observed_symbol": symbol,
                "observed_provider": provider,
                "observed_interval": interval,
                "observed_timeframe": timeframe,
            }
        )
        return ParsedChart(pd.DataFrame(), base)

    items = body.get("items")
    if not isinstance(items, list) or not items:
        base["status"] = "EMPTY_SESSION"
        return ParsedChart(pd.DataFrame(), base)

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
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        base["status"] = "NO_VALID_POINTS"
        return ParsedChart(frame, base)

    exact_columns = ["ticker", "timestamp", "price", "change", "change_percent"]
    before = len(frame)
    frame = frame.drop_duplicates(subset=exact_columns, keep="first").copy()
    duplicate_exact = before - len(frame)

    timestamp_counts = frame.groupby("timestamp", dropna=False).size()
    if bool((timestamp_counts > 1).any()):
        base.update(
            {
                "status": "DUPLICATE_TIMESTAMP_CONFLICT",
                "duplicate_exact_rows_dropped": duplicate_exact,
            }
        )
        return ParsedChart(pd.DataFrame(), base)

    observed_dates = sorted(set(frame["session_date"].astype(str)))
    if len(observed_dates) != 1:
        base.update(
            {
                "status": "MULTI_SESSION_PAYLOAD",
                "observed_session_dates": observed_dates,
                "duplicate_exact_rows_dropped": duplicate_exact,
            }
        )
        return ParsedChart(pd.DataFrame(), base)

    item_date = date.fromisoformat(observed_dates[0])
    metadata_date = _provider_date(body.get("tradingDate"))
    if metadata_date is not None and metadata_date != item_date:
        base.update(
            {
                "status": "TRADING_DATE_METADATA_MISMATCH",
                "provider_session_date": item_date.isoformat(),
                "metadata_trading_date": metadata_date.isoformat(),
                "duplicate_exact_rows_dropped": duplicate_exact,
            }
        )
        return ParsedChart(pd.DataFrame(), base)

    if item_date != expected_date:
        base.update(
            {
                "status": "NON_CURRENT_SESSION",
                "provider_session_date": item_date.isoformat(),
                "metadata_trading_date": metadata_date.isoformat() if metadata_date else None,
                "duplicate_exact_rows_dropped": duplicate_exact,
                "points": len(frame),
            }
        )
        return ParsedChart(pd.DataFrame(), base)

    frame = frame.sort_values("timestamp", kind="stable").reset_index(drop=True)
    status = {
        "ticker": ticker,
        "status": SUCCESS,
        "provider_session_date": item_date.isoformat(),
        "metadata_trading_date": metadata_date.isoformat() if metadata_date else None,
        "points": len(frame),
        "earliest_timestamp": frame["timestamp"].iloc[0],
        "latest_timestamp": frame["timestamp"].iloc[-1],
        "last_price": float(frame["price"].iloc[-1]),
        "duplicate_exact_rows_dropped": duplicate_exact,
        # SUCCESS proves identity + exact-session provider-path validity only.
        # Illiquid stocks can legitimately stop printing early, so V2 does not
        # invent a last-minute completeness threshold.
        "coverage_claim": "EXACT_SESSION_PROVIDER_PATH_ONLY",
    }
    return ParsedChart(frame, status)


def request_chart(
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
                params={"symbol": normalise_ticker(ticker).upper()},
                headers={"x-api-key": api_key},
                timeout=30,
            )
        except Exception as error:
            errors.append(_redact(f"{type(error).__name__}: {error}", (api_key,)))
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
            errors.append(_redact(f"JSONDecodeError: {error}", (api_key,)))
            return None, {
                "attempts": attempt,
                "retries": retries,
                "rate_limit_events": rate_limits,
                "errors": errors,
                "safe_headers": safe_headers,
            }
    raise AssertionError("unreachable")


def classify_request_failure(meta: Mapping[str, Any]) -> str:
    """Map a no-payload request result to deterministic recovery semantics."""

    safe = dict(meta.get("safe_headers") or {})
    try:
        http_status = int(safe.get("http_status") or 0)
    except (TypeError, ValueError):
        http_status = 0
    window = str(meta.get("rate_limit_window") or "").strip().casefold()
    errors = [str(value) for value in meta.get("errors") or []]

    if http_status == 404 or any("HTTP_404" in value for value in errors):
        return NO_CHART_404
    if (http_status == 429 and window == "month") or any("HTTP_429:month" in value for value in errors):
        return QUOTA_EXHAUSTED
    # 408/425/429 may be transient within the same provider session. 5xx and
    # transport/no-status failures are likewise eligible for the later
    # 19:30/20:30 recovery slots.
    if http_status in {0, 408, 425, 429} or http_status >= 500:
        return REQUEST_ERROR
    if http_status and http_status != 200:
        return REQUEST_TERMINAL_ERROR
    # A 200 response with invalid JSON can still recover on a later slot.
    return REQUEST_ERROR


def _canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n").encode("utf-8")


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    stream = io.StringIO()
    frame.to_csv(stream, index=False, lineterminator="\n")
    return stream.getvalue().encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_once(path: Path, value: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        if existing == value:
            return False
        raise FileExistsError(f"immutable Stockbit intraday artifact conflict: {path}")
    path.write_bytes(value)
    if path.read_bytes() != value:
        raise IOError(f"Stockbit intraday artifact read-after-write mismatch: {path}")
    return True


def canonical_current_universe(frame: pd.DataFrame, *, expected_date: date) -> pd.DataFrame:
    required = {"ticker", "listed_from"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"IDX active listing snapshot missing columns: {sorted(missing)}")
    data = frame.copy()
    data["ticker"] = data["ticker"].map(normalise_ticker).str.upper()
    data["listed_from"] = pd.to_datetime(data["listed_from"], errors="coerce").dt.normalize()
    expected = pd.Timestamp(expected_date).normalize()
    data = data[
        data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
        & data["listed_from"].notna()
        & data["listed_from"].le(expected)
    ].copy()
    if data.empty:
        raise ValueError("IDX current active-stock universe is empty")
    if data["ticker"].duplicated(keep=False).any():
        raise ValueError("duplicate ticker in current IDX universe")
    keep = [column for column in ("ticker", "company_name", "listed_from", "source") if column in data.columns]
    result = data[keep].sort_values("ticker").reset_index(drop=True)
    result.insert(0, "as_of_date", expected_date.isoformat())
    return result


class SessionJournal:
    """Immutable local journal for one prospective Stockbit intraday session.

    Every provider/gate observation is a new per-ticker attempt. Recovery never
    overwrites earlier evidence. The shape is intentionally portable to the
    later conditional-write R2 store.
    """

    def __init__(self, root: Path, *, expected_date: date):
        self.root = Path(root)
        self.expected_date = expected_date
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def universe_path(self) -> Path:
        return self.root / "universe_snapshot.csv"

    @property
    def metadata_path(self) -> Path:
        return self.root / "day_metadata.json"

    def freeze_or_verify_universe(self, source: pd.DataFrame, *, captured_at: datetime) -> pd.DataFrame:
        canonical = canonical_current_universe(source, expected_date=self.expected_date)
        universe_bytes = _csv_bytes(canonical)
        tickers = canonical["ticker"].astype(str).tolist()
        metadata = {
            "expected_date": self.expected_date.isoformat(),
            "captured_universe_at": captured_at.astimezone(JAKARTA).isoformat(),
            "universe_source": "IDX_CURRENT_ACTIVE_STOCK_LIST",
            "universe_rows": len(canonical),
            "ticker_list_sha256": _sha256_bytes(("\n".join(tickers) + "\n").encode("utf-8")),
            "universe_snapshot_sha256": _sha256_bytes(universe_bytes),
            "journal_layout_version": 2,
        }
        if self.universe_path.exists() or self.metadata_path.exists():
            if not self.universe_path.exists() or not self.metadata_path.exists():
                raise FileNotFoundError("frozen Stockbit intraday universe metadata is incomplete")
            existing = pd.read_csv(self.universe_path)
            existing_meta = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            if existing_meta.get("expected_date") != self.expected_date.isoformat():
                raise ValueError("existing Stockbit intraday journal belongs to another session")
            if existing_meta.get("universe_snapshot_sha256") != sha256_file(self.universe_path):
                raise ValueError("frozen Stockbit intraday universe hash mismatch")
            if existing["ticker"].astype(str).tolist() != tickers:
                raise ValueError("frozen Stockbit intraday universe identity mismatch")
            return existing
        _write_once(self.universe_path, universe_bytes)
        _write_once(self.metadata_path, _canonical_json_bytes(metadata))
        return canonical

    def load_universe(self) -> pd.DataFrame:
        if not self.universe_path.exists() or not self.metadata_path.exists():
            raise FileNotFoundError("Stockbit intraday universe is not frozen")
        frame = pd.read_csv(self.universe_path)
        metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        if metadata.get("expected_date") != self.expected_date.isoformat():
            raise ValueError("Stockbit intraday universe session mismatch")
        if metadata.get("universe_snapshot_sha256") != sha256_file(self.universe_path):
            raise ValueError("Stockbit intraday universe hash mismatch")
        if int(metadata.get("universe_rows") or -1) != len(frame):
            raise ValueError("Stockbit intraday universe row-count mismatch")
        return frame

    def _ticker_root(self, ticker: str) -> Path:
        return self.root / "attempts" / normalise_ticker(ticker).upper()

    def _attempt_dirs(self, ticker: str) -> list[Path]:
        root = self._ticker_root(ticker)
        if not root.exists():
            return []
        attempts: list[tuple[int, Path]] = []
        for path in root.iterdir():
            if not path.is_dir():
                continue
            match = _ATTEMPT_NAME.fullmatch(path.name)
            if match is None:
                raise ValueError(f"unexpected Stockbit intraday attempt directory: {path}")
            attempts.append((int(match.group(1)), path))
        attempts.sort(key=lambda item: item[0])
        numbers = [number for number, _ in attempts]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError(f"non-contiguous Stockbit intraday attempts for {normalise_ticker(ticker).upper()}")
        return [path for _, path in attempts]

    def _next_attempt_dir(self, ticker: str) -> Path:
        attempts = self._attempt_dirs(ticker)
        path = self._ticker_root(ticker) / f"attempt-{len(attempts) + 1:04d}"
        if path.exists():
            raise FileExistsError(f"Stockbit intraday attempt id collision: {path}")
        path.mkdir(parents=True, exist_ok=False)
        return path

    def _verify_attempt(self, attempt_dir: Path) -> dict[str, Any]:
        manifest_path = attempt_dir / "manifest.json"
        status_path = attempt_dir / "status.json"
        if not manifest_path.exists() or not status_path.exists():
            raise FileNotFoundError(f"incomplete Stockbit intraday attempt: {attempt_dir}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema") != "idx_trade_stockbit_intraday_attempt_v2":
            raise ValueError(f"Stockbit intraday attempt schema mismatch: {attempt_dir}")
        if manifest.get("session_date") != self.expected_date.isoformat():
            raise ValueError(f"Stockbit intraday attempt session mismatch: {attempt_dir}")
        if manifest.get("attempt_id") != attempt_dir.name:
            raise ValueError(f"Stockbit intraday attempt identity mismatch: {attempt_dir}")
        for relative, expected_sha in dict(manifest.get("files") or {}).items():
            path = attempt_dir / relative
            if not path.exists() or sha256_file(path) != expected_sha:
                raise ValueError(f"Stockbit intraday attempt hash mismatch: {path}")
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if normalise_ticker(str(status.get("ticker") or "")).upper() != str(manifest.get("ticker") or "").upper():
            raise ValueError(f"Stockbit intraday status ticker mismatch: {attempt_dir}")
        return status

    def _latest_status(self, ticker: str) -> dict[str, Any] | None:
        attempts = self._attempt_dirs(ticker)
        return self._verify_attempt(attempts[-1]) if attempts else None

    def latest_status_by_ticker(self) -> dict[str, dict[str, Any]]:
        universe = self.load_universe()
        result: dict[str, dict[str, Any]] = {}
        for ticker in universe["ticker"].astype(str):
            status = self._latest_status(ticker)
            if status is not None:
                result[ticker] = status
        return result

    def _assert_provider_attempt_allowed(self, ticker: str) -> None:
        prior = self._latest_status(ticker)
        if prior is None:
            return
        prior_status = str(prior.get("status") or "").upper()
        if prior_status != REQUEST_ERROR:
            raise RuntimeError(
                f"Stockbit intraday provider refetch blocked for {ticker}: prior status {prior_status or 'UNKNOWN'}"
            )

    def _write_attempt(
        self,
        ticker: str,
        *,
        status: Mapping[str, Any],
        payload: object | None = None,
        rows: pd.DataFrame | None = None,
    ) -> None:
        attempt_dir = self._next_attempt_dir(ticker)
        files: dict[str, str] = {}
        if payload is not None:
            raw = _canonical_json_bytes({"ticker": ticker, "payload": payload})
            _write_once(attempt_dir / "raw.json", raw)
            files["raw.json"] = _sha256_bytes(raw)
        if rows is not None and not rows.empty:
            row_bytes = _csv_bytes(rows)
            _write_once(attempt_dir / "rows.csv", row_bytes)
            files["rows.csv"] = _sha256_bytes(row_bytes)
        status_bytes = _canonical_json_bytes(dict(status))
        _write_once(attempt_dir / "status.json", status_bytes)
        files["status.json"] = _sha256_bytes(status_bytes)
        manifest = {
            "schema": "idx_trade_stockbit_intraday_attempt_v2",
            "session_date": self.expected_date.isoformat(),
            "ticker": ticker,
            "attempt_id": attempt_dir.name,
            "files": files,
        }
        # Manifest is deliberately written last: an interrupted attempt is not
        # admissible and blocks future recovery until inspected/repaired.
        _write_once(attempt_dir / "manifest.json", _canonical_json_bytes(manifest))
        self._verify_attempt(attempt_dir)

    def record_provider_attempt(
        self,
        ticker: str,
        *,
        payload: object | None,
        request_meta: Mapping[str, Any],
        captured_at: datetime,
    ) -> dict[str, Any]:
        ticker = normalise_ticker(ticker).upper()
        self._assert_provider_attempt_allowed(ticker)
        if payload is None:
            parsed = ParsedChart(
                pd.DataFrame(),
                {
                    "ticker": ticker,
                    "status": classify_request_failure(request_meta),
                    "points": 0,
                    "errors": list(request_meta.get("errors") or []),
                    "coverage_claim": "NONE",
                },
            )
        else:
            parsed = parse_chart_payload(ticker, payload, expected_date=self.expected_date)

        status = dict(parsed.status)
        status.update(
            {
                "captured_at": captured_at.astimezone(JAKARTA).isoformat(),
                "attempts": request_meta.get("attempts"),
                "retries": request_meta.get("retries"),
                "rate_limit_events": request_meta.get("rate_limit_events"),
                "safe_headers": dict(request_meta.get("safe_headers") or {}),
            }
        )
        self._write_attempt(ticker, status=status, payload=payload, rows=parsed.rows)
        return status

    def record_gate_skip(
        self,
        ticker: str,
        *,
        captured_at: datetime,
        gate_evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        ticker = normalise_ticker(ticker).upper()
        if gate_evidence.get("activity_or") is not False:
            raise ValueError("Stockbit intraday gate skip requires explicit activity_or=false")
        prior = self._latest_status(ticker)
        if prior is not None:
            prior_status = str(prior.get("status") or "").upper()
            if prior_status == SKIPPED_IDX_NO_ACTIVITY:
                return prior
            # A Stockbit 404 observed in SHADOW may subsequently be reconciled
            # by exact-session official IDX zero-activity evidence. Preserve the
            # 404 attempt and append the gate decision as a new immutable event.
            if prior_status != NO_CHART_404:
                raise RuntimeError(
                    f"Stockbit intraday gate skip cannot replace prior status for {ticker}: {prior_status or 'UNKNOWN'}"
                )
        status = {
            "ticker": ticker,
            "status": SKIPPED_IDX_NO_ACTIVITY,
            "points": 0,
            "captured_at": captured_at.astimezone(JAKARTA).isoformat(),
            "coverage_claim": "OFFICIAL_IDX_NO_ACTIVITY_GATE",
            "gate_evidence": dict(gate_evidence),
        }
        self._write_attempt(ticker, status=status)
        return status

    def recovery_plan(self):
        universe = self.load_universe()
        tickers = universe["ticker"].astype(str).tolist()
        return build_recovery_plan(tickers, self.latest_status_by_ticker())

    def summary(self) -> dict[str, Any]:
        universe = self.load_universe()
        tickers = universe["ticker"].astype(str).tolist()
        statuses = self.latest_status_by_ticker()
        state = completion_state(tickers, statuses)
        counts: dict[str, int] = {}
        normalized_points = 0
        for value in statuses.values():
            status = str(value.get("status") or "UNKNOWN")
            counts[status] = counts.get(status, 0) + 1
            normalized_points += int(value.get("points") or 0)
        return {
            **asdict(state),
            "status_counts": counts,
            "normalized_points": normalized_points,
            "complete": state.admissible_complete,
            "synthetic_fill_used": False,
            "minute_volume_available": False,
        }


def _remaining_month(meta: Mapping[str, Any]) -> int | None:
    safe = dict(meta.get("safe_headers") or {})
    try:
        return int(str(safe.get("remaining_month")))
    except (TypeError, ValueError):
        return None


def run_recovery_batch(
    journal: SessionJournal,
    *,
    requester: Callable[[str], tuple[object | None, Mapping[str, Any]]],
    now: datetime,
    max_new_tickers: int = 1_200,
    monthly_quota_reserve: int = DEFAULT_MONTHLY_QUOTA_RESERVE,
) -> BatchResult:
    validate_capture_window(expected_date=journal.expected_date, now=now)
    if max_new_tickers <= 0:
        raise ValueError("max_new_tickers must be positive")
    if monthly_quota_reserve < 0:
        raise ValueError("monthly_quota_reserve must be non-negative")

    plan = journal.recovery_plan()
    pending = list(plan.pending)
    if len(pending) > max_new_tickers:
        raise ValueError(f"pending ticker count {len(pending)} exceeds max_new_tickers={max_new_tickers}")

    attempted: list[str] = []
    request_attempts = retries = rate_limit_events = 0
    remaining_month: int | None = None
    stop_reason = "COMPLETED_PENDING_SET"
    for index, ticker in enumerate(pending):
        payload, meta = requester(ticker)
        journal.record_provider_attempt(ticker, payload=payload, request_meta=meta, captured_at=now)
        attempted.append(ticker)
        request_attempts += int(meta.get("attempts") or 0)
        retries += int(meta.get("retries") or 0)
        rate_limit_events += int(meta.get("rate_limit_events") or 0)
        remaining_month = _remaining_month(meta)
        if remaining_month is not None and remaining_month <= monthly_quota_reserve:
            stop_reason = "MONTHLY_QUOTA_RESERVE_REACHED"
            break
        if index + 1 < len(pending):
            time.sleep(REQUEST_DELAY_SECONDS)

    return BatchResult(
        attempted=tuple(attempted),
        stop_reason=stop_reason,
        request_attempts=request_attempts,
        retries=retries,
        rate_limit_events=rate_limit_events,
        remaining_month=remaining_month,
        summary=journal.summary(),
    )
