"""Fail-closed V4-X1 runtime population admission boundary.

This module is deliberately outside the frozen scorer and EOD pipeline.  It
proves that a same-session DATA_READY capture has a population compatible with
the frozen V1 identity/tradability policy before the scorer is entered.  It
never edits the frozen population, scorer, model, rank, percentile, or
counter; a failed proof only produces ``V1_POPULATION_NOT_PROVABLE``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence
from uuid import uuid4
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .e2e_cloud_security_master_v1 import (
    SCHEMA_VERSION as SECURITY_MASTER_REFRESH_SCHEMA_VERSION,
)
from .forward_monitoring import (
    _candidate_tables,
    _existing_session,
    _table_columns,
    _verify_ready_artifacts,
    runtime_paths,
)
from .forward_ohlcv import SESSION_OHLCV_COLUMNS, validate_model_input_regular_market_value
from .provenance import sha256_file
from .security_master import (
    COVERAGE_WINDOW_COLUMNS,
    TRADABILITY_ANCHOR_COLUMNS,
    TRADABILITY_COLUMNS,
    _point_states_compatible,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
    tradability_state,
)
from .states import TradabilityState
from .providers.idx import IDX_DELISTING_URL, IDX_STOCK_LIST_URL


SCHEMA_VERSION = "idx_trade_v4_x1_population_admission_v1"
SAFE_V1_POPULATION = "SAFE_V1_POPULATION"
V1_POPULATION_NOT_PROVABLE = "V1_POPULATION_NOT_PROVABLE"
PROVEN_V1_POPULATION_COMPATIBLE = "PROVEN_V1_POPULATION_COMPATIBLE"
NOT_PROVABLE_FROM_RETAINED_EVIDENCE = "NOT_PROVABLE_FROM_RETAINED_EVIDENCE"
FREEZE_LOCAL_DATE = date(2026, 8, 20)
FROZEN_POLICY = (
    "ACCEPTED_CLEAN_BASELINE_PLUS_RUNTIME_IDENTITIES_WITH_LISTED_FROM_STRICTLY_AFTER_2026_08_20_ONLY"
)
JAKARTA = ZoneInfo("Asia/Jakarta")
TICKER_RE = re.compile(r"^[A-Z0-9]{4}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
SECURITY_MASTER_REFRESH_SEMANTICS = (
    "CURRENT_ACTIVE_REFERENCE_PLUS_FROZEN_BASELINE_IDENTITY_CONTINUITY_AND_POST_FREEZE_DELISTING_HISTORY"
)
SECURITY_MASTER_ACTIVE_COMPLETENESS = "RECORDS_TOTAL_EXACT_SINGLE_RESPONSE"
SECURITY_MASTER_DELISTING_COMPLETENESS = (
    "MONTHLY_META_TOTAL_ITEMS_EXHAUSTIVE_PAGINATION"
)
_ATTESTATION_RUNTIME_HASH_FIELDS = (
    "security_master_refresh_manifest_sha256",
    "tradability_intervals_sha256",
    "tradability_coverage_sha256",
    "tradability_anchors_sha256",
    "feature_basis_evidence_sha256",
    "feature_basis_manifest_sha256",
    "feature_basis_trust_contract_sha256",
)

FEATURE_BASIS_SCHEMA_VERSION = "idx_trade_forward_feature_basis_v1"
FEATURE_BASIS_POLICY_ID = "FORWARD_FEATURE_BASIS_ACCEPTANCE_GATE_V1"
FEATURE_BASIS_EVIDENCE_FILENAME = "feature_basis_evidence.json"
FEATURE_BASIS_MANIFEST_SCHEMA_VERSION = "idx_trade_forward_feature_basis_manifest_v1"
FEATURE_BASIS_MANIFEST_FILENAME = "feature_basis_evidence_manifest.json"
FEATURE_BASIS_PRODUCER_ID = "idx_trade_forward_feature_basis_producer_v1"
BASIS_SAFE = "BASIS_SAFE"
BASIS_TRANSITION_OVERLAP = "BASIS_TRANSITION_OVERLAP"
BASIS_UNRESOLVED = "BASIS_UNRESOLVED"
SOURCE_CAPTURE_UNRESOLVED = "SOURCE_CAPTURE_UNRESOLVED"
FEATURE_BASIS_STATES = (
    "CERTIFIED_TRANSITION",
    "CERTIFIED_SAME_BASIS",
    "NO_KNOWN_TRANSITION",
    "BASIS_UNKNOWN",
    "SOURCE_CAPTURE_UNRESOLVED",
)
FEATURE_BASIS_FIELD_STATES = {"CERTIFIED_SAME_BASIS", "CERTIFIED_TRANSITION"}
FEATURE_BASIS_FIELDS = ("high", "low", "close", "volume", "regular_market_value")

# This is contract metadata only.  The frozen feature formulas remain in the
# pinned scorer modules.  The spans are the exact potential mixed-basis spans
# of the 28 final features recorded by the frozen feature-window audit.
FEATURE_BASIS_WINDOW_CONTRACT = (
    ("xs_rank_close_return_5", 4),
    ("xs_rank_close_return_20", 19),
    ("xs_rank_atr14_over_close", 13),
    ("xs_rank_close_position_20", 19),
    ("xs_rank_distance_high_20_atr", 19),
    ("xs_rank_distance_low_20_atr", 19),
    ("xs_rank_distance_high_60_atr", 59),
    ("xs_rank_distance_low_60_atr", 59),
    ("xs_rank_relative_volume_20", 19),
    ("xs_rank_log_regular_value_relative_20", 19),
    ("market_primary_liquid_count", 59),
    ("market_breadth_return_5_positive", 4),
    ("market_breadth_return_20_positive", 19),
    ("market_median_close_return_5", 4),
    ("market_median_close_return_20", 19),
    ("market_median_atr14_over_close", 13),
    ("market_median_close_position_20", 19),
    ("market_median_relative_volume_20", 19),
    ("market_median_log_regular_value_relative_20", 19),
    ("market_relative_close_return_5", 4),
    ("market_relative_close_return_20", 19),
    ("market_relative_atr14_over_close", 13),
    ("market_relative_close_position_20", 19),
    ("market_relative_relative_volume_20", 19),
    ("market_relative_log_regular_value_relative_20", 19),
    ("session_open_position_range", 0),
    ("session_body_signed_range", 0),
    ("session_log_high_low_range", 0),
)


class PopulationAdmissionConflict(RuntimeError):
    """An immutable admission marker was asked to change identity."""


@dataclass(frozen=True)
class PopulationAdmission:
    status: str
    session_date: str
    expected_identity_tickers: tuple[str, ...]
    observed_model_input_tickers: tuple[str, ...]
    identity_added_tickers: tuple[str, ...]
    identity_removed_tickers: tuple[str, ...]
    reason_codes: tuple[str, ...]
    identity_cases: Mapping[str, Any]
    expected_identity_set_sha256: str
    observed_model_input_set_sha256: str
    metadata: Mapping[str, Any]
    attestation_path: str | None = None
    attestation_sha256: str | None = None

    @property
    def safe(self) -> bool:
        return self.status == SAFE_V1_POPULATION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": self.status,
            "session_date": self.session_date,
            "expected_identity_tickers": list(self.expected_identity_tickers),
            "observed_model_input_tickers": list(self.observed_model_input_tickers),
            "identity_added_tickers": list(self.identity_added_tickers),
            "identity_removed_tickers": list(self.identity_removed_tickers),
            "reason_codes": list(self.reason_codes),
            "identity_cases": dict(self.identity_cases),
            "expected_identity_set_sha256": self.expected_identity_set_sha256,
            "observed_model_input_set_sha256": self.observed_model_input_set_sha256,
            "metadata": dict(self.metadata),
            **({"attestation_path": self.attestation_path} if self.attestation_path else {}),
            **({"attestation_sha256": self.attestation_sha256} if self.attestation_sha256 else {}),
        }


class V1PopulationNotProvable(RuntimeError):
    """Raised inside the frozen pipeline adapter before scorer entry."""

    def __init__(self, admission: PopulationAdmission):
        self.admission = admission
        super().__init__(V1_POPULATION_NOT_PROVABLE)


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _set_hash(values: Sequence[str]) -> str:
    return hashlib.sha256(_canonical_json(sorted(set(values)))).hexdigest()


def _feature_basis_window_contract_payload() -> list[dict[str, Any]]:
    return [
        {"feature": feature, "potential_mixed_basis_span": span}
        for feature, span in FEATURE_BASIS_WINDOW_CONTRACT
    ]


def _feature_basis_window_contract_sha256() -> str:
    return hashlib.sha256(
        _canonical_json(_feature_basis_window_contract_payload())
    ).hexdigest()


def _safe_session(value: object) -> str:
    try:
        parsed = pd.Timestamp(value).tz_localize(None).normalize()
    except (TypeError, ValueError) as exc:
        raise ValueError("SESSION_DATE_INVALID") from exc
    if pd.isna(parsed):
        raise ValueError("SESSION_DATE_INVALID")
    return parsed.date().isoformat()


def _safe_observed_at(value: object) -> str:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("OBSERVED_AT_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("OBSERVED_AT_NOT_TIMEZONE_AWARE")
    return parsed.astimezone(JAKARTA).isoformat()


def _safe_ticker(value: object) -> str:
    value = "" if value is None else str(value).upper().replace(".JK", "").strip()
    if not TICKER_RE.fullmatch(value):
        raise ValueError("TICKER_INVALID")
    return value


def _sha(value: object, label: str) -> str:
    result = str(value or "").strip().lower()
    if not HEX64_RE.fullmatch(result):
        raise ValueError(f"{label}_SHA_INVALID")
    return result


def _manifest_relative_path(base: Path, value: object, label: str) -> Path:
    """Resolve a manifest child without allowing absolute or escaping paths."""

    raw = str(value or "").strip()
    declared = Path(raw)
    if not raw or declared.is_absolute():
        raise ValueError(f"{label}_PATH_INVALID")
    resolved_base = base.expanduser().resolve()
    resolved = (resolved_base / declared).resolve()
    if resolved != resolved_base and resolved_base not in resolved.parents:
        raise ValueError(f"{label}_PATH_OUTSIDE_ROOT")
    return resolved


def _feature_basis_manifest_identity(manifest: Mapping[str, Any]) -> str:
    """Hash stable manifest policy/content fields without circular evidence hash."""

    payload = dict(manifest)
    payload.pop("manifest_id", None)
    payload.pop("evidence_sha256", None)
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _verify_feature_basis_manifest(
    manifest_path: Path,
    evidence_path: Path,
    evidence: Mapping[str, Any],
) -> tuple[str, dict[str, Mapping[str, Any]], str, Mapping[str, Any]]:
    """Verify the detached root manifest and every declared retained child."""

    if not manifest_path.is_file():
        raise ValueError("FEATURE_BASIS_MANIFEST_ARTIFACT_MISSING")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("FEATURE_BASIS_MANIFEST_INVALID") from exc
    if not isinstance(manifest, Mapping):
        raise ValueError("FEATURE_BASIS_MANIFEST_INVALID")
    if manifest.get("schema_version") != FEATURE_BASIS_MANIFEST_SCHEMA_VERSION:
        raise ValueError("FEATURE_BASIS_MANIFEST_SCHEMA_INVALID")
    if manifest.get("policy_id") != FEATURE_BASIS_POLICY_ID:
        raise ValueError("FEATURE_BASIS_MANIFEST_POLICY_INVALID")
    manifest_id = str(manifest.get("manifest_id") or "").lower()
    if not HEX64_RE.fullmatch(manifest_id) or manifest_id != _feature_basis_manifest_identity(manifest):
        raise ValueError("FEATURE_BASIS_MANIFEST_ID_MISMATCH")
    declared_evidence = _manifest_relative_path(
        manifest_path.parent, manifest.get("evidence_path"), "FEATURE_BASIS_MANIFEST_EVIDENCE"
    )
    if declared_evidence != evidence_path.resolve():
        raise ValueError("FEATURE_BASIS_MANIFEST_EVIDENCE_PATH_MISMATCH")
    declared_evidence_sha = str(manifest.get("evidence_sha256") or "").lower()
    if not HEX64_RE.fullmatch(declared_evidence_sha) or declared_evidence_sha != sha256_file(evidence_path):
        raise ValueError("FEATURE_BASIS_MANIFEST_EVIDENCE_HASH_MISMATCH")
    if str(evidence.get("root_manifest_id") or "").lower() != manifest_id:
        raise ValueError("FEATURE_BASIS_ROOT_MANIFEST_ID_MISMATCH")

    producer = manifest.get("producer")
    if not isinstance(producer, Mapping) or producer.get("producer_id") != FEATURE_BASIS_PRODUCER_ID:
        raise ValueError("FEATURE_BASIS_PRODUCER_ID_INVALID")
    if not str(producer.get("implementation_ref") or "").strip():
        raise ValueError("FEATURE_BASIS_PRODUCER_REF_MISSING")
    if not str(producer.get("implementation_repository") or "").strip():
        raise ValueError("FEATURE_BASIS_PRODUCER_REPOSITORY_MISSING")
    if not GIT_RE.fullmatch(str(producer.get("implementation_commit") or "").lower()):
        raise ValueError("FEATURE_BASIS_PRODUCER_COMMIT_INVALID")
    producer_sha = str(producer.get("implementation_sha256") or "").lower()
    if not HEX64_RE.fullmatch(producer_sha):
        raise ValueError("FEATURE_BASIS_PRODUCER_SHA_INVALID")

    children = manifest.get("children")
    if not isinstance(children, list) or not children:
        raise ValueError("FEATURE_BASIS_MANIFEST_CHILDREN_INVALID")
    by_id: dict[str, Mapping[str, Any]] = {}
    by_path: set[Path] = set()
    for child in children:
        if not isinstance(child, Mapping):
            raise ValueError("FEATURE_BASIS_MANIFEST_CHILD_INVALID")
        evidence_id = str(child.get("evidence_id") or "").strip()
        if not evidence_id or evidence_id in by_id:
            raise ValueError("FEATURE_BASIS_MANIFEST_DUPLICATE_EVIDENCE_ID")
        child_path = _manifest_relative_path(
            manifest_path.parent, child.get("path"), "FEATURE_BASIS_MANIFEST_CHILD"
        )
        if child_path in by_path:
            raise ValueError("FEATURE_BASIS_MANIFEST_DUPLICATE_CHILD_PATH")
        by_path.add(child_path)
        child_sha = str(child.get("sha256") or "").lower()
        if not HEX64_RE.fullmatch(child_sha):
            raise ValueError("FEATURE_BASIS_MANIFEST_CHILD_SHA_INVALID")
        if not child_path.is_file() or sha256_file(child_path) != child_sha:
            raise ValueError(f"FEATURE_BASIS_MANIFEST_CHILD_HASH_MISMATCH:{evidence_id}")
        if not str(child.get("kind") or "").strip():
            raise ValueError("FEATURE_BASIS_MANIFEST_CHILD_KIND_MISSING")
        by_id[evidence_id] = child

    producer_evidence_id = str(producer.get("implementation_evidence_id") or "").strip()
    producer_child = by_id.get(producer_evidence_id)
    if producer_child is None or producer_child.get("kind") != "producer_implementation":
        raise ValueError("FEATURE_BASIS_PRODUCER_EVIDENCE_INVALID")
    if str(producer_child.get("sha256") or "").lower() != producer_sha:
        raise ValueError("FEATURE_BASIS_PRODUCER_SHA_UNBOUND")
    return sha256_file(manifest_path), by_id, manifest_id, producer


def _verify_trusted_producer_contract(
    trusted: Mapping[str, Any] | None,
    producer: Mapping[str, Any],
) -> str:
    """Match bundle claims against an external, separately pinned anchor."""

    if not isinstance(trusted, Mapping):
        raise ValueError("PRODUCER_TRUST_ANCHOR_MISSING")
    required = (
        "producer_id",
        "implementation_repository",
        "implementation_ref",
        "implementation_commit",
        "implementation_sha256",
        "policy_id",
        "schema_version",
        "trust_contract_sha256",
    )
    if any(not str(trusted.get(field) or "").strip() for field in required):
        raise ValueError("PRODUCER_TRUST_ANCHOR_INVALID")
    trust_sha = str(trusted["trust_contract_sha256"]).lower()
    if not HEX64_RE.fullmatch(trust_sha):
        raise ValueError("PRODUCER_TRUST_CONTRACT_SHA_INVALID")
    if not GIT_RE.fullmatch(str(trusted["implementation_commit"]).lower()):
        raise ValueError("PRODUCER_TRUST_COMMIT_INVALID")
    if not HEX64_RE.fullmatch(str(trusted["implementation_sha256"]).lower()):
        raise ValueError("PRODUCER_TRUST_ARTIFACT_SHA_INVALID")
    if trusted["policy_id"] != FEATURE_BASIS_POLICY_ID:
        raise ValueError("PRODUCER_TRUST_POLICY_MISMATCH")
    if trusted["schema_version"] != FEATURE_BASIS_SCHEMA_VERSION:
        raise ValueError("PRODUCER_TRUST_SCHEMA_MISMATCH")
    comparisons = (
        ("producer_id", "PRODUCER_ID_MISMATCH"),
        ("implementation_repository", "PRODUCER_REPOSITORY_MISMATCH"),
        ("implementation_ref", "PRODUCER_REF_MISMATCH"),
        ("implementation_commit", "PRODUCER_COMMIT_MISMATCH"),
        ("implementation_sha256", "PRODUCER_ARTIFACT_SHA_MISMATCH"),
    )
    for field, reason in comparisons:
        if str(producer.get(field) or "") != str(trusted[field]):
            raise ValueError(reason)
    return trust_sha


def _calendar_values(path: Path, label: str) -> tuple[str, ...]:
    """Read a calendar with the frozen scorer's date semantics plus uniqueness."""

    from . import v4_x1_forward_score as frozen_score

    try:
        raw = pd.read_csv(path)
    except (OSError, ValueError) as exc:
        raise ValueError(f"FEATURE_BASIS_{label}_CALENDAR_INVALID") from exc
    if "date" not in raw.columns:
        raise ValueError(f"FEATURE_BASIS_{label}_CALENDAR_DATE_COLUMN_MISSING")
    parsed = pd.to_datetime(raw["date"], errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"FEATURE_BASIS_{label}_CALENDAR_INVALID_DATE")
    normalized = pd.DatetimeIndex(parsed).tz_localize(None).normalize()
    if normalized.duplicated().any():
        raise ValueError(f"FEATURE_BASIS_{label}_CALENDAR_DUPLICATE")
    # This is intentionally the scorer's parser, not a second calendar policy.
    canonical = frozen_score._read_session_csv(path)
    return tuple(value.date().isoformat() for value in canonical)


