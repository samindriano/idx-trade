from __future__ import annotations

from datetime import date

import pytest

from idx_trade import e2e_cloud_security_master_v1 as security


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
    with pytest.raises(security.CloudSecurityMasterError, match="RECORDS_TOTAL_MISSING"):
        security.fetch_complete_active_listings()


def test_delisting_fetch_uses_filtered_count_for_monthly_query(monkeypatch) -> None:
    payload = {
        "recordsTotal": 100,
        "recordsFiltered": 1,
        "data": [
            {
                "code": "NEWW",
                "issuerName": "New",
                "ListingDate": "2026-01-05",
                "DeListingDate": "2026-01-20",
            }
        ],
    }
    calls = []

    def fake_get_json(url, params):
        calls.append((url, dict(params)))
        return payload

    monkeypatch.setattr(security, "_get_json", fake_get_json)
    frame = security.fetch_complete_delisted_listings(2026, end=date(2026, 1, 31))
    assert list(frame["ticker"]) == ["NEWW"]
    assert len(calls) == 1


def test_delisting_fetch_rejects_partial_filtered_page(monkeypatch) -> None:
    payload = {
        "recordsTotal": 100,
        "recordsFiltered": 2,
        "data": [
            {
                "code": "NEWW",
                "issuerName": "New",
                "ListingDate": "2026-01-05",
                "DeListingDate": "2026-01-20",
            }
        ],
    }
    monkeypatch.setattr(security, "_get_json", lambda url, params: payload)
    with pytest.raises(security.CloudSecurityMasterError, match="PARTIAL_RESPONSE"):
        security.fetch_complete_delisted_listings(2026, end=date(2026, 1, 31))


def test_delisting_fetch_rejects_malformed_identity_even_when_counts_match(monkeypatch) -> None:
    payload = {
        "recordsTotal": 1,
        "recordsFiltered": 1,
        "data": [
            {
                "code": "BAD",
                "issuerName": "Bad",
                "ListingDate": "not-a-date",
                "DeListingDate": "2026-01-20",
            }
        ],
    }
    monkeypatch.setattr(security, "_get_json", lambda url, params: payload)
    with pytest.raises(security.CloudSecurityMasterError, match="ROW_IDENTITY_INVALID"):
        security.fetch_complete_delisted_listings(2026, end=date(2026, 1, 31))
