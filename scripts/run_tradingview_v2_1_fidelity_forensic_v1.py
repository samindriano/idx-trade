"""Offline Step-1 forensic audit for the TradingView V2/V2.1 2022 HLC anomaly.

Reads only immutable local artifacts.  This script contains no provider/network
call path and does not fit models or access protected outcomes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from idx_trade.tradingview_price_path_v2 import aggregate_daily, load_canonical
from idx_trade.tradingview_price_path_v2_1 import corporate_action_flags, sha256_file
from idx_trade.tradingview_v2_1_fidelity_forensic import (
    CONTROL_TICKERS,
    add_hlc_comparisons,
    adjudicate_2022,
    bar_count_summary,
    concentration_table,
    end_cohort,
    hlc_mismatch_pattern,
    three_way_classification,
    yearly_fidelity_summary,
)


WINDOW_START = "2021-04-01"
WINDOW_END = "2026-07-31"
LEGACY_V2_ROOT = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814")
V21_PREFLIGHT_ROOT = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_1_depth_preflight_20260816")
CANONICAL_RAW_ROOT = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\prices_1260\raw")
CANONICAL_PANEL = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet")
STOCK_SUMMARY_ROOT = Path(r"D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1")
OUTPUT_ROOT = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_v2_1_fidelity_forensic_v1_20260820")
EXPECTED_PANEL_SHA = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-v2-root", type=Path, default=LEGACY_V2_ROOT)
    parser.add_argument("--v21-preflight-root", type=Path, default=V21_PREFLIGHT_ROOT)
    parser.add_argument("--canonical-raw-root", type=Path, default=CANONICAL_RAW_ROOT)
    parser.add_argument("--canonical-panel", type=Path, default=CANONICAL_PANEL)
    parser.add_argument("--stock-summary-root", type=Path, default=STOCK_SUMMARY_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    return parser.parse_args()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def artifact_manifest(root: Path) -> dict[str, Any]:
    artifacts = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "artifact_manifest.json":
            continue
        artifacts.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema": "idx-trade/tradingview-v2-1-fidelity-forensic-v1-manifest",
        "artifacts": artifacts,
    }


def read_control_bars(preflight_root: Path) -> pd.DataFrame:
    frames = []
    for index, ticker in enumerate(CONTROL_TICKERS, start=1):
        path = preflight_root / "normalized" / f"{index:02d}_{ticker}.csv"
        if not path.exists():
            raise SystemExit(f"missing V2.1 control normalized artifact: {path}")
        frame = pd.read_csv(path, dtype={"ticker": str, "security_id": str, "session_date": str})
        if "session_admissible" not in frame:
            raise SystemExit(f"missing session_admissible in {path}")
        frame["session_admissible"] = frame["session_admissible"].astype(str).str.lower().eq("true")
        if not frame["ticker"].astype(str).str.upper().eq(ticker).all():
            raise SystemExit(f"control ticker mismatch in {path}")
        frames.append(frame)
    bars = pd.concat(frames, ignore_index=True)
    bars = bars[
        bars["session_admissible"]
        & bars["session_date"].between(WINDOW_START, WINDOW_END)
    ].copy()
    if bars.empty:
        raise SystemExit("V2.1 control bars are empty inside the required window")
    return bars


def load_official_idx_hlcv(
    archive_root: Path,
    keys: set[tuple[str, str]],
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    dates = sorted({date for _, date in keys})
    tickers_by_date: dict[str, set[str]] = {}
    for ticker, date in keys:
        tickers_by_date.setdefault(date, set()).add(ticker)
    for session_date in dates:
        path = archive_root / "sessions" / session_date / "stock_summary.raw.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        wanted = tickers_by_date[session_date]
        for row in payload.get("data", []):
            ticker = str(row.get("StockCode", "")).upper().replace(".JK", "").strip()
            if ticker not in wanted:
                continue
            records.append(
                {
                    "ticker": ticker,
                    "session_date": session_date,
                    "idx_high": pd.to_numeric(row.get("High"), errors="coerce"),
                    "idx_low": pd.to_numeric(row.get("Low"), errors="coerce"),
                    "idx_close": pd.to_numeric(row.get("Close"), errors="coerce"),
                    "idx_volume": pd.to_numeric(row.get("Volume"), errors="coerce"),
                }
            )
    if not records:
        return pd.DataFrame(columns=["ticker", "session_date", "idx_high", "idx_low", "idx_close", "idx_volume"])
    return pd.DataFrame(records).drop_duplicates(["ticker", "session_date"], keep="last")


def add_three_way_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = add_hlc_comparisons(
        frame,
        left_prefix="tv_",
        right_prefix="canonical_",
        result_prefix="tv_canonical",
    )
    result = add_hlc_comparisons(
        result,
        left_prefix="tv_",
        right_prefix="idx_",
        result_prefix="tv_idx",
    )
    result = add_hlc_comparisons(
        result,
        left_prefix="canonical_",
        right_prefix="idx_",
        result_prefix="canonical_idx",
    )
    result["tv_canonical_pattern"] = hlc_mismatch_pattern(
        result,
        left_prefix="tv_",
        right_prefix="canonical_",
    )
    result["three_way_class"] = three_way_classification(result)
    for field in ("high", "low", "close"):
        result[f"tv_minus_canonical_{field}"] = (
            pd.to_numeric(result[f"tv_{field}"], errors="coerce")
            - pd.to_numeric(result[f"canonical_{field}"], errors="coerce")
        )
        result[f"tv_minus_idx_{field}"] = (
            pd.to_numeric(result[f"tv_{field}"], errors="coerce")
            - pd.to_numeric(result[f"idx_{field}"], errors="coerce")
        )
    return result


def control_forensic(
    *,
    bars: pd.DataFrame,
    canonical_raw_root: Path,
    stock_summary_root: Path,
    events: pd.DataFrame,
    sessions: pd.DataFrame,
) -> pd.DataFrame:
    daily = aggregate_daily(bars).rename(
        columns={
            "open": "tv_open",
            "high": "tv_high",
            "low": "tv_low",
            "close": "tv_close",
            "volume": "tv_volume",
        }
    )
    canonical = load_canonical(canonical_raw_root, CONTROL_TICKERS)
    keys = set(zip(daily["ticker"], daily["session_date"]))
    official = load_official_idx_hlcv(stock_summary_root, keys)
    merged = (
        daily.merge(canonical, on=["ticker", "session_date"], how="left")
        .merge(official, on=["ticker", "session_date"], how="left")
    )
    quarantine_input = merged[["ticker", "session_date"]].copy()
    merged["ca_quarantined"] = corporate_action_flags(quarantine_input, events, sessions)
    merged = merged[~merged["ca_quarantined"]].copy()
    return add_three_way_columns(merged)


def load_panel_provenance(panel_path: Path, keys: pd.DataFrame) -> pd.DataFrame:
    panel = pd.read_parquet(panel_path, columns=["ticker", "date", "price_provenance"])
    panel["ticker"] = panel["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    panel["session_date"] = pd.to_datetime(panel["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    wanted = keys[["ticker", "session_date"]].drop_duplicates()
    return panel[["ticker", "session_date", "price_provenance"]].merge(
        wanted,
        on=["ticker", "session_date"],
        how="inner",
    ).drop_duplicates(["ticker", "session_date"], keep="last")


def legacy_2022_forensic(
    *,
    legacy_root: Path,
    canonical_panel: Path,
    stock_summary_root: Path,
    events: pd.DataFrame,
    sessions: pd.DataFrame,
) -> pd.DataFrame:
    fidelity_path = legacy_root / "normalized" / "fidelity_rows.csv"
    request_path = legacy_root / "request_manifest.csv"
    universe_path = legacy_root / "universe.csv"
    for path in (fidelity_path, request_path, universe_path):
        if not path.exists():
            raise SystemExit(f"missing legacy V2 artifact: {path}")

    rows = pd.read_csv(fidelity_path, dtype={"ticker": str, "session_date": str})
    rows["ticker"] = rows["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    rows = rows[pd.to_datetime(rows["session_date"], errors="coerce").dt.year.eq(2022)].copy()
    if rows.empty:
        raise SystemExit("legacy V2 has no 2022 fidelity rows")

    rows = rows.rename(
        columns={
            "high": "tv_high",
            "low": "tv_low",
            "close": "tv_close",
            "volume": "tv_volume",
        }
    )
    quarantine_input = rows[["ticker", "session_date"]].copy()
    rows["ca_quarantined_v21"] = corporate_action_flags(quarantine_input, events, sessions)
    rows = rows[~rows["ca_quarantined_v21"]].copy()

    requests = pd.read_csv(request_path, dtype={"ticker": str, "security_id": str})
    requests["ticker"] = requests["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    request_cols = [column for column in ("ticker", "required_start", "required_end", "security_id") if column in requests]
    rows = rows.merge(requests[request_cols].drop_duplicates("ticker"), on="ticker", how="left")

    universe = pd.read_csv(universe_path, dtype=str)
    universe["ticker"] = universe["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    if "listed_from" not in universe:
        universe["listed_from"] = pd.NA
    if "listed_to" not in universe:
        universe["listed_to"] = pd.NA
    intervals = (
        universe[["ticker", "listed_from", "listed_to"]]
        .sort_values(["ticker", "listed_from"])
        .drop_duplicates("ticker", keep="last")
    )
    rows = rows.merge(intervals, on="ticker", how="left")
    rows["end_cohort"] = [
        end_cohort(required_end, listed_to, WINDOW_END)
        for required_end, listed_to in zip(rows["required_end"], rows["listed_to"])
    ]

    provenance = load_panel_provenance(canonical_panel, rows)
    rows = rows.merge(provenance, on=["ticker", "session_date"], how="left")

    keys = set(zip(rows["ticker"], rows["session_date"]))
    official = load_official_idx_hlcv(stock_summary_root, keys)
    rows = rows.merge(official, on=["ticker", "session_date"], how="left")
    rows = add_three_way_columns(rows)
    return rows


def summary_payload(
    controls: pd.DataFrame,
    legacy_2022: pd.DataFrame,
) -> dict[str, Any]:
    control_year_tv_canonical = yearly_fidelity_summary(
        controls,
        source_pair_prefix="tv_canonical",
    )
    control_year_tv_idx = yearly_fidelity_summary(
        controls[controls["three_way_class"].ne("INSUFFICIENT_THREE_WAY_SUPPORT")],
        source_pair_prefix="tv_idx",
    )
    legacy_concentration = concentration_table(
        legacy_2022.assign(tv_canonical_mismatch=~legacy_2022["tv_canonical_hlc_exact"]),
        mismatch_column="tv_canonical_mismatch",
    )
    mismatch_count = int((~legacy_2022["tv_canonical_hlc_exact"]).sum())
    concentration = {}
    for n in (5, 10, 20, 50):
        top = legacy_concentration.head(n)
        concentration[f"top_{n}_mismatch_share"] = (
            float(top["mismatch_rows"].sum() / mismatch_count) if mismatch_count else 0.0
        )

    return {
        "schema": "idx-trade/tradingview-v2-1-fidelity-forensic-v1",
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "controls": list(CONTROL_TICKERS),
        "control_yearly_tv_vs_canonical": control_year_tv_canonical.to_dict(orient="records"),
        "control_yearly_tv_vs_idx": control_year_tv_idx.to_dict(orient="records"),
        "control_bar_count_by_year": bar_count_summary(controls).to_dict(orient="records"),
        "control_three_way_counts": {
            str(key): int(value)
            for key, value in controls["three_way_class"].value_counts(dropna=False).items()
        },
        "legacy_2022_rows": int(len(legacy_2022)),
        "legacy_2022_tv_vs_canonical_exact_rate": float(legacy_2022["tv_canonical_hlc_exact"].mean()),
        "legacy_2022_mismatch_pattern_counts": {
            str(key): int(value)
            for key, value in legacy_2022["tv_canonical_pattern"].value_counts(dropna=False).items()
        },
        "legacy_2022_three_way_counts": {
            str(key): int(value)
            for key, value in legacy_2022["three_way_class"].value_counts(dropna=False).items()
        },
        "legacy_2022_end_cohort_counts": {
            str(key): int(value)
            for key, value in legacy_2022["end_cohort"].value_counts(dropna=False).items()
        },
        "legacy_2022_provenance_counts": {
            str(key): int(value)
            for key, value in legacy_2022["price_provenance"].fillna("MISSING").value_counts().items()
        },
        "legacy_2022_concentration": concentration,
        "adjudication": adjudicate_2022(controls, legacy_2022),
        "network_calls": 0,
        "provider_calls": 0,
        "model_fit": False,
        "path_risk_run": False,
        "protected_outcomes_accessed": False,
    }


def main() -> int:
    args = parse_args()
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output root: {args.output_root}")
    args.output_root.mkdir(parents=True, exist_ok=True)

    required = [
        args.legacy_v2_root / "official_sessions.csv",
        args.legacy_v2_root / "corporate_action_events.csv",
        args.legacy_v2_root / "runtime_summary.json",
        args.legacy_v2_root / "normalized" / "fidelity_rows.csv",
        args.v21_preflight_root / "preflight_summary.json",
        args.v21_preflight_root / "runtime_artifact_manifest.json",
        args.canonical_panel,
        args.stock_summary_root / "archive_manifest.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("missing required immutable inputs:\n" + "\n".join(missing))
    if sha256_file(args.canonical_panel) != EXPECTED_PANEL_SHA:
        raise SystemExit("canonical panel SHA mismatch")

    preflight = json.loads((args.v21_preflight_root / "preflight_summary.json").read_text(encoding="utf-8"))
    if not preflight.get("all_controls_pass") or int(preflight.get("provider_requests_made", -1)) != 5:
        raise SystemExit("V2.1 preflight is not the accepted 5/5 control runtime")

    sessions = pd.read_csv(args.legacy_v2_root / "official_sessions.csv")
    events = pd.read_csv(args.legacy_v2_root / "corporate_action_events.csv", dtype={"ticker": str})
    control_bars = read_control_bars(args.v21_preflight_root)
    controls = control_forensic(
        bars=control_bars,
        canonical_raw_root=args.canonical_raw_root,
        stock_summary_root=args.stock_summary_root,
        events=events,
        sessions=sessions,
    )
    legacy_2022 = legacy_2022_forensic(
        legacy_root=args.legacy_v2_root,
        canonical_panel=args.canonical_panel,
        stock_summary_root=args.stock_summary_root,
        events=events,
        sessions=sessions,
    )

    write_csv(args.output_root / "control_same_ticker_fidelity_rows.csv", controls)
    write_csv(
        args.output_root / "control_same_ticker_yearly_tv_vs_canonical.csv",
        yearly_fidelity_summary(controls, source_pair_prefix="tv_canonical"),
    )
    write_csv(
        args.output_root / "control_same_ticker_yearly_tv_vs_idx.csv",
        yearly_fidelity_summary(
            controls[controls["three_way_class"].ne("INSUFFICIENT_THREE_WAY_SUPPORT")],
            source_pair_prefix="tv_idx",
        ),
    )
    write_csv(args.output_root / "control_bar_count_by_year.csv", bar_count_summary(controls))
    write_csv(args.output_root / "legacy_v2_2022_forensic_rows.csv", legacy_2022)

    by_ticker = concentration_table(
        legacy_2022.assign(tv_canonical_mismatch=~legacy_2022["tv_canonical_hlc_exact"]),
        mismatch_column="tv_canonical_mismatch",
    )
    metadata = legacy_2022[
        ["ticker", "end_cohort", "required_end", "listed_to", "price_provenance"]
    ].drop_duplicates("ticker")
    by_ticker = by_ticker.merge(metadata, on="ticker", how="left")
    write_csv(args.output_root / "legacy_v2_2022_mismatch_concentration.csv", by_ticker)

    three_way = (
        legacy_2022.groupby(["three_way_class", "tv_canonical_pattern"], dropna=False)
        .size()
        .rename("rows")
        .reset_index()
        .sort_values("rows", ascending=False)
    )
    write_csv(args.output_root / "legacy_v2_2022_three_way_breakdown.csv", three_way)

    summary = summary_payload(controls, legacy_2022)
    summary["input_hashes"] = {
        "legacy_runtime_summary": sha256_file(args.legacy_v2_root / "runtime_summary.json"),
        "legacy_fidelity_rows": sha256_file(args.legacy_v2_root / "normalized" / "fidelity_rows.csv"),
        "v21_preflight_summary": sha256_file(args.v21_preflight_root / "preflight_summary.json"),
        "v21_runtime_manifest": sha256_file(args.v21_preflight_root / "runtime_artifact_manifest.json"),
        "canonical_panel": sha256_file(args.canonical_panel),
        "stock_summary_archive_manifest": sha256_file(args.stock_summary_root / "archive_manifest.json"),
    }
    write_json(args.output_root / "forensic_summary.json", summary)
    manifest = artifact_manifest(args.output_root)
    write_json(args.output_root / "artifact_manifest.json", manifest)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
