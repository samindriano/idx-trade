from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import json

import numpy as np
import pandas as pd


class IntegrityStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class IntegrityStage(str, Enum):
    DATA_ADMISSION = "DATA_ADMISSION"
    RESEARCH_ADMISSION = "RESEARCH_ADMISSION"
    MODEL_PROMOTION = "MODEL_PROMOTION"


@dataclass(frozen=True)
class IntegrityCheck:
    check_id: str
    category: str
    status: IntegrityStatus
    summary: str
    required: bool = True
    evidence: Mapping[str, Any] = field(default_factory=dict)

    @property
    def blocking(self) -> bool:
        return self.required and self.status is not IntegrityStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["blocking"] = self.blocking
        return payload


@dataclass(frozen=True)
class IntegrityGateReport:
    stage: IntegrityStage
    checks: tuple[IntegrityCheck, ...]
    passed: bool
    blocking_check_ids: tuple[str, ...]
    nonblocking_findings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "passed": self.passed,
            "blocking_check_ids": list(self.blocking_check_ids),
            "nonblocking_findings": list(self.nonblocking_findings),
            "checks": [check.to_dict() for check in self.checks],
        }


def evaluate_integrity_gate(
    stage: IntegrityStage | str,
    checks: Iterable[IntegrityCheck],
    *,
    required_check_ids: Sequence[str] | None = None,
) -> IntegrityGateReport:
    """Evaluate an integrity gate fail-closed.

    Required checks must exist and be PASS. Missing required check IDs are
    materialized as UNKNOWN so absence of evidence cannot silently become a pass.
    Optional FAIL/UNKNOWN findings are retained but do not block the gate.
    """

    stage = IntegrityStage(stage)
    materialized = list(checks)
    for check in materialized:
        if not isinstance(check, IntegrityCheck):
            raise TypeError("Integrity checks must be IntegrityCheck instances")
        if not isinstance(check.status, IntegrityStatus):
            raise TypeError(f"Invalid integrity status for {check.check_id!r}")
        if not isinstance(check.check_id, str) or not check.check_id:
            raise ValueError("Integrity check IDs must be non-empty strings")
        if not isinstance(check.category, str) or not check.category:
            raise ValueError(f"Integrity check category must be non-empty: {check.check_id}")
        if not isinstance(check.evidence, Mapping):
            raise TypeError(f"Integrity check evidence must be an object: {check.check_id}")
    ids = [check.check_id for check in materialized]
    duplicated = sorted({value for value in ids if ids.count(value) > 1})
    if duplicated:
        raise ValueError(f"Duplicate integrity check IDs: {duplicated}")

    if required_check_ids is None or not required_check_ids:
        raise ValueError("At least one required integrity check ID must be supplied")

    required_ids = list(required_check_ids)
    duplicated_required = sorted({value for value in required_ids if required_ids.count(value) > 1})
    if duplicated_required:
        raise ValueError(f"Duplicate required integrity check IDs: {duplicated_required}")

    by_id = {check.check_id: check for check in materialized}
    for check_id in required_ids:
        if check_id not in by_id:
            missing = IntegrityCheck(
                check_id=check_id,
                category="MISSING_REQUIRED_CHECK",
                status=IntegrityStatus.UNKNOWN,
                summary="Required integrity check was not supplied.",
                required=True,
                evidence={"reason": "MISSING_REQUIRED_CHECK"},
            )
            materialized.append(missing)
            by_id[check_id] = missing

    required_set = set(required_ids)
    if required_set:
        normalized: list[IntegrityCheck] = []
        for check in materialized:
            if check.check_id in required_set and not check.required:
                check = IntegrityCheck(
                    check_id=check.check_id,
                    category=check.category,
                    status=check.status,
                    summary=check.summary,
                    required=True,
                    evidence=check.evidence,
                )
            normalized.append(check)
        materialized = normalized

    evidenced: list[IntegrityCheck] = []
    for check in materialized:
        if check.required and check.status is IntegrityStatus.PASS and not check.evidence:
            check = IntegrityCheck(
                check_id=check.check_id,
                category=check.category,
                status=IntegrityStatus.UNKNOWN,
                summary="Required PASS has no supporting evidence.",
                required=True,
                evidence={"reason": "MISSING_PASS_EVIDENCE"},
            )
        evidenced.append(check)
    materialized = evidenced

    blockers = tuple(check.check_id for check in materialized if check.blocking)
    nonblocking = tuple(
        check.check_id
        for check in materialized
        if not check.required and check.status is not IntegrityStatus.PASS
    )
    return IntegrityGateReport(
        stage=stage,
        checks=tuple(materialized),
        passed=not blockers,
        blocking_check_ids=blockers,
        nonblocking_findings=nonblocking,
    )


