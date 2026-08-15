from datetime import date

import pandas as pd

from idx_trade.providers.idx import fetch_delisted_listings
from idx_trade.security_master import build_security_master, existence_state
from idx_trade.states import ExistenceState


def test_idx_delisting_date_is_exclusive_effective_boundary() -> None:
    """A 10-Nov effective delisting must already be DELISTED on 10-Nov."""

    def fake_get_json(_url: str, params: dict[str, object]) -> dict[str, object]:
        if params["periodYear"] == 2026 and params["periodMonth"] == 11:
            return {
                "data": [
                    {
                        "code": "SRIL",
                        "issuerName": "PT Sri Rejeki Isman Tbk",
                        "ListingDate": "2013-06-17",
                        "DeListingDate": "2026-11-10",
                    }
                ]
            }
        return {"data": []}

    delisted = fetch_delisted_listings(
        2026,
        end=date(2026, 11, 30),
        get_json=fake_get_json,
    )

    assert len(delisted) == 1
    assert delisted.loc[0, "ticker"] == "SRIL"
    assert delisted.loc[0, "listed_to"] == pd.Timestamp("2026-11-09")

    master = build_security_master(pd.DataFrame(), delisted)
    assert existence_state(master, "SRIL", pd.Timestamp("2026-11-09")) is ExistenceState.LISTED
    assert existence_state(master, "SRIL", pd.Timestamp("2026-11-10")) is ExistenceState.DELISTED


def test_invalid_delisting_date_remains_fail_closed() -> None:
    def fake_get_json(_url: str, params: dict[str, object]) -> dict[str, object]:
        if params["periodMonth"] == 1:
            return {
                "data": [
                    {
                        "code": "TEST",
                        "issuerName": "Test Tbk",
                        "ListingDate": "2020-01-01",
                        "DeListingDate": "not-a-date",
                    }
                ]
            }
        return {"data": []}

    result = fetch_delisted_listings(
        2026,
        end=date(2026, 1, 31),
        get_json=fake_get_json,
    )

    assert result.empty
