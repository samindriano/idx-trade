from __future__ import annotations

import numpy as np
import pandas as pd

from .ca_feature_basis_v1 import NOT_APPLICABLE, apply_direct_feature_basis_mask
from .ca_feature_basis_v4_contract_v1 import V4_CA_BASIS_DIRECT_SOURCE_FEATURES


# Exact historical builder pinned by the accepted clean V4-X1 refit contract.
FROZEN_V4_FEATURE_BUILDER_BLOB_SHA1 = "59ad05f815870ae00480dc7945fe18371d8eff9c"

V4_XS_SOURCE_FEATURES = (
    "close_return_5",
    "close_return_20",
    "atr14_over_close",
    "close_position_20",
    "distance_high_20_atr",
    "distance_low_20_atr",
    "distance_high_60_atr",
    "distance_low_60_atr",
    "relative_volume_20",
    "log_regular_value_relative_20",
)
V4_XS_FEATURE_COLUMNS = tuple(f"xs_rank_{name}" for name in V4_XS_SOURCE_FEATURES)
V4_MARKET_CONTEXT_COLUMNS = (
    "market_primary_liquid_count",
    "market_breadth_return_5_positive",
    "market_breadth_return_20_positive",
    "market_median_close_return_5",
    "market_median_close_return_20",
    "market_median_atr14_over_close",
    "market_median_close_position_20",
    "market_median_relative_volume_20",
    "market_median_log_regular_value_relative_20",
)
V4_MARKET_RELATIVE_COLUMNS = (
    "market_relative_close_return_5",
    "market_relative_close_return_20",
    "market_relative_atr14_over_close",
    "market_relative_close_position_20",
    "market_relative_relative_volume_20",
    "market_relative_log_regular_value_relative_20",
)
V4_CONTROL_FEATURE_COLUMNS = (
    *V4_XS_FEATURE_COLUMNS,
    *V4_MARKET_CONTEXT_COLUMNS,
    *V4_MARKET_RELATIVE_COLUMNS,
)

_RELATIVE_SOURCE_TO_MARKET = {
    "close_return_5": ("market_median_close_return_5", "market_relative_close_return_5"),
    "close_return_20": ("market_median_close_return_20", "market_relative_close_return_20"),
    "atr14_over_close": ("market_median_atr14_over_close", "market_relative_atr14_over_close"),
    "close_position_20": ("market_median_close_position_20", "market_relative_close_position_20"),
    "relative_volume_20": ("market_median_relative_volume_20", "market_relative_relative_volume_20"),
    "log_regular_value_relative_20": (
        "market_median_log_regular_value_relative_20",
        "market_relative_log_regular_value_relative_20",
    ),
}


def _ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _date(series: pd.Series) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if values.isna().any():
        raise ValueError("V4 direct feature table contains invalid date")
    return values


