from __future__ import annotations

from idx_trade.v4_ca_event_windows import event_identity
from idx_trade.v4_ca_residual_document_semantics import (
    cash_document_class,
    classify_event_with_residual_document_evidence,
    parse_residual_document,
    resolve_event_document_evidence,
)


SESSIONS = [
    "2024-07-03",
    "2024-07-04",
    "2024-07-05",
    "2024-07-08",
    "2026-04-14",
    "2026-04-15",
    "2026-04-16",
]


def _doc(parsed, *, reference="KSEI-1/JKU/0426", sha="a" * 64):
    return {
        "parsed": parsed,
        "reference": reference,
        "source_url": "https://web.ksei.co.id/example.pdf",
        "source_sha256": sha,
    }


def _event(*, event_id="event-1", ticker="ABCD", source_type="Voluntary Conversion", source_dates="2026-04-15"):
    return {
        "event_id": event_id,
        "ticker": ticker,
        "source_type": source_type,
        "source_dates": source_dates,
    }


def test_voluntary_tender_exact_payment_link_is_nonblocking():
    text = """
    Perihal : Jadwal Penawaran Tender Sukarela atas saham PT Example Tbk (ABCD)
    Kode Saham ABCD
    Tanggal Pembayaran hasil Penawaran Tender 15 April 2026
    """
    parsed = parse_residual_document(text, expected_ticker="ABCD")
    assert parsed.document_class == "VOLUNTARY_TENDER_OFFER"
    assert parsed.cash_identity_dates == ("2026-04-15",)
    evidence = resolve_event_document_evidence(
        _event(), [_doc(parsed)], official_sessions=SESSIONS
    )
    assert evidence.linkage_status == "EXACT_NON_BLOCKING"
    assert evidence.evidence_kind == "VOLUNTARY_CASH_NON_BLOCKING"


def test_mandatory_tender_is_cash_semantic_for_voluntary_conversion():
    text = """
    Jadwal Penawaran Tender Wajib atas saham PT Example Tbk (ABCD)
    Tanggal Penyelesaian Transaksi 15 April 2026
    """
    parsed = parse_residual_document(text, expected_ticker="ABCD")
    assert parsed.document_class == "MANDATORY_TENDER_OFFER"
    evidence = resolve_event_document_evidence(
        _event(), [_doc(parsed)], official_sessions=SESSIONS
    )
    assert evidence.linkage_status == "EXACT_NON_BLOCKING"


def test_buyback_cash_document_classification():
    text = """
    Jadwal Pembelian Kembali Saham PT Example Tbk (ABCD)
    Tanggal Pembelian Kembali 15 April 2026
    """
    assert cash_document_class(text) == "SHARE_BUYBACK_CASH"


def test_dissenting_shareholder_cash_repurchase_precedence():
    text = """
    Pembelian Kembali Saham ABCD bagi pemegang saham yang tidak setuju
    atas penggabungan perseroan. Tanggal Pembayaran 15 April 2026.
    """
    assert cash_document_class(text) == "DISSENTING_SHAREHOLDER_CASH_REPURCHASE"


def test_cash_document_without_exact_source_date_stays_unresolved():
    text = """
    Penawaran Tender Sukarela saham ABCD
    Tanggal Pembayaran 16 April 2026
    """
    parsed = parse_residual_document(text, expected_ticker="ABCD")
    evidence = resolve_event_document_evidence(
        _event(source_dates="2026-04-15"), [_doc(parsed)], official_sessions=SESSIONS
    )
    assert evidence.linkage_status == "UNRESOLVED"


def test_cash_document_never_nonblocks_mandatory_conversion():
    text = """
    Penawaran Tender Wajib saham ABCD
    Tanggal Pembayaran 15 April 2026
    """
    parsed = parse_residual_document(text, expected_ticker="ABCD")
    evidence = resolve_event_document_evidence(
        _event(source_type="Mandatory Conversion"),
        [_doc(parsed)],
        official_sessions=SESSIONS,
    )
    assert evidence.linkage_status == "UNRESOLVED"


def test_stock_split_layout_first_new_basis_is_exact_transition():
    plain = """
    Stock Split PT Example Tbk ABCD
    Tanggal Pencatatan (Recording Date) 5 Juli 2024
    Tanggal distribusi saham dengan Nilai Nominal Baru 8 Juli 2024
    """
    layout = """
    Akhir perdagangan saham dengan Nilai Nominal Lama di Pasar Reguler 3 Juli 2024
    Mulai perdagangan saham dengan Nilai Nominal Baru di Pasar Reguler 4 Juli 2024
    Tanggal Pencatatan (Recording Date) 5 Juli 2024
    Tanggal distribusi saham dengan Nilai Nominal Baru 8 Juli 2024
    """
    parsed = parse_residual_document(
        plain, expected_ticker="ABCD", layout_text=layout
    )
    assert parsed.event_family == "STOCK_SPLIT"
    assert parsed.transition_date == "2024-07-04"
    assert parsed.transition_semantic == "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"
    evidence = resolve_event_document_evidence(
        _event(
            ticker="ABCD",
            source_type="Mandatory Conversion",
            source_dates="2024-07-05|2024-07-08",
        ),
        [_doc(parsed)],
        official_sessions=SESSIONS,
    )
    assert evidence.linkage_status == "EXACT"
    assert evidence.transition_date == "2024-07-04"


def test_record_distribution_never_become_transition_fallback():
    plain = """
    Stock Split PT Example Tbk ABCD
    Tanggal Pencatatan (Recording Date) 5 Juli 2024
    Tanggal distribusi saham 8 Juli 2024
    """
    parsed = parse_residual_document(plain, expected_ticker="ABCD")
    assert parsed.transition_date is None
    evidence = resolve_event_document_evidence(
        _event(
            ticker="ABCD",
            source_type="Mandatory Conversion",
            source_dates="2024-07-05|2024-07-08",
        ),
        [_doc(parsed)],
        official_sessions=SESSIONS,
    )
    assert evidence.linkage_status == "UNRESOLVED"


