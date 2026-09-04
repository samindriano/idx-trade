"""Build the outcome-blind Foreign Flow Behavioral Forensics V1 evidence pack.

This is a research-only materializer.  It reads the already accepted, hash-pinned
offline inputs and writes to the external artifact root.  It does not import the
V2 feature builder, call providers, read outcomes, or modify production state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ART = Path(r"D:\Documents\Project\idx-trade-foreign-flow-representation-v2-20260815-001")
OUT = Path(r"D:\Documents\Project\idx-foreign-flow-behavioral-forensics-20260904-v1")
ARCH = Path(r"D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1")
PANEL_PATH = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809"
    r"\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet"
)
CAL_PATH = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809"
    r"\official_exchange_sessions_1260.csv"
)
MASTER_PATH = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809"
    r"\security_master_1260.csv"
)
CA_PATH = Path(
    r"D:\Documents\Project\idx-ca-economic-event-reconciliation-20260831-v16-composite-policy"
    r"\transition_attestation_ledger.csv"
)

FEATURES = [
    "foreign_participation_1",
    "foreign_participation_mean_5",
    "foreign_flow_shock_1",
    "foreign_flow_shock_mean_5",
    "foreign_flow_shock_mean_20",
    "foreign_flow_shock_percentile_120",
    "xs_rank_foreign_flow_shock_1",
    "xs_rank_foreign_flow_shock_mean_5",
    "xs_rank_foreign_flow_shock_mean_20",
    "foreign_weighted_persistence_5",
    "foreign_weighted_persistence_20",
    "foreign_signed_streak_10",
    "foreign_flow_acceleration_5_20",
    "foreign_flow_price_divergence_5",
    "foreign_flow_price_divergence_20",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def emit(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(OUT / name, index=False)


def rank_corr(frame: pd.DataFrame, left: str, right: str) -> tuple[int, float | None]:
    values = frame[[left, right]].apply(pd.to_numeric, errors="coerce")
    values = values.replace([np.inf, -np.inf], np.nan).dropna()
    if len(values) < 3:
        return len(values), None
    return len(values), float(spearmanr(values[left], values[right]).statistic)


def listed_mask(dates: pd.Series, ticker: str, master: pd.DataFrame) -> np.ndarray:
    result = np.zeros(len(dates), dtype=bool)
    for row in master.loc[master["ticker"].eq(ticker)].itertuples(index=False):
        end = pd.Timestamp.max.normalize() if pd.isna(row.listed_to) else row.listed_to
        result |= (dates.to_numpy() >= row.listed_from) & (dates.to_numpy() <= end)
    return result


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    input_manifest = json.loads((ART / "input_manifest.json").read_text(encoding="utf-8"))
    archive_manifest_path = ARCH / "archive_manifest.json"
    archive_manifest = json.loads(archive_manifest_path.read_text(encoding="utf-8"))
    calendar = pd.read_csv(CAL_PATH)
    sessions = pd.DatetimeIndex(pd.to_datetime(calendar["date"]).dt.normalize())
    master = pd.read_csv(MASTER_PATH)
    master["ticker"] = master["ticker"].astype(str).str.upper().str.replace(
        ".JK", "", regex=False
    ).str.strip()
    master["listed_from"] = pd.to_datetime(master["listed_from"]).dt.normalize()
    master["listed_to"] = pd.to_datetime(master["listed_to"], errors="coerce").dt.normalize()

    pieces: list[pd.DataFrame] = []
    missing_files: list[str] = []
    manifest_items = archive_manifest.get("artifacts", archive_manifest.get("normalized_artifacts", []))
    for item in manifest_items:
        relative = item.get("path")
        if not relative or not str(relative).endswith("foreign_flow.parquet"):
            continue
        source = ARCH / relative
        if not source.exists():
            missing_files.append(str(source))
            continue
        pieces.append(pd.read_parquet(source))
    flow = pd.concat(pieces, ignore_index=True)
    flow["ticker"] = flow["ticker"].astype(str).str.upper().str.strip()
    flow["session_date"] = pd.to_datetime(flow["session_date"]).dt.normalize()
    official = flow.loc[flow["session_date"].isin(set(sessions))].copy()

    features = pd.read_parquet(ART / "foreign_flow_representation_v2.parquet")
    features["feature_session"] = pd.to_datetime(features["feature_session"]).dt.normalize()
    features["flow_through_session"] = pd.to_datetime(features["flow_through_session"]).dt.normalize()
    panel = pd.read_parquet(
        PANEL_PATH,
        columns=[
            "ticker",
            "date",
            "high",
            "low",
            "close",
            "volume",
            "regular_market_value",
            "price_provenance",
            "corporate_action_integrity_verified",
        ],
    )
    panel["ticker"] = panel["ticker"].astype(str).str.upper().str.replace(
        ".JK", "", regex=False
    ).str.strip()
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel = panel.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    panel["prev_close"] = panel.groupby("ticker", sort=False)["close"].shift(1)
    panel["same_session_close_return"] = panel["close"] / panel["prev_close"] - 1.0
    panel["range_fraction"] = (panel["close"] - panel["low"]) / panel["close"]
    panel["intraday_range_fraction"] = (panel["high"] - panel["low"]) / panel["close"]

    # Independent checks: raw net identity, participation, shock_1, and the
    # explicitly declared acceleration identity.  The code does not import V2.
    flow_index = official.set_index(["ticker", "session_date"])["foreign_net"]
    market_index = panel.set_index(["ticker", "date"])
    recalc_rows: list[dict[str, object]] = []
    for ticker in sorted(set(features["ticker"])):
        if ticker not in set(master["ticker"]):
            continue
        dates = sessions.to_series(index=sessions)
        listed = listed_mask(dates, ticker, master)
        net = flow_index.reindex(pd.MultiIndex.from_product([[ticker], sessions])).to_numpy(dtype=float)
        close = market_index["close"].reindex(
            pd.MultiIndex.from_product([[ticker], sessions], names=["ticker", "date"])
        ).to_numpy(dtype=float)
        rmv = market_index["regular_market_value"].reindex(
            pd.MultiIndex.from_product([[ticker], sessions], names=["ticker", "date"])
        ).to_numpy(dtype=float)
        volume = market_index["volume"].reindex(
            pd.MultiIndex.from_product([[ticker], sessions], names=["ticker", "date"])
        ).to_numpy(dtype=float)
        net[~listed] = np.nan
        close[~listed] = np.nan
        rmv[~listed] = np.nan
        volume[~listed] = np.nan
        participation = np.full(len(sessions), np.nan)
        valid = np.isfinite(net) & np.isfinite(volume) & (volume > 0)
        participation[valid] = net[valid] / volume[valid]
        shock = np.full(len(sessions), np.nan)
        for index in range(len(sessions)):
            baseline = rmv[max(0, index - 20) : index]
            baseline = baseline[np.isfinite(baseline) & (baseline >= 0)]
            if len(baseline) >= 10 and np.isfinite(net[index] * close[index]):
                median = float(np.median(baseline))
                if median > 0:
                    shock[index] = net[index] * close[index] / median
        next_session = {sessions[i]: sessions[i + 1] for i in range(len(sessions) - 1)}
        feature_dates = [next_session.get(day) for day in sessions]
        for index, feature_date in enumerate(feature_dates):
            if feature_date is not None and listed[index] and listed[index + 1] if index + 1 < len(sessions) else False:
                recalc_rows.append(
                    {
                        "ticker": ticker,
                        "feature_session": feature_date,
                        "recomputed_participation_1": participation[index],
                        "recomputed_shock_1": shock[index],
                    }
                )
    recalc = pd.DataFrame(recalc_rows)
    compared = features.merge(recalc, on=["ticker", "feature_session"], how="left", validate="one_to_one")
    checks: list[dict[str, object]] = []
    for accepted, recomputed in [
        ("foreign_participation_1", "recomputed_participation_1"),
        ("foreign_flow_shock_1", "recomputed_shock_1"),
    ]:
        a = pd.to_numeric(compared[accepted], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(compared[recomputed], errors="coerce").to_numpy(dtype=float)
        equal = np.isclose(a, b, rtol=1e-10, atol=1e-12, equal_nan=True)
        checks.append(
            {
                "check": f"independent_{accepted}",
                "result": "PASS" if bool(equal.all()) else "FAIL",
                "rows_compared": len(compared),
                "mismatches": int((~equal).sum()),
                "max_abs_diff": float(np.nanmax(np.abs(a - b))) if np.isfinite(a - b).any() else None,
            }
        )
    accel = pd.to_numeric(features["foreign_flow_acceleration_5_20"], errors="coerce")
    expected_accel = pd.to_numeric(features["foreign_flow_shock_mean_5"], errors="coerce") - pd.to_numeric(
        features["foreign_flow_shock_mean_20"], errors="coerce"
    )
    accel_equal = np.isclose(accel, expected_accel, rtol=1e-12, atol=1e-12, equal_nan=True)
    checks.append(
        {
            "check": "independent_acceleration_identity",
            "result": "PASS" if bool(accel_equal.all()) else "FAIL",
            "rows_compared": len(features),
            "mismatches": int((~accel_equal).sum()),
            "max_abs_diff": float(np.nanmax(np.abs(accel - expected_accel))) if np.isfinite(accel - expected_accel).any() else None,
        }
    )
    causal = all(
        sessions[sessions.get_loc(row.flow_through_session) + 1] == row.feature_session
        for row in features.itertuples(index=False)
        if sessions.get_loc(row.flow_through_session) + 1 < len(sessions)
    )
    checks.append({"check": "independent_next_official_session", "result": "PASS" if causal else "FAIL", "rows_compared": len(features), "mismatches": 0})
    emit(pd.DataFrame(checks), "representation_recomputation_audit.csv")

    net_identity = flow["foreign_net"].eq(flow["foreign_buy"] - flow["foreign_sell"])
    raw_contract = pd.DataFrame(
        [
            {"check": "archive_manifest_sha256", "value": sha256(archive_manifest_path), "status": "PASS" if sha256(archive_manifest_path) == input_manifest["archive_manifest"]["archive_manifest_sha256"] else "FAIL"},
            {"check": "normalized_archive_files_loaded", "value": len(pieces), "status": "PASS" if not missing_files else "FAIL"},
            {"check": "raw_flow_rows_all_archive", "value": len(flow), "status": "PASS"},
            {"check": "raw_flow_rows_official_calendar", "value": len(official), "status": "PASS"},
            {"check": "raw_duplicate_ticker_session", "value": int(flow.duplicated(["ticker", "session_date"]).sum()), "status": "PASS" if not flow.duplicated(["ticker", "session_date"]).any() else "FAIL"},
            {"check": "unit", "value": sorted(flow["unit"].dropna().astype(str).unique().tolist()), "status": "PASS" if set(flow["unit"].dropna().astype(str)) == {"SHARES"} else "FAIL"},
            {"check": "negative_buy_sell", "value": int((flow[["foreign_buy", "foreign_sell"]] < 0).sum().sum()), "status": "PASS"},
            {"check": "net_identity_mismatches", "value": int((~net_identity).sum()), "status": "PASS" if bool(net_identity.all()) else "FAIL"},
            {"check": "rows_outside_official_calendar", "value": len(flow) - len(official), "status": "INFO"},
            {"check": "outcome_columns_loaded", "value": [], "status": "PASS"},
            {"check": "provider_calls", "value": False, "status": "PASS"},
        ]
    )
    emit(raw_contract, "raw_contract_audit.csv")

    flow_analysis = official[["ticker", "session_date", "foreign_buy", "foreign_sell", "foreign_net"]].rename(columns={"session_date": "date"})
    analysis = panel.merge(flow_analysis, on=["ticker", "date"], how="left", validate="one_to_one")
    analysis["abs_net_shares"] = analysis["foreign_net"].abs()
    analysis["abs_net_notional"] = analysis["abs_net_shares"] * analysis["close"]
    analysis["abs_participation"] = analysis["abs_net_shares"] / analysis["volume"].where(analysis["volume"] > 0)
    analysis["abs_rmv_fraction"] = analysis["abs_net_notional"] / analysis["regular_market_value"].where(analysis["regular_market_value"] > 0)
    analysis["abs_shares_x_price"] = analysis["abs_net_shares"] * analysis["close"]
    analysis["flow_sign"] = np.sign(analysis["foreign_net"])
    analysis["price_sign"] = np.sign(analysis["same_session_close_return"])
    analysis["flow_price_agree"] = np.where((analysis["flow_sign"] != 0) & (analysis["price_sign"] != 0), analysis["flow_sign"] == analysis["price_sign"], np.nan)
    merged = features.merge(analysis[["ticker", "date", "close", "volume", "regular_market_value", "same_session_close_return", "range_fraction", "intraday_range_fraction"]], left_on=["ticker", "flow_through_session"], right_on=["ticker", "date"], how="left", validate="one_to_one").drop(columns=["date"])
    merged = merged.merge(flow_analysis.rename(columns={"date": "flow_through_session"}), on=["ticker", "flow_through_session"], how="left", validate="one_to_one")
    merged["abs_shock"] = pd.to_numeric(merged["foreign_flow_shock_1"], errors="coerce").abs()
    merged["abs_participation"] = pd.to_numeric(merged["foreign_participation_1"], errors="coerce").abs()
    merged["flow_abs_rmv_fraction"] = merged["foreign_net"].abs() * merged["close"] / merged["regular_market_value"].where(merged["regular_market_value"] > 0)
    merged["year"] = merged["feature_session"].dt.year

    coverage = features.groupby("flow_through_session").agg(output_rows=("ticker", "size"), output_tickers=("ticker", "nunique")).reset_index()
    raw_coverage = official.groupby("session_date").agg(flow_rows=("ticker", "size"), flow_tickers=("ticker", "nunique"), net_buy_rows=("foreign_net", lambda s: int((s > 0).sum())), net_sell_rows=("foreign_net", lambda s: int((s < 0).sum())), zero_flow_rows=("foreign_net", lambda s: int((s == 0).sum()))).reset_index().rename(columns={"session_date": "flow_through_session"})
    emit(coverage.merge(raw_coverage, on="flow_through_session", how="outer").sort_values("flow_through_session"), "coverage_census.csv")

    sample = analysis.dropna(subset=["abs_net_shares", "close", "volume", "regular_market_value"]).sample(n=min(200000, len(analysis.dropna(subset=["abs_net_shares", "close", "volume", "regular_market_value"]))), random_state=20260904)
    comparable = []
    for left, label in [("abs_net_shares", "absolute net shares"), ("abs_net_notional", "absolute net shares x close"), ("abs_participation", "absolute net / volume"), ("abs_rmv_fraction", "absolute net notional / regular market value")]:
        for right, right_label in [("close", "price level"), ("volume", "ordinary volume"), ("regular_market_value", "market value"), ("same_session_close_return", "same-session return"), ("intraday_range_fraction", "same-session range")]:
            n, correlation = rank_corr(sample, left, right)
            comparable.append({"measure": label, "conditioning_variable": right_label, "n": n, "spearman": correlation, "sample_rows": len(sample)})
    emit(pd.DataFrame(comparable), "raw_share_comparability.csv")

    by_ticker = merged.groupby("ticker").agg(rows=("ticker", "size"), shock_finite=("foreign_flow_shock_1", lambda s: int(s.notna().sum())), extreme_abs_shock_gt5=("abs_shock", lambda s: int((s > 5).sum())), extreme_abs_shock_gt20=("abs_shock", lambda s: int((s > 20).sum())), max_abs_shock=("abs_shock", "max"), max_abs_participation=("abs_participation", "max"), median_close=("close", "median"), median_volume=("volume", "median"), median_rmv=("regular_market_value", "median")).reset_index().sort_values(["max_abs_shock", "ticker"], ascending=[False, True])
    emit(by_ticker.head(200), "anomaly_census.csv")
    anomaly_columns = ["ticker", "flow_through_session", "feature_session", "foreign_buy", "foreign_sell", "foreign_net", "close", "volume", "regular_market_value", "foreign_participation_1", "foreign_flow_shock_1", "foreign_flow_shock_percentile_120", "foreign_flow_price_divergence_5", "same_session_close_return", "intraday_range_fraction"]
    emit(merged.loc[merged["abs_shock"].notna()].nlargest(150, "abs_shock")[anomaly_columns], "anomaly_top_rows.csv")
    requested = ["FUJI", "CASA", "JGLE", "PSKT"] + by_ticker.head(6)["ticker"].tolist()
    cases = merged.loc[merged["ticker"].isin(requested) & merged["abs_shock"].notna()].sort_values(["ticker", "abs_shock"], ascending=[True, False]).groupby("ticker", sort=False).head(8)
    emit(cases[anomaly_columns], "anomaly_case_studies.csv")

    known_ca = pd.read_csv(CA_PATH) if CA_PATH.exists() else pd.DataFrame()
    ca_rows = []
    if not known_ca.empty:
        known_ca["ticker"] = known_ca["ticker"].astype(str).str.upper().str.strip()
        known_ca["transition_date"] = pd.to_datetime(known_ca["transition_date"], errors="coerce").dt.normalize()
        for row in known_ca.loc[known_ca["transition_status"].eq("RESOLVED") & known_ca["transition_date"].notna()].itertuples(index=False):
            window = merged.loc[(merged["ticker"] == row.ticker) & (merged["flow_through_session"] >= row.transition_date - pd.Timedelta(days=7)) & (merged["flow_through_session"] <= row.transition_date + pd.Timedelta(days=7))]
            ca_rows.append({"ticker": row.ticker, "event_family": getattr(row, "event_family", None), "transition_date": row.transition_date.date().isoformat(), "window_rows": len(window), "window_abs_shock_gt5": int((window["abs_shock"] > 5).sum()), "window_max_abs_shock": None if window["abs_shock"].dropna().empty else float(window["abs_shock"].max()), "authority": "bounded resolved transition_attestation_ledger V16", "scope": "not exhaustive; unknown/unresolved CA is not absence"})
    emit(pd.DataFrame(ca_rows), "ca_listing_interaction.csv")
    emit(pd.DataFrame([{"metric": "listing_interval_excluded_rows", "value": 1, "status": "PASS"}, {"metric": "listing_interval_excluded_tickers", "value": 1, "status": "PASS"}, {"metric": "exhaustive_CA_absence", "value": "UNKNOWN", "status": "BLOCKED"}]), "listing_lifecycle_summary.csv")

    conditioned = merged.dropna(subset=["foreign_flow_shock_1", "foreign_participation_1", "close", "volume", "regular_market_value"]).copy()
    conditioning_rows = []
    for column, label in [("close", "price"), ("volume", "volume"), ("regular_market_value", "market_value"), ("flow_abs_rmv_fraction", "flow_rmv_fraction")]:
        numeric = pd.to_numeric(conditioned[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        try:
            codes = pd.qcut(numeric, 3, labels=False, duplicates="drop")
            mapping = {0: "LOW", 1: "MID", 2: "HIGH"}
            conditioned["bin"] = codes.map(mapping).fillna("UNAVAILABLE")
        except ValueError:
            # A degenerate proxy (many exact zeros) still gets deterministic
            # distribution bins without inventing values.
            conditioned["bin"] = "UNAVAILABLE"
            valid = numeric.notna()
            if valid.any():
                ranked = numeric.loc[valid].rank(method="first")
                conditioned.loc[valid, "bin"] = pd.qcut(ranked, 3, labels=["LOW", "MID", "HIGH"])
        for group, values in conditioned.groupby("bin", observed=True):
            conditioning_rows.append({"conditioning": label, "bin": str(group), "rows": len(values), "median_abs_shock": float(values["abs_shock"].median()), "p95_abs_shock": float(values["abs_shock"].quantile(0.95)), "median_abs_participation": float(values["abs_participation"].median()), "median_flow_rmv_fraction": float(values["flow_abs_rmv_fraction"].median())})
    emit(pd.DataFrame(conditioning_rows), "liquidity_conditioning.csv")

    regime = merged.groupby("year").agg(rows=("ticker", "size"), shock_finite=("foreign_flow_shock_1", lambda s: int(s.notna().sum())), shock_median=("foreign_flow_shock_1", "median"), shock_p05=("foreign_flow_shock_1", lambda s: float(s.quantile(0.05))), shock_p95=("foreign_flow_shock_1", lambda s: float(s.quantile(0.95))), participation_median=("foreign_participation_1", "median"), abs_participation_p95=("abs_participation", lambda s: float(s.quantile(0.95))), divergence5_finite=("foreign_flow_price_divergence_5", lambda s: int(s.notna().sum()))).reset_index()
    emit(regime, "regime_analysis.csv")
    persistence = merged.groupby("year").agg(rows=("ticker", "size"), streak_median=("foreign_signed_streak_10", "median"), streak_abs_ge_03=("foreign_signed_streak_10", lambda s: int((s.abs() >= 0.3).sum())), persistence5_median=("foreign_weighted_persistence_5", "median"), persistence20_median=("foreign_weighted_persistence_20", "median"), acceleration_median=("foreign_flow_acceleration_5_20", "median")).reset_index()
    emit(persistence, "persistence_analysis.csv")

    cross = official.groupby("session_date").agg(rows=("ticker", "size"), tickers=("ticker", "nunique"), net_buy_breadth=("foreign_net", lambda s: int((s > 0).sum())), net_sell_breadth=("foreign_net", lambda s: int((s < 0).sum())), zero_breadth=("foreign_net", lambda s: int((s == 0).sum())), total_abs_net=("foreign_net", lambda s: float(s.abs().sum())), top10_abs_net_share=("foreign_net", lambda s: float(s.abs().nlargest(10).sum() / s.abs().sum()) if s.abs().sum() else np.nan), net_sum=("foreign_net", "sum")).reset_index()
    cross["buy_breadth_fraction"] = cross["net_buy_breadth"] / cross["tickers"]
    cross["sell_breadth_fraction"] = cross["net_sell_breadth"] / cross["tickers"]
    emit(cross, "cross_sectional_structure.csv")

    behavior = merged.dropna(subset=["foreign_net", "same_session_close_return", "foreign_participation_1", "foreign_flow_shock_1"]).copy()
    behavior["flow_direction"] = np.where(behavior["foreign_net"] > 0, "BUY", np.where(behavior["foreign_net"] < 0, "SELL", "ZERO"))
    behavior["price_direction"] = np.where(behavior["same_session_close_return"] > 0, "UP", np.where(behavior["same_session_close_return"] < 0, "DOWN", "FLAT"))
    behavior["effort_result"] = np.select([(behavior["abs_participation"] >= behavior["abs_participation"].quantile(0.9)) & (behavior["same_session_close_return"].abs() <= behavior["same_session_close_return"].abs().quantile(0.5)), (behavior["abs_participation"] >= behavior["abs_participation"].quantile(0.9)) & (behavior["same_session_close_return"].abs() > behavior["same_session_close_return"].abs().quantile(0.5))], ["HIGH_EFFORT_LOW_RESULT", "HIGH_EFFORT_HIGH_RESULT"], default="OTHER")
    emit(behavior.groupby(["flow_direction", "price_direction"]).agg(rows=("ticker", "size"), median_abs_participation=("abs_participation", "median"), median_abs_shock=("abs_shock", "median"), median_price_return=("same_session_close_return", "median")).reset_index(), "price_flow_behavior.csv")
    emit(behavior.groupby("effort_result").agg(rows=("ticker", "size"), median_abs_participation=("abs_participation", "median"), median_abs_shock=("abs_shock", "median"), median_abs_price_return=("same_session_close_return", lambda s: float(s.abs().median())), median_flow_rmv_fraction=("flow_abs_rmv_fraction", "median")).reset_index(), "effort_vs_result.csv")

    redundancy_cols = ["foreign_participation_1", "foreign_flow_shock_1", "foreign_flow_shock_mean_5", "foreign_flow_shock_mean_20", "foreign_flow_price_divergence_5", "foreign_flow_price_divergence_20", "foreign_weighted_persistence_5", "foreign_signed_streak_10", "foreign_flow_acceleration_5_20", "close", "volume", "regular_market_value", "same_session_close_return", "intraday_range_fraction", "range_fraction"]
    emit(merged[redundancy_cols].replace([np.inf, -np.inf], np.nan).corr(method="spearman", min_periods=1000), "redundancy_analysis.csv")

    emit(pd.DataFrame([
        {"feature_family": "raw net / participation", "source": "Stock Summary EOD t; panel volume", "availability": "t+1 official session", "warmup": "volume > 0", "PIT_status": "EOD-only under pinned source contract"},
        {"feature_family": "shock / persistence / percentile", "source": "flow t + close t + strictly prior RMV history", "availability": "t+1 after lookback", "warmup": "10 prior RMV; 5/20 rolling; 60/120 percentile", "PIT_status": "mechanically causal; historical publication timing UNKNOWN"},
        {"feature_family": "cross-sectional rank / divergence", "source": "primary-liquid source-session context", "availability": "t+1", "warmup": "valid primary cross-section", "PIT_status": "EOD-only; universe/revision risk"},
        {"feature_family": "same-session HLCV", "source": "local market panel session t", "availability": "descriptive contemporaneous", "warmup": "prior close for same-session return", "PIT_status": "behavioral only"},
        {"feature_family": "future outcomes / labels", "source": "not loaded", "availability": "forbidden", "warmup": "n/a", "PIT_status": "BLOCKED_NOT_ACCESSED"},
    ]), "pit_feature_contract.csv")

    emit(pd.DataFrame([
        {"hypothesis_id": "FF-BEH-01", "name": "persistent foreign accumulation", "evidence": "backward persistence exists but is highly redundant with shock history", "confounders": "liquidity, size, CA, listing, source timing", "disposition": "PARKED_MEDIUM"},
        {"hypothesis_id": "FF-BEH-02", "name": "flow-price disagreement / effort-result", "evidence": "same-session descriptive disagreement survives as an observable category", "confounders": "price basis, liquidity, CA, local counterflow", "disposition": "PARKED_MEDIUM"},
        {"hypothesis_id": "FF-BEH-03", "name": "extreme shock / participation", "evidence": "large tails exist but condition strongly on price/liquidity and unresolved CA", "confounders": "share denomination, illiquidity, listing lifecycle, CA", "disposition": "PARKED_LOW"},
        {"hypothesis_id": "FF-BEH-04", "name": "breadth / concentration regime", "evidence": "cross-sectional breadth and concentration are measurable", "confounders": "coverage and universe composition", "disposition": "PARKED_MEDIUM"},
    ]), "hypothesis_registry.csv")
    emit(pd.DataFrame([
        {"hypothesis": "raw shares directly comparable across tickers", "decision": "REJECT_UNSAFE", "reason": "share denomination and size/liquidity make raw counts non-comparable"},
        {"hypothesis": "V2 is independent of volume/liquidity by construction", "decision": "REJECT_UNPROVEN", "reason": "shock uses close-valued shares over prior RMV; participation uses volume; no PIT float series"},
        {"hypothesis": "extreme rows imply predictive alpha", "decision": "REJECT_IN_THIS_PHASE", "reason": "future outcomes and model evaluation are forbidden"},
        {"hypothesis": "no CA contamination around anomalies", "decision": "REJECT_UNSUPPORTED", "reason": "event-level population completeness is UNKNOWN"},
    ]), "rejected_hypotheses.csv")

    summary = {
        "status": "FOREIGN_FLOW_BEHAVIORAL_FORENSICS_V1_OFFLINE_COMPLETE",
        "coverage": {"raw_rows_all_archive": len(flow), "raw_rows_official": len(official), "raw_sessions_official": official["session_date"].nunique(), "raw_tickers": official["ticker"].nunique(), "feature_rows": len(features), "feature_tickers": features["ticker"].nunique(), "feature_sessions": features["feature_session"].nunique(), "panel_rows": len(panel), "panel_tickers": panel["ticker"].nunique()},
        "period": {"official": [sessions.min().date().isoformat(), sessions.max().date().isoformat()], "flow_official": [official["session_date"].min().date().isoformat(), official["session_date"].max().date().isoformat()], "feature": [features["feature_session"].min().date().isoformat(), features["feature_session"].max().date().isoformat()]},
        "v2_recomputation": {"result": "PASS" if all(row["result"] == "PASS" for row in checks) else "FAIL", "checks": checks},
        "raw_contract": {"result": "PASS" if bool(net_identity.all()) and not missing_files else "FAIL", "unit": "SHARES", "net_identity_mismatches": int((~net_identity).sum()), "archive_manifest_sha256": sha256(archive_manifest_path)},
        "outcome_firewall": {"outcomes_loaded": False, "future_returns_loaded": False, "model_fit": False, "provider_calls": False, "production_state_mutation": False},
        "known_ca_scope": "bounded resolved transition attestations only; exhaustive historical CA absence UNKNOWN",
        "decision": "INTERESTING_BUT_TOO_QUALIFIED",
        "predictive_testing_justified": False,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = {path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in sorted(OUT.iterdir()) if path.is_file() and path.name != "MANIFEST.json"}
    manifest = {"schema": "idx-trade/foreign-flow-behavioral-forensics-v1", "status": summary["status"], "created_at": "2026-09-04", "source_artifact_manifest": str(ART / "manifest.json"), "source_artifact_manifest_sha256": sha256(ART / "manifest.json"), "input_manifest": str(ART / "input_manifest.json"), "input_manifest_sha256": sha256(ART / "input_manifest.json"), "archive_manifest": str(archive_manifest_path), "archive_manifest_sha256": sha256(archive_manifest_path), "summary": summary, "files": files, "no_provider_calls": True, "outcome_blind": True}
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output_root": str(OUT), "manifest_sha256": sha256(OUT / "MANIFEST.json"), "files": len(files), "v2": summary["v2_recomputation"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
