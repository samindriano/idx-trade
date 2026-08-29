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
from zoneinfo import ZoneInfo

import pandas as pd

from .forward_monitoring import (
    _existing_session,
    _verify_ready_artifacts,
    runtime_paths,
)
from .provenance import sha256_file
from .security_master import (
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
)


SCHEMA_VERSION = "idx_trade_v4_x1_population_admission_v1"
SAFE_V1_POPULATION = "SAFE_V1_POPULATION"
V1_POPULATION_NOT_PROVABLE = "V1_POPULATION_NOT_PROVABLE"
PROVEN_V1_POPULATION_COMPATIBLE = "PROVEN_V1_POPULATION_COMPATIBLE"
NOT_PROVABLE_FROM_RETAINED_EVIDENCE = "NOT_PROVABLE_FROM_RETAINED_EVIDENCE"
FREEZE_LOCAL_DATE = date(2026, 8, 20)
FROZEN_POLICY = (
    "ACCEPTED_CLEAN_BASELINE_PLUS_RUNTIME_IDENTITIES_WITH_LISTED_FROM_STRICTLY_AFTER_2026_08_20_ONLY"
)
DELISTING_COMPLETENESS = "MONTHLY_META_TOTAL_ITEMS_EXHAUSTIVE_PAGINATION"
LEGAL_DELISTING_SOURCE = "IDX_DIGITAL_STATISTIC_DELISTING"
JAKARTA = ZoneInfo("Asia/Jakarta")
TICKER_RE = re.compile(r"^[A-Z0-9]{4}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")


class PopulationAdmissionConflict(RuntimeError):
    """An immutable admission marker was asked to change identity."""


@dataclass(frozen=True)
class PopulationAdmission:
    status: str
    session_date: str
    expected_tickers: tuple[str, ...]
    observed_tickers: tuple[str, ...]
    added_tickers: tuple[str, ...]
    removed_tickers: tuple[str, ...]
    reason_codes: tuple[str, ...]
    identity_cases: Mapping[str, Any]
    expected_ticker_set_sha256: str
    observed_ticker_set_sha256: str
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
            "expected_tickers": list(self.expected_tickers),
            "observed_tickers": list(self.observed_tickers),
            "added_tickers": list(self.added_tickers),
            "removed_tickers": list(self.removed_tickers),
            "reason_codes": list(self.reason_codes),
            "identity_cases": dict(self.identity_cases),
            "expected_ticker_set_sha256": self.expected_ticker_set_sha256,
            "observed_ticker_set_sha256": self.observed_ticker_set_sha256,
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


def _anchor_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_frame(("ticker", "market", "as_of_date", "state", "source", "source_ref", "evidence_type"))
    required = {"ticker", "market", "as_of_date", "state", "source", "evidence_type"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"TRADABILITY_ANCHOR_COLUMNS_MISSING:{sorted(missing)}")
    data = frame.copy()
    data["ticker"] = data["ticker"].map(_safe_ticker)
    data["as_of_date"] = _frame_date_series(data["as_of_date"], "TRADABILITY_ANCHOR")
    data["state"] = data["state"].astype(str).str.upper().str.strip()
    if (~data["state"].isin({"ACTIVE", "NO_TRADE", "SUSPENDED", "FCA_WATCHLIST"})).any():
        raise ValueError("TRADABILITY_ANCHOR_STATE_UNRESOLVED")
    for column in ("source", "evidence_type"):
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


def _states_at(
    intervals: pd.DataFrame,
    anchors: pd.DataFrame,
    ticker: str,
    session: str,
) -> set[str]:
    target = pd.Timestamp(session)
    states: set[str] = set()
    if not intervals.empty:
        rows = intervals[
            intervals["ticker"].eq(ticker)
            & intervals["market"].isin(["REGULAR", "ALL"])
            & intervals["effective_from"].le(target)
            & (intervals["effective_to"].isna() | intervals["effective_to"].ge(target))
        ]
        exact = rows[rows["market"].eq("REGULAR")]
        rows = exact if not exact.empty else rows[rows["market"].eq("ALL")]
        states.update(rows["state"].astype(str).tolist())
    if not anchors.empty:
        rows = anchors[
            anchors["ticker"].eq(ticker)
            & anchors["market"].isin(["REGULAR", "ALL"])
            & anchors["as_of_date"].eq(target)
        ]
        exact = rows[rows["market"].eq("REGULAR")]
        rows = exact if not exact.empty else rows[rows["market"].eq("ALL")]
        states.update(rows["state"].astype(str).tolist())
    return states