def _finite(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").astype(float)
    return numeric.where(np.isfinite(numeric))


def assert_frozen_v4_feature_builder_blob(actual_blob_sha1: object) -> str:
    """Fail closed unless application code proves the exact frozen builder blob.

    The remediation branch intentionally does not carry the historical feature
    builder.  An application runner must resolve the authoritative retained git
    ref/blob and pass that SHA here before using this recomputation contract.
    Merely copying formulas into this module is not accepted as provenance.
    """

    actual = str(actual_blob_sha1 or "").strip().lower()
    if actual != FROZEN_V4_FEATURE_BUILDER_BLOB_SHA1:
        raise ValueError(
            "V4 frozen feature builder blob mismatch: "
            f"{actual or '<empty>'}!={FROZEN_V4_FEATURE_BUILDER_BLOB_SHA1}"
        )
    return actual


def _assert_not_applicable_is_natural_missing(
    source: pd.DataFrame,
    admission: pd.DataFrame,
) -> None:
    """Prevent CA remediation from manufacturing new warm-up missingness.

    `NOT_APPLICABLE` means the frozen sequential formula did not yet have enough
    dependency history.  Such a source feature must already be non-finite in the
    frozen direct-feature table.  If it is finite, masking it would be a science
    change rather than CA remediation, so application fails closed.
    """

    required = {"ticker", "date", "feature", "basis_integrity_state"}
    missing = required - set(admission.columns)
    if missing:
        raise ValueError(f"feature admission missing columns: {sorted(missing)}")

    states = admission[list(required)].copy()
    states["ticker"] = _ticker(states["ticker"])
    states["date"] = _date(states["date"])
    states["feature"] = states["feature"].astype(str)
    states["basis_integrity_state"] = (
        states["basis_integrity_state"].astype(str).str.upper().str.strip()
    )
    if states.duplicated(["ticker", "date", "feature"]).any():
        raise ValueError("feature admission contains duplicate identities")

    for feature in V4_CA_BASIS_DIRECT_SOURCE_FEATURES:
        not_applicable = states.loc[
            states["feature"].eq(feature)
            & states["basis_integrity_state"].eq(NOT_APPLICABLE),
            ["ticker", "date"],
        ]
        if not_applicable.empty:
            continue
        values = source[["ticker", "date", feature]].merge(
            not_applicable,
            on=["ticker", "date"],
            how="inner",
            validate="one_to_one",
        )
        finite = np.isfinite(pd.to_numeric(values[feature], errors="coerce").astype(float))
        if bool(finite.any()):
            raise ValueError(
                "NOT_APPLICABLE cannot erase finite frozen source feature: "
                f"{feature}:{int(finite.sum())}"
            )


def recompute_v4_control_after_basis_admission(
    direct_features: pd.DataFrame,
    admission: pd.DataFrame,
) -> pd.DataFrame:
    """Recompute frozen V4 cross-sectional/context features after CA masking.

    ``direct_features`` must already contain the frozen direct source-feature
    values and unchanged universe membership.  CA-sensitive direct values are
    masked first.  Every derived rank/context/relative column is then rebuilt
    from the masked source values; any stale pre-remediation derived columns are
    overwritten and cannot leak back into the result.

    This function deliberately does not alter universe membership, compute raw
    rolling features, access targets/outcomes, or fit/score a model.
    """

    required = {
        "ticker",
        "date",
        "universe_primary_liquid",
        *V4_XS_SOURCE_FEATURES,
    }
    missing = required - set(direct_features.columns)
    if missing:
        raise ValueError(f"V4 direct feature table missing columns: {sorted(missing)}")
    if direct_features.duplicated(["ticker", "date"]).any():
        raise ValueError("V4 direct feature table contains duplicate ticker/date")

    source = direct_features.copy()
    source["ticker"] = _ticker(source["ticker"])
    source["date"] = _date(source["date"])
    if source["ticker"].eq("").any():
        raise ValueError("V4 direct feature table contains empty ticker")

    # Never trust pre-existing derived columns from the contaminated build.
    source = source.drop(columns=list(V4_CONTROL_FEATURE_COLUMNS), errors="ignore")
    _assert_not_applicable_is_natural_missing(source, admission)
    masked = apply_direct_feature_basis_mask(
        source,
        admission,
        features=V4_CA_BASIS_DIRECT_SOURCE_FEATURES,
    )

    primary_mask = masked["universe_primary_liquid"].astype(bool)
    primary = masked.loc[primary_mask].copy()
    if primary.empty:
        raise ValueError("basis-remediated V4 feature table has no primary-liquid rows")

    for source_name, output in zip(
        V4_XS_SOURCE_FEATURES, V4_XS_FEATURE_COLUMNS, strict=True
    ):
        masked[output] = np.nan
        source_values = _finite(primary[source_name])
        ranks = source_values.groupby(primary["date"]).rank(method="average", pct=True)
        masked.loc[ranks.index, output] = ranks.astype(float)

    context_rows: list[dict[str, object]] = []
    for day, block in primary.groupby("date", sort=True):
        def finite_values(name: str) -> pd.Series:
            return _finite(block[name]).dropna()

        r5 = finite_values("close_return_5")
        r20 = finite_values("close_return_20")
        atr14 = finite_values("atr14_over_close")
        close_pos = finite_values("close_position_20")
        rel_volume = finite_values("relative_volume_20")
        rel_value = finite_values("log_regular_value_relative_20")
        context_rows.append(
            {
                "date": pd.Timestamp(day),
                "market_primary_liquid_count": float(len(block)),
                "market_breadth_return_5_positive": float((r5 > 0.0).mean()) if len(r5) else np.nan,
                "market_breadth_return_20_positive": float((r20 > 0.0).mean()) if len(r20) else np.nan,
                "market_median_close_return_5": float(r5.median()) if len(r5) else np.nan,
                "market_median_close_return_20": float(r20.median()) if len(r20) else np.nan,
                "market_median_atr14_over_close": float(atr14.median()) if len(atr14) else np.nan,
                "market_median_close_position_20": float(close_pos.median()) if len(close_pos) else np.nan,
                "market_median_relative_volume_20": float(rel_volume.median()) if len(rel_volume) else np.nan,
                "market_median_log_regular_value_relative_20": float(rel_value.median()) if len(rel_value) else np.nan,
            }
        )

    context = pd.DataFrame(context_rows)
    masked = masked.merge(context, on="date", how="left", validate="many_to_one")

    primary_mask = masked["universe_primary_liquid"].astype(bool)
    for source_name, (market_column, output) in _RELATIVE_SOURCE_TO_MARKET.items():
        masked[output] = np.nan
        masked.loc[primary_mask, output] = (
            _finite(masked.loc[primary_mask, source_name])
            - _finite(masked.loc[primary_mask, market_column])
        )

    return masked.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
