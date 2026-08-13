from __future__ import annotations

import pandas as pd

from idx_trade.ranking_v2_candidate import _normalize_candidate_table, build_parser as candidate_parser
from idx_trade.ranking_v2_prepare_cache import _validate_h10_labels
from idx_trade.research_v2_features import V2_XS_FEATURE_COLUMNS
from idx_trade.research_v2_models import LOGISTIC_XS


def test_candidate_runner_parser_exposes_only_frozen_candidate_argument() -> None:
    parser = candidate_parser()
    candidate_action = next(action for action in parser._actions if action.dest == "candidate")
    assert LOGISTIC_XS in candidate_action.choices


def test_candidate_table_contract_accepts_resolved_primary_rows() -> None:
    row: dict[str, object] = {
        "ticker": "AAA",
        "date": "2026-01-02",
        "signal_session_index": 600,
        "binary_target": 1,
        "label_status": "TP_FIRST",
        "universe_primary_liquid": True,
    }
    for feature in V2_XS_FEATURE_COLUMNS:
        row[feature] = 0.5
    result = _normalize_candidate_table(pd.DataFrame([row]), LOGISTIC_XS)
    assert result.loc[0, "ticker"] == "AAA"
    assert int(result.loc[0, "signal_session_index"]) == 600


def test_cache_h10_label_contract_requires_horizon_ten() -> None:
    labels = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "signal_date": ["2026-01-02"],
            "signal_session_index": [600],
            "horizon": [10],
            "label_status": ["TP_FIRST"],
            "binary_target": [1.0],
        }
    )
    result = _validate_h10_labels(labels)
    assert int(result.loc[0, "horizon"]) == 10
