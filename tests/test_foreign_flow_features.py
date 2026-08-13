from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.foreign_flow_features import (
    FEATURE_COLUMNS,
    materialize_foreign_flow_features,
    write_offline_audit_artifacts,
)


def _inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex, pd.DataFrame]:
    sessions = pd.date_range("2026-01-01", periods=22, freq="B")
    flow = pd.DataFrame(
        {
            "ticker": ["TEST"] * len(sessions),
            "session_date": sessions,
            "foreign_buy": np.arange(1, len(sessions) + 1) * 10,
            "foreign_sell": np.zeros(len(sessions), dtype=int),
            "foreign_net": np.arange(1, len(sessions) + 1) * 10,
            "unit": ["SHARES"] * len(sessions),
        }
    )
    volume = pd.DataFrame({"ticker": ["TEST"] * len(sessions), "date": sessions, "raw_volume": [100] * len(sessions)})
    master = pd.DataFrame({"ticker": ["TEST"], "listed_from": [sessions[0]], "listed_to": [pd.NaT]})
    return flow, volume, sessions, master


def test_features_start_on_next_session_and_do_not_use_same_session_flow() -> None:
    flow, volume, sessions, master = _inputs()
    output, _ = materialize_foreign_flow_features(flow, volume, sessions, master)
    row = output.loc[output["feature_session"].eq(sessions[1])].iloc[0]
    assert row["flow_through_session"] == sessions[0]
    assert row["foreign_net_to_volume_1"] == pytest.approx(0.1)
    changed = flow.copy()
    changed.loc[changed["session_date"].eq(sessions[1]), "foreign_net"] = 999999
    changed.loc[changed["session_date"].eq(sessions[1]), "foreign_buy"] = 999999
    changed_output, _ = materialize_foreign_flow_features(changed, volume, sessions, master)
    assert changed_output.loc[changed_output["feature_session"].eq(sessions[1]), "foreign_net_to_volume_1"].iloc[0] == pytest.approx(0.1)


def test_zero_volume_is_missing_not_a_zero_or_infinite_feature() -> None:
    flow, volume, sessions, master = _inputs()
    volume.loc[volume["date"].eq(sessions[0]), "raw_volume"] = 0
    output, summary = materialize_foreign_flow_features(flow, volume, sessions, master)
    row = output.loc[output["feature_session"].eq(sessions[1])].iloc[0]
    assert pd.isna(row["foreign_net_to_volume_1"])
    assert "INVALID_ZERO_DENOMINATOR" in row["missing_reasons"]
    assert summary["forward_fill_used"] is False


def test_missing_flow_session_is_not_forward_filled() -> None:
    flow, volume, sessions, master = _inputs()
    flow = flow.loc[~flow["session_date"].eq(sessions[5])].reset_index(drop=True)
    output, _ = materialize_foreign_flow_features(flow, volume, sessions, master)
    row = output.loc[output["feature_session"].eq(sessions[6])].iloc[0]
    assert pd.isna(row["foreign_net_to_volume_1"])
    assert "MISSING_FLOW_SESSION" in row["missing_reasons"]


def test_unlisted_feature_sessions_are_not_materialized() -> None:
    flow, volume, sessions, master = _inputs()
    master.loc[0, "listed_to"] = sessions[10]
    output, _ = materialize_foreign_flow_features(flow, volume, sessions, master)
    assert output["feature_session"].max() <= sessions[10]


def test_invalid_foreign_flow_lineage_fails_closed() -> None:
    flow, volume, sessions, master = _inputs()
    flow.loc[0, "foreign_net"] = 1
    with pytest.raises(ValueError, match="net identity"):
        materialize_foreign_flow_features(flow, volume, sessions, master)


def test_official_stock_summary_volume_schema_uses_regular_volume_only() -> None:
    flow, volume, sessions, master = _inputs()
    official_volume = volume.rename(columns={"date": "as_of_date", "raw_volume": "volume"})
    official_volume["as_of_date"] = official_volume["as_of_date"].astype("int64") // 10**6
    official_volume["nonregular_volume"] = 10**12
    output, summary = materialize_foreign_flow_features(
        flow, official_volume, sessions, master
    )
    row = output.loc[output["feature_session"].eq(sessions[1])].iloc[0]
    assert row["foreign_net_to_volume_1"] == pytest.approx(0.1)
    assert summary["price_columns_consumed"] == ["ticker", "date", "raw_volume"]


def test_offline_audit_writes_session_ticker_and_distribution_diagnostics(tmp_path) -> None:
    flow, volume, sessions, master = _inputs()
    output, _ = materialize_foreign_flow_features(flow, volume, sessions, master)
    audit = write_offline_audit_artifacts(output, output_root=tmp_path)
    assert audit["feature_rows"] == len(output)
    assert (tmp_path / "coverage_by_session.csv").exists()
    assert (tmp_path / "coverage_by_ticker.csv").exists()
    assert (tmp_path / "feature_distribution.csv").exists()
    assert len(pd.read_csv(tmp_path / "coverage_by_ticker.csv")) == 1
