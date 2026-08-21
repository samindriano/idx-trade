from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any

import pandas as pd

from .decision_v3_failure_diagnosis import DecisionV3FailureDiagnosisError
from .decision_v3_structural_source import canonical_json_sha256, sha256_file

CONTRACT_RELATIVE_PATH = Path("docs/specs/decision_v3_a_same_session_diagnosis_v1.json")
EXPECTED_CONTRACT_CANONICAL_SHA256 = (
    "6089bc20592a494820fdf9e63627536b4443577a22aeea13eaa2fd6fa7070953"
)
EXPECTED_PARENT_MANIFEST_SHA256 = (
    "d17f009df762678734d3f073419d44b707d55ba6dd3f25627e332438c9a7c224"
)
EXPECTED_PARENT_STATUS = "COMPLETE_OUTCOME_BLIND_DECISION_V3_A_SOFT_VACANCY_DIAGNOSIS"
EXPECTED_PARENT_COUNTS = {"A_VACANCY": 721, "A_SOFT": 422}

ENTRY_CLASSES = ("A_SOFT", "A_VACANCY")
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
    "last3_top20_count": ("last3_top20_count", ("1", "2", "3")),
}


@dataclass(frozen=True)
class SameSessionDiagnosisResult:
    summary: dict[str, Any]
    paired_entries: pd.DataFrame
    paired_session_summary: pd.DataFrame
    paired_stratified_next_severe: pd.DataFrame


def verify_same_session_contract(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser().resolve() / CONTRACT_RELATIVE_PATH
    if not path.is_file():
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_CONTRACT_MISSING")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_CONTRACT_INVALID_JSON") from exc
    if not isinstance(payload, dict):
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_CONTRACT_NOT_OBJECT")
    actual = canonical_json_sha256(payload)
    if actual != EXPECTED_CONTRACT_CANONICAL_SHA256:
        raise DecisionV3FailureDiagnosisError(
            f"A_SAME_SESSION_CONTRACT_SHA_CHANGED:{actual}!={EXPECTED_CONTRACT_CANONICAL_SHA256}"
        )
    if payload.get("status") != "FROZEN_BEFORE_EXECUTION":
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_CONTRACT_STATUS_CHANGED")
    if payload.get("execution_authorized") is not False:
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_CONTRACT_EXECUTION_FLAG_CHANGED")
    forbidden = payload.get("forbidden", {})
    if not forbidden or not all(value is True for value in forbidden.values()):
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_CONTRACT_FORBIDDEN_GUARD_CHANGED")
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
            f"A_SAME_SESSION_BOOL_PARSE_FAILED:{name}:{bad}"
        )
    return mapped.astype(bool)


