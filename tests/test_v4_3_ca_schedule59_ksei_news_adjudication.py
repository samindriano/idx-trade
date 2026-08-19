from __future__ import annotations

from idx_trade.v4_3_ca_schedule59_ksei_news_adjudication import parse_news_document
from idx_trade.v4_ca_residual_document_semantics_hardened import parse_residual_document_hardened


def test_html_table_row_preserves_explicit_new_basis_transition() -> None:
    payload = b"""
    <html><body>
      <h1>Stock Split AAA</h1>
      <table>
        <tr><td>Tanggal Pencatatan</td><td>10 Januari 2024</td></tr>
        <tr><td>Mulai Perdagangan Saham dengan Nilai Nominal Baru di Pasar Reguler</td><td>11 Januari 2024</td></tr>
      </table>
    </body></html>
    """
    text = parse_news_document(payload)
    parsed = parse_residual_document_hardened(
        text.plain_text,
        expected_ticker="AAA",
        index_subject=text.title,
        layout_text=text.layout_text,
    )
    assert parsed.ticker_evidenced is True
    assert parsed.record_date == "2024-01-10"
    assert parsed.transition_date == "2024-01-11"
    assert parsed.transition_semantic == "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"


def test_flattened_free_floating_date_is_not_layout_transition() -> None:
    payload = b"""
    <html><body>
      <h1>Stock Split BBB</h1>
      <p>Mulai Perdagangan Saham dengan Nilai Nominal Baru di Pasar Reguler</p>
      <div>11 Januari 2024</div>
      <p>Tanggal Pencatatan 10 Januari 2024</p>
    </body></html>
    """
    text = parse_news_document(payload)
    parsed = parse_residual_document_hardened(
        text.plain_text,
        expected_ticker="BBB",
        index_subject=text.title,
        layout_text=text.layout_text,
    )
    assert parsed.record_date == "2024-01-10"
    assert parsed.transition_date is None


def test_table_transition_does_not_steal_record_date() -> None:
    payload = b"""
    <html><body>
      <h1>Stock Split CCC</h1>
      <table>
        <tr><td>Mulai Perdagangan Saham dengan Nilai Nominal Baru di Pasar Reguler</td><td></td></tr>
        <tr><td>Tanggal Pencatatan</td><td>10 Januari 2024</td></tr>
      </table>
    </body></html>
    """
    text = parse_news_document(payload)
    parsed = parse_residual_document_hardened(
        text.plain_text,
        expected_ticker="CCC",
        index_subject=text.title,
        layout_text=text.layout_text,
    )
    assert parsed.transition_date is None
    assert parsed.record_date == "2024-01-10"
