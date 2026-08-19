from __future__ import annotations

import json
from pathlib import Path


def test_adjudication_config_pins_observed_acquisition() -> None:
    config = json.loads(
        Path(
            "config/v4_3_ca_training_domain_schedule_59_ksei_news_adjudication_v1.json"
        ).read_text(encoding="utf-8")
    )
    parent = config["acquisition_parent"]
    assert parent["manifest_sha256"] == "96c11caa6ed728cbd19af8f13cc30bedde45c04e7a256e6d0c9a591dd62fc7d1"
    assert parent["residual_events"] == 59
    assert parent["events_with_ksei_news_candidate"] == 56
    assert parent["events_without_ksei_news_candidate"] == 3
    assert parent["successful_raw_response_identity_sha256"] == (
        "45132e0b5ae17b74ee005c55d26ddb464bdd5bb692b4a3a62d6649189f7ff7a8"
    )


def test_adjudication_contract_remains_offline_and_fail_closed() -> None:
    config = json.loads(
        Path(
            "config/v4_3_ca_training_domain_schedule_59_ksei_news_adjudication_v1.json"
        ).read_text(encoding="utf-8")
    )
    contract = config["adjudication_contract"]
    assert contract["mechanical_source_date_linkage_required"] is True
    assert contract["explicit_regular_market_transition_required"] is True
    assert contract["record_or_distribution_dates_are_linkage_only"] is True
    assert contract["conflicts_fail_closed"] is True
    for value in config["hard_boundaries"].values():
        assert value is False


def test_runner_has_no_provider_target_model_or_performance_path() -> None:
    source = Path(
        "scripts/run_v4_3_ca_training_domain_schedule_59_ksei_news_offline_adjudication.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "curl_cffi",
        "requests.get",
        "urllib.request",
        "capture_request(",
        "materialize_v4_target_ledger",
        "HistGradientBoostingRegressor",
        "fit_v4_head",
        "score_v4_head",
    )
    for token in forbidden:
        assert token not in source


def test_runner_uses_hardened_parser_and_exact_resolver() -> None:
    source = Path(
        "scripts/run_v4_3_ca_training_domain_schedule_59_ksei_news_offline_adjudication.py"
    ).read_text(encoding="utf-8")
    assert "parse_residual_document_hardened" in source
    assert "resolve_event_document_evidence" in source
    assert "event_inventory_identity" in source
