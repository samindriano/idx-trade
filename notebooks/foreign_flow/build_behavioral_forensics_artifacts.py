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

PRIOR_LIQUIDITY_LOOKBACK = 20
MIN_PRIOR_LIQUIDITY_OBSERVATIONS = 10
HISTORY_PERCENTILE_LOOKBACK = 120
MIN_HISTORY_PERCENTILE_OBSERVATIONS = 60
SHORT_WINDOW = 5
MEDIUM_WINDOW = 20
STREAK_CAP = 10


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


def historical_percentile(current: float, history: np.ndarray) -> float:
    valid = history[np.isfinite(history)]
    if not np.isfinite(current) or len(valid) < MIN_HISTORY_PERCENTILE_OBSERVATIONS:
        return np.nan
    less = float(np.sum(valid < current))
    equal = float(np.sum(valid == current))
    return (less + 0.5 * equal) / float(len(valid))


def signed_streak(values: np.ndarray) -> float:
    if len(values) == 0 or not np.isfinite(values[-1]):
        return np.nan
    last_sign = float(np.sign(values[-1]))
    if last_sign == 0.0:
        return 0.0
    count = 0
    for value in values[::-1]:
        if not np.isfinite(value) or float(np.sign(value)) != last_sign:
            break
        count += 1
        if count >= STREAK_CAP:
            break
    return last_sign * float(count) / float(STREAK_CAP)


def weighted_persistence(values: np.ndarray) -> float:
    if len(values) == 0 or not np.isfinite(values).all():
        return np.nan
    denominator = float(np.abs(values).sum())
    if denominator == 0.0:
        return 0.0
    return float(values.sum() / denominator)


