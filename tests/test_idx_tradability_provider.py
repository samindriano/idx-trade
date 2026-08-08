import hashlib

import pandas as pd

from idx_trade.providers.idx_tradability import (
    compile_suspension_intervals,
    ingest_announcement_manifest,
    parse_idx_tradability_announcement,
)


def test_parses_regular_cash_suspension():
    text = """
    Peng-SPT-00110/BEI.WAS/06-2025
    Bursa melakukan penghentian sementara perdagangan saham PT Example Tbk (TEST)
    pada tanggal 1 Juli 2025. Penghentian tersebut dilakukan di Pasar Reguler dan Pasar Tunai.
    """
    result = parse_idx_tradability_announcement(text, source_ref="idx://suspend")
    assert result.status == "PARSED"
    assert set(result.events["market"]) == {"REGULAR", "CASH"}
    assert set(result.events["action"]) == {"SUSPEND"}
    assert result.events["effective_date"].unique().tolist() == [pd.Timestamp("2025-07-01")]
    assert set(result.events["ticker"]) == {"TEST"}


def test_effective_session_date_wins_over_earlier_announcement_date():
    text = """
    Peng-SPT-00110/BEI.WAS/06-2025 diumumkan pada tanggal 30 Juni 2025.
    Bursa melakukan penghentian sementara perdagangan saham PT Example Tbk (TEST)
    mulai sesi I tanggal 1 Juli 2025 di Pasar Reguler.
    """
    result = parse_idx_tradability_announcement(text, source_ref="idx://effective-date")
    assert result.status == "PARSED"
    assert result.events["effective_date"].unique().tolist() == [pd.Timestamp("2025-07-01")]


def test_ambiguous_effective_date_wording_requires_manual_review():
    text = """
    Bursa melakukan penghentian sementara perdagangan saham PT Example Tbk (TEST)
    di Pasar Reguler mulai sesi I tanggal 1 Juli 2025 atau tanggal 2 Juli 2025.
    """
    result = parse_idx_tradability_announcement(text, source_ref="idx://ambiguous-date")
    assert result.status == "MANUAL_REVIEW"
    assert result.diagnostic == "AMBIGUOUS_EFFECTIVE_DATE"
    assert result.events.empty


def test_stock_market_scope_wins_over_warrant_all_market_phrase():
    text = """
    Peng-UPT-00050/BEI.WAS/03-2025
    Suspensi saham PT Example Tbk (TEST) di Pasar Reguler dan Pasar Tunai serta waran seri I
    PT Example Tbk (TEST-W) di Seluruh Pasar dibuka kembali mulai sesi I tanggal 5 Maret 2025.
    """
    result = parse_idx_tradability_announcement(text, source_ref="idx://resume")
    assert result.status == "PARSED"
    assert set(result.events["market"]) == {"REGULAR", "CASH"}
    assert set(result.events["action"]) == {"RESUME"}
    assert set(result.events["ticker"]) == {"TEST"}


def test_intraday_negotiated_only_open_and_resuspend_requires_manual_review():
    text = """
    Bursa membuka penghentian sementara perdagangan saham PT Example Tbk (TEST) hanya di Pasar
    Negosiasi tanggal 18 Juli 2025 pukul 14.00 WIB. Selanjutnya Bursa melakukan Suspensi kembali
    di Seluruh Pasar pukul 14.30 WIB.
    """
    result = parse_idx_tradability_announcement(text, source_ref="idx://complex")
    assert result.status == "MANUAL_REVIEW"
    assert result.diagnostic == "MULTI_ACTION_INTRADAY_DOCUMENT"
    assert result.events.empty


def test_call_auction_later_session_resume_requires_manual_review():
    text = """
    Pengumuman Pencabutan Suspensi Efek PT Example Tbk (TEST). Bursa mencabut Suspensi Efek TEST
    di Pasar Reguler Periodic Call Auction dan Pasar Tunai Periodic Call Auction terhitung sejak
    Sesi 4 Call Auction pada hari Kamis, 31 Juli 2025.
    """
    result = parse_idx_tradability_announcement(text, source_ref="idx://call-auction")
    assert result.status == "MANUAL_REVIEW"
    assert result.diagnostic == "PARTIAL_SESSION_OR_CALL_AUCTION_RESUME"
    assert result.events.empty


