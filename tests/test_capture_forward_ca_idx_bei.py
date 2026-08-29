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
    init_kwargs: dict[str, object] = {}

    def __init__(self, *args, **kwargs):
        type(self).init_kwargs = dict(kwargs)
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
    FakeClient.init_kwargs = {}
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
        capture,
        "_build_transport_client",
        lambda checkout, raw_dir: (FakeClient(), []),
    )
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
    monkeypatch.setattr(
        capture,
        "_fetch_zapi_raw",
        lambda endpoint, params: (_ for _ in ()).throw(
            SystemExit("FORWARD_CA_ZAPI_RAW_HTTP_STATUS:503")
        ),
    )
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
    with pytest.raises(SystemExit, match="FORWARD_CA_ZAPI_RAW_HTTP_STATUS"):
        capture.main()
    assert not output.exists()
    partials = list(tmp_path.glob(".phase.partial.*"))
    assert len(partials) == 1
    assert not (partials[0] / "MANIFEST.json").exists()


def _zapi_envelope(endpoint: str, payload: object) -> bytes:
    inner = {"provider": "idx", "path": endpoint.lstrip("/"), "data": payload}
    if isinstance(payload, list):
        inner.update({"recordsTotal": len(payload), "recordsFiltered": len(payload)})
    return json.dumps(
        {"project": "finance:idx:raw", "timestamp": "2026-08-23T14:00:00Z", "data": inner},
        sort_keys=True,
    ).encode("utf-8")


def test_direct_transport_failure_uses_zapi_raw_and_verifies_nested_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calendar = {"Results": [{"Code": "BBCA", "Date": "2026-08-22", "Title": "RUPS"}]}
    responses = _responses(calendar)
    responses[0] = FakeResponse({"blocked": True}, status_code=503)
    responses[len(capture.CA_TYPES)] = FakeResponse({"blocked": True}, status_code=503)
    responses[len(capture.CA_TYPES) + 2] = FakeResponse({"blocked": True}, status_code=503)
    _install_fake_provider(monkeypatch, responses, calendar)
    monkeypatch.setenv("ZAPI_API_KEY", "test-only-secret")
    calls: list[str] = []

    def fake_zapi(endpoint: str, params: dict[str, object]) -> bytes:
        calls.append(endpoint)
        if endpoint == "/NewsAnnouncement/GetAllAnnouncement":
            return _zapi_envelope(endpoint, {"Items": [], "PageCount": 1})
        if endpoint == "/Home/GetCalendar":
            return _zapi_envelope(endpoint, calendar)
        return _zapi_envelope(endpoint, [])

    monkeypatch.setattr(capture, "_fetch_zapi_raw", fake_zapi)
    output, _ = _run(tmp_path, monkeypatch, responses=responses)
    manifest = json.loads((output / "MANIFEST.json").read_text(encoding="utf-8"))
    verified = forward_ca.verify_phase_manifest(output / "MANIFEST.json")

    assert verified["phase"] == "POST_EOD"
    assert calls == [
        "/ListingActivity/GetIssuedHistory",
        "/NewsAnnouncement/GetAllAnnouncement",
        "/Home/GetCalendar",
    ]
    assert manifest["transport_policy"] == capture.TRANSPORT_POLICY
    assert manifest["selected_transports"] == [
        capture.DIRECT_TRANSPORT,
        capture.ZAPI_TRANSPORT,
    ]
    zapi_rows = [row for row in manifest["raw_artifacts"] if row.get("transport") == capture.ZAPI_TRANSPORT]
    assert len(zapi_rows) == 3
    assert all((output / row["transport_raw_path"]).is_file() for row in zapi_rows)
    assert "test-only-secret" not in (output / "MANIFEST.json").read_text(encoding="utf-8")


