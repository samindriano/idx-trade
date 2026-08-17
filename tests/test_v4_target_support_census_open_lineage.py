import pandas as pd
import pytest

from scripts.run_v4_target_support_census import validate_and_attach_open_lineage


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "date": ["2024-01-02", "2024-01-02", "2024-01-02"],
        }
    )


def test_open_lineage_uses_derivative_then_incremental_overlay() -> None:
    panel = _panel()
    derivative = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "date": ["2024-01-02", "2024-01-02", "2024-01-02"],
            "open": [100.0, 200.0, None],
        }
    )
    overlay = pd.DataFrame(
        {
            "ticker": ["AAA", "CCC"],
            "date": ["2024-01-02", "2024-01-02"],
        }
    )

    stats = validate_and_attach_open_lineage(panel, derivative, overlay)

    assert panel["derivative_open_support"].tolist() == [True, True, False]
    assert panel["overlay_incremental_open_support"].tolist() == [False, False, True]
    assert panel["open_support"].tolist() == [True, True, True]
    assert stats == {
        "derivative_rows": 3,
        "derivative_supported_rows": 2,
        "overlay_rows": 2,
        "overlay_keys_overlapping_derivative_support": 1,
        "overlay_incremental_supported_rows": 1,
        "final_supported_rows": 3,
    }


def test_open_lineage_rejects_derivative_identity_mismatch() -> None:
    panel = _panel()
    derivative = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "DDD"],
            "date": ["2024-01-02", "2024-01-02", "2024-01-02"],
            "open": [100.0, 200.0, 300.0],
        }
    )
    overlay = pd.DataFrame(columns=["ticker", "date"])

    with pytest.raises(RuntimeError, match="OPEN_DERIVATIVE_IDENTITY_MISMATCH"):
        validate_and_attach_open_lineage(panel, derivative, overlay)
