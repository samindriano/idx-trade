from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse
from uuid import uuid4
from decimal import Decimal, InvalidOperation

import pandas as pd

from .provenance import sha256_file
from .security_master import normalise_ticker


SCHEMA_VERSION = 1
CODE_PATTERN = r"[A-Z0-9]{4,5}"
COLUMNS = (
    "security_code", "session_date", "unit", "foreign_buy", "foreign_sell",
    "foreign_net", "knowledge_at_utc", "source", "source_ref", "source_sha256",
)


def _nonnegative_integer(value: object, *, field: str, code: str) -> int:
    """Parse an official share count without silently accepting fractions."""

    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} missing/invalid for {code}")
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field} missing/invalid for {code}") from None
    if (
        not parsed.is_finite()
        or parsed < 0
        or parsed != parsed.to_integral_value()
    ):
        raise ValueError(f"{field} must be a non-negative integer for {code}")
    return int(parsed)


def _https_url(value: object, *, field: str) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError(f"{field} must be an HTTPS URL")
    return url


def _metadata_integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} missing/invalid")
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field} missing/invalid") from None
    if not parsed.is_finite() or parsed < 0 or parsed != parsed.to_integral_value():
        raise ValueError(f"{field} must be a non-negative integer")
    return int(parsed)


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
    total = _metadata_integer(payload.get("recordsTotal"), field="Stock Summary recordsTotal")
    if total != len(rows) or total <= 0:
        raise ValueError(f"Stock Summary completeness mismatch rows={len(rows)} total={total}")
    filtered = payload.get("recordsFiltered")
    if filtered is not None and _metadata_integer(
        filtered, field="Stock Summary recordsFiltered"
    ) != total:
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
    source_ref = _https_url(source_ref, field="source_ref")

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
        buy = _nonnegative_integer(raw.get("ForeignBuy"), field="ForeignBuy", code=code)
        sell = _nonnegative_integer(raw.get("ForeignSell"), field="ForeignSell", code=code)
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

    def normalise(frame: pd.DataFrame) -> pd.DataFrame | None:
        value = frame.loc[:, COLUMNS].copy()
        value["security_code"] = value["security_code"].astype("string")
        value["session_date"] = pd.to_datetime(
            value["session_date"], errors="coerce", utc=True
        ).dt.tz_localize(None).dt.normalize()
        value["knowledge_at_utc"] = pd.to_datetime(
            value["knowledge_at_utc"], errors="coerce", utc=True
        )
        if value["session_date"].isna().any() or value["knowledge_at_utc"].isna().any():
            return None
        for column in ("foreign_buy", "foreign_sell", "foreign_net"):
            numeric = pd.to_numeric(value[column], errors="coerce")
            if numeric.isna().any() or (~numeric.eq(numeric.round())).any():
                return None
            if column in {"foreign_buy", "foreign_sell"} and numeric.lt(0).any():
                return None
            value[column] = numeric.astype("int64")
        if not value["foreign_net"].eq(value["foreign_buy"] - value["foreign_sell"]).all():
            return None
        for column in ("unit", "source", "source_ref", "source_sha256"):
            value[column] = value[column].astype("string")
            if value[column].isna().any():
                return None
        return value.sort_values(["security_code", "session_date"]).reset_index(drop=True)

    left, right = normalise(existing), normalise(incoming)
    if left is None or right is None:
        return False
    return left.equals(right)


