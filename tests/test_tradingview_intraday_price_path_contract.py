from __future__ import annotations

from idx_trade.tradingview_intraday_price_path_contract import (
    load_contract,
    validate_contract,
)


def test_frozen_contract_is_structurally_valid() -> None:
    contract = load_contract()

    assert validate_contract(contract) == []
    assert contract["status"] == "FROZEN_SEMANTICS_DESIGN_ONLY"
    assert contract["readiness"]["semantic_contract_ready"] is True
    assert contract["readiness"]["admission_v2_ready"] is False


def test_official_and_provider_opens_are_distinct_non_overwriting_fields() -> None:
    fields = load_contract()["semantic_fields"]

    assert fields["official_open"]["role"] == "canonical_open_reference"
    assert fields["official_open"]["overwrite_allowed"] is False
    assert fields["tv_regular_open"]["role"] == "provider_path_observation"
    assert fields["tv_regular_open"]["overwrite_official_open"] is False


def test_provider_contract_is_raw_regular_session_only() -> None:
    provider = load_contract()["provider_lineage"]

    assert provider["session"] == "regular"
    assert provider["adjustment"] == "none"
    assert provider["price_semantics"] == "raw OHLCV"
    assert provider["symbol_format"] == "IDX:<ticker>"


def test_safe_features_keep_canonical_and_provider_anchors_explicit() -> None:
    features = load_contract()["permitted_feature_families"]

    assert features["official_open_to_first_hour_close_return"]["anchor"] == "official_open"
    assert features["tv_regular_open_to_first_hour_close_return"]["anchor"] == "tv_regular_open"
    assert "never an official-auction return" in features["tv_regular_open_to_first_hour_close_return"]["meaning"]
    assert features["regular_first_bar_movement"]["anchor"] == "tv_regular_open"


def test_auction_and_repair_shortcuts_are_prohibited() -> None:
    prohibited = set(load_contract()["prohibited_semantics"])

    assert "treat tv_regular_open as the official opening auction" in prohibited
    assert "arbitrary repaired or synthesized Open" in prohibited
    assert "nearest-OHLC correction or nearest-timestamp alignment" in prohibited
    assert "opening-auction microstructure feature without an actual auction source/flag" in prohibited
    assert "using dividends, Adj Close, or inferred split ratios to repair raw OHLC" in prohibited
    assert "converting missing or ambiguous activity evidence into NO_TRADE" in prohibited


def test_stage1_activity_conflict_remains_fail_closed() -> None:
    activity = load_contract()["stage1_evidence"]
    readiness = load_contract()["readiness"]

    assert activity["canonical_checkpoint_activity_status"]["uncertain_sessions"] == 195
    assert activity["unverified_task_claim_not_promoted"]["status"] == "NOT_PRESENT_IN_CURRENT_CANONICAL_CHECKPOINT"
    assert readiness["admission_v2_ready"] is False
