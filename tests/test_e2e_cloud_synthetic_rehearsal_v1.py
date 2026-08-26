from __future__ import annotations

import pytest

from scripts import run_e2e_cloud_synthetic_rehearsal_v1 as rehearsal


def test_rehearsal_prefix_requires_unique_isolated_child() -> None:
    value = rehearsal._safe_rehearsal_prefix(
        "e2e-paper-synthetic-rehearsal-v1/12345-1"
    )
    assert value == "e2e-paper-synthetic-rehearsal-v1/12345-1"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "e2e-paper-synthetic-rehearsal-v1",
        "e2e-paper-v1/rehearsal",
        "official-open-v1/rehearsal",
        "other-prefix/run-1",
        "e2e-paper-synthetic-rehearsal-v1/../e2e-paper-v1",
    ],
)
def test_rehearsal_prefix_rejects_nonisolated_paths(value: str) -> None:
    with pytest.raises(rehearsal.RehearsalError):
        rehearsal._safe_rehearsal_prefix(value)


def test_rehearsal_requires_manual_github_actions_dispatch() -> None:
    assert rehearsal._require_cloud_dispatch(
        {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ID": "12345",
            "GITHUB_RUN_ATTEMPT": "2",
        }
    ) == ("12345", "2")


@pytest.mark.parametrize(
    "env",
    [
        {},
        {
            "GITHUB_ACTIONS": "false",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ID": "1",
            "GITHUB_RUN_ATTEMPT": "1",
        },
        {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "schedule",
            "GITHUB_RUN_ID": "1",
            "GITHUB_RUN_ATTEMPT": "1",
        },
        {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ID": "not-a-number",
            "GITHUB_RUN_ATTEMPT": "1",
        },
    ],
)
def test_rehearsal_rejects_nonmanual_or_unidentified_execution(
    env: dict[str, str],
) -> None:
    with pytest.raises(rehearsal.RehearsalError):
        rehearsal._require_cloud_dispatch(env)


def test_production_input_manifest_pin_is_frozen() -> None:
    rehearsal._require_expected_manifest_sha(
        rehearsal.EXPECTED_INPUT_MANIFEST_SHA256,
        rehearsal.EXPECTED_INPUT_MANIFEST_SHA256,
    )
    with pytest.raises(
        rehearsal.RehearsalError,
        match="REHEARSAL_EXPECTED_INPUT_MANIFEST_PIN_CHANGED",
    ):
        rehearsal._require_expected_manifest_sha(
            rehearsal.EXPECTED_INPUT_MANIFEST_SHA256,
            "0" * 64,
        )
    with pytest.raises(
        rehearsal.RehearsalError,
        match="REHEARSAL_PRODUCTION_INPUT_MANIFEST_SHA_MISMATCH",
    ):
        rehearsal._require_expected_manifest_sha(
            "1" * 64,
            rehearsal.EXPECTED_INPUT_MANIFEST_SHA256,
        )


def test_rehearsal_contract_keeps_production_prefixes_distinct() -> None:
    assert rehearsal.REHEARSAL_ROOT_PREFIX != rehearsal.PRODUCTION_INPUT_PREFIX
    assert rehearsal.PRODUCTION_INPUT_PREFIX in rehearsal.RESERVED_WRITE_PREFIXES
    assert "official-open-v1" in rehearsal.RESERVED_WRITE_PREFIXES
