"""Run the frozen, bounded Investing.com 1-hour admission pilot."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import hashlib
import json
from pathlib import Path
import time as time_module
from typing import Any
from uuid import uuid4

import pandas as pd

from idx_trade.investing_admission import (
    PILOT_TICKERS,
    PILOT_WINDOWS,
    aggregate_daily,
    compare_daily,
    deterministic_sample_manifest,
    epoch_bounds_for_local_window,
    expected_sessions_for_listing,
    normalize_history_payload,
)


SAMPLE_CATEGORIES = {
    **{ticker: "CONTROL" for ticker in ("BBCA", "BBRI", "BMRI", "TLKM", "ASII", "AMRT", "ICBP", "INDF", "UNTR", "ANTM", "MDKA", "DSSA", "YUPI", "SPRE", "FREN")},
    **{ticker: "LONG" for ticker in ("INDS", "RIGS", "ESSA", "PTBA", "WTON", "SGRO", "KRAS", "MLBI", "NIKL", "ENRG")},
    **{ticker: "MID" for ticker in ("RUNS", "PGUN", "KUAS", "TLDN", "IDEA", "NICL", "OLIV", "SFAN", "NETV", "RMKE")},
    **{ticker: "LOW" for ticker in ("PMUI", "AADI", "BMBL", "PJHB", "HGII", "VERN", "BOAT", "MERI")},
    **{ticker: "WITHIN_LISTED_NO_DATA" for ticker in ("GTBO", "COAL", "BIRD", "ZINC")},
    **{ticker: "IDENTITY_EDGE" for ticker in ("AUTO", "MFIN", "WSKT")},
}
KNOWN_CA_CONTROLS = {("BMRI", "old"): "accepted prior audit corporate-action anomaly control",
                     ("DSSA", "mid"): "accepted prior audit corporate-action anomaly control"}
RETRY_STATUSES = {403, 429, 500, 502, 503, 504}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def parse_date(value: Any) -> date | None:
    if value is None or str(value).strip() in {"", "nan", "NaT"}:
        return None
    return pd.Timestamp(value).date()


def fetch_one(ticker: str, pair_id: str, window, session_dates: set[date]) -> dict[str, Any]:
    """Fetch one pair/window with the frozen one-retry transport contract."""
    from curl_cffi import requests as curl_requests

    start_epoch, end_epoch = epoch_bounds_for_local_window(window)
    request = {
        "ticker": ticker,
        "pair_id": pair_id,
        "market": "indonesia",
        "resolution": "60",
        "from": start_epoch,
        "to": end_epoch,
        "endpoint_template": "https://tvc6.investing.com/{ephemeral-token}/0/0/0/0/history",
    }
    attempts = 0
    retry_count = 0
    statuses: list[int] = []
    last_payload: dict[str, Any] = {"s": "provider_error", "errmsg": "no response"}
    last_error = ""
    retrieved_at = pd.Timestamp.now(tz="UTC").isoformat()
    for attempt in range(2):
        attempts += 1
        token = uuid4().hex
        url = f"https://tvc6.investing.com/{token}/0/0/0/0/history"
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.investing.com/", "Accept": "application/json"}
        try:
            response = curl_requests.get(url, params={"symbol": pair_id, "from": start_epoch, "to": end_epoch, "resolution": "60"}, headers=headers, impersonate="chrome", timeout=30)
            statuses.append(int(response.status_code))
            try:
                last_payload = response.json()
            except ValueError:
                last_payload = {"s": "provider_error", "errmsg": "non-json response"}
            if response.status_code == 200:
                break
            last_error = f"HTTP_{response.status_code}"
        except Exception as exc:  # bounded request: record error and do not hide it
            last_error = type(exc).__name__
        if attempt == 0 and statuses and statuses[-1] in RETRY_STATUSES:
            retry_count += 1
            time_module.sleep(0.5)
            continue
        break
    if statuses and statuses[-1] == 200:
        provider_status = str(last_payload.get("s", "provider_error"))
        final_status = "NO_DATA" if provider_status == "no_data" else ("AVAILABLE" if provider_status == "ok" else "PROVIDER_ERROR")
    else:
        final_status = "PROVIDER_ERROR"
    frame, diagnostics = normalize_history_payload(last_payload, ticker=ticker, pair_id=pair_id, window=window, session_dates=session_dates)
    raw_record = {"request": request, "retrieved_at_utc": retrieved_at, "attempts": attempts,
                  "retry_count": retry_count, "http_statuses": statuses, "final_status": final_status,
                  "error": last_error, "response": last_payload}
    return {"ticker": ticker, "window": window.label, "request": request, "attempts": attempts,
            "retry_count": retry_count, "http_statuses": statuses, "final_status": final_status,
            "error": last_error, "retrieved_at_utc": retrieved_at, "raw_record": raw_record,
            "frame": frame, "diagnostics": diagnostics}


def build_summary(results: list[dict[str, Any]], comparisons: pd.DataFrame, expected_by_key: dict[tuple[str, str], list[str]]) -> dict[str, Any]:
    def rate(n: int, d: int) -> float | None:
        return round(n / d, 6) if d else None

    request_rows = []
    for result in results:
        expected = expected_by_key[(result["ticker"], result["window"])]
        diagnostics = result["diagnostics"]
        returned = set(diagnostics.get("session_dates", []))
        bar_counts = {str(k): int(v) for k, v in diagnostics.get("bar_counts", {}).items()}
        request_rows.append({"ticker": result["ticker"], "window": result["window"], "final_status": result["final_status"],
                             "expected_listed_sessions": len(expected), "returned_sessions": len(returned),
                             "missing_listed_sessions": len(set(expected) - returned),
                             "listed_session_coverage": rate(len(returned), len(expected)),
                             "within_session_days_ge_5": sum(value >= 5 for value in bar_counts.values()),
                             "returned_session_count": len(bar_counts),
                             "within_session_completeness": rate(sum(value >= 5 for value in bar_counts.values()), len(bar_counts)),
                             "raw_rows": diagnostics.get("raw_rows", 0), "admitted_rows": diagnostics.get("admitted_rows", 0),
                             "malformed_rows": diagnostics.get("malformed_rows", 0), "duplicate_rows": diagnostics.get("duplicate_rows", 0),
                             "off_session_rows": diagnostics.get("off_session_rows", 0), "invalid_ohlcv_rows": diagnostics.get("invalid_ohlcv_rows", 0),
                             "http_statuses": result["http_statuses"], "attempts": result["attempts"], "retry_count": result["retry_count"]})
    request_frame = pd.DataFrame(request_rows)
    era_summaries = {}
    thresholds = {"recent": 0.90, "mid": 0.80, "old": 0.80}
    for era, threshold in thresholds.items():
        subset = request_frame[request_frame["window"] == era]
        comparisons_era = comparisons[comparisons["window"] == era] if not comparisons.empty else pd.DataFrame()
        expected = int(subset["expected_listed_sessions"].sum())
        returned = int(subset["returned_sessions"].sum())
        returned_days = int(subset["returned_session_count"].sum())
        complete_days = int(subset["within_session_days_ge_5"].sum())
        era_summaries[era] = {"expected_listed_sessions": expected, "returned_sessions": returned,
                              "listed_session_coverage": rate(returned, expected),
                              "within_session_completeness": rate(complete_days, returned_days),
                              "comparison_rows": len(comparisons_era),
                              "hlc_exact_rate": rate(int(comparisons_era["hlc_exact"].sum()), len(comparisons_era)) if not comparisons_era.empty else None,
                              "volume_near_rate": rate(int(comparisons_era["volume_near"].sum()), len(comparisons_era)) if not comparisons_era.empty else None,
                              "coverage_gate": bool(expected and returned / expected >= threshold),
                              "threshold": threshold}
    final_errors = int((request_frame["final_status"] == "PROVIDER_ERROR").sum())
    structural = int(request_frame[["malformed_rows", "duplicate_rows", "off_session_rows"]].to_numpy().sum())
    open_rows = int(comparisons["open_canonical_present"].sum()) if not comparisons.empty else 0
    open_exact = int(comparisons.loc[comparisons["open_canonical_present"], "open_exact"].sum()) if open_rows else 0
    return {"requested_ticker_window_pairs": len(results), "network_requests": int(request_frame["attempts"].sum()),
            "final_provider_errors": final_errors, "final_provider_error_rate": rate(final_errors, len(results)),
            "retry_count": int(request_frame["retry_count"].sum()), "retry_recovered": int(((request_frame["attempts"] > 1) & (request_frame["final_status"] != "PROVIDER_ERROR")).sum()),
            "http_429_count": sum(429 in statuses for statuses in request_frame["http_statuses"]),
            "structural_rejection_rows": structural, "era_summaries": era_summaries,
            "comparison_rows": len(comparisons),
            "hlc_exact_rate": rate(int(comparisons["hlc_exact"].sum()), len(comparisons)) if not comparisons.empty else None,
            "volume_exact_rate": rate(int(comparisons["volume_exact"].sum()), len(comparisons)) if not comparisons.empty else None,
            "volume_near_rate": rate(int(comparisons["volume_near"].sum()), len(comparisons)) if not comparisons.empty else None,
            "open_canonical_rows": open_rows, "open_exact_rate": rate(open_exact, open_rows),
            "corporate_action_quarantined_rows": int(comparisons.get("corporate_action_quarantined", pd.Series(dtype=bool)).sum()),
            "request_status_counts": request_frame["final_status"].value_counts().to_dict(),
            "gate_contract": {"coverage": thresholds, "hlc_exact_min": 0.90, "volume_near_min": 0.90, "open_exact_min": 0.90},
            "request_rows": request_rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity-census", type=Path, required=True)
    parser.add_argument("--depth-status", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.artifact_root
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"artifact root is non-empty: {root}")
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "normalized").mkdir(parents=True, exist_ok=True)
    identity = pd.read_csv(args.identity_census, dtype={"ticker": str, "pair_id": str})
    identity["ticker"] = identity["ticker"].str.upper()
    security = pd.read_csv(args.security_master, dtype={"ticker": str})
    security["ticker"] = security["ticker"].str.upper()
    security = security.drop_duplicates("ticker", keep="first").set_index("ticker")
    calendar_dates = {pd.Timestamp(value).date() for value in pd.read_csv(args.calendar)["date"]}
    panel = pd.read_parquet(args.panel)
    panel["ticker"] = panel["ticker"].str.upper()
    manifest = {**deterministic_sample_manifest(), "created_before_network": True, "identity_source_sha256": sha256_file(args.identity_census),
                "depth_status_source_sha256": sha256_file(args.depth_status), "security_master_sha256": sha256_file(args.security_master),
                "calendar_sha256": sha256_file(args.calendar), "canonical_panel_sha256": sha256_file(args.panel),
                "request_count_if_all_identities_resolve": len(PILOT_TICKERS) * len(PILOT_WINDOWS)}
    sample_path = root / "sample_manifest.json"
    sample_path.write_bytes(json_bytes(manifest))
    sample_sha = sha256_file(sample_path)
    results: list[dict[str, Any]] = []
    expected_by_key: dict[tuple[str, str], list[str]] = {}
    unresolved = []
    tasks = []
    for ticker in PILOT_TICKERS:
        identity_rows = identity[identity["ticker"] == ticker]
        resolved = identity_rows[identity_rows["identity_final_category"] == "RESOLVED"] if not identity_rows.empty else identity_rows
        pair_id = str(resolved.iloc[0]["pair_id"]) if len(resolved) == 1 else None
        listed_from = parse_date(security.loc[ticker, "listed_from"]) if ticker in security.index else None
        listed_to = parse_date(security.loc[ticker, "listed_to"]) if ticker in security.index else None
        for window in PILOT_WINDOWS:
            expected = expected_sessions_for_listing(calendar_dates, listed_from=listed_from, listed_to=listed_to, window=window)
            expected_by_key[(ticker, window.label)] = expected
            if not pair_id:
                unresolved.append({"ticker": ticker, "window": window.label, "reason": "IDENTITY_UNRESOLVED"})
            else:
                tasks.append((ticker, pair_id, window, {date.fromisoformat(value) for value in expected}))
    (root / "sample_identity_resolution.json").write_bytes(json_bytes({"resolved_tickers": sorted({task[0] for task in tasks}), "unresolved": unresolved, "sample_manifest_sha256": sample_sha}))
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_one, ticker, pair_id, window, session_dates): (ticker, window) for ticker, pair_id, window, session_dates in tasks}
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: (PILOT_TICKERS.index(row["ticker"]), next(index for index, window in enumerate(PILOT_WINDOWS) if window.label == row["window"])))
    normalized_frames = []
    request_records = []
    for result in results:
        raw_path = root / "raw" / f"{result['ticker']}__{result['window']}.json"
        raw_path.write_bytes(json_bytes(result["raw_record"]))
        frame = result["frame"]
        if not frame.empty:
            frame = frame.assign(window=result["window"])
            normalized_frames.append(frame)
        request_records.append({"ticker": result["ticker"], "window": result["window"], "final_status": result["final_status"],
                                "attempts": result["attempts"], "retry_count": result["retry_count"], "http_statuses": json.dumps(result["http_statuses"]),
                                "raw_sha256": sha256_file(raw_path), "admitted_rows": result["diagnostics"]["admitted_rows"],
                                "malformed_rows": result["diagnostics"]["malformed_rows"], "duplicate_rows": result["diagnostics"]["duplicate_rows"],
                                "off_session_rows": result["diagnostics"]["off_session_rows"], "invalid_ohlcv_rows": result["diagnostics"]["invalid_ohlcv_rows"]})
    normalized = pd.concat(normalized_frames, ignore_index=True) if normalized_frames else pd.DataFrame()
    normalized_path = root / "normalized" / "intraday_bars.csv"
    normalized.to_csv(normalized_path, index=False)
    daily_frames = []
    for window in PILOT_WINDOWS:
        subset = normalized[normalized["window"] == window.label] if not normalized.empty else normalized
        daily = aggregate_daily(subset)
        if daily.empty:
            continue
        daily["window"] = window.label
        daily_frames.append(daily)
    daily = pd.concat(daily_frames, ignore_index=True) if daily_frames else pd.DataFrame()
    comparisons = []
    if not daily.empty:
        for window in PILOT_WINDOWS:
            provider = daily[daily["window"] == window.label]
            compared = compare_daily(provider, panel)
            if compared.empty:
                continue
            compared["window"] = window.label
            compared["open_canonical_present"] = compared["open_canonical"].notna()
            compared["corporate_action_quarantined"] = compared.apply(lambda row: (row["ticker"], row["window"]) in KNOWN_CA_CONTROLS, axis=1)
            compared["corporate_action_reason"] = compared.apply(lambda row: KNOWN_CA_CONTROLS.get((row["ticker"], row["window"]), ""), axis=1)
            comparisons.append(compared)
    comparison = pd.concat(comparisons, ignore_index=True) if comparisons else pd.DataFrame()
    comparison_path = root / "normalized" / "daily_comparison.csv"
    comparison.to_csv(comparison_path, index=False)
    request_frame = pd.DataFrame(request_records)
    request_path = root / "request_manifest.csv"
    request_frame.to_csv(request_path, index=False)
    summary = build_summary(results, comparison, expected_by_key)
    summary["sample_manifest_sha256"] = sample_sha
    summary["identity_unresolved"] = unresolved
    summary["sample_unique_tickers"] = len(PILOT_TICKERS)
    summary["sample_unique_dates"] = int(comparison["session_date"].nunique()) if not comparison.empty else 0
    summary["category_counts"] = pd.Series(SAMPLE_CATEGORIES).value_counts().to_dict()
    summary["verdict"] = "PILOT_REJECTED" if summary["final_provider_errors"] or summary["structural_rejection_rows"] else "PILOT_CONDITIONAL_QUARANTINE_REQUIRED"
    summary_path = root / "admission_summary.json"
    summary_path.write_bytes(json_bytes(summary))
    artifact_files = [sample_path, root / "sample_identity_resolution.json", normalized_path, comparison_path, request_path, summary_path]
    artifact_files += sorted((root / "raw").glob("*.json"))
    artifact_manifest = {"contract_version": "investing-intraday-admission-v1", "sample_manifest_sha256": sample_sha,
                         "artifacts": [{"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in artifact_files]}
    artifact_manifest_path = root / "artifact_manifest.json"
    artifact_manifest_path.write_bytes(json_bytes(artifact_manifest))
    print(json.dumps({"artifact_root": str(root), "sample_manifest_sha256": sample_sha, "summary": summary,
                      "artifact_manifest_sha256": sha256_file(artifact_manifest_path)}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
