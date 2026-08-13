from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from idx_trade.ranking_v2_forward_runtime import (
    FORWARD_OUTCOME_ACCESS_STARTED,
    assert_forward_outcome_access_not_started,
    build_outcome_blind_forward_features,
    first_mature_forward_block,
    h10_maturity_diagnostics,
    write_forward_outcome_access_started,
)


def _synthetic_panel(*, sessions: int = 85) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    dates = pd.date_range("2026-04-01", periods=sessions, freq="B")
    rows: list[dict[str, object]] = []
    for ticker_index, ticker in enumerate(("AAA", "BBB", "CCC")):
        for index, date in enumerate(dates):
            close = 100.0 + ticker_index * 10.0 + index * (1.0 + ticker_index / 10.0)
            rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "high": close + 2.0,
                    "low": close - 2.0,
                    "close": close,
                    "volume": 1_000_000.0 + index * 1000.0,
                    "regular_market_value": 2_000_000_000.0 + ticker_index * 100_000_000.0,
                }
            )
    return pd.DataFrame(rows), dates


def test_forward_feature_builder_is_outcome_blind_and_post_cutoff() -> None:
    panel, dates = _synthetic_panel()
    result = build_outcome_blind_forward_features(
        panel,
        dates,
        listed_from={"AAA": dates[0], "BBB": dates[0], "CCC": dates[0]},
        cutoff_date=dates[60],
    )
    assert not result.empty
    assert result["date"].min() > dates[60]
    assert "binary_target" not in result.columns
    assert "label_status" not in result.columns


def test_forward_feature_builder_rejects_outcome_columns() -> None:
    panel, dates = _synthetic_panel()
    panel["binary_target"] = 0
    with pytest.raises(ValueError, match="outcome columns"):
        build_outcome_blind_forward_features(panel, dates, cutoff_date=dates[60])


def test_maturity_selects_first_exact_consecutive_block_without_labels() -> None:
    dates = pd.date_range("2026-08-03", periods=115, freq="B")
    maturity = h10_maturity_diagnostics(dates[:105], dates)
    block = first_mature_forward_block(maturity)
    assert block is not None
    assert len(block) == 100
    assert block["signal_session_index"].diff().dropna().eq(1).all()
    assert block.iloc[0]["signal_date"] == dates[0]


def test_marker_is_atomic_and_duplicate_access_fails(tmp_path) -> None:
    assert_forward_outcome_access_not_started(tmp_path)
    marker = write_forward_outcome_access_started(
        tmp_path,
        pre_outcome_manifest_sha256="abc",
        block_start="2026-08-03",
        block_end="2026-12-18",
    )
    assert marker.name == FORWARD_OUTCOME_ACCESS_STARTED
    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert payload["marker"] == FORWARD_OUTCOME_ACCESS_STARTED
    with pytest.raises(RuntimeError, match="already started"):
        write_forward_outcome_access_started(
            tmp_path,
            pre_outcome_manifest_sha256="def",
            block_start="2026-08-03",
            block_end="2026-12-18",
        )
