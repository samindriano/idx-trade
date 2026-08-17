from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from .ranking_v4_3_features import V4_CONTROL_FEATURE_COLUMNS
from .ranking_v4_3_preregistration import (
    SESSION_GEOMETRY_FEATURE_COLUMNS,
    equal_date_sample_weights,
    normalized_percentile_rank,
)
from .ranking_v4_3_target_execution import (
    TARGET_BOTH_AVAILABLE,
    TARGET_H10_AVAILABLE,
    TARGET_H5_AVAILABLE,
)


CONTROL = "CONTROL"
CHALLENGER = "CHALLENGER"
MODEL_MODES = {CONTROL, CHALLENGER}
TOP_K = 30
TOP_K_MIN_OBSERVABLE = 27
DATE_TARGET_COVERAGE_GATE = 0.90
MIN_ADMITTED_DATES_PER_FOLD = 90
BOOTSTRAP_BLOCK_LENGTH = 10
BOOTSTRAP_REPLICATIONS = 2000
BOOTSTRAP_SEED = 42


@dataclass(frozen=True)
class HeadSpec:
    name: Literal["H5", "H10", "CONSENSUS"]
    alpha_column: str
    target_state_column: str
    target_available_state: str
    target_rank_column: str
    raw_return_column: str | None


HEAD_SPECS = {
    "H5": HeadSpec(
        name="H5",
        alpha_column="alpha_h5",
        target_state_column="target_state_h5",
        target_available_state=TARGET_H5_AVAILABLE,
        target_rank_column="target_rank_h5",
        raw_return_column="r5",
    ),
    "H10": HeadSpec(
        name="H10",
        alpha_column="alpha_h10",
        target_state_column="target_state_h10",
        target_available_state=TARGET_H10_AVAILABLE,
        target_rank_column="target_rank_h10",
        raw_return_column="r10",
    ),
    "CONSENSUS": HeadSpec(
        name="CONSENSUS",
        alpha_column="alpha_consensus",
        target_state_column="target_state_consensus",
        target_available_state=TARGET_BOTH_AVAILABLE,
        target_rank_column="realized_consensus",
        raw_return_column=None,
    ),
}


def _normalize_dates(series: pd.Series, *, label: str) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if values.isna().any():
        raise ValueError(f"{label} contains invalid dates")
    return values


def model_feature_columns(mode: str) -> tuple[str, ...]:
    normalized = str(mode).upper()
    if normalized == CONTROL:
        return tuple(V4_CONTROL_FEATURE_COLUMNS)
    if normalized == CHALLENGER:
        return (*V4_CONTROL_FEATURE_COLUMNS, *SESSION_GEOMETRY_FEATURE_COLUMNS)
    raise ValueError(f"unsupported V4 model mode: {mode}")


def build_v4_regressor(mode: str) -> Pipeline:
    normalized = str(mode).upper()
    if normalized not in MODEL_MODES:
        raise ValueError(f"unsupported V4 model mode: {mode}")

    control_imputer = SimpleImputer(
        strategy="median",
        add_indicator=True,
        keep_empty_features=True,
    )
    if normalized == CONTROL:
        preprocess = ColumnTransformer(
            [("control", control_imputer, list(V4_CONTROL_FEATURE_COLUMNS))],
            remainder="drop",
        )
    else:
        geometry_imputer = SimpleImputer(
            strategy="median",
            add_indicator=False,
            keep_empty_features=True,
        )
        preprocess = ColumnTransformer(
            [
                ("control", control_imputer, list(V4_CONTROL_FEATURE_COLUMNS)),
                ("geometry", geometry_imputer, list(SESSION_GEOMETRY_FEATURE_COLUMNS)),
            ],
            remainder="drop",
        )

    estimator = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.05,
        max_iter=200,
        max_leaf_nodes=31,
        max_depth=None,
        min_samples_leaf=20,
        l2_regularization=1.0,
        max_bins=255,
        categorical_features=None,
        warm_start=False,
        early_stopping=False,
        random_state=42,
    )
    return Pipeline([("preprocess", preprocess), ("model", estimator)])


