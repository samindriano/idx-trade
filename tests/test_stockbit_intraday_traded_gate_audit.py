from datetime import date

import pandas as pd
import pytest

from idx_trade.stockbit_intraday_traded_gate_audit import (
    build_comparison,
    confusion_for_rule,
    parse_stock_summary_payload,
)


EXPECTED_DATE = date(2026, 8, 11)


def _payload(rows, *, records_total=None):
    payload = {"data": rows, "start": 0, "length": len(rows)}
    if records_total is not None:
        payload["recordsTotal"] = records_total
    return payload


def _row(ticker, volume, value, frequency, *, day="2026-08-11T00:00:00"):
    return {
        "StockCode": ticker,
        "Date": day,
        "Volume": volume,
        "Value": value,
        "Frequency": frequency,
        "Close": 100,
        "High": 105,
        "Low": 95,
    }


def test_parse_stock_summary_preserves_exact_activity_fields():
    frame = parse_stock_summary_payload(
        _payload([_row("BBCA", 1000, 10_000_000, 20)], records_total=1),
        expected_date=EXPECTED_DATE,
    )
    assert frame.to_dict("records") == [
        {
            "ticker": "BBCA",
            "session_date": "2026-08-11",
            "volume": 1000.0,
            "value": 10000000.0,
            "frequency": 20.0,
            "raw_close": 100.0,
            "raw_high": 105.0,
            "raw_low": 95.0,
        }
    ]


def test_parse_stock_summary_accepts_zapi_data_envelope():
    inner = _payload([_row("BBCA", 1000, 10_000_000, 20)], records_total=1)
    frame = parse_stock_summary_payload(
        {"data": {"data": inner["data"], "recordsTotal": inner["recordsTotal"]}},
        expected_date=EXPECTED_DATE,
    )
    assert frame.loc[0, "ticker"] == "BBCA"
    assert frame.loc[0, "volume"] == 1000


def test_parse_stock_summary_fails_closed_on_wrong_session():
    with pytest.raises(ValueError, match="wrong/ambiguous session"):
        parse_stock_summary_payload(
            _payload([_row("BBCA", 1, 1, 1, day="2026-08-08T00:00:00")]),
            expected_date=EXPECTED_DATE,
        )


def test_parse_stock_summary_fails_closed_on_truncation():
    with pytest.raises(ValueError, match="appears truncated"):
        parse_stock_summary_payload(
            _payload([_row("BBCA", 1, 1, 1)], records_total=962),
            expected_date=EXPECTED_DATE,
        )


def test_parse_stock_summary_fails_closed_on_conflicting_duplicates():
    with pytest.raises(ValueError, match="conflicting duplicate"):
        parse_stock_summary_payload(
            _payload([
                _row("BBCA", 1, 1, 1),
                _row("BBCA", 2, 2, 2),
            ]),
            expected_date=EXPECTED_DATE,
        )


def test_activity_gate_comparison_and_confusion_are_exact():
    universe = pd.DataFrame({"ticker": ["BBCA", "BBRI", "ZZZZ"]})
    status = pd.DataFrame(
        {
            "ticker": ["BBCA", "BBRI", "ZZZZ"],
            "status": ["SUCCESS", "SUCCESS", "REQUEST_ERROR"],
        }
    )
    summary = parse_stock_summary_payload(
        _payload([
            _row("BBCA", 10, 1000, 2),
            _row("BBRI", 0, 0, 0),
            _row("ZZZZ", 1, 100, 1),
        ]),
        expected_date=EXPECTED_DATE,
    )
    comparison = build_comparison(universe, status, summary)
    confusion = confusion_for_rule(comparison, "activity_or")
    assert confusion.true_positive == 1
    assert confusion.false_positive == 1
    assert confusion.false_negative == 1
    assert confusion.true_negative == 0
    assert confusion.precision == 0.5
    assert confusion.recall == 0.5


def test_missing_idx_summary_row_is_fail_closed_to_no_activity_not_synthetic():
    universe = pd.DataFrame({"ticker": ["BBCA", "BBRI"]})
    status = pd.DataFrame({"ticker": ["BBCA", "BBRI"], "status": ["SUCCESS", "REQUEST_ERROR"]})
    summary = parse_stock_summary_payload(
        _payload([_row("BBCA", 10, 1000, 2)]),
        expected_date=EXPECTED_DATE,
    )
    comparison = build_comparison(universe, status, summary)
    bbri = comparison.loc[comparison["ticker"].eq("BBRI")].iloc[0]
    assert not bool(bbri["idx_summary_present"])
    assert not bool(bbri["activity_or"])


def test_zero_false_negative_gate_is_possible_with_404_savings():
    universe = pd.DataFrame({"ticker": ["BBCA", "BBRI", "ZZZZ"]})
    status = pd.DataFrame(
        {
            "ticker": ["BBCA", "BBRI", "ZZZZ"],
            "status": ["SUCCESS", "SUCCESS", "REQUEST_ERROR"],
        }
    )
    summary = parse_stock_summary_payload(
        _payload([
            _row("BBCA", 10, 1000, 2),
            _row("BBRI", 5, 500, 1),
            _row("ZZZZ", 0, 0, 0),
        ]),
        expected_date=EXPECTED_DATE,
    )
    comparison = build_comparison(universe, status, summary)
    confusion = confusion_for_rule(comparison, "activity_or")
    assert confusion.false_negative == 0
    assert confusion.true_positive == 2
    assert confusion.true_negative == 1
