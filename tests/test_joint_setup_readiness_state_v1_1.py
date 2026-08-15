from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.joint_setup_readiness_state import (
    FOREIGN_FLOW_STATE_CONTRACT_VERSION,
    PRICE_STATE_CONTRACT_VERSION,
    ParentProvenance,
)
from idx_trade.joint_setup_readiness_state_v1_1 import (
    JOINT_STATE_CONTRACT_VERSION,
    JointStateContractError,
    build_joint_setup_readiness_state_v1_1,
    joint_contract_fingerprint_v1_1,
)


SESSIONS = pd.to_datetime(["2026-08-11", "2026-08-12", "2026-08-13"])
FF_SHA = "a" * 64
FF_MANIFEST_SHA = "b" * 64
PRICE_SHA = "c" * 64
PRICE_MANIFEST_SHA = "d" * 64


def _provenance() -> tuple[ParentProvenance, ParentProvenance]:
    return (
        ParentProvenance(
            artifact_sha256=FF_SHA,
            manifest_sha256=FF_MANIFEST_SHA,
            contract_version=FOREIGN_FLOW_STATE_CONTRACT_VERSION,
            source_kind="FOREIGN_FLOW_PROSPECTIVE_REPRESENTATION_V2",
            outcome_blind=True,
            provider_calls=0,
            model_fitted=False,
            model_scoring=False,
            trade_recommendation=False,
            forward_outcomes_accessed=False,
            outcomes_or_labels_accessed=False,
        ),
        ParentProvenance(
            artifact_sha256=PRICE_SHA,
            manifest_sha256=PRICE_MANIFEST_SHA,
            contract_version=PRICE_STATE_CONTRACT_VERSION,
            source_kind="PRICE_TREND_CANONICAL_EOD",
            outcome_blind=True,
            provider_calls=0,
            model_fitted=False,
            model_scoring=False,
            trade_recommendation=False,
            forward_outcomes_accessed=False,
            outcomes_or_labels_accessed=False,
        ),
    )


def _parents(tickers: tuple[str, ...] = ("AAA", "BBB")) -> tuple[pd.DataFrame, pd.DataFrame]:
    ff = pd.DataFrame(
        {
            "ticker": list(tickers),
            "feature_session": ["2026-08-12"] * len(tickers),
            "flow_through_session": ["2026-08-11"] * len(tickers),
            "setup_label": ["PERSISTENT_ACCUMULATION"] * len(tickers),
            "state_contract_version": [FOREIGN_FLOW_STATE_CONTRACT_VERSION] * len(tickers),
        }
    )
    price = pd.DataFrame(
        {
            "ticker": list(tickers),
            "source_session": ["2026-08-11"] * len(tickers),
            "feature_session": ["2026-08-12"] * len(tickers),
            "trend_state": ["UPTREND"] * len(tickers),
            "confirmation_state": ["NO_BREAKOUT"] * len(tickers),
            "state_contract_version": [PRICE_STATE_CONTRACT_VERSION] * len(tickers),
            "outcome_blind": [True] * len(tickers),
            "model_fitted": [False] * len(tickers),
            "model_scoring": [False] * len(tickers),
            "trade_recommendation": [False] * len(tickers),
        }
    )
    return ff, price


def _build(ff: pd.DataFrame, price: pd.DataFrame):
    ff_provenance, price_provenance = _provenance()
    return build_joint_setup_readiness_state_v1_1(
        ff,
        price,
        official_sessions=SESSIONS,
        foreign_flow_provenance=ff_provenance,
        price_state_provenance=price_provenance,
    )


def test_ff_superset_is_allowed_and_output_is_exact_price_domain() -> None:
    ff, price = _parents()
    extra_ff, _ = _parents(("EXTRA",))
    ff = pd.concat([ff, extra_ff], ignore_index=True)

    result = _build(ff, price)

    assert len(result.frame) == 2
    assert result.frame["ticker"].tolist() == ["AAA", "BBB"]
    assert result.domain.foreign_flow_key_count == 3
    assert result.domain.price_state_key_count == 2
    assert result.domain.overlap_key_count == 2
    assert result.domain.price_only_key_count == 0
    assert result.domain.foreign_flow_only_key_count == 1
    assert result.domain.foreign_flow_only_keys == (("EXTRA", "2026-08-12"),)
    assert result.frame["joint_state_contract_version"].eq(JOINT_STATE_CONTRACT_VERSION).all()


def test_missing_required_price_key_in_foreign_flow_fails_closed() -> None:
    ff, price = _parents()
    ff = ff.iloc[:1].copy()

    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)

    assert error.value.reason_codes == ("PRICE_KEY_MISSING_IN_FOREIGN_FLOW", "PARENT_KEY_SET_MISMATCH")
    assert error.value.domain_report.price_only_keys == (("BBB", "2026-08-12"),)  # type: ignore[attr-defined]


def test_duplicate_required_foreign_flow_key_fails_closed() -> None:
    ff, price = _parents()
    ff = pd.concat([ff, ff.iloc[[0]]], ignore_index=True)

    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)

    assert error.value.reason_codes == ("PARENT_DUPLICATE_KEY",)


def test_extra_foreign_flow_rows_cannot_change_joined_outputs() -> None:
    ff, price = _parents()
    baseline = _build(ff, price).frame
    extra_ff, _ = _parents(("EXTRA",))
    extended = _build(pd.concat([ff, extra_ff], ignore_index=True), price).frame

    pd.testing.assert_frame_equal(baseline, extended)


def test_parent_order_invariance_is_deterministic() -> None:
    ff, price = _parents()
    original = _build(ff, price).frame
    shuffled = _build(ff.sample(frac=1, random_state=4), price.sample(frac=1, random_state=9)).frame

    pd.testing.assert_frame_equal(original, shuffled)


def test_joined_source_session_mismatch_fails_closed() -> None:
    ff, price = _parents()
    price.loc[0, "source_session"] = "2026-08-12"

    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)

    assert error.value.reason_codes == ("SOURCE_SESSION_MISMATCH",)


@pytest.mark.parametrize("bad_ticker", [None, "AAA.JK", "aaa"])
def test_parent_ticker_identity_remains_strict(bad_ticker: object) -> None:
    ff, price = _parents()
    ff.loc[0, "ticker"] = bad_ticker

    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)

    assert error.value.reason_codes == ("TICKER_IDENTITY_INVALID",)


def test_protected_parent_flags_remain_fail_closed() -> None:
    ff, price = _parents()
    price.loc[0, "model_scoring"] = True

    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)

    assert error.value.reason_codes == ("PARENT_ACCESS_FLAGS_INVALID",)


def test_v1_1_fingerprint_is_pinned_and_does_not_replace_v1() -> None:
    assert joint_contract_fingerprint_v1_1() == "c1bd084dfe54dacd447ee15915e5210e539cfc99b19f42f1543bfa3f1801d5de"
