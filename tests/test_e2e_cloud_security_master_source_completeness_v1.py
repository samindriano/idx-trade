from __future__ import annotations

from datetime import date

import pytest

from idx_trade import e2e_cloud_security_master_v1 as security


def _event(ticker: str, listed: str, delisted: str) -> dict[str, object]:
    return {
        "code": ticker,
        "issuerName": ticker,
        "ListingDate": listed,
        "DeListingDate": delisted,
    }


def _month_payload(*, page: int, size: int, total: int, rows: list[dict[str, object]]):
    return {
        "meta": {"pageNumber": page, "pageSize": size, "totalItems": total},
        "data": rows,
    }


def test_active_listing_fetch_requires_exact_records_total(monkeypatch) -> None:
    payload = {
        "recordsTotal": 2,
        "recordsFiltered": 2,
        "data": [
            {"Code": "AAAA", "Name": "A", "ListingDate": "2020-01-01"},
            {"Code": "NEWW", "Name": "N", "ListingDate": "2026-08-21"},
        ],
    }
    monkeypatch.setattr(security, "_get_json", lambda url, params: payload)
    frame = security.fetch_complete_active_listings()
    assert list(frame["ticker"]) == ["AAAA", "NEWW"]


def test_active_listing_fetch_rejects_partial_page(monkeypatch) -> None:
    payload = {
        "recordsTotal": 2,
        "recordsFiltered": 2,
        "data": [{"Code": "AAAA", "Name": "A", "ListingDate": "2020-01-01"}],
    }
    monkeypatch.setattr(security, "_get_json", lambda url, params: payload)
    with pytest.raises(security.CloudSecurityMasterError, match="PARTIAL_RESPONSE"):
        security.fetch_complete_active_listings()


def test_active_listing_fetch_rejects_missing_count_metadata(monkeypatch) -> None:
    payload = {
        "data": [{"Code": "AAAA", "Name": "A", "ListingDate": "2020-01-01"}],
    }
    monkeypatch.setattr(security, "_get_json", lambda url, params: payload)
    with pytest.raises(security.CloudSecurityMasterError, match="recordsTotal_MISSING"):
        security.fetch_complete_active_listings()


def test_delisting_fetch_accepts_empty_month_proven_by_meta_total_items(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_get_json(url, params):
        calls.append(dict(params))
        return _month_payload(page=1, size=9999, total=0, rows=[])

    monkeypatch.setattr(security, "_get_json", fake_get_json)
    frame = security.fetch_complete_delisted_listings(2026, end=date(2026, 8, 31))
    assert frame.empty
    assert len(calls) == 1
    assert calls[0]["periodMonth"] == 8


def test_delisting_fetch_exhausts_all_pages_until_total_items(monkeypatch) -> None:
    monkeypatch.setattr(security, "DELISTING_PAGE_SIZE", 2)
    calls: list[int] = []
    pages = {
        1: [_event("NEWA", "2026-08-21", "2026-08-22"), _event("NEWB", "2026-08-21", "2026-08-23")],
        2: [_event("NEWC", "2026-08-21", "2026-08-24")],
    }

    def fake_get_json(url, params):
        page = int(params["pageNumber"])
        calls.append(page)
        return _month_payload(page=page, size=2, total=3, rows=pages[page])

    monkeypatch.setattr(security, "_get_json", fake_get_json)
    frame = security.fetch_complete_delisted_listings(2026, end=date(2026, 8, 31))
    assert calls == [1, 2]
    assert list(frame["ticker"]) == ["NEWA", "NEWB", "NEWC"]


def test_delisting_fetch_rejects_missing_meta(monkeypatch) -> None:
    monkeypatch.setattr(security, "_get_json", lambda url, params: {"data": []})
    with pytest.raises(security.CloudSecurityMasterError, match="META_NOT_OBJECT"):
        security.fetch_complete_delisted_listings(2026, end=date(2026, 8, 31))


def test_delisting_fetch_rejects_missing_total_items(monkeypatch) -> None:
    payload = {"meta": {"pageNumber": 1, "pageSize": 9999}, "data": []}
    monkeypatch.setattr(security, "_get_json", lambda url, params: payload)
    with pytest.raises(security.CloudSecurityMasterError, match="totalItems_MISSING"):
        security.fetch_complete_delisted_listings(2026, end=date(2026, 8, 31))


def test_delisting_fetch_rejects_page_number_mismatch(monkeypatch) -> None:
    payload = _month_payload(page=2, size=9999, total=0, rows=[])
    monkeypatch.setattr(security, "_get_json", lambda url, params: payload)
    with pytest.raises(security.CloudSecurityMasterError, match="PAGE_NUMBER_MISMATCH"):
        security.fetch_complete_delisted_listings(2026, end=date(2026, 8, 31))


def test_delisting_fetch_rejects_empty_page_before_total_is_reached(monkeypatch) -> None:
    monkeypatch.setattr(security, "DELISTING_PAGE_SIZE", 2)

    def fake_get_json(url, params):
        page = int(params["pageNumber"])
        if page == 1:
            return _month_payload(
                page=1,
                size=2,
                total=3,
                rows=[_event("NEWA", "2026-08-21", "2026-08-22"), _event("NEWB", "2026-08-21", "2026-08-23")],
            )
        return _month_payload(page=2, size=2, total=3, rows=[])

    monkeypatch.setattr(security, "_get_json", fake_get_json)
    with pytest.raises(security.CloudSecurityMasterError, match="EMPTY_PAGE_BEFORE_TOTAL"):
        security.fetch_complete_delisted_listings(2026, end=date(2026, 8, 31))


def test_delisting_fetch_rejects_total_items_changing_between_pages(monkeypatch) -> None:
    monkeypatch.setattr(security, "DELISTING_PAGE_SIZE", 1)

    def fake_get_json(url, params):
        page = int(params["pageNumber"])
        if page == 1:
            return _month_payload(
                page=1,
                size=1,
                total=2,
                rows=[_event("NEWA", "2026-08-21", "2026-08-22")],
            )
        return _month_payload(
            page=2,
            size=1,
            total=3,
            rows=[_event("NEWB", "2026-08-21", "2026-08-23")],
        )

    monkeypatch.setattr(security, "_get_json", fake_get_json)
    with pytest.raises(security.CloudSecurityMasterError, match="TOTAL_ITEMS_CHANGED"):
        security.fetch_complete_delisted_listings(2026, end=date(2026, 8, 31))


def test_delisting_fetch_rejects_malformed_identity_even_when_total_matches(monkeypatch) -> None:
    payload = _month_payload(
        page=1,
        size=9999,
        total=1,
        rows=[_event("BAD", "not-a-date", "2026-08-25")],
    )
    monkeypatch.setattr(security, "_get_json", lambda url, params: payload)
    with pytest.raises(security.CloudSecurityMasterError, match="ROW_IDENTITY_INVALID"):
        security.fetch_complete_delisted_listings(2026, end=date(2026, 8, 31))
