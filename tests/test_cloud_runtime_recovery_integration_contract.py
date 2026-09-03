from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
OPEN_WORKFLOW = ROOT / ".github" / "workflows" / "official-open-prospective-cloud-capture.yml"
E2E_WORKFLOW = ROOT / ".github" / "workflows" / "e2e-paper-cloud-orchestration.yml"

OPEN_PIN = "ac29a0552b1785045906f8d608b5371d93e01b73"
E2E_PIN = "8bc3ee3efd65e8b16478e404e4b226451b105c48"


def _cron_values(text: str) -> list[str]:
    return re.findall(r'^\s*- cron: "([^"]+)"\s*$', text, flags=re.MULTILINE)


def test_official_open_recovery_wrapper_is_exactly_pinned_and_attested():
    text = OPEN_WORKFLOW.read_text(encoding="utf-8")

    assert f"OFFICIAL_OPEN_CAPTURE_CODE_REF: {OPEN_PIN}" in text
    assert "python scripts/run_official_open_cloud_capture_v3.py" in text
    assert "python scripts/run_official_open_cloud_capture_v1.py" not in text
    assert 'test "$(git rev-parse HEAD)" = "$OFFICIAL_OPEN_CAPTURE_CODE_REF"' in text

    for input_name in (
        "scheduler_issued_at:",
        "scheduler_nonce:",
        "scheduler_signature:",
    ):
        assert input_name in text
    assert "OFFICIAL_OPEN_SCHEDULER_ISSUED_AT: ${{ inputs.scheduler_issued_at || '' }}" in text
    assert "OFFICIAL_OPEN_SCHEDULER_NONCE: ${{ inputs.scheduler_nonce || '' }}" in text
    assert "OFFICIAL_OPEN_SCHEDULER_SIGNATURE: ${{ inputs.scheduler_signature || '' }}" in text
    assert "OFFICIAL_OPEN_SCHEDULER_HMAC_KEY: ${{ secrets.OFFICIAL_OPEN_SCHEDULER_HMAC_KEY }}" in text

    assert _cron_values(text) == [
        "2 2 * * 1-5",
        "12 2 * * 1-5",
        "22 2 * * 1-5",
    ]
    assert "timeout-minutes: 10" in text
    assert "OFFICIAL_OPEN_STORAGE_PREFIX: official-open-v1" in text
    assert "\nconcurrency:\n" not in text
    assert "conditional immutable slot_manifest.json commit" in text


def test_e2e_recovery_wrapper_is_exactly_pinned_to_matching_open_producer():
    text = E2E_WORKFLOW.read_text(encoding="utf-8")

    assert f"E2E_CLOUD_IMPLEMENTATION_REF: {E2E_PIN}" in text
    assert f"E2E_CLOUD_EXPECTED_OFFICIAL_OPEN_CAPTURE_CODE_REF: {OPEN_PIN}" in text
    assert "python scripts/run_e2e_paper_cloud_v4.py" in text
    assert "python scripts/run_e2e_paper_cloud_v3.py" not in text
    assert 'test "$(git rev-parse HEAD)" = "$E2E_CLOUD_IMPLEMENTATION_REF"' in text

    assert _cron_values(text) == [
        "30 1 * * 1-5",
        "45 1 * * 1-5",
        "55 1 * * 1-5",
        "3 2 * * 1-5",
        "13 2 * * 1-5",
        "22 2 * * 1-5",
        "35 11 * * 1-5",
        "5 12 * * 1-5",
        "35 12 * * 1-5",
    ]
    assert "timeout-minutes: 90" in text
    assert "E2E_CLOUD_STORAGE_PREFIX: e2e-paper-v1" in text
    assert "E2E_CLOUD_OFFICIAL_OPEN_PREFIX: official-open-v1" in text
    assert "E2E_CLOUD_PROVIDER_COMMIT: 75d6c0f74fa360d225794c70c383348977de6798" in text
    assert "\nconcurrency:\n" not in text
    assert "conditional immutable R2 stage/checkpoint commit" in text
