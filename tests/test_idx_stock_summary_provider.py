import pandas as pd

from idx_trade.providers.idx_stock_summary import (
    parse_stock_summary_payload,
    stock_summary_status_to_anchors,
    stock_summary_url,
)


def test_stock_summary_url_uses_current_official_idx_primary_endpoint():
    url = stock_summary_url("2026-07-31")
    assert url == (
        "https://www.idx.co.id/primary/TradingSummary/GetStockSummary?date=20260731"
    )


def test_parser_preserves_explicit_security_status_without_inferring_from_remarks():
    payload = {
        "recordsTotal": 2,
        "data": [
            {
                "StockCode": "BBCA",
                "Date": "2026-07-31",
                "Remarks": "X",
                "SecurityStatus": "ACTIVE_CODE",
            },
            {
                "StockCode": "BBRI",
                "Date": "2026-07-31",
                "Remarks": "ACTIVE-looking remark must not be interpreted",
            },
        ],
    }
    frame, meta = parse_stock_summary_payload(
        payload,
        requested_date="2026-07-31",
        source_ref="idx://stock-summary/20260731",
    )
    assert len(frame) == 2
    assert meta.records_total == 2
    assert meta.explicit_security_status_rows == 1
    assert frame.loc[frame["ticker"].eq("BBCA"), "security_status_raw"].iloc[0] == "ACTIVE_CODE"
    assert frame.loc[frame["ticker"].eq("BBRI"), "security_status_raw"].iloc[0] == ""


def test_status_anchor_extraction_requires_explicit_audited_mapping():
    payload = {
        "data": [
            {
                "StockCode": "BBCA",
                "Date": "2026-07-31",
                "SecurityStatus": "A",
            },
            {
                "StockCode": "DEAL",
                "Date": "2026-07-31",
                "SecurityStatus": "S",
            },
            {
                "StockCode": "BBRI",
                "Date": "2026-07-31",
            },
        ]
    }
    frame, _ = parse_stock_summary_payload(
        payload,
        requested_date="2026-07-31",
        source_ref="idx://stock-summary/20260731",
    )
    anchors, diagnostics = stock_summary_status_to_anchors(
        frame,
        status_mapping={"A": "ACTIVE", "S": "SUSPENDED"},
    )
    assert set(anchors["ticker"]) == {"BBCA", "DEAL"}
    assert dict(zip(anchors["ticker"], anchors["state"])) == {
        "BBCA": "ACTIVE",
        "DEAL": "SUSPENDED",
    }
    assert diagnostics["ticker"].tolist() == ["BBRI"]
    assert diagnostics.loc[0, "diagnostic"] == "EXPLICIT_SECURITY_STATUS_NOT_EXPOSED"


def test_unmapped_explicit_status_remains_unresolved_not_guessed():
    frame = pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "as_of_date": [pd.Timestamp("2026-07-31")],
            "security_status_raw": ["UNAUDITED_CODE"],
            "source": ["IDX_PUBLIC_STOCK_SUMMARY"],
            "source_ref": ["idx://stock-summary/20260731"],
        }
    )
    anchors, diagnostics = stock_summary_status_to_anchors(
        frame,
        status_mapping={},
    )
    assert anchors.empty
    assert diagnostics.loc[0, "diagnostic"] == "UNMAPPED_SECURITY_STATUS_VALUE"
