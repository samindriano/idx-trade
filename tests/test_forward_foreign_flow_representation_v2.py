from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade.forward_foreign_flow_representation_v2 import (
    materialize_representation_v2_for_session,
)


def _inputs(days: int = 45):
    sessions = pd.date_range("2025-01-02", periods=days, freq="B")
    flow_rows: list[dict[str, object]] = []
    market_rows: list[dict[str, object]] = []
    for index, day in enumerate(sessions):
        for ticker, sign in (("AAA", 1), ("BBB", -1)):
            net = sign * (index + 1)
            flow_rows.append(
                {
                    "ticker": ticker,
                    "session_date": day,
                    "foreign_buy": 1000 + max(net, 0),
                    "foreign_sell": 1000 + max(-net, 0),
                    "foreign_net": net,
                    "unit": "SHARES",
                    "source": "IDX_OFFICIAL_STOCK_SUMMARY",
                }
            )
            close = 100.0 + index
            market_rows.append(
                {
                    "ticker": ticker,
                    "session_date": day,
                    "high": close + 2.0,
                    "low": close - 2.0,
                    "close": close,
                    "volume": 100_000.0,
                    "regular_market_value": 2_000_000_000.0,
                }
            )
    master = pd.DataFrame(
        [
            {"ticker": "AAA", "listed_from": sessions[0], "listed_to": pd.NaT},
            {"ticker": "BBB", "listed_from": sessions[0], "listed_to": pd.NaT},
        ]
    )
    return sessions, pd.DataFrame(flow_rows), pd.DataFrame(market_rows), master


def test_producer_is_causal_for_every_v2_feature_and_writes_pinned_pair(tmp_path: Path) -> None:
    sessions, flow, market, master = _inputs()
    source = sessions[34]
    target = sessions[35]
    base = materialize_representation_v2_for_session(
        flow=flow,
        market=market,
        security_master=master,
        official_sessions=sessions,
        source_session=source,
        output_directory=tmp_path,
        input_provenance={"calendar_sha256": "c" * 64, "source_sha256": "s" * 64},
    )
    artifact = Path(base["artifact_path"])
    manifest = Path(base["manifest_path"])
    before = artifact.read_bytes()
    before_frame = pd.read_parquet(artifact)

    changed = flow.copy()
    changed.loc[
        changed["session_date"].eq(target), ["foreign_buy", "foreign_sell", "foreign_net"]
    ] = [999999, 1, 999998]
    changed_market = market.copy()
    changed_market.loc[changed_market["session_date"].eq(target), "close"] = 9999.0
    second_dir = tmp_path / "second"
    materialize_representation_v2_for_session(
        flow=changed,
        market=changed_market,
        security_master=master,
        official_sessions=sessions,
        source_session=source,
        output_directory=second_dir,
        input_provenance={"calendar_sha256": "c" * 64, "source_sha256": "s" * 64},
    )
    after_frame = pd.read_parquet(second_dir / "foreign_flow_representation_v2.parquet")
    pd.testing.assert_frame_equal(before_frame, after_frame, check_dtype=False, check_exact=True)
    assert before == artifact.read_bytes()
    saved = json.loads(manifest.read_text(encoding="utf-8"))
    assert saved["status"] == "FOREIGN_FLOW_REPRESENTATION_V2_FORWARD_READY"
    assert saved["artifact_sha256"] == base["artifact_sha256"]
    assert saved["outcome_blind"] is True
    assert saved["provider_calls"] == 0
    assert saved["flow_through_session"] == source.date().isoformat()
    assert (before_frame["feature_session"] == target).all()
    assert (before_frame["flow_through_session"] == sessions[34]).all()


def test_producer_reuses_existing_pair_without_overwrite(tmp_path: Path) -> None:
    sessions, flow, market, master = _inputs()
    source = sessions[34]
    kwargs = dict(
        flow=flow,
        market=market,
        security_master=master,
        official_sessions=sessions,
        source_session=source,
        output_directory=tmp_path,
        input_provenance={"calendar_sha256": "c" * 64, "source_sha256": "s" * 64},
    )
    first = materialize_representation_v2_for_session(**kwargs)
    artifact = Path(first["artifact_path"])
    manifest = Path(first["manifest_path"])
    artifact_bytes = artifact.read_bytes()
    manifest_bytes = manifest.read_bytes()
    second = materialize_representation_v2_for_session(**kwargs)
    assert first["artifact_sha256"] == second["artifact_sha256"]
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert not second["created"]
    assert artifact.read_bytes() == artifact_bytes
    assert manifest.read_bytes() == manifest_bytes


def test_producer_fails_closed_when_causal_or_target_evidence_is_missing(tmp_path: Path) -> None:
    sessions, flow, market, master = _inputs()
    source = sessions[34]
    with pytest.raises(RuntimeError, match="source canonical Foreign Flow"):
        materialize_representation_v2_for_session(
            flow=flow.loc[flow["session_date"].ne(source)],
            market=market,
            security_master=master,
            official_sessions=sessions,
            source_session=source,
            output_directory=tmp_path / "missing-flow",
            input_provenance={},
        )
    with pytest.raises(RuntimeError, match="source canonical market"):
        materialize_representation_v2_for_session(
            flow=flow,
            market=market.loc[market["session_date"].ne(source)],
            security_master=master,
            official_sessions=sessions,
            source_session=source,
            output_directory=tmp_path / "missing-market",
            input_provenance={},
        )


def test_producer_succeeds_without_any_feature_session_market_or_flow_rows(tmp_path: Path) -> None:
    sessions, flow, market, master = _inputs()
    source = sessions[34]
    target = sessions[35]
    no_target_flow = flow.loc[flow["session_date"].ne(target)].copy()
    no_target_market = market.loc[market["session_date"].ne(target)].copy()
    result = materialize_representation_v2_for_session(
        flow=no_target_flow,
        market=no_target_market,
        security_master=master,
        official_sessions=sessions,
        source_session=source,
        output_directory=tmp_path,
        input_provenance={"calendar_sha256": "c" * 64, "source_sha256": "s" * 64},
    )
    output = pd.read_parquet(result["artifact_path"])
    assert result["created"] is True
    assert (output["feature_session"] == target).all()
    assert (output["flow_through_session"] == source).all()
