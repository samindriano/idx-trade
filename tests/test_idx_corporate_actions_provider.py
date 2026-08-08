import pandas as pd
import pytest

from idx_trade.providers.idx_corporate_actions import (
    IDX_CORPORATE_ACTION_SOURCE_ID,
    IDX_ISSUED_HISTORY_URL,
    cross_check_yahoo_split_events,
    derive_split_ratio,
    fetch_idx_corporate_actions,
    issued_history_url,
    parse_idx_corporate_actions,
)


def _issued_history_payload() -> dict[str, object]:
    return {
        "draw": 0,
        "recordsTotal": 4,
        "recordsFiltered": 4,
        "data": [
            {
                "id": 1,
                "KodeEmiten": "ABCD",
                "TanggalPencatatan": "2026-07-21T00:00:00",
                "JenisTindakan": "stockSplit",
                "JumlahSaham": 100,
                "JumlahSahamSetelahTindakan": 200,
            },
            {
                "id": 2,
                "KodeEmiten": "EFGH",
                "TanggalPencatatan": "2026-07-22",
                "JenisTindakan": "reverseStock",
                "JumlahSaham": 225,
                "JumlahSahamSetelahTindakan": 25,
            },
            {
                "id": 3,
                "KodeEmiten": "IJKL",
                "TanggalPencatatan": "2026-07-23",
                "JenisTindakan": "Dividen Saham",
                "JumlahSaham": 10,
                "JumlahSahamSetelahTindakan": 20,
            },
            {
                "id": 4,
                "KodeEmiten": "MNOP",
                "TanggalPencatatan": "2026-07-24",
                "JenisTindakan": "waran",
                "JumlahSaham": 10,
                "JumlahSahamSetelahTindakan": 20,
            },
        ],
    }


def test_parses_stock_split_reverse_stock_and_excludes_dividends():
    actions = parse_idx_corporate_actions(_issued_history_payload(), source_ref="idx://history")

    assert actions["action"].tolist() == ["stockSplit", "reverseStock"]
    assert actions["ticker"].tolist() == ["ABCD", "EFGH"]
    assert actions.loc[0, "effective_date"] == pd.Timestamp("2026-07-21")
    assert actions.loc[0, "listing_date"] == pd.Timestamp("2026-07-21")
    assert actions.loc[0, "old_shares"] == 100
    assert actions.loc[0, "new_shares"] == 200
    assert actions.loc[0, "ratio"] == pytest.approx(2.0)
    assert actions.loc[1, "ratio"] == pytest.approx(1 / 9)
    assert set(actions["source_identity"]) == {IDX_CORPORATE_ACTION_SOURCE_ID}


def test_safe_ratio_requires_positive_share_counts():
    assert derive_split_ratio(100, 200) == pytest.approx(2.0)
    assert derive_split_ratio(0, 200) is None
    assert derive_split_ratio(-100, 200) is None
    assert derive_split_ratio(100, 0) is None
    assert derive_split_ratio(None, 200) is None


def test_corporate_action_response_validation_fails_closed():
    with pytest.raises(ValueError, match="list-valued data"):
        parse_idx_corporate_actions({"data": None})
    with pytest.raises(ValueError, match="missing required fields"):
        parse_idx_corporate_actions(
            {
                "data": [
                    {
                        "KodeEmiten": "ABCD",
                        "TanggalPencatatan": "2026-07-21",
                        "JenisTindakan": "stockSplit",
                    }
                ]
            }
        )


def test_fetch_uses_official_issued_history_endpoint_and_audits_url():
    seen: list[str] = []

    def fetcher(url: str) -> dict[str, object]:
        seen.append(url)
        return _issued_history_payload()

    actions = fetch_idx_corporate_actions(
        "2026-07-01", "2026-07-31", fetch_json=fetcher, length=100
    )
    assert seen == [
        issued_history_url(
            length=100,
            date_from="2026-07-01",
            date_to="2026-07-31",
        )
    ]
    assert seen[0].startswith(IDX_ISSUED_HISTORY_URL)
    assert "caType=" in seen[0]
    assert "dateFrom=20260701" in seen[0]
    assert "dateTo=20260731" in seen[0]
    assert actions["source_ref"].eq(seen[0]).all()


def test_yahoo_cross_check_reports_match_mismatch_absence_and_yahoo_only():
    idx_actions = pd.DataFrame(
        [
            {
                "ticker": "ABCD",
                "action": "stockSplit",
                "effective_date": "2026-07-21",
                "ratio": 2.0,
                "source_ref": "idx://history",
            },
            {
                "ticker": "EFGH",
                "action": "reverseStock",
                "effective_date": "2026-07-22",
                "ratio": 1 / 9,
                "source_ref": "idx://history",
            },
            {
                "ticker": "IJKL",
                "action": "stockSplit",
                "effective_date": "2026-07-23",
                "ratio": 1.5,
                "source_ref": "idx://history",
            },
        ]
    )
    yahoo = pd.DataFrame(
        [
            {"ticker": "ABCD", "date": "2026-07-21", "stock_splits": 2.0},
            {"ticker": "EFGH", "date": "2026-07-22", "stock_splits": 0.25},
            {"ticker": "ZZZZ", "date": "2026-07-24", "stock_splits": 3.0},
            {"ticker": "ABCD", "date": "2026-07-22", "stock_splits": 0.0},
        ]
    )

    report = cross_check_yahoo_split_events(idx_actions, yahoo)
    statuses = dict(zip(report["ticker"], report["status"], strict=True))
    assert statuses == {
        "ABCD": "MATCH",
        "EFGH": "MISMATCH",
        "IJKL": "ABSENT",
        "ZZZZ": "YAHOO_ONLY",
    }
    assert idx_actions.loc[0, "ratio"] == 2.0


def test_yahoo_cross_check_marks_idx_ratio_unavailable_without_synthesizing():
    idx_actions = pd.DataFrame(
        [
            {
                "ticker": "ABCD",
                "action": "stockSplit",
                "effective_date": "2026-07-21",
                "ratio": None,
            }
        ]
    )
    yahoo = pd.DataFrame(
        [{"ticker": "ABCD", "date": "2026-07-21", "stock_splits": 2.0}]
    )

    report = cross_check_yahoo_split_events(idx_actions, yahoo)
    assert report.loc[0, "status"] == "IDX_RATIO_UNAVAILABLE"
    assert pd.isna(report.loc[0, "idx_ratio"])
    assert report.loc[0, "yahoo_ratio"] == pytest.approx(2.0)
