from __future__ import annotations

from idx_trade.forward_price_trend_context_bridge import produce_price_trend_state_with_context_bridge
from idx_trade.forward_price_trend_controlled_smoke import run_controlled_smoke

from test_forward_price_trend_context_anchor import _accepted_anchor_from_price_result
from test_forward_price_trend_context_bridge import _fixture


def test_controlled_smoke_runs_strict_attested_idempotent_replay(tmp_path) -> None:
    fixture = _fixture(tmp_path)
    seed = produce_price_trend_state_with_context_bridge(
        runtime_root=fixture["runtime"],
        source_session=fixture["source"],
        pins=fixture["pins"],
    )
    anchor = _accepted_anchor_from_price_result(seed, tmp_path)

    result = run_controlled_smoke(
        runtime_root=fixture["runtime"],
        source_session=fixture["source"],
        feature_session=fixture["target"],
        pins=fixture["pins"],
        anchor=anchor,
    )

    assert result["status"] == "PRICE_TREND_CONTROLLED_SMOKE_VERIFIED"
    assert result["source_session"] == "2026-08-12"
    assert result["feature_session"] == "2026-08-13"
    assert result["bridge_strict_verified"] is True
    assert result["accepted_context_attested"] is True
    assert result["idempotent_replay_verified"] is True
    assert result["target_canonical_session_required"] is False
    assert result["provider_calls"] == 0
    assert result["outcome_blind"] is True
    assert result["outcomes_or_labels_accessed"] is False
    assert result["model_fit"] is False
    assert result["model_scoring"] is False
    assert result["trade_recommendation"] is False
