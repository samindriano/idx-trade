import base64
import json
from urllib.parse import unquote

import pandas as pd
import pytest

from idx_trade.providers.idx_sessions import (
    IDX_DAILY_STATISTICS_SOURCE_ID,
    daily_statistics_url,
    fetch_exchange_sessions,
    fetch_exchange_sessions_month,
    fetch_exchange_sessions_month_with_source,
    monthly_session_page_url,
    monthly_session_data_url,
    parse_exchange_sessions_from_daily_statistics,
    parse_exchange_sessions_from_html,
    parse_exchange_sessions_from_json,
)


def _table_html(rows: list[tuple[str, str]]) -> str:
    body = "".join(f"<tr><td>{date}</td><td>{value}</td></tr>" for date, value in rows)
    return f"<html><table><thead><tr><th>Date</th><th>Value</th></tr></thead><tbody>{body}</tbody></table></html>"


def test_parses_only_date_like_table_cells_for_requested_month():
    html = _table_html(
        [
            ("01 Sep 2025", "2390249492113"),
            ("02 Sep 2025", "2180657995183"),
            ("03 Sep 2025", "3119068402882"),
        ]
    ) + "<p>24 July 2026 18:42 WIB</p>"
    sessions = parse_exchange_sessions_from_html(html, year=2025, month=9)
    assert sessions.tolist() == [
        pd.Timestamp("2025-09-01"),
        pd.Timestamp("2025-09-02"),
        pd.Timestamp("2025-09-03"),
    ]


def test_duplicate_dates_across_multiple_tables_are_deduplicated():
    table = _table_html([("01 Sep 2025", "1"), ("02 Sep 2025", "2")])
    sessions = parse_exchange_sessions_from_html(table + table, year=2025, month=9)
    assert sessions.tolist() == [pd.Timestamp("2025-09-01"), pd.Timestamp("2025-09-02")]


def test_parses_official_session_api_dates_and_ignores_out_of_month_rows():
    payload = {
        "TableName": "",
        "data": [
            {"date": "2025-09-01", "foreignForeignVolume": 1},
            {"date": "2025-09-02", "foreignForeignVolume": 2},
            {"date": "2025-10-01", "foreignForeignVolume": 3},
        ],
    }
    sessions = parse_exchange_sessions_from_json(payload, year=2025, month=9)
    assert sessions.tolist() == [pd.Timestamp("2025-09-01"), pd.Timestamp("2025-09-02")]


def test_session_parser_fails_closed_when_no_month_dates_exist():
    html = _table_html([("01 Oct 2025", "1")])
    with pytest.raises(ValueError, match="No IDX exchange sessions"):
        parse_exchange_sessions_from_html(html, year=2025, month=9)


def test_month_url_embeds_auditable_filter_payload():
    url = monthly_session_page_url(2025, 9)
    encoded = url.split("filter=", 1)[1]
    payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
    assert payload == {"year": "2025", "month": "9", "quarter": 0, "type": "monthly"}


def test_session_data_url_targets_official_idx_api():
    url = monthly_session_data_url(2025, 9)
    assert "primary/DigitalStatistic/GetApiData?" in url
    assert "LINK_TABLE_DAILY_TRADING_INVESTOR_FOREIGN" in url


def test_fetch_range_combines_months_and_clips_boundaries():
    pages = {
        "2025-09": _table_html([("29 Sep 2025", "1"), ("30 Sep 2025", "2")]),
        "2025-10": _table_html([("01 Oct 2025", "3"), ("02 Oct 2025", "4")]),
    }

    def fetcher(url: str) -> str:
        encoded = url.split("filter=", 1)[1]
        payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
        return pages[f"{payload['year']}-{int(payload['month']):02d}"]

    sessions = fetch_exchange_sessions("2025-09-30", "2025-10-01", fetch_html=fetcher)
    assert sessions.tolist() == [pd.Timestamp("2025-09-30"), pd.Timestamp("2025-10-01")]


def test_fetch_range_uses_official_json_endpoint_by_default():
    payloads = {
        "2025-09": {"data": [{"date": "2025-09-30"}]},
        "2025-10": {"data": [{"date": "2025-10-01"}]},
    }

    def fetcher(url: str) -> dict[str, object]:
        encoded = unquote(url.split("query=", 1)[1].split("&", 1)[0])
        payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
        return payloads[f"{payload['year']}-{int(payload['month']):02d}"]

    sessions = fetch_exchange_sessions(
        "2025-09-30", "2025-10-01", fetch_json=fetcher
    )
    assert sessions.tolist() == [pd.Timestamp("2025-09-30"), pd.Timestamp("2025-10-01")]


