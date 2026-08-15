"""Outcome-blind prospective producer for Foreign Flow Representation V2.

The producer is deliberately a consumer of already-captured canonical EOD
artifacts.  It does not call a provider, create a scheduler, or alter the
accepted V2 formulas.  A target session ``t+1`` is materialized only from
flow and market context through the immediately preceding official session
``t``.  Historical context is reloaded from the pinned offline archive and
then extended with verified forward session artifacts; no in-place mutable
rolling state is trusted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from .foreign_flow_features_v2 import (
    FEATURE_COLUMNS_V2,
    OUTPUT_COLUMNS_V2,
    build_foreign_flow_representation_v2,
)
from .foreign_flow_representation_v2_runner import (
    _dates,
    build_causal_market_context,
    read_verified_flow_archive,
    sha256_file,
)
from .forward_foreign_flow import _canonical_evidence, _verified_context, _write_parquet_exclusive
from .forward_foreign_flow_runtime import run_foreign_flow_catchup
from .provenance import sha256_file as provenance_sha256_file


REPRESENTATION_FILENAME = "foreign_flow_representation_v2.parquet"
REPRESENTATION_MANIFEST_FILENAME = "foreign_flow_representation_v2.manifest.json"
SCHEMA_VERSION = "idx-trade/foreign-flow-representation-v2-forward-v1"

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
        raise ValueError(f"invalid date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


def _session_index(path: Path) -> pd.DatetimeIndex:
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise ValueError(f"official calendar has no date column: {path}")
    dates = pd.DatetimeIndex(_dates(frame["date"], name="official calendar date"))
    if len(dates) == 0 or dates.has_duplicates:
        raise ValueError("official calendar is empty or duplicated")
    return dates.sort_values()


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
    except FileExistsError:
        return False
    return True


def _normalise_flow(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "security_code" in out.columns and "ticker" not in out.columns:
        out = out.rename(columns={"security_code": "ticker"})
    required = {"ticker", "session_date", "foreign_buy", "foreign_sell", "foreign_net", "unit"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"forward flow missing columns: {sorted(missing)}")
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["session_date"] = _dates(out["session_date"], name="flow session date")
    for column in ("foreign_buy", "foreign_sell", "foreign_net"):
        values = pd.to_numeric(out[column], errors="coerce")
        if values.isna().any() or (~np.isfinite(values)).any() or (values % 1 != 0).any():
            raise ValueError(f"flow has invalid {column}")
        out[column] = values.astype("int64")
    if (out[["foreign_buy", "foreign_sell"]] < 0).any().any():
        raise ValueError("flow has negative buy/sell")
    if not out["foreign_net"].eq(out["foreign_buy"] - out["foreign_sell"]).all():
        raise ValueError("flow net identity mismatch")
    if not out["unit"].astype(str).eq("SHARES").all():
        raise ValueError("flow unit is not SHARES")
    if out.duplicated(["ticker", "session_date"]).any():
        raise ValueError("flow has duplicate ticker/session rows")
    return out


def _normalise_market(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "session_date", "high", "low", "close", "volume", "regular_market_value"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"forward market data missing columns: {sorted(missing)}")
    forbidden = [
        column
        for column in frame.columns
        if any(token in str(column).lower() for token in _FORBIDDEN_TOKENS)
    ]
    if forbidden:
        raise ValueError(f"market data is not outcome-blind: {sorted(forbidden)}")
    out = frame.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    out["session_date"] = _dates(out["session_date"], name="market session date")
    numeric = ["high", "low", "close", "volume", "regular_market_value"]
    for column in numeric:
        values = pd.to_numeric(out[column], errors="coerce")
        if values.notna().any() and (~np.isfinite(values.dropna())).any():
            raise ValueError(f"market data has non-finite {column}")
        out[column] = values.astype(float)
    if (out[["high", "low", "close"]].dropna() <= 0).any().any():
        raise ValueError("market data has non-positive OHLC")
    if (out[["volume", "regular_market_value"]].dropna() < 0).any().any():
        raise ValueError("market data has negative volume/value")
    if (out["low"] > out["high"]).any():
        raise ValueError("market data has low above high")
    if out.duplicated(["ticker", "session_date"]).any():
        raise ValueError("market data has duplicate ticker/session rows")
    return out


def _normalise_master(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "listed_from", "listed_to"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"security master missing columns: {sorted(missing)}")
    out = frame[["ticker", "listed_from", "listed_to"]].copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    out["listed_from"] = _dates(out["listed_from"], name="listed_from")
    out["listed_to"] = pd.to_datetime(out["listed_to"], errors="coerce")
    if isinstance(out["listed_to"].dtype, pd.DatetimeTZDtype):
        out["listed_to"] = out["listed_to"].dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
    out["listed_to"] = out["listed_to"].dt.normalize()
    if out.duplicated(["ticker", "listed_from"]).any():
        raise ValueError("security master has duplicate listing identities")
    return out


def _merge_unique(left: pd.DataFrame, right: pd.DataFrame, keys: list[str], *, label: str) -> pd.DataFrame:
    if left.empty:
        return right.copy()
    if right.empty:
        return left.copy()
    combined = pd.concat([left, right], ignore_index=True, sort=False)
    duplicates = combined.duplicated(keys, keep=False)
    if not duplicates.any():
        return combined
    for _, group in combined.loc[duplicates].groupby(keys, sort=False):
        # Source metadata is intentionally part of the identity audit.  A
        # duplicate key from two captures is accepted only when every value is
        # byte-equivalent after normalisation.
        if len(group.drop_duplicates().index) != 1:
            raise RuntimeError(f"{label} has conflicting duplicate identity: {group[keys].iloc[0].to_dict()}")
    return combined.drop_duplicates(keys, keep="first").reset_index(drop=True)


def _read_verified_forward_market(runtime_root: Path, key: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    context = _canonical_evidence(runtime_root, key)
    parent = context["parent"]
    ohlcv_path = Path(str(parent.get("session_ohlcv_path") or "")).expanduser().resolve()
    evidence_path = Path(str(parent.get("evidence_path") or "")).expanduser().resolve()
    if not ohlcv_path.is_file() or not evidence_path.is_file():
        raise FileNotFoundError(f"canonical market artifacts are missing for {key}")
    expected_ohlcv_sha = str(parent.get("session_ohlcv_sha256") or "").lower()
    expected_evidence_sha = str(parent.get("evidence_sha256") or "").lower()
    if len(expected_ohlcv_sha) != 64 or provenance_sha256_file(ohlcv_path) != expected_ohlcv_sha:
        raise RuntimeError(f"session OHLCV hash mismatch for {key}")
    if len(expected_evidence_sha) != 64 or provenance_sha256_file(evidence_path) != expected_evidence_sha:
        raise RuntimeError(f"session evidence hash mismatch for {key}")
    ohlcv = pd.read_parquet(ohlcv_path)
    evidence = pd.read_parquet(evidence_path)
    if "point_state" not in evidence.columns:
        raise RuntimeError("session evidence point_state is missing")
    evidence = evidence.loc[evidence["point_state"].eq("ACTIVE")].copy()
    if "regular_market_value" not in evidence.columns:
        raise RuntimeError("session evidence regular_market_value is missing")
    market = ohlcv.merge(
        evidence[["ticker", "session_date", "regular_market_value"]],
        on=["ticker", "session_date"],
        how="inner",
        validate="one_to_one",
    )
    if len(market) != len(ohlcv):
        raise RuntimeError(f"active market evidence is incomplete for {key}")
    market = _normalise_market(market)
    return market, {
        "session_date": key,
        "parent_manifest_path": str(context["parent_path"]),
        "parent_manifest_sha256": context["parent_sha"],
        "session_ohlcv_path": str(ohlcv_path),
        "session_ohlcv_sha256": expected_ohlcv_sha,
        "evidence_path": str(evidence_path),
        "evidence_sha256": expected_evidence_sha,
    }


def _read_verified_forward_flow(runtime_root: Path, key: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    context, sidecar, manifest_path = _verified_context(runtime_root, key)
    actual_sha = provenance_sha256_file(sidecar)
    frame = _normalise_flow(pd.read_parquet(sidecar))
    if set(frame["session_date"].dt.date.astype(str)) != {key}:
        raise RuntimeError(f"Foreign Flow sidecar date mismatch for {key}")
    return frame, {
        "session_date": key,
        "sidecar_path": str(sidecar),
        "sidecar_sha256": actual_sha,
        "manifest_path": str(manifest_path),
        "manifest_sha256": provenance_sha256_file(manifest_path),
    }


def _context_fingerprint(inputs: Mapping[str, Any]) -> str:
    payload = json.dumps(inputs, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return __import__("hashlib").sha256(payload).hexdigest()


def materialize_representation_v2_for_session(
    *,
    flow: pd.DataFrame,
    market: pd.DataFrame,
    security_master: pd.DataFrame,
    official_sessions: Iterable[object],
    source_session: str | pd.Timestamp,
    output_directory: str | Path,
    input_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one feature session immediately after a completed source session.

    ``source_session`` is the only completed market/flow session required.
    The next official date is represented in the calendar but deliberately
    need not have a session directory or any market/flow rows yet.
    """

    source = _date(source_session)
    sessions = pd.DatetimeIndex([_date(value) for value in official_sessions]).sort_values()
    if len(sessions) == 0 or sessions.has_duplicates or source not in set(sessions):
        raise RuntimeError("source is not in a unique official session calendar")
    position = int(sessions.get_loc(source))
    if position >= len(sessions) - 1:
        raise RuntimeError("source has no next official feature session")
    target = sessions[position + 1]
    flow = _normalise_flow(flow)
    market = _normalise_market(market)
    master = _normalise_master(security_master)
    if source not in set(market["session_date"]):
        raise RuntimeError("source canonical market session is missing")
    if source not in set(flow["session_date"]):
        raise RuntimeError("source canonical Foreign Flow session is missing")
    # Explicitly clip the inputs at t.  This makes the timing guarantee
    # structural even when a caller passes a larger cached frame.
    flow = flow.loc[flow["session_date"].le(source)].reset_index(drop=True)
    market = market.loc[market["session_date"].le(source)].reset_index(drop=True)

    context, excluded = build_causal_market_context(
        market[["ticker", "session_date", "close", "volume", "regular_market_value"]].rename(
            columns={"session_date": "date"}
        ),
        master,
        sessions,
    )
    volume = market[["ticker", "session_date", "volume"]].rename(
        columns={"session_date": "date", "volume": "raw_volume"}
    )
    features = build_foreign_flow_representation_v2(
        flow,
        volume,
        context,
        master,
        sessions,
    )
    features = features.loc[features["feature_session"].eq(target)].copy()
    if features.empty:
        raise RuntimeError("target representation has no listing-valid rows")
    if not features["flow_through_session"].eq(source).all():
        raise RuntimeError("representation violates t to t+1 causality")
    if features.duplicated(["ticker", "feature_session"]).any():
        raise RuntimeError("representation has duplicate target keys")
    for column in FEATURE_COLUMNS_V2:
        values = pd.to_numeric(features[column], errors="coerce").astype(float)
        if np.isinf(values.to_numpy()).any():
            raise RuntimeError(f"representation contains infinity: {column}")
        features[column] = values
    features = features[list(OUTPUT_COLUMNS_V2)].sort_values("ticker", kind="mergesort").reset_index(drop=True)

    numeric = features[list(FEATURE_COLUMNS_V2)].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric.to_numpy(dtype=float))
    feature_availability = {
        column: {"finite": int(finite[:, index].sum()), "missing": int((~finite[:, index]).sum())}
        for index, column in enumerate(FEATURE_COLUMNS_V2)
    }
    context_source = context.loc[context["date"].eq(source)]
    availability_counts = finite.sum(axis=1)
    diagnostics = {
        "official_session_index": position,
        "official_session_count": int(len(sessions)),
        "official_session_first": sessions[0].date().isoformat(),
        "official_session_last": sessions[-1].date().isoformat(),
        "source_session": source.date().isoformat(),
        "feature_session": target.date().isoformat(),
        "flow_rows_used": int(len(flow)),
        "market_rows_used": int(len(market)),
        "source_context_rows": int(len(context_source)),
        "source_primary_liquid_rows": int(context_source["universe_primary_liquid"].sum()),
        "excluded_listing_rows": int(len(excluded)),
        "fully_available_rows": int((availability_counts == len(FEATURE_COLUMNS_V2)).sum()),
        "partial_rows": int(((availability_counts > 0) & (availability_counts < len(FEATURE_COLUMNS_V2))).sum()),
        "all_missing_rows": int((availability_counts == 0).sum()),
        "feature_availability": feature_availability,
        "warmup_policy": "FEATURE_FORMULAS_DETERMINE_MISSINGNESS; NO_FORWARD_FILL",
    }

    directory = Path(output_directory).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    artifact = directory / REPRESENTATION_FILENAME
    manifest_path = directory / REPRESENTATION_MANIFEST_FILENAME
    # Keep provenance immutable and deterministic.  Only paths/hashes and
    # counts are recorded; no observed-retrieval time is re-labelled as a
    # historical publication timestamp.
    provenance = dict(input_provenance)
    provenance["feature_session"] = target.date().isoformat()
    provenance["flow_through_session"] = source.date().isoformat()
    provenance["excluded_listing_rows"] = int(len(excluded))
    provenance["input_fingerprint"] = _context_fingerprint(provenance)
    expected_artifact_sha: str
    if artifact.exists():
        existing = pd.read_parquet(artifact)
        if list(existing.columns) != list(features.columns) or not existing.equals(features):
            raise RuntimeError("immutable representation revision conflict")
        expected_artifact_sha = provenance_sha256_file(artifact)
    else:
        _write_parquet_exclusive(features, artifact)
        expected_artifact_sha = provenance_sha256_file(artifact)
    manifest = {
        "status": "FOREIGN_FLOW_REPRESENTATION_V2_FORWARD_READY",
        "schema": SCHEMA_VERSION,
        "feature_builder": "idx_trade.foreign_flow_features_v2.build_foreign_flow_representation_v2",
        "feature_columns": list(FEATURE_COLUMNS_V2),
        "output_columns": list(OUTPUT_COLUMNS_V2),
        "feature_session": target.date().isoformat(),
        "flow_through_session": source.date().isoformat(),
        "row_count": int(len(features)),
        "ticker_count": int(features["ticker"].nunique()),
        "diagnostics": diagnostics,
        "artifact_path": str(artifact),
        "artifact_sha256": expected_artifact_sha,
        "input_provenance": provenance,
        "outcome_blind": True,
        "fresh_forward_accessed": False,
        "outcomes_or_labels_accessed": False,
        "outcome_metrics_computed": False,
        "model_fit": False,
        "model_scoring": False,
        "provider_calls": 0,
        "publication_time_known": False,
        "observed_retrieval_is_not_publication_time": True,
        "prohibited_actions": {
            "fresh_forward_accessed": False,
            "outcomes_or_labels_accessed": False,
            "model_fit": False,
            "model_scoring": False,
        },
    }
    if manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing_manifest != manifest:
            raise RuntimeError("immutable representation manifest revision conflict")
        created = False
    else:
        _write_json_exclusive(manifest_path, manifest)
        created = True
    # Re-read and verify the pair after either create or idempotent reuse.
    stored_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if stored_manifest != manifest or provenance_sha256_file(artifact) != expected_artifact_sha:
        raise RuntimeError("representation artifact/manifest pair failed verification")
    return {
        "status": manifest["status"],
        "session_date": target.date().isoformat(),
        "flow_through_session": source.date().isoformat(),
        "created": created,
        "rows": int(len(features)),
        "tickers": int(features["ticker"].nunique()),
        "artifact_path": str(artifact),
        "artifact_sha256": expected_artifact_sha,
        "manifest_path": str(manifest_path),
        "manifest_sha256": provenance_sha256_file(manifest_path),
        "provider_calls": 0,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "excluded_listing_rows": int(len(excluded)),
    }


