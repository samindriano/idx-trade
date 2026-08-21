from pathlib import Path

from idx_trade.decision_v2_failure_diagnosis_contract import (
    EXPECTED_PREREG_CANONICAL_SHA256,
    verify_failure_diagnosis_prereg,
)


def test_failure_diagnosis_prereg_is_canonical_sha_pinned() -> None:
    path = verify_failure_diagnosis_prereg(Path("."))
    assert path.name == "decision_v2_failure_mechanism_diagnosis_v1.json"
    assert len(EXPECTED_PREREG_CANONICAL_SHA256) == 64