def assert_integrity_gate(report: IntegrityGateReport | Mapping[str, Any]) -> None:
    if isinstance(report, IntegrityGateReport):
        passed = report.passed
        blockers = list(report.blocking_check_ids)
        stage = report.stage.value
    else:
        if not isinstance(report, Mapping):
            raise TypeError("Integrity gate assertion requires an IntegrityGateReport")
        stage_raw = report.get("stage")
        checks_raw = report.get("checks")
        if not isinstance(stage_raw, str) or not isinstance(checks_raw, list) or not checks_raw:
            raise RuntimeError("Serialized integrity gate report is malformed; refusing assertion")
        try:
            serialized_checks: list[IntegrityCheck] = []
            for row in checks_raw:
                if not isinstance(row, Mapping):
                    raise ValueError("serialized check is not an object")
                evidence = row.get("evidence", {})
                if not isinstance(evidence, Mapping):
                    raise ValueError("serialized evidence is not an object")
                serialized_checks.append(
                    IntegrityCheck(
                        check_id=str(row["check_id"]),
                        category=str(row["category"]),
                        status=IntegrityStatus(str(row["status"])),
                        summary=str(row.get("summary", "")),
                        required=bool(row.get("required", True)),
                        evidence=dict(evidence),
                    )
                )
            required = tuple(check.check_id for check in serialized_checks if check.required)
            if not required:
                raise ValueError("serialized report contains no required checks")
            reconstructed = evaluate_integrity_gate(
                IntegrityStage(stage_raw),
                serialized_checks,
                required_check_ids=required,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Serialized integrity gate report is malformed: {exc}") from exc
        expected_blockers = list(reconstructed.blocking_check_ids)
        expected_passed = reconstructed.passed
        actual_blockers = report.get("blocking_check_ids")
        actual_passed = report.get("passed")
        if not isinstance(actual_blockers, list) or not isinstance(actual_passed, bool):
            raise RuntimeError("Serialized integrity gate report is malformed; refusing assertion")
        if actual_blockers != expected_blockers or actual_passed != expected_passed:
            raise RuntimeError("Serialized integrity gate report is internally inconsistent")
        passed = expected_passed
        blockers = expected_blockers
        stage = reconstructed.stage.value
    if not passed:
        raise RuntimeError(f"{stage} integrity gate failed; blockers={blockers}")


def load_gate_profile(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Gate profile must be a JSON object")
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported research-integrity gate profile schema")
    if not isinstance(payload.get("profile_id"), str) or not payload["profile_id"]:
        raise ValueError("Gate profile must contain a non-empty profile_id")
    if payload.get("fail_closed") is not True or payload.get("unknown_blocks_promotion") is not True:
        raise ValueError("Gate profile must explicitly enable fail-closed UNKNOWN blocking")
    stages = payload.get("stages")
    if not isinstance(stages, dict) or not stages:
        raise ValueError("Gate profile must contain non-empty stages")
    for stage_name, stage_payload in stages.items():
        if not isinstance(stage_name, str) or not isinstance(stage_payload, Mapping):
            raise ValueError("Gate profile stages must be named objects")
        values = stage_payload.get("required_check_ids")
        if not isinstance(values, list) or not values:
            raise ValueError(f"Gate profile stage must declare required checks: {stage_name}")
    return payload


def required_checks_for_stage(profile: Mapping[str, Any], stage: IntegrityStage | str) -> tuple[str, ...]:
    stage = IntegrityStage(stage)
    stage_payload = profile.get("stages", {}).get(stage.value)
    if not isinstance(stage_payload, Mapping):
        raise KeyError(f"Stage missing from gate profile: {stage.value}")
    values = stage_payload.get("required_check_ids", [])
    if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
        raise ValueError(f"Invalid required_check_ids for {stage.value}")
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate required_check_ids for {stage.value}")
    return tuple(values)


def check_required_columns(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    check_id: str = "schema.required_columns",
    required: bool = True,
) -> IntegrityCheck:
    missing = sorted(set(columns) - set(frame.columns))
    return IntegrityCheck(
        check_id=check_id,
        category="SCHEMA_UNITS",
        status=IntegrityStatus.FAIL if missing else IntegrityStatus.PASS,
        summary="Required columns are present." if not missing else "Required columns are missing.",
        required=required,
        evidence={"missing_columns": missing, "required_columns": list(columns)},
    )


def check_unique_key(
    frame: pd.DataFrame,
    key_columns: Sequence[str],
    *,
    check_id: str = "schema.unique_key",
    required: bool = True,
) -> IntegrityCheck:
    missing = sorted(set(key_columns) - set(frame.columns))
    if missing:
        return IntegrityCheck(
            check_id=check_id,
            category="KEY_UNIQUENESS",
            status=IntegrityStatus.UNKNOWN,
            summary="Unique-key check cannot run because key columns are missing.",
            required=required,
            evidence={"missing_columns": missing},
        )
    if frame.empty:
        return IntegrityCheck(
            check_id=check_id,
            category="KEY_UNIQUENESS",
            status=IntegrityStatus.UNKNOWN,
            summary="Unique-key check cannot certify an empty dataset.",
            required=required,
            evidence={"reason": "EMPTY_DATASET", "key_columns": list(key_columns)},
        )
    duplicated = frame.duplicated(list(key_columns), keep=False)
    null_keys = frame.loc[:, list(key_columns)].isna().any(axis=1)
    examples = frame.loc[duplicated | null_keys, list(key_columns)].head(10).to_dict(orient="records")
    count = int(duplicated.sum())
    null_count = int(null_keys.sum())
    return IntegrityCheck(
        check_id=check_id,
        category="KEY_UNIQUENESS",
        status=IntegrityStatus.FAIL if count or null_count else IntegrityStatus.PASS,
        summary="Key is unique and populated." if not count and not null_count else "Duplicate or null key rows detected.",
        required=required,
        evidence={
            "duplicate_rows": count,
            "null_key_rows": null_count,
            "examples": examples,
            "key_columns": list(key_columns),
        },
    )


def check_nonnegative(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    allow_na: bool = True,
    check_id: str = "values.nonnegative",
    required: bool = True,
) -> IntegrityCheck:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        return IntegrityCheck(
            check_id=check_id,
            category="VALUE_DOMAIN",
            status=IntegrityStatus.UNKNOWN,
            summary="Non-negative domain check cannot run because columns are missing.",
            required=required,
            evidence={"missing_columns": missing},
        )
    if frame.empty:
        return IntegrityCheck(
            check_id=check_id,
            category="VALUE_DOMAIN",
            status=IntegrityStatus.UNKNOWN,
            summary="Non-negative domain check cannot certify an empty dataset.",
            required=required,
            evidence={"reason": "EMPTY_DATASET", "columns": list(columns)},
        )
    bad_mask = pd.Series(False, index=frame.index)
    for column in columns:
        source = frame[column]
        numeric = pd.to_numeric(source, errors="coerce")
        bad_mask |= numeric.lt(0)
        bad_mask |= numeric.isna() & source.notna()
        bad_mask |= numeric.notna() & ~np.isfinite(numeric)
        if not allow_na:
            bad_mask |= numeric.isna()
    count = int(bad_mask.sum())
    return IntegrityCheck(
        check_id=check_id,
        category="VALUE_DOMAIN",
        status=IntegrityStatus.FAIL if count else IntegrityStatus.PASS,
        summary="Numeric domain is valid." if not count else "Invalid negative, non-numeric, or disallowed missing values detected.",
        required=required,
        evidence={"invalid_rows": count, "columns": list(columns), "allow_na": allow_na},
    )


def check_allowed_values(
    frame: pd.DataFrame,
    column: str,
    allowed_values: Sequence[Any],
    *,
    allow_na: bool = False,
    check_id: str = "units.contract",
    category: str = "UNITS_CONTRACT",
    required: bool = True,
) -> IntegrityCheck:
    if column not in frame.columns:
        return IntegrityCheck(
            check_id=check_id,
            category=category,
            status=IntegrityStatus.UNKNOWN,
            summary="Allowed-values check cannot run because the column is missing.",
            required=required,
            evidence={"missing_column": column},
        )
    if frame.empty:
        return IntegrityCheck(
            check_id=check_id,
            category=category,
            status=IntegrityStatus.UNKNOWN,
            summary="Allowed-values check cannot certify an empty dataset.",
            required=required,
            evidence={"reason": "EMPTY_DATASET", "column": column},
        )
    series = frame[column]
    allowed = list(allowed_values)
    invalid = ~series.isin(allowed)
    if allow_na:
        invalid &= series.notna()
    count = int(invalid.sum())
    examples = series.loc[invalid].astype(str).drop_duplicates().head(10).tolist()
    return IntegrityCheck(
        check_id=check_id,
        category=category,
        status=IntegrityStatus.FAIL if count else IntegrityStatus.PASS,
        summary="Values satisfy the declared contract." if not count else "Values outside the declared contract were detected.",
        required=required,
        evidence={
            "column": column,
            "allowed_values": allowed,
            "allow_na": allow_na,
            "invalid_rows": count,
            "invalid_examples": examples,
        },
    )


def check_session_membership(
    frame: pd.DataFrame,
    official_sessions: Sequence[Any] | pd.DatetimeIndex,
    *,
    session_column: str,
    check_id: str = "calendar.session_membership",
    required: bool = True,
) -> IntegrityCheck:
    if session_column not in frame.columns:
        return IntegrityCheck(
            check_id=check_id,
            category="SESSION_CALENDAR",
            status=IntegrityStatus.UNKNOWN,
            summary="Session-membership check cannot run because the session column is missing.",
            required=required,
            evidence={"missing_column": session_column},
        )
    if frame.empty:
        return IntegrityCheck(
            check_id=check_id,
            category="SESSION_CALENDAR",
            status=IntegrityStatus.UNKNOWN,
            summary="Session-membership check cannot certify an empty dataset.",
            required=required,
            evidence={"reason": "EMPTY_DATASET", "session_column": session_column},
        )
    observed = pd.to_datetime(frame[session_column], errors="coerce")
    observed_keys = observed.dt.strftime("%Y-%m-%d")
    official = pd.to_datetime(pd.Index(official_sessions), errors="coerce")
    official_keys = set(pd.Series(official).dropna().dt.strftime("%Y-%m-%d").tolist())
    invalid = observed.isna() | ~observed_keys.isin(official_keys)
    count = int(invalid.sum())
    examples = frame.loc[invalid, session_column].astype(str).drop_duplicates().head(10).tolist()
    return IntegrityCheck(
        check_id=check_id,
        category="SESSION_CALENDAR",
        status=IntegrityStatus.FAIL if count else IntegrityStatus.PASS,
        summary="All observations map to accepted official sessions." if not count else "Non-session or invalid session observations detected.",
        required=required,
        evidence={"invalid_rows": count, "invalid_examples": examples, "session_column": session_column},
    )


def check_missingness_policy(
    frame: pd.DataFrame,
    max_missing_fraction: Mapping[str, float],
    *,
    check_id: str = "missingness.policy",
    required: bool = True,
) -> IntegrityCheck:
    missing_columns = sorted(set(max_missing_fraction) - set(frame.columns))
    if missing_columns:
        return IntegrityCheck(
            check_id=check_id,
            category="MISSINGNESS_POLICY",
            status=IntegrityStatus.UNKNOWN,
            summary="Missingness policy cannot run because governed columns are missing.",
            required=required,
            evidence={"missing_columns": missing_columns},
        )
    if frame.empty:
        return IntegrityCheck(
            check_id=check_id,
            category="MISSINGNESS_POLICY",
            status=IntegrityStatus.UNKNOWN,
            summary="Missingness policy cannot certify an empty dataset.",
            required=required,
            evidence={"reason": "EMPTY_DATASET"},
        )
    violations: dict[str, dict[str, float]] = {}
    observed: dict[str, float] = {}
    for column, limit in max_missing_fraction.items():
        if not 0.0 <= float(limit) <= 1.0:
            raise ValueError(f"Missingness limit must be in [0, 1]: {column}={limit}")
        fraction = float(frame[column].isna().mean()) if len(frame) else 0.0
        observed[column] = fraction
        if fraction > float(limit):
            violations[column] = {"observed": fraction, "limit": float(limit)}
    return IntegrityCheck(
        check_id=check_id,
        category="MISSINGNESS_POLICY",
        status=IntegrityStatus.FAIL if violations else IntegrityStatus.PASS,
        summary="Missingness is within the declared policy." if not violations else "Missingness policy violations detected.",
        required=required,
        evidence={"observed_missing_fraction": observed, "violations": violations},
    )


def check_ohlc_identity(
    frame: pd.DataFrame,
    *,
    check_id: str = "market.ohlc_identity",
    required: bool = True,
) -> IntegrityCheck:
    columns = ("open", "high", "low", "close")
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        return IntegrityCheck(
            check_id=check_id,
            category="ECONOMIC_IDENTITY",
            status=IntegrityStatus.UNKNOWN,
            summary="OHLC identity cannot run because columns are missing.",
            required=required,
            evidence={"missing_columns": missing},
        )
    if frame.empty:
        return IntegrityCheck(
            check_id=check_id,
            category="ECONOMIC_IDENTITY",
            status=IntegrityStatus.UNKNOWN,
            summary="OHLC identity cannot certify an empty dataset.",
            required=required,
            evidence={"reason": "EMPTY_DATASET"},
        )
    numeric = frame.loc[:, columns].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)
    bad = (
        numeric.isna().any(axis=1)
        | ~finite
        | numeric.le(0).any(axis=1)
        | numeric["high"].lt(numeric[["open", "close"]].max(axis=1))
        | numeric["low"].gt(numeric[["open", "close"]].min(axis=1))
        | numeric["high"].lt(numeric["low"])
    )
    count = int(bad.sum())
    return IntegrityCheck(
        check_id=check_id,
        category="ECONOMIC_IDENTITY",
        status=IntegrityStatus.FAIL if count else IntegrityStatus.PASS,
        summary="OHLC identities hold." if not count else "Impossible OHLC rows detected.",
        required=required,
        evidence={"invalid_rows": count},
    )


def check_additive_identity(
    frame: pd.DataFrame,
    *,
    lhs: str,
    positive: str,
    negative: str,
    atol: float = 0.0,
    rtol: float = 0.0,
    check_id: str = "values.additive_identity",
    required: bool = True,
) -> IntegrityCheck:
    columns = (lhs, positive, negative)
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        return IntegrityCheck(
            check_id=check_id,
            category="ECONOMIC_IDENTITY",
            status=IntegrityStatus.UNKNOWN,
            summary="Additive identity cannot run because columns are missing.",
            required=required,
            evidence={"missing_columns": missing},
        )
    if frame.empty:
        return IntegrityCheck(
            check_id=check_id,
            category="ECONOMIC_IDENTITY",
            status=IntegrityStatus.UNKNOWN,
            summary="Additive identity cannot certify an empty dataset.",
            required=required,
            evidence={"reason": "EMPTY_DATASET", "identity": f"{lhs} == {positive} - {negative}"},
        )
    lhs_values = pd.to_numeric(frame[lhs], errors="coerce").to_numpy(dtype=float)
    rhs_values = (
        pd.to_numeric(frame[positive], errors="coerce").to_numpy(dtype=float)
        - pd.to_numeric(frame[negative], errors="coerce").to_numpy(dtype=float)
    )
    finite = np.isfinite(lhs_values) & np.isfinite(rhs_values)
    matches = np.zeros(len(frame), dtype=bool)
    matches[finite] = np.isclose(lhs_values[finite], rhs_values[finite], atol=atol, rtol=rtol)
    invalid = ~matches
    count = int(invalid.sum())
    return IntegrityCheck(
        check_id=check_id,
        category="ECONOMIC_IDENTITY",
        status=IntegrityStatus.FAIL if count else IntegrityStatus.PASS,
        summary="Additive identity holds." if not count else "Additive identity violations detected.",
        required=required,
        evidence={
            "invalid_rows": count,
            "identity": f"{lhs} == {positive} - {negative}",
            "atol": atol,
            "rtol": rtol,
        },
    )


def check_knowledge_time(
    frame: pd.DataFrame,
    *,
    knowledge_column: str,
    decision_column: str,
    allow_equal: bool = True,
    check_id: str = "pit.knowledge_time",
    required: bool = True,
) -> IntegrityCheck:
    columns = (knowledge_column, decision_column)
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        return IntegrityCheck(
            check_id=check_id,
            category="PIT_KNOWLEDGE_TIME",
            status=IntegrityStatus.UNKNOWN,
            summary="PIT knowledge-time check cannot run because columns are missing.",
            required=required,
            evidence={"missing_columns": missing},
        )
    knowledge_source = frame[knowledge_column]
    decision_source = frame[decision_column]

    def _naive_timestamp_mask(series: pd.Series) -> pd.Series:
        values: list[bool] = []
        for value in series.tolist():
            try:
                if bool(pd.isna(value)):
                    values.append(False)
                    continue
                timestamp = pd.Timestamp(value)
                values.append(timestamp.tzinfo is None or timestamp.tz is None)
            except (TypeError, ValueError, OverflowError):
                values.append(False)
        return pd.Series(values, index=series.index, dtype=bool)

    knowledge_naive = _naive_timestamp_mask(knowledge_source)
    decision_naive = _naive_timestamp_mask(decision_source)
    knowledge = pd.to_datetime(knowledge_source, errors="coerce", utc=True)
    decision = pd.to_datetime(decision_source, errors="coerce", utc=True)
    bad = knowledge.isna() | decision.isna() | knowledge_naive | decision_naive
    bad |= knowledge.gt(decision) if allow_equal else knowledge.ge(decision)
    count = int(bad.sum())
    return IntegrityCheck(
        check_id=check_id,
        category="PIT_KNOWLEDGE_TIME",
        status=IntegrityStatus.FAIL if count else IntegrityStatus.PASS,
        summary="Knowledge timestamps are causally admissible." if not count else "Future/unknown knowledge timestamps detected.",
        required=required,
        evidence={
            "invalid_rows": count,
            "knowledge_column": knowledge_column,
            "decision_column": decision_column,
            "allow_equal": allow_equal,
            "naive_timestamp_rows": int((knowledge_naive | decision_naive).sum()),
        },
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_file_hashes(
    expected_sha256: Mapping[str | Path, str],
    *,
    check_id: str = "provenance.hashes",
    required: bool = True,
) -> IntegrityCheck:
    if not expected_sha256:
        return IntegrityCheck(
            check_id=check_id,
            category="PROVENANCE_HASHES",
            status=IntegrityStatus.UNKNOWN,
            summary="No expected artifact hashes were supplied.",
            required=required,
            evidence={"reason": "EMPTY_EXPECTATION"},
        )
    missing: list[str] = []
    mismatches: list[dict[str, str]] = []
    verified: list[dict[str, str]] = []
    for raw_path, expected in expected_sha256.items():
        path = Path(raw_path)
        expected_normalized = str(expected).lower()
        if len(expected_normalized) != 64 or any(char not in "0123456789abcdef" for char in expected_normalized):
            raise ValueError(f"Invalid SHA-256 expectation for {path}")
        if not path.is_file():
            missing.append(str(path))
            continue
        actual = _sha256_file(path)
        row = {"path": str(path), "expected_sha256": expected_normalized, "actual_sha256": actual}
        if actual != expected_normalized:
            mismatches.append(row)
        else:
            verified.append(row)

    if mismatches:
        status = IntegrityStatus.FAIL
        summary = "Artifact hash mismatches detected."
    elif missing:
        status = IntegrityStatus.UNKNOWN
        summary = "Expected artifacts are missing; provenance cannot be certified."
    else:
        status = IntegrityStatus.PASS
        summary = "Artifact hashes match immutable expectations."
    return IntegrityCheck(
        check_id=check_id,
        category="PROVENANCE_HASHES",
        status=status,
        summary=summary,
        required=required,
        evidence={"missing_paths": missing, "mismatches": mismatches, "verified": verified},
    )