def _july_2026_daily_statistics_rows() -> list[dict[str, object]]:
    dates = [
        "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06", "2026-07-07",
        "2026-07-08", "2026-07-09", "2026-07-10", "2026-07-13", "2026-07-14",
        "2026-07-15", "2026-07-16", "2026-07-17", "2026-07-20", "2026-07-21",
        "2026-07-22", "2026-07-23", "2026-07-24", "2026-07-27", "2026-07-28",
        "2026-07-29", "2026-07-30", "2026-07-31",
    ]
    return [
        {
            "id": 0,
            "year": 2026,
            "type": "daily",
            "number": f"DS{date[2:4]}{date[5:7]}{date[8:10]}",
            "description": f"IDX Daily Statistics - {date}",
            "date": date,
            "file": f"https://www.idx.co.id/Media/example-{date}.pdf",
        }
        for date in dates
    ]


def test_daily_statistics_value_fixture_yields_23_official_july_dates():
    sessions = parse_exchange_sessions_from_daily_statistics(
        {"value": _july_2026_daily_statistics_rows()},
        start="2026-07-01",
        end="2026-07-31",
    )
    assert len(sessions) == 23
    assert sessions[0] == pd.Timestamp("2026-07-01")
    assert sessions[-1] == pd.Timestamp("2026-07-31")


def test_daily_statistics_top_level_list_shape_is_supported():
    sessions = parse_exchange_sessions_from_daily_statistics(
        _july_2026_daily_statistics_rows()[:2],
        start="2026-07-01",
        end="2026-07-31",
    )
    assert sessions.tolist() == [pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-02")]


def test_daily_statistics_url_contains_official_listing_parameters():
    url = daily_statistics_url("2026-07-01", "2026-07-31", lang="en-us", keyword="")
    assert "primary/Statistic/GetStatistic?" in url
    assert "type=daily" in url
    assert "lang=en-us" in url
    assert "StartDate=2026-07-01" in url
    assert "EndDate=2026-07-31" in url
    assert "keyword=" in url


def test_daily_statistics_parser_fails_closed_on_malformed_or_empty_source():
    with pytest.raises(ValueError, match="no source dates"):
        parse_exchange_sessions_from_daily_statistics(
            {"value": []}, start="2026-07-01", end="2026-07-31"
        )
    with pytest.raises(ValueError, match="malformed row"):
        parse_exchange_sessions_from_daily_statistics(
            {"value": [{"description": "missing date"}]},
            start="2026-07-01",
            end="2026-07-31",
        )


def test_daily_statistics_fallback_handles_empty_monthly_source():
    daily_rows = _july_2026_daily_statistics_rows()

    def monthly_fetcher(url: str) -> dict[str, object]:
        assert "DigitalStatistic/GetApiData" in url
        return {"data": []}

    def daily_fetcher(url: str) -> dict[str, object]:
        assert "Statistic/GetStatistic" in url
        return {"value": daily_rows}

    result = fetch_exchange_sessions_month_with_source(
        2026,
        7,
        fetch_json=monthly_fetcher,
        fetch_daily_statistics_json=daily_fetcher,
    )
    assert result.source_identity == IDX_DAILY_STATISTICS_SOURCE_ID
    assert result.fallback_reason == "MONTHLY_DIGITAL_STATISTICS_EMPTY_OR_INVALID"
    assert len(result.sessions) == 23


def test_daily_statistics_fallback_replaces_incomplete_monthly_source():
    daily_rows = _july_2026_daily_statistics_rows()

    def monthly_fetcher(url: str) -> dict[str, object]:
        return {"data": [{"date": row["date"]} for row in daily_rows[:20]]}

    def daily_fetcher(url: str) -> dict[str, object]:
        return {"value": daily_rows}

    sessions = fetch_exchange_sessions_month(
        2026,
        7,
        fetch_json=monthly_fetcher,
        fetch_daily_statistics_json=daily_fetcher,
    )
    assert len(sessions) == 23
    assert sessions[-1] == pd.Timestamp("2026-07-31")
