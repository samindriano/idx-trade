from __future__ import annotations

from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "e2e-paper-cloud-orchestration.yml"
)


def test_production_workflow_dispatches_v4_and_all_phases() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "python scripts/run_e2e_paper_cloud_v4.py" in text
    assert "python scripts/run_e2e_paper_cloud_v3.py" not in text
    assert "options: [auto, PREOPEN_CA, PREOPEN, POST_EOD]" in text
    assert '"30 1 * * 1-5"' in text
    assert '"45 1 * * 1-5"' in text
    assert '"55 1 * * 1-5"' in text
    assert '"3 2 * * 1-5"' in text
    assert '"13 2 * * 1-5"' in text
    assert '"22 2 * * 1-5"' in text
    assert '"35 11 * * 1-5"' in text
    assert '"5 12 * * 1-5"' in text
    assert '"35 12 * * 1-5"' in text


def test_recovery_attempts_are_not_workflow_serialized() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "\nconcurrency:\n" not in text
    assert "no workflow-level concurrency group" in text
    assert "must never queue-block" in text
    assert "conditional immutable R2 stage/checkpoint commit" in text


def test_schedule_resolution_explicitly_maps_preopen_ca() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert (
        '"30 1 * * 1-5"|"45 1 * * 1-5"|"55 1 * * 1-5") phase="PREOPEN_CA"'
        in text
    )
