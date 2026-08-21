from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any

import pandas as pd

from .decision_v3_failure_diagnosis import DecisionV3FailureDiagnosisError
from .decision_v3_structural_source import canonical_json_sha256, sha256_file

CONTRACT_RELATIVE_PATH = Path(
    "docs/specs/decision_v3_a_admission_mechanism_diagnosis_v1.json"
)
EXPECTED_CONTRACT_CANONICAL_SHA256 = (
    "5add7fb9b18ace3347aff24025f49425ab8ee8fc08c7b34610491b477bc0c4ed"
)
EXPECTED_PARENT_MANIFEST_SHA256 = (
    "bb2b38696d83629ace4a50609eb042e42951086fda27c7d9f39ad50f25f87902"
)
EXPECTED_PARENT_STATUS = "COMPLETE_OUTCOME_BLIND_DECISION_V3_A_SAME_SESSION_DIAGNOSIS"
EXPECTED_COUNTS = {"A_SOFT": 204, "A_VACANCY": 223}
EXPECTED_PAIRED_SESSIONS = 151

REQUIRED_COLUMNS = {
    "ticker",
    "entry_index",
    "entry_date",
    "entry_class",
    "current_rank",
    "previous_rank",
    "rank_delta_current_minus_previous",
    "rank_t_minus_2",
    "rank_t_minus_3",
    "top10_run_including_entry",
    "top20_run_including_entry",
    "last3_top10_count",
    "last3_top20_count",
    "soft_rank_gap",
    "duration_sessions",
    "one_session_holding",
    "completed",
    "right_censored",
    "eventual_severe_exit",
    "next_session_observable",
    "next_session_severe_exit",
    "current_rank_bucket",
    "previous_rank_bucket",
    "top10_run_bucket",
    "top20_run_bucket",
}

EVIDENCE_COLUMNS = (
    "current_rank",
    "previous_rank",
    "rank_delta_current_minus_previous",
    "rank_t_minus_2",
    "rank_t_minus_3",
    "top10_run_including_entry",
    "top20_run_including_entry",
    "last3_top10_count",
    "last3_top20_count",
)

STRATA = {
    "current_rank": ("current_rank_bucket", ("1-3", "4-6", "7-10")),
    "previous_rank": ("previous_rank_bucket", ("1-10", "11-20")),
    "top10_run_including_entry": ("top10_run_bucket", ("1", "2", ">=3")),
    "top20_run_including_entry": ("top20_run_bucket", ("1", "2", ">=3")),
}


@dataclass(frozen=True)
class AdmissionMechanismDiagnosisResult:
    summary: dict[str, Any]
    a_soft_gap_rows: pd.DataFrame
    stratified_gap_outcomes: pd.DataFrame
    within_session_gap_concordance: pd.DataFrame


def verify_admission_mechanism_contract(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser().resolve() / CONTRACT_RELATIVE_PATH
    if not path.is_file():
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_CONTRACT_MISSING")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_CONTRACT_INVALID_JSON") from exc
    if not isinstance(payload, dict):
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_CONTRACT_NOT_OBJECT")
    actual = canonical_json_sha256(payload)
    if actual != EXPECTED_CONTRACT_CANONICAL_SHA256:
        raise DecisionV3FailureDiagnosisError(
            f"A_ADMISSION_CONTRACT_SHA_CHANGED:{actual}!={EXPECTED_CONTRACT_CANONICAL_SHA256}"
        )
    if payload.get("status") != "FROZEN_BEFORE_EXECUTION":
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_CONTRACT_STATUS_CHANGED")
    if payload.get("execution_authorized") is not False:
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_CONTRACT_EXECUTION_FLAG_CHANGED")
    forbidden = payload.get("forbidden", {})
    if not forbidden or not all(value is True for value in forbidden.values()):
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_CONTRACT_FORBIDDEN_GUARD_CHANGED")
    if not str(payload.get("stop_rule", "")).startswith("After this diagnosis is consumed"):
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_CONTRACT_STOP_RULE_CHANGED")
    return path


