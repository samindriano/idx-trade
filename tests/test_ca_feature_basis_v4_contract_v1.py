from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ca_feature_basis_gate_v1 import (
    BASIS_SAFE,
    BASIS_UNKNOWN,
    BASIS_UNSAFE,
    CA_COVERAGE_CERTIFIED,
)
from idx_trade.ca_feature_basis_v1 import (
    NOT_APPLICABLE,
    RESOLVED,
    REVERSE_SPLIT,
    RIGHTS_HMETD,
    STOCK_SPLIT,
)
from idx_trade.ca_feature_basis_v4_contract_v1 import (
    V4_CA_BASIS_DIRECT_SOURCE_FEATURES,
    V4_CA_ROW_ADMITTED,
    V4_CA_ROW_BLOCKED_UNKNOWN,
    V4_CA_ROW_BLOCKED_UNSAFE,
    evaluate_v4_application_feature_basis_admission,
    evaluate_v4_feature_basis_admission,
    summarize_v4_model_row_ca_admission,
)


SHA = "a" * 64
SEMANTIC_SHA = "b" * 64


def sessions(n: int = 150) -> pd.DatetimeIndex:
    return pd.bdate_range("2021-01-04", periods=n)


def identities(days: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame({"ticker": "TEST", "date": days})


def coverage(days: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": "TEST",
            "date": days,
            "coverage_state": CA_COVERAGE_CERTIFIED,
            "source_ref": "fixture://global-ca-coverage",
            "evidence_sha256": SHA,
        }
    )


def event(days: pd.DatetimeIndex, *, family: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "event_family": family,
                "event_identity": "EV1",
                "effective_transition_state": RESOLVED,
                "transition_session": days[70],
                "transition_lower_session": None,
                "transition_upper_session": None,
                "source_ref": "fixture://event",
                "evidence_id": "EV1-EVIDENCE",
                "evidence_sha256": SHA,
                "event_semantics_certified": True,
                "semantic_evidence_sha256": SEMANTIC_SHA,
            }
        ]
    )


def test_resolved_split_blocks_exact_19_post_event_relative_volume_rows() -> None:
    days = sessions()
    result = evaluate_v4_feature_basis_admission(
        identities(days), event(days, family=STOCK_SPLIT), coverage(days), days
    )
    volume = result[result["feature"].eq("relative_volume_20")]
    post = volume[volume["date"].ge(days[70])]
    unsafe = post[post["basis_integrity_state"].eq(BASIS_UNSAFE)]

    # rolling(20) depends on t-19..t.  At transition t0, rows t0..t0+18
    # still contain at least one old-unit raw-volume observation.
    assert len(unsafe) == 19
    assert unsafe["date"].min() == days[70]
    assert unsafe["date"].max() == days[88]
    assert post.set_index("date").loc[days[89], "basis_integrity_state"] == BASIS_SAFE


def test_reverse_split_has_same_raw_volume_unit_boundary() -> None:
    days = sessions()
    result = evaluate_v4_feature_basis_admission(
        identities(days), event(days, family=REVERSE_SPLIT), coverage(days), days
    )
    volume = result[result["feature"].eq("relative_volume_20")]
    post = volume[volume["date"].ge(days[70])]
    assert int(post["basis_integrity_state"].eq(BASIS_UNSAFE).sum()) == 19


def test_rights_event_does_not_overblock_raw_volume_without_unit_basis_contract() -> None:
    days = sessions()
    result = evaluate_v4_feature_basis_admission(
        identities(days), event(days, family=RIGHTS_HMETD), coverage(days), days
    )
    volume = result[
        result["feature"].eq("relative_volume_20") & result["date"].ge(days[70])
    ]

    assert set(volume["basis_integrity_state"]) == {BASIS_SAFE}
    # Price-derived dependencies remain independently protected across rights.
    price = result[
        result["feature"].eq("close_return_20") & result["date"].ge(days[70])
    ]
    assert int(price["basis_integrity_state"].eq(BASIS_UNSAFE).sum()) == 20


def test_application_scope_is_selected_only_after_full_stream_geometry() -> None:
    days = sessions()
    full = identities(days)
    # Deliberately sparse application identities: using these rows as the shift
    # stream would redefine "20 observations" into roughly 40 market sessions.
    scope = full.iloc[::2].reset_index(drop=True)
    result = evaluate_v4_application_feature_basis_admission(
        full,
        scope,
        event(days, family=STOCK_SPLIT),
        coverage(days),
        days,
    )
    expected = evaluate_v4_feature_basis_admission(
        full,
        event(days, family=STOCK_SPLIT),
        coverage(days),
        days,
    ).merge(scope, on=["ticker", "date"], how="inner")

    left = result.sort_values(["date", "feature"], kind="mergesort").reset_index(drop=True)
    right = expected.sort_values(["date", "feature"], kind="mergesort").reset_index(drop=True)
    assert left[["ticker", "date", "feature", "basis_integrity_state"]].equals(
        right[["ticker", "date", "feature", "basis_integrity_state"]]
    )


def test_application_scope_must_be_subset_of_full_stream() -> None:
    days = sessions()
    full = identities(days)
    scope = pd.concat(
        [full.iloc[[0]], pd.DataFrame({"ticker": ["TEST"], "date": [days[-1] + pd.Timedelta(days=7)]})],
        ignore_index=True,
    )
    with pytest.raises(ValueError, match="outside full observation stream"):
        evaluate_v4_application_feature_basis_admission(
            full,
            scope,
            event(days, family=STOCK_SPLIT),
            coverage(days),
            days,
        )


def test_natural_not_applicable_feature_does_not_change_training_row_identity() -> None:
    day = pd.Timestamp("2021-01-04")
    rows = []
    for feature in V4_CA_BASIS_DIRECT_SOURCE_FEATURES:
        rows.append(
            {
                "ticker": "TEST",
                "date": day,
                "feature": feature,
                "basis_integrity_state": (
                    NOT_APPLICABLE if feature == "distance_high_60_atr" else BASIS_SAFE
                ),
            }
        )
    summary = summarize_v4_model_row_ca_admission(pd.DataFrame(rows)).iloc[0]
    assert summary["v4_ca_row_state"] == V4_CA_ROW_ADMITTED
    assert summary["natural_not_applicable_feature_count"] == 1


def test_unsafe_or_unknown_ca_state_blocks_model_row() -> None:
    day = pd.Timestamp("2021-01-04")

    def summary_for(blocked_state: str) -> str:
        rows = []
        for feature in V4_CA_BASIS_DIRECT_SOURCE_FEATURES:
            rows.append(
                {
                    "ticker": "TEST",
                    "date": day,
                    "feature": feature,
                    "basis_integrity_state": (
                        blocked_state if feature == "close_return_5" else BASIS_SAFE
                    ),
                }
            )
        return str(summarize_v4_model_row_ca_admission(pd.DataFrame(rows)).iloc[0]["v4_ca_row_state"])

    assert summary_for(BASIS_UNSAFE) == V4_CA_ROW_BLOCKED_UNSAFE
    assert summary_for(BASIS_UNKNOWN) == V4_CA_ROW_BLOCKED_UNKNOWN


def test_v4_direct_basis_contract_includes_relative_volume_once() -> None:
    assert V4_CA_BASIS_DIRECT_SOURCE_FEATURES.count("relative_volume_20") == 1
    assert "close_return_5" in V4_CA_BASIS_DIRECT_SOURCE_FEATURES
