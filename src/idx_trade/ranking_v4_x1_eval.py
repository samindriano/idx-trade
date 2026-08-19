from __future__ import annotations

from contextlib import contextmanager
from typing import Literal

import numpy as np
import pandas as pd

from . import ranking_v4_3_model_eval as base

SUPPORT_RATE = 0.80
TOP_K = 30
TOP_K_MIN_OBSERVABLE = 24
PROSPECTIVE_WINDOW_SESSIONS = 100
MIN_ADMITTED_DATES = 80
ROBUSTNESS_BLOCKS = 5
ROBUSTNESS_BLOCK_SIZE = 20
MIN_ADMITTED_DATES_PER_BLOCK = 16
BOOTSTRAP_BLOCK_LENGTH = 10
BOOTSTRAP_REPLICATIONS = 2000
BOOTSTRAP_SEED = 42


@contextmanager
def _x1_observability_overlay():
    """Temporarily adapt only the three X1 observability knobs.

    The inherited V4 evaluator remains the authority for score/target joining,
    fixed Top30/Bottom30 identity selection, no-refill behavior, target-rank
    metrics, and raw-return diagnostics. X1 changes only date coverage and the
    fixed-basket observable count. Window-level admission is handled below.
    """

    if base.TOP_K != TOP_K:
        raise RuntimeError("V4_X1_TOP_K_PARENT_DRIFT")
    if not np.isclose(base.DATE_TARGET_COVERAGE_GATE, 0.90):
        raise RuntimeError("V4_X1_PARENT_DATE_GATE_DRIFT")
    if base.TOP_K_MIN_OBSERVABLE != 27:
        raise RuntimeError("V4_X1_PARENT_TOP30_GATE_DRIFT")

    old_date_gate = base.DATE_TARGET_COVERAGE_GATE
    old_top_min = base.TOP_K_MIN_OBSERVABLE
    try:
        base.DATE_TARGET_COVERAGE_GATE = SUPPORT_RATE
        base.TOP_K_MIN_OBSERVABLE = TOP_K_MIN_OBSERVABLE
        yield
    finally:
        base.DATE_TARGET_COVERAGE_GATE = old_date_gate
        base.TOP_K_MIN_OBSERVABLE = old_top_min


def evaluate_head_by_date_x1(
    scored_population: pd.DataFrame,
    target_ledger: pd.DataFrame,
    *,
    head: Literal["H5", "H10", "CONSENSUS"],
) -> pd.DataFrame:
    """Evaluate one X1 head with the frozen 80% observability policy.

    This function must only be used after the prospective outcome vault is
    authorized to open. It intentionally delegates metric semantics to V4.
    """

    with _x1_observability_overlay():
        result = base.evaluate_head_by_date(
            scored_population,
            target_ledger,
            head=head,
        )
    if not np.isclose(base.DATE_TARGET_COVERAGE_GATE, 0.90):
        raise RuntimeError("V4_X1_PARENT_DATE_GATE_NOT_RESTORED")
    if base.TOP_K_MIN_OBSERVABLE != 27:
        raise RuntimeError("V4_X1_PARENT_TOP30_GATE_NOT_RESTORED")
    return result


