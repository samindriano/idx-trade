from __future__ import annotations

import json
from pathlib import Path

import pytest

from idx_trade.historical_e2e_replay_v1 import (
    HistoricalE2EReplayError,
    replay_scope_manifest,
)
from idx_trade.e2e_replay_boundary_v1 import replay_boundary_static_audit_v1


def test_scope_manifest_requires_frozen_outcome_blind_status(tmp_path: Path) -> None:
    path = tmp_path / "scope.json"
    path.write_text(
        json.dumps({"status": "STRICT_SCOPE_EMPTY_BLOCKED", "outcome_access": False})
        + "\n",
        encoding="utf-8",
    )
    assert replay_scope_manifest(path)["status"] == "STRICT_SCOPE_EMPTY_BLOCKED"


def test_historical_adapter_has_no_provider_outcome_or_model_surface() -> None:
    evidence = replay_boundary_static_audit_v1(
        (Path(__file__).parents[1] / "src" / "idx_trade" / "historical_e2e_replay_v1.py",),
        source_kind="historical_artifact_adapter",
    )
    assert evidence["by_construction"] is True


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"status": "DRAFT", "outcome_access": False}, "STATUS_NOT_FROZEN"),
        ({"status": "STRICT_SCOPE_FROZEN", "outcome_access": True}, "OUTCOME_ACCESS_FLAG_INVALID"),
    ],
)
def test_scope_manifest_fails_closed_before_replay(
    tmp_path: Path, payload: dict[str, object], expected: str
) -> None:
    path = tmp_path / "scope.json"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(HistoricalE2EReplayError, match=expected):
        replay_scope_manifest(path)
