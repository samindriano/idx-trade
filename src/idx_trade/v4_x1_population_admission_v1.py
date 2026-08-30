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
from .forward_ohlcv import validate_model_input_regular_market_value
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
) -> PopulationAdmission:
    """Load only retained, same-session evidence and produce an admission."""

    try:
        observed = datetime.fromisoformat(str(observed_by))
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("OBSERVED_AT_NOT_TIMEZONE_AWARE")
        session = observed.astimezone(JAKARTA).date().isoformat()
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
    "FREEZE_LOCAL_DATE",
    "FROZEN_POLICY",
    "NOT_PROVABLE_FROM_RETAINED_EVIDENCE",
    "PopulationAdmission",
    "PopulationAdmissionConflict",
    "PopulationScoreGate",
    "PROVEN_V1_POPULATION_COMPATIBLE",
    "SAFE_V1_POPULATION",
    "V1_POPULATION_NOT_PROVABLE",
    "V1PopulationNotProvable",
    "build_runtime_population_admission",
    "classify_retained_population_attestation",
    "evaluate_population_admission",
    "persist_population_attestation",
]