def attach_prospective_window(
    date_metrics: pd.DataFrame,
    prospective_sessions: pd.DataFrame,
) -> pd.DataFrame:
    required = {"prospective_index", "date"}
    missing = required - set(prospective_sessions.columns)
    if missing:
        raise ValueError(
            f"prospective session table missing columns: {sorted(missing)}"
        )
    sessions = prospective_sessions[["prospective_index", "date"]].copy()
    sessions["prospective_index"] = pd.to_numeric(
        sessions["prospective_index"], errors="raise"
    ).astype(int)
    sessions["date"] = pd.to_datetime(
        sessions["date"], errors="raise"
    ).dt.tz_localize(None).dt.normalize()
    if sessions["date"].duplicated().any():
        raise ValueError("prospective dates must be unique")
    expected = list(range(1, PROSPECTIVE_WINDOW_SESSIONS + 1))
    if sessions.sort_values("prospective_index")["prospective_index"].tolist() != expected:
        raise ValueError("prospective indices must be exactly 1..100")

    metrics = date_metrics.copy()
    metrics["date"] = pd.to_datetime(
        metrics["date"], errors="raise"
    ).dt.tz_localize(None).dt.normalize()
    if metrics["date"].duplicated().any():
        raise ValueError("date metrics must contain one row per date")

    merged = sessions.merge(
        metrics,
        on="date",
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise RuntimeError("V4_X1_METRICS_DO_NOT_COVER_FROZEN_100_SESSIONS")
    merged = merged.drop(columns="_merge").sort_values(
        "prospective_index", kind="mergesort"
    ).reset_index(drop=True)
    merged["robustness_block"] = (
        (merged["prospective_index"] - 1) // ROBUSTNESS_BLOCK_SIZE + 1
    )
    return merged


def _finite_mean_if_count(
    values: pd.Series,
    *,
    minimum_count: int,
) -> tuple[int, bool, float]:
    numeric = pd.to_numeric(values, errors="coerce")
    finite = numeric[np.isfinite(numeric)]
    count = int(len(finite))
    valid = count >= minimum_count
    return count, valid, float(finite.mean()) if valid else np.nan


def summarize_x1_metrics(
    window_metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float | int | bool]]:
    required = {
        "prospective_index",
        "robustness_block",
        "ic_admitted",
        "top30_metric_admitted",
        "spread_metric_admitted",
        "daily_ic",
        "top30_mean_realized_percentile",
        "top30_bottom30_spread",
    }
    missing = required - set(window_metrics.columns)
    if missing:
        raise ValueError(f"X1 metrics missing columns: {sorted(missing)}")
    if len(window_metrics) != PROSPECTIVE_WINDOW_SESSIONS:
        raise ValueError("X1 requires exactly 100 prospective sessions")

    ordered = window_metrics.sort_values(
        "prospective_index", kind="mergesort"
    ).reset_index(drop=True)
    if ordered["prospective_index"].tolist() != list(range(1, 101)):
        raise ValueError("X1 prospective indices must be exactly 1..100")

    ic_count, ic_valid, mean_ic = _finite_mean_if_count(
        ordered["daily_ic"], minimum_count=MIN_ADMITTED_DATES
    )
    top_count, top_valid, mean_top = _finite_mean_if_count(
        ordered["top30_mean_realized_percentile"],
        minimum_count=MIN_ADMITTED_DATES,
    )
    spread_count, spread_valid, mean_spread = _finite_mean_if_count(
        ordered["top30_bottom30_spread"],
        minimum_count=MIN_ADMITTED_DATES,
    )

    block_rows: list[dict[str, object]] = []
    for block_id, block in ordered.groupby("robustness_block", sort=True):
        if len(block) != ROBUSTNESS_BLOCK_SIZE:
            raise ValueError("every X1 robustness block must have 20 sessions")
        count, valid, mean = _finite_mean_if_count(
            block["daily_ic"], minimum_count=MIN_ADMITTED_DATES_PER_BLOCK
        )
        block_rows.append(
            {
                "robustness_block": int(block_id),
                "ic_admitted_dates": count,
                "block_ic_valid": valid,
                "block_mean_daily_ic": mean,
            }
        )
    blocks = pd.DataFrame(block_rows).sort_values("robustness_block")
    if blocks["robustness_block"].tolist() != [1, 2, 3, 4, 5]:
        raise ValueError("X1 robustness blocks must be exactly 1..5")
    block_ic = pd.to_numeric(
        blocks.loc[blocks["block_ic_valid"], "block_mean_daily_ic"],
        errors="coerce",
    ).dropna()

    aggregate: dict[str, float | int | bool] = {
        "window_ic_valid": ic_valid,
        "window_top30_valid": top_valid,
        "window_spread_valid": spread_valid,
        "all_primary_metrics_valid": bool(ic_valid and top_valid and spread_valid),
        "ic_admitted_dates": ic_count,
        "top30_admitted_dates": top_count,
        "spread_admitted_dates": spread_count,
        "mean_daily_ic": mean_ic,
        "mean_top30_realized_percentile": mean_top,
        "mean_top30_bottom30_spread": mean_spread,
        "valid_20session_ic_block_count": int(blocks["block_ic_valid"].sum()),
        "positive_20session_block_count": int((block_ic > 0.0).sum()),
        "q25_20session_block_mean_daily_ic": (
            float(block_ic.quantile(0.25, interpolation="linear"))
            if len(block_ic)
            else np.nan
        ),
    }
    return blocks.reset_index(drop=True), aggregate


