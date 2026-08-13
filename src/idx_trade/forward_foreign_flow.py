from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .provenance import sha256_file, write_manifest_atomic
from .security_master import normalise_ticker
from .storage import write_parquet_atomic


SCHEMA_VERSION = 1
CODE_PATTERN = r"[A-Z0-9]{4,5}"
COLUMNS = (
    "security_code", "session_date", "unit", "foreign_buy", "foreign_sell",
    "foreign_net", "knowledge_at_utc", "source", "source_ref", "source_sha256",
)


def _nonnegative(value: object, *, field: str, code: str) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed) or float(parsed) < 0:
        raise ValueError(f"{field} missing/invalid for {code}")
    return float(parsed)


def parse_stock_summary_foreign_flow(
    payload: Mapping[str, object], *, session_date: str | pd.Timestamp,
    knowledge_at_utc: str | pd.Timestamp, source_ref: str, source_sha256: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Normalize official Stock Summary ForeignBuy/ForeignSell as SHARES.

    Capture time is an upper bound on knowledge time, not a publication timestamp.
    All official 4/5-character security codes are archived; common-share filtering is
    intentionally deferred to later research contracts.
    """
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Stock Summary foreign-flow source has no rows")
    try:
        total = int(payload.get("recordsTotal"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Stock Summary recordsTotal missing/invalid") from exc
    if total != len(rows) or total <= 0:
        raise ValueError(f"Stock Summary completeness mismatch rows={len(rows)} total={total}")
    filtered = payload.get("recordsFiltered")
    if filtered is not None and int(filtered) != total:
        raise ValueError("Stock Summary foreign-flow source is filtered/partial")

    session = pd.Timestamp(session_date).normalize()
    knowledge = pd.Timestamp(knowledge_at_utc)
    if knowledge.tzinfo is None:
        raise ValueError("knowledge_at_utc must be timezone-aware")
    knowledge = knowledge.tz_convert("UTC")
    if knowledge.tz_convert("Asia/Jakarta").tz_localize(None).normalize() < session:
        raise ValueError("foreign-flow knowledge time precedes session")
    digest = str(source_sha256).strip().lower()
    if len(digest) != 64:
        raise ValueError("source_sha256 must be SHA-256")
    try:
        int(digest, 16)
    except ValueError as exc:
        raise ValueError("source_sha256 must be hexadecimal") from exc
    if not str(source_ref).strip():
        raise ValueError("source_ref is empty")

    out: list[dict[str, object]] = []
    seen: set[str] = set()
    zeros = 0
    for position, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise ValueError(f"Stock Summary row {position} is not an object")
        code = normalise_ticker(raw.get("StockCode", ""))
        if not code or not pd.Series([code]).str.fullmatch(CODE_PATTERN).iloc[0]:
            raise ValueError(f"invalid StockCode at row {position}")
        if code in seen:
            raise ValueError(f"duplicate StockCode {code}")
        seen.add(code)
        day = pd.to_datetime(raw.get("Date"), errors="coerce")
        if pd.isna(day) or pd.Timestamp(day).tz_localize(None).normalize() != session:
            raise ValueError(f"Stock Summary date mismatch for {code}")
        if "ForeignBuy" not in raw or "ForeignSell" not in raw:
            raise ValueError(f"ForeignBuy/ForeignSell absent for {code}")
        buy = _nonnegative(raw.get("ForeignBuy"), field="ForeignBuy", code=code)
        sell = _nonnegative(raw.get("ForeignSell"), field="ForeignSell", code=code)
        zeros += int(buy == 0 and sell == 0)
        out.append({
            "security_code": code, "session_date": session, "unit": "SHARES",
            "foreign_buy": buy, "foreign_sell": sell, "foreign_net": buy - sell,
            "knowledge_at_utc": knowledge, "source": "IDX_OFFICIAL_STOCK_SUMMARY",
            "source_ref": str(source_ref), "source_sha256": digest,
        })
    frame = pd.DataFrame(out, columns=COLUMNS).sort_values("security_code").reset_index(drop=True)
    meta = {
        "schema_version": SCHEMA_VERSION, "unit": "SHARES", "rows": len(frame),
        "security_codes": int(frame["security_code"].nunique()),
        "four_character_codes": int(frame["security_code"].str.len().eq(4).sum()),
        "five_character_codes": int(frame["security_code"].str.len().eq(5).sum()),
        "zero_flow_rows": zeros, "publication_time_known": False,
        "knowledge_time_semantics": "CAPTURE_TIME_UPPER_BOUND_NOT_FIRST_KNOWABLE",
        "common_share_filter_applied": False,
    }
    return frame, meta


def _same(existing: pd.DataFrame, incoming: pd.DataFrame) -> bool:
    if list(existing.columns) != list(incoming.columns) or len(existing) != len(incoming):
        return False
    left, right = existing.copy(), incoming.copy()
    left["session_date"] = pd.to_datetime(left["session_date"]).dt.normalize()
    right["session_date"] = pd.to_datetime(right["session_date"]).dt.normalize()
    left["knowledge_at_utc"] = pd.to_datetime(left["knowledge_at_utc"], utc=True)
    right["knowledge_at_utc"] = pd.to_datetime(right["knowledge_at_utc"], utc=True)
    return left.reset_index(drop=True).equals(right.reset_index(drop=True))


def enrich_session_foreign_flow(runtime_root: str | Path, session_date: str | pd.Timestamp) -> dict[str, Any]:
    """Build/verify an outcome-blind sidecar from already-captured official bytes only."""
    root = Path(runtime_root).expanduser().resolve()
    key = pd.Timestamp(session_date).normalize().date().isoformat()
    directory = root / "forward_monitoring" / "sessions" / key
    parent_path = directory / "manifest.json"
    raw_path = directory / "idx_stock_summary.raw.json"
    if not parent_path.exists() or not raw_path.exists():
        raise FileNotFoundError(f"canonical Stock Summary evidence missing for {key}")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    if parent.get("session_date") != key:
        raise RuntimeError("canonical manifest session mismatch")
    if parent.get("outcome_blind") is not True or parent.get("forward_outcomes_accessed") is not False:
        raise RuntimeError("canonical session is not outcome-blind")
    raw_sha = sha256_file(raw_path)
    if parent.get("stock_summary_raw_sha256") != raw_sha:
        raise RuntimeError("Stock Summary raw SHA mismatch")
    source = parent.get("stock_summary_source")
    if not isinstance(source, Mapping) or not source.get("observed_available_at_utc") or not source.get("source_ref"):
        raise RuntimeError("Stock Summary capture metadata missing")
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise RuntimeError("Stock Summary raw payload is not an object")
    frame, meta = parse_stock_summary_foreign_flow(
        payload, session_date=key, knowledge_at_utc=source["observed_available_at_utc"],
        source_ref=str(source["source_ref"]), source_sha256=raw_sha,
    )

    sidecar = directory / "idx_foreign_flow.parquet"
    if sidecar.exists():
        if not _same(pd.read_parquet(sidecar), frame):
            raise RuntimeError("immutable foreign-flow sidecar revision conflict")
    else:
        write_parquet_atomic(frame, sidecar)
    sidecar_sha = sha256_file(sidecar)
    manifest_path = directory / "idx_foreign_flow.manifest.json"
    manifest = {
        **meta, "status": "FOREIGN_FLOW_READY", "session_date": key,
        "outcome_blind": True, "forward_outcomes_accessed": False,
        "sidecar_path": str(sidecar), "sidecar_sha256": sidecar_sha,
        "parent_session_manifest_path": str(parent_path),
        "parent_session_manifest_sha256": sha256_file(parent_path),
        "source_raw_path": str(raw_path), "source_raw_sha256": raw_sha,
        "source_endpoint": source.get("endpoint"), "source_ref": str(source["source_ref"]),
        "observed_available_at_utc": str(source["observed_available_at_utc"]),
    }
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old != manifest:
            raise RuntimeError("immutable foreign-flow manifest revision conflict")
    else:
        write_manifest_atomic(manifest_path, manifest)
    return {
        "status": "FOREIGN_FLOW_READY", "session_date": key, "rows": len(frame),
        "unit": "SHARES", "sidecar_path": str(sidecar), "sidecar_sha256": sidecar_sha,
        "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path),
        "publication_time_known": False,
        "knowledge_time_semantics": meta["knowledge_time_semantics"],
        "provider_calls": 0, "outcome_blind": True,
    }


def verify_session_foreign_flow(runtime_root: str | Path, session_date: str | pd.Timestamp) -> bool:
    root = Path(runtime_root).expanduser().resolve()
    key = pd.Timestamp(session_date).normalize().date().isoformat()
    directory = root / "forward_monitoring" / "sessions" / key
    manifest_path = directory / "idx_foreign_flow.manifest.json"
    sidecar = directory / "idx_foreign_flow.parquet"
    if not manifest_path.exists() or not sidecar.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_path = Path(str(manifest["source_raw_path"]))
        parent_path = Path(str(manifest["parent_session_manifest_path"]))
        return (
            manifest.get("status") == "FOREIGN_FLOW_READY"
            and manifest.get("session_date") == key
            and manifest.get("outcome_blind") is True
            and manifest.get("forward_outcomes_accessed") is False
            and manifest.get("sidecar_sha256") == sha256_file(sidecar)
            and raw_path.exists() and manifest.get("source_raw_sha256") == sha256_file(raw_path)
            and parent_path.exists()
            and manifest.get("parent_session_manifest_sha256") == sha256_file(parent_path)
        )
    except (KeyError, OSError, ValueError, TypeError):
        return False
