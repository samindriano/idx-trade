from __future__ import annotations

from typing import Literal

import numpy as np


Head = Literal["H5", "H10", "CONSENSUS"]


def _finite(value: object) -> float:
    number = float(value)
    return number if np.isfinite(number) else np.nan


def evaluate_absolute_confirmation(
    *,
    head: Head,
    aggregate: dict[str, object],
    preregistration: dict[str, object],
    bootstrap_ci: tuple[float, float] | None = None,
) -> dict[str, object]:
    key = "consensus" if head == "CONSENSUS" else head.lower()
    thresholds = preregistration["absolute_confirmation_gates"][key]
    obs = preregistration["observability_contract"]

    gates: dict[str, bool] = {
        "all_primary_metrics_valid": bool(
            aggregate.get("all_primary_metrics_valid", False)
        ),
        "minimum_valid_robustness_blocks": int(
            aggregate.get("valid_20session_ic_block_count", 0)
        ) >= int(obs["minimum_valid_robustness_blocks"]),
        "mean_daily_ic": _finite(aggregate.get("mean_daily_ic", np.nan))
        >= float(thresholds["mean_daily_ic_min"]),
        "q25_20session_block_mean_daily_ic": _finite(
            aggregate.get("q25_20session_block_mean_daily_ic", np.nan)
        ) >= float(thresholds["q25_20session_block_mean_daily_ic_min"]),
        "positive_20session_block_count": int(
            aggregate.get("positive_20session_block_count", 0)
        ) >= int(thresholds["positive_20session_block_count_min"]),
        "mean_top30_realized_percentile": _finite(
            aggregate.get("mean_top30_realized_percentile", np.nan)
        ) >= float(thresholds["mean_top30_realized_percentile_min"]),
        "mean_top30_bottom30_spread": _finite(
            aggregate.get("mean_top30_bottom30_spread", np.nan)
        ) >= float(thresholds["mean_top30_bottom30_spread_min"]),
    }
    if "bootstrap_95pct_lower_mean_daily_ic_strictly_gt" in thresholds:
        lower = np.nan if bootstrap_ci is None else _finite(bootstrap_ci[0])
        gates["bootstrap_95pct_lower_mean_daily_ic"] = bool(
            np.isfinite(lower)
            and lower
            > float(
                thresholds[
                    "bootstrap_95pct_lower_mean_daily_ic_strictly_gt"
                ]
            )
        )
    return {"head": head, "gates": gates, "pass": bool(all(gates.values()))}


def evaluate_incremental_confirmation(
    *,
    consensus_delta: dict[str, object],
    h5_delta: dict[str, object],
    h10_delta: dict[str, object],
    challenger_absolute_pass: bool,
    preregistration: dict[str, object],
    consensus_bootstrap_delta_ci: tuple[float, float] | None,
) -> dict[str, object]:
    thresholds = preregistration["incremental_confirmation_gates"]
    obs = preregistration["observability_contract"]
    lower = (
        np.nan
        if consensus_bootstrap_delta_ci is None
        else _finite(consensus_bootstrap_delta_ci[0])
    )
    gates: dict[str, bool] = {
        "challenger_absolute_pass": bool(challenger_absolute_pass),
        "consensus_all_paired_primary_metrics_valid": bool(
            consensus_delta.get("all_paired_primary_metrics_valid", False)
        ),
        "consensus_minimum_valid_robustness_blocks": int(
            consensus_delta.get("valid_20session_ic_delta_block_count", 0)
        ) >= int(obs["minimum_valid_robustness_blocks"]),
        "consensus_mean_daily_ic_delta": _finite(
            consensus_delta.get("mean_ic_delta", np.nan)
        ) >= float(thresholds["consensus_mean_daily_ic_delta_min"]),
        "consensus_bootstrap_95pct_lower_mean_daily_ic_delta": bool(
            np.isfinite(lower)
            and lower
            > float(
                thresholds[
                    "consensus_bootstrap_95pct_lower_mean_daily_ic_delta_strictly_gt"
                ]
            )
        ),
        "consensus_q25_20session_block_mean_ic_delta": _finite(
            consensus_delta.get("q25_20session_block_mean_ic_delta", np.nan)
        ) >= float(thresholds["consensus_q25_20session_block_mean_ic_delta_min"]),
        "consensus_positive_20session_block_ic_delta_count": int(
            consensus_delta.get("positive_20session_block_ic_delta_count", 0)
        ) >= int(thresholds["consensus_positive_20session_block_ic_delta_count_min"]),
        "consensus_mean_top30_realized_percentile_delta": _finite(
            consensus_delta.get("mean_top30_delta", np.nan)
        ) >= float(thresholds["consensus_mean_top30_realized_percentile_delta_min"]),
        "consensus_mean_top30_bottom30_spread_delta": _finite(
            consensus_delta.get("mean_spread_delta", np.nan)
        ) >= float(thresholds["consensus_mean_top30_bottom30_spread_delta_min"]),
        "h5_mean_daily_ic_delta": _finite(h5_delta.get("mean_ic_delta", np.nan))
        >= float(thresholds["h5_mean_daily_ic_delta_min"]),
        "h5_q25_20session_block_mean_ic_delta": _finite(
            h5_delta.get("q25_20session_block_mean_ic_delta", np.nan)
        ) >= float(thresholds["h5_q25_20session_block_mean_ic_delta_min"]),
        "h10_mean_daily_ic_delta": _finite(h10_delta.get("mean_ic_delta", np.nan))
        >= float(thresholds["h10_mean_daily_ic_delta_min"]),
        "h10_q25_20session_block_mean_ic_delta": _finite(
            h10_delta.get("q25_20session_block_mean_ic_delta", np.nan)
        ) >= float(thresholds["h10_q25_20session_block_mean_ic_delta_min"]),
    }
    return {"gates": gates, "pass": bool(all(gates.values()))}


def decide_v4_x1(
    *,
    challenger_consensus_absolute: dict[str, object],
    challenger_h5_absolute: dict[str, object],
    challenger_h10_absolute: dict[str, object],
    incremental: dict[str, object],
) -> str:
    challenger_absolute_pass = bool(
        challenger_consensus_absolute.get("pass", False)
        and challenger_h5_absolute.get("pass", False)
        and challenger_h10_absolute.get("pass", False)
    )
    if challenger_absolute_pass and bool(incremental.get("pass", False)):
        return "V4_X1_GEOMETRY3_PROSPECTIVE_CONFIRMED"
    return "V4_X1_GEOMETRY3_NOT_CONFIRMED"