def _normalize_bool(series: pd.Series, name: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    mapped = series.astype(str).str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    if mapped.isna().any():
        bad = sorted(series.loc[mapped.isna()].astype(str).unique().tolist())[:5]
        raise DecisionV3FailureDiagnosisError(
            f"A_ADMISSION_BOOL_PARSE_FAILED:{name}:{bad}"
        )
    return mapped.astype(bool)


def _normalize_optional_bool(series: pd.Series, name: str) -> pd.Series:
    raw = series.astype(str).str.strip().str.lower()
    mapped = raw.map(
        {
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "nan": None,
            "": None,
            "none": None,
        }
    )
    invalid = mapped.isna() & ~raw.isin(("nan", "", "none"))
    if invalid.any():
        bad = sorted(series.loc[invalid].astype(str).unique().tolist())[:5]
        raise DecisionV3FailureDiagnosisError(
            f"A_ADMISSION_OPTIONAL_BOOL_PARSE_FAILED:{name}:{bad}"
        )
    return mapped


def load_same_session_parent(parent_root: str | Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    root = Path(parent_root).expanduser().resolve()
    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_PARENT_MANIFEST_MISSING")
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != EXPECTED_PARENT_MANIFEST_SHA256:
        raise DecisionV3FailureDiagnosisError(
            f"A_ADMISSION_PARENT_MANIFEST_SHA_CHANGED:{actual_manifest_sha}!={EXPECTED_PARENT_MANIFEST_SHA256}"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_PARENT_MANIFEST_INVALID_JSON") from exc
    if manifest.get("status") != EXPECTED_PARENT_STATUS:
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_PARENT_STATUS_CHANGED")
    boundary = manifest.get("scientific_boundary")
    if not isinstance(boundary, dict) or any(bool(v) for v in boundary.values()):
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_PARENT_BOUNDARY_CHANGED")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or "paired_entries.csv" not in artifacts:
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_PARENT_ARTIFACT_PIN_MISSING")

    csv_path = root / "paired_entries.csv"
    if not csv_path.is_file():
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_PARENT_ENTRIES_MISSING")
    actual_csv_sha = sha256_file(csv_path)
    if actual_csv_sha != artifacts["paired_entries.csv"]:
        raise DecisionV3FailureDiagnosisError(
            f"A_ADMISSION_PARENT_ENTRIES_SHA_CHANGED:{actual_csv_sha}!={artifacts['paired_entries.csv']}"
        )
    frame = pd.read_csv(csv_path)
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise DecisionV3FailureDiagnosisError(
            f"A_ADMISSION_PARENT_COLUMNS_MISSING:{missing}"
        )
    actual_counts = frame["entry_class"].value_counts().to_dict()
    if actual_counts != EXPECTED_COUNTS:
        raise DecisionV3FailureDiagnosisError(
            f"A_ADMISSION_PARENT_COUNTS_CHANGED:{actual_counts}!={EXPECTED_COUNTS}"
        )
    sessions = int(frame["entry_index"].nunique())
    if sessions != EXPECTED_PAIRED_SESSIONS:
        raise DecisionV3FailureDiagnosisError(
            f"A_ADMISSION_PARENT_SESSION_COUNT_CHANGED:{sessions}!={EXPECTED_PAIRED_SESSIONS}"
        )
    for column in (
        "one_session_holding",
        "completed",
        "right_censored",
        "next_session_observable",
    ):
        frame[column] = _normalize_bool(frame[column], column)
    for column in ("eventual_severe_exit", "next_session_severe_exit"):
        frame[column] = _normalize_optional_bool(frame[column], column)
    return frame, manifest


def _numeric_summary(series: pd.Series) -> dict[str, float | int | None]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if values.empty:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
            "p90": None,
        }
    return {
        "count": int(values.size),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "p25": float(values.quantile(0.25)),
        "p75": float(values.quantile(0.75)),
        "p90": float(values.quantile(0.90)),
    }


def _spearman(x: pd.Series, y: pd.Series) -> float | None:
    pair = pd.DataFrame(
        {
            "x": pd.to_numeric(x, errors="coerce"),
            "y": pd.to_numeric(y, errors="coerce"),
        }
    ).dropna()
    if len(pair) < 2 or pair["x"].nunique() < 2 or pair["y"].nunique() < 2:
        return None
    value = pair["x"].corr(pair["y"], method="spearman")
    return None if pd.isna(value) else float(value)


def _conditional_gap_summary(
    frame: pd.DataFrame, outcome_column: str
) -> dict[str, Any]:
    observed = frame.dropna(subset=[outcome_column]).copy()
    observed[outcome_column] = observed[outcome_column].astype(bool)
    negative = observed.loc[~observed[outcome_column], "soft_rank_gap"]
    positive = observed.loc[observed[outcome_column], "soft_rank_gap"]
    neg = _numeric_summary(negative)
    pos = _numeric_summary(positive)
    return {
        "nonsevere": neg,
        "severe": pos,
        "severe_minus_nonsevere_mean_gap": (
            None
            if pos["mean"] is None or neg["mean"] is None
            else float(pos["mean"] - neg["mean"])
        ),
        "severe_minus_nonsevere_median_gap": (
            None
            if pos["median"] is None or neg["median"] is None
            else float(pos["median"] - neg["median"])
        ),
    }


def _candidate_evidence_by_next_state(soft: pd.DataFrame) -> dict[str, Any]:
    observed = soft.loc[soft["next_session_observable"]].dropna(
        subset=["next_session_severe_exit"]
    )
    severe = observed.loc[observed["next_session_severe_exit"].astype(bool)]
    nonsevere = observed.loc[~observed["next_session_severe_exit"].astype(bool)]
    result: dict[str, Any] = {}
    for column in EVIDENCE_COLUMNS:
        sev = _numeric_summary(severe[column])
        non = _numeric_summary(nonsevere[column])
        result[column] = {
            "severe": sev,
            "nonsevere": non,
            "severe_minus_nonsevere_mean": (
                None
                if sev["mean"] is None or non["mean"] is None
                else float(sev["mean"] - non["mean"])
            ),
            "severe_minus_nonsevere_median": (
                None
                if sev["median"] is None or non["median"] is None
                else float(sev["median"] - non["median"])
            ),
        }
    return result


def _build_stratified_gap_outcomes(soft: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dimension, (column, ordered_values) in STRATA.items():
        labels = soft[column].astype(str)
        for stratum in ordered_values:
            block = soft.loc[labels.eq(stratum)]
            next_obs = block.loc[block["next_session_observable"]].dropna(
                subset=["next_session_severe_exit"]
            )
            completed = block.loc[block["completed"]].dropna(
                subset=["eventual_severe_exit"]
            )
            next_conditional = _conditional_gap_summary(
                next_obs, "next_session_severe_exit"
            )
            eventual_conditional = _conditional_gap_summary(
                completed, "eventual_severe_exit"
            )
            rows.append(
                {
                    "dimension": dimension,
                    "stratum": stratum,
                    "entries": int(len(block)),
                    "next_observable": int(len(next_obs)),
                    "next_severe": int(
                        next_obs["next_session_severe_exit"].astype(bool).sum()
                    ),
                    "next_nonsevere": int(
                        (~next_obs["next_session_severe_exit"].astype(bool)).sum()
                    ),
                    "next_spearman_gap_vs_severe": _spearman(
                        next_obs["soft_rank_gap"],
                        next_obs["next_session_severe_exit"].astype(int),
                    ),
                    "next_severe_minus_nonsevere_mean_gap": next_conditional[
                        "severe_minus_nonsevere_mean_gap"
                    ],
                    "completed": int(len(completed)),
                    "eventual_severe": int(
                        completed["eventual_severe_exit"].astype(bool).sum()
                    ),
                    "eventual_nonsevere": int(
                        (~completed["eventual_severe_exit"].astype(bool)).sum()
                    ),
                    "eventual_spearman_gap_vs_severe": _spearman(
                        completed["soft_rank_gap"],
                        completed["eventual_severe_exit"].astype(int),
                    ),
                    "eventual_severe_minus_nonsevere_mean_gap": eventual_conditional[
                        "severe_minus_nonsevere_mean_gap"
                    ],
                }
            )
    return pd.DataFrame(rows)


def _stratified_direction_summary(frame: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for dimension, block in frame.groupby("dimension", sort=True):
        next_gap = pd.to_numeric(
            block["next_severe_minus_nonsevere_mean_gap"], errors="coerce"
        ).dropna()
        eventual_gap = pd.to_numeric(
            block["eventual_severe_minus_nonsevere_mean_gap"], errors="coerce"
        ).dropna()
        result[str(dimension)] = {
            "next_session": {
                "comparable_strata": int(len(next_gap)),
                "protective_direction_strata": int((next_gap < 0).sum()),
                "equal_direction_strata": int((next_gap == 0).sum()),
                "opposite_direction_strata": int((next_gap > 0).sum()),
                "median_severe_minus_nonsevere_mean_gap": (
                    None if next_gap.empty else float(next_gap.median())
                ),
            },
            "eventual": {
                "comparable_strata": int(len(eventual_gap)),
                "protective_direction_strata": int((eventual_gap < 0).sum()),
                "equal_direction_strata": int((eventual_gap == 0).sum()),
                "opposite_direction_strata": int((eventual_gap > 0).sum()),
                "median_severe_minus_nonsevere_mean_gap": (
                    None if eventual_gap.empty else float(eventual_gap.median())
                ),
            },
        }
    return result


def _build_within_session_concordance(soft: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for session_index, block in soft.groupby("entry_index", sort=True):
        observed = block.loc[block["next_session_observable"]].dropna(
            subset=["next_session_severe_exit", "soft_rank_gap"]
        )
        severe = observed.loc[observed["next_session_severe_exit"].astype(bool)]
        nonsevere = observed.loc[~observed["next_session_severe_exit"].astype(bool)]
        if severe.empty or nonsevere.empty:
            continue
        protective = 0
        equal = 0
        opposite = 0
        for sev in severe.itertuples(index=False):
            for non in nonsevere.itertuples(index=False):
                sev_gap = float(sev.soft_rank_gap)
                non_gap = float(non.soft_rank_gap)
                if non_gap > sev_gap:
                    protective += 1
                elif non_gap == sev_gap:
                    equal += 1
                else:
                    opposite += 1
        total = protective + equal + opposite
        rows.append(
            {
                "session_index": int(session_index),
                "entry_date": str(block["entry_date"].iloc[0]),
                "a_soft_entries": int(len(block)),
                "next_observable_entries": int(len(observed)),
                "next_severe_entries": int(len(severe)),
                "next_nonsevere_entries": int(len(nonsevere)),
                "discordant_outcome_pairs": int(total),
                "larger_gap_on_nonsevere_pairs": int(protective),
                "equal_gap_pairs": int(equal),
                "larger_gap_on_severe_pairs": int(opposite),
                "protective_pair_share_excluding_ties": (
                    None
                    if protective + opposite == 0
                    else float(protective / (protective + opposite))
                ),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "session_index",
                "entry_date",
                "a_soft_entries",
                "next_observable_entries",
                "next_severe_entries",
                "next_nonsevere_entries",
                "discordant_outcome_pairs",
                "larger_gap_on_nonsevere_pairs",
                "equal_gap_pairs",
                "larger_gap_on_severe_pairs",
                "protective_pair_share_excluding_ties",
            ]
        )
    return pd.DataFrame(rows).sort_values("session_index").reset_index(drop=True)


def _concordance_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "eligible_sessions": 0,
            "discordant_outcome_pairs": 0,
            "larger_gap_on_nonsevere_pairs": 0,
            "equal_gap_pairs": 0,
            "larger_gap_on_severe_pairs": 0,
            "protective_pair_share_excluding_ties": None,
            "equal_session_weighted_protective_share": None,
        }
    protective = int(frame["larger_gap_on_nonsevere_pairs"].sum())
    equal = int(frame["equal_gap_pairs"].sum())
    opposite = int(frame["larger_gap_on_severe_pairs"].sum())
    shares = pd.to_numeric(
        frame["protective_pair_share_excluding_ties"], errors="coerce"
    ).dropna()
    return {
        "eligible_sessions": int(len(frame)),
        "discordant_outcome_pairs": int(protective + equal + opposite),
        "larger_gap_on_nonsevere_pairs": protective,
        "equal_gap_pairs": equal,
        "larger_gap_on_severe_pairs": opposite,
        "protective_pair_share_excluding_ties": (
            None
            if protective + opposite == 0
            else float(protective / (protective + opposite))
        ),
        "equal_session_weighted_protective_share": (
            None if shares.empty else float(shares.mean())
        ),
    }


def run_admission_mechanism_diagnosis(
    *, parent_root: str | Path
) -> AdmissionMechanismDiagnosisResult:
    paired, parent_manifest = load_same_session_parent(parent_root)
    soft = paired.loc[paired["entry_class"].eq("A_SOFT")].copy()
    soft["soft_rank_gap"] = pd.to_numeric(soft["soft_rank_gap"], errors="coerce")
    if soft["soft_rank_gap"].isna().any():
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_SOFT_GAP_MISSING")
    if (soft["soft_rank_gap"] < 5).any():
        raise DecisionV3FailureDiagnosisError("A_ADMISSION_SOFT_GAP_RULE_MISMATCH")

    next_obs = soft.loc[soft["next_session_observable"]].dropna(
        subset=["next_session_severe_exit"]
    )
    completed = soft.loc[soft["completed"]].dropna(subset=["eventual_severe_exit"])
    stratified = _build_stratified_gap_outcomes(soft)
    concordance = _build_within_session_concordance(soft)

    summary = {
        "status": "COMPLETE_OUTCOME_BLIND_DECISION_V3_A_ADMISSION_MECHANISM_DIAGNOSIS",
        "scientific_boundary": {
            "decision_v4_implemented_or_replayed": False,
            "alternative_rule_or_portfolio_simulated": False,
            "gap_threshold_searched_or_swept": False,
            "new_numeric_cutoff_recommended": False,
            "returns_or_pnl_accessed": False,
            "protected_or_fresh_forward_accessed": False,
            "model_refit_or_retune": False,
            "provider_or_network_called": False,
            "causal_effect_claimed": False,
        },
        "pins": {
            "parent_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
            "parent_status": parent_manifest.get("status"),
            "parent_paired_entries_sha256": parent_manifest["artifacts"][
                "paired_entries.csv"
            ],
            "contract_canonical_sha256": EXPECTED_CONTRACT_CANONICAL_SHA256,
        },
        "population": {
            "paired_sessions": int(paired["entry_index"].nunique()),
            "a_soft_entries": int(len(soft)),
            "a_vacancy_reference_entries": int(
                paired["entry_class"].eq("A_VACANCY").sum()
            ),
            "next_session_observable_a_soft": int(len(next_obs)),
            "completed_a_soft": int(len(completed)),
            "soft_rank_gap": _numeric_summary(soft["soft_rank_gap"]),
        },
        "threshold_free_associations": {
            "next_session_severe": {
                "spearman_gap_vs_severe": _spearman(
                    next_obs["soft_rank_gap"],
                    next_obs["next_session_severe_exit"].astype(int),
                ),
                "conditional_gap": _conditional_gap_summary(
                    next_obs, "next_session_severe_exit"
                ),
            },
            "eventual_severe_completed_only": {
                "spearman_gap_vs_severe": _spearman(
                    completed["soft_rank_gap"],
                    completed["eventual_severe_exit"].astype(int),
                ),
                "conditional_gap": _conditional_gap_summary(
                    completed, "eventual_severe_exit"
                ),
            },
            "holding_duration_completed_only": {
                "spearman_gap_vs_duration": _spearman(
                    completed["soft_rank_gap"], completed["duration_sessions"]
                ),
                "duration_sessions": _numeric_summary(completed["duration_sessions"]),
            },
        },
        "within_session_discordant_pair_concordance": _concordance_summary(
            concordance
        ),
        "stratified_gap_direction": _stratified_direction_summary(stratified),
        "candidate_evidence_by_next_session_state": _candidate_evidence_by_next_state(
            soft
        ),
        "interpretation_guard": (
            "This diagnosis assesses association of soft-rank-gap magnitude with durability only "
            "inside the already-selected A_SOFT population. It cannot estimate the causal effect "
            "of the >=5 admission hurdle itself and cannot authorize any numeric successor cutoff."
        ),
        "stop_rule": (
            "CONSUME_AND_STOP_MECHANISM_DIAGNOSIS_RETURN_TO_DECISION_V4_DESIGN"
        ),
    }
    return AdmissionMechanismDiagnosisResult(
        summary=summary,
        a_soft_gap_rows=soft.sort_values(
            ["entry_index", "current_rank", "ticker"], kind="mergesort"
        ).reset_index(drop=True),
        stratified_gap_outcomes=stratified,
        within_session_gap_concordance=concordance,
    )


def write_admission_mechanism_artifacts(
    result: AdmissionMechanismDiagnosisResult, output_dir: str | Path
) -> Path:
    out = Path(output_dir).expanduser().resolve()
    stage = out.parent / f".{out.name}.staging"
    if out.exists():
        raise DecisionV3FailureDiagnosisError(f"A_ADMISSION_OUTPUT_EXISTS:{out}")
    if stage.exists():
        raise DecisionV3FailureDiagnosisError(f"A_ADMISSION_STAGING_EXISTS:{stage}")
    stage.mkdir(parents=True, exist_ok=False)
    try:
        (stage / "summary.json").write_text(
            json.dumps(result.summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result.a_soft_gap_rows.to_csv(stage / "a_soft_gap_rows.csv", index=False)
        result.stratified_gap_outcomes.to_csv(
            stage / "stratified_gap_outcomes.csv", index=False
        )
        result.within_session_gap_concordance.to_csv(
            stage / "within_session_gap_concordance.csv", index=False
        )
        artifact_names = [
            "summary.json",
            "a_soft_gap_rows.csv",
            "stratified_gap_outcomes.csv",
            "within_session_gap_concordance.csv",
        ]
        artifacts = {name: sha256_file(stage / name) for name in artifact_names}
        manifest = {
            "status": result.summary["status"],
            "contract_canonical_sha256": EXPECTED_CONTRACT_CANONICAL_SHA256,
            "parent_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
            "scientific_boundary": result.summary["scientific_boundary"],
            "stop_rule": result.summary["stop_rule"],
            "artifacts": artifacts,
        }
        manifest_path = stage / "MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        stage.rename(out)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    return out / "MANIFEST.json"
