"""Outcome-blind joint setup-readiness state contract.

This module combines the accepted Foreign Flow Setup State V1 and Price / Trend
Confirmation State V1 parents for descriptive context only.  It deliberately
does not write runtime artifacts, call providers, inspect outcomes, or emit a
trade recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import re
from typing import Iterable, Mapping

import pandas as pd

from .foreign_flow_setup_state import SetupLabel
from .price_trend_state import STATE_CONTRACT_VERSION as PRICE_STATE_CONTRACT_VERSION


JOINT_STATE_CONTRACT_VERSION = "JOINT_SETUP_READINESS_STATE_V1"
FOREIGN_FLOW_STATE_CONTRACT_VERSION = "FOREIGN_FLOW_SETUP_STATE_V1"
# Parent SHA fields are declared identities here.  A future runtime adapter
# owns the actual artifact/manifest byte verification.


class JointReadinessState(StrEnum):
    IGNORE = "IGNORE"
    WATCH = "WATCH"
    READY = "READY"
    ENTRY_ELIGIBLE = "ENTRY_ELIGIBLE"


class JointStateContractError(ValueError):
    """Fail-closed parent compatibility error with deterministic reason codes."""

    def __init__(self, message: str, reason_codes: Iterable[str] = ()) -> None:
        self.reason_codes = tuple(dict.fromkeys(str(code) for code in reason_codes))
        suffix = f" [{', '.join(self.reason_codes)}]" if self.reason_codes else ""
        super().__init__(message + suffix)


@dataclass(frozen=True)
class ParentProvenance:
    artifact_sha256: str
    manifest_sha256: str
    contract_version: str
    source_kind: str
    outcome_blind: bool
    provider_calls: int
    model_fitted: bool
    model_scoring: bool
    trade_recommendation: bool
    forward_outcomes_accessed: bool | None
    outcomes_or_labels_accessed: bool | None


def _provenance(value: ParentProvenance | Mapping[str, object], *, label: str) -> ParentProvenance:
    if isinstance(value, ParentProvenance):
        result = value
    elif isinstance(value, Mapping):
        required_fields = (
            "artifact_sha256",
            "manifest_sha256",
            "contract_version",
            "source_kind",
            "outcome_blind",
            "provider_calls",
            "model_fitted",
            "model_scoring",
            "trade_recommendation",
        )
        missing_fields = [field for field in required_fields if field not in value]
        if missing_fields:
            raise JointStateContractError(
                f"{label} provenance is missing explicit fields: {missing_fields}",
                ("PROVENANCE_INCOMPLETE",),
            )
        try:
            result = ParentProvenance(
                artifact_sha256=str(value["artifact_sha256"]),
                manifest_sha256=str(value["manifest_sha256"]),
                contract_version=str(value["contract_version"]),
                source_kind=str(value["source_kind"]),
                outcome_blind=value["outcome_blind"],
                provider_calls=value["provider_calls"],
                model_fitted=value["model_fitted"],
                model_scoring=value["model_scoring"],
                trade_recommendation=value["trade_recommendation"],
                forward_outcomes_accessed=value.get("forward_outcomes_accessed"),
                outcomes_or_labels_accessed=value.get("outcomes_or_labels_accessed"),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise JointStateContractError(
                f"{label} provenance is incomplete",
                ("PROVENANCE_INCOMPLETE",),
            ) from error
    else:
        raise JointStateContractError(
            f"{label} provenance must be a mapping or ParentProvenance",
            ("PROVENANCE_INCOMPLETE",),
        )

    sha_pattern = re.compile(r"^[0-9a-fA-F]{64}$")
    if not sha_pattern.fullmatch(result.artifact_sha256) or not sha_pattern.fullmatch(
        result.manifest_sha256
    ):
        raise JointStateContractError(
            f"{label} provenance has invalid SHA-256 identity",
            ("PROVENANCE_HASH_INVALID",),
        )
    if not result.contract_version or not result.source_kind:
        raise JointStateContractError(
            f"{label} provenance has empty contract/source identity",
            ("PROVENANCE_INCOMPLETE",),
        )
    boolean_fields = (
        "outcome_blind",
        "model_fitted",
        "model_scoring",
        "trade_recommendation",
    )
    for field in boolean_fields:
        if not isinstance(getattr(result, field), bool):
            raise JointStateContractError(
                f"{label} provenance field {field} is not boolean",
                ("PROVENANCE_FIELD_INVALID",),
            )
    if not isinstance(result.provider_calls, int) or isinstance(result.provider_calls, bool):
        raise JointStateContractError(
            f"{label} provenance provider_calls is not an integer",
            ("PROVENANCE_FIELD_INVALID",),
        )
    for field in ("forward_outcomes_accessed", "outcomes_or_labels_accessed"):
        value = getattr(result, field)
        if value is not None and not isinstance(value, bool):
            raise JointStateContractError(
                f"{label} provenance field {field} is not boolean",
                ("PROVENANCE_FIELD_INVALID",),
            )
    if (
        result.outcome_blind is not True
        or result.forward_outcomes_accessed is not None
        and result.forward_outcomes_accessed is not False
        or result.outcomes_or_labels_accessed is not None
        and result.outcomes_or_labels_accessed is not False
        or result.provider_calls != 0
        or result.model_fitted is not False
        or result.model_scoring is not False
        or result.trade_recommendation is not False
    ):
        raise JointStateContractError(
            f"{label} provenance is not outcome-blind and descriptive-only",
            ("PARENT_ACCESS_FLAGS_INVALID",),
        )
    return result


def _date(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise JointStateContractError("invalid session date", ("SESSION_DATE_INVALID",))
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


def _calendar(values: Iterable[object]) -> pd.DatetimeIndex:
    try:
        sessions = pd.DatetimeIndex([_date(value) for value in values]).sort_values()
    except TypeError as error:
        raise JointStateContractError(
            "official session calendar is not iterable",
            ("CALENDAR_INVALID",),
        ) from error
    if len(sessions) < 2 or sessions.has_duplicates:
        raise JointStateContractError(
            "official session calendar must contain at least two unique sessions",
            ("CALENDAR_INVALID",),
        )
    return sessions


def _reject_outcome_payload(frame: pd.DataFrame, *, label: str) -> None:
    allowed_flags = {
        "outcome_blind",
        "forward_outcomes_accessed",
        "outcomes_or_labels_accessed",
        "model_fitted",
        "model_scoring",
        "trade_recommendation",
    }
    forbidden_tokens = (
        "binary_target",
        "label_status",
        "tp_first",
        "sl_first",
        "realized",
        "forward_return",
        "future_return",
        "target_return",
        "prediction",
        "score",
    )
    forbidden = [
        str(column)
        for column in frame.columns
        if str(column) not in allowed_flags
        and any(token in str(column).lower() for token in forbidden_tokens)
    ]
    if forbidden:
        raise JointStateContractError(
            f"{label} input contains outcome/model payload columns: {sorted(forbidden)}",
            ("PARENT_PAYLOAD_NOT_OUTCOME_BLIND",),
        )


def _canonical_ticker(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise JointStateContractError(
            f"{label} parent ticker is null or not a string",
            ("TICKER_IDENTITY_INVALID",),
        )
    if value != value.strip() or value != value.upper() or value.endswith(".JK"):
        raise JointStateContractError(
            f"{label} parent ticker is not canonical: {value!r}",
            ("TICKER_IDENTITY_INVALID",),
        )
    if not re.fullmatch(r"[A-Z0-9]+", value):
        raise JointStateContractError(
            f"{label} parent ticker is not canonical: {value!r}",
            ("TICKER_IDENTITY_INVALID",),
        )
    return value


def _normalise_key_frame(
    frame: pd.DataFrame,
    *,
    label: str,
    required: tuple[str, ...],
    source_column: str,
) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise JointStateContractError(
            f"{label} parent is empty or not a DataFrame",
            ("PARENT_MISSING",),
        )
    _reject_outcome_payload(frame, label=label)
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise JointStateContractError(
            f"{label} parent is missing required columns: {missing}",
            ("PARENT_SCHEMA_INVALID",),
        )
    data = frame.copy()
    data["ticker"] = [_canonical_ticker(value, label=label) for value in data["ticker"]]
    for column in ("feature_session", source_column):
        try:
            data[column] = data[column].map(_date)
        except JointStateContractError as error:
            raise JointStateContractError(
                f"{label} parent has invalid {column}",
                ("PARENT_KEY_INVALID",),
            ) from error
    key_columns = ["ticker", "feature_session"]
    if data.duplicated(key_columns).any():
        raise JointStateContractError(
            f"{label} parent has duplicate ticker/feature-session keys",
            ("PARENT_DUPLICATE_KEY",),
        )
    return data.reset_index(drop=True)


def _check_flag_columns(frame: pd.DataFrame, *, label: str) -> None:
    expected = {
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "outcomes_or_labels_accessed": False,
        "model_fitted": False,
        "model_scoring": False,
        "trade_recommendation": False,
    }
    for column, expected_value in expected.items():
        if column in frame.columns and not all(
            isinstance(value, bool) and value is expected_value
            for value in frame[column].tolist()
        ):
            raise JointStateContractError(
                f"{label} parent has invalid {column} flag",
                ("PARENT_ACCESS_FLAGS_INVALID",),
            )


_ALLOWED_FLOW_LABELS = {value.value for value in SetupLabel}
_ALLOWED_TREND_STATES = {
    "UPTREND",
    "DOWNTREND",
    "BASING",
    "EARLY_REVERSAL",
    "TRANSITION",
    "INDETERMINATE",
}
_ALLOWED_CONFIRMATION_STATES = {
    "BREAKOUT_CONFIRMED",
    "BREAKOUT_WEAK_VOLUME",
    "FAILED_BREAKOUT_RECENT",
    "NEAR_BREAKOUT",
    "NO_BREAKOUT",
    "INDETERMINATE",
}

# Frozen descriptive semantics.  These tuples are part of the contract
# fingerprint and are also the definitions consumed by the classifier below.
HARD_BLOCKER_FLOW_LABELS = ("DISTRIBUTION_PRESSURE",)
HARD_BLOCKER_TREND_STATES = ("DOWNTREND",)
HARD_BLOCKER_CONFIRMATION_STATES = ("FAILED_BREAKOUT_RECENT",)
SUPPORTIVE_FLOW_LABELS = (
    "ABNORMAL_ACCUMULATION",
    "PERSISTENT_ACCUMULATION",
    "STEALTH_ACCUMULATION_CANDIDATE",
)
STRONG_FLOW_LABELS = (
    "PERSISTENT_ACCUMULATION",
    "STEALTH_ACCUMULATION_CANDIDATE",
)
READY_TREND_STATES = ("BASING", "EARLY_REVERSAL", "UPTREND")
ENTRY_TREND_STATES = ("EARLY_REVERSAL", "UPTREND")
EARLY_CONFIRMATION_STATES = ("BREAKOUT_WEAK_VOLUME", "NEAR_BREAKOUT")
ENTRY_CONFIRMATION_STATES = ("BREAKOUT_CONFIRMED",)


def _validate_parent_rows(
    foreign_flow: pd.DataFrame,
    price_state: pd.DataFrame,
    *,
    official_sessions: pd.DatetimeIndex,
    foreign_provenance: ParentProvenance,
    price_provenance: ParentProvenance,
) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    ff = _normalise_key_frame(
        foreign_flow,
        label="Foreign Flow",
        required=("ticker", "feature_session", "flow_through_session", "setup_label", "state_contract_version"),
        source_column="flow_through_session",
    )
    price = _normalise_key_frame(
        price_state,
        label="Price State",
        required=("ticker", "feature_session", "source_session", "trend_state", "confirmation_state", "state_contract_version"),
        source_column="source_session",
    )
    _check_flag_columns(ff, label="Foreign Flow")
    _check_flag_columns(price, label="Price State")
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
    if not ff["setup_label"].astype(str).isin(_ALLOWED_FLOW_LABELS).all():
        raise JointStateContractError(
            "Foreign Flow contains an unknown setup label",
            ("PARENT_STATE_INVALID",),
        )
    if not price["trend_state"].astype(str).isin(_ALLOWED_TREND_STATES).all():
        raise JointStateContractError(
            "Price State contains an unknown trend state",
            ("PARENT_STATE_INVALID",),
        )
    if not price["confirmation_state"].astype(str).isin(_ALLOWED_CONFIRMATION_STATES).all():
        raise JointStateContractError(
            "Price State contains an unknown confirmation state",
            ("PARENT_STATE_INVALID",),
        )

    official = set(official_sessions)
    if not ff["flow_through_session"].isin(official).all() or not ff["feature_session"].isin(official).all():
        raise JointStateContractError(
            "Foreign Flow parent contains a session outside the official calendar",
            ("SESSION_NOT_OFFICIAL",),
        )
    if not price["source_session"].isin(official).all() or not price["feature_session"].isin(official).all():
        raise JointStateContractError(
            "Price State parent contains a session outside the official calendar",
            ("SESSION_NOT_OFFICIAL",),
        )

    ff_keys = set(zip(ff["ticker"], ff["feature_session"]))
    price_keys = set(zip(price["ticker"], price["feature_session"]))
    if ff_keys != price_keys:
        raise JointStateContractError(
            "Foreign Flow and Price State parent key sets do not match",
            ("PARENT_KEY_SET_MISMATCH",),
        )
    if not ff["flow_through_session"].equals(price["source_session"]):
        merged = ff[["ticker", "feature_session", "flow_through_session"]].merge(
            price[["ticker", "feature_session", "source_session"]],
            on=["ticker", "feature_session"],
            how="inner",
            validate="one_to_one",
        )
        if not merged["flow_through_session"].eq(merged["source_session"]).all():
            raise JointStateContractError(
                "Foreign Flow source and Price State source sessions do not match",
                ("SOURCE_SESSION_MISMATCH",),
            )
    next_session = {
        official_sessions[index]: official_sessions[index + 1]
        for index in range(len(official_sessions) - 1)
    }
    expected = ff["flow_through_session"].map(next_session)
    if expected.isna().any() or not expected.equals(ff["feature_session"]):
        raise JointStateContractError(
            "parent source-to-feature session is not the next official session",
            ("CAUSAL_SESSION_MISMATCH",),
        )
    return ff, price


def _classify(flow_label: str, trend_state: str, confirmation_state: str) -> tuple[JointReadinessState, tuple[str, ...]]:
    reasons = ["PARENTS_VALID", "CAUSAL_SESSION_ALIGNED"]
    if flow_label == "INDETERMINATE":
        return JointReadinessState.IGNORE, tuple(reasons + ["FOREIGN_FLOW_STATE_INDETERMINATE"])
    if trend_state == "INDETERMINATE" or confirmation_state == "INDETERMINATE":
        return JointReadinessState.IGNORE, tuple(reasons + ["PRICE_STATE_INDETERMINATE"])
    if flow_label in HARD_BLOCKER_FLOW_LABELS:
        return JointReadinessState.IGNORE, tuple(reasons + ["FOREIGN_FLOW_DISTRIBUTION_PRESSURE"])
    if trend_state in HARD_BLOCKER_TREND_STATES:
        return JointReadinessState.IGNORE, tuple(reasons + ["PRICE_DOWNTREND"])
    if confirmation_state in HARD_BLOCKER_CONFIRMATION_STATES:
        return JointReadinessState.IGNORE, tuple(reasons + ["PRICE_FAILED_BREAKOUT_RECENT"])

    flow_supportive = flow_label in SUPPORTIVE_FLOW_LABELS
    flow_strong = flow_label in STRONG_FLOW_LABELS
    ready_trend = trend_state in READY_TREND_STATES
    entry_trend = trend_state in ENTRY_TREND_STATES
    breakout_confirmed = confirmation_state in ENTRY_CONFIRMATION_STATES

    if flow_strong and entry_trend and breakout_confirmed:
        reasons.extend(["FLOW_STRONG_ACCUMULATION", "PRICE_SUPPORTIVE_TREND", "PRICE_BREAKOUT_CONFIRMED"])
        return JointReadinessState.ENTRY_ELIGIBLE, tuple(reasons)
    if flow_supportive and ready_trend:
        reasons.extend(["FLOW_ACCUMULATION_CONTEXT", "PRICE_SUPPORTIVE_TREND"])
        return JointReadinessState.READY, tuple(reasons)
    if flow_supportive:
        reasons.append("FLOW_ACCUMULATION_CONTEXT")
    if ready_trend:
        reasons.append("PRICE_SUPPORTIVE_TREND")
    if confirmation_state in EARLY_CONFIRMATION_STATES:
        reasons.append("PRICE_EARLY_CONFIRMATION")
    if len(reasons) > 2:
        return JointReadinessState.WATCH, tuple(reasons)
    return JointReadinessState.IGNORE, tuple(reasons + ["NO_ALIGNED_SUPPORT"])


OUTPUT_SCHEMA = (
    "ticker",
    "feature_session",
    "flow_through_session",
    "source_session",
    "joint_state",
    "reason_codes",
    "foreign_flow_setup_label",
    "price_trend_state",
    "price_confirmation_state",
    "foreign_flow_state_contract_version",
    "price_state_contract_version",
    "joint_state_contract_version",
    "foreign_flow_artifact_sha256",
    "foreign_flow_manifest_sha256",
    "foreign_flow_source_kind",
    "price_state_artifact_sha256",
    "price_state_manifest_sha256",
    "price_state_source_kind",
    "outcome_blind",
    "model_fitted",
    "model_scoring",
    "trade_recommendation",
)
OUTPUT_COLUMNS = OUTPUT_SCHEMA


# Frozen descriptive matrix.  The implementation is intentionally explicit so
# future runtime wiring cannot silently turn this state layer into a signal.
JOINT_RULE_MATRIX = (
    ("INVALID_OR_MISSING_PARENT", "FAIL_CLOSED_NO_OUTPUT"),
    ("FOREIGN_FLOW_STATE_INDETERMINATE", "IGNORE"),
    ("PRICE_STATE_INDETERMINATE", "IGNORE"),
    ("FOREIGN_FLOW_DISTRIBUTION_PRESSURE", "IGNORE"),
    ("PRICE_DOWNTREND", "IGNORE"),
    ("PRICE_FAILED_BREAKOUT_RECENT", "IGNORE"),
    ("STRONG_FLOW_AND_SUPPORTIVE_TREND_AND_CONFIRMED_BREAKOUT", "ENTRY_ELIGIBLE"),
    ("SUPPORTIVE_FLOW_AND_SUPPORTIVE_TREND", "READY"),
    ("ONE_SUPPORTIVE_CONTEXT_OR_EARLY_CONFIRMATION", "WATCH"),
    ("NO_ALIGNED_SUPPORT", "IGNORE"),
)


def build_joint_setup_readiness_state(
    foreign_flow: pd.DataFrame,
    price_state: pd.DataFrame,
    *,
    official_sessions: Iterable[object],
    foreign_flow_provenance: ParentProvenance | Mapping[str, object],
    price_state_provenance: ParentProvenance | Mapping[str, object],
) -> pd.DataFrame:
    """Strictly join accepted parent states and classify descriptive readiness.

    Missing or incompatible parents raise ``JointStateContractError`` rather
    than producing a partially joined row.  Valid parent rows can still be
    classified as ``IGNORE``; ``ENTRY_ELIGIBLE`` is context-only and never a
    recommendation.
    """

    official = _calendar(official_sessions)
    ff_provenance = _provenance(foreign_flow_provenance, label="Foreign Flow")
    price_provenance = _provenance(price_state_provenance, label="Price State")
    ff, price = _validate_parent_rows(
        foreign_flow,
        price_state,
        official_sessions=official,
        foreign_provenance=ff_provenance,
        price_provenance=price_provenance,
    )
    merged = ff.merge(
        price,
        on=["ticker", "feature_session"],
        how="inner",
        suffixes=("_foreign_flow", "_price_state"),
        validate="one_to_one",
    )
    records: list[dict[str, object]] = []
    for row in merged.to_dict(orient="records"):
        state, reasons = _classify(
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
    if result.duplicated(["ticker", "feature_session"]).any():
        raise JointStateContractError(
            "joint output contains duplicate ticker/feature-session keys",
            ("JOINT_DUPLICATE_KEY",),
        )
    return result


def joint_contract_fingerprint() -> str:
    """Return a stable identity for the frozen matrix and contract version."""

    frozen_definition = (
        ("hard_blocker_flow_labels", HARD_BLOCKER_FLOW_LABELS),
        ("hard_blocker_trend_states", HARD_BLOCKER_TREND_STATES),
        ("hard_blocker_confirmation_states", HARD_BLOCKER_CONFIRMATION_STATES),
        ("supportive_flow_labels", SUPPORTIVE_FLOW_LABELS),
        ("strong_flow_labels", STRONG_FLOW_LABELS),
        ("ready_trend_states", READY_TREND_STATES),
        ("entry_trend_states", ENTRY_TREND_STATES),
        ("early_confirmation_states", EARLY_CONFIRMATION_STATES),
        ("entry_confirmation_states", ENTRY_CONFIRMATION_STATES),
        ("output_schema", OUTPUT_SCHEMA),
        ("ordered_rule_matrix", JOINT_RULE_MATRIX),
    )
    payload = repr((JOINT_STATE_CONTRACT_VERSION, frozen_definition)).encode()
    return hashlib.sha256(payload).hexdigest()