def _canonical_scoring_calendar(paths: Any, target: str) -> tuple[tuple[str, ...], Mapping[str, tuple[str, ...]]]:
    """Reuse V4-X1's historical+forward calendar construction and expose sources."""

    from . import v4_x1_forward_score as frozen_score

    historical_candidates = (
        paths.runtime_root / "research_feasibility_1260_20260809" / "official_exchange_sessions_1260.csv",
        paths.runtime_root / "sessions" / "exchange_sessions.csv",
    )
    if not any(path.is_file() for path in historical_candidates):
        raise ValueError("FEATURE_BASIS_HISTORICAL_CALENDAR_MISSING")
    forward_path = paths.calendar_root / "exchange_sessions.csv"
    if not forward_path.is_file():
        raise ValueError("FEATURE_BASIS_FORWARD_CALENDAR_MISSING")
    try:
        sessions, sources = frozen_score._local_official_sessions(paths, pd.Timestamp(target))
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        message = str(exc)
        if "TARGET_NOT_IN_LOCAL_OFFICIAL_CALENDAR" in message:
            raise ValueError("FEATURE_BASIS_SESSION_NOT_OFFICIAL") from exc
        if "FORWARD" in message or "forward" in message:
            raise ValueError("FEATURE_BASIS_FORWARD_CALENDAR_MISSING") from exc
        raise ValueError("FEATURE_BASIS_HISTORICAL_CALENDAR_MISSING") from exc
    if not sources:
        raise ValueError("FEATURE_BASIS_HISTORICAL_CALENDAR_MISSING")
    source_values: dict[str, tuple[str, ...]] = {}
    for index, source in enumerate(sources):
        label = "HISTORICAL" if index == 0 else "FORWARD"
        path = Path(str(source.get("path") or "")).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"FEATURE_BASIS_{label}_CALENDAR_MISSING")
        source_values[label.lower()] = _calendar_values(path, label)
    if "forward" not in source_values:
        raise ValueError("FEATURE_BASIS_FORWARD_CALENDAR_MISSING")
    combined = tuple(value.date().isoformat() for value in sessions)
    return combined, source_values


def _manifest_child(
    children: Mapping[str, Mapping[str, Any]], evidence_id: object, label: str
) -> Mapping[str, Any]:
    key = str(evidence_id or "").strip()
    child = children.get(key)
    if child is None:
        raise ValueError(f"{label}_EVIDENCE_UNDECLARED")
    return child


def _verify_candidate_session_ohlcv(
    path: Path,
    expected_sha256: str,
    session: str,
    observed: pd.Timestamp,
    expected_tickers: Sequence[str],
) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise ValueError("FEATURE_BASIS_SESSION_OHLCV_MISSING")
    if str(expected_sha256 or "").lower() != sha256_file(path):
        raise ValueError("FEATURE_BASIS_SESSION_OHLCV_HASH_MISMATCH")
    frame = pd.read_parquet(path)
    required = set(SESSION_OHLCV_COLUMNS)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("FEATURE_BASIS_SESSION_OHLCV_COLUMNS_MISSING")
    tickers = tuple(sorted({_safe_ticker(value) for value in frame["ticker"].tolist()}))
    if tickers != tuple(sorted(set(expected_tickers))):
        raise ValueError("FEATURE_BASIS_SESSION_OHLCV_TICKER_SET_MISMATCH")
    dates = _frame_date_series(frame["session_date"], "FEATURE_BASIS_SESSION_OHLCV")
    if not dates.eq(pd.Timestamp(session)).all() or frame["ticker"].duplicated().any():
        raise ValueError("FEATURE_BASIS_SESSION_OHLCV_SESSION_MISMATCH")
    opens = pd.to_numeric(frame["open"], errors="coerce").astype(float)
    if opens.isna().any() or not np.isfinite(opens.to_numpy()).all() or (opens <= 0).any():
        raise ValueError("FEATURE_BASIS_OPEN_VALUE_UNRESOLVED")
    if pd.Timestamp(session) > observed.tz_localize(None).normalize():
        raise ValueError("FEATURE_BASIS_SESSION_AFTER_OBSERVATION")
    retrieved = pd.to_datetime(
        frame["observed_retrieved_at_utc"], errors="coerce", utc=True
    )
    if retrieved.isna().any():
        raise ValueError("FEATURE_BASIS_CANDIDATE_RETRIEVAL_TIME_MISSING")
    if (retrieved > observed.tz_convert("UTC")).any():
        raise ValueError("FEATURE_BASIS_SESSION_OHLCV_FUTURE_DATED")
    source_metadata: dict[str, dict[str, str]] = {}
    for index, row in enumerate(frame.itertuples(index=False)):
        source = str(getattr(row, "source", "") or "").strip()
        source_ref = str(getattr(row, "source_ref", "") or "").strip()
        source_sha256 = str(getattr(row, "source_sha256", "") or "").strip().lower()
        if not source or not source_ref:
            raise ValueError("FEATURE_BASIS_CANDIDATE_SOURCE_METADATA_MISSING")
        if not HEX64_RE.fullmatch(source_sha256):
            raise ValueError("FEATURE_BASIS_CANDIDATE_SOURCE_SHA_INVALID")
        source_metadata[_safe_ticker(row.ticker)] = {
            "source": source,
            "source_ref": source_ref,
            "source_sha256": source_sha256,
            "observed_retrieved_at_utc": retrieved.iloc[index].isoformat(),
        }
    return source_metadata


