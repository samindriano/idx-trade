from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import requests

from .provenance import sha256_file
from .security_master import normalise_ticker
from .tier2_open_audit import (
    _empty_provider_frame,
    _provider_frame,
    audit_provider_rows,
    classify_zapi_access_failure,
    redact_secrets,
)

EXPECTED_SAMPLE_SHA256 = "9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344"
TRADINGVIEW_ENDPOINT = "https://api.zpi.web.id/v1/finance:tradingview/chart"
INVESTING_SEARCH_ENDPOINT = "https://api.zpi.web.id/v1/finance:investing/search"
INVESTING_HISTORICAL_ENDPOINT = "https://api.zpi.web.id/v1/finance:investing/historical"
REQUEST_DELAY_SECONDS = 1.05
INVESTING_POINTSCOUNT = 1500
RATE_LIMIT_MAX_WAIT_SECONDS = 90.0
EXPECTED_PRIOR_ARTIFACT_MANIFEST_SHA256 = "b5008e9942ca8681499f544c98a8bccda9c1e03b82ceb46ba1fbc45d3b1a6a80"


def _unwrap(payload: object) -> object:
    current = payload
    for _ in range(3):
        if not isinstance(current, dict):
            break
        if "content" in current and isinstance(current["content"], (dict, list)):
            current = current["content"]
            continue
        if "data" in current and isinstance(current["data"], (dict, list)):
            current = current["data"]
            continue
        break
    return current


def _session_date(value: object) -> pd.Timestamp | pd.NaT:
    stamp = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(stamp):
        return pd.NaT
    return stamp.tz_convert("Asia/Jakarta").normalize().tz_localize(None)


def _rate_limit_diagnostic(response: Any) -> dict[str, Any]:
    """Capture quota metadata only; never retain the 429 response body."""
    window: object = None
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        window = payload.get("window")
    window = str(window).casefold() if window is not None else "unknown"
    if window not in {"minute", "month"}:
        window = "unknown"
    headers = getattr(response, "headers", {}) or {}
    plan_expired_present = any(str(key).casefold() == "x-plan-expired" for key in headers)
    return {
        "window": window,
        "retry_after": headers.get("Retry-After"),
        "rate_limit_limit": headers.get("X-RateLimit-Limit"),
        "remaining_minute": headers.get("X-RateLimit-Remaining-Minute"),
        "remaining_month": headers.get("X-RateLimit-Remaining-Month"),
        "plan_expired_present": plan_expired_present,
    }


def _quota_window_state(diagnostics: Iterable[dict[str, Any]]) -> str:
    windows = {str(row.get("window", "unknown")) for row in diagnostics}
    if "month" in windows:
        return "month"
    if "unknown" in windows:
        return "unknown"
    if "minute" in windows:
        return "minute"
    return "none"


def _selected_tickers(sample: pd.DataFrame, tickers: Iterable[str] | None) -> list[str]:
    available = {normalise_ticker(value) for value in sample["ticker"].unique()}
    if tickers is None:
        return sorted(available)
    return sorted(available.intersection(normalise_ticker(value) for value in tickers))


def _load_sample(path: str | Path) -> pd.DataFrame:
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"Frozen sample manifest missing: {file}")
    digest = sha256_file(file)
    if digest != EXPECTED_SAMPLE_SHA256:
        raise RuntimeError(f"Frozen sample SHA mismatch: {digest}")
    sample = pd.read_csv(file)
    required = {
        "sample_id",
        "sample_role",
        "residual_problem_class",
        "ticker",
        "date",
        "panel_open",
        "panel_high",
        "panel_low",
        "panel_close",
        "yahoo_raw_open",
        "yahoo_raw_high",
        "yahoo_raw_low",
        "yahoo_raw_close",
    }
    missing = required - set(sample.columns)
    if missing:
        raise ValueError(f"Frozen sample columns missing: {sorted(missing)}")
    sample["ticker"] = sample["ticker"].map(normalise_ticker)
    sample["date"] = pd.to_datetime(sample["date"], errors="coerce").dt.normalize()
    if sample["date"].isna().any() or sample.duplicated(["sample_id"]).any():
        raise ValueError("Frozen sample contains invalid dates or duplicate sample_id")
    return sample


