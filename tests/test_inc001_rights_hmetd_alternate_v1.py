from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_inc001_rights_hmetd_alternate_v1.py"
SPEC = importlib.util.spec_from_file_location("rights_alternate", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def row(event_id: str, ticker: str, source_kind: str, candidate: str) -> dict[str, str]:
    return {
        "economic_event_id": event_id,
        "ticker": ticker,
        "source_event_ids": f"source-{event_id}",
        "source_kinds": source_kind,
        "source_native_labels": "hmetd" if source_kind.startswith("IDX") else "Right Distribution",
        "candidate_dates": candidate,
        "candidate_date": candidate,
        "cum_dates": "",
        "record_dates": candidate,
        "distribution_dates": candidate,
        "ratio_raw": f"(1 {ticker} : 2 {ticker}-R)",
        "source_refs": "https://official.example/source",
        "evidence_sha256s": "a" * 64,
        "source_contract_ids": "CONTRACT",
        "missing_semantic": "accepted REGULAR_MARKET_EX_DATE",
    }


def test_selection_requires_sger_pack_and_excludes_resolved_tickers() -> None:
    targets = [
        row(audit.REQUIRED_SGER_EVENT, "SGER", "KSEI_REGISTERED_SECURITY_HISTORY", "2024-05-29"),
        row(audit.REQUIRED_PACK_EVENT, "PACK", "KSEI_REGISTERED_SECURITY_HISTORY", "2026-01-13"),
    ]
    for index in range(8):
        targets.append(row(f"IDX-{index}", f"T{index:02d}", "IDX_GET_ISSUED_HISTORY", f"202{index % 6 + 1}-01-01"))
        targets.append(row(f"KSEI-{index}", f"K{index:02d}", "KSEI_REGISTERED_SECURITY_HISTORY", f"202{index % 6 + 1}-06-01"))
    targets.extend(row(f"EXCLUDED-{ticker}", ticker, "KSEI_REGISTERED_SECURITY_HISTORY", "2025-01-01") for ticker in ("MPPA", "GMFI", "SAME"))
    selected = audit.select_pilot(targets)
    assert len(selected) == 8
    assert {item["economic_event_id"] for item in selected} >= {audit.REQUIRED_SGER_EVENT, audit.REQUIRED_PACK_EVENT}
    assert not {item["ticker"] for item in selected} & {"MPPA", "GMFI", "SAME"}


def test_regular_market_ex_parser_requires_explicit_regular_market_semantics() -> None:
    assert audit.parse_regular_ex("Tanggal Ex di Pasar Reguler: 29 Mei 2024") == "2024-05-29"
    assert audit.parse_regular_ex("Tanggal Ex di Pasar Regular dan Pasar Negosiasi: 13 Januari 2026") == "2026-01-13"
    assert audit.parse_regular_ex("Tanggal Pencatatan: 29 Mei 2024; Tanggal Distribusi: 14 Juni 2024") == ""


def test_official_url_rejects_non_idx_hosts() -> None:
    assert audit.official_url("https://www.idx.co.id/Announcement/Files/a.pdf")
    assert audit.official_url("https://example.com/a.pdf") == ""
    assert audit.official_url("http://www.idx.co.id/a.pdf") == ""


def test_result_classification_preserves_provider_failure_and_no_document() -> None:
    target = row("E1", "SGER", "KSEI_REGISTERED_SECURITY_HISTORY", "2024-05-29")
    failed = audit.result_for_target(target, announcements=[], documents=[], provider_failed=True)
    assert failed["result_classification"] == "PROVIDER_DISCOVERY_FAILURE"
    empty = audit.result_for_target(target, announcements=[], documents=[], provider_failed=False)
    assert empty["result_classification"] == "NO_ALTERNATE_OFFICIAL_DOCUMENT_DISCOVERED"


def test_result_classification_does_not_accept_document_without_ex_semantic() -> None:
    target = row("E1", "PACK", "KSEI_REGISTERED_SECURITY_HISTORY", "2026-01-13")
    announcements = [{"ticker": "PACK", "title": "HMETD", "subject": "Jadwal pelaksanaan"}]
    documents = [{"ticker": "PACK", "regular_market_ex_date": "", "associated_event_ids": "E1", "linkage_status": "UNRESOLVED"}]
    result = audit.result_for_target(target, announcements=announcements, documents=documents, provider_failed=False)
    assert result["result_classification"] == "OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT"


def test_date_window_is_deterministic_from_retained_candidate_dates() -> None:
    target = row("E1", "PACK", "KSEI_REGISTERED_SECURITY_HISTORY", "2026-01-13")
    assert audit.date_window(target) == ("2025-07-17", "2026-07-12")


def exact_document(target: dict[str, str], *, associated_event_ids: str | None = None) -> dict[str, str | int]:
    return {
        "ticker": target["ticker"],
        "source_ref": "https://www.idx.co.id/Announcement/Files/rights.pdf",
        "evidence_sha256": "b" * 64,
        "bytes": 128,
        "rights_semantics": "true",
        "regular_market_ex_date": target["candidate_date"],
        "document_date_values": target["candidate_dates"],
        "document_ratio_signatures": "1:2",
        "associated_event_ids": associated_event_ids or target["economic_event_id"],
        "linkage_status": "UNRESOLVED",
    }


def test_document_linkage_requires_target_dates_ratio_and_hash_bound_source() -> None:
    target = row("E1", "PACK", "KSEI_REGISTERED_SECURITY_HISTORY", "2026-01-13")
    target["candidate_dates"] = "2026-01-10|2026-01-13"
    document = exact_document(target)
    assert audit.document_linkage_status(document, target)[0] == "LINKED_EXACT"

    missing_date = dict(document, document_date_values="2026-01-13")
    assert audit.document_linkage_status(missing_date, target)[0] == "UNRESOLVED"
    missing_ratio = dict(document, document_ratio_signatures="")
    assert audit.document_linkage_status(missing_ratio, target)[0] == "UNRESOLVED"
    missing_hash = dict(document, evidence_sha256="")
    assert audit.document_linkage_status(missing_hash, target)[0] == "UNRESOLVED"


def test_result_does_not_use_same_ticker_document_for_another_event() -> None:
    target = row("E1", "PACK", "KSEI_REGISTERED_SECURITY_HISTORY", "2026-01-13")
    document = exact_document(target, associated_event_ids="E2")
    result = audit.result_for_target(
        target,
        announcements=[{"ticker": "PACK", "title": "HMETD", "subject": "Jadwal"}],
        documents=[document],
        provider_failed=False,
    )
    assert result["result_classification"] == "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE"


def test_shared_attachment_is_linkage_ambiguous_even_with_exact_semantics() -> None:
    target = row("E1", "PACK", "KSEI_REGISTERED_SECURITY_HISTORY", "2026-01-13")
    document = exact_document(target, associated_event_ids="E1|E2")
    document["linkage_status"] = "AMBIGUOUS_SHARED_ATTACHMENT"
    result = audit.result_for_target(
        target,
        announcements=[{"ticker": "PACK", "title": "HMETD", "subject": "Jadwal"}],
        documents=[document],
        provider_failed=False,
    )
    assert result["result_classification"] == "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS"


def test_pagination_requires_explicit_single_page_completeness() -> None:
    assert audit.pagination_attestation({"ResultCount": 1, "Replies": [{}]}, 200)[0] is True
    assert audit.pagination_attestation({"ResultCount": 201, "Replies": [{}] * 200}, 200)[0] is False
    assert audit.pagination_attestation({"Replies": [{}]}, 200)[0] is False


def test_manifest_output_hashes_are_all_verified(tmp_path: Path) -> None:
    output = tmp_path / "output.json"
    output.write_bytes(b"payload\n")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = tmp_path / "MANIFEST.json"
    manifest.write_text(json.dumps({"output_hashes_excluding_manifest": {"output.json": {"bytes": output.stat().st_size, "sha256": digest}}}), encoding="utf-8")
    checked = audit.verify_manifest_outputs(tmp_path, audit.sha256_file(manifest))
    assert checked["output_count"] == 1
    output.write_bytes(b"tampered\n")
    with pytest.raises(RuntimeError, match="mismatch"):
        audit.verify_manifest_outputs(tmp_path)
