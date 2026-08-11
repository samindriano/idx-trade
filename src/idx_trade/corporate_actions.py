from __future__ import annotations

from enum import StrEnum

import numpy as np
import pandas as pd

from .security_master import normalise_ticker


class CorporateActionType(StrEnum):
    STOCK_SPLIT = "STOCK_SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    BONUS_SHARES = "BONUS_SHARES"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    CAPITAL_REDUCTION = "CAPITAL_REDUCTION"
    OTHER_SHARE_STRUCTURE = "OTHER_SHARE_STRUCTURE"


ACTION_COLUMNS = (
    "event_id",
    "ticker",
    "action_type",
    "announced_at",
    "knowledge_at",
    "market_effective_date",
    "cum_date",
    "ex_date",
    "recording_date",
    "ratio_old",
    "ratio_new",
    "subscription_price",
    "source",
    "source_ref",
    "source_url",
    "source_sha256",
)

_RATIO_REQUIRED = {
    CorporateActionType.STOCK_SPLIT,
    CorporateActionType.REVERSE_SPLIT,
    CorporateActionType.RIGHTS_ISSUE,
    CorporateActionType.BONUS_SHARES,
    CorporateActionType.STOCK_DIVIDEND,
}
_SPLIT_LIKE = {
    CorporateActionType.STOCK_SPLIT,
    CorporateActionType.REVERSE_SPLIT,
}


def _clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _normalise_action_type(value: object) -> str:
    text = str(value).upper().strip().replace("-", "_").replace(" ", "_")
    aliases = {
        "SPLIT": CorporateActionType.STOCK_SPLIT.value,
        "STOCKSPLIT": CorporateActionType.STOCK_SPLIT.value,
        "REVERSE_STOCK_SPLIT": CorporateActionType.REVERSE_SPLIT.value,
        "REVERSESPLIT": CorporateActionType.REVERSE_SPLIT.value,
        "RIGHT_ISSUE": CorporateActionType.RIGHTS_ISSUE.value,
        "RIGHTS": CorporateActionType.RIGHTS_ISSUE.value,
        "BONUS": CorporateActionType.BONUS_SHARES.value,
        "STOCK_DIV": CorporateActionType.STOCK_DIVIDEND.value,
    }
    text = aliases.get(text, text)
    return CorporateActionType(text).value


