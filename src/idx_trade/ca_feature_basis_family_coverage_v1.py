from __future__ import annotations

from collections.abc import Iterable, Sequence
import hashlib
import json

import pandas as pd

from .ca_feature_basis_gate_v1 import CA_COVERAGE_CERTIFIED, CA_COVERAGE_UNKNOWN
from .ca_feature_basis_v1 import STRUCTURAL_EVENT_FAMILIES


FAMILY_COVERAGE_CERTIFIED = "FAMILY_COVERAGE_CERTIFIED"
FAMILY_COVERAGE_UNKNOWN = "FAMILY_COVERAGE_UNKNOWN"
FAMILY_COVERAGE_STATES = {FAMILY_COVERAGE_CERTIFIED, FAMILY_COVERAGE_UNKNOWN}

# Every family in the frozen CA-aware policy must be covered before absence of
# a known event can be interpreted as globally safe for backward features.
DEFAULT_REQUIRED_FAMILIES: tuple[str, ...] = tuple(sorted(STRUCTURAL_EVENT_FAMILIES))


def _ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _dates(series: pd.Series, *, label: str) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if values.isna().any():
        raise ValueError(f"{label} contains invalid date")
    return values


def _sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .tz_localize(None)
        .normalize()
    )
    if sessions.isna().any() or not len(sessions):
        raise ValueError("official_sessions must be non-empty valid dates")
    return sessions.unique().sort_values()


