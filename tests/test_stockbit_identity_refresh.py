from __future__ import annotations

from datetime import date

import pytest

from idx_trade.stockbit_identity_refresh import IdentityRefreshError, reconstruct_active_roster


def sec(code: str, listing_date: str = "2020-01-01", name: str | None = None) -> dict:
    return {
        "Code": code,
        "Name": name or f"{code} Tbk.",
        "Shares": 1_000_000,
        "ListingDate": f"{listing_date}T00:00:00",
        "ListingBoard": "Utama",
    }


def comp(code: str, listing_date: str = "2020-01-01", name: str | None = None) -> dict:
    return {
        "KodeEmiten": code,
        "NamaEmiten": name or f"{code} Tbk.",
        "EfekEmiten_Saham": True,
        "TanggalPencatatan": f"{listing_date}T00:00:00",
        "PapanPencatatan": "Utama",
    }


def event_page(dataset: str, items: list[dict], *, year: int = 2026, month: int = 7) -> dict:
    return {
        "items": items,
        "count": len(items),
        "total": len(items),
        "page": 1,
        "hasMore": False,
        "nextPage": None,
        "year": year,
        "month": month,
        "dataset": dataset,
        "provider": "idx",
    }


def ipo_payload(items: list[dict], *, year: int = 2026) -> dict:
    return {
        "items": items,
        "start": 0,
        "length": 200,
        "total": len(items),
        "year": str(year),
        "dataset": "ipo",
        "provider": "idx",
    }


def build(
    securities: list[dict],
    companies: list[dict],
    *,
    previous: set[str],
    delistings: list[dict] | None = None,
    new_listings: list[dict] | None = None,
    ipos: list[dict] | None = None,
    as_of: date = date(2026, 8, 21),
):
    return reconstruct_active_roster(
        securities_rows=securities,
        companies_rows=companies,
        delisting_pages=delistings or [],
        new_listing_pages=new_listings or [],
        ipo_payloads=ipos or [],
        previous_tickers=previous,
        previous_as_of=date(2026, 7, 31),
        as_of=as_of,
    )


def test_effective_delisting_removes_stale_base_ticker_and_explains_prior_removal() -> None:
    page = event_page(
        "delistings",
        [{"code": "CNTX", "name": "Centex Tbk", "listingDate": "1979-05-22", "lastTradingDate": "2026-07-29", "delistingDate": "2026-07-30"}],
    )
    result = build([sec("CNTX"), sec("BBCA")], [comp("CNTX"), comp("BBCA")], previous={"CNTX", "BBCA"}, delistings=[page])
    assert result.tickers == ("BBCA",)
    assert result.removals == ("CNTX",)
    assert result.explained_removals == ("CNTX",)
    assert result.activation_safe is True


def test_future_delisting_does_not_remove_before_effective_date() -> None:
    page = event_page(
        "delistings",
        [{"code": "BBCA", "name": "BBCA", "listingDate": "2000-01-01", "lastTradingDate": "2026-08-24", "delistingDate": "2026-08-25"}],
        month=8,
    )
    result = build([sec("BBCA")], [comp("BBCA")], previous={"BBCA"}, delistings=[page])
    assert result.tickers == ("BBCA",)
    assert result.activation_safe is True


def test_malformed_delisting_date_fails_closed() -> None:
    page = event_page("delistings", [{"code": "CNTX", "delistingDate": "not-a-date"}])
    with pytest.raises(IdentityRefreshError, match="delistingDate"):
        build([sec("CNTX")], [comp("CNTX")], previous={"CNTX"}, delistings=[page])


def test_duplicate_delisting_code_in_scan_fails_closed() -> None:
    page = event_page(
        "delistings",
        [
            {"code": "CNTX", "delistingDate": "2026-07-30"},
            {"code": "CNTX", "delistingDate": "2026-07-31"},
        ],
    )
    with pytest.raises(IdentityRefreshError, match="duplicate delisting"):
        build([sec("CNTX")], [comp("CNTX")], previous={"CNTX"}, delistings=[page])


def test_base_requires_exact_securities_company_stock_ticker_equality() -> None:
    with pytest.raises(IdentityRefreshError, match="base ticker mismatch"):
        build([sec("BBCA"), sec("BBRI")], [comp("BBCA")], previous={"BBCA"})