def canonicalize_corporate_actions(frame: pd.DataFrame) -> pd.DataFrame:
    """Build a strict event table without inferring missing corporate-action facts.

    ``market_effective_date`` is the first exchange session/date on which the
    event changes the relevant share/price basis. Source-specific dates must be
    mapped to this semantic explicitly before calling this function.
    """

    if frame.empty:
        return pd.DataFrame(columns=ACTION_COLUMNS)

    data = frame.copy()
    required = {
        "ticker",
        "action_type",
        "market_effective_date",
        "source",
        "source_ref",
        "source_url",
        "source_sha256",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Corporate-action columns missing: {sorted(missing)}")

    data["ticker"] = data["ticker"].map(normalise_ticker)
    invalid_ticker = ~data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
    if invalid_ticker.any():
        bad = data.loc[invalid_ticker, "ticker"].tolist()[:10]
        raise ValueError(f"Unsupported corporate-action ticker(s): {bad}")

    data["action_type"] = data["action_type"].map(_normalise_action_type)

    for column in (
        "market_effective_date",
        "cum_date",
        "ex_date",
        "recording_date",
    ):
        if column not in data.columns:
            data[column] = pd.NaT
        data[column] = pd.to_datetime(data[column], errors="coerce").dt.normalize()

    for column in ("announced_at", "knowledge_at"):
        if column not in data.columns:
            data[column] = pd.NaT
        data[column] = pd.to_datetime(data[column], errors="coerce")

    if data["market_effective_date"].isna().any():
        raise ValueError("Corporate action missing market_effective_date")

    # A same-document official announcement is knowable at announcement time.
    # Explicit later knowledge_at is preserved for delayed/supporting evidence.
    fill_knowledge = data["knowledge_at"].isna() & data["announced_at"].notna()
    data.loc[fill_knowledge, "knowledge_at"] = data.loc[fill_knowledge, "announced_at"]
    invalid_knowledge = (
        data["announced_at"].notna()
        & data["knowledge_at"].notna()
        & data["knowledge_at"].lt(data["announced_at"])
    )
    if invalid_knowledge.any():
        raise ValueError("knowledge_at precedes announced_at")

    for column in ("ratio_old", "ratio_new", "subscription_price"):
        if column not in data.columns:
            data[column] = np.nan
        data[column] = pd.to_numeric(data[column], errors="coerce")

    action_enum = data["action_type"].map(CorporateActionType)
    requires_ratio = action_enum.isin(_RATIO_REQUIRED)
    bad_ratio = requires_ratio & (
        data["ratio_old"].isna()
        | data["ratio_new"].isna()
        | data["ratio_old"].le(0)
        | data["ratio_new"].le(0)
    )
    if bad_ratio.any():
        raise ValueError("Ratio-bearing corporate action has invalid ratio")

    split = action_enum.eq(CorporateActionType.STOCK_SPLIT)
    reverse = action_enum.eq(CorporateActionType.REVERSE_SPLIT)
    if (split & data["ratio_new"].le(data["ratio_old"])).any():
        raise ValueError("STOCK_SPLIT must increase shares per old-share basis")
    if (reverse & data["ratio_new"].ge(data["ratio_old"])).any():
        raise ValueError("REVERSE_SPLIT must reduce shares per old-share basis")

    rights = action_enum.eq(CorporateActionType.RIGHTS_ISSUE)
    invalid_rights_price = rights & (
        data["subscription_price"].isna() | data["subscription_price"].lt(0)
    )
    if invalid_rights_price.any():
        raise ValueError("RIGHTS_ISSUE requires a non-negative subscription_price")

    for column in ("source", "source_ref", "source_url", "source_sha256"):
        data[column] = _clean_text(data[column])
        if data[column].eq("").any():
            raise ValueError(f"Corporate action missing provenance field: {column}")

    if (~data["source_url"].str.startswith("https://")).any():
        raise ValueError("Corporate-action source_url must use HTTPS")
    if (~data["source_sha256"].str.fullmatch(r"[0-9a-fA-F]{64}")).any():
        raise ValueError("Corporate-action source_sha256 must be a SHA-256 hex digest")
    data["source_sha256"] = data["source_sha256"].str.lower()

    data["event_id"] = (
        "IDX:"
        + data["ticker"]
        + ":"
        + data["action_type"]
        + ":"
        + data["market_effective_date"].dt.strftime("%Y%m%d")
    )
    duplicate = data.duplicated("event_id", keep=False)
    if duplicate.any():
        ids = sorted(data.loc[duplicate, "event_id"].unique().tolist())[:10]
        raise ValueError(
            "Duplicate corporate-action event requires explicit evidence reconciliation: "
            f"{ids}"
        )

    return (
        data[list(ACTION_COLUMNS)]
        .sort_values(["ticker", "market_effective_date", "action_type"])
        .reset_index(drop=True)
    )


def build_split_factor_schedule(actions: pd.DataFrame) -> pd.DataFrame:
    """Return mechanical split/reverse-split ratios only.

    ``expected_post_price_ratio`` is post-event price divided by the equivalent
    pre-event price absent market movement. Rights/bonus events are deliberately
    excluded because their economics require additional terms and should not be
    silently treated as simple splits.
    """

    canonical = canonicalize_corporate_actions(actions)
    if canonical.empty:
        return pd.DataFrame(
            columns=[
                "event_id",
                "ticker",
                "market_effective_date",
                "action_type",
                "share_multiplier",
                "expected_post_price_ratio",
            ]
        )

    mask = canonical["action_type"].isin([item.value for item in _SPLIT_LIKE])
    data = canonical.loc[
        mask,
        [
            "event_id",
            "ticker",
            "market_effective_date",
            "action_type",
            "ratio_old",
            "ratio_new",
        ],
    ].copy()
    data["share_multiplier"] = data["ratio_new"] / data["ratio_old"]
    data["expected_post_price_ratio"] = data["ratio_old"] / data["ratio_new"]
    return data.drop(columns=["ratio_old", "ratio_new"]).reset_index(drop=True)


def audit_split_price_discontinuities(
    prices: pd.DataFrame,
    actions: pd.DataFrame,
    *,
    ticker_column: str = "ticker",
    date_column: str = "date",
    open_column: str = "raw_open",
    close_column: str = "raw_close",
) -> pd.DataFrame:
    """Link split events to adjacent raw-price observations for diagnostics.

    This function intentionally does not auto-correct prices or declare a
    mismatch threshold. It only exposes the observed versus mechanical ratios.
    """

    schedule = build_split_factor_schedule(actions)
    columns = [
        "event_id",
        "ticker",
        "market_effective_date",
        "previous_price_date",
        "post_price_date",
        "previous_close",
        "post_open",
        "post_close",
        "expected_post_price_ratio",
        "observed_open_ratio",
        "observed_close_ratio",
    ]
    if schedule.empty:
        return pd.DataFrame(columns=columns)

    required = {ticker_column, date_column, open_column, close_column}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"Price columns missing: {sorted(missing)}")

    panel = prices.copy()
    panel[ticker_column] = panel[ticker_column].map(normalise_ticker)
    panel[date_column] = pd.to_datetime(panel[date_column], errors="coerce").dt.normalize()
    panel[open_column] = pd.to_numeric(panel[open_column], errors="coerce")
    panel[close_column] = pd.to_numeric(panel[close_column], errors="coerce")
    panel = panel.dropna(subset=[ticker_column, date_column]).sort_values(
        [ticker_column, date_column]
    )

    rows: list[dict[str, object]] = []
    for event in schedule.itertuples(index=False):
        ticker_rows = panel[panel[ticker_column].eq(event.ticker)]
        before = ticker_rows[ticker_rows[date_column].lt(event.market_effective_date)].tail(1)
        after = ticker_rows[ticker_rows[date_column].ge(event.market_effective_date)].head(1)

        previous_date = pd.NaT
        post_date = pd.NaT
        previous_close = np.nan
        post_open = np.nan
        post_close = np.nan
        if not before.empty:
            previous_date = before.iloc[0][date_column]
            previous_close = before.iloc[0][close_column]
        if not after.empty:
            post_date = after.iloc[0][date_column]
            post_open = after.iloc[0][open_column]
            post_close = after.iloc[0][close_column]

        observed_open_ratio = (
            post_open / previous_close
            if pd.notna(post_open) and pd.notna(previous_close) and previous_close != 0
            else np.nan
        )
        observed_close_ratio = (
            post_close / previous_close
            if pd.notna(post_close) and pd.notna(previous_close) and previous_close != 0
            else np.nan
        )
        rows.append(
            {
                "event_id": event.event_id,
                "ticker": event.ticker,
                "market_effective_date": event.market_effective_date,
                "previous_price_date": previous_date,
                "post_price_date": post_date,
                "previous_close": previous_close,
                "post_open": post_open,
                "post_close": post_close,
                "expected_post_price_ratio": event.expected_post_price_ratio,
                "observed_open_ratio": observed_open_ratio,
                "observed_close_ratio": observed_close_ratio,
            }
        )

    return pd.DataFrame(rows, columns=columns)
