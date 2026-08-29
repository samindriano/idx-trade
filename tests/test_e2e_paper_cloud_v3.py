from __future__ import annotations

from types import SimpleNamespace

import pytest

from idx_trade.e2e_paper_cloud_runtime_v1 import LocalConditionalStore
from scripts import run_e2e_paper_cloud_v3 as v3


CODE_SHA = "a" * 40
SCHEDULE_SHA = "b" * 64
INPUT_SHA = "c" * 64
CHECKPOINT_SHA = "d" * 64


class _FakeArchive:
    standard = None

    def __init__(self, store):
        self.store = store

    def latest_snapshot(self, planned_sessions, *, before_or_equal):
        # Deliberately consume the iterable to reproduce the one-shot-generator
        # boundary that V3 must handle safely.
        tuple(planned_sessions)
        return self.standard


def _fake_bundle():
    return SimpleNamespace(
        refs=(SimpleNamespace(role="execution_schedule", sha256=SCHEDULE_SHA),),
        manifest_sha256=INPUT_SHA,
    )


def _fake_checkpoint():
    return SimpleNamespace(
        snapshot_bytes=b"checkpoint-snapshot",
        snapshot_sha256=CHECKPOINT_SHA,
        payload={"session_date": "2026-08-28", "stage": "PREOPEN_CA"},
    )


def test_checkpoint_wins_over_prior_session_standard_snapshot(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _FakeArchive.standard = (
        b"prior-standard",
        "e" * 64,
        {"session_date": "2026-08-27", "stage": "POST_EOD"},
    )
    monkeypatch.setattr(v3.v1, "CloudPaperArchive", _FakeArchive)
    monkeypatch.setattr(v3.CloudInputBundle, "load", lambda *a, **k: _fake_bundle())
    monkeypatch.setattr(v3, "load_preopen_ca_checkpoint", lambda *a, **k: _fake_checkpoint())
    monkeypatch.setattr(v3.v1, "_git_head", lambda *a, **k: CODE_SHA)

    with v3._patched_v1_continuity():
        archive = v3.v1.CloudPaperArchive(store)
        result = archive.latest_snapshot(
            (value for value in ("2026-08-27", "2026-08-28")),
            before_or_equal="2026-08-28",
        )
    assert result[0] == b"checkpoint-snapshot"
    assert result[2]["stage"] == "PREOPEN_CA"


def test_post_eod_routes_through_v2_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str | None, str | None]] = []
    expected = {
        "status": "WAITING",
        "cloud_runtime_tradability_bootstrap": {"status": "TRADABILITY_RUNTIME_READY"},
    }

    def fake_v2_run_once(*, phase=None, session_date=None):
        calls.append((phase, session_date))
        return expected

    monkeypatch.setattr(v3.v2, "run_once", fake_v2_run_once)
    result = v3.run_once(phase="POST_EOD", session_date="2026-08-28")

    assert calls == [("POST_EOD", "2026-08-28")]
    assert result == expected


def test_same_session_scientific_terminal_snapshot_beats_checkpoint(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    standard = (
        b"same-day-preopen",
        "f" * 64,
        {"session_date": "2026-08-28", "stage": "PREOPEN"},
    )
    _FakeArchive.standard = standard
    monkeypatch.setattr(v3.v1, "CloudPaperArchive", _FakeArchive)
    monkeypatch.setattr(v3.CloudInputBundle, "load", lambda *a, **k: _fake_bundle())
    monkeypatch.setattr(v3, "load_preopen_ca_checkpoint", lambda *a, **k: _fake_checkpoint())
    monkeypatch.setattr(v3.v1, "_git_head", lambda *a, **k: CODE_SHA)

    with v3._patched_v1_continuity():
        archive = v3.v1.CloudPaperArchive(store)
        result = archive.latest_snapshot(
            (value for value in ("2026-08-28",)),
            before_or_equal="2026-08-28",
        )
    assert result == standard


def test_checkpoint_lookup_is_skipped_for_nonplanned_session(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _FakeArchive.standard = None
    monkeypatch.setattr(v3.v1, "CloudPaperArchive", _FakeArchive)
    monkeypatch.setattr(
        v3,
        "load_preopen_ca_checkpoint",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("checkpoint lookup forbidden")),
    )

    with v3._patched_v1_continuity():
        archive = v3.v1.CloudPaperArchive(store)
        result = archive.latest_snapshot(
            (value for value in ("2026-08-27",)),
            before_or_equal="2026-08-28",
        )
    assert result is None


def test_preopen_ca_phase_dispatch_does_not_delegate_to_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = {"status": "WAITING", "controller_status": "WAITING_PREPARED_EXECUTION"}
    monkeypatch.setattr(v3, "_run_preopen_ca_once", lambda **kwargs: expected)
    monkeypatch.setattr(
        v3.v2,
        "run_once",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("V2 must not run PREOPEN_CA")),
    )
    assert v3.run_once(phase="PREOPEN_CA") == expected


class _TerminalArchive:
    def __init__(self, terminal_stage: str | None):
        self.terminal_stage = terminal_stage
        self.verified = []

    def existing_commit(self, session: str, stage: str):
        if stage == self.terminal_stage:
            return SimpleNamespace(session_date=session, status="EXECUTION_COMPLETE")
        return None

    def verify_existing_identity(self, commit, **kwargs):
        self.verified.append((commit, kwargs))


def test_checkpoint_creation_is_forbidden_after_same_session_preopen_terminal() -> None:
    archive = _TerminalArchive("PREOPEN")
    with pytest.raises(Exception, match="AFTER_TERMINAL_STAGE_FORBIDDEN:PREOPEN"):
        v3._assert_no_same_session_terminal_stage(
            archive,
            session="2026-08-28",
            schedule_sha256=SCHEDULE_SHA,
            input_manifest_sha256=INPUT_SHA,
        )
    assert len(archive.verified) == 1


def test_checkpoint_creation_is_forbidden_after_same_session_post_eod_terminal() -> None:
    archive = _TerminalArchive("POST_EOD")
    with pytest.raises(Exception, match="AFTER_TERMINAL_STAGE_FORBIDDEN:POST_EOD"):
        v3._assert_no_same_session_terminal_stage(
            archive,
            session="2026-08-28",
            schedule_sha256=SCHEDULE_SHA,
            input_manifest_sha256=INPUT_SHA,
        )
    assert len(archive.verified) == 1


def test_checkpoint_creation_allowed_when_no_same_session_terminal_exists() -> None:
    archive = _TerminalArchive(None)
    v3._assert_no_same_session_terminal_stage(
        archive,
        session="2026-08-28",
        schedule_sha256=SCHEDULE_SHA,
        input_manifest_sha256=INPUT_SHA,
    )
    assert archive.verified == []