def _feature_basis_failure(
    status: str,
    *reasons: str,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    reason_codes = list(dict.fromkeys(reasons))
    if not reason_codes and status != BASIS_SAFE:
        reason_codes = ["FEATURE_BASIS_NOT_PROVABLE"]
    return {
        "status": status,
        "reason_codes": reason_codes,
        "metadata": dict(metadata or {}),
    }


def evaluate_feature_basis_admission(
    *,
    session_date: str,
    model_input_tickers: Sequence[str],
    model_input_path: str | Path,
    model_input_sha256: str,
    clean_panel_path: str | Path,
    clean_panel_sha256: str,
    historical_panel_end: str | object,
    official_session_dates: Sequence[object],
    calendar_sources: Mapping[str, Sequence[object]] | None,
    evidence: Mapping[str, Any] | None,
    observed_at: str,
    evidence_path: str | Path | None = None,
    evidence_sha256: str | None = None,
    manifest_path: str | Path | None = None,
    manifest_sha256: str | None = None,
    candidate_ohlcv_path: str | Path | None = None,
    candidate_ohlcv_sha256: str | None = None,
    trusted_producer_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Admit a model-input basis without changing the frozen scorer."""

    metadata: dict[str, Any] = {
        "feature_basis_gate_applied": True,
        "feature_basis_policy_id": FEATURE_BASIS_POLICY_ID,
        "feature_basis_evidence_path": (
            str(Path(evidence_path).expanduser().resolve())
            if evidence_path is not None
            else ""
        ),
        "feature_basis_evidence_sha256": str(evidence_sha256 or "").lower(),
        "feature_basis_manifest_path": (
            str(Path(manifest_path).expanduser().resolve())
            if manifest_path is not None
            else ""
        ),
        "feature_basis_manifest_sha256": str(manifest_sha256 or "").lower(),
        "feature_basis_window_contract_sha256": (
            _feature_basis_window_contract_sha256()
        ),
    }
    try:
        session = _safe_session(session_date)
        observed = pd.Timestamp(_safe_observed_at(observed_at))
        model_path = Path(model_input_path).expanduser().resolve()
        panel_path = Path(clean_panel_path).expanduser().resolve()
        if not model_path.is_file() or not panel_path.is_file():
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_INPUT_ARTIFACT_MISSING",
                metadata=metadata,
            )
        if str(model_input_sha256).lower() != sha256_file(model_path):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_MODEL_INPUT_HASH_MISMATCH",
                metadata=metadata,
            )
        if str(clean_panel_sha256).lower() != sha256_file(panel_path):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_CLEAN_PANEL_HASH_MISMATCH",
                metadata=metadata,
            )
        if not isinstance(evidence, Mapping):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_EVIDENCE_MISSING",
                metadata=metadata,
            )
        if evidence.get("schema_version") != FEATURE_BASIS_SCHEMA_VERSION:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SCHEMA_INVALID",
                metadata=metadata,
            )
        if evidence.get("policy_id") != FEATURE_BASIS_POLICY_ID:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_POLICY_INVALID",
                metadata=metadata,
            )
        if evidence_path is None:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_EVIDENCE_PATH_MISSING",
                metadata=metadata,
            )
        evidence_file = Path(evidence_path).expanduser().resolve()
        if not evidence_file.is_file():
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_EVIDENCE_ARTIFACT_MISSING",
                metadata=metadata,
            )
        actual_evidence_sha256 = sha256_file(evidence_file)
        if evidence_sha256 and str(evidence_sha256).lower() != actual_evidence_sha256:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_EVIDENCE_HASH_MISMATCH",
                metadata=metadata,
            )
        declared_manifest = str(evidence.get("root_manifest_path") or "").strip()
        if not declared_manifest:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_MANIFEST_PATH_MISSING",
                metadata=metadata,
            )
        if manifest_path is None:
            root_manifest_file = Path(declared_manifest).expanduser().resolve()
        else:
            root_manifest_file = Path(manifest_path).expanduser().resolve()
            if declared_manifest and Path(declared_manifest).expanduser().resolve() != root_manifest_file:
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    "FEATURE_BASIS_MANIFEST_PATH_MISMATCH",
                    metadata=metadata,
                )
        try:
            actual_manifest_sha256, manifest_children, manifest_id, producer = _verify_feature_basis_manifest(
                root_manifest_file, evidence_file, evidence
            )
        except (OSError, TypeError, ValueError, KeyError) as exc:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                str(exc) or "FEATURE_BASIS_MANIFEST_INVALID",
                metadata=metadata,
            )
        if manifest_sha256 and str(manifest_sha256).lower() != actual_manifest_sha256:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_MANIFEST_HASH_MISMATCH",
                metadata=metadata,
            )
        try:
            trusted_producer_sha256 = _verify_trusted_producer_contract(
                trusted_producer_contract, producer
            )
        except ValueError as exc:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                str(exc),
                metadata=metadata,
            )
        metadata.update(
            {
                "feature_basis_manifest_path": str(root_manifest_file),
                "feature_basis_manifest_sha256": actual_manifest_sha256,
                "feature_basis_manifest_id": manifest_id,
                "feature_basis_manifest_child_count": len(manifest_children),
                "feature_basis_trust_contract_sha256": trusted_producer_sha256,
                "feature_basis_trusted_producer_id": str(producer.get("producer_id")),
                "feature_basis_trusted_producer_repository": str(
                    producer.get("implementation_repository")
                ),
                "feature_basis_trusted_producer_ref": str(
                    producer.get("implementation_ref")
                ),
                "feature_basis_trusted_producer_commit": str(producer.get("implementation_commit")),
            }
        )
        if _safe_session(evidence.get("session_date")) != session:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SESSION_MISMATCH",
                metadata=metadata,
            )
        try:
            knowledge_at = pd.Timestamp(
                _safe_observed_at(evidence.get("knowledge_at"))
            )
        except ValueError as exc:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                str(exc).replace("OBSERVED_AT", "FEATURE_BASIS_KNOWLEDGE_AT"),
                metadata=metadata,
            )
        if knowledge_at > observed:
            return _feature_basis_failure(
                BASIS_UNRESOLVED,
                "FEATURE_BASIS_KNOWLEDGE_AT_AFTER_OBSERVATION",
                metadata=metadata,
            )
        model_path_declared = Path(
            str(evidence.get("model_input_path") or "")
        ).expanduser().resolve()
        if model_path_declared != model_path:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_MODEL_INPUT_PATH_MISMATCH",
                metadata=metadata,
            )
        if str(evidence.get("model_input_sha256") or "").lower() != sha256_file(
            model_path
        ):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_MODEL_INPUT_HASH_MISMATCH",
                metadata=metadata,
            )
        panel_path_declared = Path(
            str(evidence.get("clean_panel_path") or "")
        ).expanduser().resolve()
        if panel_path_declared != panel_path:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_CLEAN_PANEL_PATH_MISMATCH",
                metadata=metadata,
            )
        if str(evidence.get("clean_panel_sha256") or "").lower() != sha256_file(
            panel_path
        ):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_CLEAN_PANEL_HASH_MISMATCH",
                metadata=metadata,
            )
        if evidence.get("window_contract") != _feature_basis_window_contract_payload():
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_WINDOW_CONTRACT_MISMATCH",
                metadata=metadata,
            )
        if str(evidence.get("window_contract_sha256") or "").lower() != (
            _feature_basis_window_contract_sha256()
        ):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_WINDOW_CONTRACT_HASH_MISMATCH",
                metadata=metadata,
            )
        observed_tickers = tuple(
            sorted({_safe_ticker(ticker) for ticker in model_input_tickers})
        )
        if evidence.get("model_input_set_sha256") != _set_hash(observed_tickers):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_MODEL_INPUT_SET_HASH_MISMATCH",
                metadata=metadata,
            )
        panel_dates = _frame_date_series(
            pd.read_parquet(panel_path, columns=["date"])["date"],
            "FEATURE_BASIS_CLEAN_PANEL",
        )
        panel_end = panel_dates.max().date().isoformat()
        if _safe_session(historical_panel_end) != panel_end:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_HISTORICAL_PANEL_END_MISMATCH",
                metadata=metadata,
            )
        dates = _frame_date_series(
            pd.Series(list(official_session_dates)), "FEATURE_BASIS_OFFICIAL_SESSION"
        )
        if dates.duplicated().any():
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_OFFICIAL_CALENDAR_DUPLICATE",
                metadata=metadata,
            )
        official = tuple(sorted(dates.dt.date.astype(str)))
        if not isinstance(calendar_sources, Mapping) or set(calendar_sources) != {
            "historical", "forward"
        }:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_CALENDAR_SOURCES_INVALID",
                metadata=metadata,
            )
        source_sets: dict[str, set[str]] = {}
        try:
            for source_name in ("historical", "forward"):
                source_dates = _frame_date_series(
                    pd.Series(list(calendar_sources[source_name])),
                    f"FEATURE_BASIS_{source_name.upper()}_CALENDAR",
                )
                if source_dates.duplicated().any():
                    return _feature_basis_failure(
                        SOURCE_CAPTURE_UNRESOLVED,
                        f"FEATURE_BASIS_{source_name.upper()}_CALENDAR_DUPLICATE",
                        metadata=metadata,
                    )
                source_sets[source_name] = set(source_dates.dt.date.astype(str))
        except (TypeError, ValueError) as exc:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                str(exc),
                metadata=metadata,
            )
        if (
            source_sets["historical"] & source_sets["forward"]
            or any(value > panel_end for value in source_sets["historical"])
            or any(value <= panel_end for value in source_sets["forward"])
        ):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_CALENDAR_SOURCE_CONFLICT",
                metadata=metadata,
            )
        source_union = source_sets["historical"] | source_sets["forward"]
        official_through_target = {value for value in official if value <= session}
        if {value for value in source_union if value <= session} != official_through_target:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_CALENDAR_SOURCE_CONFLICT",
                metadata=metadata,
            )
        if panel_end not in source_sets["historical"]:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_HISTORICAL_CALENDAR_PANEL_END_MISSING",
                metadata=metadata,
            )
        if _safe_session(historical_panel_end) not in official:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_HISTORICAL_PANEL_END_NOT_OFFICIAL",
                metadata=metadata,
            )
        if session not in official:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SESSION_NOT_OFFICIAL",
                metadata=metadata,
            )
        if session <= panel_end or session not in source_sets["forward"]:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SESSION_NOT_FORWARD_OFFICIAL",
                metadata=metadata,
            )
        boundary = evidence.get("scorer_boundary")
        if not isinstance(boundary, Mapping):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SCORER_BOUNDARY_INVALID",
                metadata=metadata,
            )
        if boundary.get("source") != "MAX_DATE_FROM_CLEAN_PANEL":
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SCORER_BOUNDARY_SOURCE_INVALID",
                metadata=metadata,
            )
        if str(boundary.get("historical_end") or "") != panel_end:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SCORER_BOUNDARY_MISMATCH",
                metadata=metadata,
            )
        if str(boundary.get("clean_panel_sha256") or "").lower() != sha256_file(
            panel_path
        ):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SCORER_BOUNDARY_HASH_MISMATCH",
                metadata=metadata,
            )
        if candidate_ohlcv_path is None or not str(candidate_ohlcv_sha256 or "").strip():
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SESSION_OHLCV_ARTIFACT_MISSING",
                metadata=metadata,
            )
        candidate_path = Path(candidate_ohlcv_path).expanduser().resolve()
        try:
            candidate_source_metadata = _verify_candidate_session_ohlcv(
                candidate_path,
                str(candidate_ohlcv_sha256),
                session,
                observed,
                observed_tickers,
            )
        except (OSError, TypeError, ValueError, KeyError) as exc:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                str(exc) or "FEATURE_BASIS_SESSION_OHLCV_INVALID",
                metadata=metadata,
            )
        geometry_open = evidence.get("geometry_open")
        if not isinstance(geometry_open, Mapping):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_OPEN_EVIDENCE_MISSING",
                metadata=metadata,
            )
        if geometry_open.get("status") != "CERTIFIED_SAME_BASIS":
            return _feature_basis_failure(
                BASIS_UNRESOLVED,
                "FEATURE_BASIS_OPEN_NOT_CERTIFIED",
                metadata=metadata,
            )
        declared_candidate = Path(
            str(geometry_open.get("session_ohlcv_path") or "")
        ).expanduser().resolve()
        if declared_candidate != candidate_path:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SESSION_OHLCV_PATH_MISMATCH",
                metadata=metadata,
            )
        if str(geometry_open.get("session_ohlcv_sha256") or "").lower() != sha256_file(candidate_path):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SESSION_OHLCV_HASH_MISMATCH",
                metadata=metadata,
            )
        if _safe_session(geometry_open.get("session_date")) != session:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_OPEN_SESSION_MISMATCH",
                metadata=metadata,
            )
        if str(geometry_open.get("ticker_set_sha256") or "").lower() != _set_hash(
            observed_tickers
        ):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_OPEN_TICKER_SET_MISMATCH",
                metadata=metadata,
            )
        try:
            open_knowledge_at = pd.Timestamp(
                _safe_observed_at(geometry_open.get("knowledge_at"))
            )
        except ValueError as exc:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                str(exc).replace("OBSERVED_AT", "FEATURE_BASIS_OPEN_KNOWLEDGE_AT"),
                metadata=metadata,
            )
        if open_knowledge_at > observed:
            return _feature_basis_failure(
                BASIS_UNRESOLVED,
                "FEATURE_BASIS_OPEN_KNOWLEDGE_AT_AFTER_OBSERVATION",
                metadata=metadata,
            )
        open_source = geometry_open.get("open_source_identity")
        if not isinstance(open_source, Mapping):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_OPEN_SOURCE_INVALID",
                metadata=metadata,
            )
        open_bindings = geometry_open.get("open_source_bindings")
        if open_bindings is None:
            open_bindings = {ticker: open_source for ticker in observed_tickers}
        if not isinstance(open_bindings, Mapping) or set(open_bindings) != set(observed_tickers):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_OPEN_SOURCE_BINDINGS_MISMATCH",
                metadata=metadata,
            )
        open_shas: set[str] = set()
        for ticker in observed_tickers:
            binding = open_bindings.get(ticker)
            actual_source = candidate_source_metadata.get(ticker)
            if not isinstance(binding, Mapping) or actual_source is None:
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    f"FEATURE_BASIS_OPEN_SOURCE_BINDING_MISSING:{ticker}",
                    metadata=metadata,
                )
            if any(
                str(binding.get(field) or "").strip() != actual_source[field]
                for field in (
                    "source",
                    "source_ref",
                    "source_sha256",
                    "observed_retrieved_at_utc",
                )
            ):
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    f"FEATURE_BASIS_OPEN_SOURCE_ROW_MISMATCH:{ticker}",
                    metadata=metadata,
                )
            try:
                open_child = _manifest_child(
                    manifest_children,
                    binding.get("evidence_id"),
                    f"FEATURE_BASIS_OPEN_SOURCE:{ticker}",
                )
            except ValueError as exc:
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    str(exc),
                    metadata=metadata,
                )
            open_sha = str(
                binding.get("open_evidence_sha256")
                or geometry_open.get("open_evidence_sha256")
                or ""
            ).lower()
            if (
                not HEX64_RE.fullmatch(open_sha)
                or str(open_child.get("sha256") or "").lower() != open_sha
                or str(open_child.get("kind") or "") != "open_source"
                or str(open_child.get("source") or "") != actual_source["source"]
                or str(open_child.get("source_ref") or "") != actual_source["source_ref"]
                or str(open_child.get("source_sha256") or "").lower()
                != actual_source["source_sha256"]
            ):
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    f"FEATURE_BASIS_OPEN_SOURCE_UNBOUND:{ticker}",
                    metadata=metadata,
                )
            open_shas.add(open_sha)
        ohlcv_child = _manifest_child(
            manifest_children,
            geometry_open.get("session_ohlcv_evidence_id"),
            "FEATURE_BASIS_SESSION_OHLCV",
        )
        if (
            str(ohlcv_child.get("kind") or "") != "session_ohlcv"
            or str(ohlcv_child.get("sha256") or "").lower() != sha256_file(candidate_path)
            or _manifest_relative_path(root_manifest_file.parent, ohlcv_child.get("path"), "FEATURE_BASIS_SESSION_OHLCV")
            != candidate_path
        ):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_SESSION_OHLCV_MANIFEST_UNBOUND",
                metadata=metadata,
            )
        metadata.update(
            {
                "feature_basis_session_ohlcv_path": str(candidate_path),
                "feature_basis_session_ohlcv_sha256": sha256_file(candidate_path),
                "feature_basis_open_evidence_sha256": sorted(open_shas),
            }
        )
        for name in (
            "identity_attestation",
            "calendar_attestation",
            "revision_attestation",
            "pit_attestation",
        ):
            attestation = evidence.get(name)
            if not isinstance(attestation, Mapping):
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    f"FEATURE_BASIS_{name.upper()}_INVALID",
                    metadata=metadata,
                )
            if attestation.get("status") != "VERIFIED":
                return _feature_basis_failure(
                    BASIS_UNRESOLVED,
                    f"FEATURE_BASIS_{name.upper()}_UNVERIFIED",
                    metadata=metadata,
                )
            if not HEX64_RE.fullmatch(
                str(attestation.get("sha256") or "").lower()
            ) or not str(attestation.get("ref") or "").strip():
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    f"FEATURE_BASIS_{name.upper()}_BINDING_INVALID",
                    metadata=metadata,
                )
            try:
                attestation_child = _manifest_child(
                    manifest_children,
                    attestation.get("evidence_id"),
                    f"FEATURE_BASIS_{name.upper()}",
                )
            except ValueError as exc:
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    str(exc),
                    metadata=metadata,
                )
            if (
                str(attestation_child.get("kind") or "") != "attestation"
                or str(attestation_child.get("sha256") or "").lower()
                != str(attestation.get("sha256") or "").lower()
                or str(attestation_child.get("source_ref") or "")
                != str(attestation.get("ref") or "")
            ):
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    f"FEATURE_BASIS_{name.upper()}_EVIDENCE_UNBOUND",
                    metadata=metadata,
                )
        if str(evidence["pit_attestation"].get("knowledge_at") or ""):
            try:
                pit_at = pd.Timestamp(
                    _safe_observed_at(evidence["pit_attestation"]["knowledge_at"])
                )
            except ValueError:
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    "FEATURE_BASIS_PIT_ATTESTATION_TIME_INVALID",
                    metadata=metadata,
                )
            if pit_at > observed:
                return _feature_basis_failure(
                    BASIS_UNRESOLVED,
                    "FEATURE_BASIS_PIT_ATTESTATION_AFTER_OBSERVATION",
                    metadata=metadata,
                )
        else:
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_PIT_ATTESTATION_TIME_MISSING",
                metadata=metadata,
            )
        target_index = official.index(session)
        records = evidence.get("records")
        if not isinstance(records, list):
            return _feature_basis_failure(
                SOURCE_CAPTURE_UNRESOLVED,
                "FEATURE_BASIS_RECORDS_INVALID",
                metadata=metadata,
            )
        records_by_ticker: dict[str, Mapping[str, Any]] = {}
        for record in records:
            if not isinstance(record, Mapping):
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    "FEATURE_BASIS_RECORD_INVALID",
                    metadata=metadata,
                )
            ticker = _safe_ticker(record.get("ticker"))
            if ticker in records_by_ticker:
                return _feature_basis_failure(
                    SOURCE_CAPTURE_UNRESOLVED,
                    f"FEATURE_BASIS_DUPLICATE_TICKER:{ticker}",
                    metadata=metadata,
                )
            records_by_ticker[ticker] = record
        if tuple(sorted(records_by_ticker)) != observed_tickers:
            missing = sorted(set(observed_tickers) - set(records_by_ticker))
            extra = sorted(set(records_by_ticker) - set(observed_tickers))
            reasons = [
                *(
                    ["FEATURE_BASIS_RECORD_MISSING:" + ",".join(missing)]
                    if missing
                    else []
                ),
                *(
                    ["FEATURE_BASIS_RECORD_EXTRA:" + ",".join(extra)]
                    if extra
                    else []
                ),
            ]
            return _feature_basis_failure(
                BASIS_UNRESOLVED, *reasons, metadata=metadata
            )

        overlaps: list[str] = []
        unresolved: list[str] = []
        for ticker in observed_tickers:
            record = records_by_ticker[ticker]
            state = str(record.get("state") or "").strip().upper()
            if state not in FEATURE_BASIS_STATES:
                unresolved.append(f"FEATURE_BASIS_STATE_INVALID:{ticker}")
                continue
            field_states = record.get("field_states")
            if not isinstance(field_states, Mapping) or set(field_states) != set(
                FEATURE_BASIS_FIELDS
            ):
                unresolved.append(f"FEATURE_BASIS_FIELD_STATES_MISSING:{ticker}")
                continue
            if any(
                str(field_states[field] or "").strip().upper()
                not in FEATURE_BASIS_FIELD_STATES
                for field in FEATURE_BASIS_FIELDS
            ):
                unresolved.append(f"FEATURE_BASIS_FIELD_STATE_UNRESOLVED:{ticker}")
                continue
            if any(
                str(field_states[field]).strip().upper()
                != "CERTIFIED_SAME_BASIS"
                for field in FEATURE_BASIS_FIELDS
            ):
                unresolved.append(f"FEATURE_BASIS_FIELD_BASIS_NOT_SAFE:{ticker}")
                continue
            source_hashes = record.get("source_hashes")
            if not isinstance(source_hashes, Mapping) or set(source_hashes) != set(
                FEATURE_BASIS_FIELDS
            ) or any(
                not HEX64_RE.fullmatch(str(source_hashes.get(field) or "").lower())
                for field in FEATURE_BASIS_FIELDS
            ):
                unresolved.append(f"FEATURE_BASIS_SOURCE_HASH_UNRESOLVED:{ticker}")
                continue
            source_evidence_ids = record.get("source_evidence_ids")
            if not isinstance(source_evidence_ids, Mapping) or set(source_evidence_ids) != set(
                FEATURE_BASIS_FIELDS
            ):
                unresolved.append(f"FEATURE_BASIS_SOURCE_EVIDENCE_UNRESOLVED:{ticker}")
                continue
            source_children: list[Mapping[str, Any]] = []
            try:
                for field in FEATURE_BASIS_FIELDS:
                    child = _manifest_child(
                        manifest_children,
                        source_evidence_ids.get(field),
                        f"FEATURE_BASIS_SOURCE:{ticker}:{field}",
                    )
                    if str(child.get("kind") or "") != "field_source":
                        raise ValueError(f"FEATURE_BASIS_SOURCE_KIND_INVALID:{ticker}:{field}")
                    if str(child.get("sha256") or "").lower() != str(
                        source_hashes[field]
                    ).lower():
                        raise ValueError(f"FEATURE_BASIS_SOURCE_HASH_UNBOUND:{ticker}:{field}")
                    source_children.append(child)
            except ValueError as exc:
                unresolved.append(str(exc))
                continue
            source_refs = record.get("source_refs")
            if not isinstance(source_refs, list) or not source_refs or any(
                not str(value or "").strip() for value in source_refs
            ):
                unresolved.append(f"FEATURE_BASIS_SOURCE_REF_UNRESOLVED:{ticker}")
                continue
            declared_source_refs = {
                str(child.get("source_ref") or "") for child in source_children
            }
            if not set(str(value) for value in source_refs).issubset(declared_source_refs):
                unresolved.append(f"FEATURE_BASIS_SOURCE_REF_UNBOUND:{ticker}")
                continue
            authority = record.get("authority")
            if not isinstance(authority, Mapping):
                unresolved.append(f"FEATURE_BASIS_AUTHORITY_MISSING:{ticker}")
                continue
            if not str(authority.get("name") or "").strip() or not str(
                authority.get("ref") or ""
            ).strip() or not HEX64_RE.fullmatch(
                str(authority.get("sha256") or "").lower()
            ):
                unresolved.append(f"FEATURE_BASIS_AUTHORITY_UNRESOLVED:{ticker}")
                continue
            try:
                authority_child = _manifest_child(
                    manifest_children,
                    authority.get("evidence_id"),
                    f"FEATURE_BASIS_AUTHORITY:{ticker}",
                )
            except ValueError as exc:
                unresolved.append(str(exc))
                continue
            if (
                str(authority_child.get("kind") or "") != "authority"
                or str(authority_child.get("sha256") or "").lower()
                != str(authority.get("sha256") or "").lower()
                or str(authority_child.get("source_ref") or "")
                != str(authority.get("ref") or "")
            ):
                unresolved.append(f"FEATURE_BASIS_AUTHORITY_UNBOUND:{ticker}")
                continue
            transition_dates = record.get("transition_dates")
            if not isinstance(transition_dates, list):
                unresolved.append(f"FEATURE_BASIS_TRANSITION_DATES_INVALID:{ticker}")
                continue
            try:
                transition_sessions = tuple(
                    sorted({_safe_session(value) for value in transition_dates})
                )
            except ValueError:
                unresolved.append(f"FEATURE_BASIS_TRANSITION_DATE_INVALID:{ticker}")
                continue
            if state == "CERTIFIED_SAME_BASIS" and transition_sessions:
                unresolved.append(f"FEATURE_BASIS_STATE_TRANSITION_MISMATCH:{ticker}")
                continue
            if state == "CERTIFIED_TRANSITION" and not transition_sessions:
                unresolved.append(f"FEATURE_BASIS_TRANSITION_DATE_MISSING:{ticker}")
                continue
            if state in {
                "NO_KNOWN_TRANSITION",
                "BASIS_UNKNOWN",
                "SOURCE_CAPTURE_UNRESOLVED",
            }:
                unresolved.append(f"FEATURE_BASIS_NOT_CERTIFIED:{ticker}:{state}")
                continue
            for transition_session in transition_sessions:
                if transition_session not in official:
                    unresolved.append(
                        "FEATURE_BASIS_TRANSITION_SESSION_NOT_OFFICIAL:"
                        f"{ticker}:{transition_session}"
                    )
                    continue
                transition_index = official.index(transition_session)
                if transition_index > target_index:
                    unresolved.append(
                        f"FEATURE_BASIS_TRANSITION_AFTER_SESSION:{ticker}:{transition_session}"
                    )
                    continue
                for feature, span in FEATURE_BASIS_WINDOW_CONTRACT:
                    if target_index - span <= transition_index <= target_index:
                        overlaps.append(
                            f"BASIS_TRANSITION_OVERLAP:{ticker}:{transition_session}:{feature}"
                        )
        metadata.update(
            {
                "feature_basis_model_input_set_sha256": _set_hash(observed_tickers),
                "feature_basis_record_count": len(records),
                "feature_basis_official_session_start": official[0],
                "feature_basis_official_session_end": official[-1],
                "feature_basis_scorer_historical_end": panel_end,
                "feature_basis_transition_overlaps": list(overlaps),
            }
        )
        if unresolved:
            return _feature_basis_failure(
                BASIS_UNRESOLVED, *unresolved, metadata=metadata
            )
        if overlaps:
            return _feature_basis_failure(
                BASIS_TRANSITION_OVERLAP, *overlaps, metadata=metadata
            )
        return _feature_basis_failure(BASIS_SAFE, metadata=metadata)
    except (OSError, TypeError, ValueError, KeyError) as exc:
        return _feature_basis_failure(
            SOURCE_CAPTURE_UNRESOLVED,
            f"FEATURE_BASIS_VALIDATION_ERROR:{type(exc).__name__}:{exc}",
            metadata=metadata,
        )


def _frame_date_series(series: pd.Series, label: str) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    try:
        parsed = parsed.dt.tz_localize(None)
    except TypeError:
        pass
    parsed = parsed.dt.normalize()
    if parsed.isna().any():
        raise ValueError(f"{label}_DATE_INVALID")
    return parsed


def _optional_frame_date_series(series: pd.Series, label: str) -> pd.Series:
    text = series.astype("string").fillna("").str.strip()
    nonempty = series.notna() & text.ne("")
    parsed = pd.to_datetime(series.where(nonempty), errors="coerce")
    try:
        parsed = parsed.dt.tz_localize(None)
    except TypeError:
        pass
    if (nonempty & parsed.isna()).any():
        raise ValueError(f"{label}_DATE_INVALID")
    return parsed.dt.normalize()


def _identity_frame(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise ValueError(f"{label}_NOT_DATAFRAME")
    required = {"ticker", "listed_from", "listed_to"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label}_COLUMNS_MISSING:{sorted(missing)}")
    data = frame.copy()
    data["ticker"] = data["ticker"].map(_safe_ticker)
    if data["ticker"].duplicated().any():
        raise ValueError(f"{label}_DUPLICATE_TICKER")
    data["listed_from"] = _frame_date_series(data["listed_from"], f"{label}_LISTED_FROM")
    try:
        data["listed_to"] = _optional_frame_date_series(
            data["listed_to"], f"{label}_LISTED_TO"
        )
    except ValueError as exc:
        raise ValueError(str(exc).replace("_DATE_INVALID", "_MALFORMED")) from exc
    invalid = data["listed_to"].notna() & data["listed_to"].lt(data["listed_from"])
    if invalid.any():
        raise ValueError(f"{label}_INTERVAL_INVALID")
    return data.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def _empty_frame(columns: Sequence[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=list(columns))


def _point_frame(frame: pd.DataFrame, session: str) -> pd.DataFrame:
    required = {"ticker", "session_date", "point_state"}
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("POINT_EVIDENCE_NOT_DATAFRAME")
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"POINT_EVIDENCE_COLUMNS_MISSING:{sorted(missing)}")
    data = frame.copy()
    data["ticker"] = data["ticker"].map(_safe_ticker)
    dates = _frame_date_series(data["session_date"], "POINT_EVIDENCE")
    if not dates.eq(pd.Timestamp(session)).all():
        raise ValueError("POINT_EVIDENCE_SESSION_MISMATCH")
    data["session_date"] = dates
    data["point_state"] = data["point_state"].astype(str).str.upper().str.strip()
    allowed = {"ACTIVE", "NO_TRADE", "SUSPENDED", "FCA_WATCHLIST"}
    if (~data["point_state"].isin(allowed)).any():
        raise ValueError("POINT_EVIDENCE_STATE_UNRESOLVED")
    if data.duplicated(["ticker", "session_date"]).any():
        raise ValueError("POINT_EVIDENCE_DUPLICATE")
    return data


def _interval_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_frame(("ticker", "market", "state", "effective_from", "effective_to", "announced_at", "source", "source_ref"))
    required = {"ticker", "market", "state", "effective_from", "source"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"TRADABILITY_INTERVAL_COLUMNS_MISSING:{sorted(missing)}")
    data = frame.copy()
    data["ticker"] = data["ticker"].map(_safe_ticker)
    data["state"] = data["state"].astype(str).str.upper().str.strip()
    if (~data["state"].isin({"ACTIVE", "NO_TRADE", "SUSPENDED", "FCA_WATCHLIST"})).any():
        raise ValueError("TRADABILITY_INTERVAL_STATE_UNRESOLVED")
    if data["source"].isna().any() or data["source"].astype(str).str.strip().eq("").any():
        raise ValueError("TRADABILITY_INTERVAL_SOURCE_MISSING")
    data["effective_from"] = _frame_date_series(data["effective_from"], "TRADABILITY_INTERVAL")
    if "effective_to" not in data.columns:
        data["effective_to"] = pd.NaT
    data["effective_to"] = _optional_frame_date_series(
        data["effective_to"], "TRADABILITY_INTERVAL_END"
    )
    if (data["effective_to"].notna() & data["effective_to"].lt(data["effective_from"])).any():
        raise ValueError("TRADABILITY_INTERVAL_RANGE_INVALID")
    if "announced_at" not in data.columns:
        data["announced_at"] = pd.NaT
    if "source_ref" not in data.columns:
        data["source_ref"] = ""
    try:
        canonical = canonicalize_tradability_intervals(data)
    except ValueError as exc:
        raise ValueError("TRADABILITY_INTERVAL_CONFLICT") from exc
    duplicate = canonical.duplicated(["ticker", "market", "effective_from", "effective_to"], keep=False)
    if duplicate.any():
        raise ValueError("TRADABILITY_INTERVAL_DUPLICATE")
    return canonical


def _coverage_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_frame(COVERAGE_WINDOW_COLUMNS)
    required = {"market", "effective_from", "source", "is_complete"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"TRADABILITY_COVERAGE_COLUMNS_MISSING:{sorted(missing)}")
    try:
        canonical = canonicalize_coverage_windows(frame.copy())
    except ValueError as exc:
        raise ValueError("TRADABILITY_COVERAGE_INVALID") from exc
    # An existing but non-propagating coverage table is a valid canonical
    # input. tradability_state() will return UNKNOWN where propagation cannot
    # be proved. Same-session Stock Summary point evidence keeps its frozen
    # precedence; absence of the coverage ARTIFACT itself is still rejected by
    # _load_runtime_tradability_evidence().
    return canonical


def _anchor_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_frame(("ticker", "market", "as_of_date", "state", "source", "source_ref", "evidence_type"))
    required = {
        "ticker",
        "market",
        "as_of_date",
        "state",
        "source",
        "source_ref",
        "evidence_type",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"TRADABILITY_ANCHOR_COLUMNS_MISSING:{sorted(missing)}")
    data = frame.copy()
    data["ticker"] = data["ticker"].map(_safe_ticker)
    data["as_of_date"] = _frame_date_series(data["as_of_date"], "TRADABILITY_ANCHOR")
    data["state"] = data["state"].astype(str).str.upper().str.strip()
    if (~data["state"].isin({"ACTIVE", "NO_TRADE", "SUSPENDED", "FCA_WATCHLIST"})).any():
        raise ValueError("TRADABILITY_ANCHOR_STATE_UNRESOLVED")
    for column in ("source", "source_ref", "evidence_type"):
        if data[column].isna().any() or data[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"TRADABILITY_ANCHOR_{column.upper()}_MISSING")
    duplicate = data.duplicated(["ticker", "market", "as_of_date"], keep=False)
    if duplicate.any():
        raise ValueError("TRADABILITY_ANCHOR_DUPLICATE")
    try:
        canonical = canonicalize_tradability_anchors(data)
    except ValueError as exc:
        raise ValueError("TRADABILITY_ANCHOR_CONFLICT") from exc
    return canonical


def _read_runtime_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_parquet(path)


def _discover_runtime_table_path(
    root: Path,
    required: Sequence[str],
    *,
    label: str,
) -> Path:
    """Resolve the exact table path without modifying the frozen monitor module.

    Selection intentionally mirrors the frozen ``forward_monitoring._discover_table``
    ranking while reusing its byte-frozen candidate/column helpers.  This outer
    operational gate needs the selected path only so the consumed artifact can be
    hash-bound in its attestation.
    """

    required_set = set(required)
    matches = [
        path
        for path in _candidate_tables(root)
        if required_set.issubset(_table_columns(path))
    ]
    if not matches:
        missing_codes = {
            "tradability intervals": "TRADABILITY_INTERVAL_ARTIFACT_MISSING",
            "tradability coverage": "TRADABILITY_COVERAGE_ARTIFACT_MISSING",
            "tradability anchors": "TRADABILITY_ANCHOR_ARTIFACT_MISSING",
        }
        raise ValueError(
            missing_codes.get(
                label,
                f"{label.upper().replace(' ', '_')}_ARTIFACT_MISSING",
            )
        )
    keywords = {
        "tradability intervals": ("tradability_intervals", "interval"),
        "tradability coverage": ("coverage_window", "coverage"),
        "tradability anchors": ("tradability_anchor", "anchor"),
    }.get(label, ())

    def ranking(path: Path) -> tuple[int, int, str, str]:
        return (
            0 if any(token in path.name.lower() for token in keywords) else 1,
            len(path.parts),
            path.name.lower(),
            str(path).lower(),
        )

    matches.sort(key=ranking)
    if len(matches) > 1 and ranking(matches[0])[:2] == ranking(matches[1])[:2]:
        raise ValueError(
            f"AMBIGUOUS_{label.upper().replace(' ', '_')}_ARTIFACT:"
            f"{matches[0]}:{matches[1]}"
        )
    return matches[0]


def _load_runtime_tradability_evidence(paths: Any) -> dict[str, Any]:
    """Load and bind the three canonical forward tradability artifacts."""

    interval_path = _discover_runtime_table_path(
        paths.tradability_root,
        TRADABILITY_COLUMNS,
        label="tradability intervals",
    )
    coverage_path = _discover_runtime_table_path(
        paths.tradability_root,
        COVERAGE_WINDOW_COLUMNS,
        label="tradability coverage",
    )
    anchor_path = _discover_runtime_table_path(
        paths.tradability_root,
        TRADABILITY_ANCHOR_COLUMNS,
        label="tradability anchors",
    )

    intervals = _interval_frame(_read_runtime_table(interval_path))
    coverage = _coverage_frame(_read_runtime_table(coverage_path))
    anchors = _anchor_frame(_read_runtime_table(anchor_path))

    return {
        "tradability_intervals": intervals,
        "tradability_coverage_windows": coverage,
        "tradability_anchors": anchors,
        "tradability_intervals_path": str(interval_path.resolve()),
        "tradability_intervals_sha256": sha256_file(interval_path),
        "tradability_coverage_path": str(coverage_path.resolve()),
        "tradability_coverage_sha256": sha256_file(coverage_path),
        "tradability_anchors_path": str(anchor_path.resolve()),
        "tradability_anchors_sha256": sha256_file(anchor_path),
        "tradability_evidence_source": (
            "IDX_TRADE_FORWARD_MONITORING_RUNTIME_TRADABILITY_ROOT"
        ),
    }

def _validate_security_master_refresh_manifest(
    manifest_path: Path,
    manifest: Mapping[str, Any],
    *,
    baseline_path: Path,
    current_path: Path,
    session: str,
) -> str:
    """Validate the exact contract emitted by the accepted cloud refresh."""

    if manifest.get("schema_version") != SECURITY_MASTER_REFRESH_SCHEMA_VERSION:
        raise ValueError("CURRENT_IDENTITY_REFRESH_SCHEMA_INVALID")
    if manifest.get("authority") != "IDX":
        raise ValueError("CURRENT_IDENTITY_REFRESH_AUTHORITY_INVALID")
    if manifest.get("semantics") != SECURITY_MASTER_REFRESH_SEMANTICS:
        raise ValueError("CURRENT_IDENTITY_REFRESH_SEMANTICS_INVALID")
    if str(manifest.get("observed_date") or "") != session:
        raise ValueError("CURRENT_IDENTITY_REFRESH_OBSERVED_DATE_MISMATCH")
    try:
        if _safe_observed_at(manifest.get("observed_at_jakarta"))[:10] != session:
            raise ValueError("CURRENT_IDENTITY_REFRESH_OBSERVED_AT_MISMATCH")
    except ValueError as exc:
        if str(exc) == "CURRENT_IDENTITY_REFRESH_OBSERVED_AT_MISMATCH":
            raise
        raise ValueError("CURRENT_IDENTITY_REFRESH_OBSERVED_AT_INVALID") from exc
    if str(manifest.get("freeze_local_date") or "") != FREEZE_LOCAL_DATE.isoformat():
        raise ValueError("CURRENT_IDENTITY_REFRESH_FREEZE_DATE_INVALID")
    if Path(str(manifest.get("baseline_path") or "")).expanduser().resolve() != baseline_path:
        raise ValueError("CURRENT_IDENTITY_REFRESH_BASELINE_PATH_INVALID")
    if str(manifest.get("baseline_sha256") or "").lower() != sha256_file(baseline_path):
        raise ValueError("CURRENT_IDENTITY_REFRESH_BASELINE_HASH_MISMATCH")
    if str(manifest.get("active_source") or "") != IDX_STOCK_LIST_URL:
        raise ValueError("CURRENT_IDENTITY_REFRESH_ACTIVE_SOURCE_INVALID")
    if str(manifest.get("active_completeness") or "") != SECURITY_MASTER_ACTIVE_COMPLETENESS:
        raise ValueError("CURRENT_IDENTITY_REFRESH_ACTIVE_COMPLETENESS_INVALID")
    if str(manifest.get("delisting_source") or "") != IDX_DELISTING_URL:
        raise ValueError("CURRENT_IDENTITY_REFRESH_DELISTING_SOURCE_INVALID")
    if str(manifest.get("delisting_completeness") or "") != SECURITY_MASTER_DELISTING_COMPLETENESS:
        raise ValueError("CURRENT_IDENTITY_REFRESH_DELISTING_COMPLETENESS_INVALID")
    if Path(str(manifest.get("security_master_path") or "")).expanduser().resolve() != current_path:
        raise ValueError("CURRENT_IDENTITY_REFRESH_MASTER_PATH_INVALID")
    if str(manifest.get("security_master_sha256") or "").lower() != sha256_file(current_path):
        raise ValueError("CURRENT_IDENTITY_REFRESH_MASTER_HASH_MISMATCH")
    guards = manifest.get("guards")
    required_guards = (
        "outcome_accessed",
        "protected_forward_accessed",
        "model_refit",
        "paper_state_mutated",
        "retroactive_capture_authorized",
    )
    if not isinstance(guards, Mapping) or any(guards.get(key) is not False for key in required_guards):
        raise ValueError("CURRENT_IDENTITY_REFRESH_GUARDS_INVALID")

    declared_manifest_path = manifest.get("manifest_path")
    if declared_manifest_path is not None:
        if Path(str(declared_manifest_path)).expanduser().resolve() != manifest_path.resolve():
            raise ValueError("CURRENT_IDENTITY_REFRESH_MANIFEST_PATH_INVALID")
    declared_manifest_sha = manifest.get("manifest_sha256")
    if declared_manifest_sha is not None and str(declared_manifest_sha).lower() != sha256_file(manifest_path):
        raise ValueError("CURRENT_IDENTITY_REFRESH_MANIFEST_HASH_MISMATCH")
    return sha256_file(manifest_path)


def _metadata_reasons(
    *,
    session: str,
    observed_at: object,
    frozen_policy: str,
    frozen_baseline_sha256: object,
    current_identity_sha256: object,
    eod_manifest_sha256: object,
    input_manifest_sha256: object,
    calendar_sha256: object,
    model_manifest_sha256: object,
    model_fingerprint: object,
    code_identity: Mapping[str, Any] | None,
    gate_sha256: object,
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    metadata: dict[str, Any] = {
        "frozen_policy": frozen_policy,
        "frozen_baseline_sha256": str(frozen_baseline_sha256 or "").lower(),
        "current_identity_sha256": str(current_identity_sha256 or "").lower(),
        "eod_manifest_sha256": str(eod_manifest_sha256 or "").lower(),
        "input_manifest_sha256": str(input_manifest_sha256 or "").lower(),
        "calendar_sha256": str(calendar_sha256 or "").lower(),
        "model_manifest_sha256": str(model_manifest_sha256 or "").lower(),
        "model_fingerprint": str(model_fingerprint or "").lower(),
        "gate_sha256": str(gate_sha256 or "").lower(),
    }
    try:
        metadata["observed_at_jakarta"] = _safe_observed_at(observed_at)
    except ValueError as exc:
        reasons.append(str(exc))
    if frozen_policy != FROZEN_POLICY:
        reasons.append("FROZEN_POLICY_CHANGED")
    for label, value in (
        ("FROZEN_BASELINE", frozen_baseline_sha256),
        ("CURRENT_IDENTITY", current_identity_sha256),
        ("EOD_MANIFEST", eod_manifest_sha256),
        ("INPUT_MANIFEST", input_manifest_sha256),
        ("CALENDAR", calendar_sha256),
        ("MODEL_MANIFEST", model_manifest_sha256),
        ("MODEL_FINGERPRINT", model_fingerprint),
        ("GATE", gate_sha256),
    ):
        try:
            _sha(value, label)
        except ValueError as exc:
            reasons.append(str(exc))
    identity = dict(code_identity or {})
    commit = str(identity.get("commit") or "").lower()
    if not GIT_RE.fullmatch(commit):
        reasons.append("CODE_IDENTITY_COMMIT_INVALID")
    runner = str(identity.get("runner_sha256") or "").lower()
    if not HEX64_RE.fullmatch(runner):
        reasons.append("CODE_IDENTITY_RUNNER_SHA_INVALID")
    metadata["code_identity"] = identity
    return reasons, metadata


def _eod_reasons(eod_manifest: Mapping[str, Any] | None, session: str) -> list[str]:
    if not isinstance(eod_manifest, Mapping):
        return ["SAME_SESSION_EOD_MANIFEST_MISSING"]
    reasons: list[str] = []
    if eod_manifest.get("status") != "DATA_READY":
        reasons.append("SAME_SESSION_EOD_NOT_DATA_READY")
    if str(eod_manifest.get("session_date") or "") != session:
        reasons.append("SAME_SESSION_EOD_SESSION_MISMATCH")
    if eod_manifest.get("outcome_blind") is not True:
        reasons.append("SAME_SESSION_EOD_OUTCOME_BLIND_GUARD_INVALID")
    if eod_manifest.get("forward_outcomes_accessed") is not False:
        reasons.append("SAME_SESSION_EOD_OUTCOME_GUARD_INVALID")
    return reasons


def evaluate_population_admission(
    *,
    session_date: str,
    baseline_identity: pd.DataFrame,
    current_identity: pd.DataFrame,
    point_evidence: pd.DataFrame,
    model_input: pd.DataFrame,
    eod_manifest: Mapping[str, Any] | None,
    frozen_baseline_sha256: str,
    current_identity_sha256: str,
    eod_manifest_sha256: str,
    input_manifest_sha256: str,
    calendar_sha256: str,
    model_manifest_sha256: str,
    model_fingerprint: str,
    code_identity: Mapping[str, Any],
    observed_at: str,
    gate_sha256: str,
    security_master_evidence: Mapping[str, Any] | None = None,
    expected_frozen_science_blobs: Mapping[str, str] | None = None,
    actual_frozen_science_blobs: Mapping[str, str] | None = None,
    feature_basis_result: Mapping[str, Any] | None = None,
    freeze_date: date = FREEZE_LOCAL_DATE,
) -> PopulationAdmission:
    """Evaluate one complete, independent same-session population proof."""

    try:
        session = _safe_session(session_date)
    except ValueError:
        session = str(session_date)
    reasons, metadata = _metadata_reasons(
        session=session,
        observed_at=observed_at,
        frozen_policy=FROZEN_POLICY,
        frozen_baseline_sha256=frozen_baseline_sha256,
        current_identity_sha256=current_identity_sha256,
        eod_manifest_sha256=eod_manifest_sha256,
        input_manifest_sha256=input_manifest_sha256,
        calendar_sha256=calendar_sha256,
        model_manifest_sha256=model_manifest_sha256,
        model_fingerprint=model_fingerprint,
        code_identity=code_identity,
        gate_sha256=gate_sha256,
    )
    reasons.extend(_eod_reasons(eod_manifest, session))
    if expected_frozen_science_blobs is not None and actual_frozen_science_blobs != dict(expected_frozen_science_blobs):
        reasons.append("FROZEN_SCIENCE_BLOB_MISMATCH")
    metadata["same_session_eod"] = dict(eod_manifest or {})
    metadata["frozen_science_blobs"] = dict(actual_frozen_science_blobs or {})
    metadata["listed_to_overlay_applied"] = False
    metadata["population_source"] = "FROZEN_BASELINE_PLUS_POST_FREEZE_IDENTITY_ADMISSIONS"
    metadata["population_proof_scope"] = "IDENTITY_TRADABILITY_COMPATIBILITY_ONLY"
    metadata["shared_identity_source"] = "FROZEN_BASELINE_ONLY"
    metadata["current_identity_role"] = "CONFIRM_OR_VETO_SHARED_POST_FREEZE_ADDITIONS_ONLY"
    metadata["final_scoring_population_authority"] = (
        "PINNED_V4_X1_FEATURE_BUILDER_UNIVERSE_PRIMARY_LIQUID"
    )
    metadata["final_scoring_population_attested"] = False
    metadata["feature_basis_gate_applied"] = feature_basis_result is not None
    metadata["feature_basis_status"] = (
        str(feature_basis_result.get("status"))
        if feature_basis_result is not None
        else "NOT_EVALUATED"
    )
    if feature_basis_result is not None:
        basis_metadata = feature_basis_result.get("metadata")
        if isinstance(basis_metadata, Mapping):
            metadata.update(dict(basis_metadata))
        basis_reasons = feature_basis_result.get("reason_codes")
        if feature_basis_result.get("status") != BASIS_SAFE:
            if not isinstance(basis_reasons, Sequence) or isinstance(
                basis_reasons, (str, bytes)
            ):
                reasons.append("FEATURE_BASIS_NOT_PROVABLE")
            else:
                reasons.extend(str(reason) for reason in basis_reasons)
    evidence_metadata = security_master_evidence or {}
    for field in (
        "security_master_refresh_manifest_path",
        "security_master_refresh_manifest_sha256",
        "tradability_intervals_path",
        "tradability_intervals_sha256",
        "tradability_coverage_path",
        "tradability_coverage_sha256",
        "tradability_anchors_path",
        "tradability_anchors_sha256",
        "tradability_evidence_source",
        "feature_basis_evidence_path",
        "feature_basis_evidence_sha256",
        "feature_basis_manifest_path",
        "feature_basis_manifest_sha256",
    ):
        if field in evidence_metadata:
            metadata[field] = evidence_metadata[field]
    metadata["runtime_tradability_evidence_bound"] = all(
        evidence_metadata.get(field) not in (None, "")
        for field in (
            "security_master_refresh_manifest_sha256",
            "tradability_intervals_sha256",
            "tradability_coverage_sha256",
            "tradability_anchors_sha256",
            "tradability_evidence_source",
            "feature_basis_evidence_sha256",
            "feature_basis_manifest_sha256",
        )
    )

    expected_identity: tuple[str, ...] = ()
    observed_input: tuple[str, ...] = ()
    added_identity: tuple[str, ...] = ()
    removed_identity: tuple[str, ...] = ()
    identity_cases: dict[str, Any] = {}
    try:
        baseline = _identity_frame(baseline_identity, "FROZEN_BASELINE")
        current = _identity_frame(current_identity, "CURRENT_IDENTITY")
        if baseline.empty:
            reasons.append("FROZEN_BASELINE_EMPTY")
        if current.empty:
            reasons.append("CURRENT_IDENTITY_EMPTY")
        freeze = pd.Timestamp(freeze_date)
        target = pd.Timestamp(session)
        baseline_live = baseline[
            baseline["listed_from"].le(freeze)
            & (baseline["listed_to"].isna() | baseline["listed_to"].ge(freeze))
        ]
        baseline_live_set = set(baseline_live["ticker"])
        baseline_set = set(baseline["ticker"])
        current_set = set(current["ticker"])
        missing = sorted(baseline_live_set - current_set)
        if missing:
            reasons.append("BASELINE_IDENTITY_NOT_PROVABLE:" + ",".join(missing))

        current_by_ticker = {
            str(row.ticker): row for row in current.itertuples(index=False)
        }
        baseline_by_ticker = {
            str(row.ticker): row for row in baseline.itertuples(index=False)
        }
        shared_conflicts: list[str] = []
        confirmed_shared: list[str] = []
        for ticker in sorted(baseline_set & current_set):
            frozen_row = baseline_by_ticker[ticker]
            current_row = current_by_ticker[ticker]
            frozen_from = pd.Timestamp(frozen_row.listed_from)
            current_from = pd.Timestamp(current_row.listed_from)
            frozen_to = (
                pd.Timestamp(frozen_row.listed_to)
                if pd.notna(frozen_row.listed_to)
                else None
            )
            current_to = (
                pd.Timestamp(current_row.listed_to)
                if pd.notna(current_row.listed_to)
                else None
            )
            if frozen_from != current_from or frozen_to != current_to:
                shared_conflicts.append(ticker)
                reasons.append(f"SHARED_IDENTITY_CURRENT_CONFLICT:{ticker}")
            else:
                confirmed_shared.append(ticker)

        additions = sorted(current_set - baseline_set)
        allowed_additions: list[str] = []
        post_freeze_delisted_before_target: list[str] = []
        for ticker in additions:
            row = current_by_ticker[ticker]
            listed_from = pd.Timestamp(row.listed_from)
            listed_to = (
                pd.Timestamp(row.listed_to)
                if pd.notna(row.listed_to)
                else None
            )
            if listed_from > target:
                reasons.append(f"FUTURE_IDENTITY:{ticker}")
            elif listed_from <= freeze:
                reasons.append(f"POST_FREEZE_RULE_VIOLATION:{ticker}")
            else:
                # Match the frozen _merged_security_master_path rule: a
                # post-freeze addition is admitted by listed_from alone.  Its
                # listed_to remains evidence, never a reason to rewrite or
                # shrink the shared frozen identity; the pinned feature
                # builder remains the authority for final scoring inclusion.
                allowed_additions.append(ticker)
                if listed_to is not None and listed_to < target:
                    post_freeze_delisted_before_target.append(ticker)

        # Shared expected identity always follows the frozen baseline interval.
        # Only genuinely post-freeze additions may use the current interval.
        frozen_live_at_target = baseline[
            baseline["listed_from"].le(target)
            & (baseline["listed_to"].isna() | baseline["listed_to"].ge(target))
        ]
        expected_identity = tuple(
            sorted(set(frozen_live_at_target["ticker"]) | set(allowed_additions))
        )
        identity_cases = {
            "baseline_shared_confirmed": confirmed_shared,
            "shared_identity_conflicts": shared_conflicts,
            "post_freeze_additions": additions,
            "post_freeze_additions_excluded_by_listed_to": sorted(
                post_freeze_delisted_before_target
            ),
            "missing_baseline": missing,
        }

        points = _point_frame(point_evidence, session)
        intervals = _interval_frame(
            None if security_master_evidence is None else security_master_evidence.get("tradability_intervals")
        )
        coverage = _coverage_frame(
            None if security_master_evidence is None else security_master_evidence.get("tradability_coverage_windows")
        )
        anchors = _anchor_frame(
            None if security_master_evidence is None else security_master_evidence.get("tradability_anchors")
        )
        point_by_ticker = {
            str(row.ticker): str(row.point_state)
            for row in points.itertuples(index=False)
        }
        expected_identity_set = set(expected_identity)
        extra_points = sorted(set(point_by_ticker) - expected_identity_set)
        if extra_points:
            reasons.append("POINT_EVIDENCE_OUTSIDE_EXPECTED_IDENTITY:" + ",".join(extra_points))
        model = model_input.copy()
        if not {"ticker", "date"}.issubset(model.columns):
            raise ValueError("MODEL_INPUT_COLUMNS_MISSING")
        model["ticker"] = model["ticker"].map(_safe_ticker)
        model["date"] = _frame_date_series(model["date"], "MODEL_INPUT")
        validate_model_input_regular_market_value(model)
        if not model["date"].eq(target).all():
            raise ValueError("MODEL_INPUT_SESSION_MISMATCH")
        if model.duplicated(["ticker", "date"]).any():
            raise ValueError("MODEL_INPUT_DUPLICATE")
        observed_input = tuple(sorted(set(model["ticker"])))
        added_identity = tuple(sorted(set(observed_input) - expected_identity_set))
        removed_identity = tuple(sorted(expected_identity_set - set(observed_input)))
        if added_identity:
            reasons.append(
                "MODEL_INPUT_IDENTITY_TICKER_NOT_EXPECTED:"
                + ",".join(added_identity)
            )
        for ticker in expected_identity:
            point = point_by_ticker.get(ticker)
            has_model_input = ticker in set(observed_input)
            if ticker in post_freeze_delisted_before_target:
                # Preserve the safe-parent merged-master semantics: the
                # post-freeze identity remains retained, but the pinned feature
                # builder excludes it once target is strictly after listed_to.
                if has_model_input:
                    reasons.append(
                        f"POST_FREEZE_DELISTED_MODEL_INPUT_PRESENT:{ticker}"
                    )
                if point is not None:
                    reasons.append(
                        f"POST_FREEZE_DELISTED_POINT_EVIDENCE_PRESENT:{ticker}"
                    )
                continue

            try:
                explicit_state = tradability_state(
                    intervals,
                    coverage,
                    ticker,
                    pd.Timestamp(session),
                    market="REGULAR",
                    anchors=anchors,
                )
            except ValueError:
                reasons.append(f"TRADABILITY_CONFLICT:{ticker}")
                continue

            point_state = TradabilityState(point) if point is not None else None

            if has_model_input:
                # Preserve the frozen forward-monitoring precedence: canonical
                # same-session Stock Summary ACTIVE point evidence is sufficient
                # for the ACTIVE-only model-input row.  Independent retained
                # tradability evidence is a contradiction veto, not a second
                # admission requirement.  UNKNOWN therefore does not invent a
                # new V1 rejection rule when the same-session point is present.
                if point_state is None:
                    if explicit_state is TradabilityState.UNKNOWN:
                        reasons.append(f"TRADABILITY_STATE_NOT_EXPLICIT:{ticker}")
                    elif explicit_state is TradabilityState.ACTIVE:
                        reasons.append(f"MODEL_INPUT_POINT_STATE_MISSING:{ticker}")
                    else:
                        reasons.append(
                            f"MODEL_INPUT_NON_ACTIVE_STATE:{ticker}:{explicit_state.value}"
                        )
                    continue
                if point_state is not TradabilityState.ACTIVE:
                    if (
                        explicit_state not in {TradabilityState.UNKNOWN, point_state}
                        and not _point_states_compatible(point_state, explicit_state)
                    ):
                        reasons.append(f"TRADABILITY_CONFLICT:{ticker}")
                    else:
                        reasons.append(
                            f"MODEL_INPUT_NON_ACTIVE_STATE:{ticker}:{point_state.value}"
                        )
                    continue
                if explicit_state not in {
                    TradabilityState.UNKNOWN,
                    TradabilityState.ACTIVE,
                }:
                    reasons.append(f"TRADABILITY_CONFLICT:{ticker}")
                continue

            # No model input is a valid frozen-domain state for legally retained
            # identities when the same-session point is non-active.  Do not turn
            # this into a scientific population deletion or require set equality.
            if point_state is TradabilityState.ACTIVE:
                reasons.append(f"MODEL_INPUT_ACTIVE_TICKER_MISSING:{ticker}")
                continue
            if point_state in {
                TradabilityState.NO_TRADE,
                TradabilityState.SUSPENDED,
                TradabilityState.FCA_WATCHLIST,
            }:
                # The same-session point is sufficient to prove that no ACTIVE
                # model row should exist.  If independent evidence resolves to a
                # known non-active state, require the existing canonical
                # compatibility relation; ACTIVE is not treated as proof of trade
                # occurrence and therefore does not override a NO_TRADE point.
                if (
                    explicit_state not in {TradabilityState.UNKNOWN, TradabilityState.ACTIVE}
                    and not _point_states_compatible(point_state, explicit_state)
                ):
                    reasons.append(f"TRADABILITY_CONFLICT:{ticker}")
                continue

            # When Stock Summary has no same-session point, only canonical
            # interval/coverage/anchor reconstruction may justify omission from
            # model input.  UNKNOWN is intentionally fail-closed.
            if explicit_state is TradabilityState.UNKNOWN:
                reasons.append(f"TRADABILITY_STATE_NOT_EXPLICIT:{ticker}")
            elif explicit_state is TradabilityState.ACTIVE:
                reasons.append(f"MODEL_INPUT_ACTIVE_TICKER_MISSING:{ticker}")
            elif explicit_state not in {
                TradabilityState.NO_TRADE,
                TradabilityState.SUSPENDED,
                TradabilityState.FCA_WATCHLIST,
            }:
                reasons.append(f"TRADABILITY_STATE_NOT_PROVABLE:{ticker}")
    except Exception as exc:
        reasons.append(str(exc))

    deduped_reasons = tuple(dict.fromkeys(reasons))
    metadata["model_input_identity_subset"] = not added_identity and not any(
        reason.startswith(
            (
                "MODEL_INPUT_IDENTITY_TICKER_NOT_EXPECTED",
            )
        )
        for reason in deduped_reasons
    )
    metadata["model_input_identity_equality"] = (
        metadata["model_input_identity_subset"] and not removed_identity
    )
    metadata["expected_identity_set_sha256"] = _set_hash(expected_identity)
    metadata["observed_model_input_set_sha256"] = _set_hash(observed_input)
    status = SAFE_V1_POPULATION if not deduped_reasons else V1_POPULATION_NOT_PROVABLE
    return PopulationAdmission(
        status=status,
        session_date=session,
        expected_identity_tickers=expected_identity,
        observed_model_input_tickers=observed_input,
        identity_added_tickers=added_identity,
        identity_removed_tickers=removed_identity,
        reason_codes=deduped_reasons,
        identity_cases=identity_cases,
        expected_identity_set_sha256=_set_hash(expected_identity),
        observed_model_input_set_sha256=_set_hash(observed_input),
        metadata=metadata,
    )


def _git_blobs(repo_root: Path) -> tuple[dict[str, str], dict[str, str]]:
    config_path = repo_root / "config" / "ranking_v4_x1_clean_prospective_score_v1.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    expected = {str(key): str(value) for key, value in (config.get("pinned_git_blobs") or {}).items()}
    actual: dict[str, str] = {}
    for path in expected:
        actual[path] = subprocess.run(
            ["git", "-C", str(repo_root), "hash-object", "--", path],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    return expected, actual


def _runtime_failure(**kwargs: Any) -> PopulationAdmission:
    session = str(kwargs.get("session_date") or "")
    try:
        session = _safe_session(session)
    except ValueError:
        pass
    reasons = tuple(dict.fromkeys(str(value) for value in kwargs.get("reasons", ())))
    metadata = dict(kwargs.get("metadata") or {})
    metadata.setdefault("listed_to_overlay_applied", False)
    metadata.setdefault("population_source", "FROZEN_BASELINE_PLUS_POST_FREEZE_IDENTITY_ADMISSIONS")
    metadata.setdefault("population_proof_scope", "IDENTITY_TRADABILITY_COMPATIBILITY_ONLY")
    metadata.setdefault("shared_identity_source", "FROZEN_BASELINE_ONLY")
    metadata.setdefault("final_scoring_population_authority", "PINNED_V4_X1_FEATURE_BUILDER_UNIVERSE_PRIMARY_LIQUID")
    metadata.setdefault("final_scoring_population_attested", False)
    return PopulationAdmission(
        status=V1_POPULATION_NOT_PROVABLE,
        session_date=session,
        expected_identity_tickers=(),
        observed_model_input_tickers=(),
        identity_added_tickers=(),
        identity_removed_tickers=(),
        reason_codes=reasons or ("RUNTIME_EVIDENCE_NOT_PROVABLE",),
        identity_cases={},
        expected_identity_set_sha256=_set_hash(()),
        observed_model_input_set_sha256=_set_hash(()),
        metadata=metadata,
    )


def build_runtime_population_admission(
    runtime_root: str | Path,
    *,
    clean_panel: str | Path,
    clean_security_master: str | Path,
    model_root: str | Path,
    repo_root: str | Path,
    observed_by: str,
    input_manifest_sha256: str,
    runner_path: str | Path,
    expected_baseline_sha256: str,
    expected_model_manifest_sha256: str,
    trusted_producer_contract: Mapping[str, Any] | None = None,
) -> PopulationAdmission:
    """Load only retained, same-session evidence and produce an admission."""

    try:
        observed = datetime.fromisoformat(str(observed_by))
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("OBSERVED_AT_NOT_TIMEZONE_AWARE")
        session = observed.astimezone(JAKARTA).date().isoformat()
        if not isinstance(trusted_producer_contract, Mapping):
            return _runtime_failure(
                session_date=session,
                reasons=("PRODUCER_TRUST_ANCHOR_MISSING",),
            )
        paths = runtime_paths(runtime_root)
        baseline_path = Path(clean_security_master).expanduser().resolve()
        current_path = (paths.listings_root / "security_master.csv").resolve()
        eod_path = (paths.session_root / session / "manifest.json").resolve()
        if not baseline_path.is_file():
            return _runtime_failure(session_date=session, reasons=("FROZEN_BASELINE_MISSING",))
        if not current_path.is_file():
            return _runtime_failure(session_date=session, reasons=("CURRENT_IDENTITY_MISSING",))
        if not eod_path.is_file():
            return _runtime_failure(session_date=session, reasons=("SAME_SESSION_EOD_MANIFEST_MISSING",))
        session_row = _existing_session(paths, pd.Timestamp(session))
        if session_row is None or session_row["state"] != "DATA_READY":
            return _runtime_failure(session_date=session, reasons=("SAME_SESSION_EOD_NOT_DATA_READY",))
        if Path(str(session_row["manifest_path"])).expanduser().resolve() != eod_path:
            return _runtime_failure(session_date=session, reasons=("SAME_SESSION_EOD_MANIFEST_BINDING_INVALID",))
        if not _verify_ready_artifacts(
            Path(str(session_row["snapshot_path"])).expanduser().resolve(),
            Path(str(session_row["evidence_path"])).expanduser().resolve(),
            eod_path,
            expected_session=session,
            snapshot_sha256=str(session_row["snapshot_sha256"] or ""),
            evidence_sha256=str(session_row["evidence_sha256"] or ""),
            manifest_sha256=str(session_row["manifest_sha256"] or ""),
        ):
            return _runtime_failure(session_date=session, reasons=("SAME_SESSION_EOD_ARTIFACT_INVALID",))
        eod = json.loads(eod_path.read_text(encoding="utf-8"))
        model_manifest = Path(model_root).expanduser().resolve() / "MANIFEST.json"
        if not model_manifest.is_file():
            return _runtime_failure(session_date=session, reasons=("MODEL_MANIFEST_MISSING",))
        model_hash = sha256_file(model_manifest)
        if model_hash != str(expected_model_manifest_sha256).lower():
            return _runtime_failure(session_date=session, reasons=("MODEL_MANIFEST_PIN_MISMATCH",))
        runner = Path(runner_path).expanduser().resolve()
        current_manifest_path = current_path.with_name("security_master_refresh_manifest.json")
        if not current_manifest_path.is_file():
            return _runtime_failure(session_date=session, reasons=("CURRENT_IDENTITY_EVIDENCE_MANIFEST_MISSING",))
        loaded = json.loads(current_manifest_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return _runtime_failure(session_date=session, reasons=("CURRENT_IDENTITY_EVIDENCE_MANIFEST_INVALID",))
        try:
            refresh_manifest_sha256 = _validate_security_master_refresh_manifest(
                current_manifest_path,
                loaded,
                baseline_path=baseline_path,
                current_path=current_path,
                session=session,
            )
        except ValueError as exc:
            return _runtime_failure(session_date=session, reasons=(str(exc),))
        try:
            tradability_evidence = _load_runtime_tradability_evidence(paths)
        except (OSError, ValueError, RuntimeError) as exc:
            return _runtime_failure(
                session_date=session,
                reasons=(str(exc) or "TRADABILITY_EVIDENCE_NOT_PROVABLE",),
            )
        security_evidence = {
            **loaded,
            **tradability_evidence,
            "security_master_refresh_manifest_path": str(current_manifest_path.resolve()),
            "security_master_refresh_manifest_sha256": refresh_manifest_sha256,
        }
        current = pd.read_csv(current_path)
        baseline = pd.read_csv(baseline_path)
        point = pd.read_parquet(Path(str(eod["evidence_path"])))
        model_input = pd.read_parquet(Path(str(eod["snapshot_path"])))
        clean_panel_path = Path(clean_panel).expanduser().resolve()
        if not clean_panel_path.is_file():
            return _runtime_failure(session_date=session, reasons=("CLEAN_PANEL_MISSING",))
        feature_basis_path = eod_path.parent / FEATURE_BASIS_EVIDENCE_FILENAME
        if not feature_basis_path.is_file():
            return _runtime_failure(
                session_date=session,
                reasons=("FEATURE_BASIS_EVIDENCE_ARTIFACT_MISSING",),
            )
        try:
            feature_basis_evidence = json.loads(
                feature_basis_path.read_text(encoding="utf-8")
            )
            if not isinstance(feature_basis_evidence, Mapping):
                raise ValueError("FEATURE_BASIS_EVIDENCE_NOT_OBJECT")
            clean_panel_dates = _frame_date_series(
                pd.read_parquet(clean_panel_path, columns=["date"])["date"],
                "FEATURE_BASIS_CLEAN_PANEL",
            )
            if clean_panel_dates.empty:
                raise ValueError("FEATURE_BASIS_CLEAN_PANEL_EMPTY")
            historical_panel_end = clean_panel_dates.max().date().isoformat()
            official_session_dates, calendar_sources = _canonical_scoring_calendar(
                paths, session
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError) as exc:
            return _runtime_failure(
                session_date=session,
                reasons=(str(exc) or "FEATURE_BASIS_EVIDENCE_INVALID",),
            )
        feature_basis_sha256 = sha256_file(feature_basis_path)
        feature_basis_manifest_path = eod_path.parent / FEATURE_BASIS_MANIFEST_FILENAME
        if not feature_basis_manifest_path.is_file():
            return _runtime_failure(
                session_date=session,
                reasons=("FEATURE_BASIS_MANIFEST_ARTIFACT_MISSING",),
            )
        feature_basis_manifest_sha256 = sha256_file(feature_basis_manifest_path)
        session_ohlcv_path = Path(str(eod.get("session_ohlcv_path") or "")).expanduser().resolve()
        session_ohlcv_sha256 = str(eod.get("session_ohlcv_sha256") or "").lower()
        if not session_ohlcv_path.is_file() or session_ohlcv_sha256 != sha256_file(session_ohlcv_path):
            return _runtime_failure(
                session_date=session,
                reasons=("SAME_SESSION_OHLCV_ARTIFACT_INVALID",),
            )
        feature_basis_result = evaluate_feature_basis_admission(
            session_date=session,
            model_input_tickers=model_input["ticker"].tolist()
            if "ticker" in model_input.columns
            else (),
            model_input_path=Path(str(eod["snapshot_path"])),
            model_input_sha256=str(session_row["snapshot_sha256"] or ""),
            clean_panel_path=clean_panel_path,
            clean_panel_sha256=sha256_file(clean_panel_path),
            historical_panel_end=historical_panel_end,
            official_session_dates=official_session_dates,
            calendar_sources=calendar_sources,
            evidence=feature_basis_evidence,
            observed_at=observed_by,
            evidence_path=feature_basis_path,
            evidence_sha256=feature_basis_sha256,
            manifest_path=feature_basis_manifest_path,
            manifest_sha256=feature_basis_manifest_sha256,
            candidate_ohlcv_path=session_ohlcv_path,
            candidate_ohlcv_sha256=session_ohlcv_sha256,
            trusted_producer_contract=trusted_producer_contract,
        )
        security_evidence["feature_basis_evidence_path"] = str(
            feature_basis_path.resolve()
        )
        security_evidence["feature_basis_evidence_sha256"] = feature_basis_sha256
        security_evidence["feature_basis_manifest_path"] = str(
            feature_basis_manifest_path.resolve()
        )
        security_evidence["feature_basis_manifest_sha256"] = feature_basis_manifest_sha256
        expected_blobs, actual_blobs = _git_blobs(Path(repo_root).expanduser().resolve())
        code_identity = {
            "repo": "samindriano/idx-trade",
            "commit": subprocess.run(
                ["git", "-C", str(Path(repo_root).expanduser().resolve()), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip().lower(),
            "runner_sha256": sha256_file(runner),
        }
        admission = evaluate_population_admission(
            session_date=session,
            baseline_identity=baseline,
            current_identity=current,
            point_evidence=point,
            model_input=model_input,
            eod_manifest={**eod, "manifest_path": str(eod_path)},
            frozen_baseline_sha256=sha256_file(baseline_path),
            current_identity_sha256=sha256_file(current_path),
            eod_manifest_sha256=sha256_file(eod_path),
            input_manifest_sha256=input_manifest_sha256,
            calendar_sha256=str(eod.get("calendar_sha256") or ""),
            model_manifest_sha256=model_hash,
            model_fingerprint=model_hash,
            code_identity=code_identity,
            observed_at=observed_by,
            gate_sha256=sha256_file(Path(__file__).resolve()),
            security_master_evidence=security_evidence,
            expected_frozen_science_blobs=expected_blobs,
            actual_frozen_science_blobs=actual_blobs,
            feature_basis_result=feature_basis_result,
        )
        if admission.metadata.get("frozen_baseline_sha256") != str(expected_baseline_sha256).lower():
            return PopulationAdmission(
                **{**admission.__dict__, "status": V1_POPULATION_NOT_PROVABLE,
                   "reason_codes": tuple(dict.fromkeys((*admission.reason_codes, "FROZEN_BASELINE_PIN_MISMATCH")))}
            )
        return admission
    except Exception as exc:
        return _runtime_failure(session_date=str(observed_by)[:10], reasons=(type(exc).__name__.upper() + ":" + str(exc),))


_ATTESTATION_BOUND_HASH_FIELDS = (
    "frozen_baseline_sha256",
    "current_identity_sha256",
    "eod_manifest_sha256",
    "input_manifest_sha256",
    "calendar_sha256",
    "model_manifest_sha256",
    "model_fingerprint",
    "gate_sha256",
    *_ATTESTATION_RUNTIME_HASH_FIELDS,
)


def _attestation_identity(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("POPULATION_ATTESTATION_NOT_OBJECT")
    identity = dict(payload)
    for field in ("attestation_path", "attestation_sha256", "immutable_identity_sha256"):
        identity.pop(field, None)
    metadata = identity.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("POPULATION_ATTESTATION_METADATA_INVALID")
    identity["metadata"] = {
        key: value for key, value in metadata.items() if key != "observed_at_jakarta"
    }
    return identity


def _attestation_ticker_list(payload: Mapping[str, Any], field: str) -> tuple[str, ...]:
    values = payload.get(field)
    if not isinstance(values, list):
        raise ValueError(f"POPULATION_ATTESTATION_{field.upper()}_INVALID")
    normalized = tuple(_safe_ticker(value) for value in values)
    if normalized != tuple(sorted(normalized)) or len(set(normalized)) != len(normalized):
        raise ValueError(f"POPULATION_ATTESTATION_{field.upper()}_NOT_CANONICAL")
    return normalized


def _validate_attestation_payload(
    payload: Mapping[str, Any],
    *,
    require_safe: bool,
    require_identity_hash: bool,
) -> dict[str, Any]:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("POPULATION_ATTESTATION_SCHEMA_INVALID")
    status = payload.get("status")
    if status not in {SAFE_V1_POPULATION, V1_POPULATION_NOT_PROVABLE}:
        raise ValueError("POPULATION_ATTESTATION_STATUS_INVALID")
    if require_safe and status != SAFE_V1_POPULATION:
        raise ValueError("POPULATION_ATTESTATION_NOT_SAFE")
    session = _safe_session(payload.get("session_date"))
    for field in (
        "expected_identity_tickers",
        "observed_model_input_tickers",
        "identity_added_tickers",
        "identity_removed_tickers",
    ):
        _attestation_ticker_list(payload, field)
    expected = payload["expected_identity_tickers"]
    observed = payload["observed_model_input_tickers"]
    for field, values in (
        ("expected_identity_set_sha256", expected),
        ("observed_model_input_set_sha256", observed),
    ):
        declared = str(payload.get(field) or "").lower()
        if declared != _set_hash(values):
            raise ValueError(f"POPULATION_ATTESTATION_{field.upper()}_MISMATCH")
    expected_set = set(expected)
    observed_set = set(observed)
    added = set(payload["identity_added_tickers"])
    removed = set(payload["identity_removed_tickers"])
    if not observed_set.issubset(expected_set):
        raise ValueError("POPULATION_ATTESTATION_INPUT_IDENTITY_NOT_SUBSET")
    if added != observed_set - expected_set or removed != expected_set - observed_set:
        raise ValueError("POPULATION_ATTESTATION_IDENTITY_DELTA_MISMATCH")
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("POPULATION_ATTESTATION_METADATA_INVALID")
    if metadata.get("listed_to_overlay_applied") is not False:
        raise ValueError("POPULATION_ATTESTATION_LISTED_TO_OVERLAY")
    if metadata.get("final_scoring_population_attested") is not False:
        raise ValueError("POPULATION_ATTESTATION_FINAL_DENOMINATOR_CLAIM")
    if require_safe:
        _safe_observed_at(metadata.get("observed_at_jakarta"))
        if metadata.get("frozen_policy") != FROZEN_POLICY:
            raise ValueError("POPULATION_ATTESTATION_POLICY_INVALID")
        if metadata.get("population_proof_scope") != "IDENTITY_TRADABILITY_COMPATIBILITY_ONLY":
            raise ValueError("POPULATION_ATTESTATION_SCOPE_INVALID")
        if metadata.get("shared_identity_source") != "FROZEN_BASELINE_ONLY":
            raise ValueError("POPULATION_ATTESTATION_SHARED_IDENTITY_SOURCE_INVALID")
        if metadata.get("final_scoring_population_authority") != (
            "PINNED_V4_X1_FEATURE_BUILDER_UNIVERSE_PRIMARY_LIQUID"
        ):
            raise ValueError("POPULATION_ATTESTATION_FINAL_DENOMINATOR_AUTHORITY_INVALID")
        if metadata.get("feature_basis_gate_applied") is not True:
            raise ValueError("POPULATION_ATTESTATION_FEATURE_BASIS_NOT_APPLIED")
        if metadata.get("feature_basis_status") != BASIS_SAFE:
            raise ValueError("POPULATION_ATTESTATION_FEATURE_BASIS_NOT_SAFE")
        if metadata.get("runtime_tradability_evidence_bound") is not True:
            raise ValueError("POPULATION_ATTESTATION_RUNTIME_EVIDENCE_NOT_BOUND")
        if metadata.get("model_input_identity_subset") is not True:
            raise ValueError("POPULATION_ATTESTATION_INPUT_IDENTITY_NOT_SUBSET")
        if payload.get("identity_added_tickers"):
            raise ValueError("POPULATION_ATTESTATION_IDENTITY_ADDITION")
        if payload.get("reason_codes"):
            raise ValueError("POPULATION_ATTESTATION_REASONS_PRESENT")

    if metadata.get("runtime_tradability_evidence_bound") is True:
        if metadata.get("tradability_evidence_source") != (
            "IDX_TRADE_FORWARD_MONITORING_RUNTIME_TRADABILITY_ROOT"
        ):
            raise ValueError("POPULATION_ATTESTATION_TRADABILITY_SOURCE_INVALID")
        for field in (
            "security_master_refresh_manifest_path",
            "tradability_intervals_path",
            "tradability_coverage_path",
            "tradability_anchors_path",
            "feature_basis_evidence_path",
            "feature_basis_manifest_path",
        ):
            if not str(metadata.get(field) or "").strip():
                raise ValueError(f"POPULATION_ATTESTATION_{field.upper()}_MISSING")

    for field in _ATTESTATION_BOUND_HASH_FIELDS:
        value = metadata.get(field)
        if (
            require_safe
            or value is not None
            or (
                metadata.get("runtime_tradability_evidence_bound") is True
                and field in _ATTESTATION_RUNTIME_HASH_FIELDS
            )
        ):
            _sha(value, field.upper())
    code_identity = metadata.get("code_identity")
    if require_safe or code_identity is not None:
        if not isinstance(code_identity, Mapping):
            raise ValueError("POPULATION_ATTESTATION_CODE_IDENTITY_INVALID")
        if not GIT_RE.fullmatch(str(code_identity.get("commit") or "").lower()):
            raise ValueError("POPULATION_ATTESTATION_CODE_COMMIT_INVALID")
        if not HEX64_RE.fullmatch(str(code_identity.get("runner_sha256") or "").lower()):
            raise ValueError("POPULATION_ATTESTATION_CODE_RUNNER_INVALID")
    same_session_eod = metadata.get("same_session_eod")
    if require_safe:
        if not isinstance(same_session_eod, Mapping):
            raise ValueError("POPULATION_ATTESTATION_EOD_INVALID")
        if (
            same_session_eod.get("status") != "DATA_READY"
            or str(same_session_eod.get("session_date") or "") != session
            or same_session_eod.get("outcome_blind") is not True
            or same_session_eod.get("forward_outcomes_accessed") is not False
        ):
            raise ValueError("POPULATION_ATTESTATION_EOD_INVALID")
        science_blobs = metadata.get("frozen_science_blobs")
        if not isinstance(science_blobs, Mapping) or not science_blobs:
            raise ValueError("POPULATION_ATTESTATION_FROZEN_BLOBS_INVALID")
        for value in science_blobs.values():
            if not re.fullmatch(r"[0-9a-f]{40,64}", str(value or "").lower()):
                raise ValueError("POPULATION_ATTESTATION_FROZEN_BLOB_HASH_INVALID")
    identity = _attestation_identity(payload)
    identity_sha = hashlib.sha256(_canonical_json(identity)).hexdigest()
    declared_identity_sha = str(payload.get("immutable_identity_sha256") or "").lower()
    if require_identity_hash or declared_identity_sha:
        if declared_identity_sha != identity_sha:
            raise ValueError("POPULATION_ATTESTATION_IDENTITY_HASH_MISMATCH")
    return identity


def _attestation_stage_hook(stage: str, temporary: Path, target: Path) -> None:
    """Test seam for crash-injection; production behavior is a no-op."""


def _existing_attestation(
    path: Path,
    *,
    expected_payload: Mapping[str, Any],
    expected_identity: Mapping[str, Any],
) -> bytes:
    try:
        raw = path.read_bytes()
        existing = json.loads(raw.decode("utf-8"))
        if not isinstance(existing, Mapping):
            raise ValueError("POPULATION_ATTESTATION_EXISTING_INVALID")
        actual_identity = _validate_attestation_payload(
            existing, require_safe=False, require_identity_hash=True
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, PopulationAdmissionConflict):
            raise
        raise PopulationAdmissionConflict("POPULATION_ATTESTATION_EXISTING_INVALID") from exc
    if actual_identity != dict(expected_identity) or actual_identity != _attestation_identity(expected_payload):
        raise PopulationAdmissionConflict("POPULATION_ATTESTATION_IDENTITY_CONFLICT")
    return raw


def persist_population_attestation(runtime_root: str | Path, admission: PopulationAdmission) -> PopulationAdmission:
    """Persist a fully durable create-only marker with verified idempotency."""

    path = (
        Path(runtime_root).expanduser().resolve()
        / "forward_monitoring"
        / "population_admission"
        / f"{admission.session_date}.json"
    )
    payload = admission.to_dict()
    identity = _attestation_identity(payload)
    identity_sha = hashlib.sha256(_canonical_json(identity)).hexdigest()
    payload["immutable_identity_sha256"] = identity_sha
    _validate_attestation_payload(
        payload, require_safe=False, require_identity_hash=True
    )
    raw = _canonical_json(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing_raw = _existing_attestation(
            path, expected_payload=payload, expected_identity=identity
        )
        return PopulationAdmission(
            **{
                **admission.__dict__,
                "attestation_path": str(path),
                "attestation_sha256": hashlib.sha256(existing_raw).hexdigest(),
            }
        )

    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(temporary, flags)
        with os.fdopen(fd, "wb") as handle:
            _attestation_stage_hook("temp_created", temporary, path)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
            _attestation_stage_hook("temp_fsynced", temporary, path)
        _attestation_stage_hook("promotion", temporary, path)
        try:
            # Hard-link promotion is atomic and create-only: it cannot replace
            # a concurrent writer's final marker.
            os.link(temporary, path)
        except FileExistsError:
            existing_raw = _existing_attestation(
                path, expected_payload=payload, expected_identity=identity
            )
            return PopulationAdmission(
                **{
                    **admission.__dict__,
                    "attestation_path": str(path),
                    "attestation_sha256": hashlib.sha256(existing_raw).hexdigest(),
                }
            )
        except OSError as exc:
            raise PopulationAdmissionConflict(
                "POPULATION_ATTESTATION_CREATE_ONLY_PROMOTION_UNAVAILABLE"
            ) from exc
        _attestation_stage_hook("promoted", temporary, path)
        return PopulationAdmission(
            **{
                **admission.__dict__,
                "attestation_path": str(path),
                "attestation_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    except FileExistsError:
        existing_raw = _existing_attestation(
            path, expected_payload=payload, expected_identity=identity
        )
        return PopulationAdmission(
            **{
                **admission.__dict__,
                "attestation_path": str(path),
                "attestation_sha256": hashlib.sha256(existing_raw).hexdigest(),
            }
        )
    finally:
        temporary.unlink(missing_ok=True)


def classify_retained_population_attestation(
    attestation: Mapping[str, Any],
    *,
    expected_session_date: str,
    expected_baseline_sha256: str,
) -> str:
    """Classify retained 2/100 evidence without outcomes, rescoring, or counters."""

    try:
        _validate_attestation_payload(
            attestation, require_safe=True, require_identity_hash=True
        )
        if _safe_session(attestation.get("session_date")) != _safe_session(expected_session_date):
            raise ValueError("POPULATION_ATTESTATION_SESSION_MISMATCH")
        metadata = attestation["metadata"]
        if metadata.get("frozen_baseline_sha256") != str(expected_baseline_sha256).lower():
            raise ValueError("POPULATION_ATTESTATION_BASELINE_MISMATCH")
        return PROVEN_V1_POPULATION_COMPATIBLE
    except (AttributeError, TypeError, ValueError):
        return NOT_PROVABLE_FROM_RETAINED_EVIDENCE


class PopulationScoreGate:
    """Temporarily veto frozen scorer entry when the runtime proof is unsafe."""

    def __init__(self, score_module: ModuleType, **kwargs: Any):
        self.score_module = score_module
        self.kwargs = kwargs
        self.original: Callable[..., Any] | None = None
        self.last_admission: PopulationAdmission | None = None

    def __enter__(self) -> "PopulationScoreGate":
        self.original = getattr(self.score_module, "score_v4_x1_session")

        def guarded(*args: Any, **kwargs: Any) -> Any:
            admission = build_runtime_population_admission(**self.kwargs)
            admission = persist_population_attestation(self.kwargs["runtime_root"], admission)
            self.last_admission = admission
            if not admission.safe:
                raise V1PopulationNotProvable(admission)
            assert self.original is not None
            return self.original(*args, **kwargs)

        setattr(self.score_module, "score_v4_x1_session", guarded)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.original is not None:
            setattr(self.score_module, "score_v4_x1_session", self.original)


__all__ = [
    "BASIS_SAFE",
    "BASIS_TRANSITION_OVERLAP",
    "BASIS_UNRESOLVED",
    "FREEZE_LOCAL_DATE",
    "FEATURE_BASIS_EVIDENCE_FILENAME",
    "FEATURE_BASIS_MANIFEST_FILENAME",
    "FEATURE_BASIS_MANIFEST_SCHEMA_VERSION",
    "FEATURE_BASIS_POLICY_ID",
    "FEATURE_BASIS_PRODUCER_ID",
    "FEATURE_BASIS_SCHEMA_VERSION",
    "FEATURE_BASIS_WINDOW_CONTRACT",
    "FROZEN_POLICY",
    "NOT_PROVABLE_FROM_RETAINED_EVIDENCE",
    "PopulationAdmission",
    "PopulationAdmissionConflict",
    "PopulationScoreGate",
    "PROVEN_V1_POPULATION_COMPATIBLE",
    "SAFE_V1_POPULATION",
    "SOURCE_CAPTURE_UNRESOLVED",
    "V1_POPULATION_NOT_PROVABLE",
    "V1PopulationNotProvable",
    "build_runtime_population_admission",
    "classify_retained_population_attestation",
    "evaluate_population_admission",
    "evaluate_feature_basis_admission",
    "persist_population_attestation",
]