def _compatible(point: str, explicit: set[str]) -> bool:
    if not explicit:
        return True
    if len(explicit) != 1:
        return False
    state = next(iter(explicit))
    return point == state or (
        point == "NO_TRADE" and state in {"SUSPENDED", "FCA_WATCHLIST"}
    )


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
    post_freeze_history: Mapping[str, int] | None = None,
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
    metadata["population_source"] = "FROZEN_BASELINE_PLUS_LEGAL_IDENTITY_AND_INDEPENDENT_TRADABILITY"

    expected: tuple[str, ...] = ()
    observed: tuple[str, ...] = ()
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
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
        baseline_set = set(baseline_live["ticker"])
        current_set = set(current["ticker"])
        missing = sorted(baseline_set - current_set)
        if missing:
            reasons.append("BASELINE_IDENTITY_NOT_PROVABLE:" + ",".join(missing))

        history = {str(key).upper().strip(): int(value) for key, value in (post_freeze_history or {}).items()}
        legal_set = {
            str(value).upper().strip()
            for value in ((security_master_evidence or {}).get("delisted_tickers") or ())
        }
        legal_set.update(str(value).upper().strip() for value in ((security_master_evidence or {}).get("legal_delisting_tickers") or ()))
        legal_complete = (security_master_evidence or {}).get("delisting_completeness") == DELISTING_COMPLETENESS
        additions = sorted(current_set - baseline_set)
        legal_absent: list[str] = []
        unchanged: list[str] = []
        for row in current.itertuples(index=False):
            ticker = str(row.ticker)
            listed_from = pd.Timestamp(row.listed_from)
            listed_to = pd.Timestamp(row.listed_to) if pd.notna(row.listed_to) else None
            if listed_from > target:
                reasons.append(f"FUTURE_IDENTITY:{ticker}")
            if ticker in additions:
                if listed_from <= freeze:
                    reasons.append(f"POST_FREEZE_RULE_VIOLATION:{ticker}")
                if history.get(ticker, 0) <= 0:
                    reasons.append(f"POST_FREEZE_IDENTITY_HISTORY_NOT_PROVABLE:{ticker}")
            elif ticker in baseline_set:
                if listed_to is not None and listed_to < freeze:
                    reasons.append(f"DELISTING_BEFORE_FREEZE_INCOMPATIBLE:{ticker}")
                if listed_to is not None and listed_to < target:
                    if ticker not in legal_set and not (legal_complete and str(getattr(row, "source", "")) == LEGAL_DELISTING_SOURCE):
                        reasons.append(f"DELISTING_EVIDENCE_NOT_VERIFIED:{ticker}")
                    else:
                        legal_absent.append(ticker)
                else:
                    unchanged.append(ticker)
        identity_cases = {
            "baseline_unchanged": sorted(unchanged),
            "baseline_legally_absent": sorted(legal_absent),
            "post_freeze_additions": additions,
            "missing_baseline": missing,
        }

        points = _point_frame(point_evidence, session)
        intervals = _interval_frame(None if security_master_evidence is None else security_master_evidence.get("tradability_intervals"))
        anchors = _anchor_frame(None if security_master_evidence is None else security_master_evidence.get("tradability_anchors"))
        live = current[
            current["listed_from"].le(target)
            & (current["listed_to"].isna() | current["listed_to"].ge(target))
        ]
        point_by_ticker = {str(row.ticker): str(row.point_state) for row in points.itertuples(index=False)}
        active_expected: list[str] = []
        for ticker in sorted(set(live["ticker"])):
            explicit = _states_at(intervals, anchors, ticker, session)
            point = point_by_ticker.get(ticker)
            if point is None and not explicit:
                reasons.append(f"TRADABILITY_STATE_NOT_EXPLICIT:{ticker}")
                continue
            if point is not None and not _compatible(point, explicit):
                reasons.append(f"TRADABILITY_CONFLICT:{ticker}")
                continue
            resolved = point or (next(iter(explicit)) if len(explicit) == 1 else "")
            if not resolved:
                reasons.append(f"TRADABILITY_STATE_AMBIGUOUS:{ticker}")
            elif resolved == "ACTIVE":
                active_expected.append(ticker)
        live_set = set(live["ticker"])
        extra_points = sorted(set(point_by_ticker) - live_set)
        if extra_points:
            reasons.append("POINT_EVIDENCE_OUTSIDE_LIVE_IDENTITY:" + ",".join(extra_points))
        model = model_input.copy()
        if not {"ticker", "date"}.issubset(model.columns):
            raise ValueError("MODEL_INPUT_COLUMNS_MISSING")
        model["ticker"] = model["ticker"].map(_safe_ticker)
        model["date"] = _frame_date_series(model["date"], "MODEL_INPUT")
        if not model["date"].eq(target).all():
            raise ValueError("MODEL_INPUT_SESSION_MISMATCH")
        if model.duplicated(["ticker", "date"]).any():
            raise ValueError("MODEL_INPUT_DUPLICATE")
        observed = tuple(sorted(set(model["ticker"])))
        expected = tuple(sorted(set(active_expected)))
        added = tuple(sorted(set(observed) - set(expected)))
        removed = tuple(sorted(set(expected) - set(observed)))
        if added:
            reasons.append("MODEL_INPUT_TICKER_NOT_EXPECTED:" + ",".join(added))
        if removed:
            reasons.append("MODEL_INPUT_EXPECTED_TICKER_MISSING:" + ",".join(removed))
        if set(observed) - live_set:
            reasons.append("MODEL_INPUT_TICKER_NOT_LIVE:" + ",".join(sorted(set(observed) - live_set)))
    except Exception as exc:
        reasons.append(str(exc))

    deduped_reasons = tuple(dict.fromkeys(reasons))
    metadata["population_equality"] = not added and not removed and not any(
        reason.startswith(("MODEL_INPUT_TICKER_NOT_EXPECTED", "MODEL_INPUT_EXPECTED_TICKER_MISSING"))
        for reason in deduped_reasons
    )
    metadata["expected_ticker_set_sha256"] = _set_hash(expected)
    metadata["observed_ticker_set_sha256"] = _set_hash(observed)
    status = SAFE_V1_POPULATION if not deduped_reasons else V1_POPULATION_NOT_PROVABLE
    return PopulationAdmission(
        status=status,
        session_date=session,
        expected_tickers=expected,
        observed_tickers=observed,
        added_tickers=added,
        removed_tickers=removed,
        reason_codes=deduped_reasons,
        identity_cases=identity_cases,
        expected_ticker_set_sha256=_set_hash(expected),
        observed_ticker_set_sha256=_set_hash(observed),
        metadata=metadata,
    )


