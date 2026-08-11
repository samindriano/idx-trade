from __future__ import annotations

import argparse
import hashlib
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
from .tier2_open_audit import audit_provider_rows, redact_secrets
from .zapi_alt_open_audit import (
    EXPECTED_SAMPLE_SHA256,
    TRADINGVIEW_ENDPOINT,
    _audit_input,
    _empty_provider_frame,
    _history_status_map,
    _provider_frame,
    _provider_row,
    _session_date,
    _unwrap,
    classify_provider,
    _load_sample,
)


SAMPLE_PATH = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_residual_audit_v1_20260811\zapi_targeted_sample_manifest.csv"
)
PRIOR_ROOT = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_alt_endpoints_audit_v1_20260811"
)
PRIOR_FOLLOWUP_ROOT = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_alt_endpoints_followup_v1_20260811"
)
PANEL_PATH = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet"
)
EXPECTED_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
EXPECTED_PRIOR_ROWS_SHA256 = "5e9b7284629267ba0e04abfb02a95272cb0828c85b35354ff594b75962e78a10"
EXPECTED_PRIOR_AUDIT_SHA256 = "1e6583ae739c58a8b513fe93d564bdcfbf4bc31428733d293941f40d71ab6052"
EXPECTED_PRIOR_MANIFEST_SHA256 = "b5008e9942ca8681499f544c98a8bccda9c1e03b82ceb46ba1fbc45d3b1a6a80"
EXPECTED_TICKERS = 206
PRO_MONTH_LIMIT = 25_000
PRO_MINUTE_LIMIT = 2_000
MCP_ENDPOINT = "https://mcp.zpi.web.id/mcp"
REQUEST_DELAY_SECONDS = 1.05
RATE_LIMIT_MAX_WAIT_SECONDS = 90.0


def _write_json(value: object, path: Path) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[column]):
            data[column] = data[column].dt.strftime("%Y-%m-%d")
    data.to_csv(path, index=False, lineterminator="\n")


def _safe_headers(response: Any) -> dict[str, Any]:
    headers = {str(k).casefold(): v for k, v in (getattr(response, "headers", {}) or {}).items()}
    return {
        "http_status": int(getattr(response, "status_code", 0)),
        "rate_limit_minute": headers.get("x-ratelimit-limit-minute"),
        "remaining_minute": headers.get("x-ratelimit-remaining-minute"),
        "rate_limit_month": headers.get("x-ratelimit-limit-month"),
        "remaining_month": headers.get("x-ratelimit-remaining-month"),
        "plan_expired_present": "x-plan-expired" in headers,
        "retry_after": headers.get("retry-after"),
    }


def _as_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _plan_from_headers(headers: dict[str, Any]) -> str:
    month = _as_int(headers.get("rate_limit_month"))
    minute = _as_int(headers.get("rate_limit_minute"))
    if month == PRO_MONTH_LIMIT and minute == PRO_MINUTE_LIMIT:
        return "PRO"
    if month == 200_000 and minute == 5_000:
        return "ULTRA"
    if month in {600, 2_000} or minute == 100:
        return "FREE_OR_FREE_COMPATIBLE"
    return "UNKNOWN"


def probe_pro_quota(session: requests.Session, api_key: str, *, stage: str) -> dict[str, Any]:
    """Use only safe MCP quota headers; never persist the response body/key."""

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "idx-tradingview-resume", "version": "1.0"},
        },
    }
    try:
        response = session.post(
            MCP_ENDPOINT,
            json=request,
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-06-18",
            },
            timeout=30,
        )
        safe = _safe_headers(response)
        plan = _plan_from_headers(safe)
        return {
            "stage": stage,
            "source": "MCP_SAFE_QUOTA_HEADERS",
            "account_tool_status": "NOT_DISPATCHED_TRANSPORT_ERROR" if response.status_code != 200 else "DISPATCHED_UNVERIFIED",
            "plan_status": plan,
            "quota": safe,
            "pro_limits_confirmed": plan == "PRO" and not safe["plan_expired_present"],
            "response_body_persisted": False,
        }
    except Exception as error:
        return {
            "stage": stage,
            "source": "MCP_SAFE_QUOTA_HEADERS",
            "account_tool_status": "PREFLIGHT_REQUEST_ERROR",
            "plan_status": "UNKNOWN",
            "quota": {},
            "pro_limits_confirmed": False,
            "response_body_persisted": False,
            "error": str(redact_secrets(f"{type(error).__name__}: {error}", (api_key,))),
        }


