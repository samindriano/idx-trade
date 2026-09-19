"""Read-only diagnostic for one unseen Foreign Flow transition snapshot.

This deliberately consumes the already accepted V2 builder from the isolated
forward-shadow worktree. It never writes a canonical artifact, reads outcomes,
updates a counter, or mutates the forward runtime.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


SOURCE_WORKTREE = Path(
    r"C:\Users\Sam\.codex\worktrees\idx-foreign-flow-prospective-pit-shadow-v1"
)
sys.path.insert(0, str(SOURCE_WORKTREE / "src"))

from idx_trade.foreign_flow_features_v2 import (  # noqa: E402
    build_foreign_flow_representation_v2,
)
from idx_trade.foreign_flow_representation_v2_runner import (  # noqa: E402
    build_causal_market_context,
    read_verified_flow_archive,
)


DATA_ROOT = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v")
MONITOR_ROOT = DATA_ROOT / "forward_monitoring"
ARCHIVE_ROOT = Path(
    r"D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1"
)
ARCHIVE_MANIFEST_SHA256 = (
    "fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334"
)
PANEL_PATH = (
    DATA_ROOT
    / "v4_x_clean_data_consolidation_v1_final_20260820_v2"
    / "model_safe_signal_research_panel_1260_final_clean.parquet"
)
MASTER_PATH = (
    MONITOR_ROOT
    / "v4_x1_clean_inputs"
    / "security_master"
    / "security_master_39c34074204bc09af3521a73bd66d2dbc45faf6b81dd0ed0c8c25f4e3880df93.csv"
)
HISTORICAL_LAST_SOURCE = pd.Timestamp("2026-08-13")
SOURCE_SESSION = pd.Timestamp("2026-09-16")
FEATURE_SESSION = pd.Timestamp("2026-09-17")
INCUMBENT_SCORE_PATH = (
    MONITOR_ROOT
    / "model_runs"
    / "2026-09-17"
    / "v4_x1_clean_geometry3_prospective_v1"
    / "score_artifact.parquet"
)


def _read_forward_inputs() -> tuple[list[pd.DataFrame], list[pd.DataFrame]]:
    market_frames: list[pd.DataFrame] = []
    flow_frames: list[pd.DataFrame] = []
    session_root = MONITOR_ROOT / "sessions"
    for name in sorted(path.name for path in session_root.iterdir() if path.is_dir()):
        if name <= "2026-07-31" or name > SOURCE_SESSION.date().isoformat():
            continue
        session_dir = session_root / name
        ohlcv_path = session_dir / "session_ohlcv.parquet"
        evidence_path = session_dir / "session_evidence.parquet"
        raw_path = session_dir / "idx_stock_summary.raw.json"
        if not all(path.is_file() for path in (ohlcv_path, evidence_path, raw_path)):
            continue

        ohlcv = pd.read_parquet(ohlcv_path)
        evidence = pd.read_parquet(
            evidence_path,
            columns=["ticker", "session_date", "point_state", "regular_market_value"],
        )
        evidence = evidence.loc[
            evidence["point_state"].eq("ACTIVE"),
            ["ticker", "session_date", "regular_market_value"],
        ]
        for frame in (ohlcv, evidence):
            frame["ticker"] = (
                frame["ticker"]
                .astype(str)
                .str.upper()
                .str.replace(".JK", "", regex=False)
                .str.strip()
            )
            frame["session_date"] = pd.to_datetime(frame["session_date"]).dt.normalize()
        market = ohlcv[["ticker", "session_date", "close", "volume"]].merge(
            evidence,
            on=["ticker", "session_date"],
            how="inner",
            validate="one_to_one",
        )
        market_frames.append(
            market.rename(columns={"session_date": "date"})[
                ["ticker", "date", "close", "volume", "regular_market_value"]
            ]
        )

        # Historical archive is authoritative through 2026-08-13. Do not
        # silently merge duplicate source identities from the forward root.
        if pd.Timestamp(name) <= HISTORICAL_LAST_SOURCE:
            continue
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        rows = payload.get("data", [])
        flow = pd.DataFrame(
            {
                "ticker": [str(row["StockCode"]).upper().strip() for row in rows],
                "session_date": [pd.Timestamp(row["Date"]).normalize() for row in rows],
                "foreign_buy": [row["ForeignBuy"] for row in rows],
                "foreign_sell": [row["ForeignSell"] for row in rows],
            }
        )
        for column in ("foreign_buy", "foreign_sell"):
            flow[column] = pd.to_numeric(flow[column], errors="coerce")
        if flow[["foreign_buy", "foreign_sell"]].isna().any().any():
            raise ValueError(f"missing numeric foreign flow in {name}")
        flow["foreign_buy"] = flow["foreign_buy"].astype("int64")
        flow["foreign_sell"] = flow["foreign_sell"].astype("int64")
        flow["foreign_net"] = flow["foreign_buy"] - flow["foreign_sell"]
        flow["unit"] = "SHARES"
        flow_frames.append(
            flow[
                [
                    "ticker",
                    "session_date",
                    "foreign_buy",
                    "foreign_sell",
                    "foreign_net",
                    "unit",
                ]
            ]
        )
    return market_frames, flow_frames


def main() -> None:
    historical_market = pd.read_parquet(
        PANEL_PATH,
        columns=["ticker", "date", "close", "volume", "regular_market_value"],
    )
    historical_market["ticker"] = (
        historical_market["ticker"].astype(str).str.upper().str.strip()
    )
    historical_market["date"] = pd.to_datetime(historical_market["date"]).dt.normalize()
    forward_market, forward_flow = _read_forward_inputs()
    market = pd.concat([historical_market, *forward_market], ignore_index=True)
    if market.duplicated(["ticker", "date"]).any():
        raise ValueError("market duplicate identity after merge")

    historical_flow, _ = read_verified_flow_archive(
        ARCHIVE_ROOT, ARCHIVE_MANIFEST_SHA256
    )
    flow = pd.concat([historical_flow, *forward_flow], ignore_index=True)
    flow = flow.loc[flow["session_date"].le(SOURCE_SESSION)].copy()
    if flow.duplicated(["ticker", "session_date"]).any():
        raise ValueError("flow duplicate identity after authoritative boundary")

    master = pd.read_csv(MASTER_PATH)
    master["ticker"] = master["ticker"].astype(str).str.upper().str.strip()
    master["listed_from"] = pd.to_datetime(master["listed_from"], errors="raise").dt.normalize()
    master["listed_to"] = pd.to_datetime(master["listed_to"], errors="coerce").dt.normalize()

    historical_calendar = pd.read_csv(
        DATA_ROOT
        / "v4_x_clean_data_consolidation_v1_final_20260820_v2"
        / "official_exchange_sessions_1260.csv"
    )
    historical_dates = pd.to_datetime(historical_calendar.iloc[:, 0]).dt.normalize()
    forward_dates = pd.to_datetime(
        pd.Series([path.name for path in (MONITOR_ROOT / "sessions").iterdir() if path.is_dir()])
    ).dt.normalize()
    official = pd.DatetimeIndex(sorted(set(historical_dates) | set(forward_dates)))
    official_set = set(official)
    flow = flow.loc[flow["session_date"].isin(official_set)].copy()
    market = market.loc[market["date"].isin(official_set)].copy()

    context, excluded = build_causal_market_context(market, master, official)
    volume = market[["ticker", "date", "volume"]].rename(columns={"volume": "raw_volume"})
    representation = build_foreign_flow_representation_v2(
        flow,
        volume,
        context,
        master,
        official,
    )
    target = representation.loc[
        representation["feature_session"].eq(FEATURE_SESSION)
    ].copy()
    target["transition_score"] = (
        target["foreign_weighted_persistence_5"]
        - target["foreign_weighted_persistence_20"]
    )
    valid = np.isfinite(target["transition_score"].to_numpy())
    target["transition_available"] = valid
    target["transition_rank"] = (
        target.groupby("feature_session")["transition_score"]
        .rank(method="average", pct=True)
        .fillna(0.5)
    )
    outcome_columns = [
        column
        for column in target.columns
        if any(
            token in column.lower()
            for token in ("outcome", "target", "label", "realized", "tp_first", "sl_first")
        )
    ]
    incumbent = pd.read_parquet(
        INCUMBENT_SCORE_PATH,
        columns=["ticker", "date", "rank_consensus", "alpha_consensus"],
    )
    incumbent["date"] = pd.to_datetime(incumbent["date"]).dt.normalize()
    joined = incumbent.merge(
        target[
            [
                "ticker",
                "feature_session",
                "transition_rank",
                "transition_available",
            ]
        ],
        left_on=["ticker", "date"],
        right_on=["ticker", "feature_session"],
        how="inner",
        validate="one_to_one",
    )
    structural_corr = joined[["rank_consensus", "transition_rank"]].corr(
        method="spearman"
    ).iloc[0, 1]
    top_n = min(30, len(joined))
    incumbent_top = set(
        joined.nlargest(top_n, "rank_consensus")["ticker"].astype(str)
    )
    fixed_blend = 0.90 * joined["rank_consensus"] + 0.10 * joined["transition_rank"]
    candidate_top = set(joined.assign(_fixed_blend=fixed_blend).nlargest(top_n, "_fixed_blend")["ticker"].astype(str))
    top30_overlap = len(incumbent_top & candidate_top) / float(top_n) if top_n else float("nan")
    print("diagnostic_status=OUTCOME_BLIND_SHADOW_ONLY")
    print(f"source_session={SOURCE_SESSION.date().isoformat()}")
    print(f"feature_session={FEATURE_SESSION.date().isoformat()}")
    print(f"official_session_count={len(official)}")
    print(
        f"market_rows={len(market)} flow_rows={len(flow)} "
        f"excluded_listing_rows={len(excluded)}"
    )
    print(f"target_rows={len(target)} target_tickers={target['ticker'].nunique()}")
    print(
        f"transition_available={int(valid.sum())} of {len(target)} "
        f"rate={float(valid.mean()):.8f}"
    )
    print(
        f"transition_rank_bounds={float(target['transition_rank'].min())} "
        f"{float(target['transition_rank'].max())}"
    )
    print(
        "flow_through_exact="
        f"{bool(target['flow_through_session'].eq(SOURCE_SESSION).all())}"
    )
    print(f"duplicate_target_keys={int(target.duplicated(['ticker', 'feature_session']).sum())}")
    print(f"outcome_columns_present={outcome_columns}")
    print(
        f"incumbent_score_rows={len(incumbent)} common_score_rows={len(joined)} "
        f"common_transition_available={int(joined['transition_available'].sum())}"
    )
    print(f"prospective_rank_spearman={float(structural_corr):.8f}")
    print(f"fixed_blend_top30_overlap={float(top30_overlap):.8f}")
    print(f"fixed_blend_top30_churn={1.0 - float(top30_overlap):.8f}")


if __name__ == "__main__":
    main()
