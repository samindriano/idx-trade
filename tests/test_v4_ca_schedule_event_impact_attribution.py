from __future__ import annotations

import pandas as pd
import pytest

from scripts.run_v4_ca_schedule_event_impact_attribution import (
    REASON_SCHEDULE,
    RESOLVED,
    build_engine,
    critical_event_ids,
    event_impact_table,
    exact_minimum_if_bounded,
    greedy_gate_clearing_subset,
    parse_event_ids,
    result_summary,
    reverse_prune,
)


NO_CROSS = "NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL"
COVERAGE = "KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED"


def _frame(
    *,
    events: tuple[str, ...] = ("A", "B", "C"),
    schedule_changes: tuple[tuple[int, str, int, str], ...] = (),
    fixed_unresolved: tuple[tuple[int, str, int], ...] = (),
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    changes = {(d, t, h): ids for d, t, h, ids in schedule_changes}
    fixed = set(fixed_unresolved)
    dates = pd.date_range("2024-01-02", periods=600, freq="D")
    tickers = [f"T{i:02d}" for i in range(10)]
    for d_idx, date in enumerate(dates):
        for ticker in tickers:
            for horizon in (5, 10):
                key = (d_idx, ticker, horizon)
                if key in changes:
                    status = "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE"
                    reason = REASON_SCHEDULE
                    blocking = changes[key]
                elif key in fixed:
                    status = "PRICE_CONTINUITY_UNRESOLVED_COVERAGE"
                    reason = COVERAGE
                    blocking = ""
                else:
                    status = RESOLVED
                    reason = NO_CROSS
                    blocking = ""
                rows.append(
                    {
                        "ticker": ticker,
                        "signal_date": date,
                        "horizon": horizon,
                        "continuity_status": status,
                        "continuity_reason": reason,
                        "blocking_event_ids": blocking,
                    }
                )
    return pd.DataFrame(rows)


def _needs(events: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": list(events),
            "ticker": [f"X{i}" for i in range(len(events))],
            "source_type": ["Right Distribution"] * len(events),
            "family": ["RIGHT_DISTRIBUTION"] * len(events),
            "semantic_class": ["SCHEDULE_REQUIRED"] * len(events),
            "reason": ["NEEDS_SCHEDULE"] * len(events),
            "source_dates": ["2025-01-01"] * len(events),
        }
    )


def test_parse_event_ids_is_order_independent_and_deduplicated():
    assert parse_event_ids("B|A|A") == frozenset({"A", "B"})
    assert parse_event_ids("") == frozenset()


def test_multi_event_schedule_row_requires_every_blocking_event():
    frame = _frame(
        schedule_changes=(
            (0, "T00", 5, "A|B"),
            (0, "T00", 10, "A|B"),
        ),
    )
    engine = build_engine(frame, ("A", "B", "C"))
    baseline = engine.evaluate(())
    only_a = engine.evaluate(("A",))
    both = engine.evaluate(("A", "B"))
    assert baseline.h5_resolved[0] == 9
    assert only_a.h5_resolved[0] == 9
    assert both.h5_resolved[0] == 10


def test_consensus_uses_exact_h5_h10_ticker_intersection():
    frame = _frame(
        schedule_changes=(
            (0, "T00", 5, "A"),
            (0, "T01", 10, "B"),
        ),
    )
    engine = build_engine(frame, ("A", "B", "C"))
    baseline = engine.evaluate(())
    assert baseline.h5_gate[0]
    assert baseline.h10_gate[0]
    assert not baseline.consensus_gate[0]
    assert baseline.consensus_resolved[0] == 8


def test_critical_universe_excludes_events_only_on_already_passing_dates():
    frame = _frame(
        schedule_changes=(
            (0, "T00", 5, "A"),
            (0, "T00", 10, "A"),
            (0, "T01", 5, "B"),
            (0, "T01", 10, "B"),
            (1, "T00", 5, "C"),
            (1, "T00", 10, "C"),
        ),
    )
    engine = build_engine(frame, ("A", "B", "C"))
    baseline = engine.evaluate(())
    assert critical_event_ids(engine, baseline) == ("A", "B")


