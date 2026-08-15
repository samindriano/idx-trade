"""Prospective zero-provider producer for Price / Trend / Confirmation State V1.

The producer consumes a pinned historical H/L/C/Volume panel plus verified
canonical forward ``model_input.parquet`` sessions.  A completed source session
``t`` produces an immutable state artifact for the next official session
``t+1`` under ``forward_monitoring/prospective``.  Target-session market data is
not required and no provider, model, counter, outcome, or Foreign Flow path is
called here.
"""

from __future__ import annotations

from io import BytesIO
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from .price_trend_state import (
    EVIDENCE_COLUMNS,
    STATE_COLUMNS,
    STATE_CONTRACT_VERSION,
    build_price_state_for_source_session,
)
from .provenance import sha256_file


ACCEPTED_PRICE_STATE_COMMIT = "a33863953b4521dd4549a3089f0da2cfdfb6dcd3"
SIDECAR_SCHEMA = "idx-trade/price-trend-confirmation-state-forward-v1"
ARTIFACT_FILENAME = "price_trend_confirmation_state_v1.parquet"
MANIFEST_FILENAME = "price_trend_confirmation_state_v1.manifest.json"

OUTPUT_COLUMNS = (
    "ticker",
    "source_session",
    "feature_session",
    *EVIDENCE_COLUMNS,
    *STATE_COLUMNS,
    "state_contract_version",
    "outcome_blind",
    "model_fitted",
    "trade_recommendation",
)

_FORBIDDEN_TOKENS = (
    "binary_target",
    "label_status",
    "outcome",
    "tp_first",
    "sl_first",
    "realized",
    "forward_return",
    "future_return",
    "target_return",
)

_ALLOWED_STATES: dict[str, set[str]] = {
    "trend_state": {"UPTREND", "DOWNTREND", "BASING", "EARLY_REVERSAL", "TRANSITION", "INDETERMINATE"},
    "ma_structure_state": {"BULLISH_STACK", "BEARISH_STACK", "RECOVERING", "WEAKENING", "MIXED", "INDETERMINATE"},
    "long_term_state": {"ABOVE_RISING_MA200", "BELOW_FALLING_MA200", "MIXED", "UNAVAILABLE", "INDETERMINATE"},
    "swing_structure_state": {"HIGHER_LOW_HIGHER_HIGH", "HIGHER_LOW_ONLY", "LOWER_LOW_LOWER_HIGH", "LOWER_LOW_ONLY", "MIXED", "INDETERMINATE"},
    "volume_state": {"EXPANDING", "CONTRACTING", "NORMAL", "INDETERMINATE"},
    "volatility_state": {"EXPANDING", "CONTRACTING", "NORMAL", "INDETERMINATE"},
    "confirmation_state": {"BREAKOUT_CONFIRMED", "BREAKOUT_WEAK_VOLUME", "FAILED_BREAKOUT_RECENT", "NEAR_BREAKOUT", "NO_BREAKOUT", "INDETERMINATE"},
}


