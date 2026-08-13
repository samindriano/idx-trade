from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from .research_baselines import FoldModelResult
from .research_labels import SL_FIRST, TP_FIRST
from .research_validation import FROZEN_FOLDS


def candidate_counts_by_date(features: pd.DataFrame) -> pd.DataFrame:
    required = {
        "date",
        "ticker",
        "universe_history_qualified",
        "universe_primary_liquid",
        "universe_top100",
        "universe_top300",
    }
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"feature table missing candidate-count columns: {sorted(missing)}")
    frame = features.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    return (
        frame.groupby("date", as_index=False)
        .agg(
            full_valid_rows=("ticker", "size"),
            full_valid_tickers=("ticker", "nunique"),
            history_qualified=("universe_history_qualified", "sum"),
            primary_liquid=("universe_primary_liquid", "sum"),
            top100=("universe_top100", "sum"),
            top300=("universe_top300", "sum"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )


def primary_drop_reason_ledger(features: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    required_features = {"ticker", "date", "universe_primary_liquid"}
    required_labels = {"ticker", "signal_date", "label_status"}
    if not required_features.issubset(features.columns) or not required_labels.issubset(labels.columns):
        raise ValueError("features/labels missing drop-ledger columns")
    left = features[["ticker", "date", "universe_primary_liquid"]].copy()
    left["date"] = pd.to_datetime(left["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    right = labels[["ticker", "signal_date", "label_status"]].copy()
    right["signal_date"] = pd.to_datetime(right["signal_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    joined = left.merge(
        right,
        left_on=["ticker", "date"],
        right_on=["ticker", "signal_date"],
        how="left",
        validate="one_to_one",
    )
    joined["drop_reason"] = "ADMITTED"
    joined.loc[~joined["universe_primary_liquid"].astype(bool), "drop_reason"] = "NOT_PRIMARY_LIQUID_UNIVERSE"
    missing_label = joined["label_status"].isna() & joined["universe_primary_liquid"].astype(bool)
    joined.loc[missing_label, "drop_reason"] = "NO_LABEL_ROW"
    unresolved = (
        joined["universe_primary_liquid"].astype(bool)
        & joined["label_status"].notna()
        & ~joined["label_status"].isin([TP_FIRST, SL_FIRST])
    )
    joined.loc[unresolved, "drop_reason"] = joined.loc[unresolved, "label_status"].astype(str)
    return joined[["ticker", "date", "label_status", "universe_primary_liquid", "drop_reason"]]


def drop_reason_summary(ledger: pd.DataFrame) -> pd.DataFrame:
    if "drop_reason" not in ledger.columns:
        raise ValueError("drop ledger has no drop_reason")
    total = len(ledger)
    summary = ledger["drop_reason"].value_counts(dropna=False).rename_axis("drop_reason").reset_index(name="rows")
    summary["share"] = summary["rows"] / total if total else 0.0
    return summary


def reliability_bins(result: FoldModelResult) -> pd.DataFrame:
    prediction = result.predictions.copy()
    edges = np.asarray(result.calibration_bin_edges, dtype=float)
    probability = pd.to_numeric(prediction["probability"], errors="coerce").to_numpy(dtype=float)
    target = pd.to_numeric(prediction["target"], errors="coerce").to_numpy(dtype=float)
    assignments = np.digitize(probability, edges[1:-1], right=True)
    rows = []
    for bucket in range(len(edges) - 1):
        mask = assignments == bucket
        rows.append(
            {
                "fold": result.fold,
                "model_name": result.model_name,
                "bucket": bucket,
                "lower": float(edges[bucket]),
                "upper": float(edges[bucket + 1]),
                "rows": int(mask.sum()),
                "mean_probability": float(np.mean(probability[mask])) if mask.any() else np.nan,
                "observed_tp_rate": float(np.mean(target[mask])) if mask.any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def pooled_oof_summary(results: Iterable[FoldModelResult]) -> pd.DataFrame:
    result_list = list(results)
    rows = []
    for model_name in sorted({item.model_name for item in result_list}):
        selected = [item for item in result_list if item.model_name == model_name]
        prediction = pd.concat([item.predictions for item in selected], ignore_index=True, sort=False)
        y = pd.to_numeric(prediction["target"], errors="coerce").to_numpy(dtype=int)
        p = pd.to_numeric(prediction["probability"], errors="coerce").to_numpy(dtype=float)
        if np.unique(y).size != 2:
            raise ValueError(f"pooled OOF target for {model_name} does not contain both classes")
        weighted_ece = sum(float(item.metrics["ece"]) * float(item.metrics["rows"]) for item in selected) / sum(
            float(item.metrics["rows"]) for item in selected
        )
        rows.append(
            {
                "model_name": model_name,
                "rows": int(len(y)),
                "pr_auc": float(average_precision_score(y, p)),
                "roc_auc": float(roc_auc_score(y, p)),
                "brier": float(brier_score_loss(y, p)),
                "weighted_mean_fold_ece": float(weighted_ece),
                "positive_rate": float(np.mean(y)),
                "prediction_mean": float(np.mean(p)),
                "folds": ",".join(item.fold for item in selected),
            }
        )
    return pd.DataFrame(rows).sort_values("model_name").reset_index(drop=True)


def excursion_summary(features: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    feature_keys = features[["ticker", "date", "universe_primary_liquid"]].copy()
    feature_keys["date"] = pd.to_datetime(feature_keys["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    label = labels.copy()
    label["signal_date"] = pd.to_datetime(label["signal_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    joined = feature_keys.merge(
        label,
        left_on=["ticker", "date"],
        right_on=["ticker", "signal_date"],
        how="inner",
        validate="one_to_one",
    )
    joined = joined[joined["universe_primary_liquid"].astype(bool) & joined["path_complete"].astype(bool)].copy()
    rows = []
    for status, block in joined.groupby("label_status", dropna=False):
        row = {"label_status": str(status), "rows": int(len(block))}
        for column in ("mfe_h", "mae_h", "normalized_close_return_h", "research_r_h"):
            values = pd.to_numeric(block[column], errors="coerce").dropna()
            row[f"{column}_mean"] = float(values.mean()) if len(values) else np.nan
            row[f"{column}_median"] = float(values.median()) if len(values) else np.nan
            row[f"{column}_p10"] = float(values.quantile(0.10)) if len(values) else np.nan
            row[f"{column}_p90"] = float(values.quantile(0.90)) if len(values) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("label_status").reset_index(drop=True)


def fold_boundary_audit(calendar: pd.DatetimeIndex) -> list[dict[str, object]]:
    rows = []
    for fold in FROZEN_FOLDS:
        rows.append(
            {
                "fold": fold.name,
                "train_start_index": fold.train_start,
                "train_end_index": fold.train_end,
                "train_start_date": pd.Timestamp(calendar[fold.train_start - 1]).date().isoformat(),
                "train_end_date": pd.Timestamp(calendar[fold.train_end - 1]).date().isoformat(),
                "gap_start_index": fold.gap_start,
                "gap_end_index": fold.gap_end,
                "gap_sessions": fold.gap_end - fold.gap_start + 1,
                "validation_start_index": fold.validation_start,
                "validation_end_index": fold.validation_end,
                "validation_start_date": pd.Timestamp(calendar[fold.validation_start - 1]).date().isoformat(),
                "validation_end_date": pd.Timestamp(calendar[fold.validation_end - 1]).date().isoformat(),
                "training_path_overlap_validation": bool(fold.train_end + 20 >= fold.validation_start),
            }
        )
    return rows