def test_event_impact_reports_zero_for_schedule_event_with_no_blocking_rows():
    frame = _frame(
        schedule_changes=((0, "T00", 5, "A"), (0, "T00", 10, "A")),
    )
    events = ("A", "B", "C")
    engine = build_engine(frame, events)
    impacts = event_impact_table(engine, _needs(events), engine.evaluate(()))
    zero = impacts.set_index("event_id").loc["C"]
    assert zero["blocking_rows"] == 0
    assert zero["single_event_deficit_reduction"] == 0


def test_greedy_handles_conjunctive_zero_immediate_gain_synergy():
    frame = _frame(
        schedule_changes=(
            (0, "T00", 5, "A|B"),
            (0, "T00", 10, "A|B"),
        ),
        fixed_unresolved=((0, "T01", 5), (0, "T01", 10)),
    )
    engine = build_engine(frame, ("A", "B"))
    baseline = engine.evaluate(())
    assert not baseline.all_pass
    critical = critical_event_ids(engine, baseline)
    selection, trace = greedy_gate_clearing_subset(engine, critical)
    assert selection == ["A", "B"]
    assert trace[0]["deficit_reduction"] == 0
    assert engine.evaluate(selection).all_pass


def test_reverse_prune_removes_redundant_event_and_is_inclusion_minimal():
    frame = _frame(
        schedule_changes=(
            (0, "T00", 5, "A"),
            (0, "T00", 10, "A"),
            (0, "T01", 5, "B"),
            (0, "T01", 10, "B"),
        ),
    )
    engine = build_engine(frame, ("A", "B", "C"))
    final, removed = reverse_prune(engine, ["A", "B", "C"])
    assert "C" in removed
    assert len(final) == 1
    assert engine.evaluate(final).all_pass
    assert not engine.evaluate(()).all_pass


def test_exact_search_proves_minimum_when_critical_universe_is_small():
    frame = _frame(
        schedule_changes=(
            (0, "T00", 5, "A"),
            (0, "T00", 10, "A"),
            (0, "T01", 5, "B"),
            (0, "T01", 10, "B"),
        ),
    )
    engine = build_engine(frame, ("A", "B"))
    exact, status, evaluations = exact_minimum_if_bounded(engine, ("A", "B"))
    assert exact == ["A"]
    assert status.startswith("GLOBAL_MINIMUM_CARDINALITY_PROVEN")
    assert evaluations > 0


def test_exact_search_refuses_global_claim_above_bound():
    frame = _frame(events=("A",))
    engine = build_engine(frame, ("A",))
    critical = tuple(f"E{i:02d}" for i in range(13))
    exact, status, evaluations = exact_minimum_if_bounded(engine, critical)
    assert exact is None
    assert status == "NOT_RUN_CRITICAL_UNIVERSE_ABOVE_EXACT_BOUND"
    assert evaluations == 0


def test_unknown_selected_event_fails_closed():
    engine = build_engine(_frame(events=("A",)), ("A",))
    with pytest.raises(RuntimeError, match="UNKNOWN_SELECTED_EVENT_ID"):
        engine.evaluate(("Z",))


def test_schedule_blocked_row_without_event_id_fails_closed():
    frame = _frame(schedule_changes=((0, "T00", 5, ""),))
    with pytest.raises(RuntimeError, match="SCHEDULE_BLOCKED_ROW_WITHOUT_EVENT_ID"):
        build_engine(frame, ("A",))


def test_schedule_row_with_unknown_event_id_fails_closed():
    frame = _frame(schedule_changes=((0, "T00", 5, "Z"),))
    with pytest.raises(RuntimeError, match="SCHEDULE_ROW_UNKNOWN_EVENT_IDS"):
        build_engine(frame, ("A",))


def test_result_summary_reports_gate_and_deficit_state():
    frame = _frame(
        schedule_changes=(
            (0, "T00", 5, "A"),
            (0, "T00", 10, "A"),
            (0, "T01", 5, "B"),
            (0, "T01", 10, "B"),
        ),
    )
    engine = build_engine(frame, ("A", "B"))
    summary = result_summary(engine.evaluate(()))
    assert summary["all_600_pass"] is False
    assert summary["total_deficit_units"] > 0
    assert summary["h5_gate_dates"] == 599
