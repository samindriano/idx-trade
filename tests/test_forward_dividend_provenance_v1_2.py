from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from idx_trade.forward_dividend_provenance_v1_2 import (
    AUTHORITY_V1_2,
    REVIEW_SCHEMA_V1_2,
    REVIEW_STATUS_V1_2,
    ForwardDividendProvenanceV12Error,
    canonical_event_evidence_v1_2,
    canonical_sha256,
    certify_direct_idx_dividend_from_attachment_review_v1_2,
    event_sha256_v1_2,
    resolve_discovery_manifest_path_v1_2,
    resolve_exact_announcement_provenance,
    resolve_file_by_sha_within_root_v1_2,
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _announcement(
    *,
    title: str = "Jadwal Dividen Tunai Interim",
) -> dict[str, object]:
    return {
        "Id2": "20260819183103-005/CSG-IVR/2026_id-id",
        "Id": None,
        "NoPengumuman": "005/CSG-IVR/2026",
        "Kode_Emiten": "BBCA",
        "TglPengumuman": "2026-08-19T18:31:03",
        "CreatedDate": "2026-08-19T18:31:04",
        "JudulPengumuman": title,
        "PerihalPengumuman": "",
        "Form_Id": "11000",
        "ExtraStableField": {
            "nested": True,
            "number": 25,
        },
    }


def _candidate() -> dict[str, object]:
    return {
        "ticker": "BBCA",
        "announcement_id": (
            "20260819183103-005/CSG-IVR/2026_id-id"
        ),
        "announcement_number": "005/CSG-IVR/2026",
        "announcement_timestamp": "2026-08-19T18:31:03",
        "title": "Jadwal Dividen Tunai Interim",
        "form_id": "11000",
        "classification": "CASH_DIVIDEND_CANDIDATE",
    }


def _write_discovery(
    root: Path,
    *,
    page_name: str,
    replies: list[dict[str, object]],
) -> tuple[Path, dict[str, object], str]:
    root.mkdir(parents=True, exist_ok=True)

    page = root / page_name
    raw = (
        json.dumps(
            {"Replies": replies},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    page.write_bytes(raw)

    page_sha = _sha(raw)

    discovery = {
        "schema_version": (
            "idx_trade_forward_dividend_announcement_capture_v1"
        ),
        "status": "COMPLETE",
        "raw_artifacts": [
            {
                "ticker": "BBCA",
                "path": page_name,
                "sha256": page_sha,
            }
        ],
        "candidates": [_candidate()],
    }

    manifest = root / "DISCOVERY_MANIFEST.json"
    manifest.write_text(
        json.dumps(discovery, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return manifest, discovery, page_sha


def test_canonical_json_hash_is_key_order_invariant():
    left = {
        "b": 2,
        "a": {
            "z": 3,
            "y": 4,
        },
    }
    right = {
        "a": {
            "y": 4,
            "z": 3,
        },
        "b": 2,
    }

    assert canonical_sha256(left) == canonical_sha256(right)


def test_same_announcement_different_query_pages_is_window_invariant(
    tmp_path: Path,
):
    narrow_record = _announcement()

    narrow_manifest, narrow_discovery, narrow_page_sha = (
        _write_discovery(
            tmp_path / "narrow",
            page_name="BBCA_page_001.json",
            replies=[
                {
                    "pengumuman": narrow_record,
                    "attachments": [],
                }
            ],
        )
    )

    bootstrap_record = _announcement()

    bootstrap_manifest, bootstrap_discovery, bootstrap_page_sha = (
        _write_discovery(
            tmp_path / "bootstrap",
            page_name="BBCA_page_001.json",
            replies=[
                {
                    "pengumuman": {
                        "Id2": "OTHER-1",
                        "NoPengumuman": "OTHER/1",
                        "Kode_Emiten": "BBCA",
                        "TglPengumuman": "2025-11-24T10:00:00",
                        "JudulPengumuman": "Older unrelated row",
                        "Form_Id": "999",
                    },
                    "attachments": [],
                },
                {
                    "pengumuman": bootstrap_record,
                    "attachments": [],
                },
                {
                    "pengumuman": {
                        "Id2": "OTHER-2",
                        "NoPengumuman": "OTHER/2",
                        "Kode_Emiten": "BBCA",
                        "TglPengumuman": "2026-06-05T10:00:00",
                        "JudulPengumuman": "Another unrelated row",
                        "Form_Id": "999",
                    },
                    "attachments": [],
                },
            ],
        )
    )

    narrow = resolve_exact_announcement_provenance(
        discovery_path=narrow_manifest,
        discovery=narrow_discovery,
        candidate=_candidate(),
    )

    bootstrap = resolve_exact_announcement_provenance(
        discovery_path=bootstrap_manifest,
        discovery=bootstrap_discovery,
        candidate=_candidate(),
    )

    assert narrow_page_sha != bootstrap_page_sha

    assert (
        narrow.announcement_record_sha256
        == bootstrap.announcement_record_sha256
    )

    assert (
        narrow.announcement_record
        == bootstrap.announcement_record
    )

    assert narrow.source_raw_page_sha256 == (
        narrow_page_sha,
    )
    assert bootstrap.source_raw_page_sha256 == (
        bootstrap_page_sha,
    )


def test_conflicting_same_identity_records_fail_closed(
    tmp_path: Path,
):
    root = tmp_path / "conflict"
    root.mkdir()

    record_a = _announcement()
    record_b = _announcement(
        title="CHANGED TITLE FOR SAME IDENTITY"
    )

    rows = []

    for index, record in enumerate(
        (record_a, record_b),
        start=1,
    ):
        page_name = f"BBCA_page_{index:03d}.json"
        raw = (
            json.dumps(
                {
                    "Replies": [
                        {
                            "pengumuman": record,
                            "attachments": [],
                        }
                    ]
                },
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")

        (root / page_name).write_bytes(raw)

        rows.append(
            {
                "ticker": "BBCA",
                "path": page_name,
                "sha256": _sha(raw),
            }
        )

    discovery = {
        "raw_artifacts": rows,
        "candidates": [_candidate()],
    }

    manifest = root / "DISCOVERY_MANIFEST.json"
    manifest.write_text(
        json.dumps(discovery),
        encoding="utf-8",
    )

    with pytest.raises(
        ForwardDividendProvenanceV12Error,
        match="EXACT_ANNOUNCEMENT_CONFLICT",
    ):
        resolve_exact_announcement_provenance(
            discovery_path=manifest,
            discovery=discovery,
            candidate=_candidate(),
        )


def test_event_hash_does_not_include_transport_page_sha():
    record_sha = canonical_sha256(_announcement())

    base = canonical_event_evidence_v1_2(
        announcement_record_sha256=record_sha,
        document_sha256=[
            "a" * 64,
            "b" * 64,
        ],
        ticker="BBCA",
        announcement_timestamp="2026-08-19T18:31:03",
        gross_dividend_per_share_idr="25",
        cum_date="2026-08-28",
        ex_date="2026-08-31",
        record_date="2026-09-01",
        payment_date="2026-09-16",
    )

    # There is intentionally no raw-page SHA field in canonical
    # V1.2 event evidence.
    assert "source_raw_page_sha256" not in base
    assert "raw_page_sha256" not in base
    assert event_sha256_v1_2(base) == event_sha256_v1_2(
        dict(base)
    )


def _review(
    *,
    record: dict[str, object],
    record_sha: str,
    pdf_sha: str,
    transport_page_sha: str,
    discovery_manifest_path: Path,
    attachment_manifest_sha: str,
) -> dict[str, object]:
    return {
        "schema_version": REVIEW_SCHEMA_V1_2,
        "status": REVIEW_STATUS_V1_2,
        "authority_recommendation": AUTHORITY_V1_2,
        "transport_provenance": {
            "source_raw_page_sha256": [
                transport_page_sha
            ],
            "source_discovery_manifest_resolved_path": str(
                discovery_manifest_path.resolve()
            ),
            "source_discovery_manifest_sha256": _sha(
                discovery_manifest_path.read_bytes()
            ),
            "source_attachment_manifest_sha256": (
                attachment_manifest_sha
            ),
        },
        "announcement_provenance": {
            "exact_announcement_record": record,
            "announcement_record_sha256": record_sha,
        },
        "announcement": {
            "id": (
                "20260819183103-005/CSG-IVR/2026_id-id"
            ),
            "number": "005/CSG-IVR/2026",
            "date": "2026-08-19T18:31:03",
            "code": "BBCA",
            "title": "Jadwal Dividen Tunai Interim",
            "form_id": "11000",
        },
        "documents": [
            {
                "pdf_filename": "official.pdf",
                "sha256": pdf_sha,
            }
        ],
        "expected_event": {
            "ticker": "BBCA",
            "gross_dividend_per_share_idr": "25",
            "cum_regular_negotiated": "2026-08-28",
            "ex_regular_negotiated": "2026-08-31",
            "record_date": "2026-09-01",
            "payment_date": "2026-09-16",
        },
        "semantic_matches": {
            "ticker": True,
            "dividend_subject": True,
            "dividend_per_share": True,
            "cum_regular_negotiated": True,
            "ex_regular_negotiated": True,
            "record_date": True,
            "payment_date": True,
        },
        "documents_count": 1,
        "failures": [],
        "warnings": [],
    }


def _write_semantic_pdf(path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    fonts = DictionaryObject({NameObject("/F1"): font_ref})
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): fonts}
    )

    content = (
        b"BT /F1 12 Tf 72 720 Td (BBCA cash dividend Rp 25 per share. "
        b"Cum dividend 28 August 2026. Ex dividend 31 August 2026. "
        b"Record date 1 September 2026. Payment date 16 September 2026.) "
        b"Tj ET"
    )
    stream = DecodedStreamObject()
    stream.set_data(content)
    page[NameObject("/Contents")] = writer._add_object(stream)

    with path.open("wb") as handle:
        writer.write(handle)


def test_certification_is_query_window_invariant(
    tmp_path: Path,
):
    record = _announcement()
    record_sha = canonical_sha256(record)

    pdf = tmp_path / "official.pdf"
    _write_semantic_pdf(pdf)
    pdf_sha = _sha(pdf.read_bytes())

    attachment_manifest = {
        "schema_version": (
            "idx_trade_forward_dividend_attachment_capture_v1_1"
        ),
        "status": "COMPLETE_AWAITING_SEMANTIC_REVIEW",
        "candidate": _candidate(),
        "attachments": [
            {
                "pdf_filename": "official.pdf",
                "sha256": pdf_sha,
            }
        ],
    }
    attachment_manifest_path = (
        tmp_path / "ATTACHMENT_CAPTURE_MANIFEST.json"
    )
    attachment_manifest_path.write_text(
        json.dumps(attachment_manifest, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    attachment_manifest_sha = _sha(
        attachment_manifest_path.read_bytes()
    )

    discovery_root = tmp_path / "runtime" / "batches"
    narrow_manifest, _, narrow_page_sha = _write_discovery(
        discovery_root / "2026-08-22_PREOPEN" / "discovery",
        page_name="BBCA_page_001.json",
        replies=[
            {
                "pengumuman": record,
                "attachments": [],
            }
        ],
    )
    bootstrap_manifest, _, bootstrap_page_sha = _write_discovery(
        discovery_root / "2026-08-22_POST_EOD" / "discovery",
        page_name="BBCA_page_001.json",
        replies=[
            {
                "pengumuman": {
                    "Id2": "OTHER-1",
                    "NoPengumuman": "OTHER/1",
                    "Kode_Emiten": "BBCA",
                    "TglPengumuman": "2025-11-24T10:00:00",
                    "JudulPengumuman": "Older unrelated row",
                    "Form_Id": "999",
                },
                "attachments": [],
            },
            {
                "pengumuman": record,
                "attachments": [],
            },
        ],
    )

    review_a = _review(
        record=record,
        record_sha=record_sha,
        pdf_sha=pdf_sha,
        transport_page_sha=narrow_page_sha,
        discovery_manifest_path=narrow_manifest,
        attachment_manifest_sha=attachment_manifest_sha,
    )
    review_b = _review(
        record=record,
        record_sha=record_sha,
        pdf_sha=pdf_sha,
        transport_page_sha=bootstrap_page_sha,
        discovery_manifest_path=bootstrap_manifest,
        attachment_manifest_sha=attachment_manifest_sha,
    )

    path_a = tmp_path / "review_a.json"
    path_b = tmp_path / "review_b.json"

    path_a.write_text(
        json.dumps(review_a, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path_b.write_text(
        json.dumps(review_b, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    event_a = (
        certify_direct_idx_dividend_from_attachment_review_v1_2(
            path_a,
            tmp_path,
        )
    )
    event_b = (
        certify_direct_idx_dividend_from_attachment_review_v1_2(
            path_b,
            tmp_path,
        )
    )

    assert event_a.event_id == event_b.event_id
    assert (
        event_a.source_evidence_sha256
        == event_b.source_evidence_sha256
    )
    assert event_a.ticker == "BBCA"
    assert event_a.gross_dividend_per_share_idr == 25.0
    assert event_a.cum_date == "2026-08-28"
    assert event_a.ex_date == "2026-08-31"
    assert event_a.record_date == "2026-09-01"
    assert event_a.payment_date == "2026-09-16"


def test_high_precision_amount_is_preserved_in_event_hash():
    evidence = canonical_event_evidence_v1_2(
        announcement_record_sha256="e" * 64,
        document_sha256=["f" * 64],
        ticker="TLKM",
        announcement_timestamp="2026-06-19T10:00:00",
        gross_dividend_per_share_idr="223.1658777",
        cum_date="2026-06-23",
        ex_date="2026-06-24",
        record_date="2026-06-25",
        payment_date="2026-07-10",
    )

    assert (
        evidence["gross_dividend_per_share_idr"]
        == "223.1658777"
    )


def test_correction_published_after_cum_date_is_provenance_valid():
    evidence = canonical_event_evidence_v1_2(
        announcement_record_sha256="e" * 64,
        document_sha256=["f" * 64],
        ticker="TLKM",
        announcement_timestamp="2026-06-19T13:51:49",
        gross_dividend_per_share_idr="223.1658777",
        cum_date="2026-06-17",
        ex_date="2026-06-18",
        record_date="2026-06-19",
        payment_date="2026-07-10",
    )

    assert evidence["announcement_timestamp"] == (
        "2026-06-19T13:51:49"
    )
    assert evidence["cum_date"] == "2026-06-17"


def test_stale_partial_discovery_path_recovers_by_sha(
    tmp_path: Path,
):
    batches = tmp_path / "runtime" / "batches"

    stale = (
        batches
        / ".2026-08-22_POST_EOD.partial.deadbeef"
        / "discovery"
        / "DISCOVERY_MANIFEST.json"
    )

    final = (
        batches
        / "2026-08-22_POST_EOD"
        / "discovery"
        / "DISCOVERY_MANIFEST.json"
    )

    final.parent.mkdir(parents=True)

    raw = (
        b'{"schema_version":"test","status":"COMPLETE"}\n'
    )
    final.write_bytes(raw)

    declared_sha = _sha(raw)

    assert not stale.exists()

    resolved = resolve_discovery_manifest_path_v1_2(
        declared_path=stale,
        declared_sha256=declared_sha,
    )

    assert resolved == final.resolve()


def test_stale_path_recovery_fails_if_sha_match_ambiguous(
    tmp_path: Path,
):
    root = tmp_path / "bounded"
    left = root / "a" / "artifact.json"
    right = root / "b" / "artifact.json"

    left.parent.mkdir(parents=True)
    right.parent.mkdir(parents=True)

    raw = b'{"stable":true}\n'

    left.write_bytes(raw)
    right.write_bytes(raw)

    stale = root / ".partial" / "artifact.json"

    with pytest.raises(
        ForwardDividendProvenanceV12Error,
        match="AMBIGUOUS",
    ):
        resolve_file_by_sha_within_root_v1_2(
            declared_path=stale,
            declared_sha256=_sha(raw),
            search_root=root,
            missing_code="MISSING",
            mismatch_code="MISMATCH",
            ambiguous_code="AMBIGUOUS",
        )


def test_existing_declared_path_sha_mismatch_does_not_search_fallback(
    tmp_path: Path,
):
    root = tmp_path / "bounded"

    declared = root / "staging" / "artifact.json"
    valid_elsewhere = root / "final" / "artifact.json"

    declared.parent.mkdir(parents=True)
    valid_elsewhere.parent.mkdir(parents=True)

    declared.write_bytes(b'{"wrong":true}\n')
    good = b'{"correct":true}\n'
    valid_elsewhere.write_bytes(good)

    with pytest.raises(
        ForwardDividendProvenanceV12Error,
        match="MISMATCH",
    ):
        resolve_file_by_sha_within_root_v1_2(
            declared_path=declared,
            declared_sha256=_sha(good),
            search_root=root,
            missing_code="MISSING",
            mismatch_code="MISMATCH",
            ambiguous_code="AMBIGUOUS",
        )
