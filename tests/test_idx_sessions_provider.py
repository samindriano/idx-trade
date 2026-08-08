import base64
import json

import pandas as pd
import pytest

from idx_trade.providers.idx_sessions import (
    fetch_exchange_sessions,
    monthly_session_page_url,
    parse_exchange_sessions_from_html,
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


def test_session_parser_fails_closed_when_no_month_dates_exist():
    html = _table_html([("01 Oct 2025", "1")])
    with pytest.raises(ValueError, match="No IDX exchange sessions"):
        parse_exchange_sessions_from_html(html, year=2025, month=9)


def test_month_url_embeds_auditable_filter_payload():
    url = monthly_session_page_url(2025, 9)
    encoded = url.split("filter=", 1)[1]
    payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
    assert payload == {"year": "2025", "month": "9", "quarter": 0, "type": "monthly"}


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
