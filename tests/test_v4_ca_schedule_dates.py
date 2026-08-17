from idx_trade.v4_ca_schedule_semantics import date_iso


def test_indonesian_day_first_date():
    assert date_iso("16 April 2026") == "2026-04-16"


def test_english_month_first_date():
    assert date_iso("April 16, 2026") == "2026-04-16"


def test_invalid_date_text_fails_closed():
    assert date_iso("not a date") is None