def _composite_evidence_sha256(
    *,
    ticker: str,
    date: pd.Timestamp,
    required_families: Sequence[str],
    coverage_rows: list[dict[str, str]],
) -> str:
    payload = {
        "schema_version": "composite_ca_family_coverage_evidence_v1",
        "ticker": ticker,
        "date": date.strftime("%Y-%m-%d"),
        "required_families": sorted(required_families),
        "coverage_rows": sorted(
            coverage_rows,
            key=lambda row: (
                row["event_family"],
                row["source_contract_id"],
                row["evidence_sha256"],
                row["source_ref"],
            ),
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepare_family_coverage(
    coverage: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Validate source-family-specific corporate-action coverage evidence.

    Multiple independent sources may cover one family/date.  A source row is a
    coverage claim only for the explicit family named on that row; it cannot be
    generalized to other structural families.
    """

    required = {
        "ticker",
        "date",
        "event_family",
        "coverage_state",
        "source_contract_id",
        "source_ref",
        "evidence_sha256",
    }
    missing = required - set(coverage.columns)
    if missing:
        raise ValueError(f"family CA coverage missing columns: {sorted(missing)}")

    sessions = _sessions(official_sessions)
    session_set = set(pd.Timestamp(day) for day in sessions)
    out = coverage.copy()
    out["ticker"] = _ticker(out["ticker"])
    out["date"] = _dates(out["date"], label="family CA coverage")
    out["event_family"] = out["event_family"].astype(str).str.upper().str.strip()
    out["coverage_state"] = out["coverage_state"].astype(str).str.upper().str.strip()
    out["source_contract_id"] = out["source_contract_id"].fillna("").astype(str).str.strip()
    out["source_ref"] = out["source_ref"].fillna("").astype(str).str.strip()
    out["evidence_sha256"] = (
        out["evidence_sha256"].fillna("").astype(str).str.strip().str.lower()
    )

    if out["ticker"].eq("").any():
        raise ValueError("family CA coverage contains empty ticker")
    if not set(out["date"]).issubset(session_set):
        raise ValueError("family CA coverage contains non-official session")
    unsupported_family = sorted(set(out["event_family"]) - set(STRUCTURAL_EVENT_FAMILIES))
    if unsupported_family:
        raise ValueError(f"unsupported structural family coverage: {unsupported_family}")
    unsupported_state = sorted(set(out["coverage_state"]) - FAMILY_COVERAGE_STATES)
    if unsupported_state:
        raise ValueError(f"unsupported family coverage state: {unsupported_state}")
    if out["source_contract_id"].eq("").any():
        raise ValueError("family CA coverage requires source_contract_id")
    if out.duplicated(["ticker", "date", "event_family", "source_contract_id"]).any():
        raise ValueError("duplicate family/source coverage claim")

    certified = out["coverage_state"].eq(FAMILY_COVERAGE_CERTIFIED)
    if (certified & out["source_ref"].eq("")).any():
        raise ValueError("certified family coverage requires source_ref")
    if (certified & ~out["evidence_sha256"].str.fullmatch(r"[0-9a-f]{64}")).any():
        raise ValueError("certified family coverage requires evidence_sha256")

    if "coverage_conflict" in out.columns:
        text = out["coverage_conflict"].astype(str).str.strip().str.lower()
        if not set(text).issubset({"true", "false"}):
            raise ValueError("coverage_conflict must contain strict booleans")
        out["coverage_conflict"] = text.eq("true")
    else:
        out["coverage_conflict"] = False

    return out.sort_values(
        ["ticker", "date", "event_family", "source_contract_id"], kind="mergesort"
    ).reset_index(drop=True)


def combine_family_coverage(
    identities: pd.DataFrame,
    family_coverage: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    required_families: Sequence[str] = DEFAULT_REQUIRED_FAMILIES,
    composite_source_ref: str = "COMPOSITE_CA_FAMILY_COVERAGE_V1",
) -> pd.DataFrame:
    """Collapse family-scoped evidence into the binary gate coverage ledger.

    A ticker/session is globally certified only when *every* required structural
    family has at least one authoritative certified coverage claim and no claim
    for that family is marked as a source conflict.  One provider therefore
    cannot silently certify event families outside its explicit source contract.
    """

    if not {"ticker", "date"}.issubset(identities.columns):
        raise ValueError("identity frame requires ticker/date")
    sessions = _sessions(official_sessions)
    ids = identities[["ticker", "date"]].copy()
    ids["ticker"] = _ticker(ids["ticker"])
    ids["date"] = _dates(ids["date"], label="identity frame")
    if ids["ticker"].eq("").any() or ids.duplicated(["ticker", "date"]).any():
        raise ValueError("identity frame contains empty/duplicate ticker-date")
    if not set(ids["date"]).issubset(set(sessions)):
        raise ValueError("identity frame contains non-official session")

    families = tuple(dict.fromkeys(str(value).upper().strip() for value in required_families))
    if not families:
        raise ValueError("required_families must not be empty")
    unsupported = sorted(set(families) - set(STRUCTURAL_EVENT_FAMILIES))
    if unsupported:
        raise ValueError(f"unsupported required structural families: {unsupported}")

    coverage = prepare_family_coverage(family_coverage, sessions)
    grouped = {
        key: group
        for key, group in coverage.groupby(["ticker", "date", "event_family"], sort=False)
    }

    rows: list[dict[str, object]] = []
    for identity in ids.itertuples(index=False):
        ticker = str(identity.ticker)
        date = pd.Timestamp(identity.date)
        missing: list[str] = []
        conflicting: list[str] = []
        supporting_hashes: set[str] = set()
        supporting_contracts: set[str] = set()
        supporting_rows: list[dict[str, str]] = []

        for family in families:
            claims = grouped.get((ticker, date, family))
            if claims is None or claims.empty:
                missing.append(family)
                continue
            if bool(claims["coverage_conflict"].any()):
                conflicting.append(family)
                continue
            certified = claims[claims["coverage_state"].eq(FAMILY_COVERAGE_CERTIFIED)]
            if certified.empty:
                missing.append(family)
                continue
            for claim in certified.itertuples(index=False):
                supporting_hashes.add(str(claim.evidence_sha256))
                supporting_contracts.add(str(claim.source_contract_id))
                supporting_rows.append(
                    {
                        "event_family": family,
                        "source_contract_id": str(claim.source_contract_id),
                        "source_ref": str(claim.source_ref),
                        "evidence_sha256": str(claim.evidence_sha256),
                    }
                )

        globally_safe = not missing and not conflicting
        composite_sha = (
            _composite_evidence_sha256(
                ticker=ticker,
                date=date,
                required_families=families,
                coverage_rows=supporting_rows,
            )
            if globally_safe
            else ""
        )
        rows.append(
            {
                "ticker": ticker,
                "date": date,
                "coverage_state": (
                    CA_COVERAGE_CERTIFIED if globally_safe else CA_COVERAGE_UNKNOWN
                ),
                "source_ref": str(composite_source_ref),
                "evidence_sha256": composite_sha,
                "missing_structural_families": "|".join(sorted(missing)),
                "conflicting_structural_families": "|".join(sorted(conflicting)),
                "supporting_source_contracts": "|".join(sorted(supporting_contracts)),
                "supporting_evidence_sha256": "|".join(sorted(supporting_hashes)),
            }
        )

    return pd.DataFrame(rows).sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
