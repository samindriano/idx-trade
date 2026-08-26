from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ca_feature_basis_v1 import (
    BASIS_SAFE,
    BASIS_UNKNOWN,
    BASIS_UNSAFE,
    BOUNDED_UNRESOLVED,
    CASH_DIVIDEND,
    FeatureDependency,
    NOT_BASIS_CHANGING,
    RESOLVED,
    RIGHTS_HMETD,
    STOCK_SPLIT,
    UNRESOLVED,
    V4_PRICE_FEATURE_DEPENDENCIES,
    aggregate_model_row_basis_state,
    apply_direct_feature_basis_mask,
    build_basis_epoch_ledger,
    evaluate_feature_basis_admission,
    prepare_basis_events,
)


SHA = "a" * 64


def sessions(n: int = 90) -> pd.DatetimeIndex:
    return pd.bdate_range("2021-01-04", periods=n)


def identities(n: int = 90, ticker: str = "TEST") -> pd.DataFrame:
    days = sessions(n)
    return pd.DataFrame({"ticker": ticker, "date": days})


def event(
    *,
    ticker: str = "TEST",
    family: str = STOCK_SPLIT,
    identity: str = "EV1",
    state: str = RESOLVED,
    transition_session: object = None,
    lower: object = None,
    upper: object = None,
    justification: str = "",
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "event_family": family,
        "event_identity": identity,
        "effective_transition_state": state,
        "transition_session": transition_session,
        "transition_lower_session": lower,
        "transition_upper_session": upper,
        "source_ref": "fixture://canonical-ca",
        "evidence_id": f"EVIDENCE-{identity}",
        "evidence_sha256": SHA,
        "basis_change_justification": justification,
    }


def test_resolved_split_never_crosses_one_feature_epoch() -> None:
    days = sessions(12)
    ids = pd.DataFrame({"ticker": "TEST", "date": days})
    events = pd.DataFrame(
        [event(transition_session=days[5])]
    )
    dependency = (FeatureDependency("lag2", (-2, 0)),)

    result = evaluate_feature_basis_admission(
        ids, events, days, dependencies=dependency
    )
    state = result.set_index("date")["basis_integrity_state"]

    assert state.loc[days[5]] == BASIS_UNSAFE
    assert state.loc[days[6]] == BASIS_UNSAFE
    assert state.loc[days[7]] == BASIS_SAFE


def test_exact_v4_dependency_recovery_is_geometry_based_not_blanket_60() -> None:
    # Put the transition after a complete pre-event 60-observation warmup so
    # the test measures recovery geometry rather than natural feature maturity.
    days = sessions(140)
    ids = pd.DataFrame({"ticker": "TEST", "date": days})
    transition = days[65]
    events = pd.DataFrame([event(transition_session=transition)])

    result = evaluate_feature_basis_admission(ids, events, days)
    post = result[result["date"].ge(transition)]
    unsafe_counts = (
        post[post["basis_integrity_state"].eq(BASIS_UNSAFE)]
        .groupby("feature")
        .size()
        .to_dict()
    )

    assert unsafe_counts["close_return_5"] == 5
    assert unsafe_counts["atr14_over_close"] == 14
    assert unsafe_counts["close_return_20"] == 20
    # rolling(60) uses t-59..t, so the first all-post-event window is t+59.
    assert unsafe_counts["distance_high_60_atr"] == 59
    assert unsafe_counts["distance_low_60_atr"] == 59


def test_bounded_unknown_only_blocks_dependencies_that_could_cross() -> None:
    days = sessions(15)
    ids = pd.DataFrame({"ticker": "TEST", "date": days})
    events = pd.DataFrame(
        [
            event(
                state=BOUNDED_UNRESOLVED,
                lower=days[5],
                upper=days[6],
            )
        ]
    )
    dependency = (FeatureDependency("lag2", (-2, 0)),)

    result = evaluate_feature_basis_admission(
        ids, events, days, dependencies=dependency
    ).set_index("date")

    assert result.loc[days[4], "basis_integrity_state"] == BASIS_SAFE
    assert result.loc[days[5], "basis_integrity_state"] == BASIS_UNKNOWN
    assert result.loc[days[6], "basis_integrity_state"] == BASIS_UNKNOWN
    assert result.loc[days[7], "basis_integrity_state"] == BASIS_UNKNOWN
    assert result.loc[days[8], "basis_integrity_state"] == BASIS_SAFE