def test_non_stock_company_row_cannot_make_base_eligible() -> None:
    row = comp("GOTOM")
    row["EfekEmiten_Saham"] = False
    with pytest.raises(IdentityRefreshError, match="base ticker mismatch"):
        build([sec("GOTOM")], [row], previous=set())


def test_event_only_ticker_cannot_enter_without_both_base_sources() -> None:
    listing = event_page("new-listings", [{"code": "GOTOM", "listingDate": "2026-07-10", "name": "MVS"}])
    ipo = ipo_payload([{"code": "GOTOM", "listingDate": "2026-07-10", "securityType": "saham", "listingType": "baru", "name": "MVS"}])
    result = build([sec("BBCA")], [comp("BBCA")], previous={"BBCA"}, new_listings=[listing], ipos=[ipo])
    assert "GOTOM" not in result.tickers
    assert result.tickers == ("BBCA",)


def test_base_addition_requires_observable_listing_event_evidence() -> None:
    result = build([sec("BBCA"), sec("NEWX", "2026-08-01")], [comp("BBCA"), comp("NEWX", "2026-08-01")], previous={"BBCA"})
    assert result.additions == ("NEWX",)
    assert result.unexplained_additions == ("NEWX",)
    assert result.activation_safe is False


def test_new_listing_event_can_explain_base_addition() -> None:
    page = event_page(
        "new-listings",
        [{"code": "NEWX", "name": "NEWX Tbk.", "listingDate": "2026-08-01", "listedShares": 1_000_000}],
        month=8,
    )
    result = build(
        [sec("BBCA"), sec("NEWX", "2026-08-01")],
        [comp("BBCA"), comp("NEWX", "2026-08-01")],
        previous={"BBCA"},
        new_listings=[page],
    )
    assert result.explained_additions == ("NEWX",)
    assert result.activation_safe is True


def test_ipo_stock_event_can_explain_base_addition_but_non_stock_cannot() -> None:
    stock_ipo = ipo_payload([{"code": "NEWX", "listingDate": "2026-08-01", "securityType": "saham", "listingType": "baru", "name": "NEWX"}])
    result = build(
        [sec("BBCA"), sec("NEWX", "2026-08-01")],
        [comp("BBCA"), comp("NEWX", "2026-08-01")],
        previous={"BBCA"},
        ipos=[stock_ipo],
    )
    assert result.activation_safe is True

    non_stock_ipo = ipo_payload([{"code": "NEWX", "listingDate": "2026-08-01", "securityType": "obligasi", "listingType": "baru", "name": "NEWX"}])
    blocked = build(
        [sec("BBCA"), sec("NEWX", "2026-08-01")],
        [comp("BBCA"), comp("NEWX", "2026-08-01")],
        previous={"BBCA"},
        ipos=[non_stock_ipo],
    )
    assert blocked.unexplained_additions == ("NEWX",)
    assert blocked.activation_safe is False


def test_base_removal_requires_delisting_evidence_even_when_provider_drops_ticker() -> None:
    result = build([sec("BBCA")], [comp("BBCA")], previous={"BBCA", "CNTB"})
    assert result.removals == ("CNTB",)
    assert result.unexplained_removals == ("CNTB",)
    assert result.activation_safe is False


def test_provider_dropped_ticker_is_explained_by_delisting_overlay() -> None:
    page = event_page("delistings", [{"code": "CNTB", "delistingDate": "2026-07-30", "lastTradingDate": "2026-07-29"}])
    result = build([sec("BBCA")], [comp("BBCA")], previous={"BBCA", "CNTB"}, delistings=[page])
    assert result.explained_removals == ("CNTB",)
    assert result.activation_safe is True


def test_canonical_snapshot_hash_is_deterministic_and_order_independent() -> None:
    a = build([sec("BBRI"), sec("BBCA")], [comp("BBRI"), comp("BBCA")], previous={"BBCA", "BBRI"})
    b = build([sec("BBCA"), sec("BBRI")], [comp("BBCA"), comp("BBRI")], previous={"BBCA", "BBRI"})
    assert a.tickers == b.tickers == ("BBCA", "BBRI")
    assert a.snapshot_sha256 == b.snapshot_sha256


def test_identity_refresh_has_no_market_outcome_or_stock_summary_input() -> None:
    import inspect
    from idx_trade import stockbit_identity_refresh as module

    signature = inspect.signature(module.reconstruct_active_roster)
    forbidden = {"returns", "targets", "scores", "o2", "stock_summary", "outcomes", "forward_counters"}
    assert forbidden.isdisjoint(signature.parameters)
