from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.pit_safe_replay import (
    CORRECTED_O2_KEY_SHA256,
    CORRECTED_V2_KEY_SHA256,
    O2_FEATURE_COLUMNS,
    REPLAY_BOUNDARY,
    V3_B_FEATURE_COLUMNS,
    _read_table,
    _stable_key_hash,
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