def _date(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"invalid date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


def _reject_outcome_like_columns(frame: pd.DataFrame) -> None:
    forbidden = [
        str(column)
        for column in frame.columns
        if any(token in str(column).lower() for token in _FORBIDDEN_TOKENS)
    ]
    if forbidden:
        raise ValueError(f"price-state market context contains outcome-like columns: {sorted(forbidden)}")


def _normalise_market(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize historical/canonical HLCV to the accepted V1 input schema."""

    _reject_outcome_like_columns(frame)
    data = frame.copy()
    if "session_date" not in data.columns and "date" in data.columns:
        data = data.rename(columns={"date": "session_date"})
    aliases = {
        "high": "raw_high",
        "low": "raw_low",
        "close": "raw_close",
        "volume": "raw_volume",
    }
    for source, target in aliases.items():
        if target not in data.columns and source in data.columns:
            data = data.rename(columns={source: target})

    required = {"ticker", "session_date", "raw_high", "raw_low", "raw_close", "raw_volume"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"price-state market context missing columns: {sorted(missing)}")
    data = data[["ticker", "session_date", "raw_high", "raw_low", "raw_close", "raw_volume"]].copy()
    data["ticker"] = (
        data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    if data["ticker"].eq("").any():
        raise ValueError("price-state market context contains empty ticker")

    parsed = pd.to_datetime(data["session_date"], errors="coerce")
    if parsed.isna().any():
        raise ValueError("price-state market context contains malformed session date")
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        parsed = parsed.dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
    data["session_date"] = parsed.dt.normalize()

    for column in ("raw_high", "raw_low", "raw_close", "raw_volume"):
        values = pd.to_numeric(data[column], errors="coerce")
        if values.isna().any() or (~np.isfinite(values.to_numpy(dtype=float))).any():
            raise ValueError(f"price-state market context contains invalid {column}")
        data[column] = values.astype(float)
    if (data[["raw_high", "raw_low", "raw_close"]] <= 0).any().any():
        raise ValueError("price-state market context contains non-positive HLC")
    if (data["raw_volume"] < 0).any():
        raise ValueError("price-state market context contains negative volume")
    if (data["raw_low"] > data["raw_high"]).any():
        raise ValueError("price-state market context contains low above high")
    outside = (data["raw_close"] < data["raw_low"]) | (data["raw_close"] > data["raw_high"])
    if outside.any():
        raise ValueError("price-state market context contains close outside high/low")
    if data.duplicated(["ticker", "session_date"]).any():
        raise ValueError("price-state market context contains duplicate ticker/session identity")
    return data.sort_values(["ticker", "session_date"], kind="mergesort").reset_index(drop=True)


def _read_calendar(path: Path, *, label: str) -> pd.DatetimeIndex:
    if not path.is_file():
        raise FileNotFoundError(f"{label} calendar missing: {path}")
    frame = pd.read_csv(path)
    column = "date" if "date" in frame.columns else "session_date" if "session_date" in frame.columns else None
    if column is None:
        raise ValueError(f"{label} calendar has no date column")
    parsed = pd.to_datetime(frame[column], errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"{label} calendar contains malformed date")
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        parsed = parsed.dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
    sessions = pd.DatetimeIndex(parsed.dt.normalize()).sort_values()
    if len(sessions) == 0 or sessions.has_duplicates:
        raise ValueError(f"{label} calendar is empty or duplicated")
    return sessions


def _calendar_union(historical: Iterable[object], forward: Iterable[object]) -> pd.DatetimeIndex:
    values = [_date(value) for value in historical] + [_date(value) for value in forward]
    sessions = pd.DatetimeIndex(sorted(set(values)))
    if len(sessions) < 2:
        raise ValueError("combined official calendar has fewer than two sessions")
    return sessions


def _merge_unique(left: pd.DataFrame, right: pd.DataFrame, *, label: str) -> pd.DataFrame:
    if left.empty:
        return right.copy()
    if right.empty:
        return left.copy()
    combined = pd.concat([left, right], ignore_index=True, sort=False)
    keys = ["ticker", "session_date"]
    duplicate = combined.duplicated(keys, keep=False)
    if duplicate.any():
        for _, group in combined.loc[duplicate].groupby(keys, sort=False):
            compare = group[["raw_high", "raw_low", "raw_close", "raw_volume"]].drop_duplicates()
            if len(compare) != 1:
                identity = group[keys].iloc[0].to_dict()
                raise RuntimeError(f"{label} has conflicting duplicate identity: {identity}")
    return combined.drop_duplicates(keys, keep="first").sort_values(keys, kind="mergesort").reset_index(drop=True)


def _expected_snapshot_path(runtime_root: Path, key: str) -> Path:
    return (runtime_root / "forward_monitoring" / "sessions" / key / "model_input.parquet").resolve()


def _read_verified_forward_market(
    runtime_root: Path,
    key: str,
    *,
    forward_calendar_path: Path,
    forward_calendar_sha256: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    session_dir = (runtime_root / "forward_monitoring" / "sessions" / key).resolve()
    manifest_path = (session_dir / "manifest.json").resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"canonical DATA_READY manifest missing for {key}")
    parent = json.loads(manifest_path.read_text(encoding="utf-8"))
    if parent.get("status") != "DATA_READY" or str(parent.get("session_date")) != key:
        raise RuntimeError(f"canonical session manifest is not exact DATA_READY for {key}")
    if parent.get("outcome_blind") is not True or parent.get("forward_outcomes_accessed") is not False:
        raise RuntimeError(f"canonical session manifest is not outcome-blind for {key}")

    snapshot_path = Path(str(parent.get("snapshot_path") or _expected_snapshot_path(runtime_root, key))).expanduser().resolve()
    if snapshot_path != _expected_snapshot_path(runtime_root, key):
        raise RuntimeError(f"canonical snapshot path identity mismatch for {key}")
    expected_snapshot_sha = str(parent.get("snapshot_sha256") or "").lower()
    if len(expected_snapshot_sha) != 64 or not snapshot_path.is_file() or sha256_file(snapshot_path) != expected_snapshot_sha:
        raise RuntimeError(f"canonical snapshot hash mismatch for {key}")

    manifest_calendar_path = Path(str(parent.get("calendar_path") or "")).expanduser().resolve()
    manifest_calendar_sha = str(parent.get("calendar_sha256") or "").lower()
    if manifest_calendar_path != forward_calendar_path.resolve():
        raise RuntimeError(f"canonical calendar path mismatch for {key}")
    if manifest_calendar_sha != forward_calendar_sha256.lower() or sha256_file(forward_calendar_path) != forward_calendar_sha256.lower():
        raise RuntimeError(f"canonical calendar hash mismatch for {key}")

    snapshot = _normalise_market(pd.read_parquet(snapshot_path))
    expected_session = _date(key)
    if not snapshot["session_date"].eq(expected_session).all():
        raise RuntimeError(f"canonical snapshot date mismatch for {key}")
    if snapshot.empty:
        raise RuntimeError(f"canonical snapshot is empty for {key}")
    return snapshot, {
        "session_date": key,
        "parent_manifest_path": str(manifest_path),
        "parent_manifest_sha256": sha256_file(manifest_path),
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": expected_snapshot_sha,
        "row_count": int(len(snapshot)),
    }


def _runtime_session_keys(runtime_root: Path, source: pd.Timestamp) -> list[str]:
    sessions_root = runtime_root / "forward_monitoring" / "sessions"
    if not sessions_root.is_dir():
        raise FileNotFoundError("forward monitoring sessions root is missing")
    keys: list[str] = []
    for directory in sessions_root.iterdir():
        if not directory.is_dir():
            continue
        try:
            value = _date(directory.name)
        except Exception:
            continue
        if value <= source:
            keys.append(value.date().isoformat())
    return sorted(set(keys))


def _context_fingerprint(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _write_parquet_exclusive(frame: pd.DataFrame, path: Path) -> None:
    payload = _parquet_bytes(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def _write_json_exclusive(value: Mapping[str, Any], path: Path) -> None:
    payload = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, default=str) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def _validate_state_artifact(frame: pd.DataFrame, *, source: pd.Timestamp, target: pd.Timestamp) -> pd.DataFrame:
    if list(frame.columns) != list(OUTPUT_COLUMNS):
        raise RuntimeError("price-state sidecar schema mismatch")
    if frame.empty:
        raise RuntimeError("price-state sidecar is empty")
    if frame.duplicated(["ticker", "feature_session"]).any():
        raise RuntimeError("price-state sidecar has duplicate ticker/feature-session identity")
    source_values = pd.to_datetime(frame["source_session"], errors="coerce").dt.normalize()
    target_values = pd.to_datetime(frame["feature_session"], errors="coerce").dt.normalize()
    if source_values.isna().any() or not source_values.eq(source).all():
        raise RuntimeError("price-state sidecar source-session mismatch")
    if target_values.isna().any() or not target_values.eq(target).all():
        raise RuntimeError("price-state sidecar feature-session mismatch")
    if not frame["state_contract_version"].eq(STATE_CONTRACT_VERSION).all():
        raise RuntimeError("price-state sidecar contract version mismatch")
    if not frame["outcome_blind"].eq(True).all():
        raise RuntimeError("price-state sidecar is not outcome-blind")
    if not frame["model_fitted"].eq(False).all() or not frame["trade_recommendation"].eq(False).all():
        raise RuntimeError("price-state sidecar contains prohibited model/trade flags")
    for column, allowed in _ALLOWED_STATES.items():
        observed = set(frame[column].astype(str).unique())
        if not observed <= allowed:
            raise RuntimeError(f"price-state sidecar has invalid {column}: {sorted(observed - allowed)}")
    return frame.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def materialize_price_trend_state_for_session(
    *,
    market_history: pd.DataFrame,
    official_sessions: Iterable[object],
    source_session: str | pd.Timestamp,
    output_directory: str | Path,
    input_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize exactly one accepted V1 target state from completed ``t``."""

    source = _date(source_session)
    sessions = pd.DatetimeIndex([_date(value) for value in official_sessions]).sort_values()
    if len(sessions) < 2 or sessions.has_duplicates or source not in set(sessions):
        raise RuntimeError("source is not in a unique official session calendar")
    position = int(sessions.get_loc(source))
    if position >= len(sessions) - 1:
        raise RuntimeError("source has no next official feature session")
    target = sessions[position + 1]

    market = _normalise_market(market_history)
    market = market.loc[market["session_date"].le(source)].reset_index(drop=True)
    if source not in set(market["session_date"]):
        raise RuntimeError("source market session is missing")
    if not market["session_date"].isin(set(sessions)).all():
        raise RuntimeError("market context contains a date outside the supplied official calendar")

    state = build_price_state_for_source_session(market, sessions, source)
    state = _validate_state_artifact(state, source=source, target=target)

    directory = Path(output_directory).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    artifact_path = directory / ARTIFACT_FILENAME
    manifest_path = directory / MANIFEST_FILENAME
    if artifact_path.exists() != manifest_path.exists():
        raise RuntimeError("incomplete immutable price-state artifact pair")

    provenance = dict(input_provenance)
    provenance["accepted_price_state_commit"] = ACCEPTED_PRICE_STATE_COMMIT
    provenance["source_session"] = source.date().isoformat()
    provenance["feature_session"] = target.date().isoformat()
    provenance["input_fingerprint"] = _context_fingerprint(provenance)

    distributions = {
        column: {str(key): int(value) for key, value in state[column].value_counts(dropna=False).sort_index().items()}
        for column in STATE_COLUMNS
    }

    created = False
    if artifact_path.exists():
        existing = pd.read_parquet(artifact_path)
        existing = _validate_state_artifact(existing, source=source, target=target)
        if list(existing.columns) != list(state.columns) or not existing.equals(state):
            raise RuntimeError("immutable price-state artifact revision conflict")
    else:
        _write_parquet_exclusive(state, artifact_path)
        created = True
    artifact_sha = sha256_file(artifact_path)

    manifest = {
        "status": "PRICE_TREND_CONFIRMATION_STATE_V1_FORWARD_READY",
        "schema": SIDECAR_SCHEMA,
        "state_contract_version": STATE_CONTRACT_VERSION,
        "accepted_price_state_commit": ACCEPTED_PRICE_STATE_COMMIT,
        "source_session": source.date().isoformat(),
        "feature_session": target.date().isoformat(),
        "row_count": int(len(state)),
        "ticker_count": int(state["ticker"].nunique()),
        "output_columns": list(OUTPUT_COLUMNS),
        "state_distributions": distributions,
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha,
        "input_provenance": provenance,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "outcomes_or_labels_accessed": False,
        "outcome_metrics_computed": False,
        "model_fit": False,
        "model_scoring": False,
        "trade_recommendation": False,
        "provider_calls": 0,
    }
    if manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing_manifest != manifest:
            raise RuntimeError("immutable price-state manifest revision conflict")
    else:
        _write_json_exclusive(manifest, manifest_path)

    if sha256_file(artifact_path) != artifact_sha:
        raise RuntimeError("price-state artifact changed during materialization")
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    if stored != manifest:
        raise RuntimeError("price-state manifest verification failed")
    return {
        "status": manifest["status"],
        "source_session": source.date().isoformat(),
        "feature_session": target.date().isoformat(),
        "created": created,
        "rows": int(len(state)),
        "tickers": int(state["ticker"].nunique()),
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "provider_calls": 0,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
    }


def produce_session_price_trend_state(
    *,
    runtime_root: str | Path,
    source_session: str | pd.Timestamp,
    historical_panel_path: str | Path,
    historical_panel_sha256: str,
    historical_calendar_path: str | Path,
    historical_calendar_sha256: str,
    forward_calendar_path: str | Path,
    forward_calendar_sha256: str,
) -> dict[str, Any]:
    """Build prospective ``t+1`` state from pinned history + canonical EOD through ``t``."""

    runtime = Path(runtime_root).expanduser().resolve()
    source = _date(source_session)
    historical_path = Path(historical_panel_path).expanduser().resolve()
    historical_calendar = Path(historical_calendar_path).expanduser().resolve()
    forward_calendar = Path(forward_calendar_path).expanduser().resolve()

    pins = (
        (historical_path, historical_panel_sha256, "historical market panel"),
        (historical_calendar, historical_calendar_sha256, "historical calendar"),
        (forward_calendar, forward_calendar_sha256, "forward calendar"),
    )
    for path, expected, label in pins:
        if not path.is_file() or len(str(expected)) != 64 or sha256_file(path) != str(expected).lower():
            raise RuntimeError(f"{label} missing or hash-mismatched")

    historical_sessions = _read_calendar(historical_calendar, label="historical")
    forward_sessions = _read_calendar(forward_calendar, label="forward")
    sessions = _calendar_union(historical_sessions, forward_sessions)
    if source not in set(forward_sessions):
        raise RuntimeError("source session is absent from the pinned forward calendar")
    source_position = int(forward_sessions.get_loc(source))
    if source_position >= len(forward_sessions) - 1:
        raise RuntimeError("source has no next official session in the pinned forward calendar")
    target = forward_sessions[source_position + 1]
    union_position = int(sessions.get_loc(source))
    if union_position >= len(sessions) - 1 or sessions[union_position + 1] != target:
        raise RuntimeError("historical/forward calendar union changes the next-session identity")

    historical_market = _normalise_market(pd.read_parquet(historical_path))
    if not historical_market["session_date"].isin(set(historical_sessions)).all():
        raise RuntimeError("historical market panel contains dates outside its pinned calendar")
    historical_market = historical_market.loc[historical_market["session_date"].le(source)].reset_index(drop=True)

    keys = _runtime_session_keys(runtime, source)
    if source.date().isoformat() not in keys:
        raise RuntimeError("source session is not present as canonical forward DATA_READY context")
    forward_parts: list[pd.DataFrame] = []
    forward_provenance: list[dict[str, Any]] = []
    for key in keys:
        if _date(key) not in set(forward_sessions):
            continue
        frame, meta = _read_verified_forward_market(
            runtime,
            key,
            forward_calendar_path=forward_calendar,
            forward_calendar_sha256=forward_calendar_sha256,
        )
        forward_parts.append(frame)
        forward_provenance.append(meta)

    forward_market = (
        _normalise_market(pd.concat(forward_parts, ignore_index=True, sort=False))
        if forward_parts
        else pd.DataFrame(columns=["ticker", "session_date", "raw_high", "raw_low", "raw_close", "raw_volume"])
    )
    market = _merge_unique(historical_market, forward_market, label="price-state market context")
    market = market.loc[market["session_date"].le(source)].reset_index(drop=True)
    if source not in set(market["session_date"]):
        raise RuntimeError("combined market context is missing source session")

    output_directory = (
        runtime
        / "forward_monitoring"
        / "prospective"
        / "price_trend_confirmation_state_v1"
        / target.date().isoformat()
    )
    provenance: dict[str, Any] = {
        "historical_panel_path": str(historical_path),
        "historical_panel_sha256": historical_panel_sha256.lower(),
        "historical_calendar_path": str(historical_calendar),
        "historical_calendar_sha256": historical_calendar_sha256.lower(),
        "forward_calendar_path": str(forward_calendar),
        "forward_calendar_sha256": forward_calendar_sha256.lower(),
        "forward_sources": forward_provenance,
        "combined_session_first": sessions[0].date().isoformat(),
        "combined_session_last": sessions[-1].date().isoformat(),
        "combined_session_count": int(len(sessions)),
    }
    return materialize_price_trend_state_for_session(
        market_history=market,
        official_sessions=sessions,
        source_session=source,
        output_directory=output_directory,
        input_provenance=provenance,
    )


def verify_prospective_price_trend_state(
    runtime_root: str | Path,
    feature_session: str | pd.Timestamp,
) -> bool:
    """Fail closed unless a stored prospective sidecar and all pinned inputs verify."""

    runtime = Path(runtime_root).expanduser().resolve()
    target = _date(feature_session)
    directory = (
        runtime
        / "forward_monitoring"
        / "prospective"
        / "price_trend_confirmation_state_v1"
        / target.date().isoformat()
    ).resolve()
    artifact_path = directory / ARTIFACT_FILENAME
    manifest_path = directory / MANIFEST_FILENAME
    if not artifact_path.is_file() or not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "PRICE_TREND_CONFIRMATION_STATE_V1_FORWARD_READY":
            return False
        if manifest.get("schema") != SIDECAR_SCHEMA or manifest.get("accepted_price_state_commit") != ACCEPTED_PRICE_STATE_COMMIT:
            return False
        if manifest.get("outcome_blind") is not True or manifest.get("forward_outcomes_accessed") is not False:
            return False
        if any(manifest.get(key) is not False for key in ("outcomes_or_labels_accessed", "outcome_metrics_computed", "model_fit", "model_scoring", "trade_recommendation")):
            return False
        if int(manifest.get("provider_calls", -1)) != 0:
            return False
        if Path(str(manifest.get("artifact_path") or "")).expanduser().resolve() != artifact_path:
            return False
        if str(manifest.get("artifact_sha256") or "").lower() != sha256_file(artifact_path):
            return False
        source = _date(manifest.get("source_session"))
        if _date(manifest.get("feature_session")) != target:
            return False
        artifact = _validate_state_artifact(pd.read_parquet(artifact_path), source=source, target=target)
        if len(artifact) != int(manifest.get("row_count", -1)):
            return False
        if artifact["ticker"].nunique() != int(manifest.get("ticker_count", -1)):
            return False

        provenance = manifest.get("input_provenance")
        if not isinstance(provenance, dict) or provenance.get("accepted_price_state_commit") != ACCEPTED_PRICE_STATE_COMMIT:
            return False
        for path_key, hash_key in (
            ("historical_panel_path", "historical_panel_sha256"),
            ("historical_calendar_path", "historical_calendar_sha256"),
            ("forward_calendar_path", "forward_calendar_sha256"),
        ):
            path = Path(str(provenance.get(path_key) or "")).expanduser().resolve()
            expected = str(provenance.get(hash_key) or "").lower()
            if not path.is_file() or len(expected) != 64 or sha256_file(path) != expected:
                return False
        forward_sources = provenance.get("forward_sources")
        if not isinstance(forward_sources, list) or not forward_sources:
            return False
        source_key = source.date().isoformat()
        source_seen = False
        for item in forward_sources:
            if not isinstance(item, dict):
                return False
            parent = Path(str(item.get("parent_manifest_path") or "")).expanduser().resolve()
            snapshot = Path(str(item.get("snapshot_path") or "")).expanduser().resolve()
            if not parent.is_file() or sha256_file(parent) != str(item.get("parent_manifest_sha256") or "").lower():
                return False
            if not snapshot.is_file() or sha256_file(snapshot) != str(item.get("snapshot_sha256") or "").lower():
                return False
            if str(item.get("session_date")) == source_key:
                source_seen = True
        if not source_seen:
            return False
        expected_fingerprint = _context_fingerprint({key: value for key, value in provenance.items() if key != "input_fingerprint"})
        if provenance.get("input_fingerprint") != expected_fingerprint:
            return False
        return True
    except Exception:
        return False
