from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from idx_trade.historical_e2e_replay_runner_v1 import (
    HistoricalE2EReplayRunnerError,
    canonical_summary_sha256,
    run_historical_e2e_replay,
)
from idx_trade.historical_e2e_replay_v1 import HistoricalReplayArtifacts
from idx_trade.historical_e2e_scope_validator_v1 import canonical_scope_payload_hash


SESSION_COUNT = 600
START_DATE = date(2020, 1, 2)


def _scope(tmp_path: Path, *, frozen: bool = True) -> Path:
    rows = [
        {
            "session_index": index,
            "decision_session_date": (START_DATE + timedelta(days=index)).isoformat(),
            "execution_session_date": (START_DATE + timedelta(days=index + 1)).isoformat(),
        }
        for index in range(SESSION_COUNT)
    ]
    payload: dict[str, object] = {
        "schema_version": "idx_trade_historical_e2e_scope_v1",
        "status": "STRICT_SCOPE_FROZEN" if frozen else "STRICT_SCOPE_EMPTY_BLOCKED",
        "outcome_access": False,
        "model_fit": False,
        "protected_outcome_access": False,
        "source_pins": {"calendar_sha256": "a" * 64},
        "candidate_session_count": SESSION_COUNT,
        "strict_session_indices": list(range(SESSION_COUNT)) if frozen else [],
        "open": {"per_session": rows},
    }
    payload["scope_payload_sha256"] = canonical_scope_payload_hash(payload)
    path = tmp_path / "REPLAY_SCOPE.json"
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _artifacts() -> list[HistoricalReplayArtifacts]:
    return [
        HistoricalReplayArtifacts(
            decision_session_date=(START_DATE + timedelta(days=index)).isoformat(),
            score_manifest_path=Path(f"score-{index}.json"),
            previous_score_manifest_path=None,
            session_ohlcv_path=Path(f"ohlcv-{index}.parquet"),
            model_input_path=Path(f"model-{index}.parquet"),
            official_calendar_path=Path("calendar.csv"),
            open_manifest_path=Path(f"open-{index}.json"),
            ca_attestation_path=Path(f"ca-{index}.json"),
            ca_journal_path=Path(f"journal-{index}.json"),
        )
        for index in range(SESSION_COUNT)
    ]


def _transition_result(index: int, artifact: HistoricalReplayArtifacts) -> dict[str, str]:
    def digest(label: str) -> str:
        return hashlib.sha256(f"{label}:{index}".encode("ascii")).hexdigest()

    return {
        "decision_session_date": artifact.decision_session_date,
        "execution_session_date": (START_DATE + timedelta(days=index + 1)).isoformat(),
        "status": "EXECUTION_COMPLETE",
        "execution_sha256": digest("execution"),
        "runtime_snapshot_sha256": digest("snapshot"),
        "runtime_state_sha256": digest("state"),
    }


def test_valid_six_by_one_hundred_shape_bootstraps_once_and_replays_in_order(
    tmp_path: Path,
) -> None:
    scope = _scope(tmp_path)
    artifacts = _artifacts()
    bootstrap_calls: list[tuple[object, str]] = []
    transition_calls: list[tuple[int, str, object]] = []

    def bootstrap(runtime_root: object, *, session_date: str) -> None:
        bootstrap_calls.append((runtime_root, session_date))

    def transition(
        runtime_root: object,
        artifact: HistoricalReplayArtifacts,
        *,
        scope_manifest_path: object,
    ) -> dict[str, str]:
        index = len(transition_calls)
        transition_calls.append((index, artifact.decision_session_date, scope_manifest_path))
        return _transition_result(index, artifact)

    summary = run_historical_e2e_replay(
        tmp_path / "runtime",
        artifacts,
        scope_manifest_path=scope,
        bootstrap_callback=bootstrap,
        transition_callback=transition,
    )

    assert len(bootstrap_calls) == 1
    assert bootstrap_calls[0] == (tmp_path / "runtime", "2020-01-02")
    assert len(transition_calls) == 600
    assert [call[0] for call in transition_calls] == list(range(600))
    assert transition_calls[99][1] == "2020-04-10"
    assert transition_calls[100][1] == "2020-04-11"
    assert summary.strict_session_count == 600
    assert len(summary.transitions) == 600
    assert summary.to_dict()["transition_count"] == 600
    assert summary.to_dict()["summary_sha256"] == summary.summary_sha256
    assert canonical_summary_sha256(summary.to_dict()) == summary.summary_sha256
    assert "cash_idr" not in summary.to_dict()
    assert "position_count" not in summary.to_dict()


def test_empty_scope_is_rejected_before_callbacks(tmp_path: Path) -> None:
    scope = _scope(tmp_path, frozen=False)
    calls: list[str] = []

    def bootstrap(*args: object, **kwargs: object) -> None:
        calls.append("bootstrap")

    def transition(*args: object, **kwargs: object) -> SimpleNamespace:
        calls.append("transition")
        return SimpleNamespace()

    with pytest.raises(HistoricalE2EReplayRunnerError, match="STRICT_SCOPE_EMPTY_BLOCKED"):
        run_historical_e2e_replay(
            tmp_path / "runtime",
            _artifacts(),
            scope_manifest_path=scope,
            bootstrap_callback=bootstrap,
            transition_callback=transition,
        )
    assert calls == []


def test_exact_pair_mismatch_is_rejected_before_bootstrap(tmp_path: Path) -> None:
    scope = _scope(tmp_path)
    artifacts = _artifacts()
    artifacts[250] = HistoricalReplayArtifacts(
        **{
            **artifacts[250].__dict__,
            "decision_session_date": "2099-01-01",
        }
    )
    calls: list[str] = []

    with pytest.raises(
        HistoricalE2EReplayRunnerError,
        match="SCOPE_PAIR_MISMATCH",
    ):
        run_historical_e2e_replay(
            tmp_path / "runtime",
            artifacts,
            scope_manifest_path=scope,
            bootstrap_callback=lambda *args, **kwargs: calls.append("bootstrap"),
            transition_callback=lambda *args, **kwargs: calls.append("transition"),
        )
    assert calls == []


@pytest.mark.parametrize("mutation", ["duplicate", "order"])
def test_duplicate_or_out_of_order_artifacts_are_rejected_before_callbacks(
    tmp_path: Path,
    mutation: str,
) -> None:
    scope = _scope(tmp_path)
    artifacts = _artifacts()
    if mutation == "duplicate":
        artifacts[150] = artifacts[149]
    else:
        artifacts[150], artifacts[151] = artifacts[151], artifacts[150]
    calls: list[str] = []

    with pytest.raises(HistoricalE2EReplayRunnerError):
        run_historical_e2e_replay(
            tmp_path / "runtime",
            artifacts,
            scope_manifest_path=scope,
            bootstrap_callback=lambda *args, **kwargs: calls.append("bootstrap"),
            transition_callback=lambda *args, **kwargs: calls.append("transition"),
        )
    assert calls == []


def test_summary_is_deterministic_for_identical_stubbed_replays(tmp_path: Path) -> None:
    scope = _scope(tmp_path)

    def run_once() -> object:
        return run_historical_e2e_replay(
            tmp_path / "runtime",
            _artifacts(),
            scope_manifest_path=scope,
            bootstrap_callback=lambda *args, **kwargs: None,
            transition_callback=lambda runtime_root, artifact, *, scope_manifest_path: _transition_result(
                int(artifact.score_manifest_path.stem.split("-")[1]),
                artifact,
            ),
        )

    first = run_once()
    second = run_once()
    assert first == second
    assert first.summary_sha256 == second.summary_sha256
