from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.joint_setup_readiness_state import (
    FOREIGN_FLOW_STATE_CONTRACT_VERSION,
    JOINT_STATE_CONTRACT_VERSION,
    JOINT_RULE_MATRIX,
    OUTPUT_SCHEMA,
    PRICE_STATE_CONTRACT_VERSION,
    JointStateContractError,
    JointReadinessState,
    ParentProvenance,
    build_joint_setup_readiness_state,
    joint_contract_fingerprint,
)


SESSIONS = pd.to_datetime(["2026-08-10", "2026-08-11", "2026-08-12"])
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


def _parents(labels: list[str], trends: list[str], confirmations: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    tickers = [f"TICK{index}" for index in range(len(labels))]
    ff = pd.DataFrame(
        {
            "ticker": tickers,
            "feature_session": ["2026-08-12"] * len(tickers),
            "flow_through_session": ["2026-08-11"] * len(tickers),
            "setup_label": labels,
            "state_contract_version": [FOREIGN_FLOW_STATE_CONTRACT_VERSION] * len(tickers),
        }
    )
    price = pd.DataFrame(
        {
            "ticker": tickers,
            "source_session": ["2026-08-11"] * len(tickers),
            "feature_session": ["2026-08-12"] * len(tickers),
            "trend_state": trends,
            "confirmation_state": confirmations,
            "state_contract_version": [PRICE_STATE_CONTRACT_VERSION] * len(tickers),
            "outcome_blind": [True] * len(tickers),
            "model_fitted": [False] * len(tickers),
            "model_scoring": [False] * len(tickers),
            "trade_recommendation": [False] * len(tickers),
        }
    )
    return ff, price


def _build(ff: pd.DataFrame, price: pd.DataFrame) -> pd.DataFrame:
    ff_provenance, price_provenance = _provenance()
    return build_joint_setup_readiness_state(
        ff,
        price,
        official_sessions=SESSIONS,
        foreign_flow_provenance=ff_provenance,
        price_state_provenance=price_provenance,
    )


def test_frozen_progression_matrix_is_deterministic_and_descriptive_only() -> None:
    ff, price = _parents(
        [
            "PERSISTENT_ACCUMULATION",
            "ABNORMAL_ACCUMULATION",
            "HIGH_PARTICIPATION_ROUTINE_FLOW",
            "ABNORMAL_ACCUMULATION",
            "DISTRIBUTION_PRESSURE",
            "PERSISTENT_ACCUMULATION",
        ],
        ["UPTREND", "EARLY_REVERSAL", "UPTREND", "BASING", "UPTREND", "DOWNTREND"],
        [
            "BREAKOUT_CONFIRMED",
            "NEAR_BREAKOUT",
            "NO_BREAKOUT",
            "NO_BREAKOUT",
            "NO_BREAKOUT",
            "NO_BREAKOUT",
        ],
    )

    result = _build(ff, price)
    assert result["joint_state"].tolist() == [
        "ENTRY_ELIGIBLE",
        "READY",
        "WATCH",
        "READY",
        "IGNORE",
        "IGNORE",
    ]
    assert result["joint_state_contract_version"].eq(JOINT_STATE_CONTRACT_VERSION).all()
    assert result["outcome_blind"].eq(True).all()
    assert result["model_fitted"].eq(False).all()
    assert result["model_scoring"].eq(False).all()
    assert result["trade_recommendation"].eq(False).all()
    assert "PRICE_BREAKOUT_CONFIRMED" in result.loc[0, "reason_codes"]
    assert "PRICE_DOWNTREND" in result.loc[5, "reason_codes"]
    assert result.loc[0, "foreign_flow_artifact_sha256"] == FF_SHA
    assert result.loc[0, "price_state_manifest_sha256"] == PRICE_MANIFEST_SHA
    pd.testing.assert_frame_equal(result, _build(ff, price))


def test_missing_parent_keys_fail_closed_instead_of_partial_join() -> None:
    ff, price = _parents(["PERSISTENT_ACCUMULATION"], ["UPTREND"], ["NO_BREAKOUT"])
    extra_ff, _ = _parents(["PERSISTENT_ACCUMULATION"], ["UPTREND"], ["NO_BREAKOUT"])
    extra_ff.loc[0, "ticker"] = "OTHER"
    ff = pd.concat([ff, extra_ff], ignore_index=True)

    with pytest.raises(JointStateContractError, match="key sets") as error:
        _build(ff, price)
    assert error.value.reason_codes == ("PARENT_KEY_SET_MISMATCH",)


def test_source_target_mismatch_and_non_next_session_fail_closed() -> None:
    ff, price = _parents(["PERSISTENT_ACCUMULATION"], ["UPTREND"], ["NO_BREAKOUT"])
    price.loc[0, "source_session"] = "2026-08-10"
    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)
    assert error.value.reason_codes == ("SOURCE_SESSION_MISMATCH",)

    ff, price = _parents(["PERSISTENT_ACCUMULATION"], ["UPTREND"], ["NO_BREAKOUT"])
    ff.loc[0, "feature_session"] = "2026-08-11"
    price.loc[0, "feature_session"] = "2026-08-11"
    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)
    assert error.value.reason_codes == ("CAUSAL_SESSION_MISMATCH",)


