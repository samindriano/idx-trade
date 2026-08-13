"""Freeze the TradingView 2021-2026 admission-pilot sample before network."""

from __future__ import annotations

import argparse
from datetime import date, datetime, time
import json
from pathlib import Path
from typing import Any

import pandas as pd

from idx_trade.tradingview_admission import verify_input_hashes
from idx_trade.tradingview_remediation import sha256_file
from idx_trade.tradingview_intraday import request_epochs


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n").encode("utf-8")


def _listing_active(row: pd.Series, on: date) -> bool:
    listed_from = pd.to_datetime(row.get("listed_from"), errors="coerce")
    listed_to = pd.to_datetime(row.get("listed_to"), errors="coerce")
    if pd.isna(listed_from) or listed_from.date() > on:
        return False
    return bool(pd.isna(listed_to) or listed_to.date() >= on)


def _select_sample(config: dict[str, Any], security: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    security = security.copy()
    security["ticker"] = security["ticker"].astype(str).str.upper()
    security["listed_from"] = pd.to_datetime(security["listed_from"], errors="coerce")
    security["listed_to"] = pd.to_datetime(security["listed_to"], errors="coerce")
    panel = panel.copy()
    panel["ticker"] = panel["ticker"].astype(str).str.upper()
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce")
    panel["regular_market_value"] = pd.to_numeric(panel["regular_market_value"], errors="coerce")
    panel["volume"] = pd.to_numeric(panel["volume"], errors="coerce")
    reference = panel[panel["date"].dt.year.eq(2024)]
    liquidity = reference.groupby("ticker", as_index=False).agg(
        liquidity_median_value=("regular_market_value", "median"),
        liquidity_median_volume=("volume", "median"),
    )
    eligible = security.merge(liquidity, on="ticker", how="inner")
    cutoff = date.fromisoformat(config["sample"]["core_listing_cutoff"])
    core = eligible[eligible.apply(lambda row: _listing_active(row, cutoff), axis=1)].copy()
    core = core.sort_values(["liquidity_median_value", "ticker"], ascending=[False, True]).reset_index(drop=True)
    if len(core) < config["sample"]["core_common_tickers"]:
        raise ValueError("fewer than 40 canonical common-stock candidates satisfy the core listing rule")

    mandatory = [str(value).upper() for value in config["sample"]["mandatory_tickers"]]
    missing = sorted(set(mandatory) - set(core["ticker"]))
    if missing:
        raise ValueError(f"mandatory tickers missing from core eligibility: {missing}")

    n = len(core)
    high = set(core.head(10)["ticker"])
    low = set(core.tail(10)["ticker"])
    middle_start = max(0, (n // 2) - 5)
    middle = set(core.iloc[middle_start:middle_start + 10]["ticker"])
    chosen = set(mandatory) | high | middle | low
    ordered_core = list(core["ticker"])
    for ticker in ordered_core:
        if len(chosen) >= config["sample"]["core_common_tickers"]:
            break
        chosen.add(ticker)
    chosen = set(sorted(chosen))
    core = core[core["ticker"].isin(chosen)].copy()
    core["sample_role"] = core["ticker"].map(
        lambda ticker: "mandatory_control" if ticker in mandatory else (
            "high_liquidity" if ticker in high else ("mid_liquidity" if ticker in middle else "low_liquidity")
        )
    )
    core = core.sort_values("ticker")

    edge_pool = eligible[~eligible["ticker"].isin(set(core["ticker"]))].copy()
    post_cutoff = edge_pool[edge_pool["listed_from"].dt.date > cutoff].sort_values(["listed_from", "ticker"])
    edge = list(post_cutoff.head(5)["ticker"])
    low_edge = edge_pool[~edge_pool["ticker"].isin(edge)].sort_values(["liquidity_median_value", "ticker"])
    edge.extend(list(low_edge.head(5)["ticker"]))
    if len(edge) < config["sample"]["edge_control_tickers"]:
        remaining = edge_pool[~edge_pool["ticker"].isin(edge)].sort_values("ticker")
        edge.extend(list(remaining.head(config["sample"]["edge_control_tickers"] - len(edge))["ticker"]))
    edge = sorted(set(edge))
    if len(edge) != config["sample"]["edge_control_tickers"]:
        raise ValueError(f"could not freeze exactly ten edge controls: {edge}")
    edge_frame = eligible[eligible["ticker"].isin(edge)].copy()
    edge_frame["sample_role"] = edge_frame["ticker"].map(
        lambda ticker: "post_cutoff_listing" if pd.to_datetime(edge_frame.loc[edge_frame["ticker"].eq(ticker), "listed_from"].iloc[0]).date() > cutoff else "illiquidity_identity_edge"
    )
    result = pd.concat([core, edge_frame], ignore_index=True).drop_duplicates("ticker", keep="first")
    result = result.sort_values("ticker").reset_index(drop=True)
    if len(result) != config["sample"]["total_tickers"]:
        raise ValueError(f"sample size is {len(result)}, expected {config['sample']['total_tickers']}")
    return result


def _window_rows(config: dict[str, Any], calendar: pd.DataFrame) -> list[dict[str, Any]]:
    calendar_dates = {pd.Timestamp(value).date() for value in calendar["date"]}
    rows = []
    for window in config["yearly_windows"]:
        start = date.fromisoformat(window["start"])
        end = date.fromisoformat(window["end"])
        sessions = sorted(value.isoformat() for value in calendar_dates if start <= value <= end)
        if not sessions:
            raise ValueError(f"no official session evidence for {window['label']}")
        rows.append({**window, "official_session_dates": sessions})
    return rows


def _request(index: int, *, phase: str, ticker: str, window: dict[str, Any], timeframe: str, steps: int, batch: int, wait_ms: int, timeout_ms: int) -> dict[str, Any]:
    start = date.fromisoformat(window["start"])
    end = date.fromisoformat(window["end"])
    from_epoch, to_epoch = request_epochs(start, end)
    return {
        "request_index": index,
        "phase": phase,
        "server": "prodata",
        "ticker": ticker,
        "symbol": f"IDX:{ticker}",
        "era": window["label"],
        "year": window.get("year"),
        "start": window["start"],
        "end": window["end"],
        "timeframe": timeframe,
        "session": "regular",
        "adjustment": "none",
        "initial_range": 500,
        "fetch_more_steps": steps,
        "fetch_more_batch": batch,
        "fetch_more_wait_ms": wait_ms,
        "timeout_ms": timeout_ms,
        "requested_from_epoch": from_epoch,
        "requested_to_epoch": to_epoch,
        "to": to_epoch,
    }


def prepare(config_path: Path, security_path: Path, calendar_path: Path, panel_path: Path, artifact_root: Path) -> Path:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if artifact_root.exists() and any(artifact_root.iterdir()):
        raise ValueError(f"artifact root must be new and empty: {artifact_root}")
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "raw" / "mathieu").mkdir(parents=True, exist_ok=True)
    (artifact_root / "raw" / "endenwer").mkdir(parents=True, exist_ok=True)
    (artifact_root / "normalized").mkdir(parents=True, exist_ok=True)

    actual_hashes = {
        "config_sha256": sha256_file(config_path),
        "canonical_panel_sha256": sha256_file(panel_path),
        "official_calendar_sha256": sha256_file(calendar_path),
        "security_master_sha256": sha256_file(security_path),
    }
    security = pd.read_csv(security_path, dtype={"ticker": str})
    panel = pd.read_parquet(panel_path, columns=["ticker", "date", "volume", "regular_market_value"])
    calendar = pd.read_csv(calendar_path)
    windows = _window_rows(config, calendar)
    sample = _select_sample(config, security, panel)

    mathieu_plan = []
    index = 1
    for ticker in sample["ticker"]:
        for window in windows:
            mathieu_plan.append(_request(index, phase="fixed_60m", ticker=ticker, window=window, timeframe="60", steps=0, batch=1, wait_ms=8000, timeout_ms=25000))
            index += 1
    tv1d_tickers = [str(value).upper() for value in config["request_matrix"]["tv1d_reconciliation_tickers"]]
    for ticker in tv1d_tickers:
        if ticker not in set(sample["ticker"]):
            raise ValueError(f"TV1D ticker is absent from frozen sample: {ticker}")
        for window in windows:
            mathieu_plan.append(_request(index, phase="tv1d_reconciliation", ticker=ticker, window=window, timeframe="1D", steps=0, batch=1, wait_ms=8000, timeout_ms=25000))
            index += 1

    deep_window = {"label": "deep_2021_2026", "year": 2021, "start": "2021-01-01", "end": "2026-07-31"}
    for ticker in config["request_matrix"]["deep_mathieu_tickers"]:
        mathieu_plan.append(_request(index, phase="deep_pagination", ticker=ticker, window=deep_window, timeframe="60", steps=config["request_matrix"]["deep_mathieu"]["fetch_more_steps"], batch=config["request_matrix"]["deep_mathieu"]["fetch_more_batch"], wait_ms=config["request_matrix"]["deep_mathieu"]["fetch_more_wait_ms"], timeout_ms=config["request_matrix"]["deep_mathieu"]["timeout_ms"]))
        index += 1

    endenwer_plan = []
    for end_index, ticker in enumerate(config["request_matrix"]["endenwer_corroboration_tickers"], start=1):
        endenwer_plan.append({
            "request_index": end_index, "phase": "endenwer_depth", "ticker": ticker, "symbol": f"IDX:{ticker}",
            "era": "deep_2021_2026", "year": 2021, "start": deep_window["start"], "end": deep_window["end"],
            "timeframe": config["request_matrix"]["endenwer"]["timeframe"], "amount": config["request_matrix"]["endenwer"]["amount"],
            "max_pages": config["request_matrix"]["endenwer"]["max_pages"], "adjustment": config["request_matrix"]["endenwer"]["adjustment"],
            "session": config["request_matrix"]["endenwer"]["session"],
        })

    sample_records = []
    for row in sample.to_dict(orient="records"):
        sample_records.append({
            "ticker": row["ticker"], "sample_role": row["sample_role"],
            "listed_from": None if pd.isna(row["listed_from"]) else row["listed_from"].date().isoformat(),
            "listed_to": None if pd.isna(row["listed_to"]) else row["listed_to"].date().isoformat(),
            "liquidity_median_value_2024": None if pd.isna(row["liquidity_median_value"]) else float(row["liquidity_median_value"]),
            "liquidity_median_volume_2024": None if pd.isna(row["liquidity_median_volume"]) else float(row["liquidity_median_volume"]),
            "eligibility_basis": "security_master + canonical_panel_SIGNAL_RESEARCH_HLCV",
        })
    manifest = {
        "schema": "idx-trade/tradingview-historical-intraday-admission-pilot-sample-v1",
        "created_before_network": True,
        "network_started": False,
        "sample_seed": config["sample"]["seed"],
        "input_hashes": actual_hashes,
        "upstream": config["upstream"],
        "sample_tickers": [row["ticker"] for row in sample_records],
        "sample_records": sample_records,
        "yearly_windows": windows,
        "deep_window": deep_window,
        "mathieu_commit": config["upstream"]["mathieu_commit"],
        "endenwer_commit": config["upstream"]["endenwer_commit"],
        "mathieu_plan": mathieu_plan,
        "endenwer_plan": endenwer_plan,
        "prior_authoritative_ca_evidence": {
            "artifact_root": "D:/Documents/Project/idx-trade-data-gate-20260808v/tradingview_historical_intraday_remediation_v1_20260814_retry1",
            "artifact_manifest_sha256": config["lineage"]["prior_remediation_artifact_manifest_sha256"],
            "usage": "reuse only explicit corporate_action_quarantined rows; no provider-ratio inference",
        },
    }
    sample_path = artifact_root / "sample_manifest.json"
    sample_path.write_bytes(_json_bytes(manifest))
    prep = {
        "schema": "idx-trade/tradingview-historical-intraday-admission-pilot-pre-network-v1",
        "created_at_utc": datetime.now().astimezone().isoformat(),
        "network_started": False,
        "input_hashes": actual_hashes,
        "sample_manifest_sha256": sha256_file(sample_path),
        "sample_ticker_count": len(sample_records),
        "mathieu_request_count": len(mathieu_plan),
        "endenwer_request_count": len(endenwer_plan),
        "yearly_windows": windows,
        "selection_summary": sample_records,
        "frozen_gates": config["gates"],
    }
    (artifact_root / "pre_network_preparation.json").write_bytes(_json_bytes(prep))
    (artifact_root / "selection_summary.json").write_bytes(_json_bytes({"sample_records": sample_records, "yearly_windows": windows}))
    return sample_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    sample_path = prepare(args.config, args.security_master, args.calendar, args.panel, args.artifact_root)
    print(json.dumps({"sample_manifest": str(sample_path), "sample_manifest_sha256": sha256_file(sample_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
