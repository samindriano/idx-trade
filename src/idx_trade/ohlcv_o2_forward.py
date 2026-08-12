"""Guarded infrastructure for the frozen O2 fresh-forward score ledger.

This module deliberately contains no provider calls and no outcome-reading
path. Official scoring is a later, separately reviewed action.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd

from .ohlcv_o1_research import V3_B_FEATURE_COLUMNS, raw_score
from .ohlcv_o2_geometry_research import O2_FEATURE_COLUMNS


O2_CANDIDATE_ID = "O2-GEOMETRY-FULL3-V1-CANDIDATE-001"
O2_MODEL_SHA256 = "42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb"
O2_FINAL_REFIT_ARTIFACT_MANIFEST_SHA256 = "a7045257aa85c9d1020d3fe4ceb60a1ee100aadc827305ddf5c608a616adc2d3"
O2_MODEL_MANIFEST_SHA256 = "535875e74a1b3a6532e95addf819521758798a767bc49ee9b30d54054a0ae7c2"
V3B_MODEL_SHA256 = "1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6"
V3B_MODEL_MANIFEST_SHA256 = "4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9"
V3B_ARCHITECTURE = "V3-B-STRUCTURE-LITE-V1-CANDIDATE-005"
O2_FEATURE_ORDER_SHA256 = "a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f"
V3B_FEATURE_ORDER_SHA256 = "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"
FORWARD_GATE_SESSION_COUNT = 100
H10_HORIZON = 10
SESSION_ARTIFACT_SCHEMA = "idx-trade/o2-forward-session-score-v1"
COUNTER_SCHEMA = "idx-trade/o2-forward-counter-v1"

PROTECTED_OUTCOME_COLUMNS = frozenset(
    {
        "binary_target",
        "label_status",
        "h10_label",
        "outcome",
        "outcome_label",
        "forward_outcome",
        "future_outcome",
        "future_return",
        "actual_return",
        "tp_first",
        "sl_first",
        "outcome_accessed",
        "outcome_opened",
    }
)
PROTECTED_OUTCOME_PREFIXES = ("outcome_", "forward_outcome_", "future_outcome_")


class ForwardContractError(RuntimeError):
    """Base class for fail-closed forward-contract violations."""


class ProtectedOutcomeAccessError(ForwardContractError):
    """Raised whenever a caller attempts to open protected outcome data."""


class PreFreezeSessionError(ForwardContractError):
    """Raised when a pre-freeze session is submitted to the official counter."""


class SessionGapError(ForwardContractError):
    """Raised when a session is skipped or submitted out of order."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256_text(values: Sequence[str]) -> str:
    payload = "\n".join(str(value) for value in values) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _manifest_sha256(manifest: Mapping[str, Any]) -> str:
    """Hash persisted manifest content without the self-referential field."""

    unsigned = {str(key): value for key, value in manifest.items() if key != "manifest_sha256"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assert_no_protected_outcome_columns(columns: Sequence[str]) -> None:
    blocked: list[str] = []
    for column in columns:
        name = str(column).strip().lower()
        if name in PROTECTED_OUTCOME_COLUMNS or name.startswith(PROTECTED_OUTCOME_PREFIXES):
            blocked.append(str(column))
    if blocked:
        raise ProtectedOutcomeAccessError(f"protected outcome columns are not permitted: {sorted(blocked)}")


def _hash_json_file(path: Path, expected_sha256: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ForwardContractError(f"manifest SHA mismatch for {path}: expected {expected_sha256}, got {actual}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ForwardContractError(f"manifest is not a JSON object: {path}")
    return value


@dataclass(frozen=True)
class FrozenModelIdentity:
    role: str
    candidate_id: str
    model_path: Path
    model_manifest_path: Path
    model_sha256: str
    model_manifest_sha256: str
    feature_order_sha256: str
    feature_columns: tuple[str, ...]
    parent_artifact_manifest_path: Path | None = None
    parent_artifact_manifest_sha256: str | None = None


@dataclass(frozen=True)
class FrozenModelBundle:
    o2_model: Any
    v3b_model: Any
    o2_identity: FrozenModelIdentity
    v3b_identity: FrozenModelIdentity


def _verify_model_identity(identity: FrozenModelIdentity) -> dict[str, Any]:
    model_sha = sha256_file(identity.model_path)
    if model_sha != identity.model_sha256:
        raise ForwardContractError(f"{identity.role} model SHA mismatch: expected {identity.model_sha256}, got {model_sha}")
    manifest = _hash_json_file(identity.model_manifest_path, identity.model_manifest_sha256)
    manifest_feature_hash = manifest.get("feature_order_sha256")
    if manifest_feature_hash != identity.feature_order_sha256:
        raise ForwardContractError(f"{identity.role} feature-order hash mismatch")
    if manifest.get("model_sha256") != identity.model_sha256:
        raise ForwardContractError(f"{identity.role} manifest/model hash mismatch")
    if manifest.get("fresh_forward_outcomes_accessed") is not False:
        raise ProtectedOutcomeAccessError(f"{identity.role} manifest is not fresh-forward clean")
    if manifest.get("forward_outcome_access_marker_written") is not False:
        raise ProtectedOutcomeAccessError(f"{identity.role} manifest has an outcome-access marker")
    if identity.role == "O2":
        if manifest.get("candidate_id") != identity.candidate_id:
            raise ForwardContractError("O2 candidate identity mismatch")
    if identity.role == "V3B":
        if manifest.get("architecture") != identity.candidate_id:
            raise ForwardContractError("V3-B architecture identity mismatch")
    if identity.parent_artifact_manifest_path is not None:
        if identity.parent_artifact_manifest_sha256 is None:
            raise ForwardContractError("parent artifact manifest hash is required")
        _hash_json_file(identity.parent_artifact_manifest_path, identity.parent_artifact_manifest_sha256)
    return {
        "role": identity.role,
        "candidate_id": identity.candidate_id,
        "model_path": str(identity.model_path),
        "model_manifest_path": str(identity.model_manifest_path),
        "model_sha256": model_sha,
        "model_manifest_sha256": identity.model_manifest_sha256,
        "feature_order_sha256": identity.feature_order_sha256,
        "parent_artifact_manifest_path": str(identity.parent_artifact_manifest_path) if identity.parent_artifact_manifest_path else None,
        "parent_artifact_manifest_sha256": identity.parent_artifact_manifest_sha256,
    }


def load_frozen_model_bundle(o2_identity: FrozenModelIdentity, v3b_identity: FrozenModelIdentity) -> FrozenModelBundle:
    if o2_identity.role != "O2" or v3b_identity.role != "V3B":
        raise ForwardContractError("model roles must be O2 and V3B")
    _verify_model_identity(o2_identity)
    _verify_model_identity(v3b_identity)
    o2_model = joblib.load(o2_identity.model_path)
    v3b_model = joblib.load(v3b_identity.model_path)
    return FrozenModelBundle(o2_model=o2_model, v3b_model=v3b_model, o2_identity=o2_identity, v3b_identity=v3b_identity)


def _utc_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def resolve_first_post_freeze_session(calendar: pd.DataFrame, freeze_timestamp: Any) -> dict[str, Any]:
    """Resolve, rather than hard-code, the first official session after freeze."""

    required = {"session_index", "session_date", "session_start"}
    missing = required - set(calendar.columns)
    if missing:
        raise ForwardContractError(f"official calendar missing columns: {sorted(missing)}")
    if calendar.duplicated(["session_index"]).any() or calendar.duplicated(["session_date"]).any():
        raise ForwardContractError("official calendar has duplicate session identities")
    frame = calendar.copy()
    frame["session_index"] = pd.to_numeric(frame["session_index"], errors="raise").astype(int)
    frame["session_start_utc"] = pd.to_datetime(frame["session_start"], utc=True, errors="coerce")
    if frame["session_start_utc"].isna().any():
        raise ForwardContractError("official calendar contains invalid session_start")
    freeze = _utc_timestamp(freeze_timestamp)
    eligible = frame[frame["session_start_utc"] > freeze].sort_values("session_index", kind="mergesort")
    if eligible.empty:
        raise ForwardContractError("no official session starts strictly after the freeze timestamp")
    row = eligible.iloc[0]
    return {
        "session_index": int(row["session_index"]),
        "session_date": str(pd.Timestamp(row["session_date"]).date()),
        "session_start": str(row["session_start_utc"].isoformat()),
        "freeze_timestamp": freeze.isoformat(),
    }


def _require_session(calendar: pd.DataFrame, session_index: int, freeze_timestamp: Any) -> dict[str, Any]:
    first = resolve_first_post_freeze_session(calendar, freeze_timestamp)
    rows = calendar[pd.to_numeric(calendar["session_index"], errors="raise").astype(int).eq(int(session_index))]
    if len(rows) != 1:
        raise ForwardContractError(f"session_index is not a unique official calendar session: {session_index}")
    row = rows.iloc[0]
    session_start = _utc_timestamp(row["session_start"])
    if session_start <= _utc_timestamp(freeze_timestamp):
        raise PreFreezeSessionError(f"session {session_index} starts before or at the freeze")
    return {
        "session_index": int(row["session_index"]),
        "session_date": str(pd.Timestamp(row["session_date"]).date()),
        "session_start": session_start.isoformat(),
        "first_post_freeze_session_index": int(first["session_index"]),
    }


def _valid_geometry(frame: pd.DataFrame) -> pd.Series:
    values = frame[["open", "high", "low", "open_position", "open_to_high", "open_to_low"]].apply(pd.to_numeric, errors="coerce")
    open_values = values["open"].to_numpy(dtype=float)
    high_values = values["high"].to_numpy(dtype=float)
    low_values = values["low"].to_numpy(dtype=float)
    position = values["open_position"].to_numpy(dtype=float)
    to_high = values["open_to_high"].to_numpy(dtype=float)
    to_low = values["open_to_low"].to_numpy(dtype=float)
    denominator = high_values - low_values
    expected_position = np.divide(open_values - low_values, denominator, out=np.full(len(values), np.nan), where=denominator != 0)
    expected_to_high = np.divide(high_values, open_values, out=np.full(len(values), np.nan), where=open_values != 0) - 1.0
    expected_to_low = np.divide(low_values, open_values, out=np.full(len(values), np.nan), where=open_values != 0) - 1.0
    finite = np.isfinite(values.to_numpy(dtype=float)).all(axis=1)
    valid = (
        finite
        & (open_values > 0.0)
        & (high_values > 0.0)
        & (low_values > 0.0)
        & (high_values > low_values)
        & (open_values >= low_values)
        & (open_values <= high_values)
        & (position >= 0.0)
        & (position <= 1.0)
        & np.isclose(position, expected_position, rtol=0.0, atol=1e-12)
        & np.isclose(to_high, expected_to_high, rtol=0.0, atol=1e-12)
        & np.isclose(to_low, expected_to_low, rtol=0.0, atol=1e-12)
    )
    return pd.Series(valid, index=frame.index)


def _snapshot_provenance_hash(frame: pd.DataFrame) -> str:
    rows = frame[["ticker", "signal_date", "input_provenance_sha256"]].copy()
    rows["ticker"] = rows["ticker"].astype(str)
    rows["signal_date"] = pd.to_datetime(rows["signal_date"], errors="raise").dt.strftime("%Y-%m-%d")
    rows["input_provenance_sha256"] = rows["input_provenance_sha256"].astype(str)
    values = rows.sort_values(["ticker", "signal_date"], kind="mergesort").astype(str).agg("|".join, axis=1)
    return stable_sha256_text(values.tolist())


@dataclass(frozen=True)
class ForwardScoreResult:
    session: dict[str, Any]
    rows: pd.DataFrame
    snapshot_sha256: str
    snapshot_provenance_sha256: str
    o2_model_sha256: str
    v3b_model_sha256: str
    outcomes_accessed: bool = False


def score_forward_session(
    *,
    snapshot: pd.DataFrame,
    calendar: pd.DataFrame,
    session_index: int,
    freeze_timestamp: Any,
    model_bundle: FrozenModelBundle,
    snapshot_sha256: str,
) -> ForwardScoreResult:
    """Score one post-close snapshot without opening outcomes or calling providers."""

    assert_no_protected_outcome_columns(snapshot.columns)
    required = {
        "ticker",
        "signal_date",
        "signal_session_index",
        "v3b_eligible",
        "input_provenance_sha256",
        "open",
        "high",
        "low",
        *V3_B_FEATURE_COLUMNS,
        "open_position",
        "open_to_high",
        "open_to_low",
    }
    missing = required - set(snapshot.columns)
    if missing:
        raise ForwardContractError(f"forward snapshot missing columns: {sorted(missing)}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(snapshot_sha256).lower()):
        raise ForwardContractError("snapshot_sha256 must be a lowercase hexadecimal SHA-256")
    session = _require_session(calendar, session_index, freeze_timestamp)
    frame = snapshot.copy()
    frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="coerce").dt.normalize()
    expected_date = pd.Timestamp(session["session_date"])
    if frame["signal_date"].isna().any() or not frame["signal_date"].eq(expected_date).all():
        raise ForwardContractError("snapshot contains a different signal date")
    if not pd.to_numeric(frame["signal_session_index"], errors="coerce").eq(session_index).all():
        raise ForwardContractError("snapshot contains a different signal session index")
    if frame.duplicated(["ticker"]).any():
        raise ForwardContractError("forward snapshot has duplicate tickers")
    if frame["input_provenance_sha256"].isna().any() or (frame["input_provenance_sha256"].astype(str).str.len() != 64).any():
        raise ForwardContractError("every snapshot row requires an input provenance SHA-256")
    if frame["v3b_eligible"].isna().any():
        raise ForwardContractError("v3b_eligible cannot be missing")
    frame["v3b_eligible"] = frame["v3b_eligible"].astype(bool)
    geometry_valid = _valid_geometry(frame)
    eligible = frame["v3b_eligible"] & geometry_valid
    reasons = pd.Series("ELIGIBLE", index=frame.index, dtype="object")
    reasons.loc[~frame["v3b_eligible"]] = frame.loc[~frame["v3b_eligible"], "v3b_exclusion_reason"].astype(str) if "v3b_exclusion_reason" in frame.columns else "V3B_INELIGIBLE"
    reasons.loc[frame["v3b_eligible"] & ~geometry_valid] = "MISSING_OR_INVALID_OPEN_GEOMETRY"

    output = pd.DataFrame(
        {
            "ticker": frame["ticker"].astype(str),
            "signal_date": frame["signal_date"].dt.strftime("%Y-%m-%d"),
            "signal_session_index": int(session_index),
            "o2_eligible": eligible.astype(bool),
            "eligibility_reason": reasons.astype(str),
            "input_provenance_sha256": frame["input_provenance_sha256"].astype(str),
            "o2_raw_score": np.nan,
            "v3b_raw_score": np.nan,
        }
    )
    if eligible.any():
        eligible_frame = frame.loc[eligible]
        output.loc[eligible, "o2_raw_score"] = raw_score(model_bundle.o2_model, eligible_frame[list(O2_FEATURE_COLUMNS)])
        output.loc[eligible, "v3b_raw_score"] = raw_score(model_bundle.v3b_model, eligible_frame[list(V3_B_FEATURE_COLUMNS)])
    output["o2_model_sha256"] = model_bundle.o2_identity.model_sha256
    output["v3b_model_sha256"] = model_bundle.v3b_identity.model_sha256
    output["feature_order_sha256"] = O2_FEATURE_ORDER_SHA256
    return ForwardScoreResult(
        session=session,
        rows=output,
        snapshot_sha256=str(snapshot_sha256).lower(),
        snapshot_provenance_sha256=_snapshot_provenance_hash(frame),
        o2_model_sha256=model_bundle.o2_identity.model_sha256,
        v3b_model_sha256=model_bundle.v3b_identity.model_sha256,
    )


def persist_session_score_artifact(result: ForwardScoreResult, output_dir: Path) -> dict[str, Any]:
    """Persist one immutable score artifact and its hash manifest."""

    assert_no_protected_outcome_columns(result.rows.columns)
    output_dir.mkdir(parents=True, exist_ok=True)
    session_index = int(result.session["session_index"])
    session_date = str(result.session["session_date"])
    stem = f"session_{session_index:04d}_{session_date}"
    data_path = output_dir / f"{stem}.parquet"
    manifest_path = output_dir / f"{stem}.json"
    if data_path.exists() or manifest_path.exists():
        if not data_path.exists() or not manifest_path.exists():
            raise ForwardContractError("partial session artifact exists; refusing overwrite")
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("artifact_sha256") != sha256_file(data_path):
            raise ForwardContractError("existing session artifact hash differs; immutable overwrite refused")
        stored_manifest_sha = existing.get("manifest_sha256")
        if not isinstance(stored_manifest_sha, str) or len(stored_manifest_sha) != 64:
            raise ForwardContractError("existing session manifest has no verifiable manifest_sha256")
        if stored_manifest_sha != _manifest_sha256(existing):
            raise ForwardContractError("existing session manifest hash is invalid; immutable overwrite refused")
        return existing
    result.rows.to_parquet(data_path, index=False)
    data_sha = sha256_file(data_path)
    manifest = {
        "schema": SESSION_ARTIFACT_SCHEMA,
        "session_index": session_index,
        "session_date": session_date,
        "session_start": result.session["session_start"],
        "first_post_freeze_session_index": result.session["first_post_freeze_session_index"],
        "artifact_path": str(data_path),
        "artifact_sha256": data_sha,
        "snapshot_sha256": result.snapshot_sha256,
        "snapshot_provenance_sha256": result.snapshot_provenance_sha256,
        "feature_order_sha256": O2_FEATURE_ORDER_SHA256,
        "o2_model_sha256": result.o2_model_sha256,
        "v3b_model_sha256": result.v3b_model_sha256,
        "rows": int(len(result.rows)),
        "eligible_rows": int(result.rows["o2_eligible"].sum()),
        "outcomes_accessed": False,
        "manifest_path": str(manifest_path),
    }
    manifest["manifest_sha256"] = _manifest_sha256(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    if persisted.get("manifest_sha256") != _manifest_sha256(persisted):
        raise ForwardContractError("new session manifest failed self-verification")
    return persisted


@dataclass
class OfficialO2Counter:
    first_post_freeze_session_index: int
    session_count: int = 0
    last_session_index: int | None = None

    def register(self, artifact_manifest: Mapping[str, Any]) -> int:
        if artifact_manifest.get("schema") != SESSION_ARTIFACT_SCHEMA:
            raise ForwardContractError("not an O2 session artifact manifest")
        if artifact_manifest.get("outcomes_accessed") is not False:
            raise ProtectedOutcomeAccessError("session artifact is not outcome-clean")
        index = int(artifact_manifest["session_index"])
        if index < self.first_post_freeze_session_index:
            raise PreFreezeSessionError(f"session {index} predates the official O2 counter")
        expected = self.first_post_freeze_session_index + self.session_count
        if index != expected:
            raise SessionGapError(f"expected session {expected}, received {index}")
        if not artifact_manifest.get("artifact_sha256") or not artifact_manifest.get("manifest_sha256"):
            raise ForwardContractError("session artifact must be hash-manifested before counting")
        self.session_count += 1
        self.last_session_index = index
        return self.session_count

    def is_mature(self, current_session_index: int) -> bool:
        return self.session_count == FORWARD_GATE_SESSION_COUNT and self.last_session_index is not None and int(current_session_index) >= self.last_session_index + H10_HORIZON

    def evaluation_ready(self, current_session_index: int) -> bool:
        return self.is_mature(current_session_index)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": COUNTER_SCHEMA,
            "first_post_freeze_session_index": self.first_post_freeze_session_index,
            "session_count": self.session_count,
            "last_session_index": self.last_session_index,
            "required_sessions": FORWARD_GATE_SESSION_COUNT,
            "h10_horizon": H10_HORIZON,
            "outcomes_accessed": False,
        }


def _validate_counter(counter: OfficialO2Counter) -> None:
    if counter.first_post_freeze_session_index < 0:
        raise ForwardContractError("first post-freeze session index must be non-negative")
    if not 0 <= counter.session_count <= FORWARD_GATE_SESSION_COUNT:
        raise ForwardContractError("counter session_count is outside the frozen range")
    if counter.session_count == 0:
        if counter.last_session_index is not None:
            raise ForwardContractError("empty counter cannot have a last session")
    else:
        expected_last = counter.first_post_freeze_session_index + counter.session_count - 1
        if counter.last_session_index != expected_last:
            raise ForwardContractError("counter last session is inconsistent with its consecutive count")


def load_counter_state(path: Path) -> OfficialO2Counter:
    """Reload persisted counter state and validate its monotonic contract."""

    if not path.is_file():
        raise FileNotFoundError(path)
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema") != COUNTER_SCHEMA:
        raise ForwardContractError("counter state schema mismatch")
    if state.get("required_sessions") != FORWARD_GATE_SESSION_COUNT or state.get("h10_horizon") != H10_HORIZON:
        raise ForwardContractError("counter state frozen contract mismatch")
    if state.get("outcomes_accessed") is not False:
        raise ProtectedOutcomeAccessError("counter state is not outcome-clean")
    counter = OfficialO2Counter(
        first_post_freeze_session_index=int(state["first_post_freeze_session_index"]),
        session_count=int(state.get("session_count", 0)),
        last_session_index=None if state.get("last_session_index") is None else int(state["last_session_index"]),
    )
    _validate_counter(counter)
    return counter


def persist_counter_state(counter: OfficialO2Counter, path: Path) -> dict[str, Any]:
    """Persist monotonic counter state without allowing a rewind."""

    _validate_counter(counter)
    state = counter.to_dict()
    if path.exists():
        previous_counter = load_counter_state(path)
        if previous_counter.first_post_freeze_session_index != counter.first_post_freeze_session_index:
            raise ForwardContractError("counter first post-freeze boundary cannot change")
        if previous_counter.session_count > counter.session_count:
            raise ForwardContractError("counter state cannot move backwards")
        if previous_counter.session_count == counter.session_count and previous_counter.last_session_index != counter.last_session_index:
            raise ForwardContractError("counter state cannot change at the same count")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    return state


class OutcomeAccessGuard:
    """Explicit no-outcome API for the scoring/accumulation phase."""

    def __init__(self) -> None:
        self.outcomes_accessed = False

    def open(self, *_args: Any, **_kwargs: Any) -> None:
        raise ProtectedOutcomeAccessError("protected outcomes cannot be opened in the scoring lane")
