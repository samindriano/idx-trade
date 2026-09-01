"""Read-only adapters for the IDX-Trade quant showcase notebook.

This module is deliberately a presentation-layer adapter.  It reads immutable
historical OOS exports or outcome-blind forward monitoring artifacts and never
calls a provider, writes a source artifact, or mutates PaperState.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

import pandas as pd


HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
FORWARD_LIVE = "FORWARD_LIVE"
FORWARD_MATURED = "FORWARD_MATURED"
VALID_MODES = {HISTORICAL_REPLAY, FORWARD_LIVE, FORWARD_MATURED}

_FORBIDDEN_COMPONENT = re.compile(
    r"(?i)(outcome|vault|protected|realized|return|label)"
)
_SHOWCASE_CSVS = (
    "sessions.csv",
    "scores.csv",
    "decisions.csv",
    "orders.csv",
    "fills.csv",
    "positions.csv",
    "nav.csv",
    "execution.csv",
    "benchmark.csv",
)


class ShowcaseDataError(RuntimeError):
    """Raised when an adapter would otherwise produce misleading output."""


@dataclass
class ShowcaseBundle:
    mode: str
    status: str
    message: str
    root: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    integrity: dict[str, Any] = field(default_factory=dict)
    sessions: pd.DataFrame = field(default_factory=pd.DataFrame)
    scores: pd.DataFrame = field(default_factory=pd.DataFrame)
    decisions: pd.DataFrame = field(default_factory=pd.DataFrame)
    orders: pd.DataFrame = field(default_factory=pd.DataFrame)
    fills: pd.DataFrame = field(default_factory=pd.DataFrame)
    positions: pd.DataFrame = field(default_factory=pd.DataFrame)
    nav: pd.DataFrame = field(default_factory=pd.DataFrame)
    execution: pd.DataFrame = field(default_factory=pd.DataFrame)
    benchmark: pd.DataFrame = field(default_factory=pd.DataFrame)
    alpha_outcomes: pd.DataFrame = field(default_factory=pd.DataFrame)
    field_status: pd.DataFrame = field(default_factory=pd.DataFrame)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.status == "READY"


def _empty_fields(rows: Iterable[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Field", "Status", "Evidence"])


def _empty_bundle(
    mode: str,
    status: str,
    message: str,
    *,
    root: Path | None = None,
    fields: Iterable[tuple[str, str, str]] = (),
) -> ShowcaseBundle:
    return ShowcaseBundle(
        mode=mode,
        status=status,
        message=message,
        root=root,
        field_status=_empty_fields(fields),
    )


def _reject_unsafe_path(path: Path) -> None:
    if any(_FORBIDDEN_COMPONENT.search(part) for part in path.parts):
        raise ShowcaseDataError(
            f"Refusing a protected/outcome-bearing path in showcase adapter: {path}"
        )


def _sha256(path: Path) -> str:
    _reject_unsafe_path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_record(path: Path, role: str, *, rows: int | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise ShowcaseDataError(f"Required showcase artifact is missing: {path}")
    result: dict[str, Any] = {
        "role": role,
        "path": str(path),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }
    if rows is not None:
        result["rows"] = int(rows)
    return result


def _read_json(path: Path) -> dict[str, Any]:
    _reject_unsafe_path(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ShowcaseDataError(f"Cannot read JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ShowcaseDataError(f"Expected JSON object in {path}")
    return value


def _read_csv(path: Path) -> pd.DataFrame:
    _reject_unsafe_path(path)
    try:
        return pd.read_csv(path)
    except (OSError, ValueError) as exc:
        raise ShowcaseDataError(f"Cannot read CSV artifact {path}: {exc}") from exc


def _normalize_dates(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    if frame.empty or column not in frame.columns:
        return frame
    out = frame.copy()
    out[column] = pd.to_datetime(out[column], errors="raise").dt.normalize()
    return out


def _rank_scores(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"session_date", "ticker", "alpha_consensus"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ShowcaseDataError(f"Score artifact is missing columns: {missing}")
    out = frame.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["alpha_consensus"] = pd.to_numeric(out["alpha_consensus"], errors="raise")
    out = out.sort_values(
        ["session_date", "alpha_consensus", "ticker"],
        ascending=[True, False, True],
        kind="mergesort",
    )
    out["rank"] = out.groupby("session_date", sort=False).cumcount() + 1
    return out.reset_index(drop=True)


def _historical_fields() -> list[tuple[str, str, str]]:
    return [
        ("historical alpha", "AVAILABLE", "Authorized clean historical OOS score/target export"),
        ("historical executable portfolio", "BLOCKED", "CA negative/no-event authority is not proven"),
        ("historical fills/positions/NAV", "NOT_APPLICABLE", "Execution replay is intentionally not attempted"),
        ("forward realized outcomes", "BLOCKED", "Protected prospective outcomes remain locked"),
        ("PaperState mutation", "NOT_APPLICABLE", "Notebook is read-only"),
        ("provider calls", "NOT_APPLICABLE", "Adapter performs local reads only"),
    ]


def load_historical_oos(root: Path) -> ShowcaseBundle:
    """Adapt the accepted clean historical OOS export into alpha-only frames."""

    root = root.expanduser()
    required = {
        "scores": root / "clean_challenger_validation_scores.parquet",
        "targets": root / "clean_target_ledger.parquet",
        "access_boundary": root / "HISTORICAL_OOS_ACCESS_BOUNDARY.json",
        "manifest": root / "MANIFEST.json",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        return _empty_bundle(
            HISTORICAL_REPLAY,
            "UNAVAILABLE",
            "Historical OOS root is incomplete; no alpha metrics were loaded.",
            root=root,
            fields=_historical_fields(),
        )

    for path in required.values():
        _reject_unsafe_path(path)
    try:
        score_frame = pd.read_parquet(required["scores"])
        target_frame = pd.read_parquet(required["targets"])
    except (OSError, ValueError, ImportError) as exc:
        raise ShowcaseDataError(f"Cannot read clean historical OOS parquet: {exc}") from exc

    boundary = _read_json(required["access_boundary"])
    manifest = _read_json(required["manifest"])
    score_frame = _normalize_dates(score_frame, "date")
    target_frame = _normalize_dates(target_frame, "date")
    score_frame = score_frame.rename(columns={"date": "session_date"})
    target_frame = target_frame.rename(columns={"date": "session_date"})

    target_columns = ["ticker", "session_date", "realized_consensus", "target_state_consensus"]
    missing_target = sorted(set(target_columns) - set(target_frame.columns))
    if missing_target:
        raise ShowcaseDataError(f"Historical target ledger is missing columns: {missing_target}")

    ranked_scores = _rank_scores(score_frame)
    joined = ranked_scores.merge(
        target_frame[target_columns],
        on=["ticker", "session_date"],
        how="left",
        validate="one_to_one",
    )
    valid = joined.loc[
        joined["target_state_consensus"].eq("TARGET_BOTH_AVAILABLE")
        & pd.to_numeric(joined["realized_consensus"], errors="coerce").notna(),
        ["ticker", "session_date", "alpha_consensus", "realized_consensus", "rank"],
    ].copy()
    valid = valid.rename(columns={"realized_consensus": "canonical_target"})
    valid["canonical_target"] = pd.to_numeric(valid["canonical_target"], errors="raise")

    session_rows = (
        joined.groupby("session_date", sort=True)
        .agg(
            score_rows=("ticker", "size"),
            valid_alpha_rows=("realized_consensus", lambda values: int(values.notna().sum())),
        )
        .reset_index()
    )
    session_rows["state"] = "ALPHA_AUTHORIZED_OOS"
    session_rows["execution_authority"] = "BLOCKED_CA_NEGATIVE_AUTHORITY"

    sources = [
        _source_record(required["scores"], "clean historical challenger scores", rows=len(score_frame)),
        _source_record(required["targets"], "clean target ledger", rows=len(target_frame)),
        _source_record(required["access_boundary"], "historical OOS access boundary"),
        _source_record(required["manifest"], "historical OOS manifest"),
    ]
    metadata = {
        "mode": HISTORICAL_REPLAY,
        "status": "HISTORICAL_ALPHA_AUTHORIZED_EXECUTION_BLOCKED",
        "historical_alpha_authorized": True,
        "historical_execution_authority": False,
        "actual_live_historical_portfolio": False,
        "session_count": int(len(session_rows)),
        "score_rows": int(len(score_frame)),
        "valid_alpha_rows": int(len(valid)),
        "target_filter": "target_state_consensus == TARGET_BOTH_AVAILABLE and finite realized_consensus",
        "generation_id": manifest.get("generation_id"),
        "measurement_only": bool(manifest.get("measurement_only", boundary.get("measurement_only", False))),
        "forward_outcomes_accessed": bool(manifest.get("forward_outcomes_accessed", False)),
        "source_files": sources,
    }
    integrity = {
        "model_frozen": "Historical score export is consumed; no fit or retune performed",
        "feature_contract": "Clean V4-X1 historical OOS export",
        "historical_oos_authority": boundary.get("status", "UNKNOWN"),
        "historical_execution_authority": "BLOCKED_CA_NEGATIVE_AUTHORITY",
        "target_contract": "Unresolved target states are excluded, never treated as realized outcomes",
        "forward_outcome_access": "LOCKED / NOT ACCESSED",
        "paperstate_mutation": False,
        "provider_calls": False,
        "synthetic_evidence": False,
        "source_hashes": {item["role"]: item["sha256"] for item in sources},
    }
    provenance = {
        "source_files": sources,
        "excluded_target_states": sorted(
            set(target_frame["target_state_consensus"].dropna().astype(str))
            - {"TARGET_BOTH_AVAILABLE"}
        ),
        "execution_blocker": {
            "decision_session": "2023-12-28",
            "execution_session": "2023-12-29",
            "verdict": "FIRST_HISTORICAL_E2E_SESSION_BLOCKED_BY_CA_NEGATIVE_AUTHORITY",
        },
    }
    return ShowcaseBundle(
        mode=HISTORICAL_REPLAY,
        status="READY",
        message="Authorized historical alpha loaded; executable portfolio intentionally unavailable.",
        root=root,
        metadata=metadata,
        integrity=integrity,
        sessions=session_rows,
        scores=joined,
        alpha_outcomes=valid,
        field_status=_empty_fields(_historical_fields()),
        provenance=provenance,
    )


def _forward_fields() -> list[tuple[str, str, str]]:
    return [
        ("session progress", "AVAILABLE", "Outcome-blind session manifests"),
        ("model fingerprint / frozen IDs", "AVAILABLE", "Canonical V4-X1 score manifest"),
        ("score status", "AVAILABLE", "Canonical forward score artifacts"),
        ("Decision outputs", "UNAVAILABLE", "No canonical Decision artifact found"),
        ("target positions", "UNAVAILABLE", "No canonical target-position artifact found"),
        ("prepared orders", "UNAVAILABLE", "No canonical prepared-order artifact found"),
        ("fills / executions", "UNAVAILABLE", "No canonical fill/execution artifact found"),
        ("holdings / cash / PaperState NAV", "UNAVAILABLE", "No canonical PaperState artifact found"),
        ("exposure / pending / turnover / costs", "UNAVAILABLE", "No canonical portfolio summary found"),
        ("integrity / admission", "AVAILABLE", "Session, model, and EOD manifests"),
        ("CA evidence / attestation", "UNAVAILABLE", "No CA artifact in selected forward monitoring root"),
        ("input basis / capture provenance", "AVAILABLE", "Session manifest and official source metadata"),
        ("forward realized outcomes", "BLOCKED", "Outcome access is locked by the canonical runtime"),
        ("PaperState mutation", "NOT_APPLICABLE", "Notebook performs local reads only"),
        ("provider calls", "NOT_APPLICABLE", "Adapter performs local reads only"),
    ]


def _safe_optional_json(path: Path, role: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = _read_json(path)
    sources.append(_source_record(path, role))
    return value


def load_forward_live(root: Path) -> ShowcaseBundle:
    """Read current outcome-blind forward monitoring artifacts only."""

    root = root.expanduser()
    fields = _forward_fields()
    if not root.is_dir():
        return _empty_bundle(
            FORWARD_LIVE,
            "UNAVAILABLE",
            "Set IDX_TRADE_FORWARD_ROOT to the canonical outcome-blind forward monitoring root.",
            root=root,
            fields=fields,
        )
    _reject_unsafe_path(root)

    sessions_root = root / "sessions"
    model_root = root / "model_runs"
    if not sessions_root.is_dir():
        return _empty_bundle(
            FORWARD_LIVE,
            "UNAVAILABLE",
            "Canonical forward monitoring root has no sessions directory.",
            root=root,
            fields=fields,
        )

    sources: list[dict[str, Any]] = []
    session_rows: list[dict[str, Any]] = []
    session_manifests: list[tuple[pd.Timestamp, dict[str, Any]]] = []
    for session_dir in sorted((p for p in sessions_root.iterdir() if p.is_dir()), key=lambda p: p.name):
        manifest_path = session_dir / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = _read_json(manifest_path)
        session_date = pd.to_datetime(manifest.get("session_date", session_dir.name), errors="raise").normalize()
        session_manifests.append((session_date, manifest))
        sources.append(_source_record(manifest_path, "forward session manifest"))
        session_rows.append(
            {
                "session_date": session_date,
                "state": manifest.get("status", "UNKNOWN"),
                "model_input_rows": manifest.get("model_input_rows"),
                "point_evidence_rows": manifest.get("point_evidence_rows"),
                "open_coverage_status": manifest.get("open_coverage_status"),
                "outcome_blind": manifest.get("outcome_blind"),
                "forward_outcomes_accessed": manifest.get("forward_outcomes_accessed"),
                "captured_at_utc": manifest.get("captured_at_utc"),
                "manifest_path": str(manifest_path),
                "manifest_sha256": _sha256(manifest_path),
            }
        )
    if not session_rows:
        return _empty_bundle(
            FORWARD_LIVE,
            "UNAVAILABLE",
            "No canonical forward session manifest was found.",
            root=root,
            fields=fields,
        )

    sessions = pd.DataFrame(session_rows).sort_values("session_date").reset_index(drop=True)
    latest_session_date, latest_session_manifest = sorted(session_manifests, key=lambda item: item[0])[-1]

    scores: list[pd.DataFrame] = []
    latest_model_manifest: dict[str, Any] = {}
    latest_model_date: pd.Timestamp | None = None
    if model_root.is_dir():
        for date_dir in sorted((p for p in model_root.iterdir() if p.is_dir()), key=lambda p: p.name):
            candidate = date_dir / "v4_x1_clean_geometry3_prospective_v1"
            artifact_path = candidate / "score_artifact.parquet"
            manifest_path = candidate / "manifest.json"
            if not artifact_path.is_file() or not manifest_path.is_file():
                continue
            model_manifest = _read_json(manifest_path)
            frame = pd.read_parquet(artifact_path)
            frame = _normalize_dates(frame, "date").rename(columns={"date": "session_date"})
            if "alpha_consensus" not in frame.columns or "ticker" not in frame.columns:
                continue
            frame["score_status"] = model_manifest.get("status", "UNKNOWN")
            frame["model_fingerprint"] = model_manifest.get("model_fingerprint")
            scores.append(frame)
            sources.append(_source_record(artifact_path, "forward V4-X1 score artifact", rows=len(frame)))
            sources.append(_source_record(manifest_path, "forward V4-X1 score manifest"))
            model_date = pd.to_datetime(model_manifest.get("session_date", date_dir.name), errors="raise").normalize()
            if latest_model_date is None or model_date >= latest_model_date:
                latest_model_date = model_date
                latest_model_manifest = model_manifest

    score_frame = pd.concat(scores, ignore_index=True) if scores else pd.DataFrame()
    if not score_frame.empty:
        score_frame = _rank_scores(score_frame)
        if "rank_consensus" in score_frame.columns:
            score_frame["rank"] = pd.to_numeric(score_frame["rank_consensus"], errors="coerce")

    eod_latest = _safe_optional_json(root / "eod_automation" / "latest.json", "forward EOD latest status", sources)
    x1_latest = _safe_optional_json(
        root / "eod_automation" / "v4_x1_pipeline" / "latest.json",
        "forward V4-X1 pipeline latest status",
        sources,
    )

    metadata = {
        "mode": FORWARD_LIVE,
        "status": "OUTCOME_BLIND_CANONICAL_FORWARD_OBSERVATION",
        "latest_session": latest_session_date.date().isoformat(),
        "session_count": int(len(sessions)),
        "score_sessions": int(score_frame["session_date"].nunique()) if not score_frame.empty else 0,
        "model_id": latest_model_manifest.get("model_id", "UNAVAILABLE"),
        "model_generation": latest_model_manifest.get("generation", "UNAVAILABLE"),
        "model_fingerprint": latest_model_manifest.get("model_fingerprint", "UNAVAILABLE"),
        "model_status": latest_model_manifest.get("status", "UNAVAILABLE"),
        "implementation_commit": "UNAVAILABLE_IN_FORWARD_ARTIFACT",
        "outcome_access": eod_latest.get("outcome_access", "LOCKED"),
        "forward_outcomes_accessed": bool(
            latest_session_manifest.get("forward_outcomes_accessed", False)
            or x1_latest.get("protected_outcome_accessed", False)
        ),
        "provider_calls_from_x1": bool(x1_latest.get("provider_calls_from_x1", False)),
        "source_files": sources,
    }
    integrity = {
        "model_frozen": {
            "model_id": metadata["model_id"],
            "model_fingerprint": metadata["model_fingerprint"],
            "frozen_scientific_git_blobs": latest_model_manifest.get("science", {}).get(
                "frozen_scientific_git_blobs", "UNAVAILABLE"
            ),
        },
        "score_status": metadata["model_status"],
        "forward_outcome_access": "LOCKED / NOT READ",
        "forward_outcomes_accessed": metadata["forward_outcomes_accessed"],
        "paper_portfolio": "UNAVAILABLE_CANONICAL_ARTIFACT_NOT_FOUND",
        "ca_input_basis": "CA_UNAVAILABLE; input capture provenance available",
        "paperstate_mutation": False,
        "provider_calls": False,
        "synthetic_evidence": False,
        "source_hashes": {item["role"] + " @ " + item["path"]: item["sha256"] for item in sources},
        "eod_status": eod_latest.get("status", "UNAVAILABLE"),
        "x1_pipeline_status": x1_latest.get("status", "UNAVAILABLE"),
    }
    provenance = {
        "source_files": sources,
        "selection": {
            "sessions": "sessions/*/manifest.json only",
            "scores": "model_runs/*/v4_x1_clean_geometry3_prospective_v1/{manifest,score_artifact}",
            "status": "eod_automation/latest.json and eod_automation/v4_x1_pipeline/latest.json",
            "outcome_files_read": False,
        },
        "latest_session_manifest": latest_session_manifest,
    }
    return ShowcaseBundle(
        mode=FORWARD_LIVE,
        status="READY",
        message="Outcome-blind forward monitoring artifacts loaded; portfolio/evaluation outputs remain unavailable.",
        root=root,
        metadata=metadata,
        integrity=integrity,
        sessions=sessions,
        scores=score_frame,
        field_status=_empty_fields(fields),
        provenance=provenance,
    )


def _load_flat_bundle(root: Path, mode: str) -> ShowcaseBundle:
    """Load an explicitly prepared bundle after mode-specific guards."""

    root = root.expanduser()
    _reject_unsafe_path(root)
    metadata_path = root / "metadata.json"
    integrity_path = root / "integrity.json"
    if not metadata_path.is_file() or not integrity_path.is_file():
        return _empty_bundle(mode, "UNAVAILABLE", "Prepared bundle metadata/integrity is missing.", root=root)
    if mode == FORWARD_LIVE and (root / "alpha_outcomes.csv").exists():
        return _empty_bundle(
            mode,
            "BLOCKED",
            "FORWARD_LIVE refuses a bundle containing alpha_outcomes.csv.",
            root=root,
            fields=_forward_fields(),
        )

    sources = [
        _source_record(metadata_path, "showcase metadata"),
        _source_record(integrity_path, "showcase integrity"),
    ]
    frames: dict[str, pd.DataFrame] = {}
    for name in _SHOWCASE_CSVS:
        path = root / name
        if path.is_file():
            frames[name[:-4]] = _normalize_dates(_read_csv(path), "session_date")
            sources.append(_source_record(path, f"showcase {name[:-4]}", rows=len(frames[name[:-4]])))
        else:
            frames[name[:-4]] = pd.DataFrame()
    metadata = _read_json(metadata_path)
    integrity = _read_json(integrity_path)
    if mode == FORWARD_MATURED:
        alpha_path = root / "alpha_outcomes.csv"
        if not alpha_path.is_file() or metadata.get("matured_access_granted") is not True:
            return _empty_bundle(
                mode,
                "BLOCKED",
                "FORWARD_MATURED requires an explicitly authorized matured export.",
                root=root,
                fields=[("matured evaluation", "BLOCKED", "Explicit matured authorization is absent")],
            )
        frames["alpha_outcomes"] = _normalize_dates(_read_csv(alpha_path), "session_date")
        sources.append(_source_record(alpha_path, "authorized matured alpha outcomes", rows=len(frames["alpha_outcomes"])) )
    else:
        frames["alpha_outcomes"] = pd.DataFrame()
    return ShowcaseBundle(
        mode=mode,
        status="READY",
        message="Prepared showcase bundle loaded.",
        root=root,
        metadata=metadata,
        integrity=integrity,
        sessions=frames["sessions"],
        scores=frames["scores"],
        decisions=frames["decisions"],
        orders=frames["orders"],
        fills=frames["fills"],
        positions=frames["positions"],
        nav=frames["nav"],
        execution=frames["execution"],
        benchmark=frames["benchmark"],
        alpha_outcomes=frames["alpha_outcomes"],
        field_status=_empty_fields(_forward_fields() if mode == FORWARD_LIVE else _historical_fields()),
        provenance={"source_files": sources},
    )


def load_mode_artifacts(
    mode: str,
    *,
    historical_root: str | Path | None = None,
    forward_root: str | Path | None = None,
    matured_root: str | Path | None = None,
    showcase_root: str | Path | None = None,
) -> ShowcaseBundle:
    """Load exactly one mode without crossing its evidence boundary."""

    mode = str(mode).strip().upper()
    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of {sorted(VALID_MODES)}, got {mode!r}")

    if mode == HISTORICAL_REPLAY:
        root_value = historical_root or showcase_root
        if not root_value:
            return _empty_bundle(
                mode,
                "UNAVAILABLE",
                "Set IDX_TRADE_HISTORICAL_OOS_ROOT to the authorized clean OOS export.",
                fields=_historical_fields(),
            )
        return load_historical_oos(Path(root_value))

    if mode == FORWARD_LIVE:
        root_value = forward_root or showcase_root
        if not root_value:
            return _empty_bundle(
                mode,
                "UNAVAILABLE",
                "Set IDX_TRADE_FORWARD_ROOT to the canonical outcome-blind forward monitoring root.",
                fields=_forward_fields(),
            )
        root = Path(root_value)
        if (root / "sessions").is_dir():
            return load_forward_live(root)
        return _load_flat_bundle(root, mode)

    if not matured_root:
        return _empty_bundle(
            mode,
            "BLOCKED",
            "FORWARD_MATURED DATA NOT AVAILABLE. A separate authorized matured export is required.",
            fields=[("matured evaluation", "BLOCKED", "No explicit authorized export was supplied")],
        )
    root = Path(matured_root)
    return _load_flat_bundle(root, mode)


def provenance_frame(bundle: ShowcaseBundle) -> pd.DataFrame:
    """Return a compact, display-ready source provenance table."""

    rows = bundle.provenance.get("source_files", [])
    if not rows:
        return pd.DataFrame(columns=["role", "path", "sha256", "rows", "size_bytes"])
    display_rows = []
    root = bundle.root.resolve() if bundle.root is not None else None
    for source in rows:
        display_source = dict(source)
        source_path = Path(str(source["path"]))
        if root is not None:
            try:
                relative = source_path.resolve().relative_to(root)
                display_source["path"] = f"<configured-root>/{relative.as_posix()}"
            except ValueError:
                display_source["path"] = f"<configured-root>/{source_path.name}"
        else:
            display_source["path"] = f"<configured-root>/{source_path.name}"
        display_rows.append(display_source)
    return pd.DataFrame(display_rows)
