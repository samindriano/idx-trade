from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .provenance import environment_manifest, sha256_file
from .research_v2_validation import evaluate_v2_scores
from .storage import write_parquet_atomic


PROTOCOL_STATUS = "FORWARD_100_SESSION_EVALUATION_PROTOCOL_V1_FROZEN_OUTCOME_BLIND"
PROTOCOL_COMMIT = "6c05499d01ba644c80f0c6bd6d621aac92ab2813"
PROTOCOL_SHA256 = "526b69e46a8ffbebcc0e7ebd044e54333672cd24ee1c36cf5dca8752f100a8a3"
O2_MODEL_SHA256 = "42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb"
O2_FEATURE_ORDER_SHA256 = "a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f"
BLOCK_SESSIONS = 100
HALF_SESSIONS = 50
RELIABILITY_MIN_SESSIONS = 80
RELIABILITY_MIN_HALF_SESSIONS = 40
REAL_FORWARD_MARKER = "FORWARD_OUTCOME_ACCESS_STARTED"
SYNTHETIC_MARKER = "SYNTHETIC_FORWARD_OUTCOME_ACCESS_STARTED"

O2_REQUIRED_METRICS = (
    "positive_rate",
    "pr_auc",
    "pr_auc_delta_vs_base",
    "roc_auc",
    "q1_tp_rate",
    "q5_tp_rate",
    "q5_minus_q1",
    "top_decile_tp_rate",
    "top_decile_lift",
)
RELIABILITY_METRICS = (
    "median_spearman",
    "mean_q4_minus_q1",
    "mean_top40_lift",
    "mean_conditional_lift",
)
REQUIRED_SHARED_ARTIFACTS = (
    "o2_model",
    "o2_model_manifest",
    "o2_feature_order",
    "official_calendar",
    "security_master",
    "tradability",
    "corporate_actions",
    "source_snapshot",
)


class ForwardEvaluationBlocked(RuntimeError):
    """Raised before producing a misleading or non-reproducible verdict."""


