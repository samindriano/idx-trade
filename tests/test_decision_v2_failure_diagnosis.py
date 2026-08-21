from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v2_failure_diagnosis import (
    DecisionV2FailureDiagnosisError,
    FailureDiagnosisResult,
    FrozenStructuralLedgers,
    build_churn_attribution,
    build_exit_pending_diagnosis,
    build_rejected_fresh_diagnosis,
    descriptive_rank_bin,
    write_failure_diagnosis_artifacts,
)


def _ledgers() -> FrozenStructuralLedgers:
    sessions = pd.DataFrame(
        [
            {"index": 0, "date": "2026-01-01", "bootstrap": True, "capacity_state": "FULL", "unfilled_slots": 0, "replacement_count": 0, "sell_count": 0, "buy_count": 10},
            {"index": 1, "date": "2026-01-02", "bootstrap": False, "capacity_state": "UNFILLED_NO_QUALIFIED_CHALLENGER", "unfilled_slots": 2, "replacement_count": 3, "sell_count": 3, "buy_count": 1},
            {"index": 2, "date": "2026-01-03", "bootstrap": False, "capacity_state": "FULL", "unfilled_slots": 0, "replacement_count": 1, "sell_count": 1, "buy_count": 1},
        ]
    )
    states = pd.DataFrame(
        [
            {"index": 1, "date": "2026-01-02", "kind": "INCUMBENT", "ticker": "A", "current_rank": 25, "previous_rank": 10, "state": "EXIT_PENDING_1"},
            {"index": 1, "date": "2026-01-02", "kind": "INCUMBENT", "ticker": "B", "current_rank": 150, "previous_rank": 8, "state": "EXIT_PENDING_1"},
            {"index": 2, "date": "2026-01-03", "kind": "INCUMBENT", "ticker": "A", "current_rank": 15, "previous_rank": 25, "state": "ACCEPTABLE_HOLD"},
            {"index": 2, "date": "2026-01-03", "kind": "INCUMBENT", "ticker": "B", "current_rank": 120, "previous_rank": 150, "state": "CONFIRMED_EXIT"},
            {"index": 1, "date": "2026-01-02", "kind": "CHALLENGER", "ticker": "C", "current_rank": 3, "previous_rank": 35, "state": "UNCONFIRMED_PREVIOUS_GT_THRESHOLD"},
            {"index": 1, "date": "2026-01-02", "kind": "CHALLENGER", "ticker": "D", "current_rank": 4, "previous_rank": None, "state": "UNCONFIRMED_PREVIOUS_ABSENT"},
        ]
    )
    intents = pd.DataFrame(
        [
            {"index": 1, "date": "2026-01-02", "side": "SELL_INTENT", "ticker": "X", "reason": "CONFIRMED_EXIT_GT20_2"},
            {"index": 1, "date": "2026-01-02", "side": "SELL_INTENT", "ticker": "Y", "reason": "CONFIRMED_EXIT_GT20_2"},
            {"index": 1, "date": "2026-01-02", "side": "SELL_INTENT", "ticker": "Z", "reason": "SOFT_RANK_GAP_REPLACEMENT"},
            {"index": 1, "date": "2026-01-02", "side": "BUY_INTENT", "ticker": "Q", "reason": "QUALIFIED_VACANCY_FILL"},
            {"index": 2, "date": "2026-01-03", "side": "SELL_INTENT", "ticker": "Z", "reason": "SOFT_RANK_GAP_REPLACEMENT"},
            {"index": 2, "date": "2026-01-03", "side": "BUY_INTENT", "ticker": "R", "reason": "SOFT_RANK_GAP_REPLACEMENT"},
        ]
    )
    return FrozenStructuralLedgers(
        root=Path("."),
        manifest={},
        sessions=sessions,
        memberships=pd.DataFrame(),
        intents=intents,
        states=states,
    )


def test_descriptive_rank_bins_are_fixed_reporting_strata() -> None:
    assert descriptive_rank_bin(20) == "LE20"
    assert descriptive_rank_bin(21) == "21_30"
    assert descriptive_rank_bin(30) == "21_30"
    assert descriptive_rank_bin(31) == "31_50"
    assert descriptive_rank_bin(100) == "51_100"
    assert descriptive_rank_bin(101) == "101_200"
    assert descriptive_rank_bin(201) == "GT200"
    assert descriptive_rank_bin(None) == "ABSENT"


def test_exit_pending_diagnosis_separates_recovery_from_severe_collapse() -> None:
    ledgers = _ledgers()
    ranks = {(2, "A"): 15, (2, "B"): 120}
    result = build_exit_pending_diagnosis(ledgers, ranks)
    a = result.loc[result["ticker"].eq("A")].iloc[0]
    b = result.loc[result["ticker"].eq("B")].iloc[0]
    assert bool(a["recovered_to_le20"]) is True
    assert a["current_rank_bin"] == "21_30"
    assert bool(b["recovered_to_le20"]) is False
    assert b["current_rank_bin"] == "101_200"
    assert bool(b["confirmed_exit_next"]) is True


def test_rejected_fresh_diagnosis_is_descriptive_not_counterfactual() -> None:
    ledgers = _ledgers()
    ranks = {(2, "C"): 8, (2, "D"): 40}
    result = build_rejected_fresh_diagnosis(ledgers, ranks)
    assert set(result["ticker"]) == {"C", "D"}
    assert result["session_unfilled_slots"].eq(2).all()
    assert result["session_rejected_fresh_count"].eq(2).all()
    assert result["rejected_supply_ge_vacancy"].all()
    c = result.loc[result["ticker"].eq("C")].iloc[0]
    d = result.loc[result["ticker"].eq("D")].iloc[0]
    assert c["previous_rank_bin"] == "31_50"
    assert bool(c["next_top10"]) is True
    assert d["previous_rank_bin"] == "ABSENT"
    assert bool(d["next_top20"]) is False


def test_churn_attribution_uses_only_frozen_intent_reasons() -> None:
    result = build_churn_attribution(_ledgers())
    high = result.loc[result["index"].eq(1)].iloc[0]
    assert bool(high["high_churn_ge3"]) is True
    assert high["confirmed_exit_sells"] == 2
    assert high["soft_replacement_sells"] == 1
    assert high["qualified_vacancy_fill_buys"] == 1
    assert high["dominant_sell_driver"] == "CONFIRMED_EXIT"


def test_output_writer_is_fail_closed(tmp_path: Path) -> None:
    empty = pd.DataFrame()
    result = FailureDiagnosisResult(
        summary={"status": "COMPLETE", "source": {}, "guards": {}},
        exit_pending=empty,
        rejected_fresh=empty,
        churn_attribution=empty,
        block_summary=empty,
    )
    output = tmp_path / "diag"
    manifest = write_failure_diagnosis_artifacts(result, output)
    assert manifest.is_file()
    with pytest.raises(DecisionV2FailureDiagnosisError, match="OUTPUT_ALREADY_EXISTS"):
        write_failure_diagnosis_artifacts(result, output)
