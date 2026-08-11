from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.corporate_actions import (
    audit_split_price_discontinuities,
    build_split_factor_schedule,
    canonicalize_corporate_actions,
)


def _event(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": "ABCD",
        "action_type": "STOCK_SPLIT",
        "announced_at": "2025-01-02T09:00:00",
        "market_effective_date": "2025-01-10",
        "ratio_old": 1,
        "ratio_new": 2,
        "source": "IDX",
        "source_ref": "TEST-001",
        "source_url": "https://www.idx.id/example.pdf",
        "source_sha256": "a" * 64,
    }
    row.update(overrides)
    return row


def test_canonicalize_split_and_knowledge_time() -> None:
    result = canonicalize_corporate_actions(pd.DataFrame([_event()]))

    assert result.loc[0, "event_id"] == "IDX:ABCD:STOCK_SPLIT:20250110"
    assert result.loc[0, "knowledge_at"] == pd.Timestamp("2025-01-02T09:00:00")
    assert result.loc[0, "ratio_old"] == 1
    assert result.loc[0, "ratio_new"] == 2


def test_split_factor_schedule_has_mechanical_ratios() -> None:
    actions = pd.DataFrame(
        [
            _event(),
            _event(
                ticker="EFGH",
                action_type="REVERSE_SPLIT",
                market_effective_date="2025-02-03",
                ratio_old=5,
                ratio_new=1,
                source_ref="TEST-002",
                source_sha256="b" * 64,
            ),
        ]
    )

    schedule = build_split_factor_schedule(actions).set_index("ticker")

    assert schedule.loc["ABCD", "share_multiplier"] == pytest.approx(2.0)
    assert schedule.loc["ABCD", "expected_post_price_ratio"] == pytest.approx(0.5)
    assert schedule.loc["EFGH", "share_multiplier"] == pytest.approx(0.2)
    assert schedule.loc["EFGH", "expected_post_price_ratio"] == pytest.approx(5.0)


def test_rights_issue_requires_subscription_price() -> None:
    frame = pd.DataFrame(
        [
            _event(
                action_type="RIGHTS_ISSUE",
                ratio_old=4,
                ratio_new=1,
                subscription_price=None,
            )
        ]
    )

    with pytest.raises(ValueError, match="subscription_price"):
        canonicalize_corporate_actions(frame)


def test_split_direction_is_validated() -> None:
    frame = pd.DataFrame([_event(ratio_old=2, ratio_new=1)])

    with pytest.raises(ValueError, match="STOCK_SPLIT"):
        canonicalize_corporate_actions(frame)


def test_duplicate_event_requires_explicit_reconciliation() -> None:
    frame = pd.DataFrame(
        [
            _event(source_ref="IDX-A", source_sha256="a" * 64),
            _event(source_ref="IDX-B", source_sha256="b" * 64),
        ]
    )

    with pytest.raises(ValueError, match="explicit evidence reconciliation"):
        canonicalize_corporate_actions(frame)


def test_nonstandard_ticker_fails_closed() -> None:
    frame = pd.DataFrame([_event(ticker="ABCDE")])

    with pytest.raises(ValueError, match="Unsupported corporate-action ticker"):
        canonicalize_corporate_actions(frame)


def test_split_price_discontinuity_audit_is_diagnostic_only() -> None:
    actions = pd.DataFrame([_event()])
    prices = pd.DataFrame(
        [
            {"ticker": "ABCD", "date": "2025-01-09", "raw_open": 990, "raw_close": 1000},
            {"ticker": "ABCD", "date": "2025-01-10", "raw_open": 505, "raw_close": 510},
        ]
    )

    audit = audit_split_price_discontinuities(prices, actions)

    assert len(audit) == 1
    assert audit.loc[0, "previous_close"] == 1000
    assert audit.loc[0, "post_open"] == 505
    assert audit.loc[0, "expected_post_price_ratio"] == pytest.approx(0.5)
    assert audit.loc[0, "observed_open_ratio"] == pytest.approx(0.505)
    assert audit.loc[0, "observed_close_ratio"] == pytest.approx(0.51)


def test_delayed_evidence_preserves_later_knowledge_time() -> None:
    result = canonicalize_corporate_actions(
        pd.DataFrame(
            [
                _event(
                    announced_at="2025-01-02",
                    knowledge_at="2025-02-01",
                    market_effective_date="2025-01-10",
                )
            ]
        )
    )

    assert result.loc[0, "knowledge_at"] == pd.Timestamp("2025-02-01")