def test_direct_200_schema_failure_does_not_call_zapi(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calendar = {"Results": [{"Code": "BBCA", "Date": "2026-08-22", "Title": "RUPS"}]}
    responses = _responses(calendar)
    responses[0] = FakeResponse("not-an-issued-history-object", status_code=200)
    _install_fake_provider(monkeypatch, responses, calendar)
    zapi_calls: list[str] = []

    def unexpected_zapi(endpoint: str, params: dict[str, object]) -> bytes:
        zapi_calls.append(endpoint)
        raise AssertionError("Zapi must not mask a malformed direct 200")

    monkeypatch.setattr(capture, "_fetch_zapi_raw", unexpected_zapi)
    with pytest.raises(SystemExit, match="FORWARD_CA_ISSUED_HISTORY_SCHEMA_INVALID"):
        _run(tmp_path, monkeypatch, responses=responses)
    assert zapi_calls == []


def test_zapi_wrong_provider_and_path_fail_closed() -> None:
    wrong_provider = json.dumps(
        {
            "project": "finance:idx:raw",
            "timestamp": "2026-08-23T14:00:00Z",
            "data": {"provider": "other", "path": "ListingActivity/GetIssuedHistory", "data": []},
        }
    ).encode("utf-8")
    with pytest.raises(SystemExit, match="FORWARD_CA_ZAPI_RAW_PROJECT_MISMATCH|FORWARD_CA_ZAPI_RAW_SOURCE_MISMATCH"):
        capture._normalize_zapi_raw_payload(wrong_provider, "/ListingActivity/GetIssuedHistory")

    wrong_path = _zapi_envelope("Home/GetCalendar", [])
    with pytest.raises(SystemExit, match="FORWARD_CA_ZAPI_RAW_SOURCE_MISMATCH"):
        capture._normalize_zapi_raw_payload(wrong_path, "/ListingActivity/GetIssuedHistory")


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


def test_transport_builder_uses_warmed_session_without_manual_user_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}
            self.calls: list[tuple[str, dict[str, object]]] = []

        def get(self, url: str, **kwargs: object) -> FakeResponse:
            self.calls.append((url, dict(kwargs)))
            return FakeResponse({"warmup": url})

    fake_session = FakeSession()
    fake_curl_requests = types.SimpleNamespace(
        Session=lambda **kwargs: fake_session,
    )
    fake_curl = types.ModuleType("curl_cffi")
    fake_curl.requests = fake_curl_requests
    monkeypatch.setitem(sys.modules, "curl_cffi", fake_curl)

    client_module = types.ModuleType("idx.core.client")
    client_module.IDXClient = FakeClient
    core_module = types.ModuleType("idx.core")
    core_module.client = client_module
    idx_module = types.ModuleType("idx")
    idx_module.core = core_module
    monkeypatch.setitem(sys.modules, "idx", idx_module)
    monkeypatch.setitem(sys.modules, "idx.core", core_module)
    monkeypatch.setitem(sys.modules, "idx.core.client", client_module)
    client, preflight = capture._build_transport_client(
        tmp_path / "provider",
        tmp_path / "stage" / "raw",
    )

    assert isinstance(client, FakeClient)
    assert len(fake_session.calls) == len(capture.TRANSPORT_WARMUP_URLS)
    assert [call[0] for call in fake_session.calls] == list(capture.TRANSPORT_WARMUP_URLS)
    assert fake_session.headers["Accept-Language"].startswith("id-ID")
    assert client_module.requests is fake_session
    assert "user-agent" not in {
        str(key).lower() for key in FakeClient.init_kwargs
    }
    assert FakeClient.init_kwargs["headers"]["referer"] == capture.TRANSPORT_API_REFERER
    assert preflight[0]["http_status"] == 200
    assert (tmp_path / "stage" / "raw" / "warmup_1.bin").is_file()


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


def test_recovery_cli_mode_is_provider_free_and_does_not_require_checkout(
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
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_forward_ca_idx_bei.py",
            "--recover-publication",
            "--phase", "POST_EOD",
            "--from-session", "2026-08-22",
            "--through-session", "2026-08-23",
            "--tickers", "BBCA,TLKM",
            "--output-dir", str(output),
            "--attestation-output", str(attestation),
        ],
    )

    assert capture.main() == 0
    assert attestation.is_file()
    assert not pending.exists()
    assert not (output / "PUBLISH.json").exists()
    assert FakeClient.calls == []