def _request_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any],
    api_key: str,
    delay_seconds: float = REQUEST_DELAY_SECONDS,
    timeout: int = 30,
) -> tuple[object | None, dict[str, Any]]:
    errors: list[str] = []
    rate_limits = 0
    retries = 0
    rate_limit_diagnostics: list[dict[str, Any]] = []
    access_status = "ACCESSIBLE"
    plan_status = "EMPIRICALLY_REACHED"
    for attempt in range(1, 4):
        try:
            response = session.get(url, params=params, headers={"x-api-key": api_key}, timeout=timeout)
        except Exception as error:
            errors.append(str(redact_secrets(f"{type(error).__name__}: {error}", (api_key,))))
            if attempt < 3:
                retries += 1
                time.sleep(max(delay_seconds, 1.0))
                continue
            return None, {
                "access_status": "REQUEST_ERROR",
                "plan_status": plan_status,
                "retries": retries,
                "rate_limit_events": rate_limits,
                "rate_limit_diagnostics": rate_limit_diagnostics,
                "rate_limit_stop_reason": None,
                "errors": errors,
            }
        if response.status_code == 429:
            rate_limits += 1
            diagnostic = _rate_limit_diagnostic(response)
            rate_limit_diagnostics.append(diagnostic)
            window = diagnostic["window"]
            if window == "month":
                stop_reason = "MONTH_QUOTA"
            elif window == "unknown":
                stop_reason = "UNKNOWN_QUOTA_WINDOW"
            elif attempt >= 3:
                stop_reason = "MAX_ATTEMPTS"
            else:
                try:
                    wait = max(float(diagnostic.get("retry_after") or 2.0), 1.0)
                except (TypeError, ValueError):
                    wait = 2.0
                if wait > RATE_LIMIT_MAX_WAIT_SECONDS:
                    stop_reason = "MINUTE_WAIT_EXCEEDS_BOUND"
                else:
                    retries += 1
                    time.sleep(wait)
                    continue
            if stop_reason in {"MONTH_QUOTA", "UNKNOWN_QUOTA_WINDOW"}:
                errors.append(f"HTTP_429:RATE_LIMITED:{stop_reason}")
            else:
                errors.append("HTTP_429:RATE_LIMITED")
            return None, {
                "access_status": "RATE_LIMITED",
                "plan_status": plan_status,
                "retries": retries,
                "rate_limit_events": rate_limits,
                "rate_limit_diagnostics": rate_limit_diagnostics,
                "rate_limit_stop_reason": stop_reason,
                "errors": errors,
            }
        if response.status_code != 200:
            failure = classify_zapi_access_failure(response.status_code, getattr(response, "text", ""))
            if failure == "PLAN_GATED":
                plan_status = "PLAN_GATED"
            elif failure == "ACCESS_DENIED":
                plan_status = "ACCESS_DENIED"
            return None, {
                "access_status": failure,
                "plan_status": plan_status,
                "retries": retries,
                "rate_limit_events": rate_limits,
                "rate_limit_diagnostics": rate_limit_diagnostics,
                "rate_limit_stop_reason": None,
                "errors": [f"HTTP_{response.status_code}:{failure}"],
            }
        try:
            payload = response.json()
        except Exception as error:
            return None, {
                "access_status": "REQUEST_ERROR",
                "plan_status": plan_status,
                "retries": retries,
                "rate_limit_events": rate_limits,
                "rate_limit_diagnostics": rate_limit_diagnostics,
                "rate_limit_stop_reason": None,
                "errors": [str(redact_secrets(f"JSON_ERROR:{error}", (api_key,)))],
            }
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        return payload, {
            "access_status": access_status,
            "plan_status": plan_status,
            "retries": retries,
            "rate_limit_events": rate_limits,
            "rate_limit_diagnostics": rate_limit_diagnostics,
            "rate_limit_stop_reason": None,
            "errors": errors,
        }
    raise AssertionError("unreachable")


def _provider_row(ticker: str, candle: dict[str, Any], source_ref: str) -> dict[str, Any] | None:
    date_value = candle.get("date")
    if date_value is None and candle.get("timestamp") is not None:
        raw = candle.get("timestamp")
        unit = "ms" if float(raw) > 10_000_000_000 else "s"
        date_value = pd.to_datetime(raw, unit=unit, utc=True)
    date = _session_date(date_value)
    if pd.isna(date):
        return None
    return {
        "ticker": normalise_ticker(ticker),
        "date": date,
        "raw_open": candle.get("open"),
        "raw_high": candle.get("high"),
        "raw_low": candle.get("low"),
        "raw_close": candle.get("close"),
        "raw_volume": candle.get("volume"),
        "source_ref": source_ref,
    }


