from __future__ import annotations

import pandas as pd
import pytest

from scripts.run_v4_ca_blocker_attribution import (
    REASON_CROSS_SOURCE,
    REASON_KSEI_COVERAGE,
    REASON_KNOWN_CROSSING,
    REASON_SCHEDULE,
    RESOLVED,
    attribution_verdict,
    per_date_metrics,
    scenario_resolved_mask,
    summarize_scenario,
)


def _frame() -> pd.DataFrame:
    rows = []
    reasons = {
        "AAAA": (RESOLVED, "NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL"),
        "BBBB": ("PRICE_CONTINUITY_UNRESOLVED_COVERAGE", REASON_KSEI_COVERAGE),
        "CCCC": ("PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE", REASON_SCHEDULE),
        "DDDD": ("PRICE_CONTINUITY_UNRESOLVED_COVERAGE", REASON_CROSS_SOURCE),
        "EEEE": ("PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE", REASON_KNOWN_CROSSING),
    }
    for ticker, (status, reason) in reasons.items():
        for horizon in (5, 10):
            rows.append(
                {
                    "ticker": ticker,
                    "signal_date": pd.Timestamp("2026-01-02"),
                    "horizon": horizon,
                    "continuity_status": status,
                    "continuity_reason": reason,
                    "blocking_event_ids": "",
                }
            )
    return pd.DataFrame(rows)


def test_baseline_only_resolved_rows_count():
    frame = _frame()
    mask = scenario_resolved_mask(frame, ())
    assert int(mask.sum()) == 2


def test_schedule_ceiling_does_not_waive_known_crossing_or_coverage():
    frame = _frame()
    mask = scenario_resolved_mask(frame, (REASON_SCHEDULE,))
    resolved = set(frame.loc[mask, "ticker"])
    assert resolved == {"AAAA", "CCCC"}
    assert "EEEE" not in resolved


def test_all_current_remediable_reasons_still_preserve_known_crossing():
    frame = _frame()
    mask = scenario_resolved_mask(
        frame,
        (REASON_SCHEDULE, REASON_KSEI_COVERAGE, REASON_CROSS_SOURCE),
    )
    resolved = set(frame.loc[mask, "ticker"])
    assert resolved == {"AAAA", "BBBB", "CCCC", "DDDD"}
    assert "EEEE" not in resolved


def test_consensus_uses_h5_h10_intersection():
    frame = _frame()
    # Make BBBB resolved only for H5 to prove consensus does not count it.
    mask = frame["continuity_status"].eq(RESOLVED).copy()
    mask |= frame["continuity_reason"].eq(REASON_SCHEDULE)
    mask |= frame["continuity_reason"].eq(REASON_CROSS_SOURCE)
    mask |= frame["continuity_reason"].eq(REASON_KSEI_COVERAGE) & frame["horizon"].eq(5)
    out = per_date_metrics(frame, mask)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["h5_resolved_rows"] == 4
    assert row["h10_resolved_rows"] == 3
    assert row["consensus_resolved_rows"] == 3
    assert row["consensus_rate"] == 3 / 5


def test_per_date_metrics_rejects_mask_index_mismatch():
    frame = _frame()
    mask = scenario_resolved_mask(frame, ()).copy()
    mask.index = range(100, 100 + len(mask))
    with pytest.raises(RuntimeError, match="SCENARIO_RESOLVED_MASK_INDEX_MISMATCH"):
        per_date_metrics(frame, mask)


def test_600_date_fixture_marks_all_pass_when_every_row_is_resolved():
    rows = []
    for date in pd.date_range("2024-01-02", periods=600, freq="D"):
        for horizon in (5, 10):
            rows.append(
                {
                    "ticker": "AAAA",
                    "signal_date": date,
                    "horizon": horizon,
                    "continuity_status": RESOLVED,
                    "continuity_reason": "NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL",
                    "blocking_event_ids": "",
                }
            )
    frame = pd.DataFrame(rows)
    mask = scenario_resolved_mask(frame, ())
    per_date = per_date_metrics(frame, mask)
    summary = summarize_scenario("BASELINE", frame, per_date, mask)
    assert len(per_date) == 600
    assert summary["h5_gate_dates"] == 600
    assert summary["h10_gate_dates"] == 600
    assert summary["consensus_gate_dates"] == 600
    assert summary["all_600_pass"] is True


def _summary_flag(value: bool) -> dict[str, object]:
    return {"all_600_pass": value}


def test_attribution_verdict_requires_both_dimensions_when_only_combined_passes():
    summaries = {
        "SCHEDULE_UNKNOWN_RESOLVED_CEILING": _summary_flag(False),
        "ALL_COVERAGE_RESOLVED_CEILING": _summary_flag(False),
        "SCHEDULE_PLUS_ALL_COVERAGE_CEILING": _summary_flag(True),
    }
    assert attribution_verdict(summaries) == "OPTIMISTIC_ATTRIBUTION_BOTH_SCHEDULE_AND_COVERAGE_DIMENSIONS_REQUIRED"


def test_attribution_verdict_reports_combined_ceiling_failure():
    summaries = {
        "SCHEDULE_UNKNOWN_RESOLVED_CEILING": _summary_flag(False),
        "ALL_COVERAGE_RESOLVED_CEILING": _summary_flag(False),
        "SCHEDULE_PLUS_ALL_COVERAGE_CEILING": _summary_flag(False),
    }
    assert attribution_verdict(summaries) == "OPTIMISTIC_ATTRIBUTION_EVEN_COMBINED_CURRENT_BLOCKERS_CANNOT_CLEAR_GATE"
