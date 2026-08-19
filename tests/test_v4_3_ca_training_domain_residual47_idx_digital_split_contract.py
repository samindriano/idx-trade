from __future__ import annotations

import json
from pathlib import Path


CONFIG = Path("config/v4_3_ca_training_domain_residual47_idx_digital_split_v1.json")
ACQ = Path("scripts/run_v4_3_ca_training_domain_residual47_idx_digital_split_acquisition.py")
ADJ = Path("scripts/run_v4_3_ca_training_domain_residual47_idx_digital_split_offline_adjudication.py")


def test_config_pins_parent_and_keeps_firewall() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["parent_combined_replay"]["manifest_sha256"] == (
        "12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43"
    )
    assert cfg["parent_combined_replay"]["remaining_schedule_events"] == 47
    assert cfg["provider"]["url_name"] == "LINK_STOCK_SPLIT"
    assert cfg["adjudication"]["accepted_transition_semantic"] == (
        "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"
    )
    assert cfg["official_calendar"]["filename"] == "official_exchange_sessions_1260.csv"
    assert cfg["official_calendar"]["sha256"] == (
        "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
    )
    for value in cfg["hard_boundaries"].values():
        assert value is False


def test_acquisition_never_admits_semantics_or_targets() -> None:
    source = ACQ.read_text(encoding="utf-8")
    assert '"semantic_admission_performed": False' in source
    assert '"historical_target_loaded": False' in source
    assert '"model_fit": False' in source
    assert "HistGradientBoostingRegressor" not in source


def test_adjudication_is_offline_and_requires_manifest_sha() -> None:
    source = ADJ.read_text(encoding="utf-8")
    assert "--expected-acquisition-manifest-sha" in source
    assert '"network_calls": False' in source
    assert '"provider_calls": False' in source
    assert "curl_cffi" not in source
    assert "requests.get" not in source


def test_adjudication_does_not_promote_source_date_to_transition() -> None:
    source = ADJ.read_text(encoding="utf-8")
    assert "listing_date_linked" in source
    assert 'transition_date = distinct_dates[0]' in source
    assert 'event.get("source_dates")' in source