def fetch_tradingview(
    sample: pd.DataFrame,
    api_key: str,
    *,
    session: requests.Session | None = None,
    tickers: Iterable[str] | None = None,
) -> dict[str, Any]:
    client = session or requests.Session()
    frames: list[pd.DataFrame] = []
    ticker_status: list[dict[str, Any]] = []
    requests_made = retries = rate_limits = 0
    all_errors: list[str] = []
    rate_limit_diagnostics: list[dict[str, Any]] = []
    terminal_access: str | None = None
    terminal_plan: str | None = None
    terminal_rate_limit: str | None = None

    for ticker in _selected_tickers(sample, tickers):
        payload, meta = _request_json(
            client,
            TRADINGVIEW_ENDPOINT,
            params={"symbol": f"IDX:{ticker}", "market": "indonesia", "resolution": "1D", "count": 1000},
            api_key=api_key,
        )
        requests_made += 1 + int(meta["retries"])
        retries += int(meta["retries"])
        rate_limits += int(meta["rate_limit_events"])
        all_errors.extend(f"{ticker}:{item}" for item in meta["errors"])
        rate_limit_diagnostics.extend(
            {"ticker": ticker, "operation": "tradingview_chart", **event}
            for event in meta["rate_limit_diagnostics"]
        )
        if payload is None:
            ticker_status.append({"ticker": ticker, "status": meta["access_status"], "min_date": None, "max_date": None})
            if meta["access_status"] in {"PLAN_GATED", "ACCESS_DENIED"}:
                terminal_access = meta["access_status"]
                terminal_plan = meta["plan_status"]
                break
            if meta["rate_limit_stop_reason"] in {"MONTH_QUOTA", "UNKNOWN_QUOTA_WINDOW"}:
                terminal_rate_limit = meta["rate_limit_stop_reason"]
                break
            continue
        body = _unwrap(payload)
        if not isinstance(body, dict):
            ticker_status.append({"ticker": ticker, "status": "INVALID_PAYLOAD", "min_date": None, "max_date": None})
            continue
        symbol = str(body.get("symbol", "")).upper()
        exchange = str(body.get("exchange", "")).upper()
        market = str(body.get("market", "")).lower()
        identity_ok = symbol == f"IDX:{ticker}" and exchange == "IDX" and market == "indonesia"
        candles = body.get("candles", [])
        if not identity_ok or not isinstance(candles, list):
            ticker_status.append({"ticker": ticker, "status": "IDENTITY_OR_PAYLOAD_ERROR", "min_date": None, "max_date": None})
            continue
        parsed = [
            row
            for candle in candles
            if isinstance(candle, dict)
            for row in [_provider_row(ticker, candle, f"zapi://tradingview/chart/IDX:{ticker}")]
            if row is not None
        ]
        frame = _provider_frame(pd.DataFrame(parsed)) if parsed else _empty_provider_frame()
        if not frame.empty:
            frames.append(frame)
            ticker_status.append(
                {
                    "ticker": ticker,
                    "status": "SUCCESS",
                    "min_date": frame["date"].min(),
                    "max_date": frame["date"].max(),
                    "rows": len(frame),
                }
            )
        else:
            ticker_status.append({"ticker": ticker, "status": "NO_DATA", "min_date": None, "max_date": None, "rows": 0})

    provider = _provider_frame(pd.concat(frames, ignore_index=True) if frames else _empty_provider_frame())
    return {
        "rows": provider,
        "ticker_status": pd.DataFrame(ticker_status),
        "summary": {
            "access_status": terminal_access or "ACCESSIBLE",
            "plan_status": terminal_plan or "EMPIRICALLY_REACHED",
            "requests_made": requests_made,
            "retries": retries,
            "rate_limit_events": rate_limits,
            "rate_limit_window": _quota_window_state(rate_limit_diagnostics),
            "rate_limit_diagnostics": rate_limit_diagnostics,
            "rate_limit_stop_reason": terminal_rate_limit,
            "request_errors": all_errors,
            "provider_rows": int(len(provider)),
        },
    }


def _investing_identity_candidates(payload: object, ticker: str) -> list[dict[str, Any]]:
    body = _unwrap(payload)
    if not isinstance(body, dict):
        return []
    quotes = body.get("quotes", [])
    if not isinstance(quotes, list):
        return []
    accepted: list[dict[str, Any]] = []
    for item in quotes:
        if not isinstance(item, dict) or normalise_ticker(item.get("symbol")) != normalise_ticker(ticker):
            continue
        identity_text = " ".join(
            str(item.get(key, "")) for key in ("exchange", "country", "type", "name")
        ).casefold()
        if any(token in identity_text for token in ("indonesia", "jakarta", " idx")):
            accepted.append(item)
    return accepted


