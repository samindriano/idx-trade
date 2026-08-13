"""Run the frozen bounded TradingView 2021-2026 admission pilot."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import subprocess
from typing import Any

import pandas as pd

from idx_trade.tradingview_admission import evaluate_frozen_verdict, verify_input_hashes
from idx_trade.tradingview_intraday import aggregate_daily, normalize_periods
from idx_trade.tradingview_remediation import sha256_file, three_way_reconciliation, volume_ratio_diagnostics


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n").encode("utf-8")


def run_node(adapter: Path, request: dict[str, Any], timeout_s: float) -> tuple[dict[str, Any], str | None]:
    try:
        completed = subprocess.run(
            ["node", str(adapter), json.dumps(request, separators=(",", ":"))],
            capture_output=True, text=True, timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return {"request": request, "server": request["server"], "status": "TRANSPORT_TIMEOUT", "errors": ["runner subprocess timeout"], "periods": [], "event_trace": ["runner_timeout"]}, str(exc)
    if completed.returncode != 0:
        return {"request": request, "server": request["server"], "status": "TRANSPORT_ERROR", "errors": [completed.stderr[-2000:]], "periods": [], "event_trace": ["runner_error"]}, completed.stderr[-2000:]
    try:
        return json.loads(completed.stdout), None
    except json.JSONDecodeError:
        return {"request": request, "server": request["server"], "status": "TRANSPORT_ERROR", "errors": ["invalid adapter JSON"], "periods": [], "event_trace": ["invalid_json"]}, completed.stdout[-2000:]


def raw_path(root: Path, request: dict[str, Any]) -> Path:
    return root / "raw" / "mathieu" / (
        f"{request['request_index']:04d}_{request['phase']}_{request['ticker']}_{request['era']}_{request['timeframe']}.json"
    )


def mark_network_started(root: Path) -> None:
    path = root / "pre_network_preparation.json"
    prep = json.loads(path.read_text(encoding="utf-8"))
    prep["network_started"] = True
    prep["network_started_at_utc"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    path.write_bytes(json_bytes(prep))


def execute_mathieu(manifest: dict[str, Any], adapter: Path, root: Path) -> list[dict[str, Any]]:
    plans = manifest["mathieu_plan"]
    results: list[dict[str, Any]] = []
    network_started = False
    for position, request in enumerate(plans, start=1):
        path = raw_path(root, request)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            results.append(payload)
            response = payload["response"]
            print(json.dumps({"progress": f"{position}/{len(plans)}", "reused": True, "phase": request["phase"], "ticker": request["ticker"], "year": request.get("year"), "status": response.get("status")}), flush=True)
            continue
        if not network_started:
            mark_network_started(root)
            network_started = True
        response, stderr = run_node(adapter, request, float(request.get("timeout_ms", 25000)) / 1000.0 + 20)
        payload = {"adapter_commit": manifest["mathieu_commit"], "request": request, "response": response, "adapter_stderr": stderr}
        path.write_bytes(json_bytes(payload))
        results.append(payload)
        print(json.dumps({"progress": f"{position}/{len(plans)}", "phase": request["phase"], "ticker": request["ticker"], "year": request.get("year"), "status": response.get("status"), "periods": len(response.get("periods") or [])}), flush=True)
    return results


def execute_endenwer(manifest: dict[str, Any], entry: Path, wrapper: Path, root: Path) -> list[dict[str, Any]]:
    plans = manifest["endenwer_plan"]
    results: list[dict[str, Any]] = []
    for position, request in enumerate(plans, start=1):
        path = root / "raw" / "endenwer" / f"{request['request_index']:04d}_{request['ticker']}_deep_2021_2026.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            results.append(payload)
            print(json.dumps({"endenwer_progress": f"{position}/{len(plans)}", "reused": True, "ticker": request["ticker"], "status": payload["response"].get("status")}), flush=True)
            continue
        completed = subprocess.run(
            ["node", str(wrapper), str(entry), json.dumps(request, separators=(",", ":"))],
            capture_output=True, text=True, timeout=90,
        )
        if completed.returncode == 0:
            response = json.loads(completed.stdout)
            stderr = completed.stderr[-2000:] if completed.stderr else None
        else:
            response = {"request": request, "status": "TRANSPORT_ERROR", "error": completed.stderr[-2000:], "periods": []}
            stderr = completed.stderr[-2000:]
        payload = {"client_commit": manifest["endenwer_commit"], "request": request, "response": response, "stderr": stderr}
        path.write_bytes(json_bytes(payload))
        results.append(payload)
        print(json.dumps({"endenwer_progress": f"{position}/{len(plans)}", "ticker": request["ticker"], "status": response.get("status"), "periods": len(response.get("periods") or [])}), flush=True)
    return results


def official_sessions(calendar: set[date], start: str, end: str) -> set[date] | None:
    selected = {value for value in calendar if date.fromisoformat(start) <= value <= date.fromisoformat(end)}
    return selected or None


def normalize_mathieu(results: list[dict[str, Any]], calendar_dates: set[date]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    rows: list[dict[str, Any]] = []
    for payload in results:
        request = payload["request"]
        response = payload["response"]
        frame, diag = normalize_periods(
            response.get("periods", []), ticker=request["ticker"], symbol=request["symbol"], server="prodata",
            phase=request["phase"], era=request["era"], timeframe=request["timeframe"], adjustment=request["adjustment"],
            requested_start=date.fromisoformat(request["start"]), requested_end=date.fromisoformat(request["end"]),
            official_sessions=official_sessions(calendar_dates, request["start"], request["end"]),
        )
        if not frame.empty:
            frame["year"] = request.get("year")
            frame["request_index"] = request["request_index"]
            frames.append(frame)
        periods = response.get("periods") or []
        epochs = [period.get("time") for period in periods if isinstance(period, dict) and isinstance(period.get("time"), (int, float))]
        observation = response.get("event_observation") or {}
        fetch_more = response.get("fetch_more") or {}
        steps = fetch_more.get("steps") or []
        rows.append({
            "request_index": request["request_index"], "phase": request["phase"], "ticker": request["ticker"], "year": request.get("year"), "era": request["era"],
            "timeframe": request["timeframe"], "status": response.get("status"), "errors": json.dumps(response.get("errors") or response.get("error")),
            "period_count": len(periods), "first_epoch": min(epochs) if epochs else None, "last_epoch": max(epochs) if epochs else None,
            "elapsed_ms": response.get("elapsed_ms"), "event_trace": json.dumps(response.get("event_trace", [])),
            "symbol_loaded": bool(observation.get("symbol_loaded")), "websocket_connected": bool(observation.get("websocket_connected")),
            "update_seen": bool(observation.get("update_seen")), "market_info_present": bool(response.get("market_info")),
            "fetch_more_steps_requested": fetch_more.get("requested_steps", request.get("fetch_more_steps", 0)),
            "fetch_more_steps_extended": fetch_more.get("extended_steps", sum(bool(step.get("extended")) for step in steps)),
            "fetch_more_completion_reason": fetch_more.get("completion_reason"),
            **{key: value for key, value in diag.items() if key not in {"session_dates", "timezone_hours"}},
            "session_dates": json.dumps(diag.get("session_dates", [])), "timezone_hours": json.dumps(diag.get("timezone_hours", [])),
        })
    bars = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return bars, pd.DataFrame(rows)


def load_corporate_action_keys(path: Path) -> tuple[set[tuple[str, str]], str]:
    frame = pd.read_csv(path, dtype=str)
    frame["ticker"] = frame["ticker"].astype(str).str.upper()
    frame["effective_date"] = pd.to_datetime(frame["effective_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    keys = {(row.ticker, row.effective_date) for row in frame.itertuples() if row.effective_date and row.action in {"stockSplit", "reverseStock"}}
    return keys, sha256_file(path)


def listing_status(record: dict[str, Any], start: date, end: date) -> bool:
    listed_from = date.fromisoformat(record["listed_from"]) if record.get("listed_from") else None
    listed_to = date.fromisoformat(record["listed_to"]) if record.get("listed_to") else None
    return (listed_from is None or listed_from <= end) and (listed_to is None or listed_to >= start)


def fixed_coverage_metrics(bars: pd.DataFrame, requests: pd.DataFrame, sample: list[dict[str, Any]], windows: list[dict[str, Any]]) -> dict[str, Any]:
    fixed_requests = requests[requests["phase"].eq("fixed_60m")].copy()
    if not fixed_requests.empty:
        fixed_requests["symbol_resolved"] = fixed_requests["symbol_loaded"] | fixed_requests["status"].ne("SYMBOL_ERROR")
    observed = bars[(bars["phase"] == "fixed_60m") & bars["in_requested_window"] & bars["session_admissible"]].copy() if not bars.empty else pd.DataFrame()
    observed_keys = set(zip(observed["ticker"], observed["year"], observed["session_date"])) if not observed.empty else set()
    sample_by_ticker = {row["ticker"]: row for row in sample}
    pair_rows: list[dict[str, Any]] = []
    for window in windows:
        year = int(window["year"])
        start, end = date.fromisoformat(window["start"]), date.fromisoformat(window["end"])
        expected_dates = set(window["official_session_dates"])
        for ticker in sorted(sample_by_ticker):
            listed = listing_status(sample_by_ticker[ticker], start, end)
            request = fixed_requests[(fixed_requests["ticker"] == ticker) & (fixed_requests["year"] == year)]
            if request.empty:
                continue
            request_row = request.iloc[0]
            observed_dates = {session_date for t, y, session_date in observed_keys if t == ticker and int(y) == year}
            pair_rows.append({
                "ticker": ticker, "year": year, "listed": listed, "symbol_resolved": bool(request_row["symbol_loaded"] or request_row["status"] != "SYMBOL_ERROR"),
                "has_any_exact_session": bool(observed_dates), "observed_session_count": len(observed_dates), "expected_session_count": len(expected_dates),
            })
    pair = pd.DataFrame(pair_rows)
    listed = pair[pair["listed"]].copy()
    def year_stats(group: pd.DataFrame) -> dict[str, Any]:
        expected = int(group["expected_session_count"].sum())
        observed_count = int(group["observed_session_count"].sum())
        return {
            "requested_pairs": int(len(group)), "known_listed_pairs": int(group["listed"].sum()),
            "available_pairs": int(group["has_any_exact_session"].sum()),
            "target_window_availability_rate": float(group["has_any_exact_session"].mean()) if len(group) else None,
            "observed_sessions": observed_count, "expected_sessions": expected,
            "certified_session_coverage_rate": float(observed_count / expected) if expected else None,
            "symbol_resolution_rate": float(group["symbol_resolved"].mean()) if len(group) else None,
        }
    by_year = {str(year): year_stats(listed[listed["year"] == year]) for year in sorted(listed["year"].unique())}
    symbol_rate = float(fixed_requests["symbol_resolved"].mean()) if not fixed_requests.empty else None
    return {
        "pair_rows": pair,
        "fixed_request_count": int(len(fixed_requests)),
        "symbol_resolution_rate": symbol_rate,
        "by_year": by_year,
        "symbol_resolution_by_year": {year: values.get("symbol_resolution_rate") for year, values in by_year.items()},
        "known_listed_pairs": int(len(listed)),
        "available_pairs": int(listed["has_any_exact_session"].sum()) if not listed.empty else 0,
        "target_window_availability_rate": float(listed["has_any_exact_session"].mean()) if not listed.empty else None,
        "observed_sessions": int(listed["observed_session_count"].sum()) if not listed.empty else 0,
        "expected_sessions": int(listed["expected_session_count"].sum()) if not listed.empty else 0,
        "certified_session_coverage_rate": float(listed["observed_session_count"].sum() / listed["expected_session_count"].sum()) if not listed.empty and listed["expected_session_count"].sum() else None,
    }


def _daily_rates(frame: pd.DataFrame, years: list[int], *, minimum_rows: int, volume: bool = False) -> dict[str, Any]:
    by_year: dict[str, Any] = {}
    for year in years:
        current = frame[frame["year"].eq(year)] if not frame.empty else frame
        if current.empty:
            by_year[str(year)] = {"matched_rows": 0, "rate": None}
            continue
        if volume:
            rate = float(current["volume_near"].mean())
        else:
            rate = float(current["hlc_exact"].mean())
        by_year[str(year)] = {"matched_rows": int(len(current)), "rate": rate, "sufficient_rows": len(current) >= minimum_rows}
    return by_year


def make_range_summary(years: list[int], coverage: dict[str, Any], comparison: pd.DataFrame, tv1d_comparison: pd.DataFrame, tv60_tv1d: pd.DataFrame, minimum_rows: int) -> dict[str, Any]:
    selected_coverage = [coverage["by_year"].get(str(year), {}) for year in years]
    matched = comparison[comparison["year"].isin(years)] if not comparison.empty else comparison
    clean = matched[~matched["corporate_action_quarantined"]] if not matched.empty else matched
    tv1d_selected = tv1d_comparison[tv1d_comparison["year"].isin(years)] if not tv1d_comparison.empty else tv1d_comparison
    tv1d_clean = tv1d_selected[~tv1d_selected["corporate_action_quarantined"]] if not tv1d_selected.empty else tv1d_selected
    open_pair = tv60_tv1d[tv60_tv1d["year"].isin(years)] if not tv60_tv1d.empty else tv60_tv1d
    open_pair = open_pair[open_pair["corporate_action_quarantined"] == False] if not open_pair.empty else open_pair
    open_present = open_pair.dropna(subset=["open_tv60", "open_tv1d"]) if not open_pair.empty else open_pair
    tv1d_open_present = tv1d_clean[tv1d_clean["open_canonical_present"]] if not tv1d_clean.empty else tv1d_clean
    tv1d_reference_frame = tv1d_clean.copy()
    if not tv1d_reference_frame.empty:
        tv1d_reference_frame["hlc_exact"] = tv1d_reference_frame["hlc_exact"] & (~tv1d_reference_frame["open_canonical_present"] | tv1d_reference_frame["open_exact"])
    return {
        "symbol_resolution_rate": float(sum((item.get("symbol_resolution_rate") or 0.0) * item.get("known_listed_pairs", 0) for item in selected_coverage) / sum(item.get("known_listed_pairs", 0) for item in selected_coverage)) if selected_coverage and sum(item.get("known_listed_pairs", 0) for item in selected_coverage) else None,
        "target_window_availability_rate": float(sum(item.get("available_pairs", 0) for item in selected_coverage) / sum(item.get("known_listed_pairs", 0) for item in selected_coverage)) if selected_coverage and sum(item.get("known_listed_pairs", 0) for item in selected_coverage) else None,
        "certified_session_coverage_rate": float(sum(item.get("observed_sessions", 0) for item in selected_coverage) / sum(item.get("expected_sessions", 0) for item in selected_coverage)) if selected_coverage and sum(item.get("expected_sessions", 0) for item in selected_coverage) else None,
        "hlc_exact_rate": float(clean["hlc_exact"].mean()) if not clean.empty else None,
        "hlc_exact_rows": int(len(clean)),
        "volume_within_5pct_rate": float(clean["volume_near"].mean()) if not clean.empty else None,
        "tv1d_reference_exact_rate": float((tv1d_clean["hlc_exact"] & (~tv1d_clean["open_canonical_present"] | tv1d_clean["open_exact"])).mean()) if not tv1d_clean.empty else None,
        "tv1d_reference_exact_rows": int(len(tv1d_clean)),
        "tv60_open_vs_tv1d_exact_rate": float(open_present["open_exact"].mean()) if not open_present.empty else None,
        "tv60_open_vs_tv1d_rows": int(len(open_present)),
        "target_window_availability_by_year": {str(year): coverage["by_year"].get(str(year), {}).get("target_window_availability_rate") for year in years},
        "certified_session_coverage_by_year": {str(year): coverage["by_year"].get(str(year), {}).get("certified_session_coverage_rate") for year in years},
        "hlc_exact_by_year": _daily_rates(clean, years, minimum_rows=minimum_rows),
        "volume_within_5pct_by_year": _daily_rates(clean, years, minimum_rows=minimum_rows, volume=True),
        "tv1d_reference_exact_by_year": _daily_rates(tv1d_reference_frame, years, minimum_rows=minimum_rows),
    }


def hash_manifest(root: Path) -> str:
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            entries.append({"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest_path = root / "artifact_manifest.json"
    manifest_path.write_bytes(json_bytes({"schema": "idx-trade/tradingview-historical-intraday-admission-pilot-artifact-manifest-v1", "artifacts": entries}))
    return sha256_file(manifest_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--corporate-actions", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--endenwer-entry", type=Path)
    parser.add_argument("--endenwer-wrapper", type=Path)
    args = parser.parse_args()
    root = args.artifact_root
    manifest = json.loads(args.sample_manifest.read_text(encoding="utf-8"))
    if not manifest.get("created_before_network") or not (root / "pre_network_preparation.json").exists():
        raise SystemExit("pilot requires a prepared pre-network artifact root")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    expected = manifest["input_hashes"]
    actual = {
        "config_sha256": sha256_file(args.config), "canonical_panel_sha256": sha256_file(args.panel),
        "official_calendar_sha256": sha256_file(args.calendar), "security_master_sha256": sha256_file(args.security_master),
    }
    verify_input_hashes(expected, actual)
    (root / "input_manifest.json").write_bytes(json_bytes({"hashes": actual, "paths": {"config": str(args.config), "calendar": str(args.calendar), "panel": str(args.panel), "corporate_actions": str(args.corporate_actions)}, "corporate_actions_sha256": sha256_file(args.corporate_actions)}))
    calendar_dates = {pd.Timestamp(value).date() for value in pd.read_csv(args.calendar)["date"]}
    windows = manifest["yearly_windows"]
    mathieu_results = execute_mathieu(manifest, args.adapter, root)
    bars, request_frame = normalize_mathieu(mathieu_results, calendar_dates)
    bars.to_csv(root / "normalized" / "mathieu_intraday_bars.csv", index=False)
    request_frame.to_csv(root / "normalized" / "mathieu_request_manifest.csv", index=False)

    canonical = pd.read_parquet(args.panel)
    canonical["ticker"] = canonical["ticker"].astype(str).str.upper()
    canonical["date"] = pd.to_datetime(canonical["date"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        canonical[column] = pd.to_numeric(canonical[column], errors="coerce")
    fixed_bars = bars[bars["phase"].eq("fixed_60m")].copy()
    daily = aggregate_daily(fixed_bars)
    daily = daily.rename(columns={"server": "provider_server"})
    ca_keys, ca_sha = load_corporate_action_keys(args.corporate_actions)
    daily["corporate_action_quarantined"] = [
        (str(ticker).upper(), str(session_date)) in ca_keys for ticker, session_date in zip(daily.get("ticker", []), daily.get("session_date", []))
    ]
    canonical_daily = canonical[["ticker", "date", "open", "high", "low", "close", "volume"]].copy()
    canonical_daily["session_date"] = canonical_daily["date"].dt.strftime("%Y-%m-%d")
    daily_compare = daily.merge(canonical_daily.drop(columns=["date"]), on=["ticker", "session_date"], how="inner", suffixes=("", "_canonical")) if not daily.empty else pd.DataFrame()
    if not daily_compare.empty:
        for field in ["open", "high", "low", "close", "volume"]:
            daily_compare[f"{field}_exact"] = daily_compare[field].eq(daily_compare[f"{field}_canonical"])
            daily_compare[f"{field}_near"] = (daily_compare[field] - daily_compare[f"{field}_canonical"]).abs() <= 0.05 * daily_compare[f"{field}_canonical"].abs().clip(lower=1.0)
        daily_compare["open_canonical_present"] = daily_compare["open_canonical"].notna()
        daily_compare["hlc_exact"] = daily_compare[["high_exact", "low_exact", "close_exact"]].all(axis=1)
        daily_compare["volume_ratio"] = daily_compare["volume"] / daily_compare["volume_canonical"].replace(0, pd.NA)
        daily_compare["volume_near"] = daily_compare["volume_ratio"].between(0.95, 1.05)
        daily_compare["year"] = pd.to_datetime(daily_compare["session_date"]).dt.year
    daily_compare.to_csv(root / "normalized" / "daily_comparison.csv", index=False)

    tv1d_bars = bars[bars["phase"].eq("tv1d_reconciliation")].copy()
    tv1d = tv1d_bars.rename(columns={"server": "provider_server"})
    tv1d_compare = tv1d.merge(canonical_daily.drop(columns=["date"]), on=["ticker", "session_date"], how="inner", suffixes=("", "_canonical")) if not tv1d.empty else pd.DataFrame()
    if not tv1d_compare.empty:
        for field in ["open", "high", "low", "close", "volume"]:
            tv1d_compare[f"{field}_exact"] = tv1d_compare[field].eq(tv1d_compare[f"{field}_canonical"])
        tv1d_compare["open_canonical_present"] = tv1d_compare["open_canonical"].notna()
        tv1d_compare["hlc_exact"] = tv1d_compare[["high_exact", "low_exact", "close_exact"]].all(axis=1)
        tv1d_compare["year"] = pd.to_datetime(tv1d_compare["session_date"]).dt.year
        tv1d_compare["corporate_action_quarantined"] = [(str(t), str(d)) in ca_keys for t, d in zip(tv1d_compare["ticker"], tv1d_compare["session_date"])]
    tv1d_compare.to_csv(root / "normalized" / "tv1d_comparison.csv", index=False)

    tv60_tv1d = daily[["ticker", "session_date", "open", "high", "low", "close", "volume", "corporate_action_quarantined"]].merge(tv1d[["ticker", "session_date", "open", "high", "low", "close", "volume"]], on=["ticker", "session_date"], how="inner", suffixes=("_tv60", "_tv1d")) if not daily.empty and not tv1d.empty else pd.DataFrame()
    if not tv60_tv1d.empty:
        tv60_tv1d["year"] = pd.to_datetime(tv60_tv1d["session_date"]).dt.year
        tv60_tv1d["open_exact"] = tv60_tv1d["open_tv60"].eq(tv60_tv1d["open_tv1d"])
    tv60_tv1d.to_csv(root / "normalized" / "tv60_tv1d_comparison.csv", index=False)

    deep_bars = bars[bars["phase"].eq("deep_pagination")].copy()
    deep_bars.to_csv(root / "normalized" / "deep_intraday_bars.csv", index=False)
    deep_summary = []
    deep_tickers = [request["ticker"] for request in manifest["mathieu_plan"] if request["phase"] == "deep_pagination"]
    for ticker in sorted(set(deep_tickers)):
        current = deep_bars[deep_bars["ticker"].eq(ticker)]
        min_date = current["timestamp_wib"].min()[:10] if not current.empty else None
        deep_summary.append({"ticker": ticker, "row_count": int(len(current)), "earliest_timestamp_wib": min_date, "reaches_early_2021": bool(min_date and min_date <= "2021-01-31")})
    deep_summary_frame = pd.DataFrame(deep_summary)
    deep_summary_frame.to_csv(root / "normalized" / "deep_pagination_summary.csv", index=False)

    endenwer_results: list[dict[str, Any]] = []
    if args.endenwer_entry and args.endenwer_wrapper:
        endenwer_results = execute_endenwer(manifest, args.endenwer_entry, args.endenwer_wrapper, root)
    endenwer_rows = [{"ticker": p["request"]["ticker"], "status": p["response"].get("status"), "completion_reason": p["response"].get("completion_reason"), "pagination_pages": p["response"].get("pagination_pages"), "period_count": len(p["response"].get("periods") or []), "first_epoch": min([x.get("time") for x in p["response"].get("periods") or [] if isinstance(x, dict) and isinstance(x.get("time"), (int, float))], default=None), "last_epoch": max([x.get("time") for x in p["response"].get("periods") or [] if isinstance(x, dict) and isinstance(x.get("time"), (int, float))], default=None), "numeric_comparison": p["response"].get("numeric_comparison")} for p in endenwer_results]
    pd.DataFrame(endenwer_rows).to_csv(root / "normalized" / "endenwer_depth_summary.csv", index=False)

    sample = manifest["sample_records"]
    coverage = fixed_coverage_metrics(bars, request_frame, sample, windows)
    years = [int(window["year"]) for window in windows]
    minimum_rows = int(config["gates"]["minimum_year_matched_rows"])
    range_summaries = {}
    for range_key, range_years in [("2021_2026", years), ("2022_2026", years[1:])]:
        summary = make_range_summary(range_years, coverage, daily_compare, tv1d_compare, tv60_tv1d, minimum_rows)
        summary["deep_reach_2021_rate"] = float(deep_summary_frame["reaches_early_2021"].mean()) if not deep_summary_frame.empty else None
        summary["structural_integrity"] = bool((request_frame[["malformed_rows", "duplicate_rows", "invalid_ohlcv_rows"]].sum().sum() == 0) if not request_frame.empty else False)
        summary["open_semantics"] = {
            "tv60_vs_tv1d_exact_rate": summary.get("tv60_open_vs_tv1d_exact_rate"),
            "tv60_vs_tv1d_rows": summary.get("tv60_open_vs_tv1d_rows"),
            "tv1d_vs_canonical_open_exact_rate": float(tv1d_compare.loc[tv1d_compare["open_canonical_present"] & ~tv1d_compare["corporate_action_quarantined"], "open_exact"].mean()) if not tv1d_compare.empty and (tv1d_compare["open_canonical_present"] & ~tv1d_compare["corporate_action_quarantined"]).any() else None,
        }
        range_summaries[range_key] = summary
    metrics = {
        "ranges": range_summaries,
        "deep_reach_2021_rate": float(deep_summary_frame["reaches_early_2021"].mean()) if not deep_summary_frame.empty else None,
        "structural_integrity": all(value["structural_integrity"] for value in range_summaries.values()),
        "target_window_availability_by_year": {year: range_summaries["2021_2026"]["target_window_availability_by_year"].get(year) for year in [str(y) for y in years]},
        "certified_session_coverage_by_year": range_summaries["2021_2026"]["certified_session_coverage_by_year"],
        "hlc_exact_by_year": {year: (range_summaries["2021_2026"]["hlc_exact_by_year"].get(year) or {}).get("rate") for year in [str(y) for y in years]},
        "volume_within_5pct_by_year": range_summaries["2021_2026"]["volume_within_5pct_by_year"],
        "tv1d_reference_exact_by_year": {year: (range_summaries["2021_2026"]["tv1d_reference_exact_by_year"].get(year) or {}).get("rate") for year in [str(y) for y in years]},
    }
    verdict = evaluate_frozen_verdict(metrics, config)
    status_counts = request_frame["status"].value_counts().to_dict() if not request_frame.empty else {}
    summary = {
        "schema": "idx-trade/tradingview-historical-intraday-admission-pilot-result-v1",
        "sample_manifest_sha256": sha256_file(args.sample_manifest),
        "input_hashes": actual,
        "corporate_action_evidence_sha256": ca_sha,
        "mathieu_commit": manifest["mathieu_commit"], "endenwer_commit": manifest["endenwer_commit"],
        "request_counts": {"mathieu": len(manifest["mathieu_plan"]), "endenwer": len(manifest["endenwer_plan"]), "mathieu_actual_rows": len(request_frame)},
        "mathieu_status_counts": status_counts,
        "mathieu_status_by_phase": request_frame.groupby(["phase", "status"]).size().unstack(fill_value=0).reset_index().to_dict(orient="records") if not request_frame.empty else [],
        "coverage": {"fixed_request_count": coverage["fixed_request_count"], "symbol_resolution_rate": coverage["symbol_resolution_rate"], "known_listed_pairs": coverage["known_listed_pairs"], "available_pairs": coverage["available_pairs"], "by_year": coverage["by_year"]},
        "structural_diagnostics": {"malformed_rows": int(request_frame["malformed_rows"].sum()) if not request_frame.empty else 0, "duplicate_rows": int(request_frame["duplicate_rows"].sum()) if not request_frame.empty else 0, "invalid_ohlcv_rows": int(request_frame["invalid_ohlcv_rows"].sum()) if not request_frame.empty else 0, "off_session_rows": int(request_frame["off_session_rows"].sum()) if not request_frame.empty else 0},
        "deep_pagination": {"requests": len([x for x in manifest["mathieu_plan"] if x["phase"] == "deep_pagination"]), "reached_early_2021": int(deep_summary_frame["reaches_early_2021"].sum()) if not deep_summary_frame.empty else 0, "total_tickers": int(len(deep_summary_frame)), "rows": int(len(deep_bars))},
        "endenwer": {"status_counts": pd.DataFrame(endenwer_rows)["status"].value_counts().to_dict() if endenwer_rows else {}, "completion_counts": pd.DataFrame(endenwer_rows)["completion_reason"].value_counts().to_dict() if endenwer_rows else {}, "numeric_comparison": "QUARANTINED_ADJUSTMENT_MISMATCH"},
        "daily_reconciliation": {"ranges": range_summaries, "non_ca_rows": int((~daily_compare["corporate_action_quarantined"]).sum()) if not daily_compare.empty else 0, "volume_ratio": volume_ratio_diagnostics(pd.to_numeric(daily_compare.loc[~daily_compare["corporate_action_quarantined"], "volume_ratio"], errors="coerce") if not daily_compare.empty else pd.Series(dtype=float))},
        "verdict": verdict,
        "canonical_panel_sha256_after": sha256_file(args.panel),
    }
    (root / "audit_summary.json").write_bytes(json_bytes(summary))
    artifact_sha = hash_manifest(root)
    print(json.dumps({"verdict": verdict["verdict"], "artifact_manifest_sha256": artifact_sha, "summary": str(root / "audit_summary.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
