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
    model.fit(frame, target.to_numpy(dtype=float), model__sample_weight=weights.to_numpy(dtype=float))
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
    required = {"ticker", "date", "alpha_h5"}
    if not required.issubset(scored_h5.columns):
        raise ValueError("H5 scoring table missing identity/alpha")
    required_h10 = {"ticker", "date", "alpha_h10"}
    if not required_h10.issubset(scored_h10.columns):
        raise ValueError("H10 scoring table missing identity/alpha")
    left = scored_h5[["ticker", "date", "alpha_h5"]].copy()
    right = scored_h10[["ticker", "date", "alpha_h10"]].copy()
    merged = left.merge(right, on=["ticker", "date"], how="outer", validate="one_to_one", indicator=True)
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


def _fixed_extreme_identities(block: pd.DataFrame, alpha_column: str) -> tuple[set[str], set[str]]:
    if len(block) < 2 * TOP_K:
        return set(), set()
    ordered_top = block.sort_values(
        [alpha_column, "ticker"], ascending=[False, True], kind="mergesort"
    )
    ordered_bottom = block.sort_values(
        [alpha_column, "ticker"], ascending=[True, True], kind="mergesort"
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
    if scored.duplicated(["ticker", "date"]).any():
        raise ValueError("scoring population contains duplicate identity")
    if scored[spec.alpha_column].isna().any():
        raise ValueError("scoring population contains missing alpha")

    target_columns = list(target_required)
    targets = target_ledger[target_columns].copy()
    if targets.duplicated(["ticker", "date"]).any():
        raise ValueError("target ledger contains duplicate identity")

    rows: list[dict[str, object]] = []
    for day, score_block in scored.groupby("date", sort=True):
        # Top/Bottom identities are fixed before any future target observability is inspected.
        top_ids, bottom_ids = _fixed_extreme_identities(score_block, spec.alpha_column)
        merged = score_block.merge(
            targets[targets["date"].eq(day)],
            on=["ticker", "date"],
            how="left",
            validate="one_to_one",
        )
        available = merged[spec.target_state_column].eq(spec.target_available_state)
        coverage = float(available.mean()) if len(merged) else np.nan
        coverage_admitted = bool(len(merged) >= 2 * TOP_K and coverage >= DATE_TARGET_COVERAGE_GATE)

        observable = merged.loc[available].copy()
        top_observable = observable[observable["ticker"].isin(top_ids)]
        bottom_observable = observable[observable["ticker"].isin(bottom_ids)]
        top_ok = len(top_observable) >= TOP_K_MIN_OBSERVABLE
        bottom_ok = len(bottom_observable) >= TOP_K_MIN_OBSERVABLE

        ic = np.nan
        top_mean = np.nan
        spread = np.nan
        if coverage_admitted:
            ic = _rank_correlation(observable[spec.alpha_column], observable[spec.target_rank_column])
            if top_ok:
                top_mean = float(top_observable[spec.target_rank_column].mean())
            if top_ok and bottom_ok:
                spread = float(
                    top_observable[spec.target_rank_column].mean()
                    - bottom_observable[spec.target_rank_column].mean()
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
            "daily_ic": ic,
            "top30_mean_realized_percentile": top_mean,
            "top30_bottom30_spread": spread,
        }

        if spec.raw_return_column is not None:
            raw = pd.to_numeric(observable[spec.raw_return_column], errors="coerce")
            top_raw = pd.to_numeric(top_observable[spec.raw_return_column], errors="coerce")
            row.update(
                {
                    "raw_top30_mean_return": float(top_raw.mean()) if coverage_admitted and top_ok else np.nan,
                    "raw_universe_mean_return": float(raw.mean()) if coverage_admitted and len(raw) else np.nan,
                    "raw_top30_minus_universe_return": (
                        float(top_raw.mean() - raw.mean())
                        if coverage_admitted and top_ok and len(raw)
                        else np.nan
                    ),
                    "raw_top30_median_return": float(top_raw.median()) if coverage_admitted and top_ok else np.nan,
                    "raw_top30_fraction_positive": float((top_raw > 0.0).mean()) if coverage_admitted and top_ok else np.nan,
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
    folds["date"] = pd.to_datetime(folds["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if folds["date"].isna().any() or folds["date"].duplicated().any():
        raise ValueError("validation fold dates must be unique and valid")
    counts = folds["fold"].value_counts().sort_index()
    if len(counts) != 6 or counts.tolist() != [100] * 6:
        raise ValueError("validation folds must contain exactly six folds of 100 dates")

    metrics = date_metrics.copy()
    metrics["date"] = pd.to_datetime(metrics["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    merged = folds.merge(metrics, on="date", how="left", validate="one_to_one", indicator=True)
    if not merged["_merge"].eq("both").all():
        raise RuntimeError("date metrics do not cover every frozen validation date")
    return merged.drop(columns="_merge").sort_values(["fold", "date"], kind="mergesort").reset_index(drop=True)


def summarize_fold_metrics(fold_metrics: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float | int]]:
    required = {
        "fold",
        "date_metric_admitted",
        "daily_ic",
        "top30_mean_realized_percentile",
        "top30_bottom30_spread",
    }
    missing = required - set(fold_metrics.columns)
    if missing:
        raise ValueError(f"fold metrics missing columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    for fold, block in fold_metrics.groupby("fold", sort=True):
        admitted = block["date_metric_admitted"].fillna(False).astype(bool)
        admitted_count = int(admitted.sum())
        valid_fold = admitted_count >= MIN_ADMITTED_DATES_PER_FOLD
        rows.append(
            {
                "fold": int(fold),
                "admitted_dates": admitted_count,
                "fold_valid": valid_fold,
                "fold_mean_daily_ic": float(block.loc[admitted, "daily_ic"].mean()) if valid_fold else np.nan,
                "fold_mean_top30_percentile": float(block.loc[admitted, "top30_mean_realized_percentile"].mean()) if valid_fold else np.nan,
                "fold_mean_top30_bottom30_spread": float(block.loc[admitted, "top30_bottom30_spread"].mean()) if valid_fold else np.nan,
            }
        )
    folds = pd.DataFrame(rows).sort_values("fold").reset_index(drop=True)

    def values(column: str) -> pd.Series:
        return pd.to_numeric(folds.loc[folds["fold_valid"], column], errors="coerce").dropna()

    ic = values("fold_mean_daily_ic")
    top = values("fold_mean_top30_percentile")
    spread = values("fold_mean_top30_bottom30_spread")
    aggregate: dict[str, float | int] = {
        "valid_fold_count": int(folds["fold_valid"].sum()),
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
    left_required = {"date", "fold", *metric_columns}
    right_required = {"date", "fold", *metric_columns}
    if not left_required.issubset(challenger.columns) or not right_required.issubset(control.columns):
        raise ValueError("paired delta inputs are missing metric columns")
    merged = challenger[list(left_required)].merge(
        control[list(right_required)],
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