def fetch_investing(
    sample: pd.DataFrame,
    api_key: str,
    *,
    session: requests.Session | None = None,
    tickers: Iterable[str] | None = None,
) -> dict[str, Any]:
    client = session or requests.Session()
    frames: list[pd.DataFrame] = []
    identity_rows: list[dict[str, Any]] = []
    ticker_status: list[dict[str, Any]] = []
    requests_made = retries = rate_limits = 0
    all_errors: list[str] = []
    rate_limit_diagnostics: list[dict[str, Any]] = []
    terminal_access: str | None = None
    terminal_plan: str | None = None
    terminal_rate_limit: str | None = None

    for ticker in _selected_tickers(sample, tickers):
        search_payload, search_meta = _request_json(
            client,
            INVESTING_SEARCH_ENDPOINT,
            params={"q": ticker, "type": "quotes"},
            api_key=api_key,
        )
        requests_made += 1 + int(search_meta["retries"])
        retries += int(search_meta["retries"])
        rate_limits += int(search_meta["rate_limit_events"])
        all_errors.extend(f"{ticker}:SEARCH:{item}" for item in search_meta["errors"])
        rate_limit_diagnostics.extend(
            {"ticker": ticker, "operation": "investing_search", **event}
            for event in search_meta["rate_limit_diagnostics"]
        )
        if search_payload is None:
            identity_rows.append({"ticker": ticker, "identity_status": search_meta["access_status"], "pair_id": None})
            if search_meta["access_status"] in {"PLAN_GATED", "ACCESS_DENIED"}:
                terminal_access = search_meta["access_status"]
                terminal_plan = search_meta["plan_status"]
                break
            if search_meta["rate_limit_stop_reason"] in {"MONTH_QUOTA", "UNKNOWN_QUOTA_WINDOW"}:
                terminal_rate_limit = search_meta["rate_limit_stop_reason"]
                break
            continue
        candidates = _investing_identity_candidates(search_payload, ticker)
        if len(candidates) != 1:
            status = "IDENTITY_NOT_FOUND" if not candidates else "IDENTITY_AMBIGUOUS"
            identity_rows.append({"ticker": ticker, "identity_status": status, "pair_id": None, "candidate_count": len(candidates)})
            continue
        candidate = candidates[0]
        pair_id = candidate.get("pairId")
        if pair_id is None:
            identity_rows.append({"ticker": ticker, "identity_status": "IDENTITY_NOT_FOUND", "pair_id": None})
            continue
        identity_rows.append(
            {
                "ticker": ticker,
                "identity_status": "IDENTITY_VERIFIED",
                "pair_id": pair_id,
                "exchange": candidate.get("exchange"),
                "country": candidate.get("country"),
                "name": candidate.get("name"),
            }
        )
        historical_payload, historical_meta = _request_json(
            client,
            INVESTING_HISTORICAL_ENDPOINT,
            params={
                "query": ticker,
                "pairId": pair_id,
                "interval": "1d",
                "period": "max",
                "pointscount": INVESTING_POINTSCOUNT,
            },
            api_key=api_key,
        )
        requests_made += 1 + int(historical_meta["retries"])
        retries += int(historical_meta["retries"])
        rate_limits += int(historical_meta["rate_limit_events"])
        all_errors.extend(f"{ticker}:HISTORICAL:{item}" for item in historical_meta["errors"])
        rate_limit_diagnostics.extend(
            {"ticker": ticker, "operation": "investing_historical", **event}
            for event in historical_meta["rate_limit_diagnostics"]
        )
        if historical_payload is None:
            ticker_status.append({"ticker": ticker, "status": historical_meta["access_status"], "min_date": None, "max_date": None})
            if historical_meta["access_status"] in {"PLAN_GATED", "ACCESS_DENIED"}:
                terminal_access = historical_meta["access_status"]
                terminal_plan = historical_meta["plan_status"]
                break
            if historical_meta["rate_limit_stop_reason"] in {"MONTH_QUOTA", "UNKNOWN_QUOTA_WINDOW"}:
                terminal_rate_limit = historical_meta["rate_limit_stop_reason"]
                break
            continue
        body = _unwrap(historical_payload)
        if not isinstance(body, dict) or str(body.get("pairId")) != str(pair_id):
            ticker_status.append({"ticker": ticker, "status": "IDENTITY_OR_PAYLOAD_ERROR", "min_date": None, "max_date": None})
            continue
        candles = body.get("candles", [])
        if not isinstance(candles, list):
            ticker_status.append({"ticker": ticker, "status": "INVALID_PAYLOAD", "min_date": None, "max_date": None})
            continue
        parsed = [
            row
            for candle in candles
            if isinstance(candle, dict)
            for row in [_provider_row(ticker, candle, f"zapi://investing/historical/{pair_id}")]
            if row is not None
        ]
        frame = _provider_frame(pd.DataFrame(parsed)) if parsed else _empty_provider_frame()
        if not frame.empty:
            frames.append(frame)
            ticker_status.append(
                {
                    "ticker": ticker,
                    "status": "SUCCESS",
                    "min_date": frame["date"].min(),
                    "max_date": frame["date"].max(),
                    "rows": len(frame),
                }
            )
        else:
            ticker_status.append({"ticker": ticker, "status": "NO_DATA", "min_date": None, "max_date": None, "rows": 0})

    provider = _provider_frame(pd.concat(frames, ignore_index=True) if frames else _empty_provider_frame())
    return {
        "rows": provider,
        "identity": pd.DataFrame(identity_rows),
        "ticker_status": pd.DataFrame(ticker_status),
        "summary": {
            "access_status": terminal_access or "ACCESSIBLE",
            "plan_status": terminal_plan or "EMPIRICALLY_REACHED",
            "requests_made": requests_made,
            "retries": retries,
            "rate_limit_events": rate_limits,
            "rate_limit_window": _quota_window_state(rate_limit_diagnostics),
            "rate_limit_diagnostics": rate_limit_diagnostics,
            "rate_limit_stop_reason": terminal_rate_limit,
            "request_errors": all_errors,
            "provider_rows": int(len(provider)),
        },
    }


def _audit_input(sample: pd.DataFrame) -> pd.DataFrame:
    return sample[
        [
            "sample_id",
            "sample_role",
            "ticker",
            "date",
            "panel_open",
            "panel_high",
            "panel_low",
            "panel_close",
        ]
    ].copy()


def _history_status_map(ticker_status: pd.DataFrame) -> dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None, str]]:
    result: dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None, str]] = {}
    if ticker_status.empty:
        return result
    for row in ticker_status.itertuples(index=False):
        min_date = pd.Timestamp(row.min_date).normalize() if pd.notna(getattr(row, "min_date", None)) else None
        max_date = pd.Timestamp(row.max_date).normalize() if pd.notna(getattr(row, "max_date", None)) else None
        result[normalise_ticker(row.ticker)] = (min_date, max_date, str(row.status))
    return result


