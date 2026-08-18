from __future__ import annotations

import json
from pathlib import Path


def test_adjudication_config_pins_observed_acquisition_result() -> None:
    config = json.loads(
        Path("config/v4_3_ca_training_domain_schedule_80_adjudication_v1.json").read_text(
            encoding="utf-8"
        )
    )
    parent = config["acquisition_parent"]
    assert parent["manifest_sha256"] == "a7b10ded6246102d6d7858546fdb955ad426bf9a18f762239245a7253f801765"
    assert parent["schedule_event_count"] == 80
    assert parent["events_with_candidate_documents"] == 74
    assert parent["events_without_candidate_documents"] == 6
    assert parent["candidate_documents"] == 89
    assert parent["provider_failed_documents"] == 0
    assert parent["successful_raw_response_identity_sha256"] == (
        "2f83dfa2753fd9ea2eec2d20f5720f036ac71c628a2d495b88b2f4a0f7dd57a3"
    )


def test_adjudication_contract_keeps_transition_and_linkage_separate() -> None:
    config = json.loads(
        Path("config/v4_3_ca_training_domain_schedule_80_adjudication_v1.json").read_text(
            encoding="utf-8"
        )
    )
    contract = config["adjudication_contract"]
    assert contract["mechanical_source_date_linkage_required"] is True
    assert contract["record_or_distribution_dates_are_linkage_only"] is True
    assert contract["explicit_regular_market_transition_required"] is True
    assert contract["transition_must_be_official_session"] is True
    assert contract["conflicts_fail_closed"] is True


def test_adjudication_contract_is_offline_and_outcome_blind() -> None:
    config = json.loads(
        Path("config/v4_3_ca_training_domain_schedule_80_adjudication_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert config["outcome_blind"] is True
    hard = config["hard_boundaries"]
    for key in (
        "network_calls",
        "provider_calls",
        "source_substitution",
        "new_document_discovery",
        "fuzzy_event_matching",
        "price_inference",
        "record_or_distribution_date_as_transition",
        "pass_preserving_subset_selection",
        "target_or_rank_materialization",
        "historical_target_loaded",
        "model_fit",
        "prediction",
        "performance",
        "protected_forward_access",
    ):
        assert hard[key] is False
