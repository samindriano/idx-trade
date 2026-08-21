from __future__ import annotations

import json
from pathlib import Path

from idx_trade.decision_v3_structural_source import REPLAY_CONTRACT_RELATIVE_PATH


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_tier_c_and_high_churn_diagnostics_are_explicitly_non_gating() -> None:
    payload = json.loads(
        (REPO_ROOT / REPLAY_CONTRACT_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    assert payload["tier_c_diagnostics_are_tuning_gates"] is False
    assert payload["diagnostic_definitions"]["high_churn_transition"] == (
        "NONBOOTSTRAP_REPLACEMENT_COUNT_GE3"
    )
    assert payload["diagnostic_definitions"]["tier_c_next_session_severe_exit"] == (
        "ENTRY_REASON_TIER_C_RESIDUAL_VACANCY_FILL_AND_SAME_TICKER_STATE_SEVERE_DETERIORATION_EXIT_AT_INDEX_PLUS_1"
    )
