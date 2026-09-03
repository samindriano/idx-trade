from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = REPO_ROOT / ".github" / "workflows"

SCHEDULES = {
    "e2e-paper-cloud-orchestration.yml": [
        "30 1 * * 1-5",
        "45 1 * * 1-5",
        "55 1 * * 1-5",
        "3 2 * * 1-5",
        "13 2 * * 1-5",
        "22 2 * * 1-5",
        "35 11 * * 1-5",
        "5 12 * * 1-5",
        "35 12 * * 1-5",
    ],
    "official-open-prospective-cloud-capture.yml": [
        "2 2 * * 1-5",
        "12 2 * * 1-5",
        "22 2 * * 1-5",
    ],
    "stockbit-stream-prospective-capture.yml": [
        "47 1 * * *",
        "7 5 * * *",
        "47 9 * * *",
    ],
    "stockbit-intraday-cloud-production.yml": [
        "30 11 * * 1-5",
        "30 12 * * 1-5",
        "30 13 * * 1-5",
    ],
}


def _workflow_text(name: str) -> str:
    return (WORKFLOW_ROOT / name).read_text(encoding="utf-8")


def _cron_values(text: str) -> list[str]:
    return re.findall(r'^\s+- cron:\s*["\']([^"\']+)["\']', text, flags=re.MULTILINE)


def test_production_schedules_are_unchanged_and_complete() -> None:
    for name, expected in SCHEDULES.items():
        assert _cron_values(_workflow_text(name)) == expected


def test_capture_bootstraps_do_not_upgrade_pip_or_install_unused_dev_tools() -> None:
    for name in SCHEDULES:
        text = _workflow_text(name)
        assert "pip install --upgrade pip" not in text
    stream = _workflow_text("stockbit-stream-prospective-capture.yml")
    assert 'python -m pip install -e ".[archive]"' in stream
    assert ".[dev,archive]" not in stream


def test_e2e_retains_required_uv_bootstrap() -> None:
    text = _workflow_text("e2e-paper-cloud-orchestration.yml")
    assert "astral-sh/setup-uv@v5" in text
    assert "Setup uv" in text


def test_docs_only_ci_filter_and_stale_head_cancellation_are_explicit() -> None:
    text = _workflow_text("tests.yml")
    assert text.count("paths-ignore:") == 2
    assert text.count("'coordination/TEAM_STATUS.md'") == 2
    assert "'**/*.md'" not in text
    assert "'docs/**'" not in text
    assert "'coordination/**'" not in text
    assert (
        "group: tests-${{ github.workflow }}-"
        "${{ github.event.pull_request.number || github.ref }}"
    ) in text
    assert "cancel-in-progress: true" in text


def test_narrow_coordination_filter_keeps_authority_docs_in_ci() -> None:
    ignored = "coordination/TEAM_STATUS.md"

    def workflow_runs(paths: list[str]) -> bool:
        return any(path != ignored for path in paths)

    assert not workflow_runs(["coordination/TEAM_STATUS.md"])
    assert workflow_runs(["coordination/PROJECT_ROADMAP.md"])
    assert workflow_runs(["docs/README.md"])
    assert workflow_runs(["docs/checkpoints/2026-08-24_V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1.md"])
    assert workflow_runs(["src/idx_trade/data.py"])
    assert workflow_runs([".github/workflows/tests.yml"])


def test_frozen_protocol_change_is_not_ignored_by_ci() -> None:
    text = _workflow_text("tests.yml")
    assert "docs/checkpoints/2026-08-24_V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1.md" not in text
    assert "paths-ignore:" in text


def test_intraday_complete_archive_preflight_skips_expensive_capture_bootstrap() -> None:
    text = _workflow_text("stockbit-intraday-cloud-production.yml")
    check = text.index("Validate existing archive before capture bootstrap")
    capture = text.index("  capture:")
    accepted = text.index("Checkout accepted E2E runtime bridge")
    archive_check = text.index("scripts/check_stockbit_intraday_completion.py")
    setup = text.index("uses: actions/setup-python@v5")
    provider = text.index("ZAPI_API_KEY:", capture)

    assert text.count("  capture:") == 1
    assert "  completion_check:" not in text
    assert check < archive_check < accepted < setup < provider
    assert "needs: completion_check" not in text
    assert "if: steps.archive_check.outputs.complete != 'true'" in text
    assert "AWS_ACCESS_KEY_ID: ${{ secrets.R2_ACCESS_KEY_ID }}" in text
    assert "AWS_SECRET_ACCESS_KEY: ${{ secrets.R2_SECRET_ACCESS_KEY }}" in text


def test_stream_remains_outside_cloudflare_completion_redundancy() -> None:
    scheduler = (REPO_ROOT / "infra" / "cloudflare_github_scheduler" / "src" / "core.mjs").read_text(encoding="utf-8")
    assert "stockbit-stream-prospective-capture.yml" not in scheduler