def _write_bytes_exclusive(path: Path, data: bytes) -> bool:
    """Create a file once; never replace a concurrent or existing artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(str(path), flags, 0o666)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "wb") as target:
        target.write(data)
        target.flush()
        os.fsync(target.fileno())
    return True


def _write_parquet_exclusive(frame: pd.DataFrame, path: Path) -> bool:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        frame.to_parquet(temporary, index=False)
        return _write_bytes_exclusive(path, temporary.read_bytes())
    finally:
        temporary.unlink(missing_ok=True)


def _canonical_evidence(root: Path, key: str) -> dict[str, Any]:
    directory = root / "forward_monitoring" / "sessions" / key
    parent_path = directory / "manifest.json"
    raw_path = directory / "idx_stock_summary.raw.json"
    if not parent_path.exists() or not raw_path.exists():
        raise FileNotFoundError(f"canonical Stock Summary evidence missing for {key}")

    try:
        parent = json.loads(parent_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("canonical session manifest is unreadable") from error
    if not isinstance(parent, Mapping):
        raise RuntimeError("canonical session manifest is not an object")
    if parent.get("status") != "DATA_READY":
        raise RuntimeError("canonical session is not DATA_READY")
    if parent.get("session_date") != key:
        raise RuntimeError("canonical manifest session mismatch")
    if parent.get("outcome_blind") is not True or parent.get("forward_outcomes_accessed") is not False:
        raise RuntimeError("canonical session is not outcome-blind")

    raw_sha = sha256_file(raw_path)
    declared_raw_sha = str(parent.get("stock_summary_raw_sha256") or "").lower()
    if declared_raw_sha != raw_sha:
        raise RuntimeError("Stock Summary raw SHA mismatch")

    source = parent.get("stock_summary_source")
    if not isinstance(source, Mapping):
        raise RuntimeError("Stock Summary capture metadata missing")
    if source.get("session_date") != key:
        raise RuntimeError("Stock Summary source session mismatch")
    params = source.get("params")
    expected_param_date = key.replace("-", "")
    if not isinstance(params, Mapping) or params.get("date") != expected_param_date:
        raise RuntimeError("Stock Summary source date parameter mismatch")
    if source.get("completeness_status") != "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE":
        raise RuntimeError("Stock Summary source completeness is not canonical")
    try:
        source_ref = _https_url(source.get("source_ref"), field="source_ref")
        if source.get("endpoint"):
            _https_url(source.get("endpoint"), field="source endpoint")
    except ValueError as error:
        raise RuntimeError(str(error)) from error
    observed = source.get("observed_available_at_utc")
    if not observed:
        raise RuntimeError("Stock Summary observed availability is missing")

    try:
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("Stock Summary raw payload is unreadable") from error
    if not isinstance(payload, Mapping):
        raise RuntimeError("Stock Summary raw payload is not an object")
    frame, meta = parse_stock_summary_foreign_flow(
        payload,
        session_date=key,
        knowledge_at_utc=observed,
        source_ref=source_ref,
        source_sha256=raw_sha,
    )

    payload_total = int(payload["recordsTotal"])
    payload_filtered = payload.get("recordsFiltered")
    checks = (
        ("row_count", len(frame), source.get("row_count")),
        ("records_total", payload_total, source.get("records_total")),
        ("records_filtered", payload_filtered, source.get("records_filtered")),
    )
    for name, actual, declared in checks:
        if declared is not None:
            try:
                declared_integer = _metadata_integer(declared, field=f"Stock Summary source {name}")
            except ValueError as error:
                raise RuntimeError(str(error)) from error
            if actual is None or declared_integer != int(actual):
                raise RuntimeError(f"Stock Summary source {name} metadata mismatch")

    return {
        "key": key,
        "directory": directory,
        "parent_path": parent_path,
        "raw_path": raw_path,
        "parent": parent,
        "source": source,
        "source_ref": source_ref,
        "observed_available_at_utc": str(observed),
        "raw_sha": raw_sha,
        "parent_sha": sha256_file(parent_path),
        "frame": frame,
        "meta": meta,
    }


def _foreign_flow_manifest(context: Mapping[str, Any], sidecar: Path, sidecar_sha: str) -> dict[str, Any]:
    source = context["source"]
    return {
        **context["meta"],
        "status": "FOREIGN_FLOW_READY",
        "session_date": context["key"],
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "sidecar_path": str(sidecar),
        "sidecar_sha256": sidecar_sha,
        "parent_session_manifest_path": str(context["parent_path"]),
        "parent_session_manifest_sha256": context["parent_sha"],
        "source_raw_path": str(context["raw_path"]),
        "source_raw_sha256": context["raw_sha"],
        "source_endpoint": source.get("endpoint"),
        "source_ref": context["source_ref"],
        "observed_available_at_utc": context["observed_available_at_utc"],
    }


def _result(context: Mapping[str, Any], sidecar: Path, manifest_path: Path) -> dict[str, Any]:
    meta = context["meta"]
    return {
        "status": "FOREIGN_FLOW_READY",
        "session_date": context["key"],
        "rows": int(meta["rows"]),
        "four_character_codes": int(meta["four_character_codes"]),
        "five_character_codes": int(meta["five_character_codes"]),
        "zero_flow_rows": int(meta["zero_flow_rows"]),
        "unit": "SHARES",
        "sidecar_path": str(sidecar),
        "sidecar_sha256": sha256_file(sidecar),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "source_sha256": context["raw_sha"],
        "knowledge_at_utc": context["observed_available_at_utc"],
        "publication_time_known": False,
        "knowledge_time_semantics": meta["knowledge_time_semantics"],
        "verification_result": True,
        "provider_calls": 0,
        "outcome_blind": True,
    }


def _verified_context(root: Path, key: str) -> tuple[dict[str, Any], Path, Path]:
    context = _canonical_evidence(root, key)
    directory = context["directory"]
    sidecar = directory / "idx_foreign_flow.parquet"
    manifest_path = directory / "idx_foreign_flow.manifest.json"
    if not sidecar.exists() or not manifest_path.exists():
        raise RuntimeError("foreign-flow sidecar or manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("foreign-flow manifest is unreadable") from error
    expected = _foreign_flow_manifest(context, sidecar, sha256_file(sidecar))
    if manifest != expected:
        raise RuntimeError("foreign-flow manifest does not match canonical evidence")
    try:
        stored = pd.read_parquet(sidecar)
    except Exception as error:
        raise RuntimeError("foreign-flow sidecar is unreadable") from error
    if not _same(stored, context["frame"]):
        raise RuntimeError("foreign-flow sidecar does not match canonical raw evidence")
    return context, sidecar, manifest_path


def inspect_session_foreign_flow(runtime_root: str | Path, session_date: str | pd.Timestamp) -> dict[str, Any]:
    """Return verified sidecar facts rebuilt from the deterministic parent paths."""

    root = Path(runtime_root).expanduser().resolve()
    key = pd.Timestamp(session_date).normalize().date().isoformat()
    context, sidecar, manifest_path = _verified_context(root, key)
    return _result(context, sidecar, manifest_path)


def enrich_session_foreign_flow(runtime_root: str | Path, session_date: str | pd.Timestamp) -> dict[str, Any]:
    """Build/verify an outcome-blind sidecar from already-captured official bytes only."""
    root = Path(runtime_root).expanduser().resolve()
    key = pd.Timestamp(session_date).normalize().date().isoformat()
    context = _canonical_evidence(root, key)
    directory = context["directory"]

    sidecar = directory / "idx_foreign_flow.parquet"
    if sidecar.exists():
        if not _same(pd.read_parquet(sidecar), context["frame"]):
            raise RuntimeError("immutable foreign-flow sidecar revision conflict")
    else:
        _write_parquet_exclusive(context["frame"], sidecar)
        if not _same(pd.read_parquet(sidecar), context["frame"]):
            raise RuntimeError("new foreign-flow sidecar failed canonical verification")
    sidecar_sha = sha256_file(sidecar)
    manifest_path = directory / "idx_foreign_flow.manifest.json"
    manifest = _foreign_flow_manifest(context, sidecar, sidecar_sha)
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old != manifest:
            raise RuntimeError("immutable foreign-flow manifest revision conflict")
    else:
        _write_bytes_exclusive(
            manifest_path,
            json.dumps(manifest, indent=2, ensure_ascii=False, default=str).encode("utf-8"),
        )
        written = json.loads(manifest_path.read_text(encoding="utf-8"))
        if written != manifest:
            raise RuntimeError("new foreign-flow manifest failed canonical verification")
    _verified_context(root, key)
    return _result(context, sidecar, manifest_path)


def verify_session_foreign_flow(runtime_root: str | Path, session_date: str | pd.Timestamp) -> bool:
    root = Path(runtime_root).expanduser().resolve()
    key = pd.Timestamp(session_date).normalize().date().isoformat()
    try:
        _verified_context(root, key)
        return True
    except (KeyError, OSError, RuntimeError, ValueError, TypeError, ImportError):
        return False