def test_transition_must_be_official_session():
    plain = """
    Stock Split ABCD
    Tanggal Pencatatan (Recording Date) 5 Juli 2024
    Tanggal distribusi saham 8 Juli 2024
    """
    layout = "Mulai perdagangan saham dengan Nilai Nominal Baru di Pasar Reguler 6 Juli 2024"
    parsed = parse_residual_document(
        plain, expected_ticker="ABCD", layout_text=layout
    )
    assert parsed.transition_date == "2024-07-06"
    evidence = resolve_event_document_evidence(
        _event(
            ticker="ABCD",
            source_type="Mandatory Conversion",
            source_dates="2024-07-05|2024-07-08",
        ),
        [_doc(parsed)],
        official_sessions=SESSIONS,
    )
    assert evidence.linkage_status == "UNRESOLVED"


def test_conflicting_exact_transition_documents_fail_closed():
    plain = """
    Stock Split ABCD
    Tanggal Pencatatan 5 Juli 2024
    Tanggal distribusi 8 Juli 2024
    """
    first = parse_residual_document(
        plain,
        expected_ticker="ABCD",
        layout_text="Mulai perdagangan saham dengan Nilai Nominal Baru di Pasar Reguler 4 Juli 2024",
    )
    second = parse_residual_document(
        plain,
        expected_ticker="ABCD",
        layout_text="Mulai perdagangan saham dengan Nilai Nominal Baru di Pasar Reguler 3 Juli 2024",
    )
    evidence = resolve_event_document_evidence(
        _event(
            source_type="Mandatory Conversion",
            source_dates="2024-07-05|2024-07-08",
        ),
        [_doc(first, reference="KSEI-A"), _doc(second, reference="KSEI-B", sha="b" * 64)],
        official_sessions=SESSIONS,
    )
    assert evidence.linkage_status == "CONFLICT"


def test_ticker_identity_is_exact_token_not_substring():
    text = "Penawaran Tender Sukarela saham XABCDY Tanggal Pembayaran 15 April 2026"
    parsed = parse_residual_document(text, expected_ticker="ABCD")
    assert parsed.ticker_evidenced is False


def test_layout_anchor_does_not_steal_date_from_next_semantic_row():
    plain = "Stock Split ABCD Tanggal Pencatatan 8 Juli 2024"
    layout = """
    Mulai perdagangan saham dengan Nilai Nominal Baru di Pasar Reguler
    Tanggal Pencatatan (Recording Date) 8 Juli 2024
    """
    parsed = parse_residual_document(
        plain, expected_ticker="ABCD", layout_text=layout
    )
    assert parsed.transition_date is None


def _ksei_row():
    return {
        "ticker": "ABCD",
        "row_index": 1,
        "event_family_source": "Voluntary Conversion",
        "cum_date": None,
        "record_date": None,
        "distribution_date": "2026-04-15",
        "status": "Active",
        "ratio_raw": "",
        "ratio_parse_status": "UNRESOLVED_SOURCE_TEXT",
        "ratio_left_security": None,
        "ratio_right_security": None,
        "source_sha256": "c" * 64,
    }


def test_classifier_overlay_accepts_exact_nonblocking_cash_evidence():
    row = _ksei_row()
    event_id = event_identity(row)
    evidence = [
        {
            "event_id": event_id,
            "linkage_status": "EXACT_NON_BLOCKING",
            "evidence_kind": "VOLUNTARY_CASH_NON_BLOCKING",
            "ksei_reference": "KSEI-1/JKU/0426",
            "source_sha256": "a" * 64,
        }
    ]
    result = classify_event_with_residual_document_evidence(
        row, official_sessions=SESSIONS, schedule_evidence=evidence
    )
    assert result.semantic_class == "NON_BLOCKING"
    assert result.family == "VOLUNTARY_CASH_DOCUMENT_SETTLEMENT"


def test_classifier_overlay_ignores_unresolved_cash_claim():
    row = _ksei_row()
    event_id = event_identity(row)
    evidence = [
        {
            "event_id": event_id,
            "linkage_status": "UNRESOLVED",
            "evidence_kind": "VOLUNTARY_CASH_NON_BLOCKING",
            "ksei_reference": "KSEI-1",
            "source_sha256": "a" * 64,
        }
    ]
    result = classify_event_with_residual_document_evidence(
        row, official_sessions=SESSIONS, schedule_evidence=evidence
    )
    assert result.semantic_class == "SCHEDULE_REQUIRED"


def test_classifier_overlay_cash_and_exact_transition_conflict_fails_closed():
    row = _ksei_row()
    event_id = event_identity(row)
    evidence = [
        {
            "event_id": event_id,
            "linkage_status": "EXACT_NON_BLOCKING",
            "evidence_kind": "VOLUNTARY_CASH_NON_BLOCKING",
            "ksei_reference": "KSEI-CASH",
            "source_sha256": "a" * 64,
        },
        {
            "event_id": event_id,
            "linkage_status": "EXACT",
            "evidence_kind": "EXACT_TRANSITION",
            "transition_semantic": "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
            "transition_date": "2026-04-15",
            "ksei_reference": "KSEI-TRANSITION",
            "source_sha256": "b" * 64,
        },
    ]
    result = classify_event_with_residual_document_evidence(
        row, official_sessions=SESSIONS, schedule_evidence=evidence
    )
    assert result.semantic_class == "SCHEDULE_REQUIRED"
    assert "CONFLICT" in result.reason
