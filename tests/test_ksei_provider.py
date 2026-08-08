import pandas as pd
import pytest

from idx_trade.providers.ksei import (
    parse_ksei_active_listing,
    parse_ksei_security_identity,
    reconcile_missing_security_scope,
    supplement_missing_active_listings,
)
from idx_trade.security_master import build_security_master, existence_state
from idx_trade.states import ExistenceState


def _html(
    ticker: str,
    listing_date: str,
    *,
    status: str = "Active",
    security_type: str = "Saham Biasa",
) -> str:
    return f"""
    <html><body>
      <div>Security name</div><div>{ticker} Example</div>
      <div>Issuer</div><div>{ticker} Example Tbk, PT</div>
      <div>ISIN Code</div><div>ID1000000000</div>
      <div>Short Code</div><div>{ticker}</div>
      <div>Type</div><div>{security_type}</div>
      <div>Listing Date</div><div>{listing_date}</div>
      <div>Stock Exchange</div><div>IDX</div>
      <div>Status</div><div>{status}</div>
      <div>Nominal</div><div>100.00</div>
    </body></html>
    """


def _structured_html(ticker: str, listing_date: str) -> str:
    return f"""
    <html><body>
      <nav>Status Nominal Listing Date Stock Exchange</nav>
      <dl>
        <dt>Security name</dt><dd>{ticker} Example</dd>
        <dt>Issuer</dt><dd>{ticker} Example Tbk, PT</dd>
        <dt>Short Code</dt><dd>{ticker}</dd>
        <dt>Type</dt><dd>Saham Biasa</dd>
        <dt>Listing Date</dt><dd>{listing_date}</dd>
        <dt>Stock Exchange</dt><dd>IDX</dd>
        <dt>Status</dt><dd>Active</dd>
      </dl>
    </body></html>
    """


def test_ksei_active_idx_share_parses_as_supplemental_identity():
    row = parse_ksei_active_listing(
        _html("HDTX", "June 06, 1990"),
        requested_ticker="HDTX",
        source_ref="ksei://HDTX",
    )
    assert row.loc[0, "ticker"] == "HDTX"
    assert row.loc[0, "listed_from"] == pd.Timestamp("1990-06-06")
    assert row.loc[0, "source"] == "KSEI_REGISTERED_SECURITIES"


def test_ksei_indonesian_listing_date_parses_for_common_share():
    row = parse_ksei_active_listing(
        _html("CNTB", "22 Desember 2000"),
        requested_ticker="CNTB",
        source_ref="ksei://CNTB",
    )
    assert row.loc[0, "listed_from"] == pd.Timestamp("2000-12-22")


def test_ksei_nonactive_page_fails_closed():
    with pytest.raises(ValueError, match="not explicitly ACTIVE"):
        parse_ksei_active_listing(
            _html("KPAS", "October 05, 2018", status="Inactive"),
            requested_ticker="KPAS",
            source_ref="ksei://KPAS",
        )


def test_ksei_preference_share_is_identity_evidence_but_not_common_listing():
    identity = parse_ksei_security_identity(
        _html("CNTX", "June 16, 1989", security_type="Saham Preference"),
        requested_ticker="CNTX",
        source_ref="ksei://CNTX",
    )
    assert identity.loc[0, "security_type"] == "Saham Preference"
    assert bool(identity.loc[0, "is_common_share"]) is False
    with pytest.raises(ValueError, match="not explicitly a common share"):
        parse_ksei_active_listing(
            _html("CNTX", "June 16, 1989", security_type="Saham Preference"),
            requested_ticker="CNTX",
            source_ref="ksei://CNTX",
        )


def test_ksei_structured_fields_are_not_contaminated_by_navigation_text():
    row = parse_ksei_active_listing(
        _structured_html("KPAS", "October 05, 2018"),
        requested_ticker="KPAS",
        source_ref="ksei://KPAS",
    )
    assert row.loc[0, "listed_from"] == pd.Timestamp("2018-10-05")


def test_missing_primary_names_can_be_supplemented_without_replacing_idx_rows():
    active = pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "company_name": ["Bank Central Asia Tbk"],
            "listed_from": [pd.Timestamp("2000-05-31")],
            "listed_to": [pd.NaT],
            "source": ["IDX_STOCK_LIST"],
        }
    )

    fixtures = {
        "HDTX": ("June 06, 1990", "ksei://HDTX"),
        "KPAS": ("October 05, 2018", "ksei://KPAS"),
    }

    def fetcher(ticker: str) -> pd.DataFrame:
        listing_date, source_ref = fixtures[ticker]
        return parse_ksei_active_listing(
            _html(ticker, listing_date),
            requested_ticker=ticker,
            source_ref=source_ref,
        )

    supplemented, diagnostics = supplement_missing_active_listings(
        active,
        ["BBCA", "HDTX", "KPAS"],
        fetcher=fetcher,
    )
    assert set(supplemented["ticker"]) == {"BBCA", "HDTX", "KPAS"}
    assert set(diagnostics["status"]) == {"SUPPLEMENTED"}

    master = build_security_master(supplemented, pd.DataFrame())
    assert existence_state(master, "HDTX", pd.Timestamp("2026-07-15")) is ExistenceState.LISTED
    assert existence_state(master, "KPAS", pd.Timestamp("2026-07-15")) is ExistenceState.LISTED


def test_scope_reconciliation_supplements_common_and_excludes_preference():
    active = pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "company_name": ["Bank Central Asia Tbk"],
            "listed_from": [pd.Timestamp("2000-05-31")],
            "listed_to": [pd.NaT],
            "source": ["IDX_STOCK_LIST"],
        }
    )

    def fetcher(ticker: str) -> pd.DataFrame:
        if ticker == "CNTB":
            document = _html("CNTB", "22 Desember 2000", security_type="Saham Biasa")
        elif ticker == "CNTX":
            document = _html("CNTX", "June 16, 1989", security_type="Saham Preference")
        else:
            raise AssertionError(ticker)
        return parse_ksei_security_identity(
            document,
            requested_ticker=ticker,
            source_ref=f"ksei://{ticker}",
        )

    supplemented, exclusions, diagnostics = reconcile_missing_security_scope(
        active,
        ["BBCA", "CNTB", "CNTX"],
        fetcher=fetcher,
    )
    assert set(supplemented["ticker"]) == {"BBCA", "CNTB"}
    assert exclusions.to_dict(orient="records") == [
        {
            "ticker": "CNTX",
            "reason": "NON_COMMON_SHARE",
            "security_type": "Saham Preference",
            "source": "KSEI_REGISTERED_SECURITIES",
            "source_ref": "ksei://CNTX",
        }
    ]
    status = dict(zip(diagnostics["ticker"], diagnostics["status"]))
    assert status == {
        "CNTB": "SUPPLEMENTED",
        "CNTX": "OUT_OF_SCOPE_SECURITY_TYPE",
    }