def test_provenance_and_parent_access_flags_fail_closed() -> None:
    ff, price = _parents(["PERSISTENT_ACCUMULATION"], ["UPTREND"], ["NO_BREAKOUT"])
    ff_provenance, price_provenance = _provenance()
    bad_price = ParentProvenance(
        artifact_sha256=PRICE_SHA,
        manifest_sha256=PRICE_MANIFEST_SHA,
        contract_version=PRICE_STATE_CONTRACT_VERSION,
        source_kind="PRICE_TREND_CANONICAL_EOD",
        outcome_blind=True,
        provider_calls=0,
        model_fitted=False,
        model_scoring=True,
        trade_recommendation=False,
        forward_outcomes_accessed=False,
        outcomes_or_labels_accessed=False,
    )
    with pytest.raises(JointStateContractError) as error:
        build_joint_setup_readiness_state(
            ff,
            price,
            official_sessions=SESSIONS,
            foreign_flow_provenance=ff_provenance,
            price_state_provenance=bad_price,
        )
    assert error.value.reason_codes == ("PARENT_ACCESS_FLAGS_INVALID",)

    price.loc[0, "trade_recommendation"] = True
    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)
    assert error.value.reason_codes == ("PARENT_ACCESS_FLAGS_INVALID",)


def test_duplicate_and_unknown_parent_states_fail_closed() -> None:
    ff, price = _parents(["PERSISTENT_ACCUMULATION"], ["UPTREND"], ["NO_BREAKOUT"])
    ff = pd.concat([ff, ff], ignore_index=True)
    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)
    assert error.value.reason_codes == ("PARENT_DUPLICATE_KEY",)

    ff, price = _parents(["NOT_A_SETUP"], ["UPTREND"], ["NO_BREAKOUT"])
    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)
    assert error.value.reason_codes == ("PARENT_STATE_INVALID",)


def test_outcome_like_payload_and_invalid_hash_are_rejected() -> None:
    ff, price = _parents(["PERSISTENT_ACCUMULATION"], ["UPTREND"], ["NO_BREAKOUT"])
    ff["binary_target"] = 0
    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)
    assert error.value.reason_codes == ("PARENT_PAYLOAD_NOT_OUTCOME_BLIND",)

    ff, price = _parents(["PERSISTENT_ACCUMULATION"], ["UPTREND"], ["NO_BREAKOUT"])
    bad_ff = ParentProvenance(
        artifact_sha256="not-a-sha",
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
    )
    _, price_provenance = _provenance()
    with pytest.raises(JointStateContractError) as error:
        build_joint_setup_readiness_state(
            ff,
            price,
            official_sessions=SESSIONS,
            foreign_flow_provenance=bad_ff,
            price_state_provenance=price_provenance,
        )
    assert error.value.reason_codes == ("PROVENANCE_HASH_INVALID",)


@pytest.mark.parametrize("bad_ticker", [None, "BBCA.JK", "bbca"])
def test_noncanonical_ticker_identity_is_rejected_without_normalization(bad_ticker: object) -> None:
    ff, price = _parents(["PERSISTENT_ACCUMULATION"], ["UPTREND"], ["NO_BREAKOUT"])
    ff.loc[0, "ticker"] = bad_ticker
    with pytest.raises(JointStateContractError) as error:
        _build(ff, price)
    assert error.value.reason_codes == ("TICKER_IDENTITY_INVALID",)


def test_provenance_fields_are_explicit_and_optional_flags_are_fail_closed() -> None:
    ff, price = _parents(["PERSISTENT_ACCUMULATION"], ["UPTREND"], ["NO_BREAKOUT"])
    ff_provenance, price_provenance = _provenance()
    mapping = {
        "artifact_sha256": ff_provenance.artifact_sha256,
        "manifest_sha256": ff_provenance.manifest_sha256,
        "contract_version": ff_provenance.contract_version,
        "source_kind": ff_provenance.source_kind,
        "outcome_blind": True,
        "provider_calls": 0,
        "model_fitted": False,
        "model_scoring": False,
        "trade_recommendation": False,
    }
    del mapping["provider_calls"]
    with pytest.raises(JointStateContractError) as error:
        build_joint_setup_readiness_state(
            ff,
            price,
            official_sessions=SESSIONS,
            foreign_flow_provenance=mapping,
            price_state_provenance=price_provenance,
        )
    assert error.value.reason_codes == ("PROVENANCE_INCOMPLETE",)

    mapping["provider_calls"] = 0
    mapping["forward_outcomes_accessed"] = True
    with pytest.raises(JointStateContractError) as error:
        build_joint_setup_readiness_state(
            ff,
            price,
            official_sessions=SESSIONS,
            foreign_flow_provenance=mapping,
            price_state_provenance=price_provenance,
        )
    assert error.value.reason_codes == ("PARENT_ACCESS_FLAGS_INVALID",)


def test_contract_fingerprint_is_stable() -> None:
    assert len(joint_contract_fingerprint()) == 64
    assert joint_contract_fingerprint() == "a79e37cacf9ec428e27b4b398a757b9415e6e358b11b0d10edaf78a50c3d3599"
    assert JOINT_RULE_MATRIX[0] == ("INVALID_OR_MISSING_PARENT", "FAIL_CLOSED_NO_OUTPUT")
    assert OUTPUT_SCHEMA[-4:] == (
        "outcome_blind",
        "model_fitted",
        "model_scoring",
        "trade_recommendation",
    )