def _runtime_session_keys(runtime_root: Path, source: pd.Timestamp) -> list[str]:
    root = runtime_root / "forward_monitoring" / "sessions"
    if not root.is_dir():
        raise FileNotFoundError("forward monitoring sessions root is missing")
    keys: list[str] = []
    for directory in root.iterdir():
        if not directory.is_dir():
            continue
        try:
            key = _date(directory.name).date().isoformat()
        except ValueError:
            continue
        if _date(key) <= source:
            keys.append(key)
    return sorted(set(keys))


def produce_session_foreign_flow_representation_v2(
    *,
    runtime_root: str | Path,
    source_session: str | pd.Timestamp,
    archive_root: str | Path,
    archive_manifest_sha256: str,
    historical_panel_path: str | Path,
    historical_panel_sha256: str,
    official_sessions_path: str | Path,
    official_sessions_sha256: str,
    security_master_path: str | Path,
    security_master_sha256: str,
) -> dict[str, Any]:
    """Produce the next-session artifact immediately after source EOD ``t``."""

    runtime = Path(runtime_root).expanduser().resolve()
    source = _date(source_session)
    sessions_path = Path(official_sessions_path).expanduser().resolve()
    if not sessions_path.is_file() or provenance_sha256_file(sessions_path) != official_sessions_sha256.lower():
        raise RuntimeError("official session calendar missing or hash-mismatched")
    sessions = _session_index(sessions_path)
    if source not in set(sessions):
        raise RuntimeError("source session is absent from the supplied official calendar")
    source_position = int(sessions.get_loc(source))
    if source_position >= len(sessions) - 1:
        raise RuntimeError("source has no next official feature session")
    target = sessions[source_position + 1]

    archive_flow, archive_meta = read_verified_flow_archive(
        Path(archive_root).expanduser().resolve(), archive_manifest_sha256
    )
    panel_path = Path(historical_panel_path).expanduser().resolve()
    master_path = Path(security_master_path).expanduser().resolve()
    if provenance_sha256_file(panel_path) != historical_panel_sha256.lower():
        raise RuntimeError("historical market panel hash mismatch")
    if provenance_sha256_file(master_path) != security_master_sha256.lower():
        raise RuntimeError("security master hash mismatch")
    historical_panel = pd.read_parquet(panel_path)
    historical_panel = historical_panel.rename(columns={"date": "session_date"})
    historical_market = _normalise_market(historical_panel)
    master = _normalise_master(pd.read_csv(master_path))

    # The accepted historical flow archive extends beyond the pinned clean-V2
    # market window.  Those later rows are not historical context for this
    # producer; forward rows must come from canonical EOD session artifacts so
    # 2026-08-11/12 are never silently treated as repaired history.
    historical_cutoff = historical_market["session_date"].max()
    archive_flow = archive_flow.loc[
        _dates(archive_flow["session_date"], name="archive flow session date").le(historical_cutoff)
    ].copy()

    forward_flow_parts = [archive_flow]
    forward_market_parts = [historical_market]
    forward_sources: list[dict[str, Any]] = []
    # Only verified canonical sessions through the requested target are read.
    # No raw provider request or synthetic session is created here.
    runtime_keys = _runtime_session_keys(runtime, source)
    for key in runtime_keys:
        forward_market, market_meta = _read_verified_forward_market(runtime, key)
        forward_flow, flow_meta = _read_verified_forward_flow(runtime, key)
        forward_market_parts.append(forward_market)
        forward_flow_parts.append(forward_flow)
        forward_sources.append({"market": market_meta, "flow": flow_meta})

    market = _merge_unique(
        historical_market,
        pd.concat(forward_market_parts[1:], ignore_index=True) if len(forward_market_parts) > 1 else pd.DataFrame(),
        ["ticker", "session_date"],
        label="market context",
    )
    flow = _merge_unique(
        _normalise_flow(archive_flow),
        _normalise_flow(pd.concat(forward_flow_parts[1:], ignore_index=True))
        if len(forward_flow_parts) > 1
        else pd.DataFrame(),
        ["ticker", "session_date"],
        label="Foreign Flow context",
    )
    # Never allow artifacts after the completed source session to enter the
    # build, even if an archive already contains later captures.
    market = market.loc[
        market["session_date"].le(source) & market["session_date"].isin(set(sessions))
    ].reset_index(drop=True)
    flow = flow.loc[
        flow["session_date"].le(source) & flow["session_date"].isin(set(sessions))
    ].reset_index(drop=True)
    if not market["session_date"].isin(set(sessions)).all() or not flow["session_date"].isin(set(sessions)).all():
        raise RuntimeError("market or flow contains a date outside the supplied official calendar")

    extension_sessions = sessions[
        (sessions > historical_market["session_date"].max()) & (sessions <= source)
    ]
    available_market_sessions = set(market["session_date"])
    available_flow_sessions = set(flow["session_date"])
    missing_context = [
        day.date().isoformat()
        for day in extension_sessions
        if day not in available_market_sessions or day not in available_flow_sessions
    ]
    if missing_context:
        raise RuntimeError(
            "MISSING_FORWARD_ROLLING_CONTEXT_SESSIONS: " + ",".join(missing_context)
        )

    parent = _canonical_evidence(runtime, source.date().isoformat())["parent"]
    parent_calendar = Path(str(parent.get("calendar_path") or "")).expanduser().resolve()
    parent_calendar_sha = str(parent.get("calendar_sha256") or "").lower()
    if parent_calendar != sessions_path or parent_calendar_sha != official_sessions_sha256.lower():
        raise RuntimeError("producer calendar does not match canonical target-session calendar")
    provenance = {
        "archive": {
            key: archive_meta[key]
            for key in (
                "archive_root",
                "archive_manifest_path",
                "archive_manifest_sha256",
                "archive_normalized_session_count",
                "archive_normalized_row_count",
                "archive_normalized_artifact_count",
                "archive_normalized_first_session",
                "archive_normalized_last_session",
            )
        },
        "historical_panel_path": str(panel_path),
        "historical_panel_sha256": historical_panel_sha256.lower(),
        "official_sessions_path": str(sessions_path),
        "official_sessions_sha256": official_sessions_sha256.lower(),
        "security_master_path": str(master_path),
        "security_master_sha256": security_master_sha256.lower(),
        "forward_session_sources": forward_sources,
        "source_session": source.date().isoformat(),
        "feature_session": target.date().isoformat(),
        "rolling_context_policy": "PINNED_HISTORY_PLUS_VERIFIED_CANONICAL_FORWARD_SESSIONS",
        "no_provider_calls": True,
        "outcome_blind": True,
    }
    materialized = materialize_representation_v2_for_session(
        flow=flow,
        market=market,
        security_master=master,
        official_sessions=sessions,
        source_session=source,
        output_directory=runtime
        / "forward_monitoring"
        / "prospective"
        / "foreign_flow_representation_v2"
        / target.date().isoformat(),
        input_provenance=provenance,
    )
    materialized["setup_catchup"] = run_foreign_flow_catchup(runtime)
    return materialized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Produce one causal prospective Foreign Flow V2 session")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--source-session", required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--archive-manifest-sha256", required=True)
    parser.add_argument("--historical-panel", type=Path, required=True)
    parser.add_argument("--historical-panel-sha256", required=True)
    parser.add_argument("--official-sessions", type=Path, required=True)
    parser.add_argument("--official-sessions-sha256", required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--security-master-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = produce_session_foreign_flow_representation_v2(
        runtime_root=args.runtime_root,
        source_session=args.source_session,
        archive_root=args.archive_root,
        archive_manifest_sha256=args.archive_manifest_sha256,
        historical_panel_path=args.historical_panel,
        historical_panel_sha256=args.historical_panel_sha256,
        official_sessions_path=args.official_sessions,
        official_sessions_sha256=args.official_sessions_sha256,
        security_master_path=args.security_master,
        security_master_sha256=args.security_master_sha256,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
