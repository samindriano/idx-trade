"""Prospective wiring for the Foreign Flow Setup State V1 sidecar.

This adapter deliberately consumes a previously materialized, outcome-blind
Foreign Flow Representation V2 artifact.  It does not rebuild V2 from one
session, call a provider, or infer missing history.  The raw Stock Summary
sidecar and the V2 representation are both pinned in the resulting manifest.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .foreign_flow_features_v2 import OUTPUT_COLUMNS_V2
from .foreign_flow_setup_sidecar import build_foreign_flow_setup_sidecar
from .foreign_flow_setup_state import DEFAULT_THRESHOLDS, SetupThresholds
from .forward_foreign_flow import (
    _canonical_evidence,
    _write_parquet_exclusive,
)
from .provenance import sha256_file


SETUP_SIDECAR_FILENAME = "idx_foreign_flow_setup.parquet"
SETUP_MANIFEST_FILENAME = "idx_foreign_flow_setup.manifest.json"
REPRESENTATION_FILENAME = "foreign_flow_representation_v2.parquet"
REPRESENTATION_MANIFEST_FILENAME = "foreign_flow_representation_v2.manifest.json"
_FORBIDDEN_TOKENS = (
    "binary_target",
    "label_status",
    "outcome",
    "tp_first",
    "sl_first",
    "realized",
)


def _date(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"invalid session date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError(f"{label} is unreadable") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} is not an object")
    return value


def _representation_paths(
    directory: Path,
    representation_path: str | Path | None,
    representation_manifest_path: str | Path | None,
) -> tuple[Path, Path]:
    artifact = (
        Path(representation_path).expanduser().resolve()
        if representation_path is not None
        else directory / REPRESENTATION_FILENAME
    )
    manifest = (
        Path(representation_manifest_path).expanduser().resolve()
        if representation_manifest_path is not None
        else artifact.with_name(REPRESENTATION_MANIFEST_FILENAME)
    )
    return artifact, manifest


def _representation_manifest_sha(manifest: Mapping[str, Any], artifact: Path) -> str:
    declared: object | None = manifest.get("artifact_sha256")
    artifacts = manifest.get("artifacts")
    if declared is None and isinstance(artifacts, Mapping):
        declared = artifacts.get(artifact.name)
    if not isinstance(declared, str) or len(declared) != 64:
        raise RuntimeError("Representation V2 manifest does not pin artifact SHA-256")
    digest = declared.lower()
    try:
        int(digest, 16)
    except ValueError as error:
        raise RuntimeError("Representation V2 artifact SHA-256 is invalid") from error
    actual = sha256_file(artifact)
    if actual != digest:
        raise RuntimeError("Representation V2 artifact SHA mismatch")
    return actual


def _assert_representation_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("outcome_blind") is not True:
        raise RuntimeError("Representation V2 manifest is not outcome-blind")
    forbidden_true = (
        "fresh_forward_accessed",
        "outcomes_or_labels_accessed",
        "outcome_metrics_computed",
        "model_fit",
        "model_scoring",
    )
    if any(manifest.get(key) is True for key in forbidden_true):
        raise RuntimeError("Representation V2 manifest records prohibited access")
    prohibited = manifest.get("prohibited_actions")
    if isinstance(prohibited, Mapping) and any(
        prohibited.get(key) is True
        for key in ("fresh_forward_accessed", "outcomes_or_labels_accessed", "model_fit", "model_scoring")
    ):
        raise RuntimeError("Representation V2 manifest records prohibited action")


def _calendar_contract(parent: Mapping[str, Any], session: str, flow_dates: pd.Series) -> dict[str, Any]:
    calendar_path_value = parent.get("calendar_path")
    calendar_sha = str(parent.get("calendar_sha256") or "").lower()
    if not calendar_path_value or len(calendar_sha) != 64:
        raise RuntimeError("official calendar provenance is required for setup causality")
    calendar_path = Path(str(calendar_path_value)).expanduser().resolve()
    if not calendar_path.exists() or sha256_file(calendar_path) != calendar_sha:
        raise RuntimeError("official calendar is missing or hash-mismatched")
    try:
        calendar = pd.read_csv(calendar_path)
    except Exception as error:
        raise RuntimeError("official calendar is unreadable") from error
    if "date" not in calendar.columns:
        raise RuntimeError("official calendar date column is missing")
    dates = pd.DatetimeIndex([_date(value) for value in calendar["date"]])
    if dates.has_duplicates or len(dates) == 0:
        raise RuntimeError("official calendar is empty or duplicated")
    target = _date(session)
    positions = {date: index for index, date in enumerate(dates)}
    if target not in positions:
        raise RuntimeError("setup feature session is not an official session")
    expected_flow = dates[positions[target] - 1] if positions[target] > 0 else None
    observed = pd.to_datetime(flow_dates, errors="coerce").map(_date)
    if expected_flow is None or observed.isna().any() or not observed.eq(expected_flow).all():
        raise RuntimeError("Representation V2 flow_through_session is not the prior official session")
    return {
        "path": str(calendar_path),
        "sha256": calendar_sha,
        "session_index": int(positions[target]),
        "flow_through_session": expected_flow.date().isoformat(),
    }


def _validate_representation(
    frame: pd.DataFrame,
    *,
    session: str,
    parent: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    unexpected = sorted(set(frame.columns) - set(OUTPUT_COLUMNS_V2))
    if unexpected:
        raise RuntimeError(f"Representation V2 contains non-contract columns: {unexpected}")
    missing = sorted(set(OUTPUT_COLUMNS_V2) - set(frame.columns))
    if missing:
        raise RuntimeError(f"Representation V2 is missing columns: {missing}")
    forbidden = [
        column
        for column in frame.columns
        if any(token in str(column).lower() for token in _FORBIDDEN_TOKENS)
    ]
    if forbidden:
        raise RuntimeError(f"Representation V2 contains prohibited columns: {sorted(forbidden)}")
    out = frame.loc[:, list(OUTPUT_COLUMNS_V2)].copy()
    out["ticker"] = out["ticker"].astype("string").str.upper().str.strip()
    if out["ticker"].isna().any() or out["ticker"].eq("").any():
        raise RuntimeError("Representation V2 has invalid ticker")
    for column in ("feature_session", "flow_through_session"):
        out[column] = pd.to_datetime(out[column], errors="coerce").map(_date)
        if out[column].isna().any():
            raise RuntimeError(f"Representation V2 has invalid {column}")
    target = _date(session)
    if not out["feature_session"].eq(target).all():
        raise RuntimeError("Representation V2 feature session does not match target session")
    if out.duplicated(["ticker", "feature_session"]).any() or out.duplicated(
        ["ticker", "feature_session", "flow_through_session"]
    ).any():
        raise RuntimeError("Representation V2 has duplicate session keys")
    for column in OUTPUT_COLUMNS_V2[3:]:
        values = pd.to_numeric(out[column], errors="coerce").astype(float)
        if np.isinf(values.to_numpy()).any():
            raise RuntimeError(f"Representation V2 contains infinity: {column}")
        out[column] = values
    calendar = _calendar_contract(parent, session, out["flow_through_session"])
    return out, calendar


def _same_frame(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    if list(left.columns) != list(right.columns) or len(left) != len(right):
        return False
    try:
        left = left.sort_values(["ticker", "feature_session"], kind="mergesort").reset_index(drop=True)
        right = right.sort_values(["ticker", "feature_session"], kind="mergesort").reset_index(drop=True)
        pd.testing.assert_frame_equal(left, right, check_dtype=False, check_exact=True)
    except (AssertionError, KeyError, TypeError):
        return False
    return True


def _manifest(
    *,
    context: Mapping[str, Any],
    representation_path: Path,
    representation_sha: str,
    representation_manifest_path: Path,
    representation_manifest_sha: str,
    sidecar_path: Path,
    sidecar_sha: str,
    frame: pd.DataFrame,
    calendar: Mapping[str, Any],
    thresholds: SetupThresholds,
) -> dict[str, Any]:
    return {
        "status": "FOREIGN_FLOW_SETUP_STATE_READY",
        "schema": "idx-trade/foreign-flow-setup-state-v1",
        "session_date": context["key"],
        "state_contract_version": "FOREIGN_FLOW_SETUP_STATE_V1",
        "source_representation_version": "FOREIGN_FLOW_REPRESENTATION_V2",
        "row_count": int(len(frame)),
        "indeterminate_rows": int(frame["setup_label"].eq("INDETERMINATE").sum()),
        "thresholds": dict(thresholds.__dict__),
        "setup_sidecar_path": str(sidecar_path),
        "setup_sidecar_sha256": sidecar_sha,
        "representation_path": str(representation_path),
        "representation_sha256": representation_sha,
        "representation_manifest_path": str(representation_manifest_path),
        "representation_manifest_sha256": representation_manifest_sha,
        "parent_session_manifest_path": str(context["parent_path"]),
        "parent_session_manifest_sha256": context["parent_sha"],
        "source_raw_path": str(context["raw_path"]),
        "source_raw_sha256": context["raw_sha"],
        "calendar": dict(calendar),
        "observed_available_at_utc": context["observed_available_at_utc"],
        "publication_time_known": False,
        "provider_calls": 0,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
    }


def enrich_session_foreign_flow_setup(
    runtime_root: str | Path,
    session_date: str | pd.Timestamp,
    *,
    representation_path: str | Path | None = None,
    representation_manifest_path: str | Path | None = None,
    thresholds: SetupThresholds = DEFAULT_THRESHOLDS,
) -> dict[str, Any]:
    """Create or verify Setup State for one existing valid V2 representation.

    Missing V2 representation is an explicit ``FileNotFoundError``.  It is not
    synthesized from the raw one-session Stock Summary sidecar.
    """
    root = Path(runtime_root).expanduser().resolve()
    key = _date(session_date).date().isoformat()
    context = _canonical_evidence(root, key)
    directory = context["directory"]
    representation, representation_manifest_path = _representation_paths(
        directory, representation_path, representation_manifest_path
    )
    if not representation.exists() or not representation_manifest_path.exists():
        raise FileNotFoundError("Foreign Flow Representation V2 artifact/manifest is missing")
    manifest = _read_json(representation_manifest_path, label="Representation V2 manifest")
    _assert_representation_manifest(manifest)
    representation_sha = _representation_manifest_sha(manifest, representation)
    try:
        source_frame = pd.read_parquet(representation)
    except Exception as error:
        raise RuntimeError("Representation V2 artifact is unreadable") from error
    source_frame, calendar = _validate_representation(
        source_frame, session=key, parent=context["parent"]
    )
    setup_frame = build_foreign_flow_setup_sidecar(source_frame, thresholds=thresholds)
    sidecar = directory / SETUP_SIDECAR_FILENAME
    manifest_path = directory / SETUP_MANIFEST_FILENAME
    if sidecar.exists():
        try:
            existing = pd.read_parquet(sidecar)
        except Exception as error:
            raise RuntimeError("existing setup sidecar is unreadable") from error
        if not _same_frame(existing, setup_frame):
            raise RuntimeError("immutable setup sidecar revision conflict")
    else:
        _write_parquet_exclusive(setup_frame, sidecar)
    sidecar_sha = sha256_file(sidecar)
    expected = _manifest(
        context=context,
        representation_path=representation,
        representation_sha=representation_sha,
        representation_manifest_path=representation_manifest_path,
        representation_manifest_sha=sha256_file(representation_manifest_path),
        sidecar_path=sidecar,
        sidecar_sha=sidecar_sha,
        frame=setup_frame,
        calendar=calendar,
        thresholds=thresholds,
    )
    if manifest_path.exists():
        if _read_json(manifest_path, label="setup-state manifest") != expected:
            raise RuntimeError("immutable setup-state manifest revision conflict")
    else:
        manifest_path.write_text(
            json.dumps(expected, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if not verify_session_foreign_flow_setup(
        root,
        key,
        representation_path=representation,
        representation_manifest_path=representation_manifest_path,
        thresholds=thresholds,
    ):
        raise RuntimeError("new setup-state sidecar failed canonical verification")
    return {
        "status": "FOREIGN_FLOW_SETUP_STATE_READY",
        "session_date": key,
        "rows": int(len(setup_frame)),
        "indeterminate_rows": int(expected["indeterminate_rows"]),
        "setup_sidecar_path": str(sidecar),
        "setup_sidecar_sha256": sidecar_sha,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "representation_path": str(representation),
        "representation_sha256": representation_sha,
        "representation_manifest_sha256": sha256_file(representation_manifest_path),
        "provider_calls": 0,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
    }


def verify_session_foreign_flow_setup(
    runtime_root: str | Path,
    session_date: str | pd.Timestamp,
    *,
    representation_path: str | Path | None = None,
    representation_manifest_path: str | Path | None = None,
    thresholds: SetupThresholds = DEFAULT_THRESHOLDS,
) -> bool:
    root = Path(runtime_root).expanduser().resolve()
    key = _date(session_date).date().isoformat()
    try:
        context = _canonical_evidence(root, key)
        representation, rep_manifest_path = _representation_paths(
            context["directory"], representation_path, representation_manifest_path
        )
        setup_path = context["directory"] / SETUP_SIDECAR_FILENAME
        setup_manifest_path = context["directory"] / SETUP_MANIFEST_FILENAME
        if not setup_path.exists() or not setup_manifest_path.exists():
            return False
        rep_manifest = _read_json(rep_manifest_path, label="Representation V2 manifest")
        _assert_representation_manifest(rep_manifest)
        rep_sha = _representation_manifest_sha(rep_manifest, representation)
        source_frame = pd.read_parquet(representation)
        source_frame, calendar = _validate_representation(
            source_frame, session=key, parent=context["parent"]
        )
        expected_frame = build_foreign_flow_setup_sidecar(source_frame, thresholds=thresholds)
        stored = pd.read_parquet(setup_path)
        if not _same_frame(stored, expected_frame):
            return False
        expected = _manifest(
            context=context,
            representation_path=representation,
            representation_sha=rep_sha,
            representation_manifest_path=rep_manifest_path,
            representation_manifest_sha=sha256_file(rep_manifest_path),
            sidecar_path=setup_path,
            sidecar_sha=sha256_file(setup_path),
            frame=expected_frame,
            calendar=calendar,
            thresholds=thresholds,
        )
        return _read_json(setup_manifest_path, label="setup-state manifest") == expected
    except (KeyError, OSError, RuntimeError, ValueError, TypeError, ImportError):
        return False


def inspect_session_foreign_flow_setup(
    runtime_root: str | Path, session_date: str | pd.Timestamp
) -> dict[str, Any]:
    root = Path(runtime_root).expanduser().resolve()
    key = _date(session_date).date().isoformat()
    directory = root / "forward_monitoring" / "sessions" / key
    manifest_path = directory / SETUP_MANIFEST_FILENAME
    if not verify_session_foreign_flow_setup(root, key):
        raise RuntimeError("setup-state sidecar is not canonically verified")
    return _read_json(manifest_path, label="setup-state manifest")
