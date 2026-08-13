from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.pit_safe_replay import (
    CORRECTED_O2_KEY_SHA256,
    CORRECTED_V2_KEY_SHA256,
    O2_FEATURE_COLUMNS,
    REPLAY_BOUNDARY,
    V3_B_FEATURE_COLUMNS,
    _strict_boolean_series,
    apply_conditional_ladder,
    _read_table,
    _stable_key_hash,
    verify_v2_v3_control_equivalence,
)
from idx_trade.research_v2_models import ALL_RANKING_V2_MODELS


def _mini_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBCA", "BBRI"],
            "date": ["2024-01-02", "2024-01-02"],
            "signal_session_index": [100, 100],
            "binary_target": [1, 0],
            "label_status": ["TP_FIRST", "SL_FIRST"],
            "universe_primary_liquid": [True, True],
            "feature": [0.1, 0.2],
        }
    )


def test_stable_key_hash_is_deterministic_and_order_invariant() -> None:
    frame = _mini_table()
    assert _stable_key_hash(frame) == _stable_key_hash(frame.iloc[::-1].reset_index(drop=True))


def test_read_table_requires_exact_h10_mapping(tmp_path) -> None:
    path = tmp_path / "table.parquet"
    _mini_table().to_parquet(path, index=False)
    result = _read_table(path, {"feature"})
    assert list(result["ticker"]) == ["BBCA", "BBRI"]
    assert result["date"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-02", "2024-01-02"]


def test_read_table_rejects_historical_boundary_crossing(tmp_path) -> None:
    frame = _mini_table()
    frame.loc[0, "date"] = "2026-08-03"
    path = tmp_path / "table.parquet"
    frame.to_parquet(path, index=False)
    with pytest.raises(RuntimeError, match="historical boundary"):
        _read_table(path, {"feature"})


def test_strict_boolean_parser_rejects_truthy_string() -> None:
    with pytest.raises(RuntimeError, match="strict boolean"):
        _strict_boolean_series(pd.Series(["False", "True"]), "flag")


def test_conditional_ladder_orphans_o2_without_propagating_v3_failure() -> None:
    v2 = {"champion_status": "RANKING_V2_HISTORICAL_CHAMPION_SELECTED", "champion": "HGB_XS_MARKET"}
    v3 = {"decision": "V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2"}
    o2 = {"decision": "O2_SURVIVOR"}
    ladder = apply_conditional_ladder(v2, v3, o2)
    assert ladder["o2"]["diagnostic_decision"] == "O2_SURVIVOR"
    assert ladder["o2"]["clean_lineage_decision"] == "O2_DIAGNOSTIC_ORPHANED_PARENT"
    assert o2["decision"] == "O2_DIAGNOSTIC_ORPHANED_PARENT"
    assert o2["decision"] != "O2_NO_SURVIVOR"


def test_v2_v3_control_equivalence_requires_exact_scores(tmp_path) -> None:
    keys = {
        "fold": ["V2F1", "V2F1"],
        "ticker": ["BBCA", "BBRI"],
        "date": ["2024-01-02", "2024-01-02"],
        "signal_session_index": [100, 100],
        "binary_target": [1, 0],
        "score": [0.25, -0.10],
    }
    v2_path = tmp_path / "v2.parquet"
    v3_path = tmp_path / "v3.parquet"
    pd.DataFrame({"candidate": ["HGB_XS_MARKET"] * 2, **keys}).to_parquet(v2_path, index=False)
    pd.DataFrame({"model": ["V3B_COMMON_SUPPORT_BASELINE"] * 2, **keys}).to_parquet(v3_path, index=False)
    result = verify_v2_v3_control_equivalence(v2_path, v3_path)
    assert result["status"] == "V2_V3_CONTROL_EXACT_EQUIVALENCE_PASS"
    assert result["rows"] == 2
    assert result["max_score_abs_diff"] == 0.0


def test_replay_model_and_geometry_contract_is_frozen() -> None:
    assert ALL_RANKING_V2_MODELS == (
        "V1_HGB_CONTROL",
        "LOGISTIC_XS",
        "HGB_XS",
        "HGB_XS_MARKET",
        "PAIRWISE_LOGISTIC_XS",
    )
    assert O2_FEATURE_COLUMNS[-3:] == ("open_position", "open_to_high", "open_to_low")
    assert len(V3_B_FEATURE_COLUMNS) == 33
    assert REPLAY_BOUNDARY == "2026-07-31"
    assert len(CORRECTED_V2_KEY_SHA256) == 64
    assert len(CORRECTED_O2_KEY_SHA256) == 64
