"""Outcome-blind R3 population and dependency-closure audit primitives.

These helpers intentionally operate on identities and frozen feature geometry
only.  They do not read prices, targets, labels, or model artifacts.  In
particular, an event's candidate date is retained as source evidence and is
never promoted to a transition date by this module.
"""

from __future__ import annotations

import hashlib
import re
from bisect import bisect_left, bisect_right
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from numbers import Integral

import pandas as pd
import numpy as np

from .ca_feature_basis_family_coverage_v1 import (
    combine_family_coverage,
)
from .ca_feature_basis_gate_v1 import CA_COVERAGE_CERTIFIED


R3_DEPENDENCY_OFFSETS: Mapping[str, tuple[int, ...]] = {
    "close_return_5": (-5, 0),
    "close_return_20": (-20, 0),
    "atr14": tuple(range(-14, 1)),
    "rolling20": tuple(range(-19, 1)),
    "rolling60": tuple(range(-59, 1)),
    "relative_volume_20": tuple(range(-19, 1)),
}


def _normalise_ticker(value: object) -> str:
    return str(value or "").strip().upper().replace(".JK", "")


def _normalise_date(value: object, *, label: str) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"{label}: invalid date {value!r}")
    return pd.Timestamp(parsed).date().isoformat()


def normalise_identity_frame(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    """Return deterministic ticker/date identities and reject duplicates."""

    required = {"ticker", "date"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing identity columns: {sorted(missing)}")
    out = frame[["ticker", "date"]].copy()
    out["ticker"] = out["ticker"].map(_normalise_ticker)
    if out["ticker"].eq("").any():
        raise ValueError(f"{label} contains an empty ticker")
    out["date"] = out["date"].map(lambda value: _normalise_date(value, label=label))
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError(f"{label} contains duplicate ticker/date")
    return out.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def _key_set(frame: pd.DataFrame, *, label: str) -> set[tuple[str, str]]:
    normalised = normalise_identity_frame(frame, label=label)
    return set(map(tuple, normalised[["ticker", "date"]].itertuples(index=False, name=None)))


def compare_identity_sets(
    old: Iterable[tuple[str, str]],
    current: Iterable[tuple[str, str]],
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compare two pinned identity sets without treating one as canonical."""

    old_set = {(_normalise_ticker(t), str(d)) for t, d in old}
    current_set = {(_normalise_ticker(t), str(d)) for t, d in current}
    rows = []
    for ticker, date in sorted(old_set | current_set, key=lambda item: (item[1], item[0])):
        in_old = (ticker, date) in old_set
        in_current = (ticker, date) in current_set
        rows.append(
            {
                "ticker": ticker,
                "date": date,
                "in_old": in_old,
                "in_current": in_current,
                "comparison": "COMMON" if in_old and in_current else ("OLD_ONLY" if in_old else "CURRENT_ONLY"),
            }
        )
    summary = {
        "old_rows": len(old_set),
        "current_rows": len(current_set),
        "common_rows": len(old_set & current_set),
        "old_only_rows": len(old_set - current_set),
        "current_only_rows": len(current_set - old_set),
        "equivalent": int(old_set == current_set),
    }
    return pd.DataFrame(rows, columns=["ticker", "date", "in_old", "in_current", "comparison"]), summary


def build_cross_section_population(
    features: pd.DataFrame,
    h5_keys: Iterable[tuple[str, str]],
    h10_keys: Iterable[tuple[str, str]],
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Enumerate every primary-liquid row on dates used by final-fit support."""

    required = {"ticker", "date", "universe_primary_liquid"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"feature table missing columns: {sorted(missing)}")
    identities = features[["ticker", "date", "universe_primary_liquid"]].copy()
    identities["ticker"] = identities["ticker"].map(_normalise_ticker)
    identities["date"] = identities["date"].map(lambda value: _normalise_date(value, label="feature table"))
    if identities.duplicated(["ticker", "date"]).any():
        raise ValueError("feature table contains duplicate ticker/date")
    h5 = {(_normalise_ticker(t), str(d)) for t, d in h5_keys}
    h10 = {(_normalise_ticker(t), str(d)) for t, d in h10_keys}
    fit_union = h5 | h10
    fit_dates = {date for _, date in fit_union}
    primary = identities.loc[identities["universe_primary_liquid"].astype(bool)].copy()
    application = primary.loc[primary["date"].isin(fit_dates)].copy()
    rows = []
    for row in application.sort_values(["date", "ticker"], kind="mergesort").itertuples(index=False):
        key = (row.ticker, row.date)
        in_h5 = key in h5
        in_h10 = key in h10
        rows.append(
            {
                "ticker": row.ticker,
                "date": row.date,
                "primary_liquid": True,
                "in_h5_fit": in_h5,
                "in_h10_fit": in_h10,
                "in_fit_union": in_h5 or in_h10,
                "population_role": "FINAL_FIT" if in_h5 or in_h10 else "CROSS_SECTION_ONLY",
            }
        )
    out = pd.DataFrame(
        rows,
        columns=["ticker", "date", "primary_liquid", "in_h5_fit", "in_h10_fit", "in_fit_union", "population_role"],
    )
    summary = {
        "fit_rows": len(fit_union),
        "fit_tickers": len({ticker for ticker, _ in fit_union}),
        "fit_dates": len(fit_dates),
        "application_rows": len(out),
        "application_tickers": out["ticker"].nunique() if not out.empty else 0,
        "application_dates": out["date"].nunique() if not out.empty else 0,
        "cross_section_only_rows": int((~out["in_fit_union"]).sum()) if not out.empty else 0,
        "cross_section_only_tickers": out.loc[~out["in_fit_union"], "ticker"].nunique() if not out.empty else 0,
    }
    return out, summary


def build_observed_dependency_closure(
    features: pd.DataFrame,
    application_keys: Iterable[tuple[str, str]],
    *,
    dependencies: Mapping[str, Sequence[int]] = R3_DEPENDENCY_OFFSETS,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Resolve frozen feature dependencies by observed-row position per ticker.

    A missing official day does not shift the position contract into a calendar
    day subtraction.  The caller supplies the complete admitted observation
    stream, and positions are assigned only within that stream.
    """

    identities = normalise_identity_frame(features, label="full observation stream")
    full_keys = set(map(tuple, identities.itertuples(index=False, name=None)))
    application = {(_normalise_ticker(t), str(d)) for t, d in application_keys}
    missing_application = application - full_keys
    if missing_application:
        raise ValueError(f"application identities outside observation stream: {len(missing_application)}")
    # Materialize each ticker stream once.  Repeated DataFrame filtering here
    # would scan the million-row panel once per ticker and make the audit
    # needlessly unbounded; the position semantics remain unchanged.
    streams: dict[str, list[tuple[str, str]]] = {}
    positions: dict[tuple[str, str], int] = {}
    for ticker, group in identities.groupby("ticker", sort=True):
        stream = [(str(ticker), str(date)) for date in group.sort_values("date", kind="mergesort")["date"]]
        streams[str(ticker)] = stream
        positions.update({key: position for position, key in enumerate(stream)})

    app_by_ticker: defaultdict[str, list[int]] = defaultdict(list)
    for ticker, date in application:
        key = (ticker, date)
        if key not in positions:
            raise ValueError(f"application identity not uniquely observed: {(ticker, date)}")
        app_by_ticker[ticker].append(positions[key])

    families_by_key: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    missing_offset_counts: dict[str, int] = {}
    missing_target_counts: dict[str, int] = {}
    for feature, offsets_value in dependencies.items():
        offsets = tuple(int(offset) for offset in offsets_value)
        if not offsets or any(offset > 0 for offset in offsets):
            raise ValueError(f"invalid dependency offsets for {feature}")
        missing_offsets = 0
        missing_targets = 0
        for ticker, target_indices in app_by_ticker.items():
            source_rows = streams[ticker]
            target_positions = np.asarray(target_indices, dtype=np.int64)
            source_mask = np.zeros(len(source_rows), dtype=bool)
            target_missing_mask = np.zeros(len(target_positions), dtype=bool)
            for offset in offsets:
                source_positions = target_positions + offset
                valid = (source_positions >= 0) & (source_positions < len(source_rows))
                missing_offsets += int((~valid).sum())
                target_missing_mask |= ~valid
                source_mask[source_positions[valid]] = True
            missing_targets += int(target_missing_mask.sum())
            for source_position in np.flatnonzero(source_mask):
                families_by_key[source_rows[int(source_position)]].add(str(feature))
        missing_offset_counts[str(feature)] = missing_offsets
        missing_target_counts[str(feature)] = missing_targets

    rows = []
    application_set = application
    for (ticker, date), families in sorted(families_by_key.items(), key=lambda item: (item[0][1], item[0][0])):
        position = positions[(ticker, date)]
        rows.append(
            {
                "ticker": ticker,
                "date": date,
                "source_observation_position": position,
                "dependency_families": ";".join(sorted(families)),
                "dependency_family_count": len(families),
                "is_cross_section_application": (ticker, date) in application_set,
            }
        )
    out = pd.DataFrame(rows, columns=["ticker", "date", "source_observation_position", "dependency_families", "dependency_family_count", "is_cross_section_application"])
    summary = {
        "application_rows": len(application),
        "closure_rows": len(out),
        "closure_tickers": out["ticker"].nunique() if not out.empty else 0,
        "closure_start": out["date"].min() if not out.empty else "",
        "closure_end": out["date"].max() if not out.empty else "",
        "family_rows": {feature: int(sum(feature in families for families in families_by_key.values())) for feature in dependencies},
        "missing_offset_counts": missing_offset_counts,
        "missing_target_counts": missing_target_counts,
    }
    return out, summary


def build_primary_membership_dependency_closure(
    features: pd.DataFrame,
    application_keys: Iterable[tuple[str, str]],
    official_sessions: Iterable[object],
    *,
    lookback_sessions: int = 60,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Resolve the frozen primary-liquidity membership window.

    The frozen builder uses official-session indices for its 60-session window
    and includes the current observation.  This is kept separate from the
    observed-row feature dependencies because a listed security can have
    missing observations inside an official-session window.
    """

    if lookback_sessions <= 0:
        raise ValueError("lookback_sessions must be positive")
    identities = normalise_identity_frame(features, label="full observation stream")
    full_keys = set(map(tuple, identities.itertuples(index=False, name=None)))
    application = {(_normalise_ticker(t), str(d)) for t, d in application_keys}
    if not application <= full_keys:
        raise ValueError("application identities outside observation stream")
    sessions = sorted({_normalise_date(value, label="official sessions") for value in official_sessions})
    if not sessions:
        raise ValueError("official_sessions must not be empty")
    session_index = {date: index for index, date in enumerate(sessions)}
    if not set(identities["date"]) <= set(session_index):
        raise ValueError("observation stream contains a non-official session")

    streams: dict[str, list[tuple[str, str, int]]] = {}
    positions: dict[tuple[str, str], int] = {}
    for ticker, group in identities.groupby("ticker", sort=True):
        stream = [
            (str(ticker), str(date), session_index[str(date)])
            for date in group.sort_values("date", kind="mergesort")["date"]
        ]
        streams[str(ticker)] = stream
        positions.update({(ticker, date): position for position, (_, date, _) in enumerate(stream)})

    by_ticker: defaultdict[str, list[int]] = defaultdict(list)
    for ticker, date in application:
        by_ticker[ticker].append(positions[(ticker, date)])
    rows: list[dict[str, object]] = []
    for ticker, target_positions in by_ticker.items():
        stream = streams[ticker]
        stream_sessions = [session for _, _, session in stream]
        for target_position in target_positions:
            current_session = stream_sessions[target_position]
            lower = current_session - (lookback_sessions - 1)
            left = bisect_left(stream_sessions, lower)
            right = bisect_right(stream_sessions, current_session)
            source_positions = range(left, right)
            for source_position in source_positions:
                source_ticker, source_date, _ = stream[source_position]
                rows.append(
                    {
                        "ticker": source_ticker,
                        "date": source_date,
                        "source_observation_position": source_position,
                        "dependency_families": "primary_liquidity_60",
                        "dependency_family_count": 1,
                        "is_cross_section_application": (source_ticker, source_date) in application,
                    }
                )
    out = pd.DataFrame(
        rows,
        columns=["ticker", "date", "source_observation_position", "dependency_families", "dependency_family_count", "is_cross_section_application"],
    ).drop_duplicates(["ticker", "date"], ignore_index=True)
    if not out.empty:
        out = out.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    summary = {
        "application_rows": len(application),
        "closure_rows": len(out),
        "closure_tickers": out["ticker"].nunique() if not out.empty else 0,
        "closure_start": out["date"].min() if not out.empty else "",
        "closure_end": out["date"].max() if not out.empty else "",
        "lookback_sessions": lookback_sessions,
    }
    return out, summary


def merge_dependency_closures(*frames: pd.DataFrame) -> pd.DataFrame:
    """Union direct and membership closure rows with deterministic flags."""

    nonempty = [frame.copy() for frame in frames if not frame.empty]
    if not nonempty:
        raise ValueError("at least one dependency closure is required")
    combined = pd.concat(nonempty, ignore_index=True, sort=False)
    required = {"ticker", "date", "source_observation_position", "dependency_families", "is_cross_section_application"}
    missing = required - set(combined.columns)
    if missing:
        raise ValueError(f"dependency closure missing columns: {sorted(missing)}")
    combined["dependency_families"] = combined["dependency_families"].astype(str)
    rows: list[dict[str, object]] = []
    for (ticker, date), group in combined.groupby(["ticker", "date"], sort=True):
        families = sorted({family for value in group["dependency_families"] for family in value.split(";") if family})
        rows.append(
            {
                "ticker": ticker,
                "date": date,
                "source_observation_position": int(group["source_observation_position"].min()),
                "dependency_families": ";".join(families),
                "dependency_family_count": len(families),
                "is_cross_section_application": bool(group["is_cross_section_application"].any()),
                "is_direct_dependency": bool(group["dependency_families"].str.contains("primary_liquidity_60", regex=False).eq(False).any()),
                "is_primary_membership_dependency": bool(group["dependency_families"].str.contains("primary_liquidity_60", regex=False).any()),
            }
        )
    return pd.DataFrame(rows).sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def _missing_ticker_sha(tickers: Iterable[str]) -> str:
    value = "\n".join(sorted(set(tickers))) + ("\n" if tickers else "")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _identity_set(values: Iterable[tuple[str, str]] | None, *, label: str) -> set[tuple[str, str]] | None:
    if values is None:
        return None
    result: set[tuple[str, str]] = set()
    for value in values:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
            raise ValueError(f"{label} must contain ticker/date pairs")
        ticker = _normalise_ticker(value[0])
        if not ticker:
            raise ValueError(f"{label} contains an empty ticker")
        result.add((ticker, _normalise_date(value[1], label=label)))
    return result


def _scope_values(values: int | Iterable[str], *, label: str) -> tuple[int, set[str] | None]:
    if isinstance(values, Integral) and not isinstance(values, bool):
        count = int(values)
        if count < 0:
            raise ValueError(f"{label} must not be negative")
        return count, None
    normalised = {_normalise_ticker(value) for value in values}
    if "" in normalised:
        raise ValueError(f"{label} contains an empty ticker")
    return len(normalised), normalised


def _strict_bool(value: object, *, label: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n", ""}:
        return False
    raise ValueError(f"{label}: expected a strict boolean, got {value!r}")


def _identity_sha(keys: Iterable[tuple[str, str]]) -> str:
    value = "\n".join(f"{ticker}|{date}" for ticker, date in sorted(set(keys)))
    return hashlib.sha256((value + ("\n" if value else "")).encode("utf-8")).hexdigest()


def reconcile_ksei_populations(
    populations: Mapping[str, Iterable[str]],
    ksei_rows: pd.DataFrame,
) -> pd.DataFrame:
    """Report ticker presence separately for fit, application, and closure."""

    required = {"ticker", "coverage_status"}
    missing = required - set(ksei_rows.columns)
    if missing:
        raise ValueError(f"KSEI coverage missing columns: {sorted(missing)}")
    normalised = ksei_rows.copy()
    normalised["ticker"] = normalised["ticker"].map(_normalise_ticker)
    if normalised["ticker"].eq("").any() or normalised.duplicated("ticker").any():
        raise ValueError("KSEI coverage must have one non-empty row per ticker")
    ksei_tickers = set(normalised["ticker"])
    rows = []
    for name, values in populations.items():
        population = {_normalise_ticker(value) for value in values}
        present = population & ksei_tickers
        missing_tickers = population - ksei_tickers
        statuses = normalised.set_index("ticker").loc[sorted(present), "coverage_status"] if present else pd.Series(dtype=object)
        rows.append(
            {
                "population_scope": name,
                "population_tickers": len(population),
                "ksei_present_tickers": len(present),
                "ksei_absent_tickers": len(missing_tickers),
                "ksei_certified_tickers": int((statuses == "COVERAGE_CERTIFIED").sum()),
                "ksei_unresolved_tickers": int((statuses == "COVERAGE_UNRESOLVED").sum()),
                "missing_ticker_sha256": _missing_ticker_sha(missing_tickers),
                "missing_tickers": ";".join(sorted(missing_tickers)),
                "date_level_attestation": False,
                "coverage_verdict": "UNKNOWN_TICKER_ONLY_NO_DATE_ATTESTATION",
            }
        )
    return pd.DataFrame(rows)


def classify_event_scope(
    events: pd.DataFrame,
    closure: pd.DataFrame,
) -> pd.DataFrame:
    """Classify source event evidence against closure without resolving dates."""

    required = {"ticker", "event_family", "candidate_date"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"event census missing columns: {sorted(missing)}")
    if closure.empty:
        raise ValueError("cannot scope events against an empty dependency closure")
    bounds = closure.groupby("ticker", sort=True)["date"].agg(["min", "max"])
    closure_dates = set(zip(closure["ticker"], closure["date"]))
    rows = []
    for index, source in events.reset_index(drop=True).iterrows():
        ticker = _normalise_ticker(source["ticker"])
        candidate = str(source.get("candidate_date", "") or "").strip()
        lower_bound_value = ""
        lower_bound_status = ""
        lower_bound_source_contract = ""
        lower_bound_certified = False
        if ticker not in bounds.index:
            classification = "OUTSIDE_DEPENDENCY_TICKER"
            reason = "event ticker is absent from observed dependency closure"
            candidate_in_closure = False
        elif not candidate:
            classification = "UNKNOWN_UNRESOLVED_EVENT_DATE"
            reason = "source event has no candidate date; transition is not inferred"
            candidate_in_closure = False
        else:
            try:
                candidate = _normalise_date(candidate, label=f"event[{index}].candidate_date")
            except ValueError:
                classification = "UNKNOWN_MALFORMED_EVENT_DATE"
                reason = "source candidate date is malformed; transition is not inferred"
                candidate_in_closure = False
            else:
                lower = str(bounds.loc[ticker, "min"])
                upper = str(bounds.loc[ticker, "max"])
                candidate_in_closure = (ticker, candidate) in closure_dates
                lower_bound_value = str(source.get("certified_transition_lower_bound", "") or "").strip()
                lower_bound_status = str(source.get("transition_lower_bound_status", "") or "").strip().upper()
                if lower_bound_value:
                    try:
                        lower_bound_value = _normalise_date(
                            lower_bound_value,
                            label=f"event[{index}].certified_transition_lower_bound",
                        )
                        explicit_certified = _strict_bool(
                            source.get("transition_lower_bound_certified", False),
                            label=f"event[{index}].transition_lower_bound_certified",
                        )
                    except ValueError:
                        lower_bound_value = ""
                        explicit_certified = False
                    lower_bound_source = str(
                        source.get("transition_lower_bound_source_ref", source.get("source_ref", "")) or ""
                    ).strip()
                    lower_bound_sha = str(
                        source.get("transition_lower_bound_source_sha256", source.get("source_sha256", "")) or ""
                    ).strip()
                    lower_bound_source_contract = str(
                        source.get(
                            "transition_lower_bound_source_contract_id",
                            source.get("source_contract_id", ""),
                        )
                        or ""
                    ).strip()
                    # A source-bound lower bound is not certified unless the
                    # evidence digest is present and exactly 64 hex chars.
                    # Empty evidence must remain unresolved, even when the
                    # source status and lower-bound date look authoritative.
                    lower_bound_sha_valid = bool(re.fullmatch(r"[0-9a-fA-F]{64}", lower_bound_sha))
                    lower_bound_certified = bool(
                        explicit_certified
                        and lower_bound_status in {"CERTIFIED", "SOURCE_CERTIFIED", "CERTIFIED_SOURCE_BOUND"}
                        and lower_bound_source
                        and lower_bound_sha_valid
                    )
                if lower_bound_certified and lower_bound_value > upper:
                    classification = "OUTSIDE_DEPENDENCY_AFTER_CLOSURE"
                    reason = "source-certified transition lower bound is after the observed backward dependency closure"
                elif candidate > upper:
                    classification = "UNKNOWN_UNRESOLVED_AFTER_CLOSURE"
                    reason = "candidate evidence is after closure, but it is not a certified transition lower bound"
                elif candidate < lower:
                    classification = "UNRESOLVED_CANDIDATE_BEFORE_CLOSURE"
                    reason = "pre-closure event may affect later basis; no transition date is inferred"
                else:
                    classification = "UNRESOLVED_CANDIDATE_IN_CLOSURE"
                    reason = "candidate date intersects closure but source semantics do not prove transition"
        row = {key: source.get(key, "") for key in events.columns}
        row.update(
            {
                "closure_scope_classification": classification,
                "candidate_date_in_closure": candidate_in_closure,
                "transition_semantics": "UNRESOLVED",
                "resolution_reason": reason,
            }
        )
        row["certified_transition_lower_bound"] = lower_bound_value
        row["transition_lower_bound_certified"] = bool(lower_bound_certified)
        row["transition_lower_bound_status"] = lower_bound_status
        row["transition_lower_bound_source_contract_id"] = lower_bound_source_contract
        rows.append(row)
    return pd.DataFrame(rows)


def validate_strict_event_census(
    events: pd.DataFrame,
    *,
    expected_rows: int,
    expected_family_counts: Mapping[str, int],
) -> None:
    """Reject an empty, partial, duplicate, or malformed strict event census."""

    required = {
        "source_kind",
        "ticker",
        "event_family",
        "candidate_date",
        "effective_date_status",
        "continuity_status",
        "source_action_id",
        "source_ref",
        "source_sha256",
        "published_at_utc",
        "evidence_id",
    }
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"strict event census missing columns: {sorted(missing)}")
    if len(events) != expected_rows:
        raise ValueError(f"strict event census row count mismatch: {len(events)} != {expected_rows}")
    action_id = events["source_action_id"].astype(str).str.strip()
    fallback_identity = (
        events["source_kind"].astype(str).str.strip()
        + "|"
        + events["ticker"].astype(str).str.strip().str.upper()
        + "|"
        + events["event_family"].astype(str).str.strip().str.upper()
        + "|"
        + events["candidate_date"].astype(str).str.strip()
        + "|"
        + events["source_ref"].astype(str).str.strip()
        + "|"
        + events["source_sha256"].astype(str).str.strip().str.lower()
        + "|"
        + events["published_at_utc"].astype(str).str.strip()
    )
    scoped_action_identity = (
        events["source_kind"].astype(str).str.strip()
        + "|"
        + events["ticker"].astype(str).str.strip().str.upper()
        + "|ACTION|"
        + action_id
    )
    identity = scoped_action_identity.where(action_id.ne(""), fallback_identity)
    if identity.duplicated().any():
        raise ValueError("strict event census contains duplicate source event identities")
    if (~events["source_sha256"].astype(str).str.fullmatch(r"[0-9a-fA-F]{64}")).any():
        raise ValueError("strict event census contains malformed evidence SHA")
    observed = {
        str(key): int(value)
        for key, value in events["event_family"].astype(str).value_counts().sort_index().items()
    }
    expected = {str(key): int(value) for key, value in expected_family_counts.items()}
    if observed != expected:
        raise ValueError(f"strict event census family counts mismatch: {observed} != {expected}")


def global_ca_population_gate(
    *,
    fit_tickers: int | Iterable[str],
    application_tickers: int | Iterable[str],
    closure_tickers: int | Iterable[str],
    ksei_scope: pd.DataFrame,
    structural_event_complete: bool,
    fit_identities: Iterable[tuple[str, str]] | None = None,
    application_identities: Iterable[tuple[str, str]] | None = None,
    closure_identities: Iterable[tuple[str, str]] | None = None,
    scope_evidence: pd.DataFrame | None = None,
    family_coverage: pd.DataFrame | None = None,
    official_sessions: Iterable[object] | None = None,
    temporal_attestation: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Fail-closed population gate using full identity-scope certification.

    Fit, application, and dependency-closure scopes intentionally have
    different cardinalities.  A count comparison would reject the valid
    expanded cross-sectional architecture and would not prove containment or
    date-level evidence.
    """

    fit_ticker_count, fit_ticker_set = _scope_values(fit_tickers, label="fit_tickers")
    application_ticker_count, application_ticker_set = _scope_values(application_tickers, label="application_tickers")
    closure_ticker_count, closure_ticker_set = _scope_values(closure_tickers, label="closure_tickers")
    fit_set = _identity_set(fit_identities, label="fit_identities")
    application_set = _identity_set(application_identities, label="application_identities")
    closure_set = _identity_set(closure_identities, label="closure_identities")
    diagnostics: dict[str, object] = {
        "fit_identity_scope_available": fit_set is not None,
        "application_identity_scope_available": application_set is not None,
        "closure_identity_scope_available": closure_set is not None,
        "fit_contained_in_application": False,
        "application_contained_in_closure": False,
        "missing_application_identity_count": 0,
        "missing_closure_identity_count": 0,
        "scope_evidence_rows": 0,
        "scope_evidence_missing_identity_count": 0,
        "scope_evidence_uncertified_source_count": 0,
        "scope_evidence_unattested_date_count": 0,
        "family_coverage_rows": 0,
        "family_certified_identity_count": 0,
        "temporal_attestation_rows": 0,
        "temporal_missing_identity_count": 0,
        "temporal_invalid_provenance_count": 0,
    }

    if not structural_event_complete:
        verdict = "FAIL_STRUCTURAL_CA_COVERAGE_NOT_CERTIFIED"
    elif "date_level_attestation" not in ksei_scope.columns or ksei_scope.empty:
        verdict = "FAIL_KSEI_DATE_LEVEL_ATTESTATION_MISSING"
    elif any(not _strict_bool(value, label="KSEI date_level_attestation") for value in ksei_scope["date_level_attestation"]):
        verdict = "FAIL_KSEI_DATE_LEVEL_ATTESTATION_MISSING"
    elif fit_set is None or application_set is None or closure_set is None:
        verdict = "FAIL_IDENTITY_SCOPE_ATTESTATION_MISSING"
    else:
        missing_application = fit_set - application_set
        missing_closure = application_set - closure_set
        diagnostics["fit_contained_in_application"] = not missing_application
        diagnostics["application_contained_in_closure"] = not missing_closure
        diagnostics["missing_application_identity_count"] = len(missing_application)
        diagnostics["missing_closure_identity_count"] = len(missing_closure)
        diagnostics["missing_application_identity_sha256"] = _identity_sha(missing_application)
        diagnostics["missing_closure_identity_sha256"] = _identity_sha(missing_closure)
        if missing_application:
            verdict = "FAIL_FIT_IDENTITIES_OUTSIDE_APPLICATION_SCOPE"
        elif missing_closure:
            verdict = "FAIL_APPLICATION_IDENTITIES_OUTSIDE_CLOSURE"
        elif fit_ticker_set is not None and {ticker for ticker, _ in fit_set} != fit_ticker_set:
            verdict = "FAIL_FIT_IDENTITY_TICKER_SCOPE_MISMATCH"
        elif application_ticker_set is not None and {ticker for ticker, _ in application_set} != application_ticker_set:
            verdict = "FAIL_APPLICATION_IDENTITY_TICKER_SCOPE_MISMATCH"
        elif closure_ticker_set is not None and {ticker for ticker, _ in closure_set} != closure_ticker_set:
            verdict = "FAIL_CLOSURE_IDENTITY_TICKER_SCOPE_MISMATCH"
        elif fit_ticker_set is not None and not fit_ticker_set <= (application_ticker_set or set()):
            verdict = "FAIL_FIT_TICKERS_OUTSIDE_APPLICATION_SCOPE"
        elif application_ticker_set is not None and not application_ticker_set <= (closure_ticker_set or set()):
            verdict = "FAIL_APPLICATION_TICKERS_OUTSIDE_CLOSURE"
        elif family_coverage is None or official_sessions is None:
            verdict = "FAIL_FAMILY_COVERAGE_EVIDENCE_MISSING"
        else:
            expected_identities = application_set | closure_set
            try:
                certified_family = combine_family_coverage(
                    pd.DataFrame(sorted(expected_identities), columns=["ticker", "date"]),
                    family_coverage,
                    official_sessions,
                )
            except (TypeError, ValueError) as exc:
                verdict = "FAIL_FAMILY_COVERAGE_EVIDENCE_INVALID"
                diagnostics["family_coverage_error"] = str(exc)
            else:
                diagnostics["family_coverage_rows"] = len(certified_family)
                certified_keys: set[tuple[str, str]] = set()
                invalid_provenance = 0
                invalid_family_state = 0
                for index, row in certified_family.iterrows():
                    key = (
                        _normalise_ticker(row["ticker"]),
                        _normalise_date(row["date"], label=f"combined_family_coverage[{index}].date"),
                    )
                    if row["coverage_state"] == CA_COVERAGE_CERTIFIED:
                        certified_keys.add(key)
                    if row["coverage_state"] != CA_COVERAGE_CERTIFIED or row["missing_structural_families"] or row["conflicting_structural_families"]:
                        invalid_family_state += 1
                        continue
                    source_ref = str(row["source_ref"] or "").strip()
                    composite_sha = str(row["evidence_sha256"] or "").strip().lower()
                    contracts = str(row["supporting_source_contracts"] or "").strip()
                    supporting_hashes = [value for value in str(row["supporting_evidence_sha256"] or "").split("|") if value]
                    if (
                        not source_ref
                        or not contracts
                        or not re.fullmatch(r"[0-9a-f]{64}", composite_sha)
                        or not supporting_hashes
                        or any(not re.fullmatch(r"[0-9a-f]{64}", value.lower()) for value in supporting_hashes)
                    ):
                        invalid_provenance += 1
                diagnostics["family_certified_identity_count"] = len(certified_keys)
                diagnostics["family_invalid_state_count"] = invalid_family_state
                diagnostics["family_invalid_provenance_count"] = invalid_provenance
                if invalid_family_state or invalid_provenance or certified_keys != expected_identities:
                    missing_family = expected_identities - certified_keys
                    diagnostics["family_missing_identity_count"] = len(missing_family)
                    diagnostics["family_missing_identity_sha256"] = _identity_sha(missing_family)
                    verdict = "FAIL_FAMILY_COVERAGE_NOT_FULLY_CERTIFIED"
                elif temporal_attestation is None:
                    verdict = "FAIL_TEMPORAL_ASOF_EVIDENCE_MISSING"
                else:
                    temporal_required = {
                        "ticker",
                        "date",
                        "coverage_state",
                        "source_contract_id",
                        "source_ref",
                        "evidence_sha256",
                        "as_of_semantics",
                    }
                    missing_temporal_columns = temporal_required - set(temporal_attestation.columns)
                    if missing_temporal_columns:
                        verdict = "FAIL_TEMPORAL_ASOF_EVIDENCE_INVALID"
                        diagnostics["temporal_missing_columns"] = sorted(missing_temporal_columns)
                    else:
                        temporal_seen: set[tuple[str, str]] = set()
                        temporal_invalid = 0
                        temporal_duplicate = False
                        accepted_semantics = {
                            "PER_SESSION_AS_OF_NO_EVENT_COVERAGE",
                            "HISTORICAL_DATE_LEVEL_AS_OF_NO_EVENT_COVERAGE",
                        }
                        for index, row in temporal_attestation.reset_index(drop=True).iterrows():
                            key = (
                                _normalise_ticker(row["ticker"]),
                                _normalise_date(row["date"], label=f"temporal_attestation[{index}].date"),
                            )
                            if key in temporal_seen:
                                temporal_duplicate = True
                                continue
                            temporal_seen.add(key)
                            if (
                                str(row["coverage_state"] or "").strip().upper() != "TEMPORAL_ASOF_CERTIFIED"
                                or not str(row["source_contract_id"] or "").strip()
                                or not str(row["source_ref"] or "").strip()
                                or not re.fullmatch(r"[0-9a-fA-F]{64}", str(row["evidence_sha256"] or "").strip())
                                or str(row["as_of_semantics"] or "").strip().upper() not in accepted_semantics
                            ):
                                temporal_invalid += 1
                        missing_temporal = expected_identities - temporal_seen
                        diagnostics["temporal_attestation_rows"] = len(temporal_attestation)
                        diagnostics["temporal_missing_identity_count"] = len(missing_temporal)
                        diagnostics["temporal_missing_identity_sha256"] = _identity_sha(missing_temporal)
                        diagnostics["temporal_invalid_provenance_count"] = temporal_invalid
                        if temporal_duplicate:
                            verdict = "FAIL_TEMPORAL_ASOF_EVIDENCE_DUPLICATE_IDENTITY"
                        elif missing_temporal:
                            verdict = "FAIL_TEMPORAL_ASOF_EVIDENCE_INCOMPLETE"
                        elif temporal_invalid:
                            verdict = "FAIL_TEMPORAL_ASOF_EVIDENCE_INVALID"
                        else:
                            verdict = "PASS"
                diagnostics["scope_evidence_rows"] = len(scope_evidence) if scope_evidence is not None else 0
    return {
        "verdict": verdict,
        "fit_tickers": fit_ticker_count,
        "application_tickers": application_ticker_count,
        "closure_tickers": closure_ticker_count,
        "structural_event_complete": structural_event_complete,
        **diagnostics,
    }
