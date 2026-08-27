from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd


RESOLVED = "RESOLVED"
BOUNDED_UNRESOLVED = "BOUNDED_UNRESOLVED"
UNRESOLVED = "UNRESOLVED"
NOT_BASIS_CHANGING = "NOT_BASIS_CHANGING"
TRANSITION_STATES = {
    RESOLVED,
    BOUNDED_UNRESOLVED,
    UNRESOLVED,
    NOT_BASIS_CHANGING,
}

BASIS_SAFE = "BASIS_SAFE"
BASIS_UNSAFE = "BASIS_UNSAFE"
BASIS_UNKNOWN = "BASIS_UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"
BASIS_STATES = {BASIS_SAFE, BASIS_UNSAFE, BASIS_UNKNOWN, NOT_APPLICABLE}

STOCK_SPLIT = "STOCK_SPLIT"
REVERSE_SPLIT = "REVERSE_SPLIT"
STOCK_DIVIDEND = "STOCK_DIVIDEND"
BONUS_SHARES = "BONUS_SHARES"
RIGHTS_HMETD = "RIGHTS_HMETD"
MANDATORY_CONVERSION = "MANDATORY_CONVERSION"
VOLUNTARY_CONVERSION = "VOLUNTARY_CONVERSION"
CAPITAL_RESTRUCTURING = "CAPITAL_RESTRUCTURING"
CASH_DIVIDEND = "CASH_DIVIDEND"

STRUCTURAL_EVENT_FAMILIES = {
    STOCK_SPLIT,
    REVERSE_SPLIT,
    STOCK_DIVIDEND,
    BONUS_SHARES,
    RIGHTS_HMETD,
    MANDATORY_CONVERSION,
    VOLUNTARY_CONVERSION,
    CAPITAL_RESTRUCTURING,
}
SUPPORTED_EVENT_FAMILIES = STRUCTURAL_EVENT_FAMILIES | {CASH_DIVIDEND}

_REQUIRED_EVENT_COLUMNS = {
    "ticker",
    "event_family",
    "event_identity",
    "effective_transition_state",
    "source_ref",
    "evidence_id",
    "evidence_sha256",
}


@dataclass(frozen=True)
class FeatureDependency:
    """Exact observed-row dependency geometry for one direct source feature.

    Offsets are positions within one ticker's chronologically ordered admitted
    observations, matching pandas ``shift``/``rolling`` behavior in the frozen
    historical feature builder.  They are not assumed to be contiguous
    official-session offsets.
    """

    feature: str
    offsets: tuple[int, ...]
    basis_sensitive: bool = True

    def __post_init__(self) -> None:
        if not self.feature.strip():
            raise ValueError("feature dependency name must be non-empty")
        if not self.offsets:
            raise ValueError(f"feature dependency has no offsets: {self.feature}")
        if any(int(offset) > 0 for offset in self.offsets):
            raise ValueError(f"future dependency is not allowed: {self.feature}")
        if len(set(self.offsets)) != len(self.offsets):
            raise ValueError(f"duplicate dependency offset: {self.feature}")


# H/L/C-derived direct source features in the frozen V4 control representation.
# Volume/value features are intentionally not declared price-basis-sensitive in
# this incident module; their unit/economic comparability is a separate data
# contract and must not be inferred merely from an H/L/C basis event.
V4_PRICE_FEATURE_DEPENDENCIES: tuple[FeatureDependency, ...] = (
    FeatureDependency("close_return_5", (-5, 0)),
    FeatureDependency("close_return_20", (-20, 0)),
    # ATR14 ending at t contains 14 true-range values.  TR at t-13 uses the
    # previous close at t-14, so the full price dependency is t-14..t.
    FeatureDependency("atr14_over_close", tuple(range(-14, 1))),
    FeatureDependency("close_position_20", tuple(range(-19, 1))),
    FeatureDependency("distance_high_20_atr", tuple(range(-19, 1))),
    FeatureDependency("distance_low_20_atr", tuple(range(-19, 1))),
    FeatureDependency("distance_high_60_atr", tuple(range(-59, 1))),
    FeatureDependency("distance_low_60_atr", tuple(range(-59, 1))),
)


