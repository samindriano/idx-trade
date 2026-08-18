from __future__ import annotations

import pandas as pd
import pytest

from scripts.run_v4_ca_blocker_attribution_v2 import (
    REASON_CROSS_SOURCE,
    REASON_KSEI_COVERAGE,
    REASON_KNOWN_CROSSING,
    REASON_NO_CROSSING,
    REASON_SCHEDULE,
    RESOLVED,
    SCENARIOS,
    attribution_verdict,
    minimal_clearing_scenarios,
    per_date_metrics,
    scenario_resolved_mask,
    summarize_scenario,
)


def _frame() -> pd.DataFrame:
    rows = []
    reasons = {
        "AAAA": (RESOLVED, REASON_NO_CROSSING),
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


def test_schedule_only_does_not_waive_coverage_or_known_crossing():
    frame = _frame()
    mask = scenario_resolved_mask(frame, (REASON_SCHEDULE,))
    assert set(frame.loc[mask, "ticker"]) == {"AAAA", "CCCC"}


def test_ksei_coverage_only_is_distinct_from_cross_source():
    frame = _frame()
    mask = scenario_resolved_mask(frame, (REASON_KSEI_COVERAGE,))
    assert set(frame.loc[mask, "ticker"]) == {"AAAA", "BBBB"}
    assert "DDDD" not in set(frame.loc[mask, "ticker"])


def test_cross_source_only_is_distinct_from_ksei_coverage():
    frame = _frame()
    mask = scenario_resolved_mask(frame, (REASON_CROSS_SOURCE,))
    assert set(frame.loc[mask, "ticker"]) == {"AAAA", "DDDD"}
    assert "BBBB" not in set(frame.loc[mask, "ticker"])


def test_all_current_removable_reasons_preserve_known_crossing():
    frame = _frame()
    mask = scenario_resolved_mask(
        frame,
        (REASON_SCHEDULE, REASON_KSEI_COVERAGE, REASON_CROSS_SOURCE),
    )
    assert set(frame.loc[mask, "ticker"]) == {"AAAA", "BBBB", "CCCC", "DDDD"}
    assert "EEEE" not in set(frame.loc[mask, "ticker"])


def test_explicit_known_crossing_waiver_is_rejected():
    frame = _frame()
    with pytest.raises(RuntimeError, match="KNOWN_MECHANICAL_CROSSING_CANNOT_BE_WAIVED"):
        scenario_resolved_mask(frame, (REASON_KNOWN_CROSSING,))


def test_consensus_uses_h5_h10_intersection():
    frame = _frame()
    mask = frame["continuity_status"].eq(RESOLVED).copy()
    mask |= frame["continuity_reason"].eq(REASON_SCHEDULE)
    mask |= frame["continuity_reason"].eq(REASON_CROSS_SOURCE)
    mask |= frame["continuity_reason"].eq(REASON_KSEI_COVERAGE) & frame["horizon"].eq(5)
    out = per_date_metrics(frame, mask)
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
                    "continuity_reason": REASON_NO_CROSSING,
                    "blocking_event_ids": "",
                }
            )
    frame = pd.DataFrame(rows)
    mask = scenario_resolved_mask(frame, ())
    per_date = per_date_metrics(frame, mask)
    summary = summarize_scenario("BASELINE", frame, per_date, mask)
    assert len(per_date) == 600
    assert summary["all_600_pass"] is True


def _summary(value: bool) -> dict[str, object]:
    return {"all_600_pass": value}


def _all_false() -> dict[str, dict[str, object]]:
    return {name: _summary(False) for name in SCENARIOS}


def test_minimal_clearing_scenario_prefers_single_dimension_over_superset():
    summaries = _all_false()
    summaries["KSEI_COVERAGE_ONLY_CEILING"] = _summary(True)
    summaries["ALL_COVERAGE_CEILING"] = _summary(True)
    summaries["SCHEDULE_PLUS_KSEI_COVERAGE_CEILING"] = _summary(True)
    summaries["SCHEDULE_PLUS_ALL_COVERAGE_CEILING"] = _summary(True)
    assert minimal_clearing_scenarios(summaries) == ["KSEI_COVERAGE_ONLY_CEILING"]


def test_minimal_clearing_scenarios_can_report_multiple_incomparable_paths():
    summaries = _all_false()
    summaries["SCHEDULE_ONLY_CEILING"] = _summary(True)
    summaries["KSEI_COVERAGE_ONLY_CEILING"] = _summary(True)
    summaries["SCHEDULE_PLUS_KSEI_COVERAGE_CEILING"] = _summary(True)
    assert minimal_clearing_scenarios(summaries) == [
        "KSEI_COVERAGE_ONLY_CEILING",
        "SCHEDULE_ONLY_CEILING",
    ]
    assert attribution_verdict(summaries) == "OPTIMISTIC_ATTRIBUTION_V2_MULTIPLE_MINIMAL_CLEARING_SCENARIOS"


def test_combined_only_path_is_reported_as_minimal():
    summaries = _all_false()
    summaries["SCHEDULE_PLUS_ALL_COVERAGE_CEILING"] = _summary(True)
    assert minimal_clearing_scenarios(summaries) == ["SCHEDULE_PLUS_ALL_COVERAGE_CEILING"]
    assert attribution_verdict(summaries).endswith("SCHEDULE_PLUS_ALL_COVERAGE_CEILING")


def test_no_current_removable_combination_clears_gate():
    summaries = _all_false()
    assert attribution_verdict(summaries) == (
        "OPTIMISTIC_ATTRIBUTION_V2_EVEN_ALL_CURRENT_REMOVABLE_BLOCKERS_CANNOT_CLEAR_GATE"
    )