def test_all_market_suspension_can_be_closed_only_for_resumed_markets():
    events = pd.DataFrame(
        [
            {
                "ticker": "TEST", "market": "ALL", "action": "SUSPEND",
                "effective_date": "2025-01-02", "announced_at": "2025-01-01",
                "announcement_no": "S1", "source": "IDX_EXCHANGE_ANNOUNCEMENT",
                "source_ref": "suspend", "document_sha256": "a", "parser_version": "test",
            },
            {
                "ticker": "TEST", "market": "REGULAR", "action": "RESUME",
                "effective_date": "2025-01-06", "announced_at": "2025-01-05",
                "announcement_no": "R1", "source": "IDX_EXCHANGE_ANNOUNCEMENT",
                "source_ref": "resume-regular", "document_sha256": "b", "parser_version": "test",
            },
            {
                "ticker": "TEST", "market": "CASH", "action": "RESUME",
                "effective_date": "2025-01-06", "announced_at": "2025-01-05",
                "announcement_no": "R1", "source": "IDX_EXCHANGE_ANNOUNCEMENT",
                "source_ref": "resume-cash", "document_sha256": "b", "parser_version": "test",
            },
        ]
    )
    intervals, diagnostics = compile_suspension_intervals(events)
    regular = intervals[intervals["market"].eq("REGULAR")].iloc[0]
    cash = intervals[intervals["market"].eq("CASH")].iloc[0]
    negotiated = intervals[intervals["market"].eq("NEGOTIATED")].iloc[0]
    assert regular["effective_from"] == pd.Timestamp("2025-01-02")
    assert regular["effective_to"] == pd.Timestamp("2025-01-05")
    assert cash["effective_to"] == pd.Timestamp("2025-01-05")
    assert pd.isna(negotiated["effective_to"])
    assert diagnostics.empty


def test_unmatched_resume_and_duplicate_suspend_are_explicit_and_fail_closed():
    events = pd.DataFrame(
        [
            {
                "ticker": "TEST", "market": "REGULAR", "action": "RESUME",
                "effective_date": "2025-01-02", "source": "IDX", "source_ref": "resume-only",
            },
            {
                "ticker": "TEST", "market": "REGULAR", "action": "SUSPEND",
                "effective_date": "2025-01-03", "source": "IDX", "source_ref": "suspend-1",
            },
            {
                "ticker": "TEST", "market": "REGULAR", "action": "SUSPEND",
                "effective_date": "2025-01-03", "source": "IDX", "source_ref": "suspend-duplicate",
            },
        ]
    )
    intervals, diagnostics = compile_suspension_intervals(events)
    assert set(diagnostics["status"]) == {"UNMATCHED_RESUME", "DUPLICATE_SUSPEND"}
    assert set(diagnostics["inferred_state"]) == {"UNKNOWN"}
    assert not intervals.empty
    assert not (intervals["state"] == "ACTIVE").any()


def test_manifest_ingestion_preserves_source_hash_and_parse_diagnostics():
    manifest = pd.DataFrame(
        [{"source_ref": "https://idx.example/suspend.pdf", "announced_at": "2025-06-30"}]
    )
    text = (
        "Peng-SPT-00110/BEI.WAS/06-2025 penghentian sementara perdagangan saham "
        "PT Example Tbk (TEST) pada tanggal 1 Juli 2025 di Pasar Reguler dan Pasar Tunai."
    )
    byte_hash = hashlib.sha256(b"fake-pdf-bytes").hexdigest()

    def fetcher(url: str):
        assert url == manifest.loc[0, "source_ref"]
        return text, byte_hash

    events, diagnostics = ingest_announcement_manifest(manifest, fetcher=fetcher)
    assert len(events) == 2
    assert events["document_sha256"].eq(byte_hash).all()
    assert diagnostics.loc[0, "status"] == "PARSED"
    assert diagnostics.loc[0, "event_rows"] == 2
