"""V1.1 joint setup-readiness domain contract.

V1.1 preserves the accepted V1 parent formulas, thresholds, and classifier.
Its only change is applicability: the Price State key domain is authoritative,
while Foreign-Flow-only rows are explicitly excluded and retained in a
deterministic domain report.  This module is contract-only and does not write
runtime artifacts, call providers, inspect outcomes, or emit a trade signal.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable, Mapping

import pandas as pd

from . import joint_setup_readiness_state as v1


JOINT_STATE_CONTRACT_VERSION = "JOINT_SETUP_READINESS_STATE_V1_1"
FOREIGN_FLOW_STATE_CONTRACT_VERSION = v1.FOREIGN_FLOW_STATE_CONTRACT_VERSION
PRICE_STATE_CONTRACT_VERSION = v1.PRICE_STATE_CONTRACT_VERSION
OUTPUT_SCHEMA = v1.OUTPUT_SCHEMA
OUTPUT_COLUMNS = OUTPUT_SCHEMA


JointStateContractError = v1.JointStateContractError
ParentProvenance = v1.ParentProvenance


@dataclass(frozen=True)
class DomainCompatibilityReport:
    """Exact parent-domain reconciliation retained for runtime provenance."""

    foreign_flow_key_count: int
    price_state_key_count: int
    overlap_key_count: int
    price_only_key_count: int
    foreign_flow_only_key_count: int
    price_only_keys: tuple[tuple[str, str], ...]
    foreign_flow_only_keys: tuple[tuple[str, str], ...]

    @property
    def compatible(self) -> bool:
        return self.price_only_key_count == 0

    def as_dict(self) -> dict[str, object]:
        return {
            "foreign_flow_key_count": self.foreign_flow_key_count,
            "price_state_key_count": self.price_state_key_count,
            "overlap_key_count": self.overlap_key_count,
            "price_only_key_count": self.price_only_key_count,
            "foreign_flow_only_key_count": self.foreign_flow_only_key_count,
            "price_only_keys": [list(key) for key in self.price_only_keys],
            "foreign_flow_only_keys": [list(key) for key in self.foreign_flow_only_keys],
        }


@dataclass(frozen=True)
class JointSetupReadinessV1_1Result:
    """V1.1 classified Price-domain rows plus exact domain provenance."""

    frame: pd.DataFrame
    domain: DomainCompatibilityReport
    contract_fingerprint: str


def _key_token(key: tuple[object, object]) -> tuple[str, str]:
    ticker, session = key
    return str(ticker), pd.Timestamp(session).normalize().date().isoformat()


def _keys(frame: pd.DataFrame) -> set[tuple[object, object]]:
    return set(zip(frame["ticker"], frame["feature_session"]))


def _domain_report(
    foreign_flow: pd.DataFrame,
    price_state: pd.DataFrame,
) -> DomainCompatibilityReport:
    ff_keys = _keys(foreign_flow)
    price_keys = _keys(price_state)
    price_only = tuple(sorted(_key_token(key) for key in price_keys - ff_keys))
    foreign_flow_only = tuple(sorted(_key_token(key) for key in ff_keys - price_keys))
    return DomainCompatibilityReport(
        foreign_flow_key_count=len(ff_keys),
        price_state_key_count=len(price_keys),
        overlap_key_count=len(ff_keys & price_keys),
        price_only_key_count=len(price_only),
        foreign_flow_only_key_count=len(foreign_flow_only),
        price_only_keys=price_only,
        foreign_flow_only_keys=foreign_flow_only,
    )


def _validate_rows(
    foreign_flow: pd.DataFrame,
    price_state: pd.DataFrame,
    *,
    official_sessions: pd.DatetimeIndex,
    foreign_provenance: v1.ParentProvenance,
    price_provenance: v1.ParentProvenance,
) -> tuple[pd.DataFrame, pd.DataFrame, DomainCompatibilityReport]:
    if foreign_provenance.contract_version != FOREIGN_FLOW_STATE_CONTRACT_VERSION:
        raise JointStateContractError(
            "Foreign Flow parent contract version is not accepted",
            ("PROVENANCE_CONTRACT_MISMATCH",),
        )
    if price_provenance.contract_version != PRICE_STATE_CONTRACT_VERSION:
        raise JointStateContractError(
            "Price State parent contract version is not accepted",
            ("PROVENANCE_CONTRACT_MISMATCH",),
        )

    ff = v1._normalise_key_frame(
        foreign_flow,
        label="Foreign Flow",
        required=("ticker", "feature_session", "flow_through_session", "setup_label", "state_contract_version"),
        source_column="flow_through_session",
    )
    price = v1._normalise_key_frame(
        price_state,
        label="Price State",
        required=("ticker", "feature_session", "source_session", "trend_state", "confirmation_state", "state_contract_version"),
        source_column="source_session",
    )
    v1._check_flag_columns(ff, label="Foreign Flow")
    v1._check_flag_columns(price, label="Price State")
    if not ff["state_contract_version"].eq(FOREIGN_FLOW_STATE_CONTRACT_VERSION).all():
        raise JointStateContractError(
            "Foreign Flow row contract version is not accepted",
            ("PARENT_CONTRACT_VERSION_MISMATCH",),
        )
    if not price["state_contract_version"].eq(PRICE_STATE_CONTRACT_VERSION).all():
        raise JointStateContractError(
            "Price State row contract version is not accepted",
            ("PARENT_CONTRACT_VERSION_MISMATCH",),
        )
    if not ff["setup_label"].astype(str).isin(v1._ALLOWED_FLOW_LABELS).all():
        raise JointStateContractError("Foreign Flow contains an unknown setup label", ("PARENT_STATE_INVALID",))
    if not price["trend_state"].astype(str).isin(v1._ALLOWED_TREND_STATES).all():
        raise JointStateContractError("Price State contains an unknown trend state", ("PARENT_STATE_INVALID",))
    if not price["confirmation_state"].astype(str).isin(v1._ALLOWED_CONFIRMATION_STATES).all():
        raise JointStateContractError("Price State contains an unknown confirmation state", ("PARENT_STATE_INVALID",))

    official = set(official_sessions)
    if not ff["flow_through_session"].isin(official).all() or not ff["feature_session"].isin(official).all():
        raise JointStateContractError("Foreign Flow parent contains a session outside the official calendar", ("SESSION_NOT_OFFICIAL",))
    if not price["source_session"].isin(official).all() or not price["feature_session"].isin(official).all():
        raise JointStateContractError("Price State parent contains a session outside the official calendar", ("SESSION_NOT_OFFICIAL",))

    next_session = {
        official_sessions[index]: official_sessions[index + 1]
        for index in range(len(official_sessions) - 1)
    }
    expected = ff["flow_through_session"].map(next_session)
    if expected.isna().any() or not expected.equals(ff["feature_session"]):
        raise JointStateContractError(
            "Foreign Flow parent source-to-feature session is not the next official session",
            ("CAUSAL_SESSION_MISMATCH",),
        )

    domain = _domain_report(ff, price)
    if not domain.compatible:
        error = JointStateContractError(
            "Price State contains keys missing from Foreign Flow",
            ("PRICE_KEY_MISSING_IN_FOREIGN_FLOW", "PARENT_KEY_SET_MISMATCH"),
        )
        error.domain_report = domain  # type: ignore[attr-defined]
        raise error

    # Reuse the accepted V1 validation for the authoritative overlap only.
    # The full Foreign Flow frame has already had its own rows and causality
    # validated above, including the allowed Foreign-Flow-only rows.
    price_keys = _keys(price)
    common_ff = ff[ff.apply(lambda row: (row["ticker"], row["feature_session"]) in price_keys, axis=1)]
    common_ff, price = v1._validate_parent_rows(
        common_ff,
        price,
        official_sessions=official_sessions,
        foreign_provenance=foreign_provenance,
        price_provenance=price_provenance,
    )
    return ff, price, domain


def build_joint_setup_readiness_state_v1_1(
    foreign_flow: pd.DataFrame,
    price_state: pd.DataFrame,
    *,
    official_sessions: Iterable[object],
    foreign_flow_provenance: v1.ParentProvenance | Mapping[str, object],
    price_state_provenance: v1.ParentProvenance | Mapping[str, object],
) -> JointSetupReadinessV1_1Result:
    """Classify exactly the Price State domain under the frozen V1 mapping."""

    official = v1._calendar(official_sessions)
    ff_provenance = v1._provenance(foreign_flow_provenance, label="Foreign Flow")
    price_provenance = v1._provenance(price_state_provenance, label="Price State")
    ff, price, domain = _validate_rows(
        foreign_flow,
        price_state,
        official_sessions=official,
        foreign_provenance=ff_provenance,
        price_provenance=price_provenance,
    )
    merged = price.merge(
        ff,
        on=["ticker", "feature_session"],
        how="left",
        suffixes=("_price_state", "_foreign_flow"),
        validate="one_to_one",
        sort=False,
    )
    records: list[dict[str, object]] = []
    for row in merged.to_dict(orient="records"):
        state, reasons = v1._classify(
            str(row["setup_label"]),
            str(row["trend_state"]),
            str(row["confirmation_state"]),
        )
        records.append(
            {
                "ticker": row["ticker"],
                "feature_session": row["feature_session"],
                "flow_through_session": row["flow_through_session"],
                "source_session": row["source_session"],
                "joint_state": state.value,
                "reason_codes": "|".join(reasons),
                "foreign_flow_setup_label": row["setup_label"],
                "price_trend_state": row["trend_state"],
                "price_confirmation_state": row["confirmation_state"],
                "foreign_flow_state_contract_version": row["state_contract_version_foreign_flow"],
                "price_state_contract_version": row["state_contract_version_price_state"],
                "joint_state_contract_version": JOINT_STATE_CONTRACT_VERSION,
                "foreign_flow_artifact_sha256": ff_provenance.artifact_sha256,
                "foreign_flow_manifest_sha256": ff_provenance.manifest_sha256,
                "foreign_flow_source_kind": ff_provenance.source_kind,
                "price_state_artifact_sha256": price_provenance.artifact_sha256,
                "price_state_manifest_sha256": price_provenance.manifest_sha256,
                "price_state_source_kind": price_provenance.source_kind,
                "outcome_blind": True,
                "model_fitted": False,
                "model_scoring": False,
                "trade_recommendation": False,
            }
        )
    result = pd.DataFrame(records, columns=OUTPUT_COLUMNS)
    result = result.sort_values(["feature_session", "ticker"], kind="mergesort").reset_index(drop=True)
    if len(result) != domain.price_state_key_count or result.duplicated(["ticker", "feature_session"]).any():
        raise JointStateContractError("joint V1.1 output is not exactly the Price State domain", ("JOINT_DOMAIN_OUTPUT_INVALID",))
    return JointSetupReadinessV1_1Result(
        frame=result,
        domain=domain,
        contract_fingerprint=joint_contract_fingerprint_v1_1(),
    )


def joint_contract_fingerprint_v1_1() -> str:
    """Return the V1.1 identity without changing the accepted V1 fingerprint."""

    frozen_definition = (
        ("parent_v1_fingerprint", v1.joint_contract_fingerprint()),
        ("price_state_authoritative_domain", True),
        ("required_relation", "price_keys_subset_foreign_flow_keys"),
        ("foreign_flow_only_policy", "allowed_excluded_recorded"),
        ("join_validation", "price_left_join_after_subset_check"),
        ("output_schema", OUTPUT_SCHEMA),
    )
    payload = repr((JOINT_STATE_CONTRACT_VERSION, frozen_definition)).encode()
    return hashlib.sha256(payload).hexdigest()