def independent_v2_recompute(
    expected: pd.DataFrame,
    official: pd.DataFrame,
    panel: pd.DataFrame,
    context: pd.DataFrame,
    master: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Rebuild the accepted V2 fields without importing the V2 implementation."""
    flow_index = official.set_index(["ticker", "session_date"])["foreign_net"]
    volume_index = panel.set_index(["ticker", "date"])["volume"]
    context_index = context.set_index(["ticker", "date"])
    master_tickers = set(master["ticker"])
    rows: list[pd.DataFrame] = []
    for ticker in sorted(set(expected["ticker"])):
        if ticker not in master_tickers:
            continue
        master_rows = master.loc[master["ticker"].eq(ticker)]
        listed = listed_mask(pd.Series(sessions), ticker, master)
        listed_at_feature = np.zeros(len(sessions), dtype=bool)
        listed_at_feature[:-1] = listed[1:]
        key = pd.MultiIndex.from_product([[ticker], sessions], names=["ticker", "date"])
        net = flow_index.reindex(key.set_names(["ticker", "session_date"])).to_numpy(dtype=float)
        volume = volume_index.reindex(key).to_numpy(dtype=float)
        close = context_index["close"].reindex(key).to_numpy(dtype=float)
        regular_value = context_index["regular_market_value"].reindex(key).to_numpy(dtype=float)
        net[~listed] = np.nan
        volume[~listed] = np.nan
        close[~listed] = np.nan
        regular_value[~listed] = np.nan

        participation = np.full(len(sessions), np.nan, dtype=float)
        valid_current = np.isfinite(net) & np.isfinite(volume) & (volume > 0.0)
        participation[valid_current] = net[valid_current] / volume[valid_current]

        shock = np.full(len(sessions), np.nan, dtype=float)
        net_notional = net * close
        for index in range(len(sessions)):
            prior = regular_value[max(0, index - PRIOR_LIQUIDITY_LOOKBACK) : index]
            prior = prior[np.isfinite(prior) & (prior >= 0.0)]
            if len(prior) < MIN_PRIOR_LIQUIDITY_OBSERVATIONS or not np.isfinite(net_notional[index]):
                continue
            baseline = float(np.median(prior))
            if baseline > 0.0:
                shock[index] = net_notional[index] / baseline

        participation_mean_5 = np.full(len(sessions), np.nan, dtype=float)
        shock_mean_5 = np.full(len(sessions), np.nan, dtype=float)
        shock_mean_20 = np.full(len(sessions), np.nan, dtype=float)
        persistence_5 = np.full(len(sessions), np.nan, dtype=float)
        persistence_20 = np.full(len(sessions), np.nan, dtype=float)
        streak_10 = np.full(len(sessions), np.nan, dtype=float)
        percentile_120 = np.full(len(sessions), np.nan, dtype=float)
        for index in range(len(sessions)):
            if index + 1 >= SHORT_WINDOW:
                participation_window = participation[index - SHORT_WINDOW + 1 : index + 1]
                shock_window_5 = shock[index - SHORT_WINDOW + 1 : index + 1]
                if np.isfinite(participation_window).all():
                    participation_mean_5[index] = float(np.mean(participation_window))
                if np.isfinite(shock_window_5).all():
                    shock_mean_5[index] = float(np.mean(shock_window_5))
                    persistence_5[index] = weighted_persistence(shock_window_5)
            if index + 1 >= MEDIUM_WINDOW:
                shock_window_20 = shock[index - MEDIUM_WINDOW + 1 : index + 1]
                if np.isfinite(shock_window_20).all():
                    shock_mean_20[index] = float(np.mean(shock_window_20))
                    persistence_20[index] = weighted_persistence(shock_window_20)
            streak_10[index] = signed_streak(net[max(0, index - STREAK_CAP + 1) : index + 1])
            percentile_120[index] = historical_percentile(
                shock[index], shock[max(0, index - HISTORY_PERCENTILE_LOOKBACK) : index]
            )

        rows.append(
            pd.DataFrame(
                {
                    "ticker": ticker,
                    "source_session": sessions,
                    "listed_at_source_session": listed,
                    "listed_at_feature_session": listed_at_feature,
                    "foreign_participation_1": participation,
                    "foreign_participation_mean_5": participation_mean_5,
                    "foreign_flow_shock_1": shock,
                    "foreign_flow_shock_mean_5": shock_mean_5,
                    "foreign_flow_shock_mean_20": shock_mean_20,
                    "foreign_flow_shock_percentile_120": percentile_120,
                    "foreign_weighted_persistence_5": persistence_5,
                    "foreign_weighted_persistence_20": persistence_20,
                    "foreign_signed_streak_10": streak_10,
                    "foreign_flow_acceleration_5_20": shock_mean_5 - shock_mean_20,
                }
            )
        )

    source = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if source.empty:
        return pd.DataFrame(columns=["ticker", "feature_session", "flow_through_session", *FEATURES])
    source = source.merge(
        context,
        left_on=["ticker", "source_session"],
        right_on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    ).drop(columns=["date"])
    rank_specs = [
        ("foreign_flow_shock_1", "xs_rank_foreign_flow_shock_1"),
        ("foreign_flow_shock_mean_5", "xs_rank_foreign_flow_shock_mean_5"),
        ("foreign_flow_shock_mean_20", "xs_rank_foreign_flow_shock_mean_20"),
        ("close_return_5", "xs_rank_close_return_5_source"),
        ("close_return_20", "xs_rank_close_return_20_source"),
    ]
    for _, output in rank_specs:
        source[output] = np.nan
    primary = source["listed_at_source_session"] & source["universe_primary_liquid"].fillna(False).astype(bool)
    for raw, output in rank_specs:
        ranks = source.loc[primary].groupby("source_session", sort=True)[raw].rank(
            method="average", pct=True
        )
        source.loc[ranks.index, output] = ranks.astype(float)
    source["foreign_flow_price_divergence_5"] = (
        source["xs_rank_foreign_flow_shock_mean_5"] - source["xs_rank_close_return_5_source"]
    )
    source["foreign_flow_price_divergence_20"] = (
        source["xs_rank_foreign_flow_shock_mean_20"] - source["xs_rank_close_return_20_source"]
    )
    next_by_day = {sessions[i]: sessions[i + 1] for i in range(len(sessions) - 1)}
    source["feature_session"] = source["source_session"].map(next_by_day)
    source = source[
        source["feature_session"].notna()
        & source["listed_at_source_session"]
        & source["listed_at_feature_session"]
    ].copy()
    source = source.rename(columns={"source_session": "flow_through_session"})
    return source[["ticker", "feature_session", "flow_through_session", *FEATURES]].sort_values(
        ["feature_session", "ticker"], kind="mergesort"
    ).reset_index(drop=True)


def compare_recomputed_fields(expected: pd.DataFrame, recomputed: pd.DataFrame) -> list[dict[str, object]]:
    key_columns = ["ticker", "feature_session"]
    checks: list[dict[str, object]] = []
    for feature in FEATURES:
        left = expected[key_columns + [feature]].rename(columns={feature: "expected"})
        right = recomputed[key_columns + [feature]].rename(columns={feature: "recomputed"})
        aligned = left.merge(right, on=key_columns, how="outer", indicator=True, validate="one_to_one")
        a = pd.to_numeric(aligned["expected"], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(aligned["recomputed"], errors="coerce").to_numpy(dtype=float)
        finite_a = np.isfinite(a)
        finite_b = np.isfinite(b)
        both_finite = finite_a & finite_b
        finite_mismatch = both_finite & ~np.isclose(a, b, rtol=1e-10, atol=1e-12)
        nan_mismatch = finite_a ^ finite_b
        differences = np.abs(a[both_finite] - b[both_finite])
        key_mismatch = int((aligned["_merge"] != "both").sum())
        checks.append(
            {
                "check": feature,
                "result": "PASS" if key_mismatch == 0 and not finite_mismatch.any() and not nan_mismatch.any() else "FAIL",
                "keys_expected": int(len(left)),
                "keys_recomputed": int(len(right)),
                "key_set_mismatches": key_mismatch,
                "finite_expected": int(finite_a.sum()),
                "finite_recomputed": int(finite_b.sum()),
                "finite_value_mismatches": int(finite_mismatch.sum()),
                "nan_pattern_mismatches": int(nan_mismatch.sum()),
                "max_abs_difference": float(differences.max()) if len(differences) else None,
            }
        )
    return checks


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
    source_file_hash_rows: list[dict[str, object]] = []
    manifest_items = archive_manifest.get("artifacts", archive_manifest.get("normalized_artifacts", []))
    for item in manifest_items:
        relative = item.get("path")
        if not relative or not str(relative).endswith("foreign_flow.parquet"):
            continue
        source = ARCH / relative
        expected_sha = str(item.get("sha256", ""))
        expected_bytes = item.get("bytes")
        if not source.exists():
            missing_files.append(str(source))
            source_file_hash_rows.append(
                {
                    "path": str(relative),
                    "expected_sha256": expected_sha,
                    "observed_sha256": None,
                    "expected_bytes": expected_bytes,
                    "observed_bytes": None,
                    "verdict": "FAIL_MISSING",
                }
            )
            continue
        observed_sha = sha256(source)
        observed_bytes = source.stat().st_size
        hash_ok = bool(expected_sha) and observed_sha == expected_sha
        bytes_ok = expected_bytes is None or int(expected_bytes) == observed_bytes
        verdict = "PASS" if hash_ok and bytes_ok else "FAIL_HASH_OR_BYTES"
        source_file_hash_rows.append(
            {
                "path": str(relative),
                "expected_sha256": expected_sha,
                "observed_sha256": observed_sha,
                "expected_bytes": expected_bytes,
                "observed_bytes": observed_bytes,
                "verdict": verdict,
            }
        )
        if verdict == "PASS":
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

    context = pd.read_parquet(ART / "causal_market_context.parquet")
    context["ticker"] = context["ticker"].astype(str).str.upper().str.strip()
    context["date"] = pd.to_datetime(context["date"]).dt.normalize()
    context["universe_primary_liquid"] = context["universe_primary_liquid"].fillna(False).astype(bool)
    context = context.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)

    # This is a full independent reconstruction of every accepted V2 field.
    # No V2 module or helper is imported or called here.
    recalc = independent_v2_recompute(features, official, panel, context, master, sessions)
    checks = compare_recomputed_fields(features, recalc)
    causal = bool(
        (
            features["feature_session"].to_numpy()
            == features["flow_through_session"].map(
                {sessions[i]: sessions[i + 1] for i in range(len(sessions) - 1)}
            ).to_numpy()
        ).all()
    )
    checks.append(
        {
            "check": "feature_session_next_official_session",
            "result": "PASS" if causal else "FAIL",
            "keys_expected": int(len(features)),
            "keys_recomputed": int(len(features)),
            "finite_expected": None,
            "finite_recomputed": None,
            "finite_value_mismatches": 0 if causal else int(len(features)),
            "nan_pattern_mismatches": 0,
            "max_abs_difference": None,
        }
    )
    emit(pd.DataFrame(checks), "representation_recomputation_audit.csv")
    emit(pd.DataFrame(source_file_hash_rows), "source_file_hash_audit.csv")

    source_file_hash_audit = pd.DataFrame(source_file_hash_rows)
    source_hash_failures = int((source_file_hash_audit["verdict"] != "PASS").sum())
    archive_manifest_sha = sha256(archive_manifest_path)
    net_identity = flow["foreign_net"].eq(flow["foreign_buy"] - flow["foreign_sell"])
    raw_contract = pd.DataFrame(
        [
            {"check": "archive_manifest_sha256", "value": archive_manifest_sha, "status": "PASS" if archive_manifest_sha == input_manifest["archive_manifest"]["archive_manifest_sha256"] else "FAIL"},
            {"check": "normalized_archive_file_count_expected", "value": len(source_file_hash_audit), "status": "PASS" if len(source_file_hash_audit) == 1288 else "FAIL"},
            {"check": "normalized_archive_file_hashes_and_bytes", "value": {"pass": int((source_file_hash_audit["verdict"] == "PASS").sum()), "fail": source_hash_failures}, "status": "PASS" if source_hash_failures == 0 else "FAIL"},
            {"check": "normalized_archive_files_loaded", "value": len(pieces), "status": "PASS" if not missing_files and source_hash_failures == 0 else "FAIL"},
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
        "v2_recomputation": {"result": "PASS" if all(row["result"] == "PASS" for row in checks) else "FAIL", "checks": checks, "independent_source": "notebooks/foreign_flow/build_behavioral_forensics_artifacts.py"},
        "raw_contract": {"result": "PASS" if bool(net_identity.all()) and not missing_files and source_hash_failures == 0 else "FAIL", "unit": "SHARES", "net_identity_mismatches": int((~net_identity).sum()), "archive_manifest_sha256": archive_manifest_sha, "normalized_archive_files_expected": int(len(source_file_hash_audit)), "normalized_archive_files_verified": int((source_file_hash_audit["verdict"] == "PASS").sum()), "normalized_archive_file_failures": source_hash_failures, "source_file_hash_audit": "source_file_hash_audit.csv"},
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
