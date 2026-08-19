from __future__ import annotations

import json
from pathlib import Path


def test_adjudication_output_identity_is_full_residual_59() -> None:
    config = json.loads(
        Path(
            "config/v4_3_ca_training_domain_schedule_59_ksei_news_adjudication_v1.json"
        ).read_text(encoding="utf-8")
    )
    assert config["acquisition_parent"]["residual_events"] == 59
    assert config["acquisition_parent"]["residual_event_identity_sha256"] == (
        "f1c587eca59a9e7ec68cb8b1b2fc0980489a8f8a1b608f10403f2cc9f6d85707"
    )


def test_no_post_result_scope_or_semantic_relaxation() -> None:
    config = json.loads(
        Path(
            "config/v4_3_ca_training_domain_schedule_59_ksei_news_adjudication_v1.json"
        ).read_text(encoding="utf-8")
    )
    hard = config["hard_boundaries"]
    assert hard["pass_preserving_subset_selection"] is False
    assert hard["parser_or_semantic_relaxation_after_observed_corpus"] is False
    assert hard["fuzzy_event_matching"] is False
    assert hard["record_or_distribution_date_as_transition"] is False
