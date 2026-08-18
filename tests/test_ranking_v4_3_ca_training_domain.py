from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.ranking_v4_3_ca_training_domain import (
    RESOLVED,
    attach_continuity,
    build_training_date_sets,
    build_window_skeleton,
    combine_target_support,
    validate_frozen_tail,
)


ROOT = Path(__file__).resolve().parents[1]


def test_window_skeleton_uses_exact_official_session_offsets() -> None:
    sessions = pd.date_range("2024-01-02", periods=20, freq="B")
    decisions = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": [sessions[2], sessions[3]],
            "session_index": [2, 3],
        }
    )
    windows = build_window_skeleton(
        decisions, sessions, max_signal_session_index=3
    )
    assert len(windows) == 4
    aaa5 = windows[(windows["ticker"] == "AAA") & (windows["horizon"] == 5)].iloc[0]
    aaa10 = windows[(windows["ticker"] == "AAA") & (windows["horizon"] == 10)].iloc[0]
    assert aaa5["entry_date"] == sessions[3]
    assert aaa5["terminal_date"] == sessions[7]
    assert aaa10["entry_date"] == sessions[3]
    assert aaa10["terminal_date"] == sessions[12]


def test_missing_continuity_identity_fails_closed() -> None:
    sessions = pd.date_range("2024-01-02", periods=20, freq="B")
    decisions = pd.DataFrame(
        {"ticker": ["AAA"], "date": [sessions[0]], "session_index": [0]}
    )
    windows = build_window_skeleton(
        decisions, sessions, max_signal_session_index=0
    )
    continuity = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "signal_date": [sessions[0]],
            "horizon": [5],
            "continuity_status": [RESOLVED],
            "continuity_reason": ["OK"],
        }
    )
    attached = attach_continuity(windows, continuity)
    h5 = attached[attached["horizon"] == 5].iloc[0]
    h10 = attached[attached["horizon"] == 10].iloc[0]
    assert bool(h5["ca_resolved"])
    assert not bool(h10["ca_resolved"])
    assert h10["continuity_status"] == "PRICE_CONTINUITY_UNRESOLVED_COVERAGE"
    assert h10["continuity_reason"] == "NO_CA_COVERAGE_FOR_TRAINING_DOMAIN_IDENTITY"


def test_combined_target_support_requires_price_and_ca() -> None:
    day = pd.Timestamp("2024-01-02")
    decisions = pd.DataFrame(
        {
            "ticker": [f"T{i:02d}" for i in range(10)],
            "date": day,
            "session_index": 100,
            "entry_open_support": True,
            "h5_close_support": True,
            "h10_close_support": True,
        }
    )
    rows = []
    for i, ticker in enumerate(decisions["ticker"]):
        for horizon in (5, 10):
            rows.append(
                {
                    "ticker": ticker,
                    "signal_date": day,
                    "horizon": horizon,
                    "ca_resolved": not (i == 0 and horizon == 10),
                }
            )
    continuity = pd.DataFrame(rows)
    combined, per_date = combine_target_support(decisions, continuity)
    assert int(combined["h5_full_target_support"].sum()) == 10
    assert int(combined["h10_full_target_support"].sum()) == 9
    row = per_date.iloc[0]
    assert np.isclose(row["h5_rate"], 1.0)
    assert np.isclose(row["h10_rate"], 0.9)
    assert np.isclose(row["consensus_rate"], 0.9)
    assert bool(row["h5_eligible"])
    assert bool(row["h10_eligible"])
    assert bool(row["consensus_eligible"])


def test_training_date_sets_obey_each_fold_purge_boundary() -> None:
    dates = pd.date_range("2024-01-02", periods=8, freq="B")
    per_date = pd.DataFrame(
        {
            "session_index": range(8),
            "date": dates,
            "h5_eligible": [True, True, False, True, True, True, True, True],
            "h10_eligible": [True, False, True, True, True, True, True, True],
        }
    )
    folds = pd.DataFrame(
        {
            "fold": [1, 1, 2, 2],
            "max_training_signal_session_index": [3, 3, 6, 6],
        }
    )
    result = build_training_date_sets(per_date, folds)
    f1_h5 = result[(result["fold"] == 1) & (result["head"] == "H5")]
    f1_h10 = result[(result["fold"] == 1) & (result["head"] == "H10")]
    f2_h5 = result[(result["fold"] == 2) & (result["head"] == "H5")]
    assert f1_h5["session_index"].tolist() == [0, 1, 3]
    assert f1_h10["session_index"].tolist() == [0, 2, 3]
    assert f2_h5["session_index"].max() == 6
    assert (result["session_index"] <= result["max_training_signal_session_index"]).all()


def test_frozen_tail_requires_same_600_consensus_eligible_identities() -> None:
    dates = pd.date_range("2022-01-03", periods=700, freq="B")
    per_date = pd.DataFrame(
        {
            "session_index": range(700),
            "date": dates,
            "h5_rate": 0.95,
            "h10_rate": 0.94,
            "consensus_rate": 0.93,
            "h5_eligible": True,
            "h10_eligible": True,
            "consensus_eligible": True,
        }
    )
    frozen = pd.DataFrame(
        {"session_index": range(100, 700), "date": dates[100:]}
    )
    result = validate_frozen_tail(per_date, frozen)
    assert result["all_frozen_600_full_target_eligible"] is True
    assert result["tail_600_identity_unchanged"] is True
    assert result["eligible_sessions_after_frozen_end"] == 0
    assert np.isclose(result["frozen_consensus_min_rate"], 0.93)

    broken = per_date.copy()
    broken.loc[650, "consensus_eligible"] = False
    result_broken = validate_frozen_tail(broken, frozen)
    assert result_broken["all_frozen_600_full_target_eligible"] is False
    assert result_broken["tail_600_identity_unchanged"] is False


def test_runner_is_outcome_blind_and_does_not_import_model_execution() -> None:
    source = (ROOT / "scripts" / "run_v4_3_ca_training_domain_gate.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "materialize_v4_target_ledger",
        "fit_v4_head",
        "score_v4_head",
        "ranking_v4_3_model_eval",
        "requests.get",
        "performance_computed = True",
    )
    for token in forbidden:
        assert token not in source
    assert "historical_target_loaded\": False" in source
    assert "historical_model_fit\": False" in source
