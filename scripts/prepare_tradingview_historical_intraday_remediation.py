"""Prepare immutable forensic inputs and the pre-network remediation manifest."""

from __future__ import annotations

import argparse
from datetime import date, datetime, time
import json
from pathlib import Path
import shutil
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from idx_trade.tradingview_remediation import sha256_file, volume_ratio_diagnostics


WIB = ZoneInfo("Asia/Jakarta")


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n").encode("utf-8")


def request_epochs(start: date, end: date) -> tuple[int, int]:
    start_dt = datetime(start.year, start.month, start.day, tzinfo=WIB)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=WIB)
    return int(start_dt.timestamp()), int(end_dt.timestamp())


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_mathieu_plan(config: dict[str, Any]) -> list[dict[str, Any]]:
    eras = {item["label"]: item for item in config["eras"]}
    plan: list[dict[str, Any]] = []
    for server in config["access"]["servers"]:
        for ticker in config["sample_tickers"]:
            for era in config["eras"]:
                start_epoch, end_epoch = request_epochs(date.fromisoformat(era["start"]), date.fromisoformat(era["end"]))
                contract = config["phase1_paired_servers"]
                plan.append({
                    "phase": "phase1_paired_servers", "server": server, "ticker": ticker, "symbol": f"IDX:{ticker}",
                    "era": era["label"], "year": era["year"], "start": era["start"], "end": era["end"],
                    "adjustment": contract["adjustment"], "timeframe": contract["timeframe"], "session": contract["session"],
                    "initial_range": contract["initial_range"], "fetch_more_steps": contract["fetch_more_steps"],
                    "fetch_more_batch": contract["fetch_more_batch"], "fetch_more_wait_ms": contract["fetch_more_wait_ms"],
                    "timeout_ms": contract["timeout_ms"], "to": end_epoch, "requested_from_epoch": start_epoch,
                    "requested_to_epoch": end_epoch,
                })
    contract = config["phase2_pagination"]
    for server in contract["servers"]:
        for ticker in contract["tickers"]:
            for label in contract["eras"]:
                era = eras[label]
                start_epoch, end_epoch = request_epochs(date.fromisoformat(era["start"]), date.fromisoformat(era["end"]))
                plan.append({
                    "phase": "phase2_pagination", "server": server, "ticker": ticker, "symbol": f"IDX:{ticker}",
                    "era": label, "year": era["year"], "start": era["start"], "end": era["end"],
                    "adjustment": contract["adjustment"], "timeframe": contract["timeframe"], "session": contract["session"],
                    "initial_range": contract["initial_range"], "fetch_more_steps": contract["fetch_more_steps"],
                    "fetch_more_batch": contract["fetch_more_batch"], "fetch_more_wait_ms": contract["fetch_more_wait_ms"],
                    "timeout_ms": contract["timeout_ms"], "to": end_epoch, "requested_from_epoch": start_epoch,
                    "requested_to_epoch": end_epoch,
                })
    contract = config["phase3_tv1d_reconciliation"]
    for ticker in contract["tickers"]:
        for label in contract["eras"]:
            era = eras[label]
            start_epoch, end_epoch = request_epochs(date.fromisoformat(era["start"]), date.fromisoformat(era["end"]))
            plan.append({
                "phase": "phase3_tv1d_reconciliation", "server": contract["server"], "ticker": ticker, "symbol": f"IDX:{ticker}",
                "era": label, "year": era["year"], "start": era["start"], "end": era["end"],
                "adjustment": contract["adjustment"], "timeframe": contract["timeframe"], "session": contract["session"],
                "initial_range": contract["initial_range"], "fetch_more_steps": contract["fetch_more_steps"],
                "fetch_more_batch": 0, "fetch_more_wait_ms": 0, "timeout_ms": contract["timeout_ms"],
                "to": end_epoch, "requested_from_epoch": start_epoch, "requested_to_epoch": end_epoch,
            })
    for index, request in enumerate(plan, start=1):
        request["request_index"] = index
    return plan


def build_endenwer_plan(config: dict[str, Any]) -> list[dict[str, Any]]:
    eras = {item["label"]: item for item in config["eras"]}
    contract = config["phase4_endenwer_crosscheck"]
    rows = []
    for ticker in contract["tickers"]:
        for label in contract["eras"]:
            era = eras[label]
            rows.append({
                "phase": "phase4_endenwer_crosscheck", "ticker": ticker, "symbol": f"IDX:{ticker}", "era": label,
                "year": era["year"], "start": era["start"], "end": era["end"], "timeframe": contract["timeframe"],
                "amount": contract["amount"], "adjustment": contract["adjustment"], "session": contract["session"],
            })
    for index, row in enumerate(rows, start=1):
        row["request_index"] = index
    return rows


