"""Support-bias check for the frozen Decision economic comparison.

Consumes only the already-produced comparison artifact. It never reads new
returns, reruns policies, or changes any Decision rule. The purpose is to explain
why all-policy common support is sparse in early 100-session blocks and whether
that sparsity is broad data/continuity coverage or policy-specific selection.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

EXPECTED_COMPARISON_MANIFEST_SHA256 = (
    "d33ec5ab0b6c4c7642c5faf42a7f5980f3d5e4d3d7668552d309aea0ed6e2622"
)
EXPECTED_SCHEMA = "decision_economic_target_outcome_comparison_manifest_v1"
EXPECTED_STATUS = "COMPLETE_DEVELOPMENT_ECONOMIC_TARGET_OUTCOME_COMPARISON_NOT_EXECUTABLE_PNL"
POLICIES = ("NAIVE_TOP10", "DECISION_V1", "DECISION_V2", "DECISION_V3")
EXPECTED_SESSIONS = 600
BLOCK_SIZE = 100


class DecisionEconomicSupportBiasError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise DecisionEconomicSupportBiasError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    mapped = series.astype(str).str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    if mapped.isna().any():
        raise DecisionEconomicSupportBiasError("INVALID_BOOLEAN_SUPPORT_COLUMN")
    return mapped.astype(bool)


def _state_presence(values: pd.Series) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values.fillna("").astype(str):
        tokens = {token.strip() for token in value.split("|") if token.strip()}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
    return dict(sorted(counts.items()))


def _mean_or_none(values: pd.Series) -> float | None:
    clean = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    return float(clean.mean()) if not clean.empty else None


def load_comparison_artifact(
    comparison_root: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = Path(comparison_root).expanduser().resolve()
    manifest_path = root / "MANIFEST.json"
    outcomes_path = root / "policy_signal_outcomes.csv"
    turnover_path = root / "membership_turnover_cost_proxy.csv"

    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != EXPECTED_COMPARISON_MANIFEST_SHA256:
        raise DecisionEconomicSupportBiasError(
            f"COMPARISON_MANIFEST_SHA_MISMATCH:{manifest_sha}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != EXPECTED_SCHEMA:
        raise DecisionEconomicSupportBiasError("COMPARISON_SCHEMA_CHANGED")
    if manifest.get("status") != EXPECTED_STATUS:
        raise DecisionEconomicSupportBiasError("COMPARISON_STATUS_CHANGED")

    artifacts = manifest.get("artifacts") or {}
    for name, path in (
        ("policy_signal_outcomes.csv", outcomes_path),
        ("membership_turnover_cost_proxy.csv", turnover_path),
    ):
        expected = str(artifacts.get(name) or "")
        if not expected or sha256_file(path) != expected:
            raise DecisionEconomicSupportBiasError(f"{name}_HASH_MISMATCH")

    outcomes = pd.read_csv(outcomes_path)
    required_outcomes = {
        "policy", "date", "target_size", "cash_weight",
        "h5_complete_support", "h5_unsupported_names", "h5_support_states",
        "h10_complete_support", "h10_unsupported_names", "h10_support_states",
    }
    missing = required_outcomes - set(outcomes.columns)
    if missing:
        raise DecisionEconomicSupportBiasError(
            f"OUTCOME_COLUMNS_MISSING:{sorted(missing)}"
        )

    turnover = pd.read_csv(turnover_path)
    required_turnover = {
        "policy", "date", "buy_count", "sell_count", "cost_bps_nav_primary"
    }
    missing = required_turnover - set(turnover.columns)
    if missing:
        raise DecisionEconomicSupportBiasError(
            f"TURNOVER_COLUMNS_MISSING:{sorted(missing)}"
        )

    for frame in (outcomes, turnover):
        frame["policy"] = frame["policy"].astype(str)
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
        if frame.duplicated(["policy", "date"]).any():
            raise DecisionEconomicSupportBiasError("DUPLICATE_POLICY_DATE")
        if set(frame["policy"]) != set(POLICIES):
            raise DecisionEconomicSupportBiasError("POLICY_SET_CHANGED")

    dates = pd.DatetimeIndex(outcomes["date"].unique()).sort_values()
    if len(dates) != EXPECTED_SESSIONS:
        raise DecisionEconomicSupportBiasError(
            f"SESSION_COUNT_CHANGED:{len(dates)}"
        )
    if set(turnover["date"].unique()) != set(dates):
        raise DecisionEconomicSupportBiasError("TURNOVER_DATE_SET_CHANGED")

    index_map = {pd.Timestamp(date): idx for idx, date in enumerate(dates)}
    for frame in (outcomes, turnover):
        frame["session_index"] = frame["date"].map(index_map).astype(int)
        frame["block"] = frame["session_index"].floordiv(BLOCK_SIZE).add(1).astype(int)

    for horizon in (5, 10):
        col = f"h{horizon}_complete_support"
        outcomes[col] = _bool_series(outcomes[col])

    return outcomes, turnover


def _group_summary(
    outcomes: pd.DataFrame,
    turnover: pd.DataFrame,
    horizon: int,
    blocks: set[int],
) -> dict[str, Any]:
    support_col = f"h{horizon}_complete_support"
    unsupported_col = f"h{horizon}_unsupported_names"
    states_col = f"h{horizon}_support_states"

    subset = outcomes.loc[outcomes["block"].isin(blocks)].copy()
    support = subset.pivot(index="date", columns="policy", values=support_col)
    support = support.reindex(columns=POLICIES).fillna(False).astype(bool)
    common = support.all(axis=1)
    fail_count = (~support).sum(axis=1)

    result: dict[str, Any] = {
        "sessions": int(len(support)),
        "common_support_dates": int(common.sum()),
        "common_support_share": float(common.mean()) if len(common) else None,
        "failure_multiplicity": {
            f"dates_with_{k}_incomplete_policies": int(fail_count.eq(k).sum())
            for k in range(1, 5)
        },
        "policies": {},
    }

    for policy in POLICIES:
        policy_rows = subset.loc[subset["policy"].eq(policy)].copy()
        own_support = policy_rows[support_col].astype(bool)
        incomplete = policy_rows.loc[~own_support].copy()
        own_dates = policy_rows.set_index("date")[support_col].astype(bool)
        exclusive = int(
            sum(
                (not bool(own_dates.loc[date])) and int(fail_count.loc[date]) == 1
                for date in support.index
            )
        )
        turn = turnover.loc[
            turnover["block"].isin(blocks) & turnover["policy"].eq(policy)
        ].copy()
        turn_map = turn.set_index("date")
        merged = policy_rows.set_index("date").join(
            turn_map[["buy_count", "sell_count", "cost_bps_nav_primary"]],
            how="left",
        )
        supported_rows = merged.loc[merged[support_col].astype(bool)]
        unsupported_rows = merged.loc[~merged[support_col].astype(bool)]

        result["policies"][policy] = {
            "complete_support_dates": int(own_support.sum()),
            "complete_support_share": float(own_support.mean()),
            "incomplete_dates": int((~own_support).sum()),
            "exclusive_common_support_limiter_dates": exclusive,
            "mean_unsupported_names_on_incomplete_dates": _mean_or_none(
                incomplete[unsupported_col]
            ),
            "support_state_presence_on_incomplete_dates": _state_presence(
                incomplete[states_col]
            ),
            "supported_vs_unsupported_structure": {
                "supported": {
                    "dates": int(len(supported_rows)),
                    "mean_target_size": _mean_or_none(supported_rows["target_size"]),
                    "mean_cash_weight": _mean_or_none(supported_rows["cash_weight"]),
                    "mean_buy_count": _mean_or_none(supported_rows["buy_count"]),
                    "mean_sell_count": _mean_or_none(supported_rows["sell_count"]),
                    "mean_primary_cost_bps_nav": _mean_or_none(
                        supported_rows["cost_bps_nav_primary"]
                    ),
                },
                "unsupported": {
                    "dates": int(len(unsupported_rows)),
                    "mean_target_size": _mean_or_none(unsupported_rows["target_size"]),
                    "mean_cash_weight": _mean_or_none(unsupported_rows["cash_weight"]),
                    "mean_buy_count": _mean_or_none(unsupported_rows["buy_count"]),
                    "mean_sell_count": _mean_or_none(unsupported_rows["sell_count"]),
                    "mean_primary_cost_bps_nav": _mean_or_none(
                        unsupported_rows["cost_bps_nav_primary"]
                    ),
                },
            },
        }

    return result


def summarize_support_bias(
    outcomes: pd.DataFrame,
    turnover: pd.DataFrame,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "decision_economic_support_bias_check_v1",
        "status": "COMPLETE_DEVELOPMENT_SUPPORT_BIAS_CHECK",
        "interpretation_boundary": {
            "development_evidence_only": True,
            "new_outcomes_accessed": False,
            "policy_or_threshold_tuning": False,
            "purpose": "EXPLAIN_COMMON_SUPPORT_SPARSITY_NOT_ESTIMATE_POLICY_RETURN",
        },
        "horizons": {},
    }

    for horizon in (5, 10):
        by_block = {
            f"block_{block}": _group_summary(
                outcomes, turnover, horizon, {block}
            )
            for block in range(1, 7)
        }
        result["horizons"][f"H{horizon}"] = {
            "blocks": by_block,
            "early_blocks_1_2": _group_summary(
                outcomes, turnover, horizon, {1, 2}
            ),
            "later_blocks_3_6": _group_summary(
                outcomes, turnover, horizon, {3, 4, 5, 6}
            ),
        }
    return result


def run_support_bias_check(comparison_root: str | Path) -> dict[str, Any]:
    outcomes, turnover = load_comparison_artifact(comparison_root)
    return summarize_support_bias(outcomes, turnover)
