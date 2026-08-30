from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "acquire_inc001_rights_hmetd_pilot_v1.py"
SPEC = importlib.util.spec_from_file_location("rights_hmetd_pilot", SCRIPT)
assert SPEC and SPEC.loader
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)

CANARY_SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_inc001_rights_hmetd_live_canary_v1.py"
CANARY_SPEC = importlib.util.spec_from_file_location("rights_hmetd_live_canary", CANARY_SCRIPT)
assert CANARY_SPEC and CANARY_SPEC.loader
canary = importlib.util.module_from_spec(CANARY_SPEC)
CANARY_SPEC.loader.exec_module(canary)


def target(event_id: str, ticker: str, kind: str, candidate: str) -> dict[str, str]:
    return {
        "economic_event_id": event_id,
        "ticker": ticker,
        "source_event_ids": event_id,
        "source_kinds": kind,
        "source_native_labels": "hmetd",
        "candidate_dates": candidate,
        "candidate_date": candidate,
        "cum_dates": "",
        "record_dates": "",
        "distribution_dates": "",
        "ratio_raw": "",
        "source_refs": "https://example.invalid/source",
        "evidence_sha256s": "a" * 64,
        "source_contract_ids": "CONTRACT",
        "missing_semantic": "accepted REGULAR_MARKET_EX_DATE",
    }


def test_selection_is_bounded_stratified_and_deterministic() -> None:
    rows = [
        target(f"E-{i:02d}", f"T{i:02d}", "IDX_GET_ISSUED_HISTORY", f"2021-01-{i + 1:02d}")
        for i in range(20)
    ] + [
        target(f"K-{i:02d}", f"K{i:02d}", "KSEI_REGISTERED_SECURITY_HISTORY", f"2022-01-{i + 1:02d}")
        for i in range(20)
    ]
    first = pilot.select_pilot(rows)
    second = pilot.select_pilot(rows)
    assert first == second
    assert len(first) == 12
    assert {row["source_kind"] for row in first} == {"IDX_GET_ISSUED_HISTORY", "KSEI_REGISTERED_SECURITY_HISTORY"}
    assert all(row["temporal_stratum"] in {"EARLY", "MIDDLE", "RECENT"} for row in first)
    assert len({row["ticker"] for row in first}) == 12


def test_candidate_linkage_does_not_promote_date_proximity() -> None:
    rows = [
        target("IDX-1", "TEST", "IDX_GET_ISSUED_HISTORY", "2025-01-10"),
        target("KSEI-1", "TEST", "KSEI_REGISTERED_SECURITY_HISTORY", "2025-01-24"),
    ]
    audit = pilot.candidate_linkage_audit(rows)
    assert len(audit) == 1
    assert audit[0]["classification"] == "POSSIBLE_SAME_EVENT"
    assert "prove identity" in audit[0]["reason"]


def test_idx_hmetd_action_is_source_event_evidence_only() -> None:
    body = b'{"data":[{"KodeEmiten":"TEST","JenisTindakan":"hmetd","TanggalPencatatan":"2025-01-10T00:00:00"}]}'
    records = pilot.extract_idx_records(body, "TEST", "2025-01-10")
    assert len(records) == 1
    assert records[0]["JenisTindakan"] == "hmetd"


def test_rights_document_requires_explicit_regular_market_ex_semantic(tmp_path: Path) -> None:
    raw = tmp_path / "document.pdf"
    raw.write_bytes(b"retained official bytes")
    text = tmp_path / "document.txt"
    text.write_text(
        "Tanggal Cum di Pasar Regular dan Pasar Negosiasi: 10 Januari 2025\n"
        "Tanggal Ex di Pasar Regular dan Pasar Negosiasi: 13 Januari 2025\n"
        "Tanggal Pencatatan (Recording Date): 14 Januari 2025\n"
        "Tanggal Distribusi: 20 Januari 2025\n",
        encoding="utf-8",
    )
    parsed = pilot.parse_rights_document(
        {
            "document_id": "DOC-1",
            "ticker": "TEST",
            "document_reference": "REF-1",
            "title": "HMETD TEST",
            "source_ref": "https://example.invalid/doc.pdf",
            "sha256": pilot.sha256_file(raw),
            "bytes": raw.stat().st_size,
            "status_code": 200,
            "raw_path": str(raw),
        },
        text,
    )
    assert parsed["cum_date"] == "2025-01-10"
    assert parsed["ex_date"] == "2025-01-13"
    assert parsed["record_date"] == "2025-01-14"
    assert parsed["distribution_date"] == "2025-01-20"
    assert parsed["explicit_regular_market_ex_semantic"] == "true"