def write_forensics(root: Path, old_root: Path) -> dict[str, Any]:
    comparison = pd.read_csv(old_root / "normalized" / "daily_comparison.csv")
    non_ca = comparison[~comparison["corporate_action_quarantined"].astype(bool)].copy()
    non_ca["volume_ratio"] = pd.to_numeric(non_ca["volume"], errors="coerce") / pd.to_numeric(non_ca["volume_canonical"], errors="coerce").replace(0, pd.NA)
    ratio_rows = non_ca[["ticker", "era", "session_date", "volume", "volume_canonical", "volume_ratio"]].copy()
    ratio_rows["year"] = pd.to_datetime(ratio_rows["session_date"]).dt.year
    ratio_rows.to_csv(root / "forensic_volume_ratios.csv", index=False)

    timing_rows = []
    for path in sorted((old_root / "raw").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        response = payload["response"]
        started = datetime.fromisoformat(response["started_at_utc"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(response["finished_at_utc"].replace("Z", "+00:00"))
        market = response.get("market_info") or {}
        timing_rows.append({
            "file": path.name, "ticker": payload["request"]["ticker"], "era": payload["request"]["era"],
            "adjustment": payload["request"]["adjustment"], "status": response.get("status"),
            "elapsed_s": (finished - started).total_seconds(), "market_info_present": bool(market),
            "series_id": market.get("series_id"), "has_intraday": market.get("has_intraday"),
            "period_count": len(response.get("periods") or []), "error": json.dumps(response.get("error")),
            "old_event_trace_available": False,
        })
    timing = pd.DataFrame(timing_rows)
    timing.to_csv(root / "forensic_request_timing.csv", index=False)
    summary = {
        "source_artifact_root": str(old_root),
        "source_artifact_manifest_sha256": sha256_file(old_root / "artifact_manifest.json"),
        "source_sample_manifest_sha256": sha256_file(old_root / "sample_manifest.json"),
        "volume_ratio": volume_ratio_diagnostics(non_ca["volume_ratio"]),
        "volume_ratio_by_year": non_ca.assign(year=pd.to_datetime(non_ca["session_date"]).dt.year).groupby("year")["volume_ratio"].agg(["count", "min", "max", "median", "mean"]).reset_index().to_dict(orient="records"),
        "volume_ratio_by_ticker_year": non_ca.assign(year=pd.to_datetime(non_ca["session_date"]).dt.year).groupby(["ticker", "year"])["volume_ratio"].agg(["count", "min", "max", "median", "mean"]).reset_index().to_dict(orient="records"),
        "matched_daily_rows": int(len(comparison)),
        "non_ca_matched_daily_rows": int(len(non_ca)),
        "request_timing_status_counts": timing["status"].value_counts().to_dict(),
        "timeout_observable": {
            "timeout_count": int((timing["status"] == "TIMEOUT").sum()),
            "timeout_with_market_info": int(((timing["status"] == "TIMEOUT") & timing["market_info_present"]).sum()),
            "timeout_with_periods": int(((timing["status"] == "TIMEOUT") & (timing["period_count"] > 0)).sum()),
            "old_adapter_event_trace_persisted": False,
            "interpretation": "market info arrived for timeout rows, but the old adapter did not expose websocket or series_completed/update event trace; remediation must capture those events where observable.",
        },
    }
    (root / "forensic_summary.json").write_bytes(json_bytes(summary))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--old-root", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    if args.artifact_root.exists() and any(args.artifact_root.iterdir()):
        raise SystemExit(f"artifact root is non-empty: {args.artifact_root}")
    (args.artifact_root / "raw" / "mathieu").mkdir(parents=True, exist_ok=True)
    (args.artifact_root / "raw" / "endenwer").mkdir(parents=True, exist_ok=True)
    (args.artifact_root / "normalized").mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    expected = config["lineage"]["prior_artifact_manifest_sha256"]
    actual = sha256_file(args.old_root / "artifact_manifest.json")
    if actual != expected:
        raise SystemExit(f"immutable prior artifact hash mismatch: {actual} != {expected}")
    plan = build_mathieu_plan(config)
    endenwer_plan = build_endenwer_plan(config)
    sample_manifest = {
        "schema": "idx-trade/tradingview-historical-intraday-remediation-v1-sample-manifest",
        "created_before_network": True,
        "seed": config["sample_seed"],
        "mathieu_commit": config["upstream"]["mathieu_commit"],
        "endenwer_commit": config["upstream"]["endenwer_commit"],
        "servers": config["access"]["servers"],
        "ticker_count": len(config["sample_tickers"]),
        "tickers": config["sample_tickers"],
        "eras": config["eras"],
        "mathieu_request_count": len(plan),
        "endenwer_request_count": len(endenwer_plan),
        "mathieu_plan": plan,
        "endenwer_plan": endenwer_plan,
        "input_hashes": {
            "config_sha256": sha256_file(args.config),
            "prior_artifact_manifest_sha256": actual,
            "prior_sample_manifest_sha256": sha256_file(args.old_root / "sample_manifest.json"),
            "canonical_panel_sha256": sha256_file(args.panel),
            "official_calendar_sha256": sha256_file(args.calendar),
            "security_master_sha256": sha256_file(args.security_master),
        },
        "network_contract": config["phase1_paired_servers"],
        "pagination_contract": config["phase2_pagination"],
        "three_way_contract": config["phase3_tv1d_reconciliation"],
        "independent_client_contract": config["phase4_endenwer_crosscheck"],
    }
    sample_path = args.artifact_root / "sample_manifest.json"
    sample_path.write_bytes(json_bytes(sample_manifest))
    forensic = write_forensics(args.artifact_root, args.old_root)
    prep = {
        "sample_manifest_sha256": sha256_file(sample_path),
        "sample_manifest_path": str(sample_path),
        "forensic_summary": forensic,
        "network_started": False,
    }
    (args.artifact_root / "pre_network_preparation.json").write_bytes(json_bytes(prep))
    print(json.dumps(prep, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
