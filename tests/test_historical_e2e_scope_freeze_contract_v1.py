from __future__ import annotations

from scripts.freeze_historical_e2e_scope_v1 import longest_contiguous_indices


def test_longest_contiguous_scope_run_breaks_ties_by_earliest_index() -> None:
    rows = [
        {"session_index": 0, "ready": True},
        {"session_index": 1, "ready": True},
        {"session_index": 2, "ready": False},
        {"session_index": 3, "ready": True},
        {"session_index": 4, "ready": True},
    ]
    assert longest_contiguous_indices(rows, "ready") == [0, 1]


def test_scope_run_does_not_bridge_an_ineligible_session() -> None:
    rows = [
        {"session_index": 10, "ready": True},
        {"session_index": 11, "ready": False},
        {"session_index": 12, "ready": True},
    ]
    assert longest_contiguous_indices(rows, "ready") == [10]
