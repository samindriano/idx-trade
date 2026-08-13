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
    assert contract["readiness"]["historical_price_path_preregistration_ready"] is True
    assert contract["readiness"]["admission_v2_ready"] is False
    assert contract["readiness"]["modeling_authorized"] is False
    assert contract["readiness"]["acquisition_authorized"] is False


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


def test_independent_activity_resolution_removes_stale_195_blocker() -> None:
    activity = load_contract()["stage1_evidence"]
    readiness = load_contract()["readiness"]

    resolution = activity["independent_activity_resolution"]
    assert resolution["resolved_rows"] == 195
    assert resolution["independent_no_trade_rows"] == 195
    assert resolution["unresolved_rows"] == 0
    assert "NonRegular" in resolution["scope"]
    assert readiness["historical_price_path_preregistration_ready"] is True
    assert readiness["admission_v2_ready"] is False


def test_readiness_validator_keeps_preregistration_and_execution_boundaries_distinct() -> None:
    contract = load_contract()
    contract["readiness"]["historical_price_path_preregistration_ready"] = False
    contract["readiness"]["modeling_authorized"] = True
    contract["readiness"]["acquisition_authorized"] = True

    errors = validate_contract(contract)

    assert "historical price-path preregistration must be marked ready" in errors
    assert "modeling must remain unauthorized in this design lane" in errors
    assert "acquisition must remain unauthorized in this design lane" in errors
