from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .decision_v3_structural_source import (
    DecisionV3StructuralReplayError,
    EXPECTED_SCORE_ROWS,
    EXPECTED_SCORE_SESSIONS,
    EXPECTED_SOURCE_MANIFEST_SHA256,
    EXPECTED_SOURCE_SCORE_SHA256,
    canonical_json_sha256,
)
from .v4_x1_decision_v4_refill_decoupling import (
    V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1,
)

PREREG_RELATIVE_PATH = Path("docs/specs/decision_v4_refill_decoupling_v1.json")
EXPECTED_PREREG_CANONICAL_SHA256 = (
    "aa8763bdebf7b3334016a651d0376b17d6c6d7aa3a2c2356bf126fd5de8396f7"
)
EXPECTED_RULE_ID = "V4_X1_DECISION_V4_REFILL_DECOUPLING_V1"
EXPECTED_ACCEPT_VERDICT = "DECISION_V4_REFILL_DECOUPLING_V1_STRUCTURAL_ACCEPT"
EXPECTED_REJECT_VERDICT = "DECISION_V4_REFILL_DECOUPLING_V1_STRUCTURAL_REJECT"

REQUIRED_DIAGNOSTICS = (
    "severe_exit_session_count",
    "tier_a_vacancy_fills_on_severe_sessions",
    "tier_b_candidates_blocked_on_severe_sessions",
    "tier_c_candidates_blocked_on_severe_sessions",
    "underfilled_sessions_after_severity_conditioned_refill",
    "vacancy_days_after_severity_conditioned_refill",
    "block_1_to_6_churn_quality_capacity_summary",
)


def _fail(code: str) -> None:
    raise DecisionV3StructuralReplayError(code)


def verify_frozen_v4_preregistration(
    repo_root: str | Path,
) -> tuple[Path, dict[str, Any]]:
    path = Path(repo_root).expanduser().resolve() / PREREG_RELATIVE_PATH
    if not path.is_file():
        _fail(f"DECISION_V4_REPLAY_PREREG_MISSING:{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3StructuralReplayError(
            "DECISION_V4_REPLAY_PREREG_INVALID_JSON"
        ) from exc
    if not isinstance(payload, dict):
        _fail("DECISION_V4_REPLAY_PREREG_NOT_OBJECT")

    actual = canonical_json_sha256(payload)
    if actual != EXPECTED_PREREG_CANONICAL_SHA256:
        _fail(
            "DECISION_V4_REPLAY_PREREG_CANONICAL_SHA_MISMATCH:"
            f"{actual}!={EXPECTED_PREREG_CANONICAL_SHA256}"
        )
    if payload.get("status") != "PREREGISTERED_NOT_IMPLEMENTED_NOT_REPLAYED":
        _fail("DECISION_V4_REPLAY_PREREG_STATUS_CHANGED")
    if payload.get("rule_id") != EXPECTED_RULE_ID:
        _fail("DECISION_V4_REPLAY_PREREG_RULE_ID_CHANGED")

    source = payload.get("source")
    if not isinstance(source, dict):
        _fail("DECISION_V4_REPLAY_PREREG_SOURCE_INVALID")
    source_expected = {
        "manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "score_sha256": EXPECTED_SOURCE_SCORE_SHA256,
        "sessions": EXPECTED_SCORE_SESSIONS,
        "rows": EXPECTED_SCORE_ROWS,
        "replay_authorized": False,
    }
    for key, expected in source_expected.items():
        if source.get(key) != expected:
            _fail(f"DECISION_V4_REPLAY_PREREG_SOURCE_CHANGED:{key}")

    if tuple(payload.get("required_descriptive_diagnostics", ())) != REQUIRED_DIAGNOSTICS:
        _fail("DECISION_V4_REPLAY_REQUIRED_DIAGNOSTICS_CHANGED")
    if payload.get("verdict_accept") != EXPECTED_ACCEPT_VERDICT:
        _fail("DECISION_V4_REPLAY_ACCEPT_VERDICT_CHANGED")
    if payload.get("verdict_reject") != EXPECTED_REJECT_VERDICT:
        _fail("DECISION_V4_REPLAY_REJECT_VERDICT_CHANGED")

    refill = payload.get("refill_decoupling")
    if not isinstance(refill, dict):
        _fail("DECISION_V4_REPLAY_REFILL_CONTRACT_INVALID")
    if refill.get("on_severe_exit_session_vacancy_priority") != ["A_CORE"]:
        _fail("DECISION_V4_REPLAY_SEVERE_PRIORITY_CHANGED")
    if refill.get("on_nonsevere_session_vacancy_priority") != [
        "A_CORE",
        "B_NEAR",
        "C_DISTANT",
    ]:
        _fail("DECISION_V4_REPLAY_NONSEVERE_PRIORITY_CHANGED")
    if (
        refill.get(
            "restriction_applies_to_all_vacancies_on_flagged_session_regardless_of_vacancy_origin"
        )
        is not True
    ):
        _fail("DECISION_V4_REPLAY_SEVERE_RESTRICTION_SCOPE_CHANGED")
    if refill.get("soft_replacement_semantics_unchanged_from_v3") is not True:
        _fail("DECISION_V4_REPLAY_SOFT_REPLACEMENT_CONTRACT_CHANGED")

    profile = V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1
    runtime_expected = {
        "rule_id": payload["rule_id"],
        "target_count_max": payload["target_count_max"],
        "strong_zone_max_rank": payload["strong_zone_max_rank"],
        "retention_zone_max_rank": payload["retention_zone_max_rank"],
        "mild_deterioration_max_rank": payload["mild_deterioration_max_rank"],
        "soft_replacement_min_rank_advantage": payload[
            "soft_replacement_min_rank_advantage"
        ],
        "universe_absence_exit_immediate": payload[
            "universe_absence_exit_immediate"
        ],
        "allow_temporary_underfill": refill["allow_temporary_underfill"],
        "bootstrap_first_session_exact_top10": payload[
            "bootstrap_first_session_exact_top10"
        ],
    }
    for key, expected in runtime_expected.items():
        if getattr(profile, key) != expected:
            _fail(f"DECISION_V4_REPLAY_RUNTIME_PROFILE_DRIFT:{key}")

    return path, payload
