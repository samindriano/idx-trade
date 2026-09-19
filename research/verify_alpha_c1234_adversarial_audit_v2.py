"""Independent, fail-closed replay verifier for the C1/C2/C4 audit artifact.

This verifier deliberately does not import the audit builder. It reopens the
same outcome-blind inputs, recomputes the structural checks and provenance
hashes, and compares them with the staged JSON artifact. Access flags in the
artifact remain self-attested; this tool does not claim to prove process-level
absence of protected access.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
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
EXPECTED_STAGE = "Q_J_OUTCOME_BLIND_C1234_ADVERSARIAL_AUDIT"
EXPECTED_TOP_KEYS = {
    "candidate_checks",
    "candidate_id_created",
    "candidate_support",
    "checks",
    "code_sha256",
    "identity_summary",
    "implementation",
    "incumbent_score_accessed",
    "interpretation",
    "listing_age_exposure",
    "outcome_accessed",
    "provider_accessed",
    "source_hashes",
    "stage",
    "status",
    "target_accessed",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        "rank_is_cross_sectional": '.groupby("date"' in text and ".rank(" in text,
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
        selected_rows.append(eligible[(eligible["date"] == date) & eligible["ticker"].isin(tickers)])
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


def recompute(
    implementation_path: Path,
    features_path: Path,
    panel_path: Path,
    sessions_path: Path,
    security_master_path: Path,
) -> dict[str, object]:
    features = pd.read_parquet(features_path)
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    panel = pd.read_parquet(panel_path, columns=["ticker", "date"])
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    sessions = pd.read_csv(sessions_path, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.sort_values("date", kind="mergesort").reset_index(drop=True)
    master = pd.read_csv(security_master_path)
    master["ticker"] = master["ticker"].astype(str)
    master["listed_from"] = pd.to_datetime(master["listed_from"], errors="coerce").dt.normalize()
    master["listed_to"] = pd.to_datetime(master["listed_to"], errors="coerce").dt.normalize()

    implementation = source_checks(implementation_path)
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
    eligible_keys = set(zip(features.loc[eligible, "ticker"].astype(str), features.loc[eligible, "date"]))
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
        "implementation_static_checks_all_pass": all(implementation["checks"].values()),
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

    return {
        "implementation": implementation,
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
        "checks": checks,
        "source_hashes": {
            "implementation": sha256_file(implementation_path),
            "features": sha256_file(features_path),
            "panel": sha256_file(panel_path),
            "official_sessions": sha256_file(sessions_path),
            "security_master": sha256_file(security_master_path),
        },
    }


def equal_value(left: object, right: object) -> bool:
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(equal_value(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equal_value(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-15)
    return left == right


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--audit-code", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    artifact = json.loads(args.input.read_text(encoding="utf-8"))
    recomputed = recompute(
        args.implementation,
        args.features,
        args.panel,
        args.sessions,
        args.security_master,
    )
    checks: dict[str, bool] = {
        "artifact_top_schema_exact": set(artifact) == EXPECTED_TOP_KEYS,
        "stage_exact": artifact.get("stage") == EXPECTED_STAGE,
        "status_exact": artifact.get("status") == "PASS_STRUCTURAL_ONLY",
        "access_flags_false_attested": all(
            artifact.get(key) is False
            for key in ("outcome_accessed", "provider_accessed", "target_accessed", "incumbent_score_accessed", "candidate_id_created")
        ),
        "interpretation_scope_explicit": artifact.get("interpretation") == {
            "corporate_action_basis_certified": False,
            "historical_pit_certified": False,
            "no_predictive_claim": True,
            "scope": "adversarial structural checks only",
        },
        "implementation_envelope_recomputed": equal_value(artifact.get("implementation"), recomputed["implementation"]),
        "candidate_checks_recomputed": equal_value(artifact.get("candidate_checks"), recomputed["candidate_checks"]),
        "candidate_support_recomputed": equal_value(artifact.get("candidate_support"), recomputed["candidate_support"]),
        "listing_age_recomputed": equal_value(artifact.get("listing_age_exposure"), recomputed["listing_age_exposure"]),
        "identity_summary_recomputed": equal_value(artifact.get("identity_summary"), recomputed["identity_summary"]),
        "structural_checks_recomputed": equal_value(artifact.get("checks"), recomputed["checks"]),
        "source_hashes_recomputed": equal_value(artifact.get("source_hashes"), recomputed["source_hashes"]),
        "audit_code_hash_recomputed": artifact.get("code_sha256") == sha256_file(args.audit_code),
        "candidate_keys_exact": set(artifact.get("candidate_checks", {})) == set(CANDIDATES),
        "candidate_maps_nonempty": all(artifact.get(key) for key in ("candidate_checks", "candidate_support", "listing_age_exposure")),
    }
    status = "PASS_INDEPENDENT_STRUCTURAL_REPLAY" if all(checks.values()) else "FAIL_INDEPENDENT_STRUCTURAL_REPLAY"
    output = {
        "status": status,
        "stage": "Q_J_INDEPENDENT_STRUCTURAL_REPLAY_V2",
        "checks": checks,
        "artifact": str(args.input),
        "inputs": {
            "audit_code": str(args.audit_code),
            "implementation": str(args.implementation),
            "features": str(args.features),
            "panel": str(args.panel),
            "sessions": str(args.sessions),
            "security_master": str(args.security_master),
        },
        "verifier_code_sha256": sha256_file(Path(__file__)),
        "access_flags_note": "Artifact access flags are self-attested and are not process-level execution proof.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    if status != "PASS_INDEPENDENT_STRUCTURAL_REPLAY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
