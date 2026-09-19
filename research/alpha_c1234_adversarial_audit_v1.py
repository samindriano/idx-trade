"""Adversarial, outcome-blind audit of the corrected C1/C2/C4 construction.

This is intentionally different from the structural metrics and regular
verifiers: it attacks causal-code assumptions, output/mask leakage, calendar
closure, identity interval coverage, and listing-age concentration. It does
not read targets, returns, incumbent scores, providers, or network data.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


CANDIDATES = {
    "C1": "C1_residual_reversal_5_v1",
    "C2": "C2_participation_confirmation_5_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}
RANK_COLUMNS = {label: f"rank_{column}" for label, column in CANDIDATES.items()}
STATIC_REQUIRED_TOKENS = (
    "ret_5",
    "ret_20",
    "turnover_mean_5",
    "turnover_median_60",
    "abs_ret_sum_20",
    "beta_60_prior",
    "shift(1)",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bool_value(value: object) -> bool:
    return bool(value)


def finite_float(value: object) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if np.isfinite(converted) else None


def source_checks(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    ast.parse(text)
    lower = text.lower()
    checks = {
        "ast_parse": True,
        "no_negative_shift": "shift(-" not in lower,
        "no_backward_fill": not bool(re.search(r"\b(?:bfill|ffill)\b", lower)),
        "no_network_import": not bool(
            re.search(r"(?:^|\n)\s*(?:import|from)\s+(?:requests|urllib|httpx|socket|boto3)\b", text)
        ),
        "no_http_call": not bool(re.search(r"(?:requests\.|urllib\.|httpx\.|socket\.|boto3\.)", text)),
        "required_causal_tokens": all(token in text for token in STATIC_REQUIRED_TOKENS),
        "rank_is_cross_sectional": ".groupby(\"date\"" in text and ".rank(" in text,
    }
    return {"path": str(path), "sha256": sha256_file(path), "checks": checks}


def top_selection(frame: pd.DataFrame, score_column: str, top_k: int = 30) -> dict[pd.Timestamp, set[str]]:
    eligible = frame["eligible_decision_universe"].astype(bool)
    score = pd.to_numeric(frame[score_column], errors="coerce")
    valid = eligible & score.notna() & np.isfinite(score)
    rows = frame.loc[valid, ["ticker", "date", score_column]].copy()
    result: dict[pd.Timestamp, set[str]] = {}
    for date, group in rows.groupby("date", sort=True):
        selected = group.sort_values(
            [score_column, "ticker"], ascending=[False, True], kind="mergesort"
        ).head(top_k)
        if len(selected) == top_k:
            result[pd.Timestamp(date)] = set(selected["ticker"].astype(str))
    return result


def listing_age_exposure(
    features: pd.DataFrame,
    master: pd.DataFrame,
    label: str,
) -> dict[str, object]:
    eligible = features[features["eligible_decision_universe"].astype(bool)].copy()
    eligible = eligible.merge(master, on="ticker", how="left", validate="many_to_one")
    eligible["listing_age_days"] = (eligible["date"] - eligible["listed_from"]).dt.days
    selected_sets = top_selection(features, CANDIDATES[label])
    selected_rows: list[pd.DataFrame] = []
    for date, tickers in selected_sets.items():
        group = eligible[(eligible["date"] == date) & eligible["ticker"].isin(tickers)]
        selected_rows.append(group)
    selected = pd.concat(selected_rows, ignore_index=True) if selected_rows else eligible.iloc[0:0]
    return {
        "eligible_rows": int(len(eligible)),
        "selected_rows": int(len(selected)),
        "eligible_mapped_listed_from_share": finite_float(eligible["listed_from"].notna().mean()),
        "selected_mapped_listed_from_share": finite_float(selected["listed_from"].notna().mean()),
        "eligible_le_60d_share": finite_float((eligible["listing_age_days"] <= 60).mean()),
        "selected_le_60d_share": finite_float((selected["listing_age_days"] <= 60).mean()),
        "eligible_le_365d_share": finite_float((eligible["listing_age_days"] <= 365).mean()),
        "selected_le_365d_share": finite_float((selected["listing_age_days"] <= 365).mean()),
        "top30_dates": int(len(selected_sets)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    features = pd.read_parquet(args.features)
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    panel = pd.read_parquet(args.panel, columns=["ticker", "date"])
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.sort_values("date", kind="mergesort").reset_index(drop=True)
    master = pd.read_csv(args.security_master)
    master["ticker"] = master["ticker"].astype(str)
    master["listed_from"] = pd.to_datetime(master["listed_from"], errors="coerce").dt.normalize()
    master["listed_to"] = pd.to_datetime(master["listed_to"], errors="coerce").dt.normalize()

    source = source_checks(args.implementation)
    source_checks_map = source["checks"]
    feature_columns = set(features.columns)
    score_columns = set(CANDIDATES.values())
    rank_columns = set(RANK_COLUMNS.values())
    eligible = features["eligible_decision_universe"].astype(bool)
    candidate_checks: dict[str, dict[str, object]] = {}
    candidate_support: dict[str, dict[str, object]] = {}
    listing_age: dict[str, dict[str, object]] = {}
    for label, score_column in CANDIDATES.items():
        score = pd.to_numeric(features[score_column], errors="coerce")
        rank = pd.to_numeric(features[RANK_COLUMNS[label]], errors="coerce")
        finite_score = score.notna() & np.isfinite(score)
        finite_rank = rank.notna() & np.isfinite(rank)
        candidate_checks[label] = {
            "score_outside_eligibility_count": int((finite_score & ~eligible).sum()),
            "rank_outside_eligibility_count": int((finite_rank & ~eligible).sum()),
            "rank_below_zero_count": int((rank < 0).fillna(False).sum()),
            "rank_above_one_count": int((rank > 1).fillna(False).sum()),
            "score_inf_count": int(np.isinf(score).sum()),
            "rank_inf_count": int(np.isinf(rank).sum()),
            "finite_eligible_rows": int((finite_score & eligible).sum()),
        }
        candidate_support[label] = {
            "finite_eligible_dates": int(features.loc[finite_score & eligible, "date"].nunique()),
            "finite_eligible_tickers": int(features.loc[finite_score & eligible, "ticker"].nunique()),
        }
        listing_age[label] = listing_age_exposure(features, master, label)

    session_set = set(sessions["date"])
    session_index = {date: index for index, date in enumerate(sessions["date"])}
    panel_keys = set(zip(panel["ticker"].astype(str), panel["date"]))
    feature_keys = set(zip(features["ticker"].astype(str), features["date"]))
    eligible_keys = set(
        zip(
            features.loc[eligible, "ticker"].astype(str),
            features.loc[eligible, "date"],
        )
    )
    features_sorted = features.sort_values(["ticker", "date"], kind="mergesort")
    per_ticker_dates = features_sorted.groupby("ticker", sort=False)["date"].apply(
        lambda series: all(series.map(session_index).diff().dropna().ge(1))
    )
    master_unique = not master["ticker"].duplicated().any()
    eligible_master = features.loc[eligible, ["ticker", "date"]].merge(
        master[["ticker", "listed_from", "listed_to"]],
        on="ticker",
        how="left",
        validate="many_to_one",
    )
    active_identity = (
        eligible_master["listed_from"].notna()
        & eligible_master["date"].ge(eligible_master["listed_from"])
        & (eligible_master["listed_to"].isna() | eligible_master["date"].le(eligible_master["listed_to"]))
    )
    checks = {
        "implementation_static_checks_all_pass": all(source_checks_map.values()),
        "feature_schema_has_exact_candidate_scores": score_columns.issubset(feature_columns),
        "feature_schema_has_exact_candidate_ranks": rank_columns.issubset(feature_columns),
        "feature_no_target_like_column": not any(
            re.search(r"(?:target|label|forward|outcome|pnl|nav|sharpe)", column, re.IGNORECASE)
            for column in feature_columns
        ),
        "feature_rows_equal_panel_rows": len(features) == len(panel),
        "feature_keys_equal_panel_keys": feature_keys == panel_keys,
        "feature_duplicate_keys": not features.duplicated(["ticker", "date"]).any(),
        "panel_duplicate_keys": not panel.duplicated(["ticker", "date"]).any(),
        "all_feature_dates_official": set(features["date"]).issubset(session_set),
        "per_ticker_feature_dates_forward_ordered": bool(per_ticker_dates.all()),
        "master_tickers_unique": master_unique,
        "eligible_keys_have_one_active_identity": bool(active_identity.all()),
        "eligible_keys_have_no_unmapped_identity": int(eligible_master["listed_from"].isna().sum()) == 0,
        "eligible_keys_equal_panel_subset": eligible_keys.issubset(panel_keys),
    }
    for label, values in candidate_checks.items():
        checks[f"{label}_score_mask_closed"] = values["score_outside_eligibility_count"] == 0
        checks[f"{label}_rank_mask_closed"] = values["rank_outside_eligibility_count"] == 0
        checks[f"{label}_rank_bounds"] = values["rank_below_zero_count"] == 0 and values["rank_above_one_count"] == 0
        checks[f"{label}_finite_eligible_support"] = values["finite_eligible_rows"] > 0

    result = {
        "status": "PASS_STRUCTURAL_ONLY" if all(checks.values()) else "FAIL_STRUCTURAL_AUDIT",
        "stage": "Q_J_OUTCOME_BLIND_C1234_ADVERSARIAL_AUDIT",
        "outcome_accessed": False,
        "provider_accessed": False,
        "target_accessed": False,
        "incumbent_score_accessed": False,
        "candidate_id_created": False,
        "checks": checks,
        "implementation": source,
        "candidate_checks": candidate_checks,
        "candidate_support": candidate_support,
        "listing_age_exposure": listing_age,
        "identity_summary": {
            "master_rows": int(len(master)),
            "master_unique_tickers": int(master["ticker"].nunique()),
            "eligible_rows": int(eligible.sum()),
            "eligible_active_identity_rows": int(active_identity.sum()),
            "eligible_unmapped_rows": int(eligible_master["listed_from"].isna().sum()),
        },
        "source_hashes": {
            "implementation": sha256_file(args.implementation),
            "features": sha256_file(args.features),
            "panel": sha256_file(args.panel),
            "official_sessions": sha256_file(args.sessions),
            "security_master": sha256_file(args.security_master),
        },
        "code_sha256": sha256_file(Path(__file__)),
        "interpretation": {
            "scope": "adversarial structural checks only",
            "no_predictive_claim": True,
            "corporate_action_basis_certified": False,
            "historical_pit_certified": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS_STRUCTURAL_ONLY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
