from __future__ import annotations

import pytest

from idx_trade.v4_ca_continuity_remediation import (
    RESOLVED,
    UNRESOLVED_COVERAGE,
    UNRESOLVED_EVENT,
    classify_ticker_period,
    row_intersects_period,
)
from idx_trade.v4_ksei_ca_history import (
    KseiHistoryParseError,
    normalize_ca_family,
    parse_ksei_security_history,
)


def _page(short_code: str = "BNBR") -> bytes:
    return f"""
    <html><body>
      <div>Short Code {short_code}</div>
      <table>
        <thead><tr>
          <th>Type of CA</th><th>Ratio</th><th>Cum Date</th>
          <th>Record Date</th><th>Distribution Date</th><th>Status</th>
        </tr></thead>
        <tbody>
          <tr>
            <td>Right Distribution</td><td>(27 BNBR : 14 BNBR-R)</td>
            <td>2026070808 Jul 2026</td><td>2026071010 Jul 2026</td>
            <td>2026071313 Jul 2026</td><td>Active</td>
          </tr>
          <tr>
            <td>Proxy Voting</td><td></td><td>-</td>
            <td>2025060505 Jun 2025</td><td>2025063030 Jun 2025</td>
            <td>Active</td>
          </tr>
        </tbody>
      </table>
    </body></html>
    """.encode()


def _row(*, family: str, status: str = "Active", date: str | None = "2025-06-01"):
    return {
        "ticker": "TEST",
        "event_family": family,
        "status": status,
        "cum_date": date,
        "record_date": None,
        "distribution_date": None,
    }


def test_parse_exact_ksei_history_and_identity() -> None:
    parsed = parse_ksei_security_history(
        _page(),
        expected_ticker="BNBR",
        source_url="https://web.ksei.co.id/test",
        source_sha256="abc",
    )
    assert parsed.coverage_certified is True
    assert len(parsed.rows) == 2
    assert parsed.rows[0]["event_family"] == "RIGHTS_HMETD"
    assert parsed.rows[0]["cum_date"] == "2026-07-08"
    assert parsed.rows[0]["record_date"] == "2026-07-10"
    assert parsed.rows[0]["distribution_date"] == "2026-07-13"
    assert parsed.rows[1]["event_family"] == "PROXY_VOTING"


def test_parse_rejects_wrong_ticker_identity() -> None:
    with pytest.raises(KseiHistoryParseError, match="identity mismatch"):
        parse_ksei_security_history(
            _page("BBCA"),
            expected_ticker="BNBR",
            source_url="https://web.ksei.co.id/test",
            source_sha256="abc",
        )


def test_family_mapping_is_fail_closed_for_unknown() -> None:
    assert normalize_ca_family("Mandatory Conversion") == "MANDATORY_CONVERSION"
    assert normalize_ca_family("Stock Dividend") == "STOCK_DIVIDEND"
    assert normalize_ca_family("Cash Dividend") == "CASH_DIVIDEND"
    assert normalize_ca_family("Something New") == "UNKNOWN"


def test_ticker_period_clean_history_resolves() -> None:
    result = classify_ticker_period(
        coverage_certified=True,
        rows=[_row(family="CASH_DIVIDEND")],
        period_start="2024-01-01",
        period_end="2026-07-31",
    )
    assert result["continuity_status"] == RESOLVED


def test_ticker_period_mechanical_or_unknown_quarantines() -> None:
    mechanical = classify_ticker_period(
        coverage_certified=True,
        rows=[_row(family="RIGHTS_HMETD")],
        period_start="2024-01-01",
        period_end="2026-07-31",
    )
    unknown = classify_ticker_period(
        coverage_certified=True,
        rows=[_row(family="UNKNOWN", date=None)],
        period_start="2024-01-01",
        period_end="2026-07-31",
    )
    assert mechanical["continuity_status"] == UNRESOLVED_EVENT
    assert unknown["continuity_status"] == UNRESOLVED_EVENT


def test_cancelled_mechanical_event_does_not_quarantine() -> None:
    result = classify_ticker_period(
        coverage_certified=True,
        rows=[_row(family="RIGHTS_HMETD", status="Cancelled")],
        period_start="2024-01-01",
        period_end="2026-07-31",
    )
    assert result["continuity_status"] == RESOLVED


def test_missing_coverage_or_cross_source_conflict_stays_unresolved() -> None:
    missing = classify_ticker_period(
        coverage_certified=False,
        rows=[],
        period_start="2024-01-01",
        period_end="2026-07-31",
    )
    conflict = classify_ticker_period(
        coverage_certified=True,
        rows=[],
        period_start="2024-01-01",
        period_end="2026-07-31",
        prior_official_candidate_in_period=True,
    )
    assert missing["continuity_status"] == UNRESOLVED_COVERAGE
    assert conflict["continuity_status"] == UNRESOLVED_COVERAGE


def test_fixed_halo_is_conservative_but_bounded() -> None:
    inside = _row(family="RIGHTS_HMETD", date="2023-12-01")
    outside = _row(family="RIGHTS_HMETD", date="2023-10-01")
    assert row_intersects_period(
        inside, period_start="2024-01-01", period_end="2026-07-31"
    )
    assert not row_intersects_period(
        outside, period_start="2024-01-01", period_end="2026-07-31"
    )
