from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from idx_trade.personal_portfolio import (
    InvestmentHealthContext,
    ShortHorizonModelContext,
    TradingOpportunityContext,
    assert_minimized_canonical_payload,
)


def test_short_horizon_context_is_not_long_term_investment_action():
    context = ShortHorizonModelContext(
        as_of=datetime(2026, 8, 13, 16, 0, tzinfo=timezone(timedelta(hours=7))),
        model_id="synthetic-ranker",
        horizon_sessions=10,
        rank=4,
        score=Decimal("0.61"),
    )
    trading = TradingOpportunityContext(short_horizon_model=context)
    investment = InvestmentHealthContext()
    assert context.interpretation == "CONTEXT_ONLY_NO_LONG_TERM_ACTION"
    assert not hasattr(context, "action")
    assert trading != investment


def test_sensitive_field_names_fail_closed():
    for key in ("nik", "rekening", "account_number", "refresh_token"):
        with pytest.raises(ValueError, match="forbidden sensitive field"):
            assert_minimized_canonical_payload({key: "synthetic-only"})
