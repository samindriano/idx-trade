from __future__ import annotations

import pytest

from idx_trade.e2e_paper_cloud_runtime_v1 import CloudPaperRuntimeError
from scripts import run_e2e_paper_cloud_v1 as cloud_runner


@pytest.mark.parametrize("controller_status", ["EXECUTION_COMPLETE", "ALREADY_COMPLETE"])
def test_terminal_preopen_requires_cloud_admission(controller_status: str) -> None:
    with pytest.raises(
        CloudPaperRuntimeError,
        match="CLOUD_E2E_PREOPEN_TERMINAL_WITHOUT_OFFICIAL_OPEN_ADMISSION",
    ):
        cloud_runner._require_terminal_preopen_admission(
            stage="PREOPEN",
            controller_status=controller_status,
            official_open_admission=None,
        )


def test_missed_preopen_may_have_no_cloud_admission() -> None:
    cloud_runner._require_terminal_preopen_admission(
        stage="PREOPEN",
        controller_status="MISSED_EXECUTION_NO_CERTIFIED_OPEN",
        official_open_admission=None,
    )


def test_post_eod_is_not_subject_to_preopen_admission_guard() -> None:
    cloud_runner._require_terminal_preopen_admission(
        stage="POST_EOD",
        controller_status="POST_EOD_PREPARED",
        official_open_admission=None,
    )