def _normal_dates(values: Sequence[object] | pd.Series) -> pd.Series:
    dates = pd.to_datetime(pd.Series(values), errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
    if dates.isna().any():
        raise ForwardEvaluationBlocked("invalid session date")
    return dates


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_json_value(dict(payload)), sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(_json_value(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _require_columns(frame: pd.DataFrame, required: set[str], *, label: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ForwardEvaluationBlocked(f"{label} missing columns: {sorted(missing)}")


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ForwardEvaluationBlocked(f"malformed {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ForwardEvaluationBlocked(f"{label} must be a JSON object: {path}")
    return payload


def _optional_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def validate_named_artifacts(
    artifacts: Mapping[str, Mapping[str, str]], *, fixture_root: Path
) -> dict[str, dict[str, str]]:
    missing = set(REQUIRED_SHARED_ARTIFACTS) - set(artifacts)
    if missing:
        raise ForwardEvaluationBlocked(f"shared artifact inventory missing: {sorted(missing)}")
    root = fixture_root.resolve()
    verified: dict[str, dict[str, str]] = {}
    for role in REQUIRED_SHARED_ARTIFACTS:
        record = artifacts[role]
        path_value = _optional_text(record.get("path"))
        hash_value = _optional_text(record.get("sha256")).lower()
        if not path_value or len(hash_value) != 64:
            raise ForwardEvaluationBlocked(f"invalid shared artifact declaration: {role}")
        path = Path(path_value).resolve()
        if path != root and root not in path.parents:
            raise ForwardEvaluationBlocked(f"shared artifact escapes fixture root: {role}")
        if not path.is_file() or sha256_file(path) != hash_value:
            raise ForwardEvaluationBlocked(f"shared artifact hash mismatch: {role}")
        verified[role] = {"path": str(path), "sha256": hash_value}
    return verified


def validate_session_inventory(inventory: pd.DataFrame, *, fixture_root: Path | None = None) -> pd.DataFrame:
    """Validate the immutable 100-session identity and source-hash inventory.

    This validator is intentionally generic.  The synthetic runner additionally
    requires every path to live below its non-protected fixture root.
    """

    required = {
        "session_date",
        "session_index",
        "o2_score_path",
        "o2_score_sha256",
        "o2_manifest_path",
        "o2_manifest_sha256",
        "reliability_path",
        "reliability_sha256",
        "reliability_manifest_path",
        "reliability_manifest_sha256",
        "protected",
    }
    _require_columns(inventory, required, label="session inventory")
    data = inventory.copy()
    if len(data) != BLOCK_SESSIONS:
        raise ForwardEvaluationBlocked("session inventory must contain exactly 100 rows")
    data["session_date"] = _normal_dates(data["session_date"])
    data["session_index"] = pd.to_numeric(data["session_index"], errors="raise").astype(int)
    data = data.sort_values(["session_index", "session_date"], kind="mergesort").reset_index(drop=True)
    if data["session_date"].duplicated().any() or data["session_index"].duplicated().any():
        raise ForwardEvaluationBlocked("session inventory contains duplicate dates or indices")
    if not np.array_equal(np.diff(data["session_index"].to_numpy(dtype=int)), np.ones(BLOCK_SESSIONS - 1, dtype=int)):
        raise ForwardEvaluationBlocked("session indices are not consecutive")
    if not data["session_date"].is_monotonic_increasing:
        raise ForwardEvaluationBlocked("session dates are not strictly ordered")
    if data["protected"].astype(bool).any():
        raise ForwardEvaluationBlocked("synthetic evaluator refuses protected artifacts")

    root = fixture_root.resolve() if fixture_root is not None else None
    artifact_pairs = (
        ("o2_score_path", "o2_score_sha256", False),
        ("o2_manifest_path", "o2_manifest_sha256", False),
        ("reliability_path", "reliability_sha256", True),
        ("reliability_manifest_path", "reliability_manifest_sha256", True),
    )
    for row in data.itertuples(index=False):
        rel_values = [
            _optional_text(getattr(row, "reliability_path")),
            _optional_text(getattr(row, "reliability_sha256")),
            _optional_text(getattr(row, "reliability_manifest_path")),
            _optional_text(getattr(row, "reliability_manifest_sha256")),
        ]
        if any(rel_values) and not all(rel_values):
            raise ForwardEvaluationBlocked("partial Reliability sidecar declaration")
        for path_column, hash_column, optional in artifact_pairs:
            path_value = _optional_text(getattr(row, path_column))
            hash_value = _optional_text(getattr(row, hash_column)).lower()
            if optional and not path_value and not hash_value:
                continue
            if not path_value or len(hash_value) != 64:
                raise ForwardEvaluationBlocked(f"invalid artifact declaration: {path_column}")
            path = Path(path_value).resolve()
            if root is not None and path != root and root not in path.parents:
                raise ForwardEvaluationBlocked("synthetic artifact escapes fixture root")
            if not path.is_file():
                raise ForwardEvaluationBlocked(f"missing artifact: {path}")
            if sha256_file(path) != hash_value:
                raise ForwardEvaluationBlocked(f"artifact hash mismatch: {path}")

        session_date = row.session_date.date().isoformat()
        o2_manifest_path = Path(str(row.o2_manifest_path)).resolve()
        o2_manifest = _read_json_object(o2_manifest_path, label="O2 session manifest")
        o2_checks = {
            "status": o2_manifest.get("status") == "DONE",
            "session_date": o2_manifest.get("session_date") == session_date,
            "session_index": int(o2_manifest.get("official_session_index", -1)) == int(row.session_index),
            "score_sha": o2_manifest.get("score_artifact_sha256") == row.o2_score_sha256,
            "model_sha": o2_manifest.get("model_sha256") == O2_MODEL_SHA256,
            "feature_sha": o2_manifest.get("feature_order_sha256") == O2_FEATURE_ORDER_SHA256,
            "outcome_blind": o2_manifest.get("outcome_blind") is True,
            "outcomes_locked": o2_manifest.get("fresh_forward_outcomes_accessed") is False,
            "marker_locked": o2_manifest.get("forward_outcome_access_marker_written") is False,
        }
        failed_o2 = sorted(name for name, passed in o2_checks.items() if not passed)
        if failed_o2:
            raise ForwardEvaluationBlocked(f"O2 manifest contract mismatch {session_date}: {failed_o2}")

        if all(rel_values):
            reliability_manifest_path = Path(str(row.reliability_manifest_path)).resolve()
            reliability_manifest = _read_json_object(reliability_manifest_path, label="Reliability manifest")
            reliability_checks = {
                "status": reliability_manifest.get("status") == "READY",
                "session_date": reliability_manifest.get("session_date") == session_date,
                "session_index": int(reliability_manifest.get("official_session_index", -1)) == int(row.session_index),
                "artifact_sha": reliability_manifest.get("reliability_artifact_sha256") == row.reliability_sha256,
                "o2_score_sha": reliability_manifest.get("o2_source_score_artifact_sha256") == row.o2_score_sha256,
                "o2_manifest_sha": reliability_manifest.get("o2_source_session_manifest_sha256") == row.o2_manifest_sha256,
                "o2_model_sha": reliability_manifest.get("o2_model_sha256") == O2_MODEL_SHA256,
                "o2_feature_sha": reliability_manifest.get("o2_feature_order_sha256") == O2_FEATURE_ORDER_SHA256,
                "outcomes_locked": reliability_manifest.get("outcome_access") == "LOCKED",
                "protected_flags": reliability_manifest.get("runtime_flags")
                == {
                    "provider_call": False,
                    "outcome_access": False,
                    "o2_refit": False,
                    "o2_rescore": False,
                    "counter_change": False,
                    "tiering_or_filtering": False,
                },
            }
            failed_reliability = sorted(name for name, passed in reliability_checks.items() if not passed)
            if failed_reliability:
                raise ForwardEvaluationBlocked(
                    f"Reliability manifest contract mismatch {session_date}: {failed_reliability}"
                )
    return data


def validate_o2_scores(frame: pd.DataFrame, sessions: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", "session_index", "o2_eligible", "score"}
    _require_columns(frame, required, label="O2 score frame")
    data = frame.copy()
    data["date"] = _normal_dates(data["date"])
    data["session_index"] = pd.to_numeric(data["session_index"], errors="raise").astype(int)
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    if data["ticker"].eq("").any() or data.duplicated(["date", "ticker"]).any():
        raise ForwardEvaluationBlocked("O2 score keys are invalid or duplicated")
    expected = sessions[["session_date", "session_index"]].rename(columns={"session_date": "date"})
    merged = data[["date", "session_index"]].drop_duplicates().merge(expected, how="outer", indicator=True)
    if not merged["_merge"].eq("both").all():
        raise ForwardEvaluationBlocked("O2 rows do not exactly use the frozen 100 sessions and indices")
    data["o2_eligible"] = data["o2_eligible"].astype(bool)
    data["score"] = pd.to_numeric(data["score"], errors="coerce")
    eligible = data["o2_eligible"]
    if not eligible.groupby(data["date"]).any().all():
        raise ForwardEvaluationBlocked("every frozen session requires at least one O2-scored row")
    if data.loc[eligible, "score"].isna().any() or not np.isfinite(data.loc[eligible, "score"].to_numpy()).all():
        raise ForwardEvaluationBlocked("O2-eligible rows require finite accepted scores")
    if data.loc[~eligible, "score"].notna().any():
        raise ForwardEvaluationBlocked("O2-ineligible rows must not contain scores")
    return data.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def materialize_outcome_frame(o2_scores: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", "binary_target", "unresolved_reason", "source_ref", "source_sha256"}
    _require_columns(outcomes, required, label="outcome frame")
    expected = o2_scores.loc[o2_scores["o2_eligible"], ["ticker", "date", "session_index", "score"]].copy()
    result = outcomes.copy()
    result["date"] = _normal_dates(result["date"])
    result["ticker"] = result["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    if result["ticker"].eq("").any() or result.duplicated(["date", "ticker"]).any():
        raise ForwardEvaluationBlocked("outcome keys are invalid or duplicated")
    key_check = expected[["date", "ticker"]].merge(result[["date", "ticker"]], how="outer", indicator=True)
    if not key_check["_merge"].eq("both").all():
        raise ForwardEvaluationBlocked("outcome rows must exactly match frozen O2-scored rows")
    result["binary_target"] = pd.to_numeric(result["binary_target"], errors="coerce")
    resolved = result["binary_target"].notna()
    if not result.loc[resolved, "binary_target"].isin([0.0, 1.0]).all():
        raise ForwardEvaluationBlocked("resolved outcomes must be binary")
    if result.loc[~resolved, "unresolved_reason"].fillna("").astype(str).str.strip().eq("").any():
        raise ForwardEvaluationBlocked("unresolved outcomes require an explicit reason")
    if result["source_ref"].fillna("").astype(str).str.strip().eq("").any():
        raise ForwardEvaluationBlocked("outcomes require source provenance")
    hashes = result["source_sha256"].fillna("").astype(str).str.lower()
    if (~hashes.str.fullmatch(r"[0-9a-f]{64}")).any():
        raise ForwardEvaluationBlocked("outcomes require valid source SHA-256")
    joined = expected.merge(result, on=["date", "ticker"], how="inner", validate="one_to_one")
    return joined.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def _empty_o2_metrics() -> dict[str, float]:
    return {name: float("nan") for name in ("rows", *O2_REQUIRED_METRICS)}


def _o2_metrics(frame: pd.DataFrame) -> dict[str, float]:
    try:
        return evaluate_v2_scores(
            frame.rename(columns={"date": "date"}),
            pd.to_numeric(frame["score"], errors="raise").to_numpy(dtype=float),
        )
    except (KeyError, ValueError, IndexError):
        return _empty_o2_metrics()


def classify_o2_decision(
    aggregate: Mapping[str, float],
    first_50: Mapping[str, float],
    last_50: Mapping[str, float],
    *,
    provenance_and_maturity_pass: bool,
) -> tuple[str, dict[str, bool]]:
    gating = [
        *(aggregate[name] for name in O2_REQUIRED_METRICS),
        first_50["pr_auc_delta_vs_base"],
        first_50["q5_minus_q1"],
        last_50["pr_auc_delta_vs_base"],
        last_50["q5_minus_q1"],
    ]
    finite = bool(np.isfinite(np.asarray(gating, dtype=float)).all())
    aggregate_core = bool(
        finite and aggregate["pr_auc_delta_vs_base"] > 0 and aggregate["q5_minus_q1"] > 0
    )
    stability = bool(
        finite
        and first_50["pr_auc_delta_vs_base"] > 0
        and last_50["pr_auc_delta_vs_base"] > 0
        and first_50["q5_minus_q1"] > 0
        and last_50["q5_minus_q1"] > 0
    )
    checks = {
        "provenance_and_maturity_pass": bool(provenance_and_maturity_pass),
        "all_required_metrics_finite": finite,
        "aggregate_pr_delta_positive": bool(finite and aggregate["pr_auc_delta_vs_base"] > 0),
        "aggregate_roc_above_half": bool(finite and aggregate["roc_auc"] > 0.5),
        "aggregate_q5_minus_q1_positive": bool(finite and aggregate["q5_minus_q1"] > 0),
        "early_late_stability_pass": stability,
    }
    if not provenance_and_maturity_pass or not aggregate_core:
        return "O2_FORWARD_FAIL", checks
    if aggregate["roc_auc"] > 0.5 and stability:
        return "O2_FORWARD_PASS", checks
    return "O2_FORWARD_MIXED", checks


def evaluate_o2(outcome_frame: pd.DataFrame, sessions: pd.DataFrame, *, provenance_and_maturity_pass: bool) -> dict[str, Any]:
    dates = sessions["session_date"].tolist()
    resolved = outcome_frame["binary_target"].notna()
    sample = outcome_frame.loc[resolved].copy()
    sample["binary_target"] = sample["binary_target"].astype(int)
    aggregate = _o2_metrics(sample)
    first = _o2_metrics(sample[sample["date"].isin(dates[:HALF_SESSIONS])].copy())
    last = _o2_metrics(sample[sample["date"].isin(dates[HALF_SESSIONS:])].copy())
    decision, checks = classify_o2_decision(
        aggregate,
        first,
        last,
        provenance_and_maturity_pass=provenance_and_maturity_pass,
    )
    unresolved_reasons = (
        outcome_frame.loc[~resolved, "unresolved_reason"].fillna("UNKNOWN").astype(str).value_counts().sort_index().to_dict()
    )
    return {
        "decision": decision,
        "expected_o2_scored_rows": int(len(outcome_frame)),
        "resolved_outcome_rows": int(resolved.sum()),
        "unresolved_outcome_rows": int((~resolved).sum()),
        "unresolved_reasons": {str(key): int(value) for key, value in unresolved_reasons.items()},
        "outcome_coverage": float(resolved.mean()) if len(outcome_frame) else 0.0,
        "aggregate": aggregate,
        "first_50": first,
        "last_50": last,
        "checks": checks,
        "top_decile_is_diagnostic_only": True,
    }


def local_pairwise_quality(target: Sequence[int], score: Sequence[float]) -> np.ndarray:
    y = np.asarray(target, dtype=int)
    s = np.asarray(score, dtype=float)
    if len(y) == 0 or len(y) != len(s) or not np.isfinite(s).all() or not set(np.unique(y)).issubset({0, 1}):
        raise ForwardEvaluationBlocked("local pairwise quality requires finite aligned binary inputs")
    positive = np.flatnonzero(y == 1)
    negative = np.flatnonzero(y == 0)
    if len(positive) == 0 or len(negative) == 0:
        raise ForwardEvaluationBlocked("local pairwise quality requires both classes")
    result = np.empty(len(y), dtype=float)
    neg_scores = s[negative]
    pos_scores = s[positive]
    for index in positive:
        result[index] = (np.sum(neg_scores < s[index]) + 0.5 * np.sum(neg_scores == s[index])) / len(negative)
    for index in negative:
        result[index] = (np.sum(pos_scores > s[index]) + 0.5 * np.sum(pos_scores == s[index])) / len(positive)
    return result


def _ordinal_bucket(frame: pd.DataFrame, value_column: str, buckets: int) -> pd.Series:
    ordered = frame.sort_values([value_column, "ticker"], kind="mergesort")
    ordinal = np.arange(len(ordered), dtype=int)
    labels = (ordinal * buckets) // len(ordered) + 1
    result = pd.Series(index=ordered.index, data=labels, dtype=int)
    return result.reindex(frame.index)


def reliability_session_metrics(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = {"ticker", "binary_target", "score", "score_margin_reliability"}
    _require_columns(frame, required, label="Reliability session frame")
    data = frame.copy().sort_values("ticker", kind="mergesort").reset_index(drop=True)
    finite = np.isfinite(pd.to_numeric(data["score_margin_reliability"], errors="coerce").to_numpy(dtype=float))
    data = data.loc[finite].copy().reset_index(drop=True)
    if len(data) < 30 or data["binary_target"].nunique() != 2:
        return data.assign(local_pairwise_quality=np.nan), {
            "metric_eligible": False,
            "rows": int(len(data)),
            "spearman": float("nan"),
            "q4_minus_q1": float("nan"),
            "top40_lift": float("nan"),
            "conditional_lift": float("nan"),
        }
    data["local_pairwise_quality"] = local_pairwise_quality(data["binary_target"], data["score"])
    if data["score_margin_reliability"].nunique() < 2 or data["local_pairwise_quality"].nunique() < 2:
        spearman = float("nan")
    else:
        spearman = float(data["score_margin_reliability"].corr(data["local_pairwise_quality"], method="spearman"))
    data["reliability_quartile"] = _ordinal_bucket(data, "score_margin_reliability", 4)
    quartile = data.groupby("reliability_quartile", sort=True)["local_pairwise_quality"].mean()
    q4_minus_q1 = float(quartile.loc[4] - quartile.loc[1])

    top_n = int(math.ceil(0.4 * len(data)))
    top = data.sort_values(["score_margin_reliability", "ticker"], ascending=[False, True], kind="mergesort").head(top_n)
    top40_lift = float(top["local_pairwise_quality"].mean() - data["local_pairwise_quality"].mean())

    data["score_quintile"] = _ordinal_bucket(data, "score", 5)
    conditional_parts: list[float] = []
    for _, group in data.groupby("score_quintile", sort=True):
        if len(group) < 8 or group["score_margin_reliability"].nunique() < 2:
            continue
        half = _ordinal_bucket(group, "score_margin_reliability", 2)
        quality = group.assign(_half=half).groupby("_half")["local_pairwise_quality"].mean()
        conditional_parts.append(float(quality.loc[2] - quality.loc[1]))
    conditional = float(np.mean(conditional_parts)) if conditional_parts else float("nan")
    eligible = bool(np.isfinite([spearman, q4_minus_q1, top40_lift, conditional]).all())
    return data, {
        "metric_eligible": eligible,
        "rows": int(len(data)),
        "spearman": spearman,
        "q4_minus_q1": q4_minus_q1,
        "top40_lift": top40_lift,
        "conditional_lift": conditional,
    }


def _aggregate_reliability(per_session: pd.DataFrame) -> dict[str, float]:
    eligible = per_session[per_session["metric_eligible"]].copy()
    if eligible.empty:
        return {name: float("nan") for name in RELIABILITY_METRICS}
    return {
        "median_spearman": float(eligible["spearman"].median()),
        "mean_q4_minus_q1": float(eligible["q4_minus_q1"].mean()),
        "mean_top40_lift": float(eligible["top40_lift"].mean()),
        "mean_conditional_lift": float(eligible["conditional_lift"].mean()),
    }


def classify_reliability_decision(
    aggregate: Mapping[str, float],
    first_50: Mapping[str, float],
    last_50: Mapping[str, float],
    *,
    sidecars_valid_and_complete: bool,
    eligible_sessions: int,
    eligible_first_50: int,
    eligible_last_50: int,
) -> tuple[str, dict[str, bool]]:
    all_values = [*(aggregate[name] for name in RELIABILITY_METRICS), *(first_50[name] for name in RELIABILITY_METRICS), *(last_50[name] for name in RELIABILITY_METRICS)]
    finite = bool(np.isfinite(np.asarray(all_values, dtype=float)).all())
    readiness = bool(
        sidecars_valid_and_complete
        and eligible_sessions >= RELIABILITY_MIN_SESSIONS
        and eligible_first_50 >= RELIABILITY_MIN_HALF_SESSIONS
        and eligible_last_50 >= RELIABILITY_MIN_HALF_SESSIONS
        and finite
    )
    checks = {
        "sidecars_valid_and_complete": bool(sidecars_valid_and_complete),
        "eligible_sessions_at_least_80": eligible_sessions >= RELIABILITY_MIN_SESSIONS,
        "eligible_first_50_at_least_40": eligible_first_50 >= RELIABILITY_MIN_HALF_SESSIONS,
        "eligible_last_50_at_least_40": eligible_last_50 >= RELIABILITY_MIN_HALF_SESSIONS,
        "all_aggregate_metrics_finite": finite,
        "readiness_pass": readiness,
    }
    if not readiness:
        return "RELIABILITY_FORWARD_INCONCLUSIVE_DATA", checks
    full_positive = all(float(aggregate[name]) > 0 for name in RELIABILITY_METRICS)
    halves_positive = all(float(first_50[name]) > 0 and float(last_50[name]) > 0 for name in RELIABILITY_METRICS)
    if not full_positive:
        return "RELIABILITY_FORWARD_FAIL", checks
    if halves_positive:
        return "RELIABILITY_FORWARD_PASS", checks
    return "RELIABILITY_FORWARD_INCONCLUSIVE", checks


def evaluate_reliability(
    outcome_frame: pd.DataFrame,
    reliability: pd.DataFrame | None,
    sessions: pd.DataFrame,
    *,
    sidecars_valid_and_complete: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    dates = sessions["session_date"].tolist()
    base = outcome_frame[outcome_frame["binary_target"].notna()].copy()
    if reliability is None:
        merged = base.iloc[0:0].assign(score_margin_reliability=pd.Series(dtype=float))
    else:
        required = {"ticker", "date", "score_margin_reliability"}
        _require_columns(reliability, required, label="Reliability frame")
        sidecar = reliability.copy()
        sidecar["date"] = _normal_dates(sidecar["date"])
        sidecar["ticker"] = sidecar["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
        if sidecar.duplicated(["date", "ticker"]).any():
            raise ForwardEvaluationBlocked("Reliability keys are duplicated")
        extra = sidecar[["date", "ticker"]].merge(outcome_frame[["date", "ticker"]], how="left", indicator=True)
        if extra["_merge"].eq("left_only").any():
            raise ForwardEvaluationBlocked("Reliability contains rows outside exact O2 support")
        sidecar["score_margin_reliability"] = pd.to_numeric(sidecar["score_margin_reliability"], errors="coerce")
        merged = base.merge(sidecar[["date", "ticker", "score_margin_reliability"]], on=["date", "ticker"], how="left", validate="one_to_one")

    row_frames: list[pd.DataFrame] = []
    session_rows: list[dict[str, Any]] = []
    for date in dates:
        block = merged[merged["date"].eq(date)].copy()
        rows, metrics = reliability_session_metrics(block)
        rows["date"] = date
        row_frames.append(rows)
        session_rows.append({"date": date, **metrics})
    row_frame = pd.concat(row_frames, ignore_index=True) if row_frames else pd.DataFrame()
    per_session = pd.DataFrame(session_rows)
    first_mask = per_session["date"].isin(dates[:HALF_SESSIONS])
    aggregate = _aggregate_reliability(per_session)
    first = _aggregate_reliability(per_session[first_mask])
    last = _aggregate_reliability(per_session[~first_mask])
    eligible = per_session["metric_eligible"].astype(bool)
    eligible_first = int((eligible & first_mask).sum())
    eligible_last = int((eligible & ~first_mask).sum())
    decision, checks = classify_reliability_decision(
        aggregate,
        first,
        last,
        sidecars_valid_and_complete=sidecars_valid_and_complete,
        eligible_sessions=int(eligible.sum()),
        eligible_first_50=eligible_first,
        eligible_last_50=eligible_last,
    )
    return row_frame, per_session, {
        "decision": decision,
        "metric_eligible_sessions": int(eligible.sum()),
        "metric_eligible_first_50": eligible_first,
        "metric_eligible_last_50": eligible_last,
        "aggregate": aggregate,
        "first_50": first,
        "last_50": last,
        "checks": checks,
        "percentile_used_for_scientific_verdict": False,
    }


def joint_interpretation(o2_decision: str, reliability_decision: str) -> dict[str, Any]:
    allowed_o2 = {"O2_FORWARD_PASS", "O2_FORWARD_MIXED", "O2_FORWARD_FAIL"}
    allowed_reliability = {
        "RELIABILITY_FORWARD_PASS",
        "RELIABILITY_FORWARD_INCONCLUSIVE",
        "RELIABILITY_FORWARD_INCONCLUSIVE_DATA",
        "RELIABILITY_FORWARD_FAIL",
    }
    if o2_decision not in allowed_o2 or reliability_decision not in allowed_reliability:
        raise ForwardEvaluationBlocked("unknown frozen verdict")
    return {
        "o2_decision": o2_decision,
        "reliability_decision": reliability_decision,
        "controlling_alpha_decision": o2_decision,
        "reliability_can_rescue_o2": False,
        "composite_score_created": False,
        "o2_1_evaluated": False,
    }


def _write_synthetic_marker(marker_root: Path, *, pre_manifest_sha256: str, sessions: pd.DataFrame) -> Path:
    if marker_root.name == REAL_FORWARD_MARKER:
        raise ForwardEvaluationBlocked("synthetic runner cannot use the real forward marker")
    marker_root.mkdir(parents=True, exist_ok=True)
    marker = marker_root / SYNTHETIC_MARKER
    payload = {
        "marker": SYNTHETIC_MARKER,
        "synthetic_fixture_only": True,
        "pre_outcome_manifest_sha256": pre_manifest_sha256,
        "block_start": sessions.iloc[0]["session_date"].date().isoformat(),
        "block_end": sessions.iloc[-1]["session_date"].date().isoformat(),
    }
    try:
        with marker.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    except FileExistsError as exc:
        raise ForwardEvaluationBlocked(f"synthetic one-shot already consumed: {marker}") from exc
    return marker


def run_synthetic_forward_evaluation(
    *,
    output_dir: Path,
    marker_root: Path,
    fixture_root: Path,
    protocol_path: Path,
    session_inventory: pd.DataFrame,
    shared_artifacts: Mapping[str, Mapping[str, str]],
    o2_scores: pd.DataFrame,
    reliability: pd.DataFrame | None,
    outcome_loader: Callable[[], pd.DataFrame],
    code_commit: str,
    expected_protocol_sha256: str = PROTOCOL_SHA256,
    event_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Exercise the frozen one-shot protocol on explicitly non-protected data.

    This entry point deliberately cannot use the production marker or discover
    the forward runtime.  A separate pre-vault review must wire an authorized
    protected loader after the counter reaches 100/100.
    """

    output_dir = Path(output_dir)
    fixture_root = Path(fixture_root).resolve()
    marker_root = Path(marker_root)
    if (marker_root / REAL_FORWARD_MARKER).exists():
        raise ForwardEvaluationBlocked("real forward marker exists; synthetic runner refuses this location")
    if (marker_root / SYNTHETIC_MARKER).exists():
        raise ForwardEvaluationBlocked(f"synthetic one-shot already consumed: {marker_root / SYNTHETIC_MARKER}")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ForwardEvaluationBlocked("synthetic output directory must be new or empty")
    if not protocol_path.is_file() or sha256_file(protocol_path) != expected_protocol_sha256:
        raise ForwardEvaluationBlocked("frozen protocol hash mismatch")
    sessions = validate_session_inventory(session_inventory, fixture_root=fixture_root)
    verified_shared_artifacts = validate_named_artifacts(shared_artifacts, fixture_root=fixture_root)
    scores = validate_o2_scores(o2_scores, sessions)
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory_path = output_dir / "session_identity_inventory.parquet"
    write_parquet_atomic(sessions, inventory_path)
    pre_payload = {
        "schema": "idx-trade/forward-100-pre-outcome-contract-v1",
        "status": "SYNTHETIC_PRE_OUTCOME_CONTRACT_READY",
        "protocol_status": PROTOCOL_STATUS,
        "protocol_path": str(protocol_path),
        "protocol_sha256": expected_protocol_sha256,
        "protocol_commit": PROTOCOL_COMMIT,
        "evaluator_code_commit": code_commit,
        "o2_model_sha256": O2_MODEL_SHA256,
        "o2_feature_order_sha256": O2_FEATURE_ORDER_SHA256,
        "sessions": [
            {"date": row.session_date.date().isoformat(), "index": int(row.session_index)}
            for row in sessions.itertuples(index=False)
        ],
        "session_inventory_sha256": sha256_file(inventory_path),
        "shared_artifacts": verified_shared_artifacts,
        "source_artifact_hashes_verified": True,
        "synthetic_fixture_only": True,
        "protected_forward_outcomes_accessed": False,
        "real_forward_marker_written": False,
        "runtime_flags": {
            "provider_call": False,
            "model_refit": False,
            "threshold_optimization": False,
            "second_counter": False,
            "o2_1_evaluation": False,
            "pre_marker_outcome_access": False,
        },
        "environment": environment_manifest(
            source_paths=[Path(__file__), protocol_path],
            config={"phase": "SYNTHETIC_FORWARD_100_EVALUATOR", "protected_outcomes": False},
        ),
    }
    pre_payload["content_sha256"] = _canonical_hash(pre_payload)
    pre_path = output_dir / "pre_outcome_contract.json"
    _write_json(pre_path, pre_payload)
    if event_hook:
        event_hook("pre_outcome_manifest_written")

    marker = _write_synthetic_marker(marker_root, pre_manifest_sha256=sha256_file(pre_path), sessions=sessions)
    if event_hook:
        event_hook("synthetic_marker_written")
    outcomes = outcome_loader()
    if event_hook:
        event_hook("outcome_loader_returned")

    outcome_frame = materialize_outcome_frame(scores, outcomes)
    o2_result = evaluate_o2(outcome_frame, sessions, provenance_and_maturity_pass=True)
    reliability_complete = bool(
        sessions["reliability_path"].fillna("").astype(str).str.strip().ne("").all()
        and sessions["reliability_manifest_path"].fillna("").astype(str).str.strip().ne("").all()
    )
    reliability_rows, reliability_sessions, reliability_result = evaluate_reliability(
        outcome_frame,
        reliability,
        sessions,
        sidecars_valid_and_complete=reliability_complete,
    )
    joint = joint_interpretation(o2_result["decision"], reliability_result["decision"])

    artifact_paths = {
        "session_identity_inventory": inventory_path,
        "pre_outcome_contract": pre_path,
        "resolved_unresolved_outcomes": output_dir / "resolved_unresolved_outcomes.parquet",
        "o2_aggregate_metrics": output_dir / "o2_aggregate_metrics.json",
        "o2_half_metrics": output_dir / "o2_half_metrics.json",
        "o2_decision": output_dir / "o2_decision.json",
        "reliability_rows": output_dir / "reliability_rows.parquet",
        "reliability_sessions": output_dir / "reliability_sessions.parquet",
        "reliability_aggregate_metrics": output_dir / "reliability_aggregate_metrics.json",
        "reliability_decision": output_dir / "reliability_decision.json",
        "joint_interpretation": output_dir / "joint_interpretation.json",
        "runtime_flags": output_dir / "runtime_flags.json",
    }
    write_parquet_atomic(outcome_frame, artifact_paths["resolved_unresolved_outcomes"])
    _write_json(artifact_paths["o2_aggregate_metrics"], o2_result["aggregate"])
    _write_json(
        artifact_paths["o2_half_metrics"],
        {"first_50": o2_result["first_50"], "last_50": o2_result["last_50"]},
    )
    _write_json(
        artifact_paths["o2_decision"],
        {key: value for key, value in o2_result.items() if key not in {"aggregate", "first_50", "last_50"}},
    )
    write_parquet_atomic(reliability_rows, artifact_paths["reliability_rows"])
    write_parquet_atomic(reliability_sessions, artifact_paths["reliability_sessions"])
    _write_json(
        artifact_paths["reliability_aggregate_metrics"],
        {
            "aggregate": reliability_result["aggregate"],
            "first_50": reliability_result["first_50"],
            "last_50": reliability_result["last_50"],
        },
    )
    _write_json(artifact_paths["reliability_decision"], reliability_result)
    _write_json(artifact_paths["joint_interpretation"], joint)
    runtime_flags = {
        "synthetic_fixture_only": True,
        "real_forward_marker_written": False,
        "protected_forward_outcomes_accessed": False,
        "provider_call": False,
        "model_refit": False,
        "threshold_optimization": False,
        "second_counter": False,
        "o2_1_evaluated": False,
        "synthetic_marker_path": str(marker),
        "synthetic_marker_sha256": sha256_file(marker),
    }
    _write_json(artifact_paths["runtime_flags"], runtime_flags)
    hashes = {name: sha256_file(path) for name, path in sorted(artifact_paths.items())}
    manifest = {
        "schema": "idx-trade/forward-100-synthetic-evaluation-artifacts-v1",
        "status": "SYNTHETIC_FORWARD_100_EVALUATION_COMPLETE",
        "artifacts": {name: {"path": str(artifact_paths[name]), "sha256": hashes[name]} for name in sorted(hashes)},
        "o2_decision": o2_result["decision"],
        "reliability_decision": reliability_result["decision"],
        "runtime_flags": runtime_flags,
    }
    manifest["content_sha256"] = _canonical_hash(manifest)
    final_manifest = output_dir / "artifact_manifest.json"
    _write_json(final_manifest, manifest)
    return {
        "status": manifest["status"],
        "o2": o2_result,
        "reliability": reliability_result,
        "joint": joint,
        "artifact_manifest_path": str(final_manifest),
        "artifact_manifest_sha256": sha256_file(final_manifest),
        "synthetic_marker_path": str(marker),
    }