def _rate_limit_meta(response: Any) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception:
        payload = None
    window = payload.get("window") if isinstance(payload, dict) else None
    if str(window).casefold() not in {"minute", "month"}:
        window = "unknown"
    safe = _safe_headers(response)
    return {
        "window": str(window).casefold(),
        "retry_after": safe.get("retry_after"),
        "remaining_minute": safe.get("remaining_minute"),
        "remaining_month": safe.get("remaining_month"),
        "plan_expired_present": safe.get("plan_expired_present"),
    }


def _request_resume(session: requests.Session, ticker: str, api_key: str) -> tuple[object | None, dict[str, Any]]:
    params = {"symbol": f"IDX:{ticker}", "market": "indonesia", "resolution": "1D", "count": 1000}
    errors: list[str] = []
    retries = rate_limits = 0
    diagnostics: list[dict[str, Any]] = []
    safe_headers: dict[str, Any] = {}
    for attempt in range(1, 4):
        try:
            response = session.get(TRADINGVIEW_ENDPOINT, params=params, headers={"x-api-key": api_key}, timeout=30)
        except Exception as error:
            errors.append(str(redact_secrets(f"{type(error).__name__}: {error}", (api_key,))))
            if attempt < 3:
                retries += 1
                time.sleep(max(REQUEST_DELAY_SECONDS, 1.0))
                continue
            return None, {"attempts": attempt, "retries": retries, "rate_limit_events": rate_limits, "rate_limit_diagnostics": diagnostics, "rate_limit_stop_reason": None, "errors": errors, "safe_headers": safe_headers}
        safe_headers = _safe_headers(response)
        if response.status_code == 429:
            rate_limits += 1
            diagnostic = _rate_limit_meta(response)
            diagnostics.append(diagnostic)
            window = diagnostic["window"]
            if window == "month":
                reason = "MONTH_QUOTA"
            elif window == "unknown":
                reason = "UNKNOWN_QUOTA_WINDOW"
            elif attempt >= 3:
                reason = "MAX_ATTEMPTS"
            else:
                try:
                    wait = float(diagnostic.get("retry_after") or 2.0)
                except (TypeError, ValueError):
                    wait = 2.0
                if wait > RATE_LIMIT_MAX_WAIT_SECONDS:
                    reason = "MINUTE_WAIT_EXCEEDS_BOUND"
                else:
                    retries += 1
                    time.sleep(max(wait, 1.0))
                    continue
            errors.append(f"HTTP_429:{reason}")
            return None, {"attempts": attempt, "retries": retries, "rate_limit_events": rate_limits, "rate_limit_diagnostics": diagnostics, "rate_limit_stop_reason": reason, "errors": errors, "safe_headers": safe_headers}
        if response.status_code != 200:
            errors.append(f"HTTP_{response.status_code}")
            return None, {"attempts": attempt, "retries": retries, "rate_limit_events": rate_limits, "rate_limit_diagnostics": diagnostics, "rate_limit_stop_reason": None, "errors": errors, "safe_headers": safe_headers, "access_status": "REQUEST_ERROR"}
        try:
            payload = response.json()
        except Exception as error:
            errors.append(str(redact_secrets(f"JSON_ERROR:{error}", (api_key,))))
            return None, {"attempts": attempt, "retries": retries, "rate_limit_events": rate_limits, "rate_limit_diagnostics": diagnostics, "rate_limit_stop_reason": None, "errors": errors, "safe_headers": safe_headers}
        time.sleep(REQUEST_DELAY_SECONDS)
        return payload, {"attempts": attempt, "retries": retries, "rate_limit_events": rate_limits, "rate_limit_diagnostics": diagnostics, "rate_limit_stop_reason": None, "errors": errors, "safe_headers": safe_headers}
    raise AssertionError("unreachable")


