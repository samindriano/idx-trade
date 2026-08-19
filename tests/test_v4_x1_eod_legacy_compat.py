from __future__ import annotations

from pathlib import Path

from idx_trade import v4_x1_eod_legacy_compat as compat
from idx_trade.provenance import sha256_file


def _row(tmp_path: Path) -> dict[str, object]:
    files = {}
    for name in ("snapshot", "evidence", "manifest"):
        path = tmp_path / f"{name}.bin"
        path.write_bytes(name.encode("utf-8"))
        files[name] = path
    return {
        "state": "DATA_READY",
        "session_date": "2026-08-10",
        "snapshot_path": str(files["snapshot"]),
        "snapshot_sha256": sha256_file(files["snapshot"]),
        "evidence_path": str(files["evidence"]),
        "evidence_sha256": sha256_file(files["evidence"]),
        "manifest_path": str(files["manifest"]),
        "manifest_sha256": sha256_file(files["manifest"]),
    }


def test_scoped_verifier_prefers_modern_strict_verifier(tmp_path: Path, monkeypatch) -> None:
    row = _row(tmp_path)
    monkeypatch.setattr(
        compat,
        "verify_canonical_eod_calendar_parent_attestation",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("attestation must not be consulted")),
    )
    verify = compat.build_scoped_ready_verifier(tmp_path, lambda _: True)
    assert verify(row) is True


def test_scoped_verifier_accepts_verified_modern_calendar_extension(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _row(tmp_path)
    monkeypatch.setattr(compat, "_modern_calendar_extension_compatible", lambda root, candidate: True)
    monkeypatch.setattr(
        compat,
        "_legacy_direct_parent_still_exact",
        lambda _: (_ for _ in ()).throw(AssertionError("legacy path must not be consulted")),
    )
    monkeypatch.setattr(
        compat,
        "verify_canonical_eod_calendar_parent_attestation",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("attestation must not be consulted")),
    )
    verify = compat.build_scoped_ready_verifier(tmp_path, lambda _: False)
    assert verify(row) is True


def test_scoped_verifier_accepts_legacy_direct_parent_without_attestation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _row(tmp_path)
    monkeypatch.setattr(compat, "_modern_calendar_extension_compatible", lambda root, candidate: False)
    monkeypatch.setattr(compat, "_legacy_direct_parent_still_exact", lambda _: True)
    monkeypatch.setattr(
        compat,
        "verify_canonical_eod_calendar_parent_attestation",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("attestation must not be consulted")),
    )
    verify = compat.build_scoped_ready_verifier(tmp_path, lambda _: False)
    assert verify(row) is True


def test_scoped_verifier_requires_attestation_when_all_compat_checks_fail(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _row(tmp_path)
    monkeypatch.setattr(compat, "_modern_calendar_extension_compatible", lambda root, candidate: False)
    monkeypatch.setattr(compat, "_legacy_direct_parent_still_exact", lambda _: False)
    verify = compat.build_scoped_ready_verifier(tmp_path, lambda _: False)
    assert verify(row) is False


def test_scoped_verifier_accepts_only_verified_attestation_with_exact_db_core(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row = _row(tmp_path)
    proof = compat.attestation_path(tmp_path, "2026-08-10")
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text("{}\n", encoding="utf-8")
    seen = {}

    monkeypatch.setattr(compat, "_modern_calendar_extension_compatible", lambda root, candidate: False)
    monkeypatch.setattr(compat, "_legacy_direct_parent_still_exact", lambda _: False)

    def verified(path, **kwargs):
        seen["path"] = Path(path).resolve()
        seen.update(kwargs)
        return True

    monkeypatch.setattr(compat, "verify_canonical_eod_calendar_parent_attestation", verified)
    verify = compat.build_scoped_ready_verifier(tmp_path, lambda _: False)
    assert verify(row) is True
    assert seen["path"] == proof.resolve()
    assert seen["expected_session"] == "2026-08-10"

    Path(str(row["snapshot_path"])).write_bytes(b"tampered")
    assert verify(row) is False


def test_scoped_monkeypatch_is_restored_after_pipeline_call(tmp_path: Path, monkeypatch) -> None:
    original = compat.monitor._verify_ready_row
    observed = {}

    def fake_pipeline(*args, **kwargs):
        observed["patched"] = compat.monitor._verify_ready_row is not original
        return {"status": "PIPELINE_OK_TEST"}

    monkeypatch.setattr(compat.pipeline, "run_eod_v4_x1_pipeline", fake_pipeline)
    result = compat.run_with_legacy_attestation_compat(
        tmp_path,
        tmp_path,
        repo_root=tmp_path,
    )
    assert result["status"] == "PIPELINE_OK_TEST"
    assert observed["patched"] is True
    assert compat.monitor._verify_ready_row is original