def fit_v4_head(
    frame: pd.DataFrame,
    *,
    target_column: str,
    mode: str,
) -> Pipeline:
    required = {"date", target_column, *model_feature_columns(mode)}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"V4 training frame missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("V4 training frame must not be empty")

    target = pd.to_numeric(frame[target_column], errors="coerce").astype(float)
    if target.isna().any() or not np.isfinite(target).all():
        raise ValueError("V4 training target must be fully finite")
    if target.lt(0.0).any() or target.gt(1.0).any():
        raise ValueError("V4 training rank target must be within [0, 1]")

    weights = equal_date_sample_weights(frame["date"])
    model = build_v4_regressor(mode)
    model.fit(
        frame,
        target.to_numpy(dtype=float),
        model__sample_weight=weights.to_numpy(dtype=float),
    )
    return model


def score_v4_head(
    model: Pipeline,
    frame: pd.DataFrame,
    *,
    mode: str,
    raw_score_column: str,
    alpha_column: str,
) -> pd.DataFrame:
    required = {"ticker", "date", *model_feature_columns(mode)}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"V4 scoring frame missing columns: {sorted(missing)}")
    scored = frame.copy()
    scored["date"] = _normalize_dates(scored["date"], label="V4 scoring frame")
    if scored.duplicated(["ticker", "date"]).any():
        raise ValueError("V4 scoring frame contains duplicate identity")
    raw = np.asarray(model.predict(scored), dtype=float)
    if len(raw) != len(scored) or not np.isfinite(raw).all():
        raise RuntimeError("V4 model produced non-finite or misaligned predictions")
    scored[raw_score_column] = raw
    scored[alpha_column] = np.nan
    for _, block in scored.groupby("date", sort=False):
        ranked = normalized_percentile_rank(block[raw_score_column])
        scored.loc[ranked.index, alpha_column] = ranked
    if scored[alpha_column].isna().any():
        raise RuntimeError("within-date V4 prediction rank unexpectedly missing")
    return scored


