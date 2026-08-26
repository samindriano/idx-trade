from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
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
    required_check_ids: Sequence[str] = (),
) -> IntegrityGateReport:
    """Evaluate an integrity gate fail-closed.

    Required checks must exist and be PASS. Missing required check IDs are
    materialized as UNKNOWN so absence of evidence cannot silently become a pass.
    Optional FAIL/UNKNOWN findings are retained but do not block the gate.
    """

    stage = IntegrityStage(stage)
    materialized = list(checks)
    ids = [check.check_id for check in materialized]
    duplicated = sorted({value for value in ids if ids.count(value) > 1})
    if duplicated:
        raise ValueError(f"Duplicate integrity check IDs: {duplicated}")

    by_id = {check.check_id: check for check in materialized}
    for check_id in required_check_ids:
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

    required_set = set(required_check_ids)
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
        passed = bool(report.get("passed", False))
        blockers = list(report.get("blocking_check_ids", []))
        stage = str(report.get("stage", "UNKNOWN_STAGE"))
    if not passed:
        raise RuntimeError(f"{stage} integrity gate failed; blockers={blockers}")


def load_gate_profile(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported research-integrity gate profile schema")
    stages = payload.get("stages")
    if not isinstance(stages, dict) or not stages:
        raise ValueError("Gate profile must contain non-empty stages")
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
    duplicated = frame.duplicated(list(key_columns), keep=False)
    examples = frame.loc[duplicated, list(key_columns)].head(10).to_dict(orient="records")
    count = int(duplicated.sum())
    return IntegrityCheck(
        check_id=check_id,
        category="KEY_UNIQUENESS",
        status=IntegrityStatus.FAIL if count else IntegrityStatus.PASS,
        summary="Key is unique." if not count else "Duplicate key rows detected.",
        required=required,
        evidence={"duplicate_rows": count, "examples": examples, "key_columns": list(key_columns)},
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
    bad_mask = pd.Series(False, index=frame.index)
    for column in columns:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        bad_mask |= numeric.lt(0)
        if not allow_na:
            bad_mask |= numeric.isna()
    count = int(bad_mask.sum())
    return IntegrityCheck(
        check_id=check_id,
        category="VALUE_DOMAIN",
        status=IntegrityStatus.FAIL if count else IntegrityStatus.PASS,
        summary="Numeric domain is valid." if not count else "Invalid negative or missing values detected.",
        required=required,
        evidence={"invalid_rows": count, "columns": list(columns), "allow_na": allow_na},
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
    numeric = frame.loc[:, columns].apply(pd.to_numeric, errors="coerce")
    bad = (
        numeric.isna().any(axis=1)
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
    knowledge = pd.to_datetime(frame[knowledge_column], errors="coerce", utc=True)
    decision = pd.to_datetime(frame[decision_column], errors="coerce", utc=True)
    bad = knowledge.isna() | decision.isna()
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
        },
    )