def classify_provider(sample: pd.DataFrame, audit: pd.DataFrame, ticker_status: pd.DataFrame, prefix: str) -> pd.DataFrame:
    data = audit.merge(
        sample[["sample_id", "residual_problem_class", "yahoo_raw_high", "yahoo_raw_low", "yahoo_raw_close"]],
        on="sample_id",
        how="left",
        validate="one_to_one",
    )
    history = _history_status_map(ticker_status)
    classes: list[str] = []
    supports_yahoo: list[bool] = []
    for row in data.itertuples(index=False):
        yahoo_match = (
            pd.notna(row.raw_high)
            and pd.notna(row.raw_low)
            and pd.notna(row.raw_close)
            and row.raw_high == row.yahoo_raw_high
            and row.raw_low == row.yahoo_raw_low
            and row.raw_close == row.yahoo_raw_close
        )
        supports_yahoo.append(bool(yahoo_match))
        if row.sample_role == "KNOWN_CONTROL":
            if bool(row.hlc_exact) and pd.notna(row.known_open_exact) and bool(row.known_open_exact):
                classes.append(f"{prefix}_PANEL_HLC_OPEN_EXACT_CONTROL")
            elif bool(row.hlc_exact):
                classes.append(f"{prefix}_PANEL_HLC_ONLY_CONTROL")
            elif row.diagnostic != "NO_PROVIDER_ROW":
                classes.append(f"{prefix}_HLC_DISAGREEMENT")
            else:
                classes.append(_missing_class(row, history, prefix))
            continue
        if row.admission_status == "ADMISSIBLE_OPEN_EVIDENCE":
            classes.append(f"{prefix}_RECOVERY_CANDIDATE")
        elif row.diagnostic == "NO_PROVIDER_ROW":
            classes.append(_missing_class(row, history, prefix))
        elif bool(row.hlc_exact):
            classes.append(f"{prefix}_PANEL_HLC_MATCH_OPEN_REJECTED")
        else:
            classes.append(f"{prefix}_HLC_DISAGREEMENT")
    data["provider_class"] = classes
    data["provider_hlc_matches_yahoo"] = supports_yahoo
    return data


def _missing_class(row: Any, history: dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None, str]], prefix: str) -> str:
    min_date, max_date, status = history.get(normalise_ticker(row.ticker), (None, None, "NO_STATUS"))
    date = pd.Timestamp(row.date).normalize()
    if status == "SUCCESS" and min_date is not None and max_date is not None and (date < min_date or date > max_date):
        return f"{prefix}_HISTORY_WINDOW_UNAVAILABLE"
    return f"{prefix}_IDENTITY_OR_PROVIDER_ERROR" if prefix == "TV" else f"{prefix}_PROVIDER_ERROR"


def _provider_summary(classified: pd.DataFrame, base_summary: dict[str, Any]) -> dict[str, Any]:
    known = classified["sample_role"].eq("KNOWN_CONTROL")
    missing = ~known
    exact_dates = classified["diagnostic"].ne("NO_PROVIDER_ROW")
    return {
        **base_summary,
        "sample_rows": int(len(classified)),
        "exact_ticker_date_rows": int(exact_dates.sum()),
        "hlc_exact_count": int(classified["hlc_exact"].fillna(False).sum()),
        "known_control_rows": int(known.sum()),
        "known_control_hlc_exact": int(classified.loc[known, "hlc_exact"].fillna(False).sum()),
        "known_control_open_exact": int(classified.loc[known, "known_open_exact"].fillna(False).sum()),
        "missing_open_rows": int(missing.sum()),
        "recovery_candidates": int(classified["provider_class"].str.endswith("RECOVERY_CANDIDATE").sum()),
        "class_counts": {str(k): int(v) for k, v in classified["provider_class"].value_counts().items()},
        "yahoo_mismatch_rows_supporting_provider_yahoo_hlc": int(
            (
                classified["sample_role"].eq("RESIDUAL_HLC_MISMATCH")
                & classified["provider_hlc_matches_yahoo"].fillna(False)
            ).sum()
        ),
    }


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[column]):
            data[column] = data[column].dt.strftime("%Y-%m-%d")
    data.to_csv(path, index=False, lineterminator="\n")


def _write_json(value: object, path: Path) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _load_provider_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return _empty_provider_frame()
    try:
        data = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return _empty_provider_frame()
    return _provider_frame(data)


def _load_status_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame(columns=["ticker", "status", "min_date", "max_date"])
    try:
        data = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=["ticker", "status", "min_date", "max_date"])
    if "ticker" in data.columns:
        data["ticker"] = data["ticker"].map(normalise_ticker)
    return data


def _merge_provider_rows(prior: pd.DataFrame, followup: pd.DataFrame) -> pd.DataFrame:
    if prior.empty and followup.empty:
        return _empty_provider_frame()
    combined = _provider_frame(pd.concat([prior, followup], ignore_index=True))
    return combined.drop_duplicates(["ticker", "date"], keep="first").sort_values(["ticker", "date"]).reset_index(drop=True)


def _merge_status_rows(prior: pd.DataFrame, followup: pd.DataFrame) -> pd.DataFrame:
    if prior.empty and followup.empty:
        return pd.DataFrame(columns=["ticker", "status", "min_date", "max_date"])
    replaced = set(followup["ticker"]) if "ticker" in followup.columns else set()
    retained = prior[~prior["ticker"].isin(replaced)] if not prior.empty and "ticker" in prior.columns else prior
    combined = pd.concat([retained, followup], ignore_index=True)
    return combined.drop_duplicates(["ticker"], keep="last").sort_values("ticker").reset_index(drop=True)


