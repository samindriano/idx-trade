"""Offline correctness and bounded-preflight contracts for TradingView V2.1.

This module deliberately does not acquire provider data.  It supplies the
identity, session, corporate-action, fidelity, request-schema, and resumable
artifact primitives used by the V2.1 remediation audit.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


UTC = timezone.utc
REQUIRED_SYMBOL = "IDX:"
V2_1_CONTROLS = ("BBCA", "BBRI", "BMRI", "TLKM", "ASII")
STATUS_MAPPED = "MAPPED"
STATUS_OUTSIDE = "OUTSIDE_LISTING_INTERVAL"
STATUS_AMBIGUOUS = "AMBIGUOUS_SECURITY_IDENTITY"
STATUS_MISMATCH = "SECURITY_ID_MISMATCH"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ticker(value: object) -> str:
    return str(value).upper().replace(".JK", "").strip()


def _date_series(values: Iterable[object]) -> pd.Series:
    return pd.to_datetime(pd.Series(values), errors="coerce").dt.normalize()


def load_identity_intervals(
    security_master_path: Path,
    curated_identities_path: Path | None = None,
    scope_exclusions_path: Path | None = None,
) -> pd.DataFrame:
    """Load the PIT common-stock identity intervals without collapsing history."""

    master = pd.read_csv(security_master_path, dtype=str)
    master = master.rename(columns={"KodeEmiten": "ticker"})
    required = {"security_id", "ticker", "listed_from", "listed_to"}
    missing = required - set(master.columns)
    if missing:
        raise ValueError(f"security master missing columns: {sorted(missing)}")
    columns = ["security_id", "ticker", "company_name", "listed_from", "listed_to", "source"]
    for column in columns:
        if column not in master:
            master[column] = ""
    master = master[columns].copy()

    if curated_identities_path and curated_identities_path.exists():
        curated = pd.read_csv(curated_identities_path, dtype=str)
        common = curated[curated.get("security_type", pd.Series(dtype=str)).str.contains("Biasa|Common", case=False, na=False)].copy()
        if not common.empty:
            common["ticker"] = common["ticker"].map(_ticker)
            common["security_id"] = "IDX:" + common["ticker"] + ":" + pd.to_datetime(common["listed_from"]).dt.strftime("%Y%m%d")
            common["source"] = common.get("source", "CURATED_SECURITY_IDENTITY")
            for column in columns:
                if column not in common:
                    common[column] = ""
            master = pd.concat([master, common[columns]], ignore_index=True)

    exclusions: set[str] = set()
    if scope_exclusions_path and scope_exclusions_path.exists():
        excluded = pd.read_csv(scope_exclusions_path, dtype=str)
        exclusions = set(excluded.get("ticker", pd.Series(dtype=str)).map(_ticker).dropna())

    master["ticker"] = master["ticker"].map(_ticker)
    master["listed_from"] = _date_series(master["listed_from"])
    master["listed_to"] = _date_series(master["listed_to"])
    master = master.dropna(subset=["ticker", "listed_from"])
    master = master[~master["ticker"].isin(exclusions)]
    master = master.drop_duplicates(["security_id", "ticker", "listed_from", "listed_to"], keep="last")
    return master.sort_values(["ticker", "listed_from", "security_id"]).reset_index(drop=True)


def map_identity_frame(frame: pd.DataFrame, intervals: pd.DataFrame, date_column: str = "session_date") -> pd.DataFrame:
    """Map each row to exactly one PIT identity, or fail closed.

    Provider ticker is retained as a separate field.  A provider bar is never
    considered model-safe merely because its ticker falls inside a broad date
    range.
    """

    if date_column not in frame or "ticker" not in frame:
        raise ValueError("identity mapping requires ticker and date columns")
    result = frame.copy()
    result["ticker"] = result["ticker"].map(_ticker)
    dates = pd.to_datetime(result[date_column], errors="coerce").dt.normalize()
    result["identity_count"] = 0
    result["mapped_security_id"] = ""
    result["identity_status"] = STATUS_OUTSIDE
    for ticker, row_indices in result.groupby("ticker", sort=False).groups.items():
        subset = intervals[intervals["ticker"].eq(ticker)]
        if subset.empty:
            continue
        indices = list(row_indices)
        counts = pd.Series(0, index=indices, dtype="int64")
        mapped = pd.Series("", index=indices, dtype="string")
        for identity in subset.itertuples(index=False):
            start = pd.Timestamp(identity.listed_from)
            end = pd.Timestamp(identity.listed_to) if pd.notna(identity.listed_to) else pd.Timestamp.max
            mask = dates.loc[indices].ge(start) & dates.loc[indices].le(end)
            matching = [index for index, keep in mask.items() if bool(keep)]
            counts.loc[matching] += 1
            for index in matching:
                mapped.loc[index] = str(identity.security_id)
        result.loc[indices, "identity_count"] = counts
        result.loc[indices, "mapped_security_id"] = mapped
        result.loc[indices, "identity_status"] = counts.map({0: STATUS_OUTSIDE, 1: STATUS_MAPPED}).fillna(STATUS_AMBIGUOUS)
    return result


def identity_audit_summary(expected: pd.DataFrame, mapped_bars: pd.DataFrame, intervals: pd.DataFrame) -> dict[str, Any]:
    expected_map = map_identity_frame(expected, intervals)
    expected_mismatch = expected_map[
        expected_map["identity_status"].eq(STATUS_MAPPED)
        & expected_map["security_id"].astype(str).ne(expected_map["mapped_security_id"].astype(str))
    ]
    bar_status = mapped_bars.get("identity_status", pd.Series(dtype=str))
    return {
        "security_master_rows": int(len(intervals)),
        "security_master_tickers": int(intervals["ticker"].nunique()),
        "tickers_with_multiple_intervals": int((intervals.groupby("ticker").size() > 1).sum()),
        "overlapping_interval_tickers": int(_overlapping_tickers(intervals)),
        "expected_rows": int(len(expected_map)),
        "expected_mapped_rows": int(expected_map["identity_status"].eq(STATUS_MAPPED).sum()),
        "expected_outside_rows": int(expected_map["identity_status"].eq(STATUS_OUTSIDE).sum()),
        "expected_ambiguous_rows": int(expected_map["identity_status"].eq(STATUS_AMBIGUOUS).sum()),
        "expected_security_id_mismatch_rows": int(len(expected_mismatch)),
        "provider_bar_rows": int(len(mapped_bars)),
        "provider_bar_mapped_rows": int((bar_status == STATUS_MAPPED).sum()),
        "provider_bar_outside_rows": int((bar_status == STATUS_OUTSIDE).sum()),
        "provider_bar_ambiguous_rows": int((bar_status == STATUS_AMBIGUOUS).sum()),
        "provider_bar_security_id_mismatch_rows": int((mapped_bars.get("security_id", pd.Series(dtype=str)).astype(str) != mapped_bars.get("mapped_security_id", pd.Series(dtype=str)).astype(str)).sum()) if not mapped_bars.empty else 0,
        "provider_identity_contract": "provider_ticker_and_exchange_security_id_are_separate; exact one-interval mapping required",
    }


def _overlapping_tickers(intervals: pd.DataFrame) -> int:
    count = 0
    for _, group in intervals.groupby("ticker", sort=False):
        ordered = group.sort_values("listed_from")
        previous_end = None
        for row in ordered.itertuples(index=False):
            start = pd.Timestamp(row.listed_from)
            end = pd.Timestamp(row.listed_to) if pd.notna(row.listed_to) else pd.Timestamp.max
            if previous_end is not None and start <= previous_end:
                count += 1
                break
            previous_end = end
    return count


def official_session_neighborhood(official_sessions: pd.DataFrame, events: pd.DataFrame) -> tuple[set[tuple[str, str]], dict[str, Any]]:
    """Return event/current/previous/next official sessions by ordered index."""

    sessions = pd.to_datetime(official_sessions["date"], errors="coerce").dt.normalize().dropna().sort_values().drop_duplicates().tolist()
    index = {value.date().isoformat(): position for position, value in enumerate(sessions)}
    keys: set[tuple[str, str]] = set()
    unmapped: list[dict[str, str]] = []
    for row in events.itertuples(index=False):
        ticker = _ticker(getattr(row, "ticker", ""))
        effective = pd.Timestamp(getattr(row, "effective_date")).normalize()
        date_key = effective.date().isoformat()
        if date_key not in index:
            unmapped.append({"ticker": ticker, "effective_date": date_key})
            continue
        position = index[date_key]
        for candidate in (position - 1, position, position + 1):
            if 0 <= candidate < len(sessions):
                keys.add((ticker, sessions[candidate].date().isoformat()))
    return keys, {"official_session_count": len(sessions), "event_count": int(len(events)), "unmapped_event_count": len(unmapped), "unmapped_events": unmapped}


def corporate_action_flags(rows: pd.DataFrame, events: pd.DataFrame, official_sessions: pd.DataFrame) -> pd.Series:
    keys, _ = official_session_neighborhood(official_sessions, events)
    return rows.apply(lambda row: (_ticker(row["ticker"]), str(row["session_date"])) in keys, axis=1)


def calendar_radius_flags(rows: pd.DataFrame, events: pd.DataFrame, radius: int = 1) -> pd.Series:
    keys: set[tuple[str, str]] = set()
    for row in events.itertuples(index=False):
        ticker = _ticker(getattr(row, "ticker", ""))
        effective = pd.Timestamp(getattr(row, "effective_date"))
        for delta in range(-radius, radius + 1):
            keys.add((ticker, (effective + pd.Timedelta(days=delta)).date().isoformat()))
    return rows.apply(lambda row: (_ticker(row["ticker"]), str(row["session_date"])) in keys, axis=1)


def fidelity_report_v2_1(rows: pd.DataFrame, events: pd.DataFrame, official_sessions: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Recompute fidelity with ordered official-session CA quarantine."""

    result = rows.copy()
    _, session_detail = official_session_neighborhood(official_sessions, events)
    result["old_calendar_quarantined"] = result.get("corporate_action_quarantined", False).astype(bool)
    result["calendar_radius_quarantined"] = calendar_radius_flags(result, events)
    result["session_index_quarantined"] = corporate_action_flags(result, events, official_sessions)
    clean = result[~result["session_index_quarantined"]].copy()
    for field in ("high", "low", "close"):
        clean[f"{field}_exact"] = clean[field].eq(clean[f"canonical_{field}"])
    clean["hlc_exact"] = clean[["high_exact", "low_exact", "close_exact"]].all(axis=1)
    clean["volume_within_5"] = (clean["volume"] - clean["canonical_volume"]).abs() <= clean["canonical_volume"].abs().clip(lower=1.0) * 0.05
    by_year: dict[str, Any] = {}
    clean["year"] = pd.to_datetime(clean["session_date"]).dt.year
    for year, group in clean.groupby("year", sort=True):
        by_year[str(year)] = {
            "rows": int(len(group)),
            "hlc_exact_rate": float(group["hlc_exact"].mean()) if len(group) else None,
            "volume_within_5_rate": float(group["volume_within_5"].mean()) if len(group) else None,
        }
    changed = int((result["old_calendar_quarantined"] != result["session_index_quarantined"]).sum())
    return result, {
        "matched_rows": int(len(result)),
        "old_calendar_quarantined_rows": int(result["old_calendar_quarantined"].sum()),
        "calendar_radius_quarantined_rows": int(result["calendar_radius_quarantined"].sum()),
        "session_index_quarantined_rows": int(result["session_index_quarantined"].sum()),
        "quarantine_flag_changed_rows": changed,
        "unmapped_event_count": int(session_detail["unmapped_event_count"]),
        "unmapped_events": session_detail["unmapped_events"],
        "non_ca_rows": int(len(clean)),
        "hlc_exact_rate": float(clean["hlc_exact"].mean()) if len(clean) else None,
        "volume_within_5_rate": float(clean["volume_within_5"].mean()) if len(clean) else None,
        "by_year": by_year,
    }


