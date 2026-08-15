"""Finalize the existing V2.1 offline evidence without repeating identity mapping."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any

import pandas as pd

from idx_trade.tradingview_price_path_v2_1 import (
    artifact_manifest,
    control_request_fixture,
    directory_manifest,
    official_stock_summary_hlcv_oracle,
    sha256_file,
    yearly_fidelity_support,
)


PANEL_SHA = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
ERROR_TICKERS = ["CNTB", "FORZ", "FREN", "HDTX", "JKSW", "KPAL", "KPAS", "KRAH", "MAMI", "MASA", "MFIN", "MYRX", "NIPS", "PRAS", "RMBA", "TURI"]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-root", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_1_remediation_20260816_retry2"))
    parser.add_argument("--output-root", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_1_final_20260816"))
    parser.add_argument("--stock-summary-root", type=Path, default=Path(r"D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1"))
    parser.add_argument("--canonical-raw-root", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\prices_1260\raw"))
    parser.add_argument("--security-master", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\listings\security_master.csv"))
    parser.add_argument("--scope-exclusions", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\listings\security_scope_exclusions.csv"))
    parser.add_argument("--curated-identities", type=Path, default=Path(r"config\curated_security_identities.csv"))
    parser.add_argument("--config", type=Path, default=Path(r"config\tradingview_historical_price_path_v2_1.json"))
    parser.add_argument("--adapter", type=Path, default=Path(r"adapters\tradingview\index.js"))
    parser.add_argument("--package-lock", type=Path, default=Path(r"adapters\tradingview\package-lock.json"))
    return parser.parse_args()


def main() -> int:
    a = args()
    if a.output_root.exists() and any(a.output_root.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output root: {a.output_root}")
    a.output_root.mkdir(parents=True, exist_ok=True)
    offline = a.offline_root
    summary = json.loads((offline / "audit_summary.json").read_text(encoding="utf-8"))
    if sha256_file(a.canonical_raw_root / "AADI.parquet") == "":
        raise SystemExit("canonical source unavailable")
    panel = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet")
    if sha256_file(panel) != PANEL_SHA:
        raise SystemExit("canonical panel SHA mismatch")

    activity = pd.read_csv(Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814\activity_reconciliation.csv"), dtype={"ticker": str, "session_date": str})
    expected = pd.read_csv(Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814\expected_ticker_sessions.csv"), dtype={"ticker": str, "session_date": str, "security_id": str})
    master = pd.read_csv(a.security_master, dtype=str)
    curated = pd.read_csv(a.curated_identities, dtype=str)
    errors = activity[activity["ticker"].isin(ERROR_TICKERS)].copy()
    error_details = []
    for ticker, group in errors.groupby("ticker", sort=True):
        identities = master[master["ticker"].eq(ticker)].copy()
        if ticker == "FREN":
            curated_fren = curated[curated["ticker"].eq(ticker)].copy()
            if not curated_fren.empty:
                curated_fren["security_id"] = "IDX:" + curated_fren["ticker"] + ":" + pd.to_datetime(curated_fren["listed_from"]).dt.strftime("%Y%m%d")
            identities = pd.concat([identities, curated_fren], ignore_index=True)
        identities["listed_from"] = pd.to_datetime(identities["listed_from"], errors="coerce")
        identities["listed_to"] = pd.to_datetime(identities["listed_to"], errors="coerce")
        active = group[group["activity_state"].eq("ACTIVE")]
        yearly = group[group["activity_state"].eq("ACTIVE")].assign(year=lambda x: x["session_date"].str[:4]).groupby("year").size().to_dict()
        for identity in identities.itertuples(index=False):
            listed_to = getattr(identity, "listed_to", pd.NaT)
            error_details.append({
                "ticker": ticker,
                "provider_status": "SYMBOL_ERROR",
                "security_id": getattr(identity, "security_id", ""),
                "listed_from": getattr(identity, "listed_from", ""),
                "listed_to": listed_to,
                "listed_at_window_end": bool(pd.isna(listed_to) or listed_to >= pd.Timestamp("2026-07-31")),
                "active_sessions": int(len(active)),
                "no_trade_sessions": int((group["activity_state"] == "NO_TRADE").sum()),
                "unknown_sessions": int((group["activity_state"] == "UNKNOWN").sum()),
                "first_expected_date": group["session_date"].min(),
                "last_expected_date": group["session_date"].max(),
                "active_by_year": json.dumps({str(k): int(v) for k, v in yearly.items()}, sort_keys=True),
            })
    error_frame = pd.DataFrame(error_details).drop_duplicates(["ticker", "security_id", "listed_from", "listed_to"])
    error_frame.to_csv(a.output_root / "symbol_error_detail.csv", index=False)

    config = json.loads(a.config.read_text(encoding="utf-8"))
    years = sorted(activity["session_date"].str[:4].unique())
    yearly_ceiling = {}
    for year in years:
        group = activity[activity["session_date"].str.startswith(year)]
        active = group[group["activity_state"].eq("ACTIVE")]
        blocked = active[active["ticker"].isin(ERROR_TICKERS)]
        yearly_ceiling[year] = {"active_sessions": int(len(active)), "blocked_symbol_active_sessions": int(len(blocked)), "maximum_if_other_symbols_perfect": float((len(active) - len(blocked)) / len(active)) if len(active) else 0.0, "yearly_gate": 0.95}
    overall_active = activity[activity["activity_state"].eq("ACTIVE")]
    maximum_overall = float((len(overall_active) - error_frame.drop_duplicates("ticker")["active_sessions"].sum()) / len(overall_active))
    write_json(a.output_root / "symbol_error_coverage_ceiling.json", {"error_tickers": ERROR_TICKERS, "blocked_active_sessions": int(error_frame["active_sessions"].sum()), "maximum_overall_if_other_symbols_perfect": maximum_overall, "by_year": yearly_ceiling})

    reconciliation = pd.read_csv(offline / "expected_state_reconciliation.csv", dtype={"ticker": str, "session_date": str})
    fidelity = pd.read_csv(offline / "fidelity_rows_v2_1.csv", dtype={"ticker": str, "session_date": str})
    support = yearly_fidelity_support(reconciliation[reconciliation["activity_state"].eq("ACTIVE")], fidelity, range(2021, 2027), 10)
    write_json(a.output_root / "fidelity_support_report.json", support)
    top20 = pd.read_csv(offline / "fidelity_mismatch_top20_2022_2026.csv")
    top20[top20["year"].eq(2022)].to_csv(a.output_root / "2022_forensic_report.csv", index=False)

    sessions = pd.read_csv(Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814\official_sessions.csv"))
    events = pd.read_csv(Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814\corporate_action_events.csv"), dtype={"ticker": str})
    oracle_rows, oracle_summary = official_stock_summary_hlcv_oracle(a.stock_summary_root, a.canonical_raw_root, events, sessions)
    oracle_mismatches = oracle_rows[(~oracle_rows["hlc_exact"]) | (~oracle_rows["volume_within_5"]) | (~oracle_rows["valid_hlcv"])].copy()
    oracle_mismatches.to_csv(a.output_root / "official_stock_summary_hlcv_mismatches.csv", index=False)
    write_json(a.output_root / "official_stock_summary_hlcv_oracle.json", oracle_summary)

    existing_bars = pd.read_csv(Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814\normalized\intraday_bars.csv"), usecols=["raw_epoch", "ticker"])
    normalized_bytes = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814\normalized\intraday_bars.csv").stat().st_size
    raw_root = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814\raw\mathieu")
    raw_bytes = sum(path.stat().st_size for path in raw_root.rglob("*.json"))
    bars_per_ticker = existing_bars.groupby("ticker").size()
    future_bars = 978 * 5000
    write_json(a.output_root / "scalability_estimate.json", {"assumption": "future maximum 5,000 bars/ticker from frozen 500/5000/3 depth safety cap; actual early stop may be lower", "existing_tickers_with_bars": int(bars_per_ticker.size), "existing_bars": int(len(existing_bars)), "existing_raw_bytes": int(raw_bytes), "existing_normalized_bytes": int(normalized_bytes), "existing_normalized_bytes_per_row": float(normalized_bytes / len(existing_bars)), "future_upper_bound_tickers": 978, "future_upper_bound_bars": future_bars, "estimated_normalized_bytes_upper": int(future_bars * normalized_bytes / len(existing_bars)), "estimated_raw_bytes_upper": int(future_bars * raw_bytes / len(existing_bars)), "peak_ram_policy": "one provider response plus one per-ticker normalized chunk; never all raw responses"})

    code_head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    code_inputs = {"config": a.config, "adapter": a.adapter, "package_lock": a.package_lock, "security_master": a.security_master, "scope_exclusions": a.scope_exclusions, "curated_identities": a.curated_identities}
    input_hashes = {name: sha256_file(path) for name, path in code_inputs.items()}
    summary_manifest = json.loads((offline / "artifact_manifest.json").read_text(encoding="utf-8"))
    original_prereg = json.loads((offline / "preregistration.json").read_text(encoding="utf-8"))
    prereg = {
        "schema": "idx-trade/tradingview-historical-price-path-v2-1-preregistration-final",
        "created_before_network": True,
        "network_authorized": False,
        "network_calls": 0,
        "code_head": code_head,
        "lineage": summary.get("frozen_failed_v2_verdict_unchanged"),
        "depth_contract": {"initial_range": 500, "fetch_more_batch": 5000, "fetch_more_steps": 3, "required_start": "2021-04-01", "prior_official_session_buffer": 1},
        "control_matrix": control_request_fixture(json.loads(a.config.read_text(encoding="utf-8"))),
        "input_hashes": input_hashes,
        "existing_offline_artifact_root": str(offline),
        "existing_offline_manifest_sha256": summary_manifest.get("manifest_sha256"),
        "existing_offline_preregistration_sha256": sha256_file(offline / "preregistration.json"),
        "existing_offline_decision_input_hashes": original_prereg.get("input_hashes", {}),
        "canonical_panel_sha256": PANEL_SHA,
        "canonical_fidelity_directory_manifest": directory_manifest(a.canonical_raw_root),
        "official_stock_summary_archive_manifest_sha256": sha256_file(a.stock_summary_root / "archive_manifest.json"),
        "completion_taxonomy": ["REQUIRED_START_REACHED", "MAX_DEPTH_EXHAUSTED", "NO_EXTENSION", "TIMEOUT", "PROVIDER_ERROR"],
        "boundaries": {"no_full_acquisition": True, "no_model": True, "no_panel_write": True, "no_path_risk": True, "no_o2_or_outcomes": True},
    }
    write_json(a.output_root / "preregistration.json", prereg)
    prereg_files = {"preregistration.json", "symbol_error_detail.csv"}
    pre_artifacts = []
    for name in sorted(prereg_files):
        path = a.output_root / name
        pre_artifacts.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(a.output_root / "prereg_artifact_manifest.json", {"schema": "idx-trade/tradingview-price-path-v2-1-prereg-artifact-manifest", "artifacts": pre_artifacts})
    write_json(a.output_root / "confirmed_bug_remediation_report.json", {"bugs_addressed": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21], "depth_contract": "500 initial / 5000 batch / 3 hard cap with early required-start stop", "network_calls": 0, "frozen_v2_verdict_unchanged": True, "official_stock_summary_oracle_role": "diagnostic only; no admission oracle substitution"})
    symbol_resolution_required = maximum_overall < float(config["gates"]["active_coverage_overall"]) or any(
        row["maximum_if_other_symbols_perfect"] < float(config["gates"]["active_coverage_year"])
        for row in yearly_ceiling.values()
    )
    offline_verdict = "V2_1_BLOCKED_SYMBOL_RESOLUTION_REQUIRED" if symbol_resolution_required else "V2_1_REMEDIATION_READY_FOR_FULL_PREREGISTRATION"
    offline_reason = (
        "16 exact TradingView SYMBOL_ERROR tickers remain under unchanged IDX:<ticker> contract and their theoretical coverage ceiling misses a frozen gate"
        if symbol_resolution_required else
        "16 exact TradingView SYMBOL_ERROR tickers remain, but their theoretical coverage ceiling clears all frozen coverage gates; bounded depth preflight is the next permitted test"
    )
    final = {"verdict": offline_verdict, "reason": offline_reason, "offline_root_reused": str(offline), "offline_root_manifest_sha256": summary_manifest.get("manifest_sha256"), "canonical_panel_sha256_before": PANEL_SHA, "canonical_panel_sha256_after": sha256_file(panel), "network_calls": 0, "symbol_error_active_sessions": int(error_frame.drop_duplicates("ticker")["active_sessions"].sum()), "maximum_overall_if_other_symbols_perfect": maximum_overall, "official_stock_summary_oracle_recommendation": oracle_summary["recommendation"], "official_stock_summary_oracle_role": "diagnostic only", "fidelity_support": support, "oracle": oracle_summary, "modeling_authorized": False, "protected_outcomes_accessed": False}
    write_json(a.output_root / "final_remediation_summary.json", final)
    runtime_manifest = artifact_manifest(a.output_root, exclude={"prereg_artifact_manifest.json", "runtime_artifact_manifest.json"})
    write_json(a.output_root / "runtime_artifact_manifest.json", runtime_manifest)
    print(json.dumps({"output_root": str(a.output_root), "verdict": final["verdict"], "manifest_sha256": runtime_manifest["manifest_sha256"], "oracle_recommendation": oracle_summary["recommendation"], "oracle_summary": oracle_summary, "yearly_symbol_ceiling": yearly_ceiling}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
