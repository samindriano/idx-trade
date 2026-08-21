import hashlib
import json
from pathlib import Path

import pytest

import idx_trade.forward_ca_attestation_v1 as ca


def _write_json(path: Path, payload) -> str:
    body = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(body)
    return hashlib.sha256(body).hexdigest()


def _phase(
    tmp_path: Path,
    phase: str,
    *,
    issued_event=False,
    calendar_ca_event=False,
    calendar_nonca_event=False,
    announcement_event=False,
    provider_commit=ca.PROVIDER_COMMIT,
    forged_fingerprint=False,
):
    root = tmp_path / phase.lower()
    raw = root / "raw"
    raw.mkdir(parents=True)

    issued_payload = {"data": []}
    if issued_event:
        issued_payload = {
            "data": [
                {
                    "KodeEmiten": "AAA",
                    "TanggalPencatatan": "2026-08-24T00:00:00",
                    "JenisTindakan": "stockSplit",
                }
            ]
        }

    announcement_items = []
    if announcement_event:
        announcement_items.append(
            {
                "Code": "AAA",
                "PublishDate": "2026-08-21T18:30:00",
                "AnnouncementNo": "ANN-1",
                "Title": "Pengumuman stock split AAA",
            }
        )

    calendar_results = [
        {
            "title": "ZZZZ",
            "start": "2026-08-24T00:00:00",
            "Jenis": "RUPS",
            "description": "Rapat umum pemegang saham ZZZZ",
        }
    ]
    if calendar_nonca_event:
        calendar_results.append(
            {
                "title": "AAA",
                "start": "2026-08-24T00:00:00",
                "Jenis": "RUPS",
                "description": "Rapat umum pemegang saham AAA",
            }
        )
    if calendar_ca_event:
        calendar_results.append(
            {
                "title": "AAA",
                "start": "2026-08-24T00:00:00",
                "Jenis": "stockSplit",
                "description": "tanggal awal perdagangan nominal baru Stock split AAA",
            }
        )

    issued = raw / "issued.json"
    announcements = raw / "announcements.json"
    calendar = raw / "calendar.json"
    issued_sha = _write_json(issued, issued_payload)
    announcements_sha = _write_json(announcements, {"Items": announcement_items})
    calendar_payload = {"Results": calendar_results}
    calendar_sha = _write_json(calendar, calendar_payload)

    fingerprint = ca._structural_fingerprint(calendar_payload)
    declared_fingerprint = "a" * 64 if forged_fingerprint else fingerprint
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
        "calendar_capture_scope": ca.CALENDAR_CAPTURE_SCOPE,
        "legs": {
            "issued_history": {"status": "COMPLETE"},
            "announcements": {"status": "COMPLETE"},
            "calendar": {"status": "COMPLETE"},
        },
        "calendar_schema_fingerprints": [declared_fingerprint],
        "raw_artifacts": [
            {
                "leg": "issued_history",
                "endpoint": ca.EXPECTED_ENDPOINT_BY_LEG["issued_history"],
                "path": "raw/issued.json",
                "sha256": issued_sha,
                "http_status": 200,
                "content_type": "application/json; charset=utf-8",
            },
            {
                "leg": "announcements",
                "endpoint": ca.EXPECTED_ENDPOINT_BY_LEG["announcements"],
                "path": "raw/announcements.json",
                "sha256": announcements_sha,
                "http_status": 200,
                "content_type": "application/json; charset=utf-8",
            },
            {
                "leg": "calendar",
                "endpoint": ca.EXPECTED_ENDPOINT_BY_LEG["calendar"],
                "path": "raw/calendar.json",
                "sha256": calendar_sha,
                "http_status": 200,
                "content_type": "application/json; charset=utf-8",
            },
        ],
    }
    manifest_path = root / "MANIFEST.json"
    _write_json(manifest_path, manifest)
    return manifest_path, fingerprint


def _source(tmp_path: Path, **phase_kwargs):
    post, fingerprint = _phase(tmp_path, "POST_EOD", **phase_kwargs)
    pre, _ = _phase(tmp_path, "PREOPEN", **phase_kwargs)
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


def test_phase_manifest_recomputes_calendar_fingerprint_from_raw(tmp_path):
    path, _ = _phase(tmp_path, "POST_EOD", forged_fingerprint=True)
    with pytest.raises(ca.ForwardCAError, match="CALENDAR_SCHEMA_FINGERPRINT_RAW_MISMATCH"):
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
        ca.build_attestation(
            source_manifest_path=source,
            output_path=tmp_path / "attestation.json",
        )


def test_no_event_attestation_after_schema_pin(monkeypatch, tmp_path):
    source, fingerprint = _source(tmp_path)
    monkeypatch.setattr(ca, "EXPECTED_CALENDAR_SCHEMA_FINGERPRINT", fingerprint)
    out = ca.build_attestation(
        source_manifest_path=source,
        output_path=tmp_path / "attestation.json",
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "NO_RELEVANT_EVENTS"
    assert payload["provider_commit"] == ca.PROVIDER_COMMIT
    assert payload["evidence_rows"] == [
        {"reasons": [], "status": "NO_RELEVANT_EVENT", "ticker": "AAA"}
    ]


def test_issued_history_event_blocks_no_event_attestation(monkeypatch, tmp_path):
    source, fingerprint = _source(tmp_path, issued_event=True)
    monkeypatch.setattr(ca, "EXPECTED_CALENDAR_SCHEMA_FINGERPRINT", fingerprint)
    out = ca.build_attestation(
        source_manifest_path=source,
        output_path=tmp_path / "attestation.json",
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "RELEVANT_EVENT_DETECTED"
    assert payload["evidence_rows"][0]["status"] == "RELEVANT_EVENT"
    assert any("stockSplit" in x for x in payload["evidence_rows"][0]["reasons"])


def test_calendar_ca_event_blocks_but_rups_does_not(monkeypatch, tmp_path):
    source, fingerprint = _source(tmp_path, calendar_nonca_event=True)
    monkeypatch.setattr(ca, "EXPECTED_CALENDAR_SCHEMA_FINGERPRINT", fingerprint)
    out = ca.build_attestation(
        source_manifest_path=source,
        output_path=tmp_path / "nonca.json",
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "NO_RELEVANT_EVENTS"

    tmp2 = tmp_path / "ca_case"
    tmp2.mkdir()
    source2, fingerprint2 = _source(tmp2, calendar_ca_event=True)
    monkeypatch.setattr(ca, "EXPECTED_CALENDAR_SCHEMA_FINGERPRINT", fingerprint2)
    out2 = ca.build_attestation(
        source_manifest_path=source2,
        output_path=tmp2 / "ca.json",
    )
    payload2 = json.loads(out2.read_text(encoding="utf-8"))
    assert payload2["status"] == "RELEVANT_EVENT_DETECTED"
    assert any("CALENDAR_EVENT" in x for x in payload2["evidence_rows"][0]["reasons"])


def test_from_date_ca_announcement_is_conservatively_relevant(monkeypatch, tmp_path):
    source, fingerprint = _source(tmp_path, announcement_event=True)
    monkeypatch.setattr(ca, "EXPECTED_CALENDAR_SCHEMA_FINGERPRINT", fingerprint)
    out = ca.build_attestation(
        source_manifest_path=source,
        output_path=tmp_path / "announcement.json",
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "RELEVANT_EVENT_DETECTED"
    assert any("ANNOUNCEMENT" in x for x in payload["evidence_rows"][0]["reasons"])
