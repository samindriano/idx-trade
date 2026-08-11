from __future__ import annotations

import pandas as pd

from .security_master import build_security_master, normalise_ticker


LIFECYCLE_COLUMNS = (
    "ticker",
    "company_name",
    "listed_from",
    "listed_to",
    "source",
    "source_ref",
    "source_url",
    "evidence_level",
)

UNIVERSE_COVERAGE_COLUMNS = (
    "effective_from",
    "effective_to",
    "source",
    "is_complete",
    "discovery_basis",
)


def canonicalize_lifecycle_records(frame: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize legal listing intervals for historical-universe use.

    ``listed_from`` and ``listed_to`` are inclusive legal-existence boundaries,
    matching ``security_master.existence_state`` semantics.  The canonical
    table contains one reconciled row per listing interval; multiple raw
    evidence rows must be reconciled upstream rather than silently collapsed.
    """

    if frame.empty:
        return pd.DataFrame(columns=LIFECYCLE_COLUMNS)

    data = frame.copy()
    required = {"ticker", "listed_from", "source"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Lifecycle columns missing: {sorted(missing)}")

    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["listed_from"] = pd.to_datetime(data["listed_from"], errors="coerce").dt.normalize()

    if "listed_to" not in data.columns:
        data["listed_to"] = pd.NaT
    data["listed_to"] = pd.to_datetime(data["listed_to"], errors="coerce").dt.normalize()

    defaults = {
        "company_name": "",
        "source_ref": "",
        "source_url": "",
        "evidence_level": "",
    }
    for column, default in defaults.items():
        if column not in data.columns:
            data[column] = default
        data[column] = data[column].fillna(default).astype(str).str.strip()

    data["source"] = data["source"].fillna("").astype(str).str.strip()

    invalid_ticker = ~data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
    if invalid_ticker.any():
        examples = data.loc[invalid_ticker, "ticker"].astype(str).tolist()[:10]
        raise ValueError(f"Invalid IDX ticker(s) in lifecycle data: {examples}")

    if data["listed_from"].isna().any():
        examples = data.loc[data["listed_from"].isna(), "ticker"].tolist()[:10]
        raise ValueError(f"Missing listed_from for lifecycle ticker(s): {examples}")

    if data["source"].eq("").any():
        examples = data.loc[data["source"].eq(""), "ticker"].tolist()[:10]
        raise ValueError(f"Missing lifecycle source for ticker(s): {examples}")

    invalid_interval = data["listed_to"].notna() & data["listed_to"].lt(data["listed_from"])
    if invalid_interval.any():
        examples = data.loc[invalid_interval, "ticker"].tolist()[:10]
        raise ValueError(f"Lifecycle interval ends before it starts: {examples}")

    duplicate_interval = data.duplicated(
        ["ticker", "listed_from", "listed_to"], keep=False
    )
    if duplicate_interval.any():
        examples = (
            data.loc[duplicate_interval, ["ticker", "listed_from", "listed_to"]]
            .astype(str)
            .drop_duplicates()
            .head(10)
            .to_dict("records")
        )
        raise ValueError(
            "Duplicate lifecycle intervals require explicit upstream reconciliation: "
            f"{examples}"
        )

    ordered = data.sort_values(
        ["ticker", "listed_from", "listed_to"], na_position="last"
    ).reset_index(drop=True)

    for ticker, group in ordered.groupby("ticker", sort=False):
        previous_to: pd.Timestamp | None = None
        previous_open = False
        for row in group.itertuples(index=False):
            current_from = pd.Timestamp(row.listed_from)
            current_open = pd.isna(row.listed_to)
            current_to = (
                pd.Timestamp.max.normalize()
                if current_open
                else pd.Timestamp(row.listed_to)
            )
            if previous_to is not None and current_from <= previous_to:
                raise ValueError(f"Overlapping lifecycle intervals for {ticker}")
            if previous_open:
                raise ValueError(
                    f"Open-ended lifecycle interval followed by another interval for {ticker}"
                )
            previous_to = current_to
            previous_open = current_open

    return ordered[list(LIFECYCLE_COLUMNS)]


def lifecycle_to_security_master(frame: pd.DataFrame) -> pd.DataFrame:
    """Bridge canonical lifecycle intervals into the existing security master."""

    data = canonicalize_lifecycle_records(frame)
    if data.empty:
        raise ValueError("Historical lifecycle data must not be empty")

    columns = ["ticker", "company_name", "listed_from", "listed_to", "source"]
    active = data[data["listed_to"].isna()][columns].copy()
    delisted = data[data["listed_to"].notna()][columns].copy()
    return build_security_master(active, delisted)


def historical_universe_as_of(
    lifecycle: pd.DataFrame,
    as_of_date: pd.Timestamp,
) -> pd.DataFrame:
    """Return the legally listed security intervals active on ``as_of_date``."""

    data = canonicalize_lifecycle_records(lifecycle)
    if data.empty:
        return data

    as_of = pd.Timestamp(as_of_date).tz_localize(None).normalize()
    active = data[
        data["listed_from"].le(as_of)
        & (data["listed_to"].isna() | data["listed_to"].ge(as_of))
    ].copy()
    return active.sort_values(["ticker", "listed_from"]).reset_index(drop=True)


def audit_price_lifecycle_consistency(
    lifecycle: pd.DataFrame,
    observations: pd.DataFrame,
) -> pd.DataFrame:
    """Find price observations that cannot exist under the lifecycle table.

    This is intentionally independent of trading/suspension state.  A listed
    security may legitimately have no trade, but a price observation may not
    occur outside every legal listing interval.
    """

    data = canonicalize_lifecycle_records(lifecycle)
    required = {"ticker", "date"}
    missing = required - set(observations.columns)
    if missing:
        raise ValueError(f"Observation columns missing: {sorted(missing)}")

    obs = observations[["ticker", "date"]].copy()
    obs["ticker"] = obs["ticker"].map(normalise_ticker)
    obs["date"] = pd.to_datetime(obs["date"], errors="coerce").dt.normalize()
    if obs["date"].isna().any():
        raise ValueError("Price observations contain invalid dates")
    invalid_ticker = ~obs["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
    if invalid_ticker.any():
        raise ValueError("Price observations contain invalid IDX tickers")
    obs = obs.drop_duplicates().sort_values(["ticker", "date"]).reset_index(drop=True)

    lifecycle_by_ticker = {
        ticker: group for ticker, group in data.groupby("ticker", sort=False)
    }
    issues: list[pd.DataFrame] = []

    for ticker, group in obs.groupby("ticker", sort=False):
        intervals = lifecycle_by_ticker.get(ticker)
        if intervals is None or intervals.empty:
            problem = group.copy()
            problem["issue"] = "NO_LIFECYCLE_RECORD"
            issues.append(problem)
            continue

        covered = pd.Series(False, index=group.index)
        for interval in intervals.itertuples(index=False):
            covered |= group["date"].ge(pd.Timestamp(interval.listed_from)) & (
                pd.isna(interval.listed_to)
                | group["date"].le(pd.Timestamp(interval.listed_to))
            )

        if (~covered).any():
            problem = group.loc[~covered].copy()
            problem["issue"] = "OBSERVED_OUTSIDE_LISTING_INTERVAL"
            issues.append(problem)

    if not issues:
        return pd.DataFrame(columns=["ticker", "date", "issue"])
    return pd.concat(issues, ignore_index=True).sort_values(
        ["ticker", "date", "issue"]
    ).reset_index(drop=True)


def compare_current_universe(
    lifecycle: pd.DataFrame,
    official_current_tickers: pd.Series | list[str] | tuple[str, ...] | set[str],
    as_of_date: pd.Timestamp,
) -> pd.DataFrame:
    """Compare a lifecycle-derived snapshot with an official current snapshot."""

    expected = set(historical_universe_as_of(lifecycle, as_of_date)["ticker"])
    official = {normalise_ticker(value) for value in official_current_tickers}

    rows = [
        {"ticker": ticker, "issue": "MISSING_FROM_LIFECYCLE_SNAPSHOT"}
        for ticker in sorted(official - expected)
    ]
    rows.extend(
        {"ticker": ticker, "issue": "STALE_LISTED_IN_LIFECYCLE_SNAPSHOT"}
        for ticker in sorted(expected - official)
    )
    return pd.DataFrame(rows, columns=["ticker", "issue"])


def canonicalize_universe_coverage(frame: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize bounded completeness claims for historical universe data.

    Completeness is fail-closed: a row cannot remain ``is_complete=True``
    without a finite right boundary and an explicit discovery basis.
    """

    if frame.empty:
        return pd.DataFrame(columns=UNIVERSE_COVERAGE_COLUMNS)

    data = frame.copy()
    required = {"effective_from", "source", "is_complete"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Universe coverage columns missing: {sorted(missing)}")

    data["effective_from"] = pd.to_datetime(
        data["effective_from"], errors="coerce"
    ).dt.normalize()
    if "effective_to" not in data.columns:
        data["effective_to"] = pd.NaT
    data["effective_to"] = pd.to_datetime(
        data["effective_to"], errors="coerce"
    ).dt.normalize()
    if "discovery_basis" not in data.columns:
        data["discovery_basis"] = ""

    data["source"] = data["source"].fillna("").astype(str).str.strip()
    data["discovery_basis"] = (
        data["discovery_basis"].fillna("").astype(str).str.strip()
    )
    data["is_complete"] = data["is_complete"].astype(bool)

    if data["effective_from"].isna().any() or data["source"].eq("").any():
        raise ValueError("Universe coverage rows require effective_from and source")

    invalid = data["effective_to"].notna() & data["effective_to"].lt(
        data["effective_from"]
    )
    if invalid.any():
        raise ValueError("Universe coverage window ends before it starts")

    unsupported_complete = data["is_complete"] & (
        data["effective_to"].isna() | data["discovery_basis"].eq("")
    )
    data.loc[unsupported_complete, "is_complete"] = False

    return data[list(UNIVERSE_COVERAGE_COLUMNS)].sort_values(
        ["effective_from", "effective_to"], na_position="last"
    ).reset_index(drop=True)


def universe_coverage_complete_on(
    coverage: pd.DataFrame,
    as_of_date: pd.Timestamp,
) -> bool:
    """Return whether a proven-complete coverage window contains a date."""

    data = canonicalize_universe_coverage(coverage)
    if data.empty:
        return False
    as_of = pd.Timestamp(as_of_date).tz_localize(None).normalize()
    covered = (
        data["is_complete"]
        & data["effective_from"].le(as_of)
        & data["effective_to"].notna()
        & data["effective_to"].ge(as_of)
    )
    return bool(covered.any())
