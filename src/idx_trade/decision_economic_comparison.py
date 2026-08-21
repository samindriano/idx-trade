"""Economic target-outcome comparison for frozen Decision policies.

This module deliberately does *not* construct a historical executable NAV path.
Historical quantity/cash continuity across corporate actions remains a separate
execution-layer blocker.  Instead, it compares the economic quality of the
already-frozen policy target memberships using the canonical V4-X1 H5/H10
forward-return ledger, whose available states already require observable
Open(t+1), observable terminal Close, active market state, and resolved price
continuity.

The 600-session window has been inspected extensively during Decision research,
so every result from this module is development evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

EXPECTED_SOURCE_MANIFEST_SHA256 = (
    "6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205"
)
EXPECTED_SOURCE_SCORE_SHA256 = (
    "48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b"
)
EXPECTED_SOURCE_SCHEMA = "ranking_v4_x1_clean_historical_oos_replay_manifest_v1"
EXPECTED_SOURCE_STATUS = "V4_X1_CLEAN_HISTORICAL_OOS_REPLAY_COMPLETE_REVIEW_REQUIRED"
EXPECTED_SESSIONS = 600
TARGET_SEATS = 10
SEAT_WEIGHT = 1.0 / TARGET_SEATS
POLICY_ORDER = ("NAIVE_TOP10", "DECISION_V1", "DECISION_V2", "DECISION_V3")

# Existing frozen Execution V1 retail assumptions.  These are not tuned here.
REFERENCE_NAV_RP = 50_000_000.0
STAMP_DUTY_RP = 10_000.0
STAMP_DUTY_GROSS_TURNOVER_THRESHOLD_RP = 10_000_000.0
COST_SCENARIOS: dict[str, dict[str, float]] = {
    "ZERO": {"buy_fee_bps": 0.0, "sell_fee_bps": 0.0, "slippage_bps_per_side": 0.0},
    "FEES_ONLY": {"buy_fee_bps": 15.0, "sell_fee_bps": 25.0, "slippage_bps_per_side": 0.0},
    "PRIMARY": {"buy_fee_bps": 15.0, "sell_fee_bps": 25.0, "slippage_bps_per_side": 10.0},
    "HIGH_SLIPPAGE": {"buy_fee_bps": 15.0, "sell_fee_bps": 25.0, "slippage_bps_per_side": 25.0},
}


class DecisionEconomicComparisonError(RuntimeError):
    pass


@dataclass(frozen=True)
class HistoricalSource:
    root: Path
    manifest_path: Path
    score_path: Path
    target_path: Path
    manifest_sha256: str
    score_sha256: str
    target_sha256: str
    scores: pd.DataFrame
    targets: pd.DataFrame
    dates: tuple[pd.Timestamp, ...]


@dataclass(frozen=True)
class PolicyMembership:
    policy: str
    by_date: dict[pd.Timestamp, tuple[str, ...]]
    source_root: str
    source_manifest_sha256: str | None


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise DecisionEconomicComparisonError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise DecisionEconomicComparisonError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DecisionEconomicComparisonError(f"{label}_NOT_OBJECT:{path}")
    return value


def _normalize_ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _normalize_date(series: pd.Series, label: str) -> pd.Series:
    result = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if result.isna().any():
        raise DecisionEconomicComparisonError(f"{label}_INVALID_DATE")
    return result


def load_historical_source(root: str | Path) -> HistoricalSource:
    resolved = Path(root).expanduser().resolve()
    manifest_path = resolved / "MANIFEST.json"
    score_path = resolved / "clean_challenger_validation_scores.parquet"
    target_path = resolved / "clean_target_ledger.parquet"

    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise DecisionEconomicComparisonError(
            f"SOURCE_MANIFEST_SHA_MISMATCH:{manifest_sha}!={EXPECTED_SOURCE_MANIFEST_SHA256}"
        )
    manifest = _read_json(manifest_path, "SOURCE_MANIFEST")
    if manifest.get("schema_version") != EXPECTED_SOURCE_SCHEMA:
        raise DecisionEconomicComparisonError("SOURCE_MANIFEST_SCHEMA_CHANGED")
    if manifest.get("status") != EXPECTED_SOURCE_STATUS:
        raise DecisionEconomicComparisonError("SOURCE_MANIFEST_STATUS_CHANGED")

    output_hashes = manifest.get("output_hashes") or {}
    score_sha = sha256_file(score_path)
    target_sha = sha256_file(target_path)
    if score_sha != EXPECTED_SOURCE_SCORE_SHA256:
        raise DecisionEconomicComparisonError(
            f"SOURCE_SCORE_SHA_MISMATCH:{score_sha}!={EXPECTED_SOURCE_SCORE_SHA256}"
        )
    if str(output_hashes.get("scores_challenger") or "") != score_sha:
        raise DecisionEconomicComparisonError("SOURCE_SCORE_CHILD_HASH_MISMATCH")
    if str(output_hashes.get("target_ledger") or "") != target_sha:
        raise DecisionEconomicComparisonError("SOURCE_TARGET_CHILD_HASH_MISMATCH")

    scores = pd.read_parquet(score_path)
    score_required = {"ticker", "date", "alpha_consensus"}
    missing = score_required - set(scores.columns)
    if missing:
        raise DecisionEconomicComparisonError(f"SOURCE_SCORE_COLUMNS_MISSING:{sorted(missing)}")
    scores = scores.copy()
    scores["ticker"] = _normalize_ticker(scores["ticker"])
    scores["date"] = _normalize_date(scores["date"], "SOURCE_SCORE")
    if scores.duplicated(["ticker", "date"]).any():
        raise DecisionEconomicComparisonError("SOURCE_SCORE_DUPLICATE_IDENTITY")
    dates = tuple(pd.DatetimeIndex(scores["date"].unique()).sort_values())
    if len(dates) != EXPECTED_SESSIONS:
        raise DecisionEconomicComparisonError(
            f"SOURCE_SCORE_SESSION_COUNT_CHANGED:{len(dates)}!={EXPECTED_SESSIONS}"
        )

    targets = pd.read_parquet(target_path)
    target_required = {
        "ticker", "date", "target_state_h5", "r5", "target_state_h10", "r10",
        "h5_continuity_resolved", "h10_continuity_resolved",
    }
    missing = target_required - set(targets.columns)
    if missing:
        raise DecisionEconomicComparisonError(f"SOURCE_TARGET_COLUMNS_MISSING:{sorted(missing)}")
    targets = targets.copy()
    targets["ticker"] = _normalize_ticker(targets["ticker"])
    targets["date"] = _normalize_date(targets["date"], "SOURCE_TARGET")
    targets = targets.loc[targets["date"].isin(dates)].copy()
    if targets.duplicated(["ticker", "date"]).any():
        raise DecisionEconomicComparisonError("SOURCE_TARGET_DUPLICATE_IDENTITY")

    score_identity = set(zip(scores["date"], scores["ticker"], strict=False))
    target_identity = set(zip(targets["date"], targets["ticker"], strict=False))
    if not score_identity.issubset(target_identity):
        raise DecisionEconomicComparisonError("SOURCE_TARGET_MISSING_SCORED_IDENTITY")

    for horizon in (5, 10):
        state = f"target_state_h{horizon}"
        ret = f"r{horizon}"
        resolved_col = f"h{horizon}_continuity_resolved"
        available = targets[state].eq(f"TARGET_H{horizon}_AVAILABLE")
        if targets.loc[available, ret].isna().any():
            raise DecisionEconomicComparisonError(f"H{horizon}_AVAILABLE_RETURN_MISSING")
        if not targets.loc[available, resolved_col].astype(bool).all():
            raise DecisionEconomicComparisonError(f"H{horizon}_AVAILABLE_CONTINUITY_NOT_RESOLVED")
        invalid_available = ~np.isfinite(pd.to_numeric(targets.loc[available, ret], errors="coerce"))
        if invalid_available.any():
            raise DecisionEconomicComparisonError(f"H{horizon}_AVAILABLE_RETURN_NONFINITE")

    return HistoricalSource(
        root=resolved,
        manifest_path=manifest_path,
        score_path=score_path,
        target_path=target_path,
        manifest_sha256=manifest_sha,
        score_sha256=score_sha,
        target_sha256=target_sha,
        scores=scores,
        targets=targets,
        dates=dates,
    )


def _parse_pipe_tickers(value: object) -> tuple[str, ...]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ()
    items = tuple(x.strip().upper().replace(".JK", "") for x in str(value).split("|") if x.strip())
    if len(items) != len(set(items)):
        raise DecisionEconomicComparisonError("POLICY_TARGET_DUPLICATE_TICKER")
    if len(items) > TARGET_SEATS:
        raise DecisionEconomicComparisonError("POLICY_TARGET_OVER_CAPACITY")
    return items


def derive_naive_top10(source: HistoricalSource) -> PolicyMembership:
    by_date: dict[pd.Timestamp, tuple[str, ...]] = {}
    for date, block in source.scores.groupby("date", sort=True):
        ordered = block.sort_values(
            ["alpha_consensus", "ticker"],
            ascending=[False, True],
            kind="mergesort",
        )
        target = tuple(ordered.head(TARGET_SEATS)["ticker"].astype(str))
        if len(target) != TARGET_SEATS:
            raise DecisionEconomicComparisonError(f"NAIVE_TOP10_INCOMPLETE:{pd.Timestamp(date).date()}")
        by_date[pd.Timestamp(date)] = target
    return PolicyMembership(
        policy="NAIVE_TOP10",
        by_date=by_date,
        source_root=str(source.root),
        source_manifest_sha256=source.manifest_sha256,
    )


def load_decision_v1(root: str | Path, expected_dates: Iterable[pd.Timestamp]) -> PolicyMembership:
    resolved = Path(root).expanduser().resolve()
    manifest_path = resolved / "MANIFEST.json"
    daily_path = resolved / "decision_v1_trajectory_daily.csv"
    manifest_sha = sha256_file(manifest_path)
    manifest = _read_json(manifest_path, "DECISION_V1_MANIFEST")
    if str(manifest.get("source_manifest_sha256") or "") != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise DecisionEconomicComparisonError("DECISION_V1_SOURCE_MANIFEST_MISMATCH")
    if str(manifest.get("source_score_sha256") or "") != EXPECTED_SOURCE_SCORE_SHA256:
        raise DecisionEconomicComparisonError("DECISION_V1_SOURCE_SCORE_MISMATCH")
    expected_daily_sha = str((manifest.get("output_hashes") or {}).get("daily") or "")
    actual_daily_sha = sha256_file(daily_path)
    if not expected_daily_sha or actual_daily_sha != expected_daily_sha:
        raise DecisionEconomicComparisonError("DECISION_V1_DAILY_HASH_MISMATCH")

    daily = pd.read_csv(daily_path)
    required = {"date", "target_tickers"}
    missing = required - set(daily.columns)
    if missing:
        raise DecisionEconomicComparisonError(f"DECISION_V1_DAILY_COLUMNS_MISSING:{sorted(missing)}")
    daily["date"] = _normalize_date(daily["date"], "DECISION_V1")
    if daily["date"].duplicated().any():
        raise DecisionEconomicComparisonError("DECISION_V1_DUPLICATE_DATE")
    by_date = {
        pd.Timestamp(row.date): _parse_pipe_tickers(row.target_tickers)
        for row in daily[["date", "target_tickers"]].itertuples(index=False)
    }
    _validate_policy_dates("DECISION_V1", by_date, expected_dates)
    if any(len(target) != TARGET_SEATS for target in by_date.values()):
        raise DecisionEconomicComparisonError("DECISION_V1_TARGET_SIZE_NOT_10")
    return PolicyMembership("DECISION_V1", by_date, str(resolved), manifest_sha)


def _validate_policy_dates(
    policy: str,
    by_date: dict[pd.Timestamp, tuple[str, ...]],
    expected_dates: Iterable[pd.Timestamp],
) -> None:
    expected = tuple(pd.Timestamp(x) for x in expected_dates)
    actual = tuple(sorted(by_date))
    if actual != expected:
        raise DecisionEconomicComparisonError(
            f"{policy}_DATE_IDENTITY_MISMATCH:actual={len(actual)}:expected={len(expected)}"
        )


def load_structural_membership(
    root: str | Path,
    policy: str,
    expected_dates: Iterable[pd.Timestamp],
) -> PolicyMembership:
    if policy not in {"DECISION_V2", "DECISION_V3"}:
        raise ValueError(policy)
    resolved = Path(root).expanduser().resolve()
    manifest_path = resolved / "MANIFEST.json"
    membership_path = resolved / "decision_membership_ledger.csv"
    sessions_path = resolved / "decision_session_ledger.csv"
    manifest_sha = sha256_file(manifest_path)
    manifest = _read_json(manifest_path, f"{policy}_MANIFEST")

    source = manifest.get("source") or {}
    if str(source.get("manifest_sha256") or "") != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise DecisionEconomicComparisonError(f"{policy}_SOURCE_MANIFEST_MISMATCH")
    if str(source.get("score_sha256") or "") != EXPECTED_SOURCE_SCORE_SHA256:
        raise DecisionEconomicComparisonError(f"{policy}_SOURCE_SCORE_MISMATCH")
    artifacts = manifest.get("artifacts") or {}
    for filename, path in (
        ("decision_membership_ledger.csv", membership_path),
        ("decision_session_ledger.csv", sessions_path),
    ):
        actual = sha256_file(path)
        expected = str(artifacts.get(filename) or "")
        if not expected or actual != expected:
            raise DecisionEconomicComparisonError(f"{policy}_{filename}_HASH_MISMATCH")

    sessions = pd.read_csv(sessions_path)
    membership = pd.read_csv(membership_path)
    if not {"date", "target_size"}.issubset(sessions.columns):
        raise DecisionEconomicComparisonError(f"{policy}_SESSION_COLUMNS_MISSING")
    if not {"date", "ticker"}.issubset(membership.columns):
        raise DecisionEconomicComparisonError(f"{policy}_MEMBERSHIP_COLUMNS_MISSING")
    sessions["date"] = _normalize_date(sessions["date"], f"{policy}_SESSIONS")
    membership["date"] = _normalize_date(membership["date"], f"{policy}_MEMBERSHIP")
    membership["ticker"] = _normalize_ticker(membership["ticker"])
    if sessions["date"].duplicated().any():
        raise DecisionEconomicComparisonError(f"{policy}_SESSION_DUPLICATE_DATE")
    if membership.duplicated(["date", "ticker"]).any():
        raise DecisionEconomicComparisonError(f"{policy}_MEMBERSHIP_DUPLICATE")

    grouped = {
        pd.Timestamp(date): tuple(sorted(block["ticker"].astype(str)))
        for date, block in membership.groupby("date", sort=True)
    }
    by_date: dict[pd.Timestamp, tuple[str, ...]] = {}
    for row in sessions[["date", "target_size"]].itertuples(index=False):
        date = pd.Timestamp(row.date)
        target = grouped.get(date, ())
        if len(target) != int(row.target_size):
            raise DecisionEconomicComparisonError(
                f"{policy}_TARGET_SIZE_LEDGER_MISMATCH:{date.date()}:{len(target)}!={int(row.target_size)}"
            )
        if len(target) > TARGET_SEATS:
            raise DecisionEconomicComparisonError(f"{policy}_TARGET_OVER_CAPACITY")
        by_date[date] = target
    _validate_policy_dates(policy, by_date, expected_dates)
    return PolicyMembership(policy, by_date, str(resolved), manifest_sha)


def validate_membership_against_source(
    source: HistoricalSource,
    memberships: Iterable[PolicyMembership],
) -> None:
    available = {
        date: set(block["ticker"].astype(str))
        for date, block in source.scores.groupby("date", sort=True)
    }
    for policy in memberships:
        for date in source.dates:
            missing = set(policy.by_date[date]) - available[date]
            if missing:
                raise DecisionEconomicComparisonError(
                    f"{policy.policy}_TARGET_OUTSIDE_SCORE_UNIVERSE:{date.date()}:{sorted(missing)}"
                )


def _transition_rows(policy: PolicyMembership, dates: tuple[pd.Timestamp, ...]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    previous: set[str] = set()
    for index, date in enumerate(dates):
        current = set(policy.by_date[date])
        buys = current - previous
        sells = previous - current
        row: dict[str, Any] = {
            "policy": policy.policy,
            "session_index": index,
            "date": date.date().isoformat(),
            "target_size": len(current),
            "buy_count": len(buys),
            "sell_count": len(sells),
            "replacement_count_proxy": max(len(buys), len(sells)),
        }
        for name, spec in COST_SCENARIOS.items():
            buy_bps = spec["buy_fee_bps"] + spec["slippage_bps_per_side"]
            sell_bps = spec["sell_fee_bps"] + spec["slippage_bps_per_side"]
            variable_fraction = SEAT_WEIGHT * (
                len(buys) * buy_bps + len(sells) * sell_bps
            ) / 10_000.0
            gross_turnover_rp = REFERENCE_NAV_RP * SEAT_WEIGHT * (len(buys) + len(sells))
            stamp_fraction = 0.0
            if name != "ZERO" and gross_turnover_rp > STAMP_DUTY_GROSS_TURNOVER_THRESHOLD_RP:
                stamp_fraction = STAMP_DUTY_RP / REFERENCE_NAV_RP
            row[f"cost_fraction_{name.lower()}"] = variable_fraction + stamp_fraction
            row[f"cost_bps_nav_{name.lower()}"] = 10_000.0 * (variable_fraction + stamp_fraction)
        rows.append(row)
        previous = current
    return pd.DataFrame(rows)


def build_turnover_table(
    memberships: Iterable[PolicyMembership], dates: tuple[pd.Timestamp, ...]
) -> pd.DataFrame:
    return pd.concat(
        [_transition_rows(policy, dates) for policy in memberships],
        ignore_index=True,
    )


def build_signal_outcomes(
    source: HistoricalSource,
    memberships: Iterable[PolicyMembership],
    turnover: pd.DataFrame,
) -> pd.DataFrame:
    target = source.targets.set_index(["date", "ticker"], drop=False)
    cost_lookup = turnover.set_index(["policy", "date"])
    rows: list[dict[str, Any]] = []

    for policy in memberships:
        for date in source.dates:
            tickers = policy.by_date[date]
            row: dict[str, Any] = {
                "policy": policy.policy,
                "date": date.date().isoformat(),
                "target_size": len(tickers),
                "cash_slots": TARGET_SEATS - len(tickers),
                "cash_weight": (TARGET_SEATS - len(tickers)) * SEAT_WEIGHT,
            }
            for scenario in COST_SCENARIOS:
                row[f"cost_fraction_{scenario.lower()}"] = float(
                    cost_lookup.loc[(policy.policy, date.date().isoformat()), f"cost_fraction_{scenario.lower()}"]
                )

            for horizon in (5, 10):
                state_col = f"target_state_h{horizon}"
                return_col = f"r{horizon}"
                available_state = f"TARGET_H{horizon}_AVAILABLE"
                returns: list[float] = []
                supported = 0
                states: list[str] = []
                for ticker in tickers:
                    key = (date, ticker)
                    if key not in target.index:
                        raise DecisionEconomicComparisonError(
                            f"TARGET_OUTCOME_IDENTITY_MISSING:{policy.policy}:{date.date()}:{ticker}"
                        )
                    item = target.loc[key]
                    if isinstance(item, pd.DataFrame):
                        raise DecisionEconomicComparisonError("TARGET_OUTCOME_DUPLICATE_LOOKUP")
                    state = str(item[state_col])
                    states.append(state)
                    value = float(item[return_col]) if pd.notna(item[return_col]) else np.nan
                    if state == available_state and np.isfinite(value):
                        supported += 1
                        returns.append(value)
                complete = supported == len(tickers)
                row[f"h{horizon}_supported_names"] = supported
                row[f"h{horizon}_complete_support"] = bool(complete)
                row[f"h{horizon}_unsupported_names"] = len(tickers) - supported
                row[f"h{horizon}_gross_basket_return"] = (
                    float(SEAT_WEIGHT * np.sum(returns)) if complete else np.nan
                )
                row[f"h{horizon}_support_states"] = "|".join(sorted(set(states)))
                if complete:
                    for scenario in COST_SCENARIOS:
                        gross = float(row[f"h{horizon}_gross_basket_return"])
                        cost = float(row[f"cost_fraction_{scenario.lower()}"])
                        row[f"h{horizon}_net_proxy_{scenario.lower()}"] = gross - cost
                else:
                    for scenario in COST_SCENARIOS:
                        row[f"h{horizon}_net_proxy_{scenario.lower()}"] = np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def _distribution(values: pd.Series) -> dict[str, float | int | None]:
    clean = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if clean.empty:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None, "std": None, "positive_share": None}
    return {
        "n": int(len(clean)),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "p25": float(clean.quantile(0.25)),
        "p75": float(clean.quantile(0.75)),
        "std": float(clean.std(ddof=1)) if len(clean) > 1 else 0.0,
        "positive_share": float(clean.gt(0.0).mean()),
    }


def summarize_comparison(
    source: HistoricalSource,
    memberships: tuple[PolicyMembership, ...],
    outcomes: pd.DataFrame,
    turnover: pd.DataFrame,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "decision_economic_target_outcome_comparison_v1",
        "status": "COMPLETE_DEVELOPMENT_ECONOMIC_TARGET_OUTCOME_COMPARISON_NOT_EXECUTABLE_PNL",
        "interpretation_boundary": {
            "window_role": "DECISION_DEVELOPMENT_SET_NOT_UNTOUCHED_VALIDATION",
            "historical_executable_nav_computed": False,
            "cagr_sharpe_drawdown_computed": False,
            "reason": "HISTORICAL_CA_QUANTITY_CASH_CONTINUITY_NOT_CERTIFIED_FOR_EXECUTABLE_NAV",
            "economic_measure": "CANONICAL_CA_SAFE_H5_H10_TARGET_RETURNS_PLUS_MEMBERSHIP_FRICTION_PROXY",
            "overlapping_horizon_observations": True,
            "net_proxy_is_not_portfolio_pnl": True,
        },
        "source": {
            "root": str(source.root),
            "manifest_sha256": source.manifest_sha256,
            "score_sha256": source.score_sha256,
            "target_sha256": source.target_sha256,
            "sessions": len(source.dates),
        },
        "policy_sources": {
            policy.policy: {
                "root": policy.source_root,
                "manifest_sha256": policy.source_manifest_sha256,
            }
            for policy in memberships
        },
        "cost_assumptions": {
            "reference_nav_rp": REFERENCE_NAV_RP,
            "target_seat_weight": SEAT_WEIGHT,
            "stamp_duty_rp": STAMP_DUTY_RP,
            "stamp_threshold_gross_turnover_rp": STAMP_DUTY_GROSS_TURNOVER_THRESHOLD_RP,
            "scenarios": COST_SCENARIOS,
            "note": "Membership-level friction proxy only; no lot rounding, capacity fills, weight drift, or CA quantity transforms.",
        },
        "horizons": {},
        "turnover_cost_burden": {},
    }

    for policy in memberships:
        block = turnover.loc[turnover["policy"].eq(policy.policy)].copy()
        transitions = block.iloc[1:].copy()
        result["turnover_cost_burden"][policy.policy] = {
            "total_buys_excluding_bootstrap": int(transitions["buy_count"].sum()),
            "total_sells_excluding_bootstrap": int(transitions["sell_count"].sum()),
            "mean_buys_per_transition": float(transitions["buy_count"].mean()),
            "mean_sells_per_transition": float(transitions["sell_count"].mean()),
            "mean_target_size": float(block["target_size"].mean()),
            "minimum_target_size": int(block["target_size"].min()),
            "scenarios": {
                scenario: {
                    "mean_cost_bps_nav_per_transition": float(transitions[f"cost_bps_nav_{scenario.lower()}"].mean()),
                    "simple_sum_cost_fraction_over_window": float(block[f"cost_fraction_{scenario.lower()}"].sum()),
                }
                for scenario in COST_SCENARIOS
            },
        }

    for horizon in (5, 10):
        support_col = f"h{horizon}_complete_support"
        pivot_support = outcomes.pivot(index="date", columns="policy", values=support_col)
        pivot_support = pivot_support.reindex(columns=POLICY_ORDER)
        common_dates = pivot_support.fillna(False).astype(bool).all(axis=1)
        common_date_index = set(pivot_support.index[common_dates])

        horizon_result: dict[str, Any] = {
            "common_support_dates": int(common_dates.sum()),
            "common_support_share_of_600": float(common_dates.mean()),
            "policy_own_complete_support": {},
            "common_support_policy_metrics": {},
            "common_support_excess_vs_naive": {},
            "common_support_rankings": {},
        }
        for policy in memberships:
            block = outcomes.loc[outcomes["policy"].eq(policy.policy)].copy()
            horizon_result["policy_own_complete_support"][policy.policy] = {
                "dates": int(block[support_col].astype(bool).sum()),
                "share": float(block[support_col].astype(bool).mean()),
            }
            common = block.loc[block["date"].isin(common_date_index)].copy()
            metrics: dict[str, Any] = {
                "gross": _distribution(common[f"h{horizon}_gross_basket_return"]),
                "mean_target_size": float(common["target_size"].mean()) if len(common) else None,
                "mean_cash_weight": float(common["cash_weight"].mean()) if len(common) else None,
                "net_proxy": {
                    scenario: _distribution(common[f"h{horizon}_net_proxy_{scenario.lower()}"])
                    for scenario in COST_SCENARIOS
                },
            }
            horizon_result["common_support_policy_metrics"][policy.policy] = metrics

        naive = outcomes.loc[
            outcomes["policy"].eq("NAIVE_TOP10") & outcomes["date"].isin(common_date_index),
            ["date", f"h{horizon}_gross_basket_return", *[
                f"h{horizon}_net_proxy_{scenario.lower()}" for scenario in COST_SCENARIOS
            ]],
        ].set_index("date")
        for policy in memberships:
            if policy.policy == "NAIVE_TOP10":
                continue
            block = outcomes.loc[
                outcomes["policy"].eq(policy.policy) & outcomes["date"].isin(common_date_index)
            ].set_index("date")
            gross_delta = block[f"h{horizon}_gross_basket_return"] - naive[f"h{horizon}_gross_basket_return"]
            item: dict[str, Any] = {
                "gross_delta": _distribution(gross_delta),
                "gross_win_share_vs_naive": float(gross_delta.gt(0.0).mean()) if len(gross_delta) else None,
                "net_proxy_delta": {},
            }
            for scenario in COST_SCENARIOS:
                col = f"h{horizon}_net_proxy_{scenario.lower()}"
                delta = block[col] - naive[col]
                item["net_proxy_delta"][scenario] = {
                    "distribution": _distribution(delta),
                    "win_share_vs_naive": float(delta.gt(0.0).mean()) if len(delta) else None,
                }
            horizon_result["common_support_excess_vs_naive"][policy.policy] = item

        gross_means = {
            policy: metrics["gross"]["mean"]
            for policy, metrics in horizon_result["common_support_policy_metrics"].items()
        }
        horizon_result["common_support_rankings"]["GROSS_MEAN"] = [
            name for name, value in sorted(
                gross_means.items(), key=lambda item: (-float(item[1]) if item[1] is not None else float("inf"), item[0])
            )
        ]
        for scenario in COST_SCENARIOS:
            means = {
                policy: metrics["net_proxy"][scenario]["mean"]
                for policy, metrics in horizon_result["common_support_policy_metrics"].items()
            }
            horizon_result["common_support_rankings"][f"NET_PROXY_{scenario}"] = [
                name for name, value in sorted(
                    means.items(), key=lambda item: (-float(item[1]) if item[1] is not None else float("inf"), item[0])
                )
            ]
        result["horizons"][f"H{horizon}"] = horizon_result

    return result


def run_comparison(
    historical_root: str | Path,
    decision_v1_root: str | Path,
    decision_v2_root: str | Path,
    decision_v3_root: str | Path,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    source = load_historical_source(historical_root)
    memberships = (
        derive_naive_top10(source),
        load_decision_v1(decision_v1_root, source.dates),
        load_structural_membership(decision_v2_root, "DECISION_V2", source.dates),
        load_structural_membership(decision_v3_root, "DECISION_V3", source.dates),
    )
    validate_membership_against_source(source, memberships)
    turnover = build_turnover_table(memberships, source.dates)
    outcomes = build_signal_outcomes(source, memberships, turnover)
    summary = summarize_comparison(source, memberships, outcomes, turnover)
    return summary, outcomes, turnover