def _merge_identity_rows(prior: pd.DataFrame, followup: pd.DataFrame) -> pd.DataFrame:
    if prior.empty and followup.empty:
        return pd.DataFrame(columns=["ticker", "identity_status", "pair_id"])
    replaced = set(followup["ticker"]) if "ticker" in followup.columns else set()
    retained = prior[~prior["ticker"].isin(replaced)] if not prior.empty and "ticker" in prior.columns else prior
    combined = pd.concat([retained, followup], ignore_index=True)
    return combined.drop_duplicates(["ticker"], keep="last").sort_values("ticker").reset_index(drop=True)


def _candidate_breakdown(sample: pd.DataFrame, prior_audit: pd.DataFrame) -> pd.DataFrame:
    candidates = prior_audit.loc[
        prior_audit["provider_class"].eq("TV_RECOVERY_CANDIDATE"),
        ["sample_id", "provider_class", "admission_status"],
    ].copy()
    fields = sample[["sample_id", "sample_role", "residual_problem_class", "ticker", "date"]].copy()
    data = candidates.merge(fields, on="sample_id", how="inner", validate="one_to_one")
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    data["year"] = data["date"].dt.year.astype("Int64")
    columns = [
        "sample_id",
        "sample_role",
        "residual_problem_class",
        "ticker",
        "date",
        "year",
        "provider_class",
        "admission_status",
    ]
    return data[columns].sort_values(["sample_role", "ticker", "date", "sample_id"]).reset_index(drop=True)


def _empty_provider_result() -> dict[str, Any]:
    return {
        "rows": _empty_provider_frame(),
        "ticker_status": pd.DataFrame(columns=["ticker", "status", "min_date", "max_date"]),
        "summary": {
            "access_status": "SKIPPED",
            "plan_status": "NOT_ATTEMPTED",
            "requests_made": 0,
            "retries": 0,
            "rate_limit_events": 0,
            "rate_limit_window": "none",
            "rate_limit_diagnostics": [],
            "rate_limit_stop_reason": None,
            "request_errors": [],
            "provider_rows": 0,
        },
    }


