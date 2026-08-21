import hashlib
import json
from pathlib import Path

import pytest

import idx_trade.forward_ca_attestation_v1 as ca


def _write_json(path: Path, payload) -> str:
    body = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(body)
    return hashlib.sha256(body).hexdigest()


def _phase(tmp_path: Path, phase: str, *, event=False, provider_commit=ca.PROVIDER_COMMIT):
    root = tmp_path / phase.lower()
    raw = root / "raw"
    raw.mkdir(parents=True)

    issued_payload = {"data": []}
    if event:
        issued_payload = {
            "data": [{
                "KodeEmiten": "AAA",
                "TanggalPencatatan": "2026-08-24T00:00:00",
                "JenisTindakan": "stockSplit",
            }]
        }
    issued = raw / "issued.json"
    announcements = raw / "announcements.json"
    calendar = raw / "calendar.json"
    issued_sha = _write_json(issued, issued_payload)
    announcements_sha = _write_json(announcements, {"Items": []})
    calendar_sha = _write_json(calendar, {"data": []})

    fingerprint = "a" * 64
    manifest = {
        "schema_version": ca.PHASE_SCHEMA,
        "status": "COMPLETE",
        "phase": phase,
        "provider_repository": ca.PROVIDER_REPOSITORY,
        "provider_commit": provider_commit,
        "upstream_base_url": ca.UPSTREAM_BASE_URL,
        "from_session_date": "2026-08-21",
        "through_session_date": "2026-08-24",
        "required_tickers": ["AAA"],
        "legs": {
            "issued_history": {"status": "COMPLETE"},
            "announcements": {"status": "COMPLETE"},
            "calendar": {"status": "COMPLETE"},
        },
        "calendar_schema_fingerprints": [fingerprint],
        "raw_artifacts": [
            {"leg": "issued_history", "path": "raw/issued.json", "sha256": issued_sha, "http_status": 200},
            {"leg": "announcements", "path": "raw/announcements.json", "sha256": announcements_sha, "http_status": 200},
            {"leg": "calendar", "path": "raw/calendar.json", "sha256": calendar_sha, "http_status": 200},
        ],
    }
    manifest_path = root / "MANIFEST.json"
    _write_json(manifest_path, manifest)
    return manifest_path, fingerprint


def _source(tmp_path: Path, *, event=False):
    post, fingerprint = _phase(tmp_path, "POST_EOD", event=event)
    pre, _ = _phase(tmp_path, "PREOPEN", event=event)
    source = tmp_path / "SOURCE_MANIFEST.json"
    ca.merge_phase_manifests(
        post_eod_manifest_path=post,
        preopen_manifest_path=pre,
        output_path=source,
    )
    return source, fingerprint


def test_phase_manifest_rejects_wrong_provider_pin(tmp_path):
    path, _ = _phase(tmp_path, "POST_EOD", provider_commit="0" * 40)
    with pytest.raises(ca.ForwardCAError, match="PROVIDER_COMMIT_MISMATCH"):
        ca.verify_phase_manifest(path)


def test_phase_manifest_rejects_raw_hash_mutation(tmp_path):
    path, _ = _phase(tmp_path, "POST_EOD")
    (path.parent / "raw" / "issued.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ca.ForwardCAError, match="RAW_SHA_MISMATCH"):
        ca.verify_phase_manifest(path)


def test_merge_requires_same_two_phase_scope(tmp_path):
    post, _ = _phase(tmp_path, "POST_EOD")
    pre, _ = _phase(tmp_path, "PREOPEN")
    payload = json.loads(pre.read_text(encoding="utf-8"))
    payload["required_tickers"] = ["BBB"]
    _write_json(pre, payload)
    with pytest.raises(ca.ForwardCAError, match="PHASE_SCOPE_MISMATCH:required_tickers"):
        ca.merge_phase_manifests(
            post_eod_manifest_path=post,
            preopen_manifest_path=pre,
            output_path=tmp_path / "source.json",
        )


def test_attestation_is_blocked_until_calendar_schema_is_frozen(tmp_path):
    source, _ = _source(tmp_path)
    assert ca.EXPECTED_CALENDAR_SCHEMA_FINGERPRINT is None
    with pytest.raises(ca.ForwardCAError, match="CALENDAR_SCHEMA_NOT_FROZEN"):
        ca.build_attestation(source_manifest_path=source, output_path=tmp_path / "attestation.json")


def test_no_event_attestation_after_schema_pin(monkeypatch, tmp_path):
    source, fingerprint = _source(tmp_path)
    monkeypatch.setattr(ca, "EXPECTED_CALENDAR_SCHEMA_FINGERPRINT", fingerprint)
    out = ca.build_attestation(source_manifest_path=source, output_path=tmp_path / "attestation.json")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "NO_RELEVANT_EVENTS"
    assert payload["provider_commit"] == ca.PROVIDER_COMMIT
    assert payload["evidence_rows"] == [{"reasons": [], "status": "NO_RELEVANT_EVENT", "ticker": "AAA"}]


def test_issued_history_event_blocks_no_event_attestation(monkeypatch, tmp_path):
    source, fingerprint = _source(tmp_path, event=True)
    monkeypatch.setattr(ca, "EXPECTED_CALENDAR_SCHEMA_FINGERPRINT", fingerprint)
    out = ca.build_attestation(source_manifest_path=source, output_path=tmp_path / "attestation.json")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "RELEVANT_EVENT_DETECTED"
    assert payload["evidence_rows"][0]["status"] == "RELEVANT_EVENT"
    assert any("stockSplit" in x for x in payload["evidence_rows"][0]["reasons"])
