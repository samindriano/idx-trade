from __future__ import annotations

from pathlib import Path

import pandas as pd

from .security_master import normalise_ticker


CURATED_IDENTITY_COLUMNS = (
    "ticker",
    "company_name",
    "security_type",
    "listed_from",
    "listed_to",
    "source",
    "source_ref",
    "evidence_note",
)


def _is_common_share(value: object) -> bool:
    normalized = str(value).casefold().strip()
    return "saham biasa" in normalized or "common share" in normalized


def canonicalize_curated_security_identities(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate manually curated authoritative historical identity evidence.

    This registry is a last-resort identity source for securities that are
    discoverable from official PIT market evidence but absent from the current
    IDX/KSEI identity surfaces. It must never be used to invent identity merely
    to make a data gate pass.
    """

    if frame.empty:
        return pd.DataFrame(columns=CURATED_IDENTITY_COLUMNS)
    missing = set(CURATED_IDENTITY_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Curated identity columns missing: {sorted(missing)}")

    data = frame[list(CURATED_IDENTITY_COLUMNS)].copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["company_name"] = data["company_name"].fillna("").astype(str).str.strip()
    data["security_type"] = data["security_type"].fillna("").astype(str).str.strip()
    data["listed_from"] = pd.to_datetime(data["listed_from"], errors="coerce").dt.normalize()
    data["listed_to"] = pd.to_datetime(data["listed_to"], errors="coerce").dt.normalize()
    data["source"] = data["source"].fillna("").astype(str).str.strip()
    data["source_ref"] = data["source_ref"].fillna("").astype(str).str.strip()
    data["evidence_note"] = data["evidence_note"].fillna("").astype(str).str.strip()

    invalid = data[
        ~data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
        | data["company_name"].eq("")
        | data["security_type"].eq("")
        | data["listed_from"].isna()
        | data["source"].eq("")
        | data["source_ref"].eq("")
        | data["evidence_note"].eq("")
    ]
    if not invalid.empty:
        raise ValueError("Curated security identity contains incomplete evidence")
    if (~data["security_type"].map(_is_common_share)).any():
        raise ValueError("Curated identity registry currently accepts common shares only")
    if (
        data["listed_to"].notna()
        & data["listed_to"].lt(data["listed_from"])
    ).any():
        raise ValueError("Curated security identity has listed_to before listed_from")
    if data["ticker"].duplicated().any():
        raise ValueError("Curated security identity registry contains duplicate tickers")
    return data.sort_values(["ticker", "listed_from"]).reset_index(drop=True)


def load_curated_security_identities(path: str | Path) -> pd.DataFrame:
    return canonicalize_curated_security_identities(pd.read_csv(path))


def supplement_historical_security_identities(
    active_listings: pd.DataFrame,
    delisted_listings: pd.DataFrame,
    curated_identities: pd.DataFrame,
    *,
    required_tickers: list[str] | tuple[str, ...] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Supplement only still-missing common-share identities from curated evidence.

    Primary IDX/KSEI identity always wins. Curated rows are added only when the
    ticker is absent from both primary active and delisted identity inputs. This
    prevents a hand-maintained row from silently overriding an authoritative
    listing interval already known to the pipeline.
    """

    curated = canonicalize_curated_security_identities(curated_identities)
    active = active_listings.copy()
    delisted = delisted_listings.copy()
    existing = set()
    for frame in (active, delisted):
        if "ticker" in frame.columns:
            existing.update(frame["ticker"].dropna().map(normalise_ticker))

    wanted = (
        {normalise_ticker(value) for value in required_tickers}
        if required_tickers is not None
        else set(curated["ticker"])
    )
    additions_active: list[dict[str, object]] = []
    additions_delisted: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []

    for row in curated.itertuples(index=False):
        ticker = normalise_ticker(row.ticker)
        if ticker not in wanted:
            continue
        if ticker in existing:
            diagnostics.append(
                {
                    "ticker": ticker,
                    "status": "PRIMARY_IDENTITY_ALREADY_PRESENT",
                    "source": row.source,
                    "source_ref": row.source_ref,
                }
            )
            continue
        target = additions_delisted if not pd.isna(row.listed_to) else additions_active
        target.append(
            {
                "ticker": ticker,
                "company_name": row.company_name,
                "listed_from": pd.Timestamp(row.listed_from).normalize(),
                "listed_to": (
                    pd.Timestamp(row.listed_to).normalize()
                    if not pd.isna(row.listed_to)
                    else pd.NaT
                ),
                "source": row.source,
            }
        )
        diagnostics.append(
            {
                "ticker": ticker,
                "status": "CURATED_IDENTITY_SUPPLEMENTED",
                "source": row.source,
                "source_ref": row.source_ref,
            }
        )
        existing.add(ticker)

    if additions_active:
        active = pd.concat([active, pd.DataFrame(additions_active)], ignore_index=True)
    if additions_delisted:
        delisted = pd.concat([delisted, pd.DataFrame(additions_delisted)], ignore_index=True)

    return active, delisted, pd.DataFrame(
        diagnostics,
        columns=("ticker", "status", "source", "source_ref"),
    )