def _provider_overlap(tv_classified: pd.DataFrame, inv_classified: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    overlap = tv_classified[
        ["sample_id", "raw_open", "raw_high", "raw_low", "raw_close", "diagnostic"]
    ].merge(
        inv_classified[["sample_id", "raw_open", "raw_high", "raw_low", "raw_close", "diagnostic"]],
        on="sample_id",
        suffixes=("_tv", "_inv"),
        validate="one_to_one",
    )
    both = overlap["diagnostic_tv"].ne("NO_PROVIDER_ROW") & overlap["diagnostic_inv"].ne("NO_PROVIDER_ROW")
    overlap["raw_ohlc_exact_between_providers"] = (
        both
        & overlap["raw_open_tv"].eq(overlap["raw_open_inv"])
        & overlap["raw_high_tv"].eq(overlap["raw_high_inv"])
        & overlap["raw_low_tv"].eq(overlap["raw_low_inv"])
        & overlap["raw_close_tv"].eq(overlap["raw_close_inv"])
    )
    return overlap, int(both.sum()), int(overlap["raw_ohlc_exact_between_providers"].sum())


def run_alt_open_followup(
    *,
    sample_manifest_path: str | Path,
    prior_output_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    sample = _load_sample(sample_manifest_path)
    prior = Path(prior_output_dir)
    output = Path(output_dir)
    prior_manifest = prior / "artifact_manifest.json"
    if not prior_manifest.is_file():
        raise FileNotFoundError(f"Prior artifact manifest missing: {prior_manifest}")
    prior_manifest_sha = sha256_file(prior_manifest)
    if prior_manifest_sha != EXPECTED_PRIOR_ARTIFACT_MANIFEST_SHA256:
        raise RuntimeError(f"Prior artifact manifest SHA mismatch: {prior_manifest_sha}")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("ZAPI_API_KEY")
    if not api_key:
        raise RuntimeError("ZAPI_API_KEY is absent; zero provider calls authorized")

    prior_tv_rows = _load_provider_csv(prior / "tradingview_candidate_rows.csv")
    prior_tv_status = _load_status_csv(prior / "tradingview_ticker_status.csv")
    prior_tv_audit = pd.read_csv(prior / "tradingview_row_audit.csv")
    prior_inv_rows = _load_provider_csv(prior / "investing_candidate_rows.csv")
    prior_inv_status = _load_status_csv(prior / "investing_ticker_status.csv")
    prior_inv_identity = pd.read_csv(prior / "investing_identity.csv")

    breakdown = _candidate_breakdown(sample, prior_tv_audit)
    _write_csv(breakdown, output / "tradingview_candidate_breakdown.csv")
    prior_rate_limited = sorted(
        set(prior_tv_status.loc[prior_tv_status["status"].eq("RATE_LIMITED"), "ticker"])
    )
    retry_sample = sample[sample["ticker"].isin(prior_rate_limited)].copy()
    tv_followup = fetch_tradingview(sample, api_key, tickers=prior_rate_limited)
    tv_combined_rows = _merge_provider_rows(prior_tv_rows, tv_followup["rows"])
    tv_combined_status = _merge_status_rows(prior_tv_status, tv_followup["ticker_status"])
    tv_audit, _ = audit_provider_rows(_audit_input(sample), tv_combined_rows, "ZAPI_TRADINGVIEW_CHART")
    tv_classified = classify_provider(sample, tv_audit, tv_combined_status, "TV")
    tv_followup_summary = dict(tv_followup["summary"])
    tv_followup_summary["retry_ticker_count"] = len(prior_rate_limited)
    tv_followup_summary["prior_success_tickers_refetched"] = 0
    tv_combined_summary = _provider_summary(
        tv_classified,
        {**tv_followup["summary"], "provider_rows": int(len(tv_combined_rows))},
    )

    tv_status_values = set(tv_followup["ticker_status"].get("status", pd.Series(dtype=str)))
    tv_quota_clear = (
        bool(prior_rate_limited)
        and not (tv_status_values & {"RATE_LIMITED"})
        and tv_followup["summary"].get("rate_limit_stop_reason") not in {"MONTH_QUOTA", "UNKNOWN_QUOTA_WINDOW"}
    )
    if tv_quota_clear:
        inv_followup = fetch_investing(sample, api_key)
        investing_skip_reason = None
    else:
        inv_followup = _empty_provider_result()
        investing_skip_reason = "TRADINGVIEW_QUOTA_STATUS_NOT_CLEAR"
    inv_combined_rows = _merge_provider_rows(prior_inv_rows, inv_followup["rows"])
    inv_combined_status = _merge_status_rows(prior_inv_status, inv_followup["ticker_status"])
    inv_combined_identity = _merge_identity_rows(prior_inv_identity, inv_followup.get("identity", pd.DataFrame()))
    inv_audit, _ = audit_provider_rows(_audit_input(sample), inv_combined_rows, "ZAPI_INVESTING_HISTORICAL")
    inv_classified = classify_provider(sample, inv_audit, inv_combined_status, "INV")
    inv_summary = _provider_summary(inv_classified, inv_followup["summary"])
    inv_summary["identity_counts"] = (
        {str(k): int(v) for k, v in inv_combined_identity["identity_status"].value_counts().items()}
        if not inv_combined_identity.empty
        else {}
    )
    inv_summary["followup_attempted"] = bool(tv_quota_clear)
    inv_summary["followup_skip_reason"] = investing_skip_reason

    overlap, overlap_rows, overlap_exact = _provider_overlap(tv_classified, inv_classified)
    artifacts = {
        "tradingview_followup_candidate_rows.csv": tv_followup["rows"],
        "tradingview_followup_ticker_status.csv": tv_followup["ticker_status"],
        "tradingview_followup_rate_limit_diagnostics.csv": pd.DataFrame(tv_followup["summary"].get("rate_limit_diagnostics", [])),
        "tradingview_combined_candidate_rows.csv": tv_combined_rows,
        "tradingview_combined_ticker_status.csv": tv_combined_status,
        "tradingview_combined_row_audit.csv": tv_classified,
        "investing_followup_candidate_rows.csv": inv_followup["rows"],
        "investing_followup_ticker_status.csv": inv_followup["ticker_status"],
        "investing_followup_identity.csv": inv_followup.get("identity", pd.DataFrame()),
        "investing_followup_rate_limit_diagnostics.csv": pd.DataFrame(inv_followup["summary"].get("rate_limit_diagnostics", [])),
        "investing_combined_candidate_rows.csv": inv_combined_rows,
        "investing_combined_ticker_status.csv": inv_combined_status,
        "investing_combined_identity.csv": inv_combined_identity,
        "investing_combined_row_audit.csv": inv_classified,
        "provider_overlap.csv": overlap,
    }
    for name, frame in artifacts.items():
        _write_csv(frame, output / name)

    summary = {
        "status": "ZAPI_ALT_OPEN_FOLLOWUP_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "prior_artifact_manifest_sha256": prior_manifest_sha,
        "sample_manifest_sha256": EXPECTED_SAMPLE_SHA256,
        "sample_rows": int(len(sample)),
        "sample_tickers": int(sample["ticker"].nunique()),
        "offline_candidate_breakdown": {
            "rows": int(len(breakdown)),
            "by_role": {str(k): int(v) for k, v in breakdown["sample_role"].value_counts().sort_index().items()},
            "by_year": {str(k): int(v) for k, v in breakdown["year"].value_counts().sort_index().items()},
            "by_ticker": {str(k): int(v) for k, v in breakdown["ticker"].value_counts().sort_index().items()},
        },
        "tradingview_followup": tv_followup_summary,
        "tradingview_combined": tv_combined_summary,
        "investing_followup": inv_summary,
        "investing_combined": inv_summary,
        "provider_overlap_rows": overlap_rows,
        "provider_overlap_raw_ohlc_exact": overlap_exact,
        "execution_grade_promoted": False,
        "bulk_backfill_authorized": False,
        "corporate_action_repair_performed": False,
    }
    _write_json(summary, output / "zapi_alt_open_followup_summary.json")
    manifest_files = sorted(
        path for path in output.iterdir() if path.is_file() and path.name not in {"artifact_manifest.json", "zapi_alt_open_followup_summary.json"}
    )
    manifest = {
        "runtime": "zapi_alt_open_followup_v1_20260811",
        "prior_artifact_manifest_sha256": prior_manifest_sha,
        "files": {path.name: sha256_file(path) for path in manifest_files},
        "execution_grade_promoted": False,
    }
    _write_json(manifest, output / "artifact_manifest.json")
    summary["artifact_manifest_sha256"] = sha256_file(output / "artifact_manifest.json")
    _write_json(summary, output / "zapi_alt_open_followup_summary.json")
    return summary


def run_alt_open_audit(*, sample_manifest_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    sample = _load_sample(sample_manifest_path)
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("ZAPI_API_KEY")
    if not api_key:
        raise RuntimeError("ZAPI_API_KEY is absent; zero provider calls authorized")

    tv = fetch_tradingview(sample, api_key)
    tv_audit, _ = audit_provider_rows(_audit_input(sample), tv["rows"], "ZAPI_TRADINGVIEW_CHART")
    tv_classified = classify_provider(sample, tv_audit, tv["ticker_status"], "TV")
    tv_summary = _provider_summary(tv_classified, tv["summary"])

    investing = fetch_investing(sample, api_key)
    inv_audit, _ = audit_provider_rows(_audit_input(sample), investing["rows"], "ZAPI_INVESTING_HISTORICAL")
    inv_classified = classify_provider(sample, inv_audit, investing["ticker_status"], "INV")
    inv_summary = _provider_summary(inv_classified, investing["summary"])
    inv_summary["identity_counts"] = (
        {str(k): int(v) for k, v in investing["identity"]["identity_status"].value_counts().items()}
        if not investing["identity"].empty
        else {}
    )

    overlap = tv_classified[
        ["sample_id", "raw_open", "raw_high", "raw_low", "raw_close", "diagnostic"]
    ].merge(
        inv_classified[["sample_id", "raw_open", "raw_high", "raw_low", "raw_close", "diagnostic"]],
        on="sample_id",
        suffixes=("_tv", "_inv"),
        validate="one_to_one",
    )
    both = overlap["diagnostic_tv"].ne("NO_PROVIDER_ROW") & overlap["diagnostic_inv"].ne("NO_PROVIDER_ROW")
    overlap["raw_ohlc_exact_between_providers"] = (
        both
        & overlap["raw_open_tv"].eq(overlap["raw_open_inv"])
        & overlap["raw_high_tv"].eq(overlap["raw_high_inv"])
        & overlap["raw_low_tv"].eq(overlap["raw_low_inv"])
        & overlap["raw_close_tv"].eq(overlap["raw_close_inv"])
    )

    artifacts = {
        "tradingview_candidate_rows.csv": tv["rows"],
        "tradingview_ticker_status.csv": tv["ticker_status"],
        "tradingview_row_audit.csv": tv_classified,
        "investing_identity.csv": investing["identity"],
        "investing_candidate_rows.csv": investing["rows"],
        "investing_ticker_status.csv": investing["ticker_status"],
        "investing_row_audit.csv": inv_classified,
        "provider_overlap.csv": overlap,
    }
    for name, frame in artifacts.items():
        _write_csv(frame, output / name)

    summary = {
        "status": "ZAPI_ALT_OPEN_AUDIT_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "sample_manifest_sha256": EXPECTED_SAMPLE_SHA256,
        "sample_rows": int(len(sample)),
        "sample_tickers": int(sample["ticker"].nunique()),
        "tradingview": tv_summary,
        "investing": inv_summary,
        "provider_overlap_rows": int(both.sum()),
        "provider_overlap_raw_ohlc_exact": int(overlap["raw_ohlc_exact_between_providers"].sum()),
        "execution_grade_promoted": False,
        "bulk_backfill_authorized": False,
        "corporate_action_repair_performed": False,
    }
    _write_json(summary, output / "zapi_alt_open_summary.json")
    manifest_files = sorted(
        path for path in output.iterdir() if path.is_file() and path.name not in {"artifact_manifest.json", "zapi_alt_open_summary.json"}
    )
    manifest = {
        "runtime": "zapi_alt_open_audit_v1_20260811",
        "files": {path.name: sha256_file(path) for path in manifest_files},
        "execution_grade_promoted": False,
    }
    _write_json(manifest, output / "artifact_manifest.json")
    summary["artifact_manifest_sha256"] = sha256_file(output / "artifact_manifest.json")
    _write_json(summary, output / "zapi_alt_open_summary.json")
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded Zapi TradingView + Investing Open audit")
    parser.add_argument("--sample-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prior-output-dir")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.prior_output_dir:
        result = run_alt_open_followup(
            sample_manifest_path=args.sample_manifest,
            prior_output_dir=args.prior_output_dir,
            output_dir=args.output_dir,
        )
    else:
        result = run_alt_open_audit(sample_manifest_path=args.sample_manifest, output_dir=args.output_dir)
    print(json.dumps(redact_secrets(result), ensure_ascii=False, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