def mismatch_top20(rows: pd.DataFrame, years: Sequence[int] = (2022, 2026)) -> pd.DataFrame:
    working = rows[~rows["session_index_quarantined"]].copy()
    for field in ("high", "low", "close"):
        working[f"{field}_abs_error"] = (working[field] - working[f"canonical_{field}"]).abs()
        working[f"{field}_exact"] = working[field].eq(working[f"canonical_{field}"])
    working["hlc_exact"] = working[["high_exact", "low_exact", "close_exact"]].all(axis=1)
    working["volume_relative_error"] = (working["volume"] - working["canonical_volume"]).abs() / working["canonical_volume"].abs().clip(lower=1.0)
    records: list[dict[str, Any]] = []
    for year in years:
        subset = working[pd.to_datetime(working["session_date"]).dt.year.eq(year)]
        grouped = subset.groupby("ticker", sort=True)
        for ticker, group in grouped:
            records.append({
                "year": int(year),
                "ticker": ticker,
                "rows": int(len(group)),
                "hlc_mismatch_rows": int((~group["hlc_exact"]).sum()),
                "hlc_mismatch_rate": float((~group["hlc_exact"]).mean()) if len(group) else 0.0,
                "mean_high_abs_error": float(group["high_abs_error"].mean()),
                "mean_low_abs_error": float(group["low_abs_error"].mean()),
                "mean_close_abs_error": float(group["close_abs_error"].mean()),
                "volume_within_5_rate": float((group["volume_relative_error"] <= 0.05).mean()),
            })
    output = pd.DataFrame(records)
    if output.empty:
        return output
    output["rank"] = output.groupby("year")["hlc_mismatch_rows"].rank(method="first", ascending=False)
    return output[output["rank"] <= 20].sort_values(["year", "rank"]).reset_index(drop=True)