def _normalize_ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _normalize_date(series: pd.Series, *, label: str) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if values.isna().any():
        raise ValueError(f"{label} contains invalid date")
    return values


def _official_sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .tz_localize(None)
        .normalize()
    )
    if sessions.isna().any():
        raise ValueError("official_sessions contains invalid date")
    sessions = sessions.unique().sort_values()
    if not len(sessions):
        raise ValueError("official_sessions must not be empty")
    return sessions


def _strict_optional_date_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns]")
    raw = frame[column]
    parsed = pd.to_datetime(raw, errors="coerce").dt.tz_localize(None).dt.normalize()
    supplied = raw.notna() & raw.astype(str).str.strip().ne("")
    if (supplied & parsed.isna()).any():
        raise ValueError(f"{column} contains malformed non-empty date")
    return parsed


def prepare_basis_events(
    events: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Validate and normalize source-backed CA basis-transition evidence.

    The function is deliberately strict.  It never infers transition dates
    from record/listing dates or adjacent price jumps.
    """

    missing = _REQUIRED_EVENT_COLUMNS - set(events.columns)
    if missing:
        raise ValueError(f"basis event ledger missing columns: {sorted(missing)}")
    if events.empty:
        return events.copy()

    sessions = _official_sessions(official_sessions)
    session_set = set(pd.Timestamp(day) for day in sessions)
    out = events.copy()
    out["ticker"] = _normalize_ticker(out["ticker"])
    if out["ticker"].eq("").any():
        raise ValueError("basis event ticker must be non-empty")

    out["event_family"] = out["event_family"].astype(str).str.upper().str.strip()
    unsupported = sorted(set(out["event_family"]) - SUPPORTED_EVENT_FAMILIES)
    if unsupported:
        raise ValueError(f"unsupported basis event family: {unsupported}")

    out["event_identity"] = out["event_identity"].fillna("").astype(str).str.strip()
    if out["event_identity"].eq("").any():
        raise ValueError("basis event identity must be non-empty")
    if out.duplicated(["ticker", "event_identity"]).any():
        raise ValueError("basis event identity must be unique within ticker")

    out["effective_transition_state"] = (
        out["effective_transition_state"].astype(str).str.upper().str.strip()
    )
    invalid_states = sorted(set(out["effective_transition_state"]) - TRANSITION_STATES)
    if invalid_states:
        raise ValueError(f"unsupported transition state: {invalid_states}")

    for column in ("source_ref", "evidence_id", "evidence_sha256"):
        out[column] = out[column].fillna("").astype(str).str.strip()
        if out[column].eq("").any():
            raise ValueError(f"basis event missing provenance field: {column}")
    if (~out["evidence_sha256"].str.fullmatch(r"[0-9a-fA-F]{64}")).any():
        raise ValueError("basis event evidence_sha256 must be 64 hex characters")
    out["evidence_sha256"] = out["evidence_sha256"].str.lower()

    out["transition_session"] = _strict_optional_date_column(out, "transition_session")
    out["transition_lower_session"] = _strict_optional_date_column(
        out, "transition_lower_session"
    )
    out["transition_upper_session"] = _strict_optional_date_column(
        out, "transition_upper_session"
    )

    for row in out.itertuples(index=False):
        state = row.effective_transition_state
        family = row.event_family
        exact = row.transition_session
        lower = row.transition_lower_session
        upper = row.transition_upper_session

        if family == CASH_DIVIDEND and state != NOT_BASIS_CHANGING:
            raise ValueError("cash dividend cannot create a V1 price-basis reset")

        if state == RESOLVED:
            if pd.isna(exact):
                raise ValueError("resolved basis event requires transition_session")
            if pd.Timestamp(exact) not in session_set:
                raise ValueError("resolved transition_session is not an official session")
            if not pd.isna(lower) or not pd.isna(upper):
                raise ValueError("resolved basis event must not also carry uncertain bounds")
        elif state == BOUNDED_UNRESOLVED:
            if not pd.isna(exact):
                raise ValueError("bounded unresolved event cannot carry exact transition_session")
            if pd.isna(lower) or pd.isna(upper):
                raise ValueError("bounded unresolved event requires lower and upper sessions")
            if pd.Timestamp(lower) not in session_set or pd.Timestamp(upper) not in session_set:
                raise ValueError("bounded transition interval must use official sessions")
            if pd.Timestamp(lower) > pd.Timestamp(upper):
                raise ValueError("bounded transition lower session is after upper session")
        elif state == UNRESOLVED:
            if not pd.isna(exact) or not pd.isna(lower) or not pd.isna(upper):
                raise ValueError("unresolved event must not smuggle an inferred transition date")
        elif state == NOT_BASIS_CHANGING:
            if not pd.isna(exact) or not pd.isna(lower) or not pd.isna(upper):
                raise ValueError("non-basis-changing event must not create an epoch boundary")
            if family in STRUCTURAL_EVENT_FAMILIES:
                justification = str(getattr(row, "basis_change_justification", "") or "").strip()
                if not justification:
                    raise ValueError(
                        "structural NOT_BASIS_CHANGING event requires explicit justification"
                    )

    return out.sort_values(
        ["ticker", "event_identity"], kind="mergesort"
    ).reset_index(drop=True)


def prepare_identity_frame(
    identities: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    required = {"ticker", "date"}
    missing = required - set(identities.columns)
    if missing:
        raise ValueError(f"identity frame missing columns: {sorted(missing)}")
    sessions = _official_sessions(official_sessions)
    session_index = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}

    out = identities[["ticker", "date"]].copy()
    out["ticker"] = _normalize_ticker(out["ticker"])
    out["date"] = _normalize_date(out["date"], label="identity frame")
    if out["ticker"].eq("").any():
        raise ValueError("identity frame contains empty ticker")
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError("identity frame contains duplicate ticker/date")
    out["session_index"] = out["date"].map(session_index)
    if out["session_index"].isna().any():
        raise ValueError("identity frame contains non-official session")
    out["session_index"] = out["session_index"].astype(int)
    out = out.sort_values(["ticker", "session_index"], kind="mergesort").reset_index(drop=True)
    out["ticker_observation_index"] = out.groupby("ticker", sort=False).cumcount()
    return out


def _resolved_epoch_number(
    session_index: int,
    resolved_boundaries: Sequence[int],
) -> int:
    return int(sum(boundary <= session_index for boundary in resolved_boundaries))


def build_basis_epoch_ledger(
    identities: pd.DataFrame,
    events: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Assign deterministic epoch IDs from *resolved* structural transitions.

    Unresolved events are retained in the feature-admission calculation and do
    not receive an invented boundary here.
    """

    sessions = _official_sessions(official_sessions)
    session_index = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    rows = prepare_identity_frame(identities, sessions)
    ledger = prepare_basis_events(events, sessions)

    resolved: dict[str, list[int]] = {}
    for row in ledger.itertuples(index=False):
        if row.effective_transition_state != RESOLVED:
            continue
        resolved.setdefault(row.ticker, []).append(session_index[pd.Timestamp(row.transition_session)])
    for ticker in resolved:
        resolved[ticker] = sorted(set(resolved[ticker]))

    epoch_numbers: list[int] = []
    epoch_ids: list[str] = []
    for ticker, index in rows[["ticker", "session_index"]].itertuples(index=False):
        number = _resolved_epoch_number(int(index), resolved.get(str(ticker), ()))
        epoch_numbers.append(number)
        epoch_ids.append(f"{ticker}:E{number:04d}")
    rows["basis_epoch_number"] = epoch_numbers
    rows["basis_epoch_id"] = epoch_ids
    return rows


def _event_crossing_state(
    *,
    minimum_dependency_session: int,
    maximum_dependency_session: int,
    event_row: object,
    session_index: Mapping[pd.Timestamp, int],
) -> tuple[str, str] | None:
    state = str(getattr(event_row, "effective_transition_state"))
    identity = str(getattr(event_row, "event_identity"))
    if state == NOT_BASIS_CHANGING:
        return None
    if state == UNRESOLVED:
        return BASIS_UNKNOWN, f"UNBOUNDED_TRANSITION:{identity}"
    if state == RESOLVED:
        boundary = session_index[pd.Timestamp(getattr(event_row, "transition_session"))]
        if minimum_dependency_session < boundary <= maximum_dependency_session:
            return BASIS_UNSAFE, f"CROSSES_RESOLVED_TRANSITION:{identity}"
        return None
    if state == BOUNDED_UNRESOLVED:
        lower = session_index[pd.Timestamp(getattr(event_row, "transition_lower_session"))]
        upper = session_index[pd.Timestamp(getattr(event_row, "transition_upper_session"))]
        # A crossing is possible when at least one allowed transition q lies in
        # (minimum_dependency_session, maximum_dependency_session].
        possible_lower = max(lower, minimum_dependency_session + 1)
        possible_upper = min(upper, maximum_dependency_session)
        if possible_lower <= possible_upper:
            return BASIS_UNKNOWN, f"COULD_CROSS_BOUNDED_TRANSITION:{identity}"
        return None
    raise ValueError(f"unexpected transition state: {state}")


def evaluate_feature_basis_admission(
    identities: pd.DataFrame,
    events: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    dependencies: Sequence[FeatureDependency] = V4_PRICE_FEATURE_DEPENDENCIES,
) -> pd.DataFrame:
    """Evaluate direct feature basis safety without loading values or outcomes."""

    sessions = _official_sessions(official_sessions)
    session_index = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    identity = prepare_identity_frame(identities, sessions)
    ledger = prepare_basis_events(events, sessions)
    epochs = build_basis_epoch_ledger(identity[["ticker", "date"]], ledger, sessions)

    events_by_ticker = {
        ticker: list(group.itertuples(index=False))
        for ticker, group in ledger.groupby("ticker", sort=False)
    }
    epoch_lookup = {
        (row.ticker, int(row.ticker_observation_index)): str(row.basis_epoch_id)
        for row in epochs.itertuples(index=False)
    }

    result: list[dict[str, object]] = []
    for ticker, group in identity.groupby("ticker", sort=False):
        group = group.sort_values("ticker_observation_index", kind="mergesort")
        by_position = {
            int(row.ticker_observation_index): row
            for row in group.itertuples(index=False)
        }
        ticker_events = events_by_ticker.get(str(ticker), [])
        for current in group.itertuples(index=False):
            position = int(current.ticker_observation_index)
            for dependency in dependencies:
                dependency_positions = [position + int(offset) for offset in dependency.offsets]
                if any(pos not in by_position for pos in dependency_positions):
                    result.append(
                        {
                            "ticker": ticker,
                            "date": current.date,
                            "feature": dependency.feature,
                            "basis_integrity_state": NOT_APPLICABLE,
                            "reason": "INSUFFICIENT_FROZEN_DEPENDENCY_HISTORY",
                            "dependency_min_date": pd.NaT,
                            "dependency_max_date": pd.NaT,
                            "dependency_epoch_ids": "",
                        }
                    )
                    continue

                dependency_rows = [by_position[pos] for pos in dependency_positions]
                minimum_session = min(int(row.session_index) for row in dependency_rows)
                maximum_session = max(int(row.session_index) for row in dependency_rows)
                dependency_epoch_ids = sorted(
                    {
                        epoch_lookup[(str(ticker), int(row.ticker_observation_index))]
                        for row in dependency_rows
                    }
                )

                state = BASIS_SAFE
                reasons: list[str] = []
                if dependency.basis_sensitive:
                    for event_row in ticker_events:
                        crossing = _event_crossing_state(
                            minimum_dependency_session=minimum_session,
                            maximum_dependency_session=maximum_session,
                            event_row=event_row,
                            session_index=session_index,
                        )
                        if crossing is None:
                            continue
                        event_state, reason = crossing
                        reasons.append(reason)
                        if event_state == BASIS_UNSAFE:
                            state = BASIS_UNSAFE
                        elif state != BASIS_UNSAFE:
                            state = BASIS_UNKNOWN

                    if len(dependency_epoch_ids) > 1:
                        state = BASIS_UNSAFE
                        reasons.append("DEPENDENCIES_SPAN_RESOLVED_EPOCHS")

                result.append(
                    {
                        "ticker": ticker,
                        "date": current.date,
                        "feature": dependency.feature,
                        "basis_integrity_state": state,
                        "reason": "|".join(sorted(set(reasons))) if reasons else "SAME_RESOLVED_BASIS_EPOCH",
                        "dependency_min_date": min(row.date for row in dependency_rows),
                        "dependency_max_date": max(row.date for row in dependency_rows),
                        "dependency_epoch_ids": "|".join(dependency_epoch_ids),
                    }
                )

    out = pd.DataFrame(result)
    if out.empty:
        return pd.DataFrame(
            columns=[
                "ticker",
                "date",
                "feature",
                "basis_integrity_state",
                "reason",
                "dependency_min_date",
                "dependency_max_date",
                "dependency_epoch_ids",
            ]
        )
    return out.sort_values(["date", "ticker", "feature"], kind="mergesort").reset_index(drop=True)


def aggregate_model_row_basis_state(
    admission: pd.DataFrame,
    *,
    required_features: Sequence[str],
) -> pd.DataFrame:
    """Aggregate direct feature states into a fail-closed model-row state."""

    required_columns = {"ticker", "date", "feature", "basis_integrity_state"}
    missing = required_columns - set(admission.columns)
    if missing:
        raise ValueError(f"feature admission missing columns: {sorted(missing)}")
    required = tuple(dict.fromkeys(str(name) for name in required_features))
    if not required:
        raise ValueError("required_features must not be empty")

    subset = admission[admission["feature"].isin(required)].copy()
    expected = len(required)
    counts = subset.groupby(["ticker", "date"], sort=False)["feature"].nunique()
    if counts.empty or (counts != expected).any():
        raise ValueError("feature admission is incomplete for required model features")

    rows: list[dict[str, object]] = []
    for (ticker, date), group in subset.groupby(["ticker", "date"], sort=False):
        states = set(group["basis_integrity_state"].astype(str))
        unknown_states = states - BASIS_STATES
        if unknown_states:
            raise ValueError(f"unexpected basis integrity state: {sorted(unknown_states)}")
        if BASIS_UNKNOWN in states:
            state = BASIS_UNKNOWN
        elif BASIS_UNSAFE in states:
            state = BASIS_UNSAFE
        elif NOT_APPLICABLE in states:
            state = NOT_APPLICABLE
        else:
            state = BASIS_SAFE
        rows.append(
            {
                "ticker": ticker,
                "date": date,
                "model_row_basis_state": state,
                "basis_safe_feature_count": int((group["basis_integrity_state"] == BASIS_SAFE).sum()),
                "required_feature_count": expected,
            }
        )
    return pd.DataFrame(rows).sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def apply_direct_feature_basis_mask(
    frame: pd.DataFrame,
    admission: pd.DataFrame,
    *,
    features: Sequence[str],
) -> pd.DataFrame:
    """Mask direct unsafe/unknown feature values before downstream XS transforms.

    This helper does not recompute ranks/market context.  Its output is intended
    to be fed into the frozen downstream transform implementation so that stale
    pre-remediation cross-sectional columns cannot be reused.
    """

    required = {"ticker", "date", *features}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"feature frame missing columns: {sorted(missing)}")
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("feature frame contains duplicate ticker/date")

    out = frame.copy()
    out["ticker"] = _normalize_ticker(out["ticker"])
    out["date"] = _normalize_date(out["date"], label="feature frame")
    lookup = admission[["ticker", "date", "feature", "basis_integrity_state"]].copy()
    if lookup.duplicated(["ticker", "date", "feature"]).any():
        raise ValueError("feature admission contains duplicate identities")

    for feature in features:
        state = lookup[lookup["feature"].eq(feature)][
            ["ticker", "date", "basis_integrity_state"]
        ].rename(columns={"basis_integrity_state": f"{feature}__basis_state"})
        out = out.merge(state, on=["ticker", "date"], how="left", validate="one_to_one")
        state_column = f"{feature}__basis_state"
        if out[state_column].isna().any():
            raise ValueError(f"missing basis admission for feature: {feature}")
        blocked = out[state_column].isin({BASIS_UNSAFE, BASIS_UNKNOWN, NOT_APPLICABLE})
        out.loc[blocked, feature] = np.nan

    return out