def attach_consensus_alpha(scored_h5: pd.DataFrame, scored_h10: pd.DataFrame) -> pd.DataFrame:
    required_h5 = {"ticker", "date", "alpha_h5"}
    required_h10 = {"ticker", "date", "alpha_h10"}
    if not required_h5.issubset(scored_h5.columns):
        raise ValueError("H5 scoring table missing identity/alpha")
    if not required_h10.issubset(scored_h10.columns):
        raise ValueError("H10 scoring table missing identity/alpha")
    left = scored_h5[["ticker", "date", "alpha_h5"]].copy()
    right = scored_h10[["ticker", "date", "alpha_h10"]].copy()
    left["date"] = _normalize_dates(left["date"], label="H5 scoring table")
    right["date"] = _normalize_dates(right["date"], label="H10 scoring table")
    merged = left.merge(
        right,
        on=["ticker", "date"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise RuntimeError("H5/H10 scoring populations differ")
    merged = merged.drop(columns="_merge")
    merged["alpha_consensus"] = 0.5 * merged["alpha_h5"] + 0.5 * merged["alpha_h10"]
    return merged


def _rank_correlation(left: pd.Series, right: pd.Series) -> float:
    x = pd.to_numeric(left, errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(right, errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 2 or np.ptp(x) == 0.0 or np.ptp(y) == 0.0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def _fixed_extreme_identities(
    block: pd.DataFrame,
    alpha_column: str,
) -> tuple[set[str], set[str]]:
    if len(block) < 2 * TOP_K:
        return set(), set()
    ordered_top = block.sort_values(
        [alpha_column, "ticker"],
        ascending=[False, True],
        kind="mergesort",
    )
    ordered_bottom = block.sort_values(
        [alpha_column, "ticker"],
        ascending=[True, True],
        kind="mergesort",
    )
    return set(ordered_top.head(TOP_K)["ticker"]), set(ordered_bottom.head(TOP_K)["ticker"])


def evaluate_head_by_date(
    scored_population: pd.DataFrame,
    target_ledger: pd.DataFrame,
    *,
    head: Literal["H5", "H10", "CONSENSUS"],
) -> pd.DataFrame:
    spec = HEAD_SPECS[head]
    score_required = {"ticker", "date", spec.alpha_column}
    target_required = {
        "ticker",
        "date",
        spec.target_state_column,
        spec.target_rank_column,
    }
    if spec.raw_return_column is not None:
        target_required.add(spec.raw_return_column)
    missing_score = score_required - set(scored_population.columns)
    missing_target = target_required - set(target_ledger.columns)
    if missing_score:
        raise ValueError(f"scoring population missing columns: {sorted(missing_score)}")
    if missing_target:
        raise ValueError(f"target ledger missing columns: {sorted(missing_target)}")

    scored = scored_population[list(score_required)].copy()
    scored["ticker"] = scored["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    scored["date"] = _normalize_dates(scored["date"], label="scoring population")
    if scored.duplicated(["ticker", "date"]).any():
        raise ValueError("scoring population contains duplicate identity")
    scored[spec.alpha_column] = pd.to_numeric(scored[spec.alpha_column], errors="coerce")
    if scored[spec.alpha_column].isna().any() or not np.isfinite(scored[spec.alpha_column]).all():
        raise ValueError("scoring population contains missing/non-finite alpha")

    targets = target_ledger[list(target_required)].copy()
    targets["ticker"] = targets["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    targets["date"] = _normalize_dates(targets["date"], label="target ledger")
    if targets.duplicated(["ticker", "date"]).any():
        raise ValueError("target ledger contains duplicate identity")

    rows: list[dict[str, object]] = []
    for day, score_block in scored.groupby("date", sort=True):
        # Top/Bottom identities are fixed before target observability is inspected.
        top_ids, bottom_ids = _fixed_extreme_identities(score_block, spec.alpha_column)
        merged = score_block.merge(
            targets[targets["date"].eq(day)],
            on=["ticker", "date"],
            how="left",
            validate="one_to_one",
        )
        available = merged[spec.target_state_column].eq(spec.target_available_state)
        coverage = float(available.mean()) if len(merged) else np.nan
        coverage_admitted = bool(
            len(merged) >= 2 * TOP_K and coverage >= DATE_TARGET_COVERAGE_GATE
        )

        observable = merged.loc[available].copy()
        top_observable = observable[observable["ticker"].isin(top_ids)]
        bottom_observable = observable[observable["ticker"].isin(bottom_ids)]
        top_ok = len(top_observable) >= TOP_K_MIN_OBSERVABLE
        bottom_ok = len(bottom_observable) >= TOP_K_MIN_OBSERVABLE

        ic = np.nan
        top_mean = np.nan
        spread = np.nan
        if coverage_admitted:
            ic = _rank_correlation(
                observable[spec.alpha_column],
                observable[spec.target_rank_column],
            )
            if top_ok:
                top_mean = float(top_observable[spec.target_rank_column].mean())
            if top_ok and bottom_ok:
                spread = float(
                    top_observable[spec.target_rank_column].mean()
                    - bottom_observable[spec.target_rank_column].mean()
                )

        ic_admitted = bool(coverage_admitted and np.isfinite(ic))
        top_metric_admitted = bool(coverage_admitted and top_ok and np.isfinite(top_mean))
        spread_metric_admitted = bool(
            coverage_admitted and top_ok and bottom_ok and np.isfinite(spread)
        )

        row: dict[str, object] = {
            "date": pd.Timestamp(day),
            "head": head,
            "scored_rows": int(len(merged)),
            "target_observable_rows": int(available.sum()),
            "target_coverage_rate": coverage,
            "date_metric_admitted": coverage_admitted,
            "top30_observable": int(len(top_observable)),
            "bottom30_observable": int(len(bottom_observable)),
            "ic_admitted": ic_admitted,
            "top30_metric_admitted": top_metric_admitted,
            "spread_metric_admitted": spread_metric_admitted,
            "daily_ic": ic if ic_admitted else np.nan,
            "top30_mean_realized_percentile": top_mean if top_metric_admitted else np.nan,
            "top30_bottom30_spread": spread if spread_metric_admitted else np.nan,
        }

        if spec.raw_return_column is not None:
            raw = pd.to_numeric(observable[spec.raw_return_column], errors="coerce")
            top_raw = pd.to_numeric(top_observable[spec.raw_return_column], errors="coerce")
            row.update(
                {
                    "raw_top30_mean_return": float(top_raw.mean()) if top_metric_admitted else np.nan,
                    "raw_universe_mean_return": float(raw.mean()) if coverage_admitted and len(raw) else np.nan,
                    "raw_top30_minus_universe_return": (
                        float(top_raw.mean() - raw.mean())
                        if top_metric_admitted and len(raw)
                        else np.nan
                    ),
                    "raw_top30_median_return": float(top_raw.median()) if top_metric_admitted else np.nan,
                    "raw_top30_fraction_positive": float((top_raw > 0.0).mean()) if top_metric_admitted else np.nan,
                }
            )
        rows.append(row)

    return pd.DataFrame(rows).sort_values("date", kind="mergesort").reset_index(drop=True)


def attach_folds(date_metrics: pd.DataFrame, validation_folds: pd.DataFrame) -> pd.DataFrame:
    required = {"fold", "date"}
    missing = required - set(validation_folds.columns)
    if missing:
        raise ValueError(f"validation fold table missing columns: {sorted(missing)}")
    folds = validation_folds[["fold", "date"]].copy()
    folds["date"] = _normalize_dates(folds["date"], label="validation folds")
    if folds["date"].duplicated().any():
        raise ValueError("validation fold dates must be unique")
    counts = folds["fold"].value_counts().sort_index()
    if len(counts) != 6 or counts.tolist() != [100] * 6:
        raise ValueError("validation folds must contain exactly six folds of 100 dates")

    metrics = date_metrics.copy()
    metrics["date"] = _normalize_dates(metrics["date"], label="date metrics")
    merged = folds.merge(
        metrics,
        on="date",
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise RuntimeError("date metrics do not cover every frozen validation date")
    return merged.drop(columns="_merge").sort_values(
        ["fold", "date"], kind="mergesort"
    ).reset_index(drop=True)


def summarize_fold_metrics(
    fold_metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float | int | bool]]:
    required = {
        "fold",
        "ic_admitted",
        "top30_metric_admitted",
        "spread_metric_admitted",
        "daily_ic",
        "top30_mean_realized_percentile",
        "top30_bottom30_spread",
    }
    missing = required - set(fold_metrics.columns)
    if missing:
        raise ValueError(f"fold metrics missing columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    for fold, block in fold_metrics.groupby("fold", sort=True):
        if len(block) != 100:
            raise ValueError("every validation fold must contain exactly 100 dates")
        ic_mask = block["ic_admitted"].fillna(False).astype(bool)
        top_mask = block["top30_metric_admitted"].fillna(False).astype(bool)
        spread_mask = block["spread_metric_admitted"].fillna(False).astype(bool)
        ic_count = int(ic_mask.sum())
        top_count = int(top_mask.sum())
        spread_count = int(spread_mask.sum())
        ic_valid = ic_count >= MIN_ADMITTED_DATES_PER_FOLD
        top_valid = top_count >= MIN_ADMITTED_DATES_PER_FOLD
        spread_valid = spread_count >= MIN_ADMITTED_DATES_PER_FOLD
        rows.append(
            {
                "fold": int(fold),
                "ic_admitted_dates": ic_count,
                "top30_admitted_dates": top_count,
                "spread_admitted_dates": spread_count,
                "fold_ic_valid": ic_valid,
                "fold_top30_valid": top_valid,
                "fold_spread_valid": spread_valid,
                "fold_all_primary_valid": bool(ic_valid and top_valid and spread_valid),
                "fold_mean_daily_ic": float(block.loc[ic_mask, "daily_ic"].mean()) if ic_valid else np.nan,
                "fold_mean_top30_percentile": float(block.loc[top_mask, "top30_mean_realized_percentile"].mean()) if top_valid else np.nan,
                "fold_mean_top30_bottom30_spread": float(block.loc[spread_mask, "top30_bottom30_spread"].mean()) if spread_valid else np.nan,
            }
        )
    folds = pd.DataFrame(rows).sort_values("fold").reset_index(drop=True)

    def values(column: str, valid_column: str) -> pd.Series:
        return pd.to_numeric(
            folds.loc[folds[valid_column].astype(bool), column], errors="coerce"
        ).dropna()

    ic = values("fold_mean_daily_ic", "fold_ic_valid")
    top = values("fold_mean_top30_percentile", "fold_top30_valid")
    spread = values("fold_mean_top30_bottom30_spread", "fold_spread_valid")
    aggregate: dict[str, float | int | bool] = {
        "all_six_primary_metric_folds_valid": bool(
            len(folds) == 6 and folds["fold_all_primary_valid"].all()
        ),
        "valid_ic_fold_count": int(folds["fold_ic_valid"].sum()),
        "valid_top30_fold_count": int(folds["fold_top30_valid"].sum()),
        "valid_spread_fold_count": int(folds["fold_spread_valid"].sum()),
        "positive_fold_count": int((ic > 0.0).sum()),
        "median_fold_mean_daily_ic": float(ic.median()) if len(ic) else np.nan,
        "q25_fold_mean_daily_ic": float(ic.quantile(0.25, interpolation="linear")) if len(ic) else np.nan,
        "median_fold_top30_mean_realized_percentile": float(top.median()) if len(top) else np.nan,
        "median_fold_top30_bottom30_spread": float(spread.median()) if len(spread) else np.nan,
        "q25_fold_top30_bottom30_spread": float(spread.quantile(0.25, interpolation="linear")) if len(spread) else np.nan,
    }
    return folds, aggregate


def fold_stratified_block_bootstrap_mean(
    fold_metrics: pd.DataFrame,
    *,
    value_column: str = "daily_ic",
    replications: int = BOOTSTRAP_REPLICATIONS,
    seed: int = BOOTSTRAP_SEED,
) -> np.ndarray:
    blocks: dict[int, np.ndarray] = {}
    for fold, frame in fold_metrics.groupby("fold", sort=True):
        ordered = frame.sort_values("date", kind="mergesort")
        if len(ordered) != 100:
            raise ValueError("bootstrap requires exactly 100 dates in every fold")
        values = pd.to_numeric(ordered[value_column], errors="coerce").to_numpy(dtype=float)
        if int(np.isfinite(values).sum()) < MIN_ADMITTED_DATES_PER_FOLD:
            raise ValueError("bootstrap requires at least 90 finite metric dates per fold")
        blocks[int(fold)] = values
    if sorted(blocks) != [1, 2, 3, 4, 5, 6]:
        raise ValueError("bootstrap requires folds 1..6")

    rng = np.random.default_rng(seed)
    out = np.full(replications, np.nan, dtype=float)
    max_start = 100 - BOOTSTRAP_BLOCK_LENGTH
    for replicate in range(replications):
        sampled_parts: list[np.ndarray] = []
        for fold in range(1, 7):
            starts = rng.integers(0, max_start + 1, size=10)
            sampled_parts.extend(
                blocks[fold][start : start + BOOTSTRAP_BLOCK_LENGTH]
                for start in starts
            )
        sampled = np.concatenate(sampled_parts)
        finite = sampled[np.isfinite(sampled)]
        out[replicate] = float(finite.mean()) if len(finite) else np.nan
    return out


def percentile_ci(values: np.ndarray) -> tuple[float, float]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if not len(finite):
        return np.nan, np.nan
    low, high = np.quantile(finite, [0.025, 0.975], method="linear")
    return float(low), float(high)


def paired_date_delta(
    challenger: pd.DataFrame,
    control: pd.DataFrame,
    *,
    metric_columns: tuple[str, ...] = (
        "daily_ic",
        "top30_mean_realized_percentile",
        "top30_bottom30_spread",
    ),
) -> pd.DataFrame:
    required = {"date", "fold", *metric_columns}
    if not required.issubset(challenger.columns) or not required.issubset(control.columns):
        raise ValueError("paired delta inputs are missing metric columns")
    left = challenger[list(required)].copy()
    right = control[list(required)].copy()
    left["date"] = _normalize_dates(left["date"], label="challenger paired metrics")
    right["date"] = _normalize_dates(right["date"], label="control paired metrics")
    merged = left.merge(
        right,
        on=["date", "fold"],
        suffixes=("_challenger", "_control"),
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise RuntimeError("challenger/control metric date support differs")
    merged = merged.drop(columns="_merge")
    for column in metric_columns:
        c = pd.to_numeric(merged[f"{column}_challenger"], errors="coerce")
        b = pd.to_numeric(merged[f"{column}_control"], errors="coerce")
        both = c.notna() & b.notna()
        merged[f"delta_{column}"] = np.where(both, c - b, np.nan)
    return merged.sort_values(["fold", "date"], kind="mergesort").reset_index(drop=True)


def summarize_paired_deltas(
    paired: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float | int | bool]]:
    metric_map = {
        "ic": "delta_daily_ic",
        "top30": "delta_top30_mean_realized_percentile",
        "spread": "delta_top30_bottom30_spread",
    }
    required = {"fold", *metric_map.values()}
    missing = required - set(paired.columns)
    if missing:
        raise ValueError(f"paired delta table missing columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    for fold, block in paired.groupby("fold", sort=True):
        if len(block) != 100:
            raise ValueError("paired delta fold must contain exactly 100 dates")
        row: dict[str, object] = {"fold": int(fold)}
        for label, column in metric_map.items():
            values = pd.to_numeric(block[column], errors="coerce")
            finite = values[np.isfinite(values)]
            count = int(len(finite))
            valid = count >= MIN_ADMITTED_DATES_PER_FOLD
            row[f"{label}_paired_dates"] = count
            row[f"{label}_paired_valid"] = valid
            row[f"fold_mean_{label}_delta"] = float(finite.mean()) if valid else np.nan
        row["fold_all_paired_valid"] = bool(
            row["ic_paired_valid"] and row["top30_paired_valid"] and row["spread_paired_valid"]
        )
        rows.append(row)
    folds = pd.DataFrame(rows).sort_values("fold").reset_index(drop=True)

    def values(label: str) -> pd.Series:
        return pd.to_numeric(
            folds.loc[folds[f"{label}_paired_valid"], f"fold_mean_{label}_delta"],
            errors="coerce",
        ).dropna()

    ic = values("ic")
    top = values("top30")
    spread = values("spread")
    aggregate: dict[str, float | int | bool] = {
        "all_six_paired_metric_folds_valid": bool(
            len(folds) == 6 and folds["fold_all_paired_valid"].all()
        ),
        "positive_fold_ic_delta_count": int((ic > 0.0).sum()),
        "median_fold_mean_ic_delta": float(ic.median()) if len(ic) else np.nan,
        "q25_fold_mean_ic_delta": float(ic.quantile(0.25, interpolation="linear")) if len(ic) else np.nan,
        "median_fold_top30_percentile_delta": float(top.median()) if len(top) else np.nan,
        "median_fold_top30_bottom30_spread_delta": float(spread.median()) if len(spread) else np.nan,
    }
    return folds, aggregate


def evaluate_absolute_viability_gates(
    *,
    head: Literal["H5", "H10", "CONSENSUS"],
    aggregate: dict[str, float | int | bool],
    preregistration: dict[str, object],
    bootstrap_ci: tuple[float, float] | None = None,
) -> dict[str, object]:
    config = preregistration["absolute_viability_gates"]
    key = "head_H5" if head == "H5" else "head_H10" if head == "H10" else "consensus"
    thresholds = config[key]
    gates: dict[str, bool] = {
        "all_six_primary_metric_folds_valid": bool(
            aggregate.get("all_six_primary_metric_folds_valid", False)
        ),
        "median_fold_mean_daily_ic": float(aggregate["median_fold_mean_daily_ic"])
        >= float(thresholds["median_fold_mean_daily_ic_min"]),
        "q25_fold_mean_daily_ic": float(aggregate["q25_fold_mean_daily_ic"])
        >= float(thresholds["q25_fold_mean_daily_ic_min"]),
        "median_fold_top30_mean_realized_percentile": float(
            aggregate["median_fold_top30_mean_realized_percentile"]
        )
        >= float(thresholds["median_fold_top30_mean_realized_percentile_min"]),
        "median_fold_top30_bottom30_spread": float(
            aggregate["median_fold_top30_bottom30_spread"]
        )
        >= float(thresholds["median_fold_top30_bottom30_spread_min"]),
        "positive_fold_count": int(aggregate["positive_fold_count"])
        >= int(thresholds["positive_fold_count_min"]),
    }
    if "q25_fold_top30_bottom30_spread_min" in thresholds:
        gates["q25_fold_top30_bottom30_spread"] = float(
            aggregate["q25_fold_top30_bottom30_spread"]
        ) >= float(thresholds["q25_fold_top30_bottom30_spread_min"])
    if "bootstrap_95pct_lower_mean_daily_ic_strictly_gt" in thresholds:
        lower = np.nan if bootstrap_ci is None else float(bootstrap_ci[0])
        gates["bootstrap_95pct_lower_mean_daily_ic"] = bool(
            np.isfinite(lower)
            and lower > float(thresholds["bootstrap_95pct_lower_mean_daily_ic_strictly_gt"])
        )
    return {"head": head, "gates": gates, "pass": bool(all(gates.values()))}


def evaluate_incremental_promotion_gates(
    *,
    h5_delta: dict[str, float | int | bool],
    h10_delta: dict[str, float | int | bool],
    consensus_delta: dict[str, float | int | bool],
    consensus_bootstrap_delta_ci: tuple[float, float],
    challenger_absolute_pass: bool,
    preregistration: dict[str, object],
) -> dict[str, object]:
    thresholds = preregistration["challenger_incremental_promotion_gates"]
    lower = float(consensus_bootstrap_delta_ci[0])
    gates = {
        "challenger_absolute_pass": bool(challenger_absolute_pass),
        "all_six_h5_paired_metric_folds_valid": bool(
            h5_delta.get("all_six_paired_metric_folds_valid", False)
        ),
        "all_six_h10_paired_metric_folds_valid": bool(
            h10_delta.get("all_six_paired_metric_folds_valid", False)
        ),
        "all_six_consensus_paired_metric_folds_valid": bool(
            consensus_delta.get("all_six_paired_metric_folds_valid", False)
        ),
        "H5_median_fold_mean_ic_delta": float(h5_delta["median_fold_mean_ic_delta"])
        >= float(thresholds["H5_median_fold_mean_ic_delta_min"]),
        "H5_q25_fold_mean_ic_delta": float(h5_delta["q25_fold_mean_ic_delta"])
        >= float(thresholds["H5_q25_fold_mean_ic_delta_min"]),
        "H10_median_fold_mean_ic_delta": float(h10_delta["median_fold_mean_ic_delta"])
        >= float(thresholds["H10_median_fold_mean_ic_delta_min"]),
        "H10_q25_fold_mean_ic_delta": float(h10_delta["q25_fold_mean_ic_delta"])
        >= float(thresholds["H10_q25_fold_mean_ic_delta_min"]),
        "consensus_median_fold_mean_ic_delta": float(
            consensus_delta["median_fold_mean_ic_delta"]
        )
        >= float(thresholds["consensus_median_fold_mean_ic_delta_min"]),
        "consensus_q25_fold_mean_ic_delta": float(consensus_delta["q25_fold_mean_ic_delta"])
        >= float(thresholds["consensus_q25_fold_mean_ic_delta_min"]),
        "consensus_median_fold_top30_percentile_delta": float(
            consensus_delta["median_fold_top30_percentile_delta"]
        )
        >= float(thresholds["consensus_median_fold_top30_percentile_delta_min"]),
        "consensus_median_fold_top30_bottom30_spread_delta": float(
            consensus_delta["median_fold_top30_bottom30_spread_delta"]
        )
        >= float(thresholds["consensus_median_fold_top30_bottom30_spread_delta_min"]),
        "consensus_positive_fold_ic_delta_count": int(
            consensus_delta["positive_fold_ic_delta_count"]
        )
        >= int(thresholds["consensus_positive_fold_ic_delta_count_min"]),
        "consensus_bootstrap_95pct_lower_mean_daily_ic_delta": bool(
            np.isfinite(lower)
            and lower
            > float(
                thresholds[
                    "consensus_bootstrap_95pct_lower_mean_daily_ic_delta_strictly_gt"
                ]
            )
        ),
    }
    return {"gates": gates, "pass": bool(all(gates.values()))}
