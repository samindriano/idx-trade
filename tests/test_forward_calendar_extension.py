import hashlib

import pandas as pd
import pytest

import idx_trade.forward_calendar_extension as extension_module
from idx_trade.forward_calendar_extension import (
    CalendarExtensionError,
    TradingHoursEvidence,
    extend_official_calendar,
    resolve_first_post_freeze_extension_session,
    verify_official_trading_hours,
)
from idx_trade.providers.idx_sessions import ExchangeSessionSourceResult


HOURS_HTML = """
<table>
<tr><td>Pre opening (Input)</td><td>Monday - Friday</td><td>08.45.00 – 08.57.59</td></tr>
<tr><td>Session I</td><td>Monday - Thursday</td><td>09.00.00 – 12.00.00</td></tr>
</table>
"""


def test_trading_hours_requires_live_official_rule():
    evidence = verify_official_trading_hours(HOURS_HTML)
    assert evidence.session_start_time == "08:45:00"
    assert evidence.timezone == "Asia/Jakarta"
    with pytest.raises(CalendarExtensionError, match="does not support"):
        verify_official_trading_hours("<p>Session I 10:00</p>")


def test_extension_continues_indices_deterministically_and_resolves_first_session(tmp_path, monkeypatch):
    historical = tmp_path / "historical.csv"
    historical.write_text("date\n2026-07-30\n2026-07-31\n", encoding="utf-8")
    monkeypatch.setattr(
        extension_module,
        "HISTORICAL_CALENDAR_SHA256",
        hashlib.sha256(historical.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(extension_module, "HISTORICAL_SESSION_COUNT", 2)
    hours = TradingHoursEvidence(
        source_identity="IDX_EQUITY_TRADING_HOURS_CURRENT",
        source_ref="https://www.idx.id/en/products-services/trading-hours-and-mechanism/",
        retrieved_at_utc="2026-08-12T00:00:00+00:00",
        raw_sha256="0" * 64,
    )

    def fetch_month(year, month):
        assert (year, month) == (2026, 8)
        return ExchangeSessionSourceResult(
            sessions=pd.DatetimeIndex(["2026-08-03", "2026-08-04"]),
            source_identity="IDX_DAILY_STATISTICS_PUBLICATION_LISTING",
            source_ref="https://www.idx.id/primary/Statistic/GetStatistic",
        )

    first, sources, _ = extend_official_calendar(
        historical_calendar_path=historical,
        end="2026-08-05",
        trading_hours=hours,
        fetch_month=fetch_month,
    )
    assert first["session_index"].tolist() == [3, 4]
    assert first["session_date"].tolist() == ["2026-08-03", "2026-08-04"]
    assert first["session_start"].tolist() == [
        "2026-08-03T08:45:00+07:00",
        "2026-08-04T08:45:00+07:00",
    ]
    assert sources.loc[0, "status"] == "PARSED"
    resolved = resolve_first_post_freeze_extension_session(first, "2026-08-03T08:45:00+07:00")
    assert resolved["session_index"] == 4
    assert resolved["session_date"] == "2026-08-04"


def test_extension_source_failure_is_recorded_and_no_inferred_dates_are_created(tmp_path, monkeypatch):
    historical = tmp_path / "historical.csv"
    historical.write_text("date\n2026-07-30\n2026-07-31\n", encoding="utf-8")
    monkeypatch.setattr(
        extension_module,
        "HISTORICAL_CALENDAR_SHA256",
        hashlib.sha256(historical.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(extension_module, "HISTORICAL_SESSION_COUNT", 2)
    hours = TradingHoursEvidence("IDX", "https://www.idx.id/hours", "now", "0" * 64)

    def fetch_month(year, month):
        raise ValueError("official source unavailable")

    with pytest.raises(CalendarExtensionError, match="contains no dates"):
        extend_official_calendar(
            historical_calendar_path=historical,
            end="2026-08-05",
            trading_hours=hours,
            fetch_month=fetch_month,
        )
