from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import run_e2e_paper_preopen_v2 as preopen_v2


DECISION = "2026-08-27"
EXECUTION = "2026-08-28"
SCHEDULE_SHA = "b" * 64


class _TickerSeries:
    def tolist(self):
        return ["BBCA"]


class _Scores:
    def __getitem__(self, key):
        assert key == "ticker"
        return _TickerSeries()


def test_preopen_consumer_reconciles_preopen_ca_as_decision_to_execution_scope(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = SimpleNamespace(session_date=DECISION, scores=_Scores())
    eod = SimpleNamespace(session_date=DECISION, next_official_session_date=EXECUTION)
    seen = {}

    monkeypatch.setattr(preopen_v2, "load_score_manifest", lambda path: current)
    monkeypatch.setattr(
        preopen_v2,
        "verify_eod_execution_inputs_with_schedule",
        lambda **kwargs: eod,
    )
    monkeypatch.setattr(
        preopen_v2,
        "load_verified_official_trading_schedule",
        lambda *args, **kwargs: SimpleNamespace(session_dates=(DECISION, EXECUTION)),
    )
    monkeypatch.setattr(preopen_v2, "require_phase_window", lambda **kwargs: None)
    monkeypatch.setattr(preopen_v2, "verify_prepared_schedule_binding", lambda *args, **kwargs: None)
    monkeypatch.setattr(preopen_v2, "verify_open_execution_inputs", lambda **kwargs: object())
    monkeypatch.setattr(
        preopen_v2,
        "derive_required_execution_tickers",
        lambda *args, **kwargs: ("BBCA",),
    )

    def reconcile(**kwargs):
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(
        preopen_v2,
        "reconcile_corporate_action_attestation_v1_2_journal",
        reconcile,
    )
    monkeypatch.setattr(
        preopen_v2,
        "execute_preopen",
        lambda *args, **kwargs: SimpleNamespace(
            status="EXECUTION_COMPLETE",
            path=tmp_path / "execution.json",
            file_sha256="1" * 64,
            runtime_snapshot_path=tmp_path / "snapshot.json",
            runtime_snapshot_sha256="2" * 64,
            execution_session_date=EXECUTION,
        ),
    )

    args = SimpleNamespace(
        current_score_manifest="current.json",
        previous_score_manifest=None,
        session_ohlcv="ohlcv.parquet",
        model_input="model.parquet",
        calendar="calendar.csv",
        execution_schedule_attestation="schedule.json",
        execution_schedule_attestation_sha256=SCHEDULE_SHA,
        runtime_root=str(tmp_path / "runtime"),
        prepared="prepared.json",
        open_manifest="open.json",
        dividend_review=[],
        attachment_dir=None,
        ca_attestation="ca.json",
        ca_journal="journal.json",
    )

    assert preopen_v2._run(args) == 0
    assert seen["expected_from_session_date"] == DECISION
    assert seen["expected_through_session_date"] == EXECUTION
    assert seen["required_tickers"] == ("BBCA",)
