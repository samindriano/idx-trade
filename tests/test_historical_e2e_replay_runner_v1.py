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
from idx_trade.historical_e2e_scope_validator_v1 import (
    EXPECTED_CANDIDATE_SESSION_COUNT,
    canonical_scope_payload_hash,
)


SESSION_COUNT = EXPECTED_CANDIDATE_SESSION_COUNT
START_DATE = date(2020, 1, 2)


def _scope(
    tmp_path: Path,
    *,
    frozen: bool = True,
    strict_start: int = 0,
    strict_count: int = SESSION_COUNT,
) -> Path:
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
        "strict_session_indices": (
            list(range(strict_start, strict_start + strict_count)) if frozen else []
        ),
        "open": {"per_session": rows},
    }
    if frozen:
        payload.update(
            {
                "start_session": rows[strict_start]["decision_session_date"],
                "end_session": rows[strict_start + strict_count - 1][
                    "decision_session_date"
                ],
                "session_count": strict_count,
            }
        )
    payload["scope_payload_sha256"] = canonical_scope_payload_hash(payload)
    path = tmp_path / "REPLAY_SCOPE.json"
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _artifacts(
    *, strict_start: int = 0, strict_count: int = SESSION_COUNT
) -> list[HistoricalReplayArtifacts]:
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
            session_index=index,
            execution_session_date=(START_DATE + timedelta(days=index + 1)).isoformat(),
        )
        for index in range(strict_start, strict_start + strict_count)
    ]


def _transition_result(index: int, artifact: HistoricalReplayArtifacts) -> dict[str, str]:
    def digest(label: str) -> str:
        return hashlib.sha256(f"{label}:{index}".encode("ascii")).hexdigest()

    return {
        "decision_session_date": artifact.decision_session_date,
        "execution_session_date": artifact.execution_session_date
        or (START_DATE + timedelta(days=index + 1)).isoformat(),
        "status": "EXECUTION_COMPLETE",
        "execution_sha256": digest("execution"),
        "runtime_snapshot_sha256": digest("snapshot"),
        "runtime_state_sha256": digest("state"),
    }


@pytest.mark.parametrize("strict_count", [20, 60, 120, 252, SESSION_COUNT])
def test_valid_contiguous_scope_bootstraps_once_and_replays_in_order(
    tmp_path: Path, strict_count: int
) -> None:
    strict_start = 0
    scope = _scope(tmp_path, strict_start=strict_start, strict_count=strict_count)
    artifacts = _artifacts(strict_start=strict_start, strict_count=strict_count)
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
    assert bootstrap_calls[0] == (
        tmp_path / "runtime",
        (START_DATE + timedelta(days=strict_start)).isoformat(),
    )
    assert len(transition_calls) == strict_count
    assert [call[0] for call in transition_calls] == list(range(strict_count))
    assert transition_calls[0][1] == (
        START_DATE + timedelta(days=strict_start)
    ).isoformat()
    assert summary.strict_session_count == strict_count
    assert len(summary.transitions) == strict_count
    assert summary.to_dict()["transition_count"] == strict_count
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
            _artifacts(strict_count=20),
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


@pytest.mark.parametrize("mutation", ["duplicate", "order", "gap"])
def test_duplicate_or_out_of_order_artifacts_are_rejected_before_callbacks(
    tmp_path: Path,
    mutation: str,
) -> None:
    scope = _scope(tmp_path, strict_start=0, strict_count=20)
    artifacts = _artifacts(strict_start=0, strict_count=20)
    if mutation == "duplicate":
        artifacts[10] = artifacts[9]
    elif mutation == "order":
        artifacts[10], artifacts[11] = artifacts[11], artifacts[10]
    else:
        artifacts[10] = HistoricalReplayArtifacts(
            **{**artifacts[10].__dict__, "session_index": 62}
        )
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
    scope = _scope(tmp_path, strict_start=0, strict_count=20)

    def run_once() -> object:
        return run_historical_e2e_replay(
            tmp_path / "runtime",
            _artifacts(strict_start=0, strict_count=20),
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