def build_expected_state_reconciliation(expected: pd.DataFrame, activity: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    """Build exact future model-safe status without dropping contradictions."""

    expected_keys = expected[["ticker", "session_date", "security_id"]].copy()
    activity_keys = activity[["ticker", "session_date", "activity_state"]].copy()
    usable = bars[
        bars.get("session_admissible", pd.Series(dtype=bool)).eq(True)
        & bars.get("identity_status", pd.Series(dtype=str)).eq(STATUS_MAPPED)
        & bars.get("security_id", pd.Series(dtype=str)).astype(str).eq(bars.get("mapped_security_id", pd.Series(dtype=str)).astype(str))
    ][["ticker", "session_date"]].drop_duplicates()
    usable["provider_bar_present"] = True
    result = expected_keys.merge(activity_keys, on=["ticker", "session_date"], how="left").merge(usable, on=["ticker", "session_date"], how="left")
    result["provider_bar_present"] = result["provider_bar_present"].astype("boolean").fillna(False).astype(bool)
    def status(row: pd.Series) -> str:
        state = row["activity_state"]
        has_bar = bool(row["provider_bar_present"])
        if state == "ACTIVE":
            return "COVERED_ACTIVE" if has_bar else "TRUE_PROVIDER_MISS"
        if state == "NO_TRADE":
            return "NO_TRADE_WITH_PROVIDER_BARS_REQUIRES_REVIEW" if has_bar else "NO_TRADE_NOT_EXPECTED"
        return "UNKNOWN_FAIL_CLOSED"
    result["reconciliation_status"] = result.apply(status, axis=1)
    return result.sort_values(["ticker", "session_date"]).reset_index(drop=True)


def boundary_report(requests: pd.DataFrame, bars: pd.DataFrame, diagnostics: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        observed = pd.DataFrame(columns=["ticker", "observed_first_session", "observed_last_session", "observed_rows"])
    else:
        observed = bars.groupby("ticker", sort=True).agg(
            observed_first_session=("session_date", "min"),
            observed_last_session=("session_date", "max"),
            observed_rows=("raw_epoch", "size"),
        ).reset_index()
    request_cols = ["ticker", "required_start", "required_end"]
    result = requests[request_cols].merge(observed, on="ticker", how="left")
    if not diagnostics.empty:
        result = result.merge(diagnostics[["ticker", "status", "completion_reason", "period_count", "elapsed_ms"]], on="ticker", how="left")
    observed_first = pd.to_datetime(result["observed_first_session"], errors="coerce")
    required_start = pd.to_datetime(result["required_start"], errors="coerce")
    result["required_start_reached"] = observed_first.notna() & required_start.notna() & observed_first.le(required_start)
    result["boundary_complete"] = result["required_start_reached"] & result["completion_reason"].isin(["required_start_reached", "no_extension"])
    result["boundary_status"] = result.apply(lambda row: "REQUIRED_START_REACHED" if bool(row["required_start_reached"]) else "BOUNDARY_INCOMPLETE", axis=1)
    return result


def theoretical_ceilings(activity: pd.DataFrame, diagnostics: pd.DataFrame, reconciliation: pd.DataFrame, error_tickers: Iterable[str], identity_resolved_tickers: Iterable[str]) -> dict[str, Any]:
    errors = {_ticker(value) for value in error_tickers}
    resolved = {_ticker(value) for value in identity_resolved_tickers}
    active = activity[activity["activity_state"].eq("ACTIVE")]
    total = len(active)
    error_active = int(active["ticker"].isin(errors).sum())
    identity_resolved_error_active = int(active["ticker"].isin(errors & resolved).sum())
    current_covered = int((reconciliation["reconciliation_status"] == "COVERED_ACTIVE").sum())
    non_error_active = total - error_active
    return {
        "active_sessions": int(total),
        "current_observed_coverage": float(current_covered / total) if total else 0.0,
        "symbol_error_tickers": sorted(errors),
        "symbol_error_active_sessions": error_active,
        "official_identity_resolved_symbol_error_tickers": sorted(errors & resolved),
        "official_identity_resolved_symbol_error_active_sessions": identity_resolved_error_active,
        "A_perfect_depth_current_provider_symbols": {"numerator": non_error_active, "denominator": total, "coverage": float(non_error_active / total) if total else 0.0, "interpretation": "all currently non-error provider symbols perfect-depth; invalid-symbol rows remain unresolved"},
        "B_perfect_depth_official_identity_resolved_symbols": {"numerator": total - (error_active - identity_resolved_error_active), "denominator": total, "coverage": float((total - (error_active - identity_resolved_error_active)) / total) if total else 0.0, "interpretation": "official exchange identity resolves provider-error ticker identity, but does not prove the frozen TradingView IDX:<ticker> symbol works"},
        "C_perfect_depth_all_provider_symbols": {"numerator": total, "denominator": total, "coverage": 1.0 if total else 0.0, "interpretation": "counterfactual all provider symbol errors resolved"},
        "frozen_provider_symbol_contract_unresolved": sorted(errors),
    }


def serialize_v2_1_request(request: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize the exact request types for any future probe."""

    if request.get("symbol") != f"IDX:{_ticker(request.get('ticker'))}":
        raise ValueError("symbol must be exact IDX:<ticker>")
    if request.get("server") != "prodata":
        raise ValueError("V2.1 preflight is pinned to anonymous prodata")
    if request.get("timeframe") != "60" or not isinstance(request.get("timeframe"), str):
        raise TypeError('timeframe must be string "60"')
    if request.get("session") != "regular" or request.get("adjustment") != "none":
        raise ValueError("regular session and adjustment=none are required")
    for field in ("initial_range", "fetch_more_steps", "fetch_more_batch", "timeout_ms", "to"):
        value = request.get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field} must be int")
    if request["initial_range"] <= 0 or request["fetch_more_steps"] < 0 or request["fetch_more_batch"] <= 0 or request["timeout_ms"] <= 0:
        raise ValueError("invalid pagination bounds")
    return {key: request[key] for key in sorted(request)}


def control_request_fixture(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [serialize_v2_1_request({
        "ticker": ticker,
        "symbol": f"IDX:{ticker}",
        "server": "prodata",
        "timeframe": "60",
        "session": "regular",
        "adjustment": "none",
        "initial_range": 10000,
        "fetch_more_steps": 0,
        "fetch_more_batch": int(config["acquisition"].get("fetch_more_batch", 5)),
        "timeout_ms": int(config["acquisition"].get("timeout_ms", 25000)),
        "to": int(config["window"].get("end_epoch", 1785517199)),
        "required_start": config["window"]["start"],
        "required_end": config["window"]["end"],
    }) for ticker in V2_1_CONTROLS]


def atomic_write_bytes(path: Path, payload: bytes, overwrite: bool = False) -> str:
    """Write a complete artifact atomically and return its SHA-256."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return hashlib.sha256(payload).hexdigest()


def write_streaming_artifact(path: Path, chunks: Iterable[bytes], overwrite: bool = False) -> dict[str, Any]:
    """Persist chunks through a private partial file; no partial final is visible."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".partial", dir=path.parent)
    digest = hashlib.sha256()
    total = 0
    try:
        with os.fdopen(fd, "wb") as handle:
            for chunk in chunks:
                if not isinstance(chunk, bytes):
                    raise TypeError("artifact chunks must be bytes")
                handle.write(chunk)
                digest.update(chunk)
                total += len(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return {"status": "COMPLETE", "bytes": total, "sha256": digest.hexdigest()}


def artifact_manifest(root: Path, exclude: set[str] | None = None) -> dict[str, Any]:
    exclude = exclude or set()
    artifacts: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in exclude or path.name.endswith(".partial"):
            continue
        artifacts.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = {"schema": "idx-trade/tradingview-price-path-v2-1-artifact-manifest", "artifacts": artifacts}
    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
    payload["manifest_sha256"] = hashlib.sha256(encoded).hexdigest()
    return payload


def directory_manifest(root: Path) -> dict[str, Any]:
    """Create a deterministic file-level manifest for a directory input."""

    artifacts = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        artifacts.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    encoded = (json.dumps(artifacts, sort_keys=True, indent=2) + "\n").encode("utf-8")
    return {"root": str(root), "file_count": len(artifacts), "artifacts": artifacts, "aggregate_sha256": hashlib.sha256(encoded).hexdigest()}


def verify_input_hashes(paths: Mapping[str, Path], expected_hashes: Mapping[str, str]) -> dict[str, Any]:
    """Verify every decision-bearing input before a provider call."""

    missing = sorted(name for name, path in paths.items() if not path.exists())
    mismatches = []
    for name, path in paths.items():
        if not path.exists() or name not in expected_hashes:
            continue
        actual = sha256_file(path)
        if actual != expected_hashes[name]:
            mismatches.append({"name": name, "path": str(path), "expected": expected_hashes[name], "actual": actual})
    return {"valid": not missing and not mismatches and set(paths) == set(expected_hashes), "missing": missing, "mismatches": mismatches, "unexpected_expected_keys": sorted(set(expected_hashes) - set(paths))}


def immutable_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n").encode("utf-8")


def freeze_immutable_json(path: Path, value: Any) -> str:
    """Write preregistration bytes once; identical re-use is allowed."""

    payload = immutable_json_bytes(value)
    digest = hashlib.sha256(payload).hexdigest()
    if path.exists():
        existing = path.read_bytes()
        if existing != payload:
            raise ValueError(f"immutable artifact changed: {path}")
        return digest
    atomic_write_bytes(path, payload)
    return digest


def write_network_start_marker(path: Path, preregistration_path: Path, request_count: int) -> dict[str, Any]:
    """Write a separate one-shot marker bound to immutable preregistration bytes."""

    marker = {
        "schema": "idx-trade/tradingview-price-path-v2-1-network-start-marker",
        "started_at_utc": datetime.now(tz=UTC).isoformat(),
        "preregistration_path": str(preregistration_path),
        "preregistration_sha256": sha256_file(preregistration_path),
        "request_count": int(request_count),
    }
    payload = immutable_json_bytes(marker)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("preregistration_sha256") != marker["preregistration_sha256"]:
            raise ValueError("network start marker is bound to another preregistration")
        return existing
    atomic_write_bytes(path, payload)
    return marker


def raw_request_matches(raw_request: Mapping[str, Any], expected_request: Mapping[str, Any], preregistration_sha256: str) -> bool:
    fields = ("request_index", "ticker", "symbol", "server", "timeframe", "session", "adjustment", "to", "initial_range", "fetch_more_batch", "fetch_more_steps", "timeout_ms", "required_start", "adapter_commit")
    return all(raw_request.get(field) == expected_request.get(field) for field in fields) and raw_request.get("preregistration_sha256") == preregistration_sha256


def depth_completion_status(
    *,
    provider_data_status: str,
    earliest_session: str | None,
    required_start: str,
    prior_buffer_reached: bool,
    extension_reason: str | None = None,
) -> str:
    """Classify provider availability separately from historical completeness."""

    if provider_data_status in {"SYMBOL_ERROR", "PROVIDER_ERROR"}:
        return "NOT_APPLICABLE"
    if provider_data_status in {"TRANSPORT_ERROR", "TIMEOUT"}:
        return "INCOMPLETE_TIMEOUT" if provider_data_status == "TIMEOUT" else "PROVIDER_ERROR"
    reached = earliest_session is not None and earliest_session <= required_start and prior_buffer_reached
    if reached:
        return "REQUIRED_START_REACHED"
    if extension_reason == "max_steps":
        return "INCOMPLETE_MAX_DEPTH"
    if extension_reason in {"no_extension", "page_timeout_no_extension"}:
        return "INCOMPLETE_NO_EXTENSION" if extension_reason == "no_extension" else "INCOMPLETE_TIMEOUT"
    return "INCOMPLETE_NO_EXTENSION"


def pagination_step(before_periods: Sequence[Mapping[str, Any]], after_periods: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Capture before values before the provider mutates the chart series."""

    before_epochs = [int(row["time"]) for row in before_periods if "time" in row]
    after_epochs = [int(row["time"]) for row in after_periods if "time" in row]
    before_min = min(before_epochs) if before_epochs else None
    after_min = min(after_epochs) if after_epochs else None
    return {"before_count": len(before_periods), "before_min_epoch": before_min, "after_count": len(after_periods), "after_min_epoch": after_min, "delta_bars": len(after_periods) - len(before_periods), "extended": bool(after_min is not None and (before_min is None or after_min < before_min))}


def validate_structural_rows(rows: pd.DataFrame) -> dict[str, Any]:
    """Validate, rather than silently drop, raw OHLCV structural evidence."""

    required = ["open", "high", "low", "close", "volume"]
    if rows.empty:
        return {"rows": 0, "invalid_rows": 0, "valid": True}
    numeric = rows[required].apply(pd.to_numeric, errors="coerce")
    invalid = (
        numeric.isna().any(axis=1)
        | (numeric["volume"] < 0)
        | (numeric[["open", "high", "low", "close"]] <= 0).any(axis=1)
        | (numeric["high"] < numeric["low"])
        | (numeric["open"] < numeric["low"])
        | (numeric["open"] > numeric["high"])
        | (numeric["close"] < numeric["low"])
        | (numeric["close"] > numeric["high"])
    )
    return {"rows": int(len(rows)), "invalid_rows": int(invalid.sum()), "valid": not bool(invalid.any())}


def regular_session_bar_admissible(timestamp_wib: object) -> bool:
    value = pd.Timestamp(timestamp_wib)
    return datetime.strptime("09:00", "%H:%M").time() <= value.time() < datetime.strptime("16:30", "%H:%M").time()


def yearly_fidelity_support(
    covered_active: pd.DataFrame,
    canonical_comparable: pd.DataFrame,
    years: Iterable[int],
    minimum_year_matched_rows: int = 10,
) -> dict[str, Any]:
    """Report every year, including zero-support years, with a fixed floor."""

    covered = covered_active.copy()
    comparable = canonical_comparable.copy()
    covered["year"] = pd.to_datetime(covered["session_date"]).dt.year
    comparable["year"] = pd.to_datetime(comparable["session_date"]).dt.year
    result: dict[str, Any] = {}
    for year in years:
        all_year = covered[covered["year"].eq(year)]
        compared = comparable[comparable["year"].eq(year)]
        result[str(year)] = {
            "covered_active_rows": int(len(all_year)),
            "canonical_comparable_rows": int(len(compared)),
            "unique_compared_tickers": int(compared["ticker"].nunique()) if "ticker" in compared else 0,
            "fidelity_support_ratio": float(len(compared) / len(all_year)) if len(all_year) else 0.0,
            "minimum_support_floor": int(minimum_year_matched_rows),
            "minimum_support_pass": len(compared) >= minimum_year_matched_rows,
        }
    return result


def active_only_model_safe_rows(
    bars: pd.DataFrame,
    reconciliation: pd.DataFrame,
    depth_by_ticker: Mapping[str, str],
    ca_keys: set[tuple[str, str]],
) -> pd.DataFrame:
    """Exact-inner-join the future model-safe path to ACTIVE evidence only."""

    safe = bars.copy()
    safe = safe[safe.get("session_admissible", False).astype(bool)]
    safe = safe[safe.get("identity_status", "").eq(STATUS_MAPPED)]
    safe = safe[safe["security_id"].astype(str).eq(safe["mapped_security_id"].astype(str))]
    safe = safe.merge(reconciliation[["ticker", "session_date", "activity_state", "reconciliation_status"]], on=["ticker", "session_date"], how="inner")
    safe = safe[safe["activity_state"].eq("ACTIVE") & safe["reconciliation_status"].eq("COVERED_ACTIVE")]
    safe = safe[safe["ticker"].map(depth_by_ticker).eq("REQUIRED_START_REACHED")]
    safe = safe[~safe.apply(lambda row: (_ticker(row["ticker"]), str(row["session_date"])) in ca_keys, axis=1)]
    return safe.reset_index(drop=True)


def _ratio_summary(values: pd.Series) -> dict[str, Any]:
    values = pd.to_numeric(values, errors="coerce").replace([math.inf, -math.inf], pd.NA).dropna()
    if values.empty:
        return {"count": 0}
    quantiles = values.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    return {"count": int(len(values)), **{f"q{int(key * 100):02d}": float(value) for key, value in quantiles.to_dict().items()}, "mean": float(values.mean()), "min": float(values.min()), "max": float(values.max())}


def official_stock_summary_hlcv_oracle(
    archive_root: Path,
    canonical_raw_root: Path,
    events: pd.DataFrame | None = None,
    official_sessions: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Compare accepted official Stock Summary H/L/C/V to canonical raw daily data."""

    canonical_frames = []
    for path in sorted(canonical_raw_root.glob("*.parquet")):
        frame = pd.read_parquet(path, columns=["date", "ticker", "raw_high", "raw_low", "raw_close", "raw_volume"])
        frame["session_date"] = pd.to_datetime(frame["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        canonical_frames.append(frame.rename(columns={"raw_high": "canonical_high", "raw_low": "canonical_low", "raw_close": "canonical_close", "raw_volume": "canonical_volume"})[["ticker", "session_date", "canonical_high", "canonical_low", "canonical_close", "canonical_volume"]])
    canonical = pd.concat(canonical_frames, ignore_index=True) if canonical_frames else pd.DataFrame()
    canonical["ticker"] = canonical["ticker"].map(_ticker)
    canonical_keys = set(zip(canonical["ticker"], canonical["session_date"]))
    official_records: list[dict[str, Any]] = []
    for path in sorted((archive_root / "sessions").glob("*/stock_summary.raw.json")):
        session_date = path.parent.name
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("data", []):
            key = (_ticker(row.get("StockCode")), session_date)
            if key not in canonical_keys:
                continue
            official_records.append({"ticker": key[0], "session_date": session_date, "official_high": row.get("High"), "official_low": row.get("Low"), "official_close": row.get("Close"), "official_volume": row.get("Volume")})
    official = pd.DataFrame(official_records).drop_duplicates(["ticker", "session_date"])
    merged = official.merge(canonical, on=["ticker", "session_date"], how="inner")
    for field in ("high", "low", "close", "volume"):
        merged[f"{field}_exact"] = merged[f"official_{field}"].eq(merged[f"canonical_{field}"])
    numeric = merged[["official_high", "official_low", "official_close", "official_volume", "canonical_high", "canonical_low", "canonical_close", "canonical_volume"]].apply(pd.to_numeric, errors="coerce")
    merged["valid_hlcv"] = numeric[["official_high", "official_low", "official_close"]].gt(0).all(axis=1) & numeric["official_volume"].ge(0) & numeric[["canonical_high", "canonical_low", "canonical_close"]].gt(0).all(axis=1) & numeric["canonical_volume"].ge(0)
    merged["volume_within_5"] = (numeric["official_volume"] - numeric["canonical_volume"]).abs() <= numeric["canonical_volume"].abs().clip(lower=1.0) * 0.05
    merged["hlc_exact"] = merged[["high_exact", "low_exact", "close_exact"]].all(axis=1)
    merged["volume_ratio"] = numeric["official_volume"] / numeric["canonical_volume"].replace(0, pd.NA)
    if events is not None and official_sessions is not None and not merged.empty:
        merged["ca_quarantined"] = corporate_action_flags(merged.rename(columns={"session_date": "session_date"}), events, official_sessions)
    else:
        merged["ca_quarantined"] = False
    clean = merged[~merged["ca_quarantined"]]
    by_year: dict[str, Any] = {}
    for year, group in merged.assign(year=merged["session_date"].str[:4]).groupby("year", sort=True):
        valid = group[group["valid_hlcv"]]
        by_year[str(year)] = {"common_rows": int(len(group)), "valid_rows": int(len(valid)), "ca_quarantined_rows": int(group["ca_quarantined"].sum()), "h_exact": float(valid["high_exact"].mean()) if len(valid) else None, "l_exact": float(valid["low_exact"].mean()) if len(valid) else None, "c_exact": float(valid["close_exact"].mean()) if len(valid) else None, "hlc_exact": float(valid["hlc_exact"].mean()) if len(valid) else None, "volume_exact": float(valid["volume_exact"].mean()) if len(valid) else None, "volume_within_5": float(valid["volume_within_5"].mean()) if len(valid) else None}
    recommendation = "OFFICIAL_STOCK_SUMMARY_HLCV_ORACLE_INCONCLUSIVE"
    if len(clean) and clean["valid_hlcv"].mean() >= 0.99 and clean.loc[clean["valid_hlcv"], "hlc_exact"].mean() >= 0.99 and clean.loc[clean["valid_hlcv"], "volume_within_5"].mean() >= 0.99:
        recommendation = "OFFICIAL_STOCK_SUMMARY_HLCV_ORACLE_SUPPORTED"
    elif len(clean) and clean["valid_hlcv"].mean() < 0.95:
        recommendation = "OFFICIAL_STOCK_SUMMARY_HLCV_ORACLE_NOT_SUPPORTED"
    valid_clean = clean[clean["valid_hlcv"]]
    field_error_summary = {}
    missingness = {}
    for field in ("high", "low", "close", "volume"):
        official_field = pd.to_numeric(clean[f"official_{field}"], errors="coerce")
        canonical_field = pd.to_numeric(clean[f"canonical_{field}"], errors="coerce")
        absolute = (official_field - canonical_field).abs().dropna()
        field_error_summary[field] = _ratio_summary(absolute)
        missingness[field] = {"official_missing": int(official_field.isna().sum()), "canonical_missing": int(canonical_field.isna().sum()), "official_zero": int((official_field == 0).sum()), "canonical_zero": int((canonical_field == 0).sum())}
    summary = {"common_rows": int(len(merged)), "valid_rows": int(merged["valid_hlcv"].sum()), "h_exact": float(valid_clean["high_exact"].mean()) if len(valid_clean) else None, "l_exact": float(valid_clean["low_exact"].mean()) if len(valid_clean) else None, "c_exact": float(valid_clean["close_exact"].mean()) if len(valid_clean) else None, "hlc_exact": float(valid_clean["hlc_exact"].mean()) if len(valid_clean) else None, "volume_exact": float(valid_clean["volume_exact"].mean()) if len(valid_clean) else None, "volume_within_5": float(valid_clean["volume_within_5"].mean()) if len(valid_clean) else None, "ca_quarantined_rows": int(merged["ca_quarantined"].sum()), "missing_or_invalid_hlcv_rows": int((~merged["valid_hlcv"]).sum()), "volume_ratio": _ratio_summary(valid_clean["volume_ratio"]), "field_absolute_error_summary": field_error_summary, "missingness": missingness, "units_scaling_interpretation": "bulk median ratio is inspected without rescaling; tail ratios are reported as mismatches", "by_year": by_year, "recommendation": recommendation, "oracle_role": "diagnostic_only; canonical daily source remains the admission oracle"}
    return merged, summary