def _parse_payload(ticker: str, payload: object, provenance: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    body = _unwrap(payload)
    if not isinstance(body, dict):
        return _empty_provider_frame(), {"status": "INVALID_PAYLOAD", "min_date": None, "max_date": None, "rows": 0}
    symbol = str(body.get("symbol", "")).upper()
    exchange = str(body.get("exchange", "")).upper()
    market = str(body.get("market", "")).lower()
    candles = body.get("candles", [])
    if symbol != f"IDX:{ticker}" or exchange != "IDX" or market != "indonesia" or not isinstance(candles, list):
        return _empty_provider_frame(), {"status": "IDENTITY_OR_PAYLOAD_ERROR", "min_date": None, "max_date": None, "rows": 0}
    parsed = []
    for candle in candles:
        if not isinstance(candle, dict):
            continue
        row = _provider_row(ticker, candle, f"zapi://tradingview/chart/IDX:{ticker}")
        if row is not None:
            row["provenance"] = provenance
            parsed.append(row)
    if not parsed:
        return _empty_provider_frame(), {"status": "NO_DATA", "min_date": None, "max_date": None, "rows": 0}
    frame = _provider_frame(pd.DataFrame(parsed))
    frame["provenance"] = provenance
    return frame, {"status": "SUCCESS", "min_date": frame["date"].min(), "max_date": frame["date"].max(), "rows": len(frame)}


def _load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _selected_resume_tickers(prior_status: pd.DataFrame) -> list[str]:
    return sorted(normalise_ticker(value) for value in prior_status.loc[prior_status["status"].eq("RATE_LIMITED"), "ticker"])


def _ticker_hash(tickers: list[str]) -> str:
    return hashlib.sha256(("\n".join(tickers) + "\n").encode("utf-8")).hexdigest()


def _merge_rows(prior: pd.DataFrame, resume: pd.DataFrame) -> pd.DataFrame:
    columns = list(dict.fromkeys([*prior.columns, *resume.columns, "provenance"]))
    combined = pd.concat([prior.reindex(columns=columns), resume.reindex(columns=columns)], ignore_index=True)
    combined = combined.drop_duplicates(["ticker", "date"], keep="first")
    return combined.sort_values(["ticker", "date"]).reset_index(drop=True)


def _merge_status(prior: pd.DataFrame, resume: pd.DataFrame) -> pd.DataFrame:
    replaced = set(resume["ticker"]) if not resume.empty else set()
    retained = prior[~prior["ticker"].isin(replaced)]
    return pd.concat([retained, resume], ignore_index=True).drop_duplicates(["ticker"], keep="last").sort_values("ticker").reset_index(drop=True)


def _arbitration(sample: pd.DataFrame, audit: pd.DataFrame) -> dict[str, int]:
    data = audit.copy()
    if not {"yahoo_raw_high", "yahoo_raw_low", "yahoo_raw_close"}.issubset(data.columns):
        data = data.merge(sample[["sample_id", "yahoo_raw_high", "yahoo_raw_low", "yahoo_raw_close"]], on="sample_id", how="left", validate="one_to_one")
    counts: dict[str, int] = {}
    for _, row in data.iterrows():
        if row.get("diagnostic") == "NO_PROVIDER_ROW":
            label = "UNUSABLE"
        else:
            provider_panel = bool(row.get("hlc_exact", False))
            yahoo = all(
                pd.notna(row.get(name)) and row.get(name) == row.get(yahoo_name)
                for name, yahoo_name in (("raw_high", "yahoo_raw_high"), ("raw_low", "yahoo_raw_low"), ("raw_close", "yahoo_raw_close"))
            )
            if provider_panel and yahoo:
                label = "SUPPORTS_CERTIFIED_PANEL_AND_YAHOO"
            elif provider_panel:
                label = "SUPPORTS_CERTIFIED_PANEL"
            elif yahoo:
                label = "SUPPORTS_YAHOO"
            else:
                label = "DISAGREEMENT"
        counts[label] = counts.get(label, 0) + 1
    return counts


def _metrics(sample: pd.DataFrame, audit: pd.DataFrame, status: pd.DataFrame, base: dict[str, Any]) -> dict[str, Any]:
    data = audit.copy()
    candidate = data[data["provider_class"].eq("TV_RECOVERY_CANDIDATE")].copy()
    if not candidate.empty:
        candidate["year"] = pd.to_datetime(candidate["date"]).dt.year
    by_role = candidate["sample_role"].value_counts().to_dict() if not candidate.empty else {}
    by_problem = candidate["residual_problem_class"].value_counts().to_dict() if not candidate.empty else {}
    by_year = candidate.assign(year=pd.to_datetime(candidate["date"]).dt.year).groupby("year").size().to_dict() if not candidate.empty else {}
    hist = int(data["provider_class"].eq("TV_HISTORY_WINDOW_UNAVAILABLE").sum())
    return {
        **base,
        "final_ticker_count": int(len(status)),
        "final_ticker_status_counts": {str(k): int(v) for k, v in status["status"].value_counts().items()},
        "sample_date_coverage": int(data["diagnostic"].ne("NO_PROVIDER_ROW").sum()),
        "hlc_exact_count": int(data["hlc_exact"].fillna(False).sum()),
        "known_control_hlc_exact": int(data.loc[data["sample_role"].eq("KNOWN_CONTROL"), "hlc_exact"].fillna(False).sum()),
        "known_control_open_exact": int(data.loc[data["sample_role"].eq("KNOWN_CONTROL"), "known_open_exact"].fillna(False).sum()),
        "missing_open_recovery_candidates": int(len(candidate)),
        "recovery_by_sample_role": {str(k): int(v) for k, v in by_role.items()},
        "recovery_by_problem_class": {str(k): int(v) for k, v in by_problem.items()},
        "recovery_by_year": {str(k): int(v) for k, v in by_year.items()},
        "history_window_unavailable": hist,
        "provider_class_counts": {str(k): int(v) for k, v in data["provider_class"].value_counts().items()},
        "yahoo_arbitration": _arbitration(sample, audit),
    }


def _artifact_manifest(output: Path, summary_name: str) -> dict[str, Any]:
    files = sorted(path for path in output.iterdir() if path.is_file() and path.name not in {"artifact_manifest.json", summary_name})
    return {"runtime": "zapi_tradingview_resume_v1_20260811", "files": {path.name: sha256_file(path) for path in files}}


def _finalize_existing(*, sample_manifest_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Finish summaries from a completed network batch without refetching."""

    sample = _load_sample(sample_manifest_path)
    output = Path(output_dir)
    required = (
        "quota_before.json",
        "quota_after.json",
        "tradingview_resume_raw_responses.jsonl",
        "tradingview_resume_rows.csv",
        "tradingview_resume_ticker_status.csv",
        "tradingview_combined_rows_with_provenance.csv",
        "tradingview_combined_ticker_status.csv",
    )
    for name in required:
        if not (output / name).is_file():
            raise FileNotFoundError(output / name)
    prior_manifest = PRIOR_ROOT / "artifact_manifest.json"
    prior_rows_path = PRIOR_ROOT / "tradingview_candidate_rows.csv"
    prior_status_path = PRIOR_ROOT / "tradingview_ticker_status.csv"
    prior_audit_path = PRIOR_ROOT / "tradingview_row_audit.csv"
    followup_manifest = PRIOR_FOLLOWUP_ROOT / "artifact_manifest.json"
    prior_status = _load_csv(prior_status_path)
    selected = _selected_resume_tickers(prior_status)
    successful_prior = sorted(normalise_ticker(value) for value in prior_status.loc[prior_status["status"].eq("SUCCESS"), "ticker"])
    resume_provider = _provider_frame(_load_csv(output / "tradingview_resume_rows.csv"))
    resume_status = _load_csv(output / "tradingview_resume_ticker_status.csv")
    combined_provider = _load_csv(output / "tradingview_combined_rows_with_provenance.csv")
    combined_status = _load_csv(output / "tradingview_combined_ticker_status.csv")
    if "provenance" not in resume_provider.columns:
        resume_provider["provenance"] = "PRO_RESUME"
    if "provenance" not in combined_provider.columns:
        raise RuntimeError("Combined provenance column missing")
    raw_records = [json.loads(line) for line in (output / "tradingview_resume_raw_responses.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    resume_core = _provider_frame(resume_provider)
    combined_core = _provider_frame(combined_provider)
    resume_audit_raw, _ = audit_provider_rows(_audit_input(sample), resume_core, "ZAPI_TRADINGVIEW_CHART_PRO_RESUME")
    resume_classified = classify_provider(sample, resume_audit_raw, resume_status, "TV")
    combined_audit_raw, _ = audit_provider_rows(_audit_input(sample), combined_core, "ZAPI_TRADINGVIEW_CHART_COMBINED")
    combined_classified = classify_provider(sample, combined_audit_raw, combined_status, "TV")
    _write_csv(resume_classified, output / "tradingview_resume_row_audit.csv")
    _write_csv(combined_classified, output / "tradingview_combined_row_audit.csv")
    quota_before = json.loads((output / "quota_before.json").read_text(encoding="utf-8"))
    quota_after = json.loads((output / "quota_after.json").read_text(encoding="utf-8"))
    last_response_headers = raw_records[-1].get("safe_headers", {}) if raw_records else {}
    request_errors = [
        f"{record.get('requested_ticker')}:{error}"
        for record in raw_records
        for error in record.get("meta", {}).get("errors", [])
    ]
    incremental = _metrics(sample, resume_classified, resume_status, {
        "selected_ticker_count": len(selected),
        "selected_ticker_sha256": _ticker_hash(selected),
        "requests_made": sum(int(record.get("meta", {}).get("attempts", 0)) for record in raw_records),
        "retries": sum(int(record.get("meta", {}).get("retries", 0)) for record in raw_records),
        "rate_limit_events": sum(int(record.get("meta", {}).get("rate_limit_events", 0)) for record in raw_records),
        "provider_errors": request_errors,
        "provider_rows": int(len(resume_provider)),
        "successful_tickers": int((resume_status["status"] == "SUCCESS").sum()),
        "failed_tickers": int((resume_status["status"] != "SUCCESS").sum()),
        "quota_before": quota_before,
        "quota_after": quota_after,
        "last_response_quota_headers": last_response_headers,
    })
    combined_errors = [
        {"ticker": str(row.ticker), "status": str(row.status)}
        for row in combined_status.itertuples(index=False)
        if str(row.status) not in {"SUCCESS"}
    ]
    combined = _metrics(sample, combined_classified, combined_status, {
        "prior_success_tickers": 134,
        "prior_success_tickers_refetched": 0,
        "prior_success_ticker_set_disjoint_from_resume": not bool(set(successful_prior) & set(selected)),
        "prior_first_runtime_manifest_sha256": sha256_file(prior_manifest),
        "prior_followup_manifest_sha256": sha256_file(followup_manifest),
        "prior_candidate_rows_sha256": sha256_file(prior_rows_path),
        "prior_audit_sha256": sha256_file(prior_audit_path),
        "new_resume_rows": int(len(resume_provider)),
        "combined_provider_rows": int(len(combined_provider)),
        "deduplicated_by_provider_ticker_date": True,
        "provider_symbol_or_terminal_errors": combined_errors,
    })
    panel_after = sha256_file(PANEL_PATH)
    summary = {
        "status": "ZAPI_TRADINGVIEW_RESUME_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "sample_manifest_sha256": EXPECTED_SAMPLE_SHA256,
        "sample_rows": 240,
        "sample_tickers": 206,
        "incremental_pro_resume": incremental,
        "combined_original_plus_resume": combined,
        "immutable_panel_sha256_before": EXPECTED_PANEL_SHA256,
        "immutable_panel_sha256_after": panel_after,
        "immutable_panel_unchanged": panel_after == EXPECTED_PANEL_SHA256,
        "execution_grade_promoted": False,
        "bulk_backfill_authorized": False,
        "panel_backfill_performed": False,
        "investing_called": False,
        "stock_history_called": False,
        "network_refetch_after_batch": False,
    }
    _write_json(summary, output / "zapi_tradingview_resume_summary.json")
    _write_json(_artifact_manifest(output, "zapi_tradingview_resume_summary.json"), output / "artifact_manifest.json")
    summary["artifact_manifest_sha256"] = sha256_file(output / "artifact_manifest.json")
    _write_json(summary, output / "zapi_tradingview_resume_summary.json")
    return summary


def run_resume(*, sample_manifest_path: str | Path = SAMPLE_PATH, output_dir: str | Path) -> dict[str, Any]:
    sample = _load_sample(sample_manifest_path)
    if len(sample) != 240 or sample["ticker"].nunique() != EXPECTED_TICKERS:
        raise RuntimeError("Frozen sample contract mismatch")
    if not PANEL_PATH.is_file() or sha256_file(PANEL_PATH) != EXPECTED_PANEL_SHA256:
        raise RuntimeError("Immutable panel SHA mismatch before runtime")
    prior_manifest = PRIOR_ROOT / "artifact_manifest.json"
    prior_rows_path = PRIOR_ROOT / "tradingview_candidate_rows.csv"
    prior_status_path = PRIOR_ROOT / "tradingview_ticker_status.csv"
    prior_audit_path = PRIOR_ROOT / "tradingview_row_audit.csv"
    followup_manifest = PRIOR_FOLLOWUP_ROOT / "artifact_manifest.json"
    for path in (prior_manifest, prior_rows_path, prior_status_path, prior_audit_path, followup_manifest):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256_file(prior_manifest) != EXPECTED_PRIOR_MANIFEST_SHA256:
        raise RuntimeError("Prior first-runtime manifest SHA mismatch")
    if sha256_file(prior_rows_path) != EXPECTED_PRIOR_ROWS_SHA256:
        raise RuntimeError("Prior TradingView candidate-row SHA mismatch")
    if sha256_file(prior_audit_path) != EXPECTED_PRIOR_AUDIT_SHA256:
        raise RuntimeError("Prior TradingView audit SHA mismatch")
    prior_status = _load_csv(prior_status_path)
    selected = _selected_resume_tickers(prior_status)
    successful_prior = sorted(normalise_ticker(value) for value in prior_status.loc[prior_status["status"].eq("SUCCESS"), "ticker"])
    if len(selected) != 71 or len(successful_prior) != 134 or set(selected) & set(successful_prior):
        raise RuntimeError("Prior retry-set contract mismatch")
    if "FREN" in selected:
        raise RuntimeError("FREN is not eligible for automatic retry")
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("ZAPI_API_KEY")
    if not api_key:
        raise RuntimeError("ZAPI_API_KEY absent; zero provider calls authorized")
    client = requests.Session()
    quota_before = probe_pro_quota(client, api_key, stage="before")
    _write_json(quota_before, output / "quota_before.json")
    if not quota_before["pro_limits_confirmed"]:
        raise RuntimeError("Pro quota not confirmed before TradingView calls")

    raw_records: list[dict[str, Any]] = []
    resume_rows: list[pd.DataFrame] = []
    resume_status: list[dict[str, Any]] = []
    total_requests = retries = rate_limits = 0
    errors: list[str] = []
    terminal_stop: str | None = None
    for ticker in selected:
        payload, meta = _request_resume(client, ticker, api_key)
        total_requests += int(meta["attempts"])
        retries += int(meta["retries"])
        rate_limits += int(meta["rate_limit_events"])
        errors.extend(f"{ticker}:{error}" for error in meta["errors"])
        raw_records.append({
            "requested_ticker": ticker,
            "request": {"endpoint": TRADINGVIEW_ENDPOINT, "params": {"symbol": f"IDX:{ticker}", "market": "indonesia", "resolution": "1D", "count": 1000}},
            "meta": {key: value for key, value in meta.items() if key != "safe_headers"},
            "safe_headers": meta.get("safe_headers", {}),
            "response": redact_secrets(payload, (api_key,)) if payload is not None else None,
        })
        if payload is None:
            resume_status.append({"ticker": ticker, "status": "RATE_LIMITED" if meta.get("rate_limit_stop_reason") else meta.get("access_status", "REQUEST_ERROR"), "min_date": None, "max_date": None, "rows": 0})
            if meta.get("rate_limit_stop_reason") in {"MONTH_QUOTA", "UNKNOWN_QUOTA_WINDOW"}:
                terminal_stop = meta["rate_limit_stop_reason"]
                break
            continue
        frame, status = _parse_payload(ticker, payload, "PRO_RESUME")
        if not frame.empty:
            resume_rows.append(frame)
        resume_status.append({"ticker": ticker, **status})
    if terminal_stop:
        remaining = [ticker for ticker in selected if ticker not in set(row["ticker"] for row in resume_status)]
        resume_status.extend({"ticker": ticker, "status": "NOT_ATTEMPTED_AFTER_QUOTA_STOP", "min_date": None, "max_date": None, "rows": 0} for ticker in remaining)
    resume_provider = _provider_frame(pd.concat(resume_rows, ignore_index=True) if resume_rows else _empty_provider_frame())
    resume_provider["provenance"] = "PRO_RESUME"
    resume_status_df = pd.DataFrame(resume_status).sort_values("ticker").reset_index(drop=True)
    prior_provider = _provider_frame(_load_csv(prior_rows_path))
    prior_provider["provenance"] = "ORIGINAL_RUN"
    combined_provider = _merge_rows(prior_provider, resume_provider)
    combined_status = _merge_status(prior_status, resume_status_df)
    prior_audit = _load_csv(prior_audit_path)
    combined_core = _provider_frame(combined_provider)
    resume_core = _provider_frame(resume_provider)
    resume_audit_raw, _ = audit_provider_rows(_audit_input(sample), resume_core, "ZAPI_TRADINGVIEW_CHART_PRO_RESUME")
    resume_classified = classify_provider(sample, resume_audit_raw, resume_status_df, "TV")
    combined_audit_raw, _ = audit_provider_rows(_audit_input(sample), combined_core, "ZAPI_TRADINGVIEW_CHART_COMBINED")
    combined_classified = classify_provider(sample, combined_audit_raw, combined_status, "TV")
    quota_after = probe_pro_quota(client, api_key, stage="after")
    last_response_headers = raw_records[-1].get("safe_headers", {}) if raw_records else {}
    _write_jsonl(raw_records, output / "tradingview_resume_raw_responses.jsonl")
    _write_csv(resume_provider, output / "tradingview_resume_rows.csv")
    _write_csv(resume_status_df, output / "tradingview_resume_ticker_status.csv")
    _write_csv(resume_classified, output / "tradingview_resume_row_audit.csv")
    _write_csv(combined_provider, output / "tradingview_combined_rows_with_provenance.csv")
    _write_csv(combined_status, output / "tradingview_combined_ticker_status.csv")
    _write_csv(combined_classified, output / "tradingview_combined_row_audit.csv")
    _write_json(quota_after, output / "quota_after.json")
    panel_after = sha256_file(PANEL_PATH)
    incremental = _metrics(sample, resume_classified, resume_status_df, {
        "selected_ticker_count": len(selected),
        "selected_ticker_sha256": _ticker_hash(selected),
        "requests_made": total_requests,
        "retries": retries,
        "rate_limit_events": rate_limits,
        "provider_errors": errors,
        "provider_rows": int(len(resume_provider)),
        "successful_tickers": int((resume_status_df["status"] == "SUCCESS").sum()),
        "failed_tickers": int((resume_status_df["status"] != "SUCCESS").sum()),
        "quota_before": quota_before,
        "quota_after": quota_after,
        "last_response_quota_headers": last_response_headers,
    })
    combined = _metrics(sample, combined_classified, combined_status, {
        "prior_success_tickers": 134,
        "prior_success_tickers_refetched": 0,
        "prior_success_ticker_set_disjoint_from_resume": not bool(set(successful_prior) & set(selected)),
        "prior_first_runtime_manifest_sha256": sha256_file(prior_manifest),
        "prior_followup_manifest_sha256": sha256_file(followup_manifest),
        "prior_candidate_rows_sha256": sha256_file(prior_rows_path),
        "prior_audit_sha256": sha256_file(prior_audit_path),
        "new_resume_rows": int(len(resume_provider)),
        "combined_provider_rows": int(len(combined_provider)),
        "deduplicated_by_provider_ticker_date": True,
    })
    summary = {
        "status": "ZAPI_TRADINGVIEW_RESUME_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "sample_manifest_sha256": EXPECTED_SAMPLE_SHA256,
        "sample_rows": 240,
        "sample_tickers": 206,
        "incremental_pro_resume": incremental,
        "combined_original_plus_resume": combined,
        "immutable_panel_sha256_before": EXPECTED_PANEL_SHA256,
        "immutable_panel_sha256_after": panel_after,
        "immutable_panel_unchanged": panel_after == EXPECTED_PANEL_SHA256,
        "execution_grade_promoted": False,
        "bulk_backfill_authorized": False,
        "panel_backfill_performed": False,
        "investing_called": False,
        "stock_history_called": False,
        "terminal_stop": terminal_stop,
    }
    _write_json(summary, output / "zapi_tradingview_resume_summary.json")
    manifest = _artifact_manifest(output, "zapi_tradingview_resume_summary.json")
    _write_json(manifest, output / "artifact_manifest.json")
    summary["artifact_manifest_sha256"] = sha256_file(output / "artifact_manifest.json")
    _write_json(summary, output / "zapi_tradingview_resume_summary.json")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Resume only unfinished Zapi TradingView tickers")
    parser.add_argument("--sample-manifest", default=str(SAMPLE_PATH))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--finalize-existing", action="store_true")
    args = parser.parse_args()
    result = _finalize_existing(sample_manifest_path=args.sample_manifest, output_dir=args.output_dir) if args.finalize_existing else run_resume(sample_manifest_path=args.sample_manifest, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