def test_unbounded_unknown_fails_closed_for_full_dependency_rows() -> None:
    days = sessions(8)
    ids = pd.DataFrame({"ticker": "TEST", "date": days})
    events = pd.DataFrame([event(state=UNRESOLVED)])
    dependency = (FeatureDependency("lag1", (-1, 0)),)

    result = evaluate_feature_basis_admission(ids, events, days, dependencies=dependency)
    applicable = result[result["basis_integrity_state"].ne("NOT_APPLICABLE")]
    assert set(applicable["basis_integrity_state"]) == {BASIS_UNKNOWN}


def test_cash_dividend_does_not_create_price_basis_epoch() -> None:
    days = sessions(8)
    ids = pd.DataFrame({"ticker": "TEST", "date": days})
    events = pd.DataFrame(
        [
            event(
                family=CASH_DIVIDEND,
                state=NOT_BASIS_CHANGING,
                transition_session=None,
            )
        ]
    )
    dependency = (FeatureDependency("lag1", (-1, 0)),)

    result = evaluate_feature_basis_admission(ids, events, days, dependencies=dependency)
    applicable = result[result["basis_integrity_state"].ne("NOT_APPLICABLE")]
    assert set(applicable["basis_integrity_state"]) == {BASIS_SAFE}


def test_rights_cannot_be_declared_non_basis_changing_without_justification() -> None:
    days = sessions(5)
    frame = pd.DataFrame(
        [event(family=RIGHTS_HMETD, state=NOT_BASIS_CHANGING)]
    )
    with pytest.raises(ValueError, match="requires explicit justification"):
        prepare_basis_events(frame, days)


def test_multiple_resolved_events_create_distinct_epochs() -> None:
    days = sessions(12)
    ids = pd.DataFrame({"ticker": "TEST", "date": days})
    events = pd.DataFrame(
        [
            event(identity="EV1", transition_session=days[4]),
            event(identity="EV2", transition_session=days[8]),
        ]
    )
    ledger = build_basis_epoch_ledger(ids, events, days).set_index("date")

    assert ledger.loc[days[3], "basis_epoch_id"] == "TEST:E0000"
    assert ledger.loc[days[4], "basis_epoch_id"] == "TEST:E0001"
    assert ledger.loc[days[7], "basis_epoch_id"] == "TEST:E0001"
    assert ledger.loc[days[8], "basis_epoch_id"] == "TEST:E0002"


def test_model_row_aggregation_is_fail_closed() -> None:
    days = sessions(8)
    ids = pd.DataFrame({"ticker": "TEST", "date": days})
    events = pd.DataFrame([event(state=UNRESOLVED)])
    dependencies = (
        FeatureDependency("a", (-1, 0)),
        FeatureDependency("b", (-2, 0)),
    )
    admission = evaluate_feature_basis_admission(
        ids, events, days, dependencies=dependencies
    )
    rows = aggregate_model_row_basis_state(admission, required_features=["a", "b"])

    mature = rows[rows["date"].ge(days[2])]
    assert set(mature["model_row_basis_state"]) == {BASIS_UNKNOWN}


def test_direct_mask_preserves_reason_and_removes_blocked_value() -> None:
    days = sessions(6)
    ids = pd.DataFrame({"ticker": "TEST", "date": days})
    events = pd.DataFrame([event(transition_session=days[3])])
    dependency = (FeatureDependency("signal", (-1, 0)),)
    admission = evaluate_feature_basis_admission(
        ids, events, days, dependencies=dependency
    )
    frame = ids.copy()
    frame["signal"] = 1.0

    masked = apply_direct_feature_basis_mask(
        frame, admission, features=["signal"]
    ).set_index("date")

    assert pd.isna(masked.loc[days[3], "signal"])
    assert masked.loc[days[3], "signal__basis_state"] == BASIS_UNSAFE
    assert masked.loc[days[4], "signal"] == 1.0


def test_evidence_hash_is_required_and_strict() -> None:
    days = sessions(5)
    bad = event(transition_session=days[2])
    bad["evidence_sha256"] = "not-a-sha"
    with pytest.raises(ValueError, match="64 hex"):
        prepare_basis_events(pd.DataFrame([bad]), days)


def test_default_dependency_contract_has_no_future_offsets() -> None:
    assert V4_PRICE_FEATURE_DEPENDENCIES
    assert all(max(spec.offsets) == 0 for spec in V4_PRICE_FEATURE_DEPENDENCIES)
    assert all(min(spec.offsets) <= 0 for spec in V4_PRICE_FEATURE_DEPENDENCIES)
