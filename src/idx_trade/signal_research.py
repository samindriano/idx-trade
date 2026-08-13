from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from .provenance import environment_manifest, sha256_file, write_manifest_atomic
from .storage import write_parquet_atomic


EXECUTION_GRADE_OHLCV = "EXECUTION_GRADE_OHLCV"
SIGNAL_RESEARCH_HLCV = "SIGNAL_RESEARCH_HLCV"


def _normalise_ticker(value: object) -> str:
    return str(value).upper().replace(".JK", "").strip()


def _normalise_dates(values: Iterable[object]) -> pd.DatetimeIndex:
    return (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .tz_localize(None)
        .normalize()
        .dropna()
        .unique()
        .sort_values()
    )


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def validate_signal_research_hlcv(frame: pd.DataFrame) -> bool:
    """Validate the Open-optional, official-ACTIVE HLCV research contract."""

    required = {
        "ticker",
        "date",
        "high",
        "low",
        "close",
        "volume",
        "price_provenance",
        "open_available",
        "open_evidence_status",
        "corporate_action_integrity_verified",
        "signal_contract",
    }
    if frame.empty or not required.issubset(frame.columns):
        return False

    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if data["date"].isna().any() or data.duplicated(["ticker", "date"]).any():
        return False
    if data["price_provenance"].fillna("").astype(str).str.strip().eq("").any():
        return False
    if data["open_evidence_status"].fillna("").astype(str).str.strip().eq("").any():
        return False
    if not data["corporate_action_integrity_verified"].astype(bool).all():
        return False
    if not data["signal_contract"].eq(SIGNAL_RESEARCH_HLCV).all():
        return False

    numeric = data[["high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not (numeric > 0).all().all():
        return False
    if not (
        (numeric["high"] >= numeric[["low", "close"]].max(axis=1))
        & (numeric["low"] <= numeric[["high", "close"]].min(axis=1))
    ).all():
        return False

    open_values = pd.to_numeric(data["open"], errors="coerce") if "open" in data else pd.Series(pd.NA, index=data.index)
    available = data["open_available"].astype(bool)
    if available.any() and (open_values[available].isna() | open_values[available].le(0)).any():
        return False
    if data.loc[~available, "open"].notna().any():
        return False
    if not data.loc[available, "open_evidence_status"].astype(str).str.contains("OPTIONAL").all():
        return False
    if not data.loc[~available, "open_evidence_status"].astype(str).str.contains("UNAVAILABLE|NOT_RECONCILED").all():
        return False
    return True


def _optional_open(
    official: pd.DataFrame,
    raw: pd.DataFrame | None,
) -> pd.DataFrame:
    result = official[["date", "high", "low"]].copy()
    result["open"] = pd.NA
    result["open_evidence_status"] = "OPEN_UNAVAILABLE"

    if "open" in official.columns:
        official_open = pd.to_numeric(official["open"], errors="coerce")
        valid = official_open.gt(0) & official_open.between(
            pd.to_numeric(official["low"], errors="coerce"),
            pd.to_numeric(official["high"], errors="coerce"),
        )
        result.loc[valid, "open"] = official_open.loc[valid]
        result.loc[valid, "open_evidence_status"] = "IDX_PUBLIC_STOCK_SUMMARY_OPEN_OPTIONAL"

    if raw is None or raw.empty:
        result["open_available"] = False
        return result

    raw_data = raw.copy()
    raw_data["date"] = pd.to_datetime(raw_data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    raw_column = "raw_open" if "raw_open" in raw_data.columns else "open"
    if raw_column not in raw_data.columns:
        result["open_available"] = False
        return result
    raw_data["_optional_open"] = pd.to_numeric(raw_data[raw_column], errors="coerce")
    raw_data = raw_data.drop_duplicates("date", keep="last").set_index("date")
    result = result.set_index("date")
    candidate = result.index.to_series().map(raw_data["_optional_open"] if "_optional_open" in raw_data else pd.Series(dtype=float))
    valid_raw = candidate.gt(0) & candidate.between(
        pd.to_numeric(result["low"], errors="coerce"),
        pd.to_numeric(result["high"], errors="coerce"),
    )
    fill = valid_raw & result["open"].isna()
    result.loc[fill, "open"] = candidate.loc[fill]
    result.loc[fill, "open_evidence_status"] = "YAHOO_RAW_OPTIONAL"
    result["open_available"] = result["open"].notna()
    return result.reset_index()


def build_signal_research_hlcv_panel(
    official_frames: Mapping[str, pd.DataFrame],
    required_tickers: Iterable[str],
    active_sessions: Mapping[str, Iterable[object]],
    *,
    raw_price_frames: Mapping[str, pd.DataFrame] | None = None,
    corporate_action_verified: Mapping[str, bool] | None = None,
) -> pd.DataFrame:
    """Build an ACTIVE-only signal panel with nullable, never-synthesized Open.

    The official frames supply High/Low/Close/Volume and provenance. Provider
    raw frames may supply an optional Open only when it is positive and within
    the official High/Low envelope. This function is intentionally separate
    from the strict execution-grade model-safe panel and never changes its
    gate or raw-price semantics.
    """

    tickers = sorted({_normalise_ticker(value) for value in required_tickers})
    action_flags = corporate_action_verified or {}
    panels: list[pd.DataFrame] = []

    for ticker in tickers:
        expected = _normalise_dates(active_sessions.get(ticker, []))
        if not len(expected):
            continue
        official = official_frames.get(ticker, pd.DataFrame()).copy()
        if official.empty or "date" not in official.columns:
            raise ValueError(f"Missing official signal HLCV evidence for {ticker}")
        official["date"] = pd.to_datetime(official["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
        official["ticker"] = ticker
        if official["date"].duplicated().any():
            raise ValueError(f"Duplicate official signal HLCV dates for {ticker}")
        missing = sorted(set(expected) - set(official["date"].dropna()))
        if missing:
            dates = ", ".join(pd.Timestamp(value).date().isoformat() for value in missing[:5])
            raise ValueError(f"Missing official signal HLCV sessions for {ticker}: {dates}")
        official = official[official["date"].isin(expected)].copy()
        if "regular_market_value" not in official.columns:
            official["regular_market_value"] = official.get("regular_value", pd.NA)
        if "price_provenance" not in official.columns:
            official["price_provenance"] = official.get("source", "IDX_PUBLIC_STOCK_SUMMARY")
        if "open" not in official.columns:
            official["open"] = pd.NA

        open_frame = _optional_open(official, (raw_price_frames or {}).get(ticker))
        data = official[["ticker", "date", "high", "low", "close", "volume", "regular_market_value", "price_provenance"]].merge(
            open_frame[["date", "open", "open_available", "open_evidence_status"]],
            on="date",
            how="left",
            validate="one_to_one",
        )
        data["corporate_action_integrity_verified"] = bool(action_flags.get(ticker, False))
        if not data["corporate_action_integrity_verified"].all():
            raise ValueError(f"Corporate-action integrity is not verified for {ticker}")
        data["signal_contract"] = SIGNAL_RESEARCH_HLCV
        panels.append(data)

    if not panels:
        return pd.DataFrame(
            columns=[
                "ticker", "date", "open", "high", "low", "close", "volume",
                "regular_market_value", "price_provenance", "open_available",
                "open_evidence_status", "corporate_action_integrity_verified",
                "signal_contract",
            ]
        )
    panel = pd.concat(panels, ignore_index=True, sort=False)
    panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)
    if not validate_signal_research_hlcv(panel):
        raise ValueError("Signal-research HLCV panel violates its contract")
    return panel


def write_signal_research_hlcv_panel(
    panel: pd.DataFrame,
    output_path: str | Path,
) -> dict[str, object]:
    """Persist a previously validated signal-research HLCV panel."""

    if not validate_signal_research_hlcv(panel):
        raise ValueError("Cannot write an invalid signal-research HLCV panel")
    path = Path(output_path)
    write_parquet_atomic(panel, path)
    return {
        "path": str(path),
        "rows": int(len(panel)),
        "tickers": int(panel["ticker"].nunique()),
        "first_date": pd.Timestamp(panel["date"].min()).date().isoformat(),
        "last_date": pd.Timestamp(panel["date"].max()).date().isoformat(),
        "null_open_rows": int(panel["open"].isna().sum()),
        "null_open_percentage": float(panel["open"].isna().mean() * 100.0),
        "contract": SIGNAL_RESEARCH_HLCV,
    }


def create_signal_research_snapshot_manifest(
    research_summary: Mapping[str, object],
    artifacts: Mapping[str, str | Path],
    *,
    code_commit: str,
    output_path: str | Path,
    metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Create a hash manifest for a GO signal-research snapshot.

    This is deliberately separate from strict certified-snapshot manifests:
    strict execution-grade certification must remain impossible while the
    strict gate is failing, even when the Open-optional research contract GO
    criteria are satisfied.
    """

    if str(research_summary.get("signal_research_decision", "")) != "GO":
        raise RuntimeError("Cannot create a signal-research manifest from a non-GO diagnostic")
    if int(research_summary.get("unknown_expected_active_intersection", -1)) != 0:
        raise RuntimeError("Cannot create a signal-research manifest with UNKNOWN/ACTIVE overlap")
    if not artifacts:
        raise ValueError("At least one signal-research artifact is required")
    commit = str(code_commit).strip()
    if not commit:
        raise ValueError("code_commit is required for a signal-research manifest")

    hashes: dict[str, str] = {}
    paths: dict[str, str] = {}
    for logical_name, raw_path in sorted(artifacts.items()):
        name = str(logical_name).strip()
        path = Path(raw_path)
        if not name:
            raise ValueError("Signal-research artifact names must be non-empty")
        if not path.is_file():
            raise FileNotFoundError(f"Signal-research artifact missing: {path}")
        hashes[name] = sha256_file(path)
        paths[name] = str(path)

    manifest = {
        "snapshot_schema_version": 1,
        "manifest_type": "SIGNAL_RESEARCH_1260",
        "code_commit": commit,
        "research_contract": SIGNAL_RESEARCH_HLCV,
        "strict_execution_grade_contract": EXECUTION_GRADE_OHLCV,
        "research_summary": dict(research_summary),
        "artifacts": {
            name: {"path": paths[name], "sha256": hashes[name]}
            for name in sorted(hashes)
        },
        "metadata": dict(metadata or {}),
        "reproducibility": environment_manifest(
            config={
                "code_commit": commit,
                "contract": SIGNAL_RESEARCH_HLCV,
                "window_start": research_summary.get("window_start"),
                "window_end": research_summary.get("window_end"),
            },
            data_snapshots=hashes,
        ),
    }
    write_manifest_atomic(Path(output_path), manifest)
    return manifest


def verify_signal_research_snapshot_manifest(manifest: Mapping[str, object]) -> dict[str, object]:
    """Verify every artifact hash in a signal-research manifest."""

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping) or not artifacts:
        raise ValueError("Signal-research manifest has no artifacts")
    mismatches: list[dict[str, object]] = []
    verified = 0
    for logical_name, raw in artifacts.items():
        if not isinstance(raw, Mapping):
            mismatches.append({"artifact": str(logical_name), "status": "INVALID_MANIFEST_ENTRY"})
            continue
        path = Path(str(raw.get("path", "")))
        expected = str(raw.get("sha256", ""))
        if not path.is_file():
            mismatches.append({"artifact": str(logical_name), "status": "MISSING", "path": str(path)})
            continue
        actual = sha256_file(path)
        if actual != expected:
            mismatches.append(
                {
                    "artifact": str(logical_name),
                    "status": "HASH_MISMATCH",
                    "path": str(path),
                    "expected": expected,
                    "actual": actual,
                }
            )
            continue
        verified += 1
    return {
        "valid": not mismatches,
        "verified_artifacts": verified,
        "artifact_count": len(artifacts),
        "mismatches": mismatches,
    }
