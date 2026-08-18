from __future__ import annotations

import json
from pathlib import Path


def test_config_pins_complete_59_event_diagnosis() -> None:
    config = json.loads(
        Path("config/v4_3_ca_training_domain_schedule_59_ksei_news_v1.json").read_text(
            encoding="utf-8"
        )
    )
    parent = config["diagnosis_parent"]
    assert config["outcome_blind"] is True
    assert parent["manifest_sha256"] == "8c717e8f4bf7fb69edfe366cd0f219ef0c7d9f812006c409ed682eb6e9c9fb12"
    assert parent["residual_events"] == 59
    assert parent["residual_event_identity_sha256"] == "f1c587eca59a9e7ec68cb8b1b2fc0980489a8f8a1b608f10403f2cc9f6d85707"
    assert sum(parent["failure_mode_counts"].values()) == 59
    assert sum(parent["remediation_class_counts"].values()) == 59


def test_provider_is_ksei_internal_search_only() -> None:
    config = json.loads(
        Path("config/v4_3_ca_training_domain_schedule_59_ksei_news_v1.json").read_text(
            encoding="utf-8"
        )
    )
    provider = config["provider"]
    assert provider["name"] == "KSEI_PUBLIC_SITE_SEARCH_AND_NEWS"
    assert provider["base_url"] == "https://web.ksei.co.id"
    assert provider["search_path_prefix"] == "/search/results/"
    assert provider["allowed_news_path_prefix"] == "/ksei_news/read/"
    assert provider["external_search_engine"] is False
    assert provider["source_substitution"] is False
    assert provider["max_pages_per_query"] == 20


def test_runner_is_non_admissive_and_has_no_outcome_path() -> None:
    source = Path(
        "scripts/run_v4_3_ca_training_domain_schedule_59_ksei_news_acquisition.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "google.com",
        "bing.com",
        "materialize_v4_target_ledger",
        "HistGradientBoostingRegressor",
        "fit_v4_head",
        "score_v4_head",
        "TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION",
        "classify_event_with_residual_document_evidence",
        "GATE_RATE =",
    )
    for token in forbidden:
        assert token not in source
    assert '"semantic_admission_performed": False' in source
    assert '"pass_preserving_subset_selection": False' in source
    assert '"historical_target_loaded": False' in source
    assert '"model_fit": False' in source
    assert '"performance_computed": False' in source


def test_runner_refuses_output_overwrite() -> None:
    source = Path(
        "scripts/run_v4_3_ca_training_domain_schedule_59_ksei_news_acquisition.py"
    ).read_text(encoding="utf-8")
    assert "REFUSE_OVERWRITE_EXISTING_OUTPUT" in source
