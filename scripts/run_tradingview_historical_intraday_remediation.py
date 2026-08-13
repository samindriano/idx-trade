"""Run the preregistered, bounded TradingView remediation audit."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import subprocess
from typing import Any

import pandas as pd

from idx_trade.tradingview_intraday import aggregate_daily, compare_daily, normalize_periods
from idx_trade.tradingview_remediation import listing_aware_denominators, pagination_boundary, sha256_file, three_way_reconciliation, volume_ratio_diagnostics


CONTROL_PAIRS = {("DSSA", "late_mid"), ("BBCA", "recent"), ("BMRI", "mid")}


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


def read_manifest(path: Path, config: Path, panel: Path, calendar: Path, security: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not manifest.get("created_before_network"):
        raise SystemExit("sample manifest is not marked created_before_network")
    expected = manifest["input_hashes"]
    actual = {
        "config_sha256": sha256_file(config),
        "canonical_panel_sha256": sha256_file(panel),
        "official_calendar_sha256": sha256_file(calendar),
        "security_master_sha256": sha256_file(security),
    }
    for key, value in actual.items():
        if expected[key] != value:
            raise SystemExit(f"input hash mismatch for {key}: {value} != {expected[key]}")
    return manifest


def official_sessions(calendar: Path, era: dict[str, Any]) -> set[date] | None:
    values = {pd.Timestamp(value).date() for value in pd.read_csv(calendar)["date"]}
    start, end = date.fromisoformat(era["start"]), date.fromisoformat(era["end"])
    selected = {value for value in values if start <= value <= end}
    return selected or None


def raw_path(root: Path, request: dict[str, Any]) -> Path:
    return root / "raw" / "mathieu" / (
        f"{request['request_index']:04d}_{request['phase']}_{request['server']}_{request['ticker']}_{request['era']}_{request['timeframe']}.json"
    )


def execute_mathieu(manifest: dict[str, Any], adapter: Path, root: Path) -> list[dict[str, Any]]:
    results = []
    plans = manifest["mathieu_plan"]
    for position, request in enumerate(plans, start=1):
        path = raw_path(root, request)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            response = payload["response"]
            results.append(payload)
            print(json.dumps({"progress": f"{position}/{len(plans)}", "reused": True, "phase": request["phase"], "server": request["server"], "ticker": request["ticker"], "era": request["era"], "status": response.get("status")}), flush=True)
            continue
        response, adapter_stderr = run_node(adapter, request, request["timeout_ms"] / 1000 + 12)
        payload = {
            "adapter_commit": manifest["mathieu_commit"], "request": request, "response": response,
            "adapter_stderr": adapter_stderr,
        }
        path.write_bytes(json_bytes(payload))
        results.append(payload)
        print(json.dumps({"progress": f"{position}/{len(plans)}", "phase": request["phase"], "server": request["server"], "ticker": request["ticker"], "era": request["era"], "status": response.get("status"), "periods": len(response.get("periods") or [])}), flush=True)
    return results


def normalize_mathieu(results: list[dict[str, Any]], calendar: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    rows = []
    era_by_label = {row["label"]: row for row in json.loads((Path(__file__).parents[1] / "config" / "tradingview_historical_intraday_remediation_v1.json").read_text(encoding="utf-8"))["eras"]}
    for payload in results:
        request = payload["request"]
        response = payload["response"]
        era = era_by_label[request["era"]]
        frame, diag = normalize_periods(
            response.get("periods", []), ticker=request["ticker"], symbol=request["symbol"], server=request["server"],
            phase=request["phase"], era=request["era"], timeframe=request["timeframe"], adjustment=request["adjustment"],
            requested_start=date.fromisoformat(request["start"]), requested_end=date.fromisoformat(request["end"]),
            official_sessions=official_sessions(calendar, era),
        )
        if not frame.empty:
            frames.append(frame)
        periods = response.get("periods") or []
        epochs = [period.get("time") for period in periods if isinstance(period, dict) and isinstance(period.get("time"), (int, float))]
        event_observation = response.get("event_observation") or {}
        fetch_more = response.get("fetch_more") or {}
        fetch_more_steps = fetch_more.get("steps") or []
        extended_steps = fetch_more.get("extended_steps")
        if extended_steps is None:
            extended_steps = sum(bool(step.get("extended")) for step in fetch_more_steps)
        rows.append({
            "request_index": request["request_index"], "phase": request["phase"], "server": request["server"],
            "ticker": request["ticker"], "era": request["era"], "year": request["year"], "timeframe": request["timeframe"],
            "adjustment": request["adjustment"], "status": response.get("status"), "errors": json.dumps(response.get("errors") or response.get("error")),
            "period_count": len(periods), "first_epoch": min(epochs) if epochs else None, "last_epoch": max(epochs) if epochs else None,
            "elapsed_ms": response.get("elapsed_ms"),
            "requested_from_epoch": request["requested_from_epoch"], "requested_to_epoch": request["requested_to_epoch"],
            "market_info_present": bool(response.get("market_info")), "market_timezone": (response.get("market_info") or {}).get("timezone"), "has_intraday": (response.get("market_info") or {}).get("has_intraday"),
            "event_trace": json.dumps(response.get("event_trace", [])), "websocket_connected": event_observation.get("websocket_connected"),
            "symbol_loaded": event_observation.get("symbol_loaded"), "update_seen": event_observation.get("update_seen"),
            "series_completed_observable": event_observation.get("series_completed_observable"),
            "fetch_more_steps_requested": fetch_more.get("requested_steps"), "fetch_more_steps_extended": extended_steps,
            "fetch_more_completion_reason": fetch_more.get("completion_reason"),
            **{key: value for key, value in diag.items() if key not in {"session_dates", "timezone_hours"}},
            "session_dates": json.dumps(diag.get("session_dates", [])), "timezone_hours": json.dumps(diag.get("timezone_hours", [])),
        })
    bars = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return bars, pd.DataFrame(rows)


def run_endenwer(manifest: dict[str, Any], entry: Path, wrapper: Path, root: Path) -> list[dict[str, Any]]:
    results = []
    plans = manifest["endenwer_plan"]
    for position, request in enumerate(plans, start=1):
        path = root / "raw" / "endenwer" / f"{request['request_index']:04d}_{request['ticker']}_{request['era']}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            results.append(payload)
            print(json.dumps({"endenwer_progress": f"{position}/{len(plans)}", "reused": True, "ticker": request["ticker"], "era": request["era"], "status": payload["response"].get("status")}), flush=True)
            continue
        try:
            completed = subprocess.run(["node", str(wrapper), str(entry), json.dumps(request, separators=(",", ":"))], capture_output=True, text=True, timeout=75)
            response = json.loads(completed.stdout) if completed.returncode == 0 else {"request": request, "status": "TRANSPORT_ERROR", "error": completed.stderr[-2000:], "periods": []}
            stderr = completed.stderr[-2000:] if completed.stderr else None
        except subprocess.TimeoutExpired as exc:
            response, stderr = {"request": request, "status": "TRANSPORT_TIMEOUT", "error": str(exc), "periods": []}, str(exc)
        payload = {"client_commit": manifest["endenwer_commit"], "request": request, "response": response, "stderr": stderr}
        path.write_bytes(json_bytes(payload))
        results.append(payload)
        print(json.dumps({"endenwer_progress": f"{position}/{len(plans)}", "ticker": request["ticker"], "era": request["era"], "status": response.get("status"), "periods": len(response.get("periods") or [])}), flush=True)
    return results


def normalize_endenwer(results: list[dict[str, Any]], calendar: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames, rows = [], []
    era_by_label = {row["label"]: row for row in config["eras"]}
    for payload in results:
        request, response = payload["request"], payload["response"]
        era = era_by_label[request["era"]]
        frame, diag = normalize_periods(
            response.get("periods", []), ticker=request["ticker"], symbol=request["symbol"], server="prodata_endenwer", phase=request["phase"],
            era=request["era"], timeframe=str(request["timeframe"]), adjustment=request["adjustment"],
            requested_start=date.fromisoformat(request["start"]), requested_end=date.fromisoformat(request["end"]), official_sessions=official_sessions(calendar, era),
        )
        if not frame.empty: frames.append(frame)
        periods = response.get("periods") or []
        epochs = [period.get("time") for period in periods if isinstance(period, dict) and isinstance(period.get("time"), (int, float))]
        rows.append({"request_index": request["request_index"], "ticker": request["ticker"], "era": request["era"], "status": response.get("status"), "completion_reason": response.get("completion_reason"), "pagination_pages": response.get("pagination_pages"), "period_count": len(periods), "first_epoch": min(epochs) if epochs else None, "last_epoch": max(epochs) if epochs else None, "event_trace": json.dumps(response.get("event_trace", [])), "numeric_comparison": response.get("numeric_comparison")})
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), pd.DataFrame(rows)


def hash_manifest(root: Path) -> str:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            files.append({"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest_path = root / "artifact_manifest.json"
    manifest_path.write_bytes(json_bytes({"schema": "idx-trade/tradingview-historical-intraday-remediation-artifact-manifest-v1", "artifacts": files}))
    return sha256_file(manifest_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--endenwer-entry", type=Path, required=False)
    parser.add_argument("--endenwer-wrapper", type=Path, required=False)
    args = parser.parse_args()
    if not args.artifact_root.exists() or not (args.artifact_root / "pre_network_preparation.json").exists():
        raise SystemExit("run requires prepared artifact root")
    manifest = read_manifest(args.sample_manifest, args.config, args.panel, args.calendar, args.security_master)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    mathieu_results = execute_mathieu(manifest, args.adapter, args.artifact_root)
    bars, request_frame = normalize_mathieu(mathieu_results, args.calendar)
    bars.to_csv(args.artifact_root / "normalized" / "mathieu_intraday_bars.csv", index=False)
    request_frame.to_csv(args.artifact_root / "normalized" / "mathieu_request_manifest.csv", index=False)

    canonical = pd.read_parquet(args.panel)
    canonical["ticker"] = canonical["ticker"].astype(str).str.upper()
    phase1 = bars[(bars["phase"] == "phase1_paired_servers") & (bars["timeframe"].astype(str) == "60")]
    daily_frames = []
    for server in config["access"]["servers"]:
        daily_frames.append(aggregate_daily(phase1[phase1["server"] == server]))
    daily = pd.concat(daily_frames, ignore_index=True) if daily_frames else pd.DataFrame()
    comparisons = []
    for server in config["access"]["servers"]:
        current = daily[daily["server"] == server] if not daily.empty else daily
        comp = compare_daily(current, canonical, tolerance=0.05)
        if not comp.empty:
            comp["corporate_action_quarantined"] = comp.apply(lambda row: (row["ticker"], row["era"]) in CONTROL_PAIRS, axis=1)
            comparisons.append(comp)
    comparison = pd.concat(comparisons, ignore_index=True) if comparisons else pd.DataFrame()
    comparison.to_csv(args.artifact_root / "normalized" / "daily_comparison.csv", index=False)

    tv1d = bars[(bars["phase"] == "phase3_tv1d_reconciliation") & (bars["timeframe"].astype(str).str.upper().isin(["1D", "D"]))]
    tv1d_daily = aggregate_daily(tv1d)
    tv1d_daily.to_csv(args.artifact_root / "normalized" / "tv1d_daily.csv", index=False)
    three_way_frames = []
    for server in config["access"]["servers"]:
        tv60 = daily[daily["server"] == server] if not daily.empty else daily
        for era in config["phase3_tv1d_reconciliation"]["eras"]:
            current60 = tv60[tv60["era"] == era] if not tv60.empty else tv60
            current1d = tv1d_daily[tv1d_daily["era"] == era] if not tv1d_daily.empty else tv1d_daily
            result = three_way_reconciliation(current60, current1d, canonical, tolerance=0.05)
            if not result.empty:
                result["tv60_server"] = server
                result["era"] = era
                three_way_frames.append(result)
    three_way = pd.concat(three_way_frames, ignore_index=True) if three_way_frames else pd.DataFrame()
    three_way.to_csv(args.artifact_root / "normalized" / "three_way_reconciliation.csv", index=False)

    endenwer_rows = []
    endenwer_bars = pd.DataFrame()
    if args.endenwer_entry and args.endenwer_wrapper:
        endenwer_results = run_endenwer(manifest, args.endenwer_entry, args.endenwer_wrapper, args.artifact_root)
        endenwer_bars, endenwer_manifest = normalize_endenwer(endenwer_results, args.calendar, config)
        endenwer_bars.to_csv(args.artifact_root / "normalized" / "endenwer_intraday_bars.csv", index=False)
        endenwer_manifest.to_csv(args.artifact_root / "normalized" / "endenwer_request_manifest.csv", index=False)
        endenwer_rows = endenwer_manifest.to_dict(orient="records")

    phase1_requests = request_frame[request_frame["phase"] == "phase1_paired_servers"].copy()
    listing = pd.read_csv(args.security_master, dtype={"ticker": str})
    listing["ticker"] = listing["ticker"].astype(str).str.upper()
    listing["listed_from"] = pd.to_datetime(listing["listed_from"], errors="coerce")
    listing["listed_to"] = pd.to_datetime(listing["listed_to"], errors="coerce")
    phase1_plan = pd.DataFrame(manifest["mathieu_plan"])
    phase1_plan = phase1_plan[phase1_plan["phase"] == "phase1_paired_servers"].copy()
    phase1_plan["start_date"] = pd.to_datetime(phase1_plan["start"])
    phase1_plan["end_date"] = pd.to_datetime(phase1_plan["end"])
    phase1_analysis = phase1_plan.merge(
        phase1_requests[["request_index", "status", "session_dates", "event_trace", "elapsed_ms", "market_info_present"]],
        on="request_index", how="left",
    )
    def listed_during(row: pd.Series) -> bool:
        candidates = listing[listing["ticker"] == str(row["ticker"]).upper()]
        if candidates.empty:
            return False
        return bool((
            ((candidates["listed_from"].isna()) | (candidates["listed_from"] <= row["end_date"]))
            & ((candidates["listed_to"].isna()) | (candidates["listed_to"] >= row["start_date"]))
        ).any())
    phase1_analysis["known_listed"] = phase1_analysis.apply(listed_during, axis=1)
    phase1_analysis["exact_window_rows"] = phase1_analysis["session_dates"].fillna("[]").map(
        lambda value: len(json.loads(value)) if isinstance(value, str) and value.startswith("[") else 0
    )
    phase1_analysis["event_trace_text"] = phase1_analysis["event_trace"].fillna("")
    phase1_analysis["adapter_timeout"] = phase1_analysis["event_trace_text"].str.contains("adapter_timeout")
    phase1_analysis["update_seen_observed"] = phase1_analysis["event_trace_text"].str.contains("update")
    phase1_pair_pivot = phase1_analysis.pivot(index=["ticker", "era"], columns="server", values=["status", "exact_window_rows"])
    phase1_pair_summary = []
    for era, group in phase1_analysis.groupby("era", sort=True):
        data = group[group["server"] == "data"].set_index("ticker")
        prodata = group[group["server"] == "prodata"].set_index("ticker")
        phase1_pair_summary.append({
            "era": era, "pairs": int(len(group) / 2),
            "data_available": int((data["status"] == "AVAILABLE").sum()),
            "prodata_available": int((prodata["status"] == "AVAILABLE").sum()),
            "both_available": int(((data["status"] == "AVAILABLE") & (prodata["status"] == "AVAILABLE")).sum()),
            "prodata_only": int(((prodata["status"] == "AVAILABLE") & (data["status"] != "AVAILABLE")).sum()),
            "data_only": int(((data["status"] == "AVAILABLE") & (prodata["status"] != "AVAILABLE")).sum()),
            "data_exact_window": int((data["exact_window_rows"] > 0).sum()),
            "prodata_exact_window": int((prodata["exact_window_rows"] > 0).sum()),
        })
    listing_aware_availability = phase1_analysis.groupby(["server", "era"], sort=True).apply(
        lambda group: pd.Series({
            "requested": int(len(group)),
            "known_listed": int(group["known_listed"].sum()),
            "raw_available": int((group["status"] == "AVAILABLE").sum()),
            "raw_available_listed": int(((group["status"] == "AVAILABLE") & group["known_listed"]).sum()),
            "exact_window_listed": int(((group["exact_window_rows"] > 0) & group["known_listed"]).sum()),
        }), include_groups=False,
    ).reset_index().to_dict(orient="records")
    transport_observation = phase1_analysis.groupby(["server", "era"], sort=True).apply(
        lambda group: pd.Series({
            "requests": int(len(group)),
            "websocket_connected": int(group["event_trace_text"].str.contains("connected").sum()),
            "market_info_present": int(group["market_info_present"].sum()),
            "partial_update_observed": int(group["update_seen_observed"].sum()),
            "adapter_timeout_observed": int(group["adapter_timeout"].sum()),
            "elapsed_ms_median": float(pd.to_numeric(group["elapsed_ms"], errors="coerce").median()),
        }), include_groups=False,
    ).reset_index().to_dict(orient="records")
    all_official = {pd.Timestamp(value).date().isoformat() for value in pd.read_csv(args.calendar)["date"]}
    denominators = listing_aware_denominators(
        pd.DataFrame(manifest["mathieu_plan"])[lambda frame: frame["phase"] == "phase1_paired_servers"],
        listing,
        all_official,
    )
    non_ca = comparison[~comparison["corporate_action_quarantined"]] if not comparison.empty else comparison
    ratios = pd.to_numeric(non_ca["volume_ratio"], errors="coerce") if not non_ca.empty else pd.Series(dtype=float)
    daily_by_server = []
    for server, group in comparison.groupby("server", sort=True):
        clean = group[~group["corporate_action_quarantined"]]
        daily_by_server.append({
            "server": server, "matched_rows": int(len(group)), "non_ca_rows": int(len(clean)),
            "hlc_exact_rate": float(clean["hlc_exact"].mean()) if not clean.empty else None,
            "open_exact_rate_when_present": float(clean.loc[clean["open_canonical_present"], "open_exact"].mean()) if clean["open_canonical_present"].any() else None,
            "open_rows": int(clean["open_canonical_present"].sum()),
            "volume_near_5pct_rate": float(clean["volume_near"].mean()) if not clean.empty else None,
            "volume_ratio": volume_ratio_diagnostics(pd.to_numeric(clean["volume_ratio"], errors="coerce")),
        })
    summary = {
        "schema": "idx-trade/tradingview-historical-intraday-remediation-result-v1",
        "sample_manifest_sha256": sha256_file(args.sample_manifest),
        "mathieu_commit": manifest["mathieu_commit"], "endenwer_commit": manifest["endenwer_commit"],
        "mathieu_request_count": len(phase1_requests) + len(request_frame[request_frame["phase"] == "phase2_pagination"]) + len(request_frame[request_frame["phase"] == "phase3_tv1d_reconciliation"]),
        "mathieu_status_counts": request_frame["status"].value_counts().to_dict(),
        "mathieu_status_by_server_era": request_frame.groupby(["server", "era"])["status"].value_counts().unstack(fill_value=0).reset_index().to_dict(orient="records"),
        "phase1_raw_availability": request_frame[request_frame["phase"] == "phase1_paired_servers"].groupby(["server", "era"]).agg(requests=("status", "size"), available=("status", lambda value: int((value == "AVAILABLE").sum())), periods=("period_count", "sum")).reset_index().to_dict(orient="records"),
        "phase1_pair_summary": phase1_pair_summary,
        "phase1_listing_aware_availability": listing_aware_availability,
        "phase1_transport_observation": transport_observation,
        "listing_aware_denominators_phase1": denominators,
        "certified_calendar_note": "2018/2020 have no preserved official session rows; timestamp depth is diagnostic only for those eras.",
        "pagination": {
            "phase2_requests": int((request_frame["phase"] == "phase2_pagination").sum()),
            "completion_reason_counts": request_frame[request_frame["phase"] == "phase2_pagination"]["fetch_more_completion_reason"].value_counts(dropna=False).to_dict(),
            "extended_step_total": int(request_frame[request_frame["phase"] == "phase2_pagination"]["fetch_more_steps_extended"].fillna(0).sum()),
        },
        "daily_reconciliation": {
            "matched_rows": int(len(comparison)),
            "non_ca_rows": int(len(non_ca)),
            "hlc_exact_rate": float(non_ca["hlc_exact"].mean()) if not non_ca.empty else None,
            "open_exact_rate_when_present": float(non_ca.loc[non_ca["open_canonical_present"], "open_exact"].mean()) if not non_ca.empty and non_ca["open_canonical_present"].any() else None,
            "volume_ratio": volume_ratio_diagnostics(ratios),
            "volume_near_5pct_rate": float(((ratios >= 0.95) & (ratios <= 1.05)).mean()) if len(ratios) else None,
            "corporate_action_quarantined_rows": int(comparison["corporate_action_quarantined"].sum()) if not comparison.empty else 0,
            "by_server": daily_by_server,
        },
        "three_way_class_counts": three_way["three_way_class"].value_counts().to_dict() if not three_way.empty else {},
        "endenwer": {
            "request_count": len(endenwer_rows),
            "status_counts": pd.Series([row.get("status") for row in endenwer_rows]).value_counts(dropna=False).to_dict() if endenwer_rows else {},
            "completion_reason_counts": pd.Series([row.get("completion_reason") for row in endenwer_rows]).value_counts(dropna=False).to_dict() if endenwer_rows else {},
            "numeric_comparison": "QUARANTINED_ADJUSTMENT_MISMATCH: pinned endenwer resolver hardcodes adjustment=splits",
            "request_to_timestamp": "unsupported by pinned public API; cross-check is depth/completion/overlap only",
        },
        "canonical_panel_sha256_before": manifest["input_hashes"]["canonical_panel_sha256"],
        "verdict": "PENDING_INDEPENDENT_REVIEW",
    }
    (args.artifact_root / "audit_summary.json").write_bytes(json_bytes(summary))
    manifest_sha = hash_manifest(args.artifact_root)
    print(json.dumps({"artifact_root": str(args.artifact_root), "summary": summary, "artifact_manifest_sha256": manifest_sha}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
