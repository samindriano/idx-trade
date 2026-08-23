from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from idx_trade.historical_e2e_replay_v1 import (
    HistoricalE2EReplayError,
    HistoricalReplayArtifacts,
    replay_scope_manifest,
    replay_verified_session,
)
from idx_trade.historical_e2e_scope_validator_v1 import canonical_scope_payload_hash
from idx_trade.e2e_replay_boundary_v1 import replay_boundary_static_audit_v1


def test_scope_manifest_requires_frozen_outcome_blind_status(tmp_path: Path) -> None:
    sessions = []
    for index in range(600):
        decision = date(2020, 1, 2) + timedelta(days=index)
        execution = decision + timedelta(days=1)
        sessions.append(
            {
                "session_index": index,
                "decision_session_date": decision.isoformat(),
                "execution_session_date": execution.isoformat(),
            }
        )
    path = tmp_path / "scope.json"
    payload = {
        "schema_version": "idx_trade_historical_e2e_scope_v1",
        "status": "STRICT_SCOPE_EMPTY_BLOCKED",
        "outcome_access": False,
        "model_fit": False,
        "protected_outcome_access": False,
        "source_pins": {"calendar_sha256": "a" * 64},
        "candidate_session_count": 600,
        "strict_session_indices": [],
        "open": {"per_session": sessions},
    }
    payload["scope_payload_sha256"] = canonical_scope_payload_hash(payload)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    assert replay_scope_manifest(path)["status"] == "STRICT_SCOPE_EMPTY_BLOCKED"


def test_historical_adapter_has_no_provider_outcome_or_model_surface() -> None:
    evidence = replay_boundary_static_audit_v1(
        (Path(__file__).parents[1] / "src" / "idx_trade" / "historical_e2e_replay_v1.py",),
        source_kind="historical_artifact_adapter",
    )
    assert evidence["by_construction"] is True


@pytest.mark.parametrize(
    "field, expected",
    [
        ("DRAFT", "REPLAY_SCOPE_STATUS_INVALID"),
        ("OUTCOME", "REPLAY_SCOPE_OUTCOME_ACCESS_FLAG_INVALID"),
    ],
)
def test_scope_manifest_fails_closed_before_replay(
    tmp_path: Path, field: str, expected: str
) -> None:
    # Reuse the minimal constructor above without duplicating any production
    # artifact or outcome data.
    sessions = []
    for index in range(600):
        decision = date(2020, 1, 2) + timedelta(days=index)
        sessions.append(
            {
                "session_index": index,
                "decision_session_date": decision.isoformat(),
                "execution_session_date": (decision + timedelta(days=1)).isoformat(),
            }
        )
    payload: dict[str, object] = {
        "schema_version": "idx_trade_historical_e2e_scope_v1",
        "status": "STRICT_SCOPE_FROZEN",
        "outcome_access": False,
        "model_fit": False,
        "protected_outcome_access": False,
        "source_pins": {"calendar_sha256": "a" * 64},
        "candidate_session_count": 600,
        "strict_session_indices": list(range(600)),
        "open": {"per_session": sessions},
    }
    if field == "DRAFT":
        payload["status"] = "DRAFT"
    else:
        payload["outcome_access"] = True
    path = tmp_path / "scope.json"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(HistoricalE2EReplayError, match=expected):
        replay_scope_manifest(path)


def test_replay_rejects_empty_scope_before_artifact_access(tmp_path: Path) -> None:
    scope = tmp_path / "scope.json"
    sessions = [
        {
            "session_index": index,
            "decision_session_date": (date(2020, 1, 2) + timedelta(days=index)).isoformat(),
            "execution_session_date": (date(2020, 1, 3) + timedelta(days=index)).isoformat(),
        }
        for index in range(600)
    ]
    payload = {
        "schema_version": "idx_trade_historical_e2e_scope_v1",
        "status": "STRICT_SCOPE_EMPTY_BLOCKED",
        "outcome_access": False,
        "model_fit": False,
        "protected_outcome_access": False,
        "source_pins": {"calendar_sha256": "a" * 64},
        "candidate_session_count": 600,
        "strict_session_indices": [],
        "open": {"per_session": sessions},
    }
    payload["scope_payload_sha256"] = canonical_scope_payload_hash(payload)
    scope.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    artifacts = HistoricalReplayArtifacts(
        decision_session_date="2020-01-02",
        score_manifest_path=tmp_path / "missing-score.json",
        previous_score_manifest_path=None,
        session_ohlcv_path=tmp_path / "missing-ohlcv.parquet",
        model_input_path=tmp_path / "missing-model.parquet",
        official_calendar_path=tmp_path / "missing-calendar.csv",
        open_manifest_path=tmp_path / "missing-open.json",
        ca_attestation_path=tmp_path / "missing-ca.json",
        ca_journal_path=tmp_path / "missing-journal.json",
    )
    with pytest.raises(HistoricalE2EReplayError, match="SCOPE_NOT_FROZEN"):
        replay_verified_session(tmp_path / "runtime", artifacts, scope_manifest_path=scope)
