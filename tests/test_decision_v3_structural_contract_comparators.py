from __future__ import annotations

import json
from pathlib import Path

from idx_trade.decision_v3_structural_replay import (
    EXPECTED_DECISION_V1_REPLACEMENTS,
    EXPECTED_DECISION_V2_PLAN_DIGEST,
    EXPECTED_DECISION_V2_REPLACEMENTS,
    EXPECTED_DECISION_V2_RESULT_MANIFEST_SHA256,
)
from idx_trade.decision_v3_structural_source import (
    EXPECTED_NAIVE_TOP10_REPLACEMENTS,
    REPLAY_CONTRACT_RELATIVE_PATH,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_replay_comparator_lineage_is_exactly_frozen() -> None:
    payload = json.loads(
        (REPO_ROOT / REPLAY_CONTRACT_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    comparators = payload["comparators"]
    assert comparators["naive_exact_daily_top10_replacements"] == (
        EXPECTED_NAIVE_TOP10_REPLACEMENTS
    )
    assert comparators["decision_v1_replacements"] == EXPECTED_DECISION_V1_REPLACEMENTS
    assert comparators["decision_v2_replacements"] == EXPECTED_DECISION_V2_REPLACEMENTS
    assert comparators["decision_v2_result_manifest_sha256"] == (
        EXPECTED_DECISION_V2_RESULT_MANIFEST_SHA256
    )
    assert comparators["decision_v2_plan_digest"] == EXPECTED_DECISION_V2_PLAN_DIGEST