def _git_blobs(repo_root: Path) -> tuple[dict[str, str], dict[str, str]]:
    config_path = repo_root / "config" / "ranking_v4_x1_clean_prospective_score_v1.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    expected = {str(key): str(value) for key, value in (config.get("pinned_git_blobs") or {}).items()}
    actual: dict[str, str] = {}
    for path in expected:
        actual[path] = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", f"HEAD:{path}"],
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
    metadata.setdefault("population_source", "FROZEN_BASELINE_PLUS_LEGAL_IDENTITY_AND_INDEPENDENT_TRADABILITY")
    return PopulationAdmission(
        status=V1_POPULATION_NOT_PROVABLE,
        session_date=session,
        expected_tickers=(),
        observed_tickers=(),
        added_tickers=(),
        removed_tickers=(),
        reason_codes=reasons or ("RUNTIME_EVIDENCE_NOT_PROVABLE",),
        identity_cases={},
        expected_ticker_set_sha256=_set_hash(()),
        observed_ticker_set_sha256=_set_hash(()),
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
        security_evidence: dict[str, Any] = {}
        if not current_manifest_path.is_file():
            return _runtime_failure(session_date=session, reasons=("CURRENT_IDENTITY_EVIDENCE_MANIFEST_MISSING",))
        loaded = json.loads(current_manifest_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return _runtime_failure(session_date=session, reasons=("CURRENT_IDENTITY_EVIDENCE_MANIFEST_INVALID",))
        security_evidence = loaded
        if (
            Path(str(security_evidence.get("security_master_path") or "")).expanduser().resolve() != current_path
            or str(security_evidence.get("security_master_sha256") or "") != sha256_file(current_path)
            or str(security_evidence.get("baseline_sha256") or "") != sha256_file(Path(clean_security_master).expanduser().resolve())
            or (security_evidence.get("guards") or {}).get("outcome_accessed") is not False
            or (security_evidence.get("guards") or {}).get("protected_forward_accessed") is not False
        ):
            return _runtime_failure(session_date=session, reasons=("CURRENT_IDENTITY_EVIDENCE_BINDING_INVALID",))
        current = pd.read_csv(current_path)
        baseline = pd.read_csv(baseline_path)
        point = pd.read_parquet(Path(str(eod["evidence_path"])))
        model_input = pd.read_parquet(Path(str(eod["snapshot_path"])))
        panel = pd.read_parquet(Path(clean_panel).expanduser().resolve())
        current_work = current.copy()
        history: dict[str, int] = {}
        if {"ticker", "date"}.issubset(panel.columns):
            panel["ticker"] = panel["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
            panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
            for row in current_work.itertuples(index=False):
                ticker = str(getattr(row, "ticker")).upper().strip()
                listed_from = pd.to_datetime(getattr(row, "listed_from"), errors="coerce")
                if pd.notna(listed_from):
                    history[ticker] = int(
                        panel.loc[
                            panel["ticker"].eq(ticker)
                            & panel["date"].ge(pd.Timestamp(listed_from).normalize())
                            & panel["date"].le(pd.Timestamp(session)),
                            "date",
                        ].nunique()
                    )
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
            post_freeze_history=history,
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


def persist_population_attestation(runtime_root: str | Path, admission: PopulationAdmission) -> PopulationAdmission:
    """Persist a create-only marker; same evidence is idempotent, changes conflict."""

    path = (Path(runtime_root).expanduser().resolve() / "forward_monitoring" / "population_admission" / f"{admission.session_date}.json")
    payload = admission.to_dict()
    payload.pop("attestation_path", None)
    payload.pop("attestation_sha256", None)
    identity = dict(payload)
    identity.pop("metadata", None)
    identity["metadata"] = {
        key: value
        for key, value in (payload.get("metadata") or {}).items()
        if key != "observed_at_jakarta"
    }
    identity_sha = hashlib.sha256(_canonical_json(identity)).hexdigest()
    payload["immutable_identity_sha256"] = identity_sha
    raw = _canonical_json(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0))
    except FileExistsError:
        existing_raw = path.read_bytes()
        try:
            existing = json.loads(existing_raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PopulationAdmissionConflict("POPULATION_ATTESTATION_EXISTING_INVALID") from exc
        if existing.get("immutable_identity_sha256") != identity_sha:
            raise PopulationAdmissionConflict("POPULATION_ATTESTATION_IDENTITY_CONFLICT")
        return PopulationAdmission(
            **{**admission.__dict__, "attestation_path": str(path), "attestation_sha256": hashlib.sha256(existing_raw).hexdigest()}
        )
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return PopulationAdmission(
        **{**admission.__dict__, "attestation_path": str(path), "attestation_sha256": hashlib.sha256(raw).hexdigest()}
    )


def classify_retained_population_attestation(
    attestation: Mapping[str, Any],
    *,
    expected_session_date: str,
    expected_baseline_sha256: str,
) -> str:
    """Classify retained 2/100 evidence without outcomes, rescoring, or counters."""

    try:
        if attestation.get("schema_version") != SCHEMA_VERSION:
            raise ValueError
        if attestation.get("status") != SAFE_V1_POPULATION:
            raise ValueError
        if _safe_session(attestation.get("session_date")) != _safe_session(expected_session_date):
            raise ValueError
        metadata = attestation.get("metadata")
        if not isinstance(metadata, Mapping):
            raise ValueError
        if metadata.get("frozen_baseline_sha256") != str(expected_baseline_sha256).lower():
            raise ValueError
        if metadata.get("listed_to_overlay_applied") is not False:
            raise ValueError
        if metadata.get("population_equality") is not True:
            raise ValueError
        if attestation.get("expected_ticker_set_sha256") != attestation.get("observed_ticker_set_sha256"):
            raise ValueError
        if not HEX64_RE.fullmatch(str(attestation.get("immutable_identity_sha256") or "")):
            raise ValueError
        if not isinstance(attestation.get("expected_tickers"), list) or not isinstance(attestation.get("observed_tickers"), list):
            raise ValueError
        if attestation.get("added_tickers") or attestation.get("removed_tickers"):
            raise ValueError
        same_session_eod = metadata.get("same_session_eod")
        if not isinstance(same_session_eod, Mapping) or same_session_eod.get("status") != "DATA_READY":
            raise ValueError
        if not metadata.get("frozen_science_blobs"):
            raise ValueError
        if attestation.get("reason_codes"):
            raise ValueError
        return PROVEN_V1_POPULATION_COMPATIBLE
    except (TypeError, ValueError):
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
