from __future__ import annotations

from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "e2e-paper-cloud-orchestration.yml"
)


def test_production_workflow_dispatches_v3_and_all_phases() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "python scripts/run_e2e_paper_cloud_v3.py" in text
    assert "python scripts/run_e2e_paper_cloud_v2.py" not in text
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


def test_preopen_ca_and_preopen_have_independent_serialized_groups() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "idx-trade-e2e-paper-cloud-v3-${{" in text
    assert "'preopen-ca'" in text
    assert "'preopen'" in text
    assert "'post-eod'" in text
    assert "cancel-in-progress: false" in text
    assert "cannot queue-block the" in text


def test_schedule_resolution_explicitly_maps_preopen_ca() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert (
        '"30 1 * * 1-5"|"45 1 * * 1-5"|"55 1 * * 1-5") phase="PREOPEN_CA"'
        in text
    )
