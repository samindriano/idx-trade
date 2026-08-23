from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest

from idx_trade import forward_ca_attestation_v1 as forward_ca


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capture_forward_ca_idx_bei.py"
spec = importlib.util.spec_from_file_location("forward_ca_capture_test", SCRIPT)
assert spec is not None and spec.loader is not None
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class FakeResponse:
    def __init__(self, payload: object, *, status_code: int = 200):
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self.content = json.dumps(payload, sort_keys=True).encode("utf-8")

    def json(self) -> object:
        return json.loads(self.content.decode("utf-8"))


class FakeClient:
    responses: list[FakeResponse] = []
    calls: list[tuple[str, dict[str, object]]] = []

    def __init__(self, *args, **kwargs):
        self.responses_iter = iter(type(self).responses)

    def get(self, endpoint: str, *, params: dict[str, object], **kwargs) -> FakeResponse:
        type(self).calls.append((endpoint, dict(params)))
        return next(self.responses_iter)


def _install_fake_provider(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[FakeResponse],
    calendar: dict,
) -> None:
    FakeClient.responses = responses
    FakeClient.calls = []
    client_module = types.ModuleType("idx.core.client")
    client_module.IDXClient = FakeClient
    core_module = types.ModuleType("idx.core")
    core_module.client = client_module
    idx_module = types.ModuleType("idx")
    idx_module.core = core_module
    monkeypatch.setitem(sys.modules, "idx", idx_module)
    monkeypatch.setitem(sys.modules, "idx.core", core_module)
    monkeypatch.setitem(sys.modules, "idx.core.client", client_module)
    monkeypatch.setattr(capture, "_verify_provider_checkout", lambda checkout: None)
    monkeypatch.setattr(
        capture.forward_ca,
        "EXPECTED_CALENDAR_SCHEMA_FINGERPRINT",
        capture._structural_fingerprint(calendar),
    )


def _responses(calendar: dict, *, status_code: int = 200) -> list[FakeResponse]:
    return (
        [
            FakeResponse({"data": [], "recordsFiltered": 0}, status_code=status_code)
            for _ in capture.CA_TYPES
        ]
        + [FakeResponse({"Items": [], "PageCount": 1}) for _ in ("BBCA", "TLKM")]
        + [FakeResponse(calendar)]
    )


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    responses: list[FakeResponse],
) -> tuple[Path, Path]:
    calendar = {"Results": [{"Code": "BBCA", "Date": "2026-08-22", "Title": "RUPS"}]}
    _install_fake_provider(monkeypatch, responses, calendar)
    output = tmp_path / "phase"
    attestation = tmp_path / "attestations" / "2026-08-22_POST_EOD.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_forward_ca_idx_bei.py",
            "--provider-checkout", str(tmp_path / "provider"),
            "--phase", "POST_EOD",
            "--from-session", "2026-08-22",
            "--through-session", "2026-08-23",
            "--tickers", "TLKM,BBCA",
            "--output-dir", str(output),
            "--attestation-output", str(attestation),
        ],
    )
    assert capture.main() == 0
    return output, attestation


def test_capture_publishes_only_after_phase_manifest_and_attestation_verify(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calendar = {"Results": [{"Code": "BBCA", "Date": "2026-08-22", "Title": "RUPS"}]}
    output, attestation = _run(tmp_path, monkeypatch, responses=_responses(calendar))
    manifest = output / "MANIFEST.json"
    assert manifest.is_file()
    assert attestation.is_file()
    verified = forward_ca.verify_phase_manifest(manifest)
    assert verified["phase"] == "POST_EOD"
    assert verified["required_tickers"] == ["BBCA", "TLKM"]
    assert json.loads(attestation.read_text(encoding="utf-8"))["phase_manifest_path"] == str(manifest.resolve())
    assert len(FakeClient.calls) == len(capture.CA_TYPES) + 3


def test_non_200_capture_keeps_only_a_partial_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calendar = {"Results": [{"Code": "BBCA", "Date": "2026-08-22", "Title": "RUPS"}]}
    _install_fake_provider(monkeypatch, _responses(calendar, status_code=403), calendar)
    output = tmp_path / "phase"
    attestation = tmp_path / "attestation.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_forward_ca_idx_bei.py",
            "--provider-checkout", str(tmp_path / "provider"),
            "--phase", "POST_EOD",
            "--from-session", "2026-08-22",
            "--through-session", "2026-08-23",
            "--tickers", "BBCA,TLKM",
            "--output-dir", str(output),
            "--attestation-output", str(attestation),
        ],
    )
    with pytest.raises(SystemExit, match="FORWARD_CA_HTTP_STATUS"):
        capture.main()
    assert not output.exists()
    partials = list(tmp_path.glob(".phase.partial.*"))
    assert len(partials) == 1
    assert not (partials[0] / "MANIFEST.json").exists()


def test_existing_output_fails_before_provider_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "phase"
    output.mkdir()
    _install_fake_provider(monkeypatch, [], {"Results": [{"Code": "BBCA"}]})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_forward_ca_idx_bei.py",
            "--provider-checkout", str(tmp_path / "provider"),
            "--phase", "POST_EOD",
            "--from-session", "2026-08-22",
            "--through-session", "2026-08-23",
            "--tickers", "BBCA",
            "--output-dir", str(output),
            "--attestation-output", str(tmp_path / "attestation.json"),
        ],
    )
    with pytest.raises(SystemExit, match="FORWARD_CA_OUTPUT_EXISTS"):
        capture.main()
    assert FakeClient.calls == []


def test_interrupted_publication_is_completed_without_provider_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calendar = {"Results": [{"Code": "BBCA", "Date": "2026-08-22", "Title": "RUPS"}]}
    output, attestation = _run(tmp_path, monkeypatch, responses=_responses(calendar))
    pending = attestation.with_name(".pending-attestation")
    pending.write_bytes(attestation.read_bytes())
    attestation.unlink()
    marker = {
        "schema_version": "idx_trade_forward_ca_publication_v1",
        "output_dir": str(output.resolve()),
        "attestation": str(attestation.resolve()),
        "pending_attestation": str(pending.resolve()),
        "manifest_sha256": capture._sha256_bytes((output / "MANIFEST.json").read_bytes()),
        "pending_attestation_sha256": capture._sha256_bytes(pending.read_bytes()),
    }
    (output / "PUBLISH.json").write_text(json.dumps(marker), encoding="utf-8")
    FakeClient.calls = []

    assert capture._recover_interrupted_publication(
        output,
        attestation,
        expected_phase="POST_EOD",
        expected_from_session="2026-08-22",
        expected_through_session="2026-08-23",
        required_tickers=["BBCA", "TLKM"],
    ) is True
    assert attestation.is_file()
    assert not pending.exists()
    assert not (output / "PUBLISH.json").exists()
    assert FakeClient.calls == []
