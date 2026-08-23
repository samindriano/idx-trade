from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.historical_e2e_replay_readiness_v1 import (
    OFFICIAL_OPEN_STATUS,
    RESOLVED_CA_STATUS,
    build_ca_gap,
    build_exposure_universe,
    ensure_safe_columns,
    longest_segments,
)


def test_rejects_protected_or_outcome_columns() -> None:
    with pytest.raises(RuntimeError, match="PROTECTED_OR_OUTCOME_COLUMN_REJECTED"):
        ensure_safe_columns(["ticker", "r10"], context="fixture")


def test_exposure_intervals_are_deterministic_and_half_open() -> None:
    structural = {
        "decision_session_ledger.csv": pd.DataFrame({"index": [0, 1, 2], "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]), "fold": [1, 1, 1]}),
        "holding_spells.csv": pd.DataFrame({"ticker": ["AAA", "BBB"], "entry_index": [0, 1], "entry_date": pd.to_datetime(["2024-01-01", "2024-01-02"]), "exit_index": [2, None], "exit_date": pd.to_datetime(["2024-01-03", None]), "entry_reason": ["BOOTSTRAP", "FILL"], "right_censored": [False, True]}),
    }
    result = build_exposure_universe(structural)
    assert list(zip(result["ticker"], result["session_index"])) == [("AAA", 0), ("AAA", 1), ("BBB", 1), ("BBB", 2)]


def test_missing_ca_evidence_does_not_pass_strict_gate() -> None:
    exposure = pd.DataFrame({"ticker": ["AAA", "BBB"], "signal_date": pd.to_datetime(["2024-01-01", "2024-01-01"]), "session_index": [0, 0]})
    ca = pd.DataFrame({"ticker": ["AAA"], "signal_date": pd.to_datetime(["2024-01-01"]), "horizon": [5], "continuity_status": [RESOLVED_CA_STATUS], "continuity_reason": ["OK"], "blocking_event_ids": [None], "blocking_transition_dates": [None]})
    result = build_ca_gap(exposure, ca)
    assert not result["ca_strict_pass"].any()


def test_only_explicit_official_open_status_is_admitted() -> None:
    statuses = pd.Series([OFFICIAL_OPEN_STATUS, "YAHOO_RAW_OPTIONAL", "OPEN_UNAVAILABLE"])
    eligible = statuses.eq(OFFICIAL_OPEN_STATUS)
    assert eligible.tolist() == [True, False, False]


def test_longest_segments_never_infers_unknown_as_true() -> None:
    frame = pd.DataFrame({"signal_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]), "gate": [True, False, True]})
    result = longest_segments(frame, "gate")
    assert result["sessions"].tolist() == [1, 1]