def load_parent_entries(parent_root: str | Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    root = Path(parent_root).expanduser().resolve()
    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_PARENT_MANIFEST_MISSING")
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != EXPECTED_PARENT_MANIFEST_SHA256:
        raise DecisionV3FailureDiagnosisError(
            f"A_SAME_SESSION_PARENT_MANIFEST_SHA_CHANGED:{actual_manifest_sha}!={EXPECTED_PARENT_MANIFEST_SHA256}"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3FailureDiagnosisError(
            "A_SAME_SESSION_PARENT_MANIFEST_INVALID_JSON"
        ) from exc
    if manifest.get("status") != EXPECTED_PARENT_STATUS:
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_PARENT_STATUS_CHANGED")
    boundary = manifest.get("scientific_boundary")
    if not isinstance(boundary, dict) or any(bool(v) for v in boundary.values()):
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_PARENT_BOUNDARY_CHANGED")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or "a_entry_diagnosis.csv" not in artifacts:
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_PARENT_ARTIFACT_PIN_MISSING")

    csv_path = root / "a_entry_diagnosis.csv"
    if not csv_path.is_file():
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_PARENT_ENTRY_CSV_MISSING")
    actual_csv_sha = sha256_file(csv_path)
    if actual_csv_sha != artifacts["a_entry_diagnosis.csv"]:
        raise DecisionV3FailureDiagnosisError(
            f"A_SAME_SESSION_PARENT_ENTRY_SHA_CHANGED:{actual_csv_sha}!={artifacts['a_entry_diagnosis.csv']}"
        )

    frame = pd.read_csv(csv_path)
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise DecisionV3FailureDiagnosisError(
            f"A_SAME_SESSION_PARENT_COLUMNS_MISSING:{missing}"
        )
    actual_counts = frame["entry_class"].value_counts().to_dict()
    if actual_counts != EXPECTED_PARENT_COUNTS:
        raise DecisionV3FailureDiagnosisError(
            f"A_SAME_SESSION_PARENT_COUNTS_CHANGED:{actual_counts}!={EXPECTED_PARENT_COUNTS}"
        )
    for column in (
        "one_session_holding",
        "completed",
        "right_censored",
        "next_session_observable",
    ):
        frame[column] = _normalize_bool(frame[column], column)
    for column in ("eventual_severe_exit", "next_session_severe_exit"):
        raw = frame[column]
        lower = raw.astype(str).str.strip().str.lower()
        mapped = lower.map(
            {"true": True, "false": False, "1": True, "0": False, "nan": None, "": None}
        )
        invalid = mapped.isna() & ~lower.isin(("nan", ""))
        if invalid.any():
            bad = sorted(raw.loc[invalid].astype(str).unique().tolist())[:5]
            raise DecisionV3FailureDiagnosisError(
                f"A_SAME_SESSION_OPTIONAL_BOOL_PARSE_FAILED:{column}:{bad}"
            )
        frame[column] = mapped
    return frame, manifest


def _rate(series: pd.Series) -> float | None:
    clean = series.dropna()
    if clean.empty:
        return None
    return float(clean.astype(bool).mean())


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


def _difference_summary(series: pd.Series) -> dict[str, float | int | None]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if values.empty:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "soft_lower": 0,
            "equal": 0,
            "soft_higher": 0,
        }
    return {
        "count": int(values.size),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "soft_lower": int((values < 0).sum()),
        "equal": int((values == 0).sum()),
        "soft_higher": int((values > 0).sum()),
    }


def _class_summary(frame: pd.DataFrame, entry_class: str) -> dict[str, Any]:
    block = frame.loc[frame["entry_class"].eq(entry_class)]
    next_obs = block.loc[block["next_session_observable"]]
    completed = block.loc[block["completed"]]
    evidence = {column: _numeric_summary(block[column]) for column in EVIDENCE_COLUMNS}
    result: dict[str, Any] = {
        "entries": int(len(block)),
        "next_session_observable_entries": int(len(next_obs)),
        "next_session_severe_rate": _rate(next_obs["next_session_severe_exit"]),
        "completed_entries": int(len(completed)),
        "eventual_severe_rate_completed_only": _rate(
            completed["eventual_severe_exit"]
        ),
        "one_session_holding_rate": _rate(block["one_session_holding"]),
        "duration_sessions": _numeric_summary(block["duration_sessions"]),
        "candidate_evidence": evidence,
    }
    if entry_class == "A_SOFT":
        result["soft_rank_gap"] = _numeric_summary(block["soft_rank_gap"])
    return result


def _paired_session_indices(frame: pd.DataFrame) -> list[int]:
    class_counts = frame.groupby("entry_index")["entry_class"].nunique()
    indices = sorted(int(x) for x in class_counts.loc[class_counts.eq(2)].index)
    if not indices:
        raise DecisionV3FailureDiagnosisError("A_SAME_SESSION_NO_PAIRED_SESSIONS")
    return indices


def _assert_session_context_constant(block: pd.DataFrame) -> None:
    for column in (
        "entry_date",
        "severe_exit_count",
        "confirmed_mild_exit_count",
        "universe_exit_count",
        "mandatory_exit_count",
        "top10_overlap",
        "top20_overlap",
        "previous_top10_to_gt50_or_absent_count",
    ):
        if column in block.columns and block[column].nunique(dropna=False) != 1:
            raise DecisionV3FailureDiagnosisError(
                f"A_SAME_SESSION_CONTEXT_NOT_CONSTANT:{int(block['entry_index'].iloc[0])}:{column}"
            )


def _build_session_summary(paired: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for session_index, block in paired.groupby("entry_index", sort=True):
        _assert_session_context_constant(block)
        soft = block.loc[block["entry_class"].eq("A_SOFT")]
        vacancy = block.loc[block["entry_class"].eq("A_VACANCY")]
        if soft.empty or vacancy.empty:
            raise DecisionV3FailureDiagnosisError(
                f"A_SAME_SESSION_PAIR_INCOMPLETE:{session_index}"
            )
        soft_next = soft.loc[soft["next_session_observable"]]
        vacancy_next = vacancy.loc[vacancy["next_session_observable"]]
        soft_completed = soft.loc[soft["completed"]]
        vacancy_completed = vacancy.loc[vacancy["completed"]]
        soft_next_rate = _rate(soft_next["next_session_severe_exit"])
        vacancy_next_rate = _rate(vacancy_next["next_session_severe_exit"])
        soft_eventual = _rate(soft_completed["eventual_severe_exit"])
        vacancy_eventual = _rate(vacancy_completed["eventual_severe_exit"])
        row: dict[str, Any] = {
            "session_index": int(session_index),
            "entry_date": str(block["entry_date"].iloc[0]),
            "a_soft_entries": int(len(soft)),
            "a_vacancy_entries": int(len(vacancy)),
            "a_soft_next_observable": int(len(soft_next)),
            "a_vacancy_next_observable": int(len(vacancy_next)),
            "a_soft_next_severe_rate": soft_next_rate,
            "a_vacancy_next_severe_rate": vacancy_next_rate,
            "soft_minus_vacancy_next_severe_gap": (
                None
                if soft_next_rate is None or vacancy_next_rate is None
                else float(soft_next_rate - vacancy_next_rate)
            ),
            "a_soft_completed": int(len(soft_completed)),
            "a_vacancy_completed": int(len(vacancy_completed)),
            "a_soft_eventual_severe_rate": soft_eventual,
            "a_vacancy_eventual_severe_rate": vacancy_eventual,
            "soft_minus_vacancy_eventual_severe_gap": (
                None
                if soft_eventual is None or vacancy_eventual is None
                else float(soft_eventual - vacancy_eventual)
            ),
            "severe_exit_count": int(block["severe_exit_count"].iloc[0]),
            "mandatory_exit_count": int(block["mandatory_exit_count"].iloc[0]),
            "top10_overlap": int(block["top10_overlap"].iloc[0]),
            "top20_overlap": int(block["top20_overlap"].iloc[0]),
        }
        for column in EVIDENCE_COLUMNS:
            soft_mean = pd.to_numeric(soft[column], errors="coerce").mean()
            vacancy_mean = pd.to_numeric(vacancy[column], errors="coerce").mean()
            row[f"a_soft_{column}_mean"] = (
                None if pd.isna(soft_mean) else float(soft_mean)
            )
            row[f"a_vacancy_{column}_mean"] = (
                None if pd.isna(vacancy_mean) else float(vacancy_mean)
            )
            row[f"soft_minus_vacancy_{column}_mean_gap"] = (
                None
                if pd.isna(soft_mean) or pd.isna(vacancy_mean)
                else float(soft_mean - vacancy_mean)
            )
        soft_gap = pd.to_numeric(soft["soft_rank_gap"], errors="coerce").mean()
        row["a_soft_soft_rank_gap_mean"] = (
            None if pd.isna(soft_gap) else float(soft_gap)
        )
        rows.append(row)
    return pd.DataFrame(rows).sort_values("session_index").reset_index(drop=True)


def _build_stratified(paired: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dimension, (column, ordered_values) in STRATA.items():
        values = paired[column].astype(str)
        for stratum in ordered_values:
            block = paired.loc[values.eq(stratum)]
            soft = block.loc[block["entry_class"].eq("A_SOFT")]
            vacancy = block.loc[block["entry_class"].eq("A_VACANCY")]
            soft_next = soft.loc[soft["next_session_observable"]]
            vacancy_next = vacancy.loc[vacancy["next_session_observable"]]
            soft_completed = soft.loc[soft["completed"]]
            vacancy_completed = vacancy.loc[vacancy["completed"]]
            soft_rate = _rate(soft_next["next_session_severe_exit"])
            vacancy_rate = _rate(vacancy_next["next_session_severe_exit"])
            soft_eventual = _rate(soft_completed["eventual_severe_exit"])
            vacancy_eventual = _rate(vacancy_completed["eventual_severe_exit"])
            rows.append(
                {
                    "dimension": dimension,
                    "stratum": stratum,
                    "a_soft_entries": int(len(soft)),
                    "a_vacancy_entries": int(len(vacancy)),
                    "a_soft_next_observable": int(len(soft_next)),
                    "a_vacancy_next_observable": int(len(vacancy_next)),
                    "a_soft_next_severe_rate": soft_rate,
                    "a_vacancy_next_severe_rate": vacancy_rate,
                    "soft_minus_vacancy_next_severe_gap": (
                        None
                        if soft_rate is None or vacancy_rate is None
                        else float(soft_rate - vacancy_rate)
                    ),
                    "a_soft_completed": int(len(soft_completed)),
                    "a_vacancy_completed": int(len(vacancy_completed)),
                    "a_soft_eventual_severe_rate": soft_eventual,
                    "a_vacancy_eventual_severe_rate": vacancy_eventual,
                    "soft_minus_vacancy_eventual_severe_gap": (
                        None
                        if soft_eventual is None or vacancy_eventual is None
                        else float(soft_eventual - vacancy_eventual)
                    ),
                }
            )
    return pd.DataFrame(rows)


def _stratified_direction(frame: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for dimension, block in frame.groupby("dimension", sort=True):
        comparable = block.dropna(subset=["soft_minus_vacancy_next_severe_gap"])
        gaps = pd.to_numeric(
            comparable["soft_minus_vacancy_next_severe_gap"], errors="coerce"
        ).dropna()
        result[str(dimension)] = {
            "comparable_strata": int(len(gaps)),
            "soft_lower_next_severe_strata": int((gaps < 0).sum()),
            "soft_equal_next_severe_strata": int((gaps == 0).sum()),
            "soft_higher_next_severe_strata": int((gaps > 0).sum()),
            "median_soft_minus_vacancy_gap": (
                None if gaps.empty else float(gaps.median())
            ),
        }
    return result


def run_same_session_diagnosis(
    *, parent_root: str | Path
) -> SameSessionDiagnosisResult:
    entries, parent_manifest = load_parent_entries(parent_root)
    indices = _paired_session_indices(entries)
    paired = entries.loc[entries["entry_index"].isin(indices)].copy()
    paired = paired.sort_values(
        ["entry_index", "entry_class", "current_rank", "ticker"],
        kind="mergesort",
    ).reset_index(drop=True)
    session_summary = _build_session_summary(paired)
    stratified = _build_stratified(paired)

    soft = paired.loc[paired["entry_class"].eq("A_SOFT")]
    vacancy = paired.loc[paired["entry_class"].eq("A_VACANCY")]
    soft_next = soft.loc[soft["next_session_observable"]]
    vacancy_next = vacancy.loc[vacancy["next_session_observable"]]
    soft_completed = soft.loc[soft["completed"]]
    vacancy_completed = vacancy.loc[vacancy["completed"]]
    soft_next_rate = _rate(soft_next["next_session_severe_exit"])
    vacancy_next_rate = _rate(vacancy_next["next_session_severe_exit"])
    soft_eventual = _rate(soft_completed["eventual_severe_exit"])
    vacancy_eventual = _rate(vacancy_completed["eventual_severe_exit"])

    evidence_session_differences = {
        column: _difference_summary(
            session_summary[f"soft_minus_vacancy_{column}_mean_gap"]
        )
        for column in EVIDENCE_COLUMNS
    }

    summary = {
        "status": "COMPLETE_OUTCOME_BLIND_DECISION_V3_A_SAME_SESSION_DIAGNOSIS",
        "scientific_boundary": {
            "decision_v4_implemented_or_replayed": False,
            "alternative_rule_or_portfolio_simulated": False,
            "returns_or_outcomes_accessed": False,
            "protected_or_fresh_forward_accessed": False,
            "model_refit_or_retune": False,
            "provider_or_network_called": False,
            "causal_effect_claimed": False,
        },
        "pins": {
            "parent_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
            "parent_status": parent_manifest.get("status"),
            "parent_a_entry_diagnosis_sha256": parent_manifest["artifacts"][
                "a_entry_diagnosis.csv"
            ],
            "contract_canonical_sha256": EXPECTED_CONTRACT_CANONICAL_SHA256,
        },
        "paired_population": {
            "paired_sessions": int(len(indices)),
            "first_session_index": int(min(indices)),
            "last_session_index": int(max(indices)),
            "A_SOFT": _class_summary(paired, "A_SOFT"),
            "A_VACANCY": _class_summary(paired, "A_VACANCY"),
            "entry_weighted_next_session_severe_gap_soft_minus_vacancy": (
                None
                if soft_next_rate is None or vacancy_next_rate is None
                else float(soft_next_rate - vacancy_next_rate)
            ),
            "entry_weighted_eventual_severe_gap_soft_minus_vacancy": (
                None
                if soft_eventual is None or vacancy_eventual is None
                else float(soft_eventual - vacancy_eventual)
            ),
        },
        "equal_session_weighted": {
            "next_session_severe_gap": _difference_summary(
                session_summary["soft_minus_vacancy_next_severe_gap"]
            ),
            "eventual_severe_gap": _difference_summary(
                session_summary["soft_minus_vacancy_eventual_severe_gap"]
            ),
            "candidate_evidence_mean_gaps_soft_minus_vacancy": evidence_session_differences,
        },
        "stratified_direction": _stratified_direction(stratified),
        "interpretation_guard": (
            "Same-session restriction removes session-level context differences by construction "
            "but does not randomize selection into A_SOFT versus A_VACANCY. All results remain "
            "descriptive and do not automatically authorize a successor rule."
        ),
    }
    return SameSessionDiagnosisResult(
        summary=summary,
        paired_entries=paired,
        paired_session_summary=session_summary,
        paired_stratified_next_severe=stratified,
    )


def write_same_session_artifacts(
    result: SameSessionDiagnosisResult, output_dir: str | Path
) -> Path:
    out = Path(output_dir).expanduser().resolve()
    stage = out.parent / f".{out.name}.staging"
    if out.exists():
        raise DecisionV3FailureDiagnosisError(f"A_SAME_SESSION_OUTPUT_EXISTS:{out}")
    if stage.exists():
        raise DecisionV3FailureDiagnosisError(f"A_SAME_SESSION_STAGING_EXISTS:{stage}")
    stage.mkdir(parents=True, exist_ok=False)
    try:
        (stage / "summary.json").write_text(
            json.dumps(result.summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result.paired_entries.to_csv(stage / "paired_entries.csv", index=False)
        result.paired_session_summary.to_csv(
            stage / "paired_session_summary.csv", index=False
        )
        result.paired_stratified_next_severe.to_csv(
            stage / "paired_stratified_next_severe.csv", index=False
        )
        artifact_names = [
            "summary.json",
            "paired_entries.csv",
            "paired_session_summary.csv",
            "paired_stratified_next_severe.csv",
        ]
        artifacts = {name: sha256_file(stage / name) for name in artifact_names}
        manifest = {
            "status": result.summary["status"],
            "contract_canonical_sha256": EXPECTED_CONTRACT_CANONICAL_SHA256,
            "parent_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
            "scientific_boundary": result.summary["scientific_boundary"],
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