def moving_block_bootstrap_mean_x1(
    window_metrics: pd.DataFrame,
    *,
    value_column: str = "daily_ic",
    replications: int = BOOTSTRAP_REPLICATIONS,
    seed: int = BOOTSTRAP_SEED,
) -> np.ndarray:
    ordered = window_metrics.sort_values(
        "prospective_index", kind="mergesort"
    )
    if len(ordered) != PROSPECTIVE_WINDOW_SESSIONS:
        raise ValueError("X1 bootstrap requires exactly 100 sessions")
    values = pd.to_numeric(
        ordered[value_column], errors="coerce"
    ).to_numpy(dtype=float)
    if int(np.isfinite(values).sum()) < MIN_ADMITTED_DATES:
        raise ValueError("X1 bootstrap requires at least 80 finite metric dates")

    rng = np.random.default_rng(seed)
    out = np.full(replications, np.nan, dtype=float)
    max_start = PROSPECTIVE_WINDOW_SESSIONS - BOOTSTRAP_BLOCK_LENGTH
    blocks_per_rep = PROSPECTIVE_WINDOW_SESSIONS // BOOTSTRAP_BLOCK_LENGTH
    for i in range(replications):
        starts = rng.integers(0, max_start + 1, size=blocks_per_rep)
        sampled = np.concatenate(
            [values[start : start + BOOTSTRAP_BLOCK_LENGTH] for start in starts]
        )
        finite = sampled[np.isfinite(sampled)]
        out[i] = float(finite.mean()) if len(finite) else np.nan
    return out


def percentile_ci(values: np.ndarray) -> tuple[float, float]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if not len(finite):
        return np.nan, np.nan
    low, high = np.quantile(finite, [0.025, 0.975], method="linear")
    return float(low), float(high)


def paired_x1_deltas(
    challenger: pd.DataFrame,
    control: pd.DataFrame,
) -> pd.DataFrame:
    metrics = (
        "daily_ic",
        "top30_mean_realized_percentile",
        "top30_bottom30_spread",
    )
    required = {"prospective_index", "date", "robustness_block", *metrics}
    if not required.issubset(challenger.columns) or not required.issubset(control.columns):
        raise ValueError("X1 paired inputs are missing required columns")
    left = challenger[list(required)].copy()
    right = control[list(required)].copy()
    merged = left.merge(
        right,
        on=["prospective_index", "date", "robustness_block"],
        suffixes=("_challenger", "_control"),
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise RuntimeError("V4_X1_PAIRED_SESSION_IDENTITY_MISMATCH")
    merged = merged.drop(columns="_merge")
    for metric in metrics:
        c = pd.to_numeric(merged[f"{metric}_challenger"], errors="coerce")
        b = pd.to_numeric(merged[f"{metric}_control"], errors="coerce")
        both = np.isfinite(c) & np.isfinite(b)
        merged[f"delta_{metric}"] = np.where(both, c - b, np.nan)
    return merged.sort_values("prospective_index", kind="mergesort").reset_index(drop=True)


def summarize_x1_deltas(
    paired: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float | int | bool]]:
    metric_columns = {
        "ic": "delta_daily_ic",
        "top30": "delta_top30_mean_realized_percentile",
        "spread": "delta_top30_bottom30_spread",
    }
    required = {"prospective_index", "robustness_block", *metric_columns.values()}
    missing = required - set(paired.columns)
    if missing:
        raise ValueError(f"X1 paired delta table missing columns: {sorted(missing)}")
    if len(paired) != 100:
        raise ValueError("X1 paired delta summary requires 100 sessions")

    aggregate: dict[str, float | int | bool] = {}
    for label, column in metric_columns.items():
        count, valid, mean = _finite_mean_if_count(
            paired[column], minimum_count=MIN_ADMITTED_DATES
        )
        aggregate[f"{label}_paired_dates"] = count
        aggregate[f"{label}_paired_valid"] = valid
        aggregate[f"mean_{label}_delta"] = mean

    block_rows: list[dict[str, object]] = []
    for block_id, block in paired.groupby("robustness_block", sort=True):
        if len(block) != 20:
            raise ValueError("X1 paired robustness block must have 20 sessions")
        count, valid, mean = _finite_mean_if_count(
            block["delta_daily_ic"], minimum_count=MIN_ADMITTED_DATES_PER_BLOCK
        )
        block_rows.append(
            {
                "robustness_block": int(block_id),
                "ic_paired_dates": count,
                "block_ic_delta_valid": valid,
                "block_mean_ic_delta": mean,
            }
        )
    blocks = pd.DataFrame(block_rows).sort_values("robustness_block")
    valid_values = pd.to_numeric(
        blocks.loc[blocks["block_ic_delta_valid"], "block_mean_ic_delta"],
        errors="coerce",
    ).dropna()
    aggregate.update(
        {
            "all_paired_primary_metrics_valid": bool(
                aggregate["ic_paired_valid"]
                and aggregate["top30_paired_valid"]
                and aggregate["spread_paired_valid"]
            ),
            "valid_20session_ic_delta_block_count": int(
                blocks["block_ic_delta_valid"].sum()
            ),
            "positive_20session_block_ic_delta_count": int(
                (valid_values > 0.0).sum()
            ),
            "q25_20session_block_mean_ic_delta": (
                float(valid_values.quantile(0.25, interpolation="linear"))
                if len(valid_values)
                else np.nan
            ),
        }
    )
    return blocks.reset_index(drop=True), aggregate
