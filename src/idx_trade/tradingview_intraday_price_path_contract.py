"""Frozen semantic contract for a possible TradingView IDX price-path lane.

This module is intentionally descriptive and validation-only. It does not
download data, create a panel, fit a model, or transform provider prices.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


CONTRACT_PATH = Path(__file__).resolve().parents[2] / "config" / "tradingview_intraday_price_path_contract_v1.json"


REQUIRED_FIELD_NAMES = {
    "official_open",
    "tv_regular_open",
    "tv_intraday_hlc",
    "tv_intraday_volume",
}


REQUIRED_FEATURE_NAMES = {
    "official_open_to_first_hour_close_return",
    "tv_regular_open_to_first_hour_close_return",
    "intraday_range",
    "path_volatility",
    "mae_mfe",
    "drawdown",
    "hlc_path",
    "volume_path",
    "regular_first_bar_movement",
}


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    """Load the checked-in contract without any external/runtime inputs."""

    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(contract: Mapping[str, Any]) -> list[str]:
    """Return deterministic contract violations; an empty list means valid."""

    errors: list[str] = []
    fields = contract.get("semantic_fields", {})
    features = contract.get("permitted_feature_families", {})
    provider = contract.get("provider_lineage", {})
    readiness = contract.get("readiness", {})

    missing_fields = REQUIRED_FIELD_NAMES - set(fields)
    if missing_fields:
        errors.append(f"missing semantic fields: {sorted(missing_fields)}")
    missing_features = REQUIRED_FEATURE_NAMES - set(features)
    if missing_features:
        errors.append(f"missing feature families: {sorted(missing_features)}")

    if fields.get("official_open", {}).get("overwrite_allowed") is not False:
        errors.append("official_open must not be overwriteable")
    if fields.get("tv_regular_open", {}).get("overwrite_official_open") is not False:
        errors.append("tv_regular_open must not overwrite official_open")
    if provider.get("session") != "regular":
        errors.append("primary provider session must be regular")
    if provider.get("adjustment") != "none":
        errors.append("provider adjustment must be none")
    if provider.get("price_semantics") != "raw OHLCV":
        errors.append("provider price semantics must be raw OHLCV")
    if readiness.get("semantic_contract_ready") is not True:
        errors.append("semantic contract must be marked ready")
    if readiness.get("historical_price_path_preregistration_ready") is not True:
        errors.append("historical price-path preregistration must be marked ready")
    if readiness.get("admission_v2_ready") is not False:
        errors.append("admission V2 must remain closed in this design lane")
    if readiness.get("modeling_authorized") is not False:
        errors.append("modeling must remain unauthorized in this design lane")
    if readiness.get("acquisition_authorized") is not False:
        errors.append("acquisition must remain unauthorized in this design lane")

    prohibited = contract.get("prohibited_semantics", [])
    required_prohibited = {
        "treat tv_regular_open as the official opening auction",
        "overwrite official_open with tv_regular_open",
        "arbitrary repaired or synthesized Open",
        "opening-auction microstructure feature without an actual auction source/flag",
        "using dividends, Adj Close, or inferred split ratios to repair raw OHLC",
        "rescaling provider volume to force canonical parity",
        "converting missing or ambiguous activity evidence into NO_TRADE",
    }
    missing_prohibited = required_prohibited - set(prohibited)
    if missing_prohibited:
        errors.append(f"missing prohibited semantics: {sorted(missing_prohibited)}")

    return errors


def contract_is_valid(path: Path = CONTRACT_PATH) -> bool:
    """Return whether the checked-in semantic contract passes validation."""

    return not validate_contract(load_contract(path))
