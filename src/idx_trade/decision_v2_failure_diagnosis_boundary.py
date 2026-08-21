from __future__ import annotations

from copy import deepcopy

import pandas as pd

from .decision_v2_failure_diagnosis import FailureDiagnosisResult


LAST_FROZEN_INDEX = 599


def _rate(frame: pd.DataFrame, column: str) -> float | None:
    eligible = frame.loc[frame["next_evaluable"].astype(bool)]
    if eligible.empty:
        return None
    return float(eligible[column].astype(bool).mean())


def apply_next_session_boundary(result: FailureDiagnosisResult) -> FailureDiagnosisResult:
    """Exclude only terminal session rows from next-session rate denominators.

    Ticker absence on a real following session remains an evaluated failure of
    Top-10/Top-20 persistence. Only ledger index 599 lacks a following frozen
    score session and is therefore not evaluable.
    """
    exit_pending = result.exit_pending.copy()
    rejected_fresh = result.rejected_fresh.copy()
    exit_pending["next_evaluable"] = exit_pending["index"].astype(int).lt(LAST_FROZEN_INDEX)
    rejected_fresh["next_evaluable"] = rejected_fresh["index"].astype(int).lt(LAST_FROZEN_INDEX)

    summary = deepcopy(result.summary)

    exit_summary = summary["exit_grace_severity"]
    exit_summary["eligible_next_session"] = int(exit_pending["next_evaluable"].sum())
    exit_summary["overall_recovery_rate"] = _rate(exit_pending, "recovered_to_le20")
    for label, payload in exit_summary.get("by_current_rank_bin", {}).items():
        part = exit_pending.loc[exit_pending["current_rank_bin"].eq(label)]
        payload["eligible_next_session"] = int(part["next_evaluable"].sum())
        payload["recovery_rate"] = _rate(part, "recovered_to_le20")
        payload["next_top10_rate"] = _rate(part, "next_top10")
        payload["next_top20_rate"] = _rate(part, "next_top20")
        payload["confirmed_exit_next_rate"] = _rate(part, "confirmed_exit_next")

    scarcity = summary["candidate_scarcity"]
    scarcity["rejected_fresh_next_session_evaluable"] = int(rejected_fresh["next_evaluable"].sum())
    for label, payload in scarcity.get("by_previous_rank_bin", {}).items():
        part = rejected_fresh.loc[rejected_fresh["previous_rank_bin"].eq(label)]
        payload["eligible_next_session"] = int(part["next_evaluable"].sum())
        payload["next_top10_rate"] = _rate(part, "next_top10")
        payload["next_top20_rate"] = _rate(part, "next_top20")
        eligible = part.loc[part["next_evaluable"].astype(bool)]
        payload["next_absent_rate"] = (
            float((~eligible["next_present"].astype(bool)).mean())
            if not eligible.empty
            else None
        )

    block_rows = summary.get("block_mechanism_summary", [])
    for payload in block_rows:
        block = int(payload["block"])
        e = exit_pending.loc[exit_pending["block"].eq(block)]
        f = rejected_fresh.loc[rejected_fresh["block"].eq(block)]
        payload["exit_pending_next_session_evaluable"] = int(e["next_evaluable"].sum())
        payload["exit_pending_recovery_rate"] = _rate(e, "recovered_to_le20")
        payload["rejected_fresh_next_session_evaluable"] = int(f["next_evaluable"].sum())
        payload["rejected_fresh_next_top20_rate"] = _rate(f, "next_top20")

    block_summary = result.block_summary.copy()
    for idx, row in block_summary.iterrows():
        block = int(row["block"])
        e = exit_pending.loc[exit_pending["block"].eq(block)]
        f = rejected_fresh.loc[rejected_fresh["block"].eq(block)]
        block_summary.loc[idx, "exit_pending_next_session_evaluable"] = int(e["next_evaluable"].sum())
        block_summary.loc[idx, "exit_pending_recovery_rate"] = _rate(e, "recovered_to_le20")
        block_summary.loc[idx, "rejected_fresh_next_session_evaluable"] = int(f["next_evaluable"].sum())
        block_summary.loc[idx, "rejected_fresh_next_top20_rate"] = _rate(f, "next_top20")

    summary["next_session_boundary"] = {
        "last_frozen_index": LAST_FROZEN_INDEX,
        "terminal_rows_excluded_from_next_session_rates_only": True,
        "ticker_absence_on_real_next_session_counts_as_non_persistence": True,
    }

    return FailureDiagnosisResult(
        summary=summary,
        exit_pending=exit_pending,
        rejected_fresh=rejected_fresh,
        churn_attribution=result.churn_attribution,
        block_summary=block_summary,
    )
