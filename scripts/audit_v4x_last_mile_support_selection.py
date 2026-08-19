"""Last-mile read-only audit for already-consumed V4-3R / V4-X evidence.

Attack A measures whether historical IC survives after restricting evaluation to
rows whose ticker history has exact official-session spacing for the rolling
features used by the frozen V4 control representation.

Attack B measures whether future target observability is systematically related
to the already-frozen alpha rank. It cannot recover missing outcomes and does
not claim missing-at-random; it only quantifies selection pressure visible in
score/support identity.

No provider calls, model fitting/scoring, target materialization, or protected
forward outcome access are permitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPECTED_MANIFEST_SHA256 = "05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef"
EXPECTED_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
EXPECTED_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
MODES = ("control", "challenger")
HEADS = ("h5", "h10", "consensus")
HEAD_SPEC = {
    "h5": {
        "alpha": "alpha_h5",
        "state": "target_state_h5",
        "available": "TARGET_H5_AVAILABLE",
        "target": "target_rank_h5",
    },
    "h10": {
        "alpha": "alpha_h10",
        "state": "target_state_h10",
        "available": "TARGET_H10_AVAILABLE",
        "target": "target_rank_h10",
    },
    "consensus": {
        "alpha": "alpha_consensus",
        "state": "target_state_consensus",
        "available": "TARGET_BOTH_AVAILABLE",
        "target": "realized_consensus",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"FROZEN_HASH_MISMATCH:{label}:{actual}!={expected}")
    return actual


def normalize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["ticker"] = (
        out["ticker"]
        .astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )
    out["date"] = (
        pd.to_datetime(out["date"], errors="raise")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    return out


def normalized_rank(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    valid = numeric[np.isfinite(numeric)]
    result = pd.Series(np.nan, index=values.index, dtype=float)
    if not len(valid):
        return result
    if len(valid) == 1:
        result.loc[valid.index] = 0.5
        return result
    ranks = valid.rank(method="average", ascending=True)
    result.loc[valid.index] = (ranks - 1.0) / float(len(valid) - 1)
    return result


def pearson(left: pd.Series, right: pd.Series) -> float | None:
    x = pd.to_numeric(left, errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(right, errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 2 or np.ptp(x) == 0.0 or np.ptp(y) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def finite_mean(values: list[float] | pd.Series) -> float | None:
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    return float(array.mean()) if len(array) else None


def finite_median(values: list[float] | pd.Series) -> float | None:
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    return float(np.median(array)) if len(array) else None


def ks_statistic(left: np.ndarray, right: np.ndarray) -> float | None:
    x = np.sort(np.asarray(left, dtype=float))
    y = np.sort(np.asarray(right, dtype=float))
    x = x[np.isfinite(x)]
    y = y[np.isfinite(y)]
    if not len(x) or not len(y):
        return None
    grid = np.unique(np.concatenate([x, y]))
    cdf_x = np.searchsorted(x, grid, side="right") / float(len(x))
    cdf_y = np.searchsorted(y, grid, side="right") / float(len(y))
    return float(np.max(np.abs(cdf_x - cdf_y)))


def build_exact_support(panel: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    index_by_date = dict(zip(calendar["date"], calendar["session_index"], strict=True))
    work = panel[["ticker", "date"]].copy()
    work["session_index"] = work["date"].map(index_by_date)
    if work["session_index"].isna().any():
        raise RuntimeError("PANEL_DATE_OUTSIDE_FROZEN_CALENDAR")
    work["session_index"] = work["session_index"].astype(int)
    work = work.sort_values(["ticker", "session_index"], kind="mergesort").reset_index(drop=True)
    grouped = work.groupby("ticker", sort=False)["session_index"]

    for lag in (5, 13, 19, 20, 59, 60):
        prior = grouped.shift(lag)
        work[f"exact_shift_{lag}"] = (work["session_index"] - prior).eq(lag)

    # A simple endpoint test matching the earlier 5/20/60 diagnostic.
    work["exact_endpoint_5_20_60"] = (
        work["exact_shift_5"]
        & work["exact_shift_20"]
        & work["exact_shift_60"]
    )
    # Strict semantics for the actual frozen feature formulas:
    # shift(5), shift(20), ATR14 rolling window (13 prior intervals),
    # rolling20 (19 prior intervals), and rolling60 (59 prior intervals).
    work["exact_feature_windows_strict"] = (
        work["exact_shift_5"]
        & work["exact_shift_20"]
        & work["exact_shift_13"]
        & work["exact_shift_19"]
        & work["exact_shift_59"]
    )
    return work[
        [
            "ticker",
            "date",
            "exact_shift_5",
            "exact_shift_20",
            "exact_shift_60",
            "exact_endpoint_5_20_60",
            "exact_feature_windows_strict",
        ]
    ].copy()


def daily_common_support_ic(frame: pd.DataFrame, alpha: str, target: str) -> float | None:
    reranked_alpha = normalized_rank(frame[alpha])
    reranked_target = normalized_rank(frame[target])
    return pearson(reranked_alpha, reranked_target)


def exact_support_attack(
    root: Path,
    mode: str,
    head: str,
    exact_support: pd.DataFrame,
) -> dict[str, Any]:
    spec = HEAD_SPEC[head]
    scores = normalize_identity(pd.read_parquet(root / f"v4_3r_{mode}_validation_scores.parquet"))
    targets = normalize_identity(pd.read_parquet(root / "v4_3r_target_ledger.parquet"))
    metrics = pd.read_csv(root / f"v4_3r_{mode}_{head}_date_metrics.csv")
    metrics["date"] = pd.to_datetime(metrics["date"], errors="raise").dt.normalize()
    fold_by_date = metrics.set_index("date")["fold"].astype(int).to_dict()

    merged = scores[["ticker", "date", spec["alpha"]]].merge(
        targets[["ticker", "date", spec["state"], spec["target"]]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    ).merge(
        exact_support,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    for column in (
        "exact_shift_5",
        "exact_shift_20",
        "exact_shift_60",
        "exact_endpoint_5_20_60",
        "exact_feature_windows_strict",
    ):
        merged[column] = merged[column].fillna(False).astype(bool)

    observable = merged[merged[spec["state"]].eq(spec["available"])].copy()
    filters = {
        "all_common_support": pd.Series(True, index=observable.index),
        "exact_shift_5": observable["exact_shift_5"],
        "exact_shift_5_and_20": observable["exact_shift_5"] & observable["exact_shift_20"],
        "exact_endpoint_5_20_60": observable["exact_endpoint_5_20_60"],
        "exact_feature_windows_strict": observable["exact_feature_windows_strict"],
    }
    output: dict[str, Any] = {}
    for label, mask in filters.items():
        subset = observable.loc[mask].copy()
        daily_rows: list[dict[str, Any]] = []
        for day, block in subset.groupby("date", sort=True):
            ic = daily_common_support_ic(block, spec["alpha"], spec["target"])
            if ic is None:
                continue
            daily_rows.append(
                {
                    "date": pd.Timestamp(day),
                    "fold": int(fold_by_date[pd.Timestamp(day)]),
                    "rows": int(len(block)),
                    "ic": float(ic),
                }
            )
        daily = pd.DataFrame(daily_rows)
        fold_means: list[float] = []
        if not daily.empty:
            fold_means = [
                float(block["ic"].mean())
                for _, block in daily.groupby("fold", sort=True)
            ]
        output[label] = {
            "rows": int(len(subset)),
            "retained_fraction_of_observable_rows": (
                float(len(subset) / len(observable)) if len(observable) else None
            ),
            "dates_with_ic": int(len(daily)),
            "mean_daily_common_support_spearman_ic": (
                float(daily["ic"].mean()) if len(daily) else None
            ),
            "median_fold_mean_common_support_spearman_ic": finite_median(fold_means),
            "positive_fold_count": int(sum(value > 0.0 for value in fold_means)),
            "mean_rows_per_date": float(daily["rows"].mean()) if len(daily) else None,
            "min_rows_per_date": int(daily["rows"].min()) if len(daily) else None,
        }
    baseline = output["all_common_support"]["mean_daily_common_support_spearman_ic"]
    for label, values in output.items():
        current = values["mean_daily_common_support_spearman_ic"]
        values["delta_mean_ic_vs_all_common_support"] = (
            float(current - baseline)
            if current is not None and baseline is not None
            else None
        )
    return output


def observability_selection_attack(root: Path, mode: str, head: str) -> dict[str, Any]:
    spec = HEAD_SPEC[head]
    scores = normalize_identity(pd.read_parquet(root / f"v4_3r_{mode}_validation_scores.parquet"))
    targets = normalize_identity(pd.read_parquet(root / "v4_3r_target_ledger.parquet"))
    merged = scores[["ticker", "date", spec["alpha"]]].merge(
        targets[["ticker", "date", spec["state"]]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    merged["observable"] = merged[spec["state"]].eq(spec["available"])
    merged["alpha_rank"] = merged.groupby("date", sort=False)[spec["alpha"]].transform(normalized_rank)

    daily_rows: list[dict[str, Any]] = []
    for day, block in merged.groupby("date", sort=True):
        valid = block[np.isfinite(pd.to_numeric(block["alpha_rank"], errors="coerce"))].copy()
        obs = valid[valid["observable"]]
        miss = valid[~valid["observable"]]
        if not len(valid) or not len(obs) or not len(miss):
            continue
        ranks = valid["alpha_rank"].to_numpy(dtype=float)
        obs_indicator = valid["observable"].astype(float)
        corr = pearson(pd.Series(ranks), obs_indicator.reset_index(drop=True))
        q10 = valid["alpha_rank"].quantile(0.10)
        q90 = valid["alpha_rank"].quantile(0.90)
        bottom = valid[valid["alpha_rank"].le(q10)]
        top = valid[valid["alpha_rank"].ge(q90)]
        daily_rows.append(
            {
                "date": pd.Timestamp(day),
                "rows": int(len(valid)),
                "observable_rate": float(valid["observable"].mean()),
                "observable_mean_alpha_rank": float(obs["alpha_rank"].mean()),
                "unobservable_mean_alpha_rank": float(miss["alpha_rank"].mean()),
                "observable_minus_unobservable_mean_rank": float(
                    obs["alpha_rank"].mean() - miss["alpha_rank"].mean()
                ),
                "alpha_observability_correlation": corr,
                "ks_observable_vs_unobservable_alpha_rank": ks_statistic(
                    obs["alpha_rank"].to_numpy(dtype=float),
                    miss["alpha_rank"].to_numpy(dtype=float),
                ),
                "top_decile_observable_rate": float(top["observable"].mean()),
                "bottom_decile_observable_rate": float(bottom["observable"].mean()),
            }
        )
    daily = pd.DataFrame(daily_rows)

    pooled_obs = merged.loc[merged["observable"], "alpha_rank"].to_numpy(dtype=float)
    pooled_miss = merged.loc[~merged["observable"], "alpha_rank"].to_numpy(dtype=float)
    state_rows: list[dict[str, Any]] = []
    for state, block in merged.groupby(spec["state"], dropna=False, sort=True):
        rank_values = pd.to_numeric(block["alpha_rank"], errors="coerce")
        finite = rank_values[np.isfinite(rank_values)]
        state_rows.append(
            {
                "state": "<MISSING_STATE>" if pd.isna(state) else str(state),
                "rows": int(len(block)),
                "fraction": float(len(block) / len(merged)) if len(merged) else None,
                "mean_alpha_rank": float(finite.mean()) if len(finite) else None,
            }
        )
    state_rows.sort(key=lambda row: row["rows"], reverse=True)

    return {
        "score_rows": int(len(merged)),
        "observable_rows": int(merged["observable"].sum()),
        "unobservable_rows": int((~merged["observable"]).sum()),
        "overall_observable_rate": float(merged["observable"].mean()) if len(merged) else None,
        "pooled_observable_mean_alpha_rank": finite_mean(pooled_obs),
        "pooled_unobservable_mean_alpha_rank": finite_mean(pooled_miss),
        "pooled_observable_minus_unobservable_mean_rank": (
            float(np.nanmean(pooled_obs) - np.nanmean(pooled_miss))
            if np.isfinite(pooled_obs).any() and np.isfinite(pooled_miss).any()
            else None
        ),
        "pooled_ks_observable_vs_unobservable_alpha_rank": ks_statistic(pooled_obs, pooled_miss),
        "dates_compared": int(len(daily)),
        "mean_daily_observable_minus_unobservable_mean_rank": (
            float(daily["observable_minus_unobservable_mean_rank"].mean()) if len(daily) else None
        ),
        "median_daily_observable_minus_unobservable_mean_rank": (
            float(daily["observable_minus_unobservable_mean_rank"].median()) if len(daily) else None
        ),
        "mean_abs_daily_observable_minus_unobservable_mean_rank": (
            float(daily["observable_minus_unobservable_mean_rank"].abs().mean()) if len(daily) else None
        ),
        "mean_daily_alpha_observability_correlation": (
            finite_mean(daily["alpha_observability_correlation"].dropna()) if len(daily) else None
        ),
        "mean_abs_daily_alpha_observability_correlation": (
            finite_mean(daily["alpha_observability_correlation"].abs().dropna()) if len(daily) else None
        ),
        "mean_daily_ks_observable_vs_unobservable_alpha_rank": (
            finite_mean(daily["ks_observable_vs_unobservable_alpha_rank"].dropna()) if len(daily) else None
        ),
        "mean_top_decile_observable_rate": (
            float(daily["top_decile_observable_rate"].mean()) if len(daily) else None
        ),
        "mean_bottom_decile_observable_rate": (
            float(daily["bottom_decile_observable_rate"].mean()) if len(daily) else None
        ),
        "top_decile_minus_overall_observable_rate": (
            float(daily["top_decile_observable_rate"].mean() - daily["observable_rate"].mean())
            if len(daily) else None
        ),
        "bottom_decile_minus_overall_observable_rate": (
            float(daily["bottom_decile_observable_rate"].mean() - daily["observable_rate"].mean())
            if len(daily) else None
        ),
        "target_state_breakdown": state_rows,
        "note": (
            "This is a selection diagnostic only. Small alpha-rank shifts support, but do not prove, "
            "a weak relationship between score rank and future target observability. Missing outcomes "
            "cannot be reconstructed from this audit."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-result-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.historical_result_root.resolve()
    artifact_root = args.artifact_root.resolve()
    manifest_path = root / "MANIFEST.json"
    panel_path = (
        artifact_root
        / "unknown_state_diagnostic_1260_20260809"
        / "model_safe_signal_research_panel_1260.parquet"
    )
    calendar_path = artifact_root / "official_exchange_sessions_1260.csv"

    manifest_sha = verify(manifest_path, EXPECTED_MANIFEST_SHA256, "historical_manifest")
    panel_sha = verify(panel_path, EXPECTED_PANEL_SHA256, "frozen_panel")
    calendar_sha = verify(calendar_path, EXPECTED_CALENDAR_SHA256, "frozen_calendar")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("protected_forward_accessed") is not False or manifest.get("provider_calls") is not False:
        raise RuntimeError("HISTORICAL_GUARD_CHANGED")

    panel = normalize_identity(pd.read_parquet(panel_path))
    if panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("FROZEN_PANEL_DUPLICATE_IDENTITY")
    calendar = pd.read_csv(calendar_path)
    calendar["date"] = pd.to_datetime(calendar["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)
    calendar["session_index"] = np.arange(len(calendar), dtype=int)
    exact_support = build_exact_support(panel, calendar)

    exact = {
        mode: {
            head: exact_support_attack(root, mode, head, exact_support)
            for head in HEADS
        }
        for mode in MODES
    }
    selection = {
        mode: {
            head: observability_selection_attack(root, mode, head)
            for head in HEADS
        }
        for mode in MODES
    }

    output = {
        "schema_version": "v4x_last_mile_support_selection_audit_v1",
        "status": "V4X_LAST_MILE_SUPPORT_SELECTION_AUDIT_COMPLETE",
        "historical_result_root": str(root),
        "hashes": {
            "historical_manifest": manifest_sha,
            "frozen_panel": panel_sha,
            "frozen_calendar": calendar_sha,
        },
        "provider_calls": False,
        "model_fit": False,
        "model_scored": False,
        "protected_forward_accessed": False,
        "target_materialized": False,
        "attack_a_exact_session_support": exact,
        "attack_b_target_observability_selection": selection,
        "interpretation_boundary": (
            "These diagnostics re-evaluate already-consumed historical scores only. "
            "They must not be used to retune V4-X1 or to claim prospective validation."
        ),
    }
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
