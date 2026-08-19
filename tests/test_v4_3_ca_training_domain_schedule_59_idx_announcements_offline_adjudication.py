from __future__ import annotations

import json
from pathlib import Path


RUNNER = Path("scripts/run_v4_3_ca_training_domain_schedule_59_idx_announcements_offline_adjudication.py")


def test_adjudication_requires_explicit_acquisition_manifest_sha() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "--expected-acquisition-manifest-sha" in source
    assert "ACQUISITION_MANIFEST_SHA_MISMATCH" in source


def test_adjudication_uses_only_frozen_hardened_semantics() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "parse_residual_document_hardened" in source
    assert "resolve_event_document_evidence" in source
    forbidden = (
        "curl_cffi",
        "requests.get",
        "urllib.request",
        "materialize_v4_target_ledger",
        "HistGradientBoostingRegressor",
        "fit_v4_head(",
        "score_v4_head(",
    )
    for token in forbidden:
        assert token not in source


def test_config_keeps_original_scientific_firewall() -> None:
    config = json.loads(
        Path("config/v4_3_ca_training_domain_schedule_59_idx_adjudication_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert config["residual_events"] == 59
    assert config["acquisition_manifest_sha_required_via_cli"] is True
    assert config["official_calendar"]["sha256"] == (
        "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
    )
    for value in config["hard_boundaries"].values():
        assert value is False


def test_existing_output_is_refused_before_acquisition_read() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    main_start = source.index("def main()")
    refusal = source.index("REFUSE_OVERWRITE_EXISTING_OUTPUT", main_start)
    verification = source.index("verify_acquisition_root(", main_start)
    assert refusal < verification
