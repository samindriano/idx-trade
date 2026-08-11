from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

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
                "errors": errors,
            }
        if response.status_code == 429:
            rate_limits += 1
            if attempt < 3:
                retries += 1
                try:
                    wait = max(float(response.headers.get("Retry-After", "2")), 1.0)
                except ValueError:
                    wait = 2.0
                time.sleep(wait)
                continue
            return None, {
                "access_status": "RATE_LIMITED",
                "plan_status": plan_status,
                "retries": retries,
                "rate_limit_events": rate_limits,
                "errors": errors + ["HTTP_429:RATE_LIMITED"],
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
                "errors": [str(redact_secrets(f"JSON_ERROR:{error}", (api_key,)))],
            }
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        return payload, {
            "access_status": access_status,
            "plan_status": plan_status,
            "retries": retries,
            "rate_limit_events": rate_limits,
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


def fetch_tradingview(sample: pd.DataFrame, api_key: str, *, session: requests.Session | None = None) -> dict[str, Any]:
    client = session or requests.Session()
    frames: list[pd.DataFrame] = []
    ticker_status: list[dict[str, Any]] = []
    requests_made = retries = rate_limits = 0
    all_errors: list[str] = []
    terminal_access: str | None = None
    terminal_plan: str | None = None

    for ticker in sorted(sample["ticker"].unique()):
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
        if payload is None:
            ticker_status.append({"ticker": ticker, "status": meta["access_status"], "min_date": None, "max_date": None})
            if meta["access_status"] in {"PLAN_GATED", "ACCESS_DENIED"}:
                terminal_access = meta["access_status"]
                terminal_plan = meta["plan_status"]
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


def fetch_investing(sample: pd.DataFrame, api_key: str, *, session: requests.Session | None = None) -> dict[str, Any]:
    client = session or requests.Session()
    frames: list[pd.DataFrame] = []
    identity_rows: list[dict[str, Any]] = []
    ticker_status: list[dict[str, Any]] = []
    requests_made = retries = rate_limits = 0
    all_errors: list[str] = []
    terminal_access: str | None = None
    terminal_plan: str | None = None

    for ticker in sorted(sample["ticker"].unique()):
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
        if search_payload is None:
            identity_rows.append({"ticker": ticker, "identity_status": search_meta["access_status"], "pair_id": None})
            if search_meta["access_status"] in {"PLAN_GATED", "ACCESS_DENIED"}:
                terminal_access = search_meta["access_status"]
                terminal_plan = search_meta["plan_status"]
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
        if historical_payload is None:
            ticker_status.append({"ticker": ticker, "status": historical_meta["access_status"], "min_date": None, "max_date": None})
            if historical_meta["access_status"] in {"PLAN_GATED", "ACCESS_DENIED"}:
                terminal_access = historical_meta["access_status"]
                terminal_plan = historical_meta["plan_status"]
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
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run_alt_open_audit(sample_manifest_path=args.sample_manifest, output_dir=args.output_dir)
    print(json.dumps(redact_secrets(result), ensure_ascii=False, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