def test_corrected_ksei_rights_index_discovers_mppa_style_row(tmp_path: Path) -> None:
    index = tmp_path / "rights-distribution_202606.body"
    index.write_text(
        "<html><title>Distribusi HMETD</title><tbody>"
        '<tr><td class="text-nowrap"><a href="/Announcement/Files/KSEI-15669_RIGHT_20260629_ID.pdf">'
        "KSEI-15669/JKU/0626</a></td>"
        "<td>Jadwal Kegiatan Penawaran Umum Terbatas dalam rangka Penerbitan "
        "Hak Memesan Efek Terlebih Dahulu (HMETD) PT Matahari Putra Prima Tbk (MPPA)</td>"
        '<td class="text-nowrap">29 Juni 2026</td></tr></tbody></html>',
        encoding="utf-8",
    )
    rows = pilot.parse_ksei_index(
        index,
        {"request_number": 1, "sha256": pilot.sha256_file(index)},
        "KSEI_RIGHTS_DISTRIBUTION_OFFICIAL_INDEX_CONTRACT",
    )
    assert pilot.KSEI_RIGHTS_DISTRIBUTION.endswith("/rights-distribution")
    assert len(rows) == 1
    assert rows[0]["document_reference"] == "KSEI-15669/JKU/0626"
    assert rows[0]["source_ref"].endswith("KSEI-15669_RIGHT_20260629_ID.pdf")
    assert pilot.ticker_in_title(rows[0]["title"], "MPPA")
    assert rows[0]["source_contract_id"] == "KSEI_RIGHTS_DISTRIBUTION_OFFICIAL_INDEX_CONTRACT"


def test_selected_targets_restores_source_identity_from_scope(tmp_path: Path) -> None:
    fields = ["economic_event_id", "ticker", "source_event_ids", "source_kinds", "candidate_dates", "candidate_date"]
    with (tmp_path / "rights_event_scope.csv").open("w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(fields) + "\n")
        for index in range(12):
            handle.write(f"E-{index},T{index},S-{index},KSEI_REGISTERED_SECURITY_HISTORY,2025-01-01,2025-01-01\n")
    with (tmp_path / "pilot_selection.csv").open("w", encoding="utf-8", newline="") as handle:
        handle.write("economic_event_id,ticker,source_kind,candidate_date,temporal_stratum,selection_rank,selection_reason\n")
        for index in range(12):
            handle.write(f"E-{index},T{index},KSEI_REGISTERED_SECURITY_HISTORY,2025-01-01,EARLY,{index + 1},test\n")
    selected = pilot.selected_targets(tmp_path)
    assert len(selected) == 12
    assert selected[0]["source_event_ids"] == "S-0"
    assert selected[-1]["source_kinds"] == "KSEI_REGISTERED_SECURITY_HISTORY"


def test_canary_url_contract_uses_padded_month_and_id_locale() -> None:
    assert canary.index_url("06", "2026") == (
        "https://web.ksei.co.id/publications/corporate-action-schedules/rights-distribution"
        "?Month=06&Year=2026&setLocale=id-ID"
    )


def test_canary_failure_is_fail_closed_and_does_not_continue() -> None:
    result = canary.classify_canary({"status_code": 500}, Path("missing-canary-body"))
    assert result["classification"] == "HTTP_500"
    assert result["provider_execution_stopped"] is True
    assert result["remaining_five_requests"] == 0


def test_request_contract_marks_unrecorded_transport_metadata_unknown(tmp_path: Path) -> None:
    targets = [
        {"ticker": "MPPA", "candidate_date": "2026-06-29", "prior_request_url": "old", "corrected_request_url": "new"}
    ]
    retained = tmp_path / "retained"
    retained.mkdir()
    (retained / "request_records.jsonl").write_text(
        json.dumps([
            {
                "request_kind": "SCHEDULE_INDEX",
                "requested_url": canary.index_url("06", "2026"),
                "final_url": canary.index_url("06", "2026"),
                "status_code": 200,
                "sha256": "a" * 64,
            }
        ]),
        encoding="utf-8",
    )
    (retained / "event_candidate_documents.csv").write_text(
        "ticker,document_reference,source_ref\nMPPA,KSEI-15669/JKU/0626,https://example.invalid/doc.pdf\n",
        encoding="utf-8",
    )
    diff = canary.contract_diff(targets, retained)
    assert diff["fields"]["setLocale"]["retained_success"] == "id-ID"
    assert diff["fields"]["user_agent"]["retained_success"] == "UNKNOWN_NOT_RECORDED"
    assert diff["fields"]["cookies_session"]["retained_success"] == "UNKNOWN_NOT_RECORDED"


def test_mppa_canary_performs_one_exact_get_and_retains_body(tmp_path: Path, monkeypatch) -> None:
    calls = []

    class Response:
        status = 200
        reason = "OK"
        headers = {"Content-Type": "text/html; charset=UTF-8"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"retained canary body"

        def geturl(self):
            return canary.index_url("06", "2026")

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return Response()

    monkeypatch.setattr(canary.urllib.request, "urlopen", fake_urlopen)
    raw = tmp_path / "mppa.body"
    url = canary.index_url("06", "2026")
    result = canary.perform_mppa_canary(url, raw)
    assert len(calls) == 1
    assert calls[0][0].full_url == url
    assert calls[0][0].get_method() == "GET"
    assert calls[0][1] == 30
    assert raw.read_bytes() == b"retained canary body"
    assert result["status_code"] == 200
