import pandas as pd
import pytest

from idx_trade.providers.ksei import (
    parse_ksei_active_listing,
    supplement_missing_active_listings,
)
from idx_trade.security_master import build_security_master, existence_state
from idx_trade.states import ExistenceState


def _html(ticker: str, listing_date: str, *, status: str = "Active") -> str:
    return f"""
    <html><body>
      <div>Security name</div><div>{ticker} Example Tbk</div>
      <div>Issuer</div><div>{ticker} Example Tbk, PT</div>
      <div>ISIN Code</div><div>ID1000000000</div>
      <div>Short Code</div><div>{ticker}</div>
      <div>Type</div><div>Saham Biasa</div>
      <div>Listing Date</div><div>{listing_date}</div>
      <div>Stock Exchange</div><div>IDX</div>
      <div>Status</div><div>{status}</div>
      <div>Nominal</div><div>100.00</div>
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


def test_ksei_nonactive_page_fails_closed():
    with pytest.raises(ValueError, match="not explicitly ACTIVE"):
        parse_ksei_active_listing(
            _html("KPAS", "October 05, 2018", status="Inactive"),
            requested_ticker="KPAS",
            source_ref="ksei://KPAS",
        )


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
