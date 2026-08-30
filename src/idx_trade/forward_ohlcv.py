"""Outcome-blind OHLCV enrichment for forward monitoring sessions.

The frozen ``model_input.parquet`` contract intentionally remains H/L/C/V only.
This module keeps Open in a separate, provenance-bearing sibling artifact and
supports local-first enrichment of legacy sessions without rewriting them.
"""

from __future__ import annotations

from io import BytesIO
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .data import canonicalize_ohlcv
from .price_backfill import _download_in_batches
from .provenance import sha256_file, write_manifest_atomic
from .providers.yahoo import download_daily


MODEL_INPUT_COLUMNS = (
    "ticker",
    "date",
    "high",
    "low",
    "close",
    "volume",
    "regular_market_value",
)

SESSION_OHLCV_COLUMNS = (
    "ticker",
    "session_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source",
    "source_ref",
    "source_sha256",
    "observed_retrieved_at_utc",
)


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def validate_model_input_regular_market_value(model_input: pd.DataFrame) -> None:
    """Reject non-finite or negative market values before V4 feature admission."""

    if "regular_market_value" not in model_input.columns:
        return
    values = pd.to_numeric(model_input["regular_market_value"], errors="coerce").astype(float)
    valid = np.isfinite(values) & values.ge(0.0)
    if not valid.all():
        raise ValueError("model input regular_market_value must be finite and non-negative")


def provider_row_evidence_sha256(
    ticker: str,
    session_date: str | pd.Timestamp,
    row: Mapping[str, object],
) -> str:
    """Hash the normalized provider row when no raw provider byte blob exists."""

    values = {
        "ticker": str(ticker).upper(),
        "session_date": pd.Timestamp(session_date).normalize().date().isoformat(),
        "open": float(row["raw_open"] if "raw_open" in row else row["open"]),
        "high": float(row["raw_high"] if "raw_high" in row else row["high"]),
        "low": float(row["raw_low"] if "raw_low" in row else row["low"]),
        "close": float(row["raw_close"] if "raw_close" in row else row["close"]),
        "volume": float(row["raw_volume"] if "raw_volume" in row else row["volume"]),
    }
    encoded = json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _numeric(row: Mapping[str, object], *names: str) -> float:
    for name in names:
        if name in row:
            value = pd.to_numeric(pd.Series([row[name]]), errors="coerce").iloc[0]
            if pd.notna(value):
                return float(value)
    raise ValueError(f"provider OHLCV field missing or invalid: {names}")


def _normalized_row(
    ticker: str,
    session_date: str | pd.Timestamp,
    row: Mapping[str, object],
    *,
    source: str,
    source_ref: str,
    source_sha256: str,
    observed_retrieved_at_utc: str | None,
) -> dict[str, object]:
    result = {
        "ticker": str(ticker).upper().strip(),
        "session_date": pd.Timestamp(session_date).normalize(),
        "open": _numeric(row, "raw_open", "open"),
        "high": _numeric(row, "raw_high", "high"),
        "low": _numeric(row, "raw_low", "low"),
        "close": _numeric(row, "raw_close", "close"),
        "volume": _numeric(row, "raw_volume", "volume"),
        "source": source,
        "source_ref": source_ref,
        "source_sha256": source_sha256,
        "observed_retrieved_at_utc": observed_retrieved_at_utc,
    }
    prices = [result[name] for name in ("open", "high", "low", "close")]
    if not all(np.isfinite(value) and value > 0 for value in prices):
        raise ValueError(f"invalid positive OHLC values for {ticker}")
    if not np.isfinite(result["volume"]) or result["volume"] < 0:
        raise ValueError(f"invalid non-negative volume for {ticker}")
    if result["low"] > min(result["open"], result["close"]):
        raise ValueError(f"low is above open/close for {ticker}")
    if result["high"] < max(result["open"], result["close"]):
        raise ValueError(f"high is below open/close for {ticker}")
    return result


def _canonical_provider_row(
    frame: pd.DataFrame,
    ticker: str,
    session_date: pd.Timestamp,
) -> dict[str, object] | None:
    if frame.empty or "date" not in frame.columns:
        return None
    dates = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    selected = frame.loc[dates.eq(pd.Timestamp(session_date).normalize())].copy()
    if selected.empty:
        return None
    for raw, regular in (
        ("raw_open", "open"),
        ("raw_high", "high"),
        ("raw_low", "low"),
        ("raw_close", "close"),
        ("raw_volume", "volume"),
    ):
        if raw in selected.columns:
            selected[regular] = selected[raw]
    canonical = canonicalize_ohlcv(selected, ticker)
    if canonical.empty:
        return None
    if len(canonical) != 1:
        raise ValueError(f"provider OHLCV has ambiguous session identity for {ticker}")
    return canonical.iloc[0].to_dict()


def validate_ohlcv_against_model_input(
    ohlcv: pd.DataFrame,
    model_input: pd.DataFrame,
    session_date: str | pd.Timestamp,
    *,
    compare_volume: bool = True,
) -> None:
    """Require exact ticker/date identity and provider H/L/C agreement.

    Canonical captures use ``compare_volume=True`` because the model-input and
    sibling artifact are created from the same provider payload. Legacy Open
    repair uses ``False``: the frozen model input must not be rewritten when a
    later provider retrieval revises volume, while H/L/C identity remains a
    hard safety gate for the recovered Open row.
    """

    missing = set(SESSION_OHLCV_COLUMNS) - set(ohlcv.columns)
    if missing:
        raise ValueError(f"session OHLCV columns missing: {sorted(missing)}")
    missing_model = set(MODEL_INPUT_COLUMNS) - set(model_input.columns)
    if missing_model:
        raise ValueError(f"model input columns missing: {sorted(missing_model)}")
    requested = pd.Timestamp(session_date).normalize()
    left = ohlcv.copy()
    left["session_date"] = pd.to_datetime(left["session_date"], errors="coerce").dt.normalize()
    right = model_input.copy()
    right["date"] = pd.to_datetime(right["date"], errors="coerce").dt.normalize()
    if left["session_date"].isna().any() or not left["session_date"].eq(requested).all():
        raise ValueError("session OHLCV contains an invalid or mismatched session date")
    if right["date"].isna().any() or not right["date"].eq(requested).all():
        raise ValueError("model input contains an invalid or mismatched session date")
    if left["ticker"].duplicated().any() or right["ticker"].duplicated().any():
        raise ValueError("duplicate ticker in session OHLCV/model input")
    if set(left["ticker"]) != set(right["ticker"]):
        raise ValueError("session OHLCV ticker set disagrees with model input")
    merged = right.merge(
        left[["ticker", "open", "high", "low", "close", "volume"]].rename(
            columns={
                "open": "provider_open",
                "high": "provider_high",
                "low": "provider_low",
                "close": "provider_close",
                "volume": "provider_volume",
            }
        ),
        on="ticker",
        how="left",
        validate="one_to_one",
    )
    fields = ["high", "low", "close"]
    if compare_volume:
        fields.append("volume")
    for name in fields:
        if not np.isclose(
            pd.to_numeric(merged[name], errors="coerce"),
            pd.to_numeric(merged[f"provider_{name}"], errors="coerce"),
            rtol=1e-10,
            atol=1e-10,
            equal_nan=False,
        ).all():
            raise ValueError(f"session OHLCV {name} disagrees with model input")


def build_session_ohlcv(price_rows: Mapping[str, Mapping[str, object]]) -> pd.DataFrame:
    rows = [dict(row, ticker=str(ticker).upper()) for ticker, row in price_rows.items()]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=SESSION_OHLCV_COLUMNS)
    if "session_date" not in frame.columns and "date" in frame.columns:
        frame["session_date"] = frame["date"]
    missing = set(SESSION_OHLCV_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"price payload missing OHLCV provenance columns: {sorted(missing)}")
    return frame.loc[:, SESSION_OHLCV_COLUMNS].sort_values("ticker").reset_index(drop=True)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def write_immutable_ohlcv(frame: pd.DataFrame, path: Path) -> str:
    """Create a sibling parquet artifact once and reject byte revisions."""

    payload = _parquet_bytes(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable session OHLCV revision conflict: {path}")
    else:
        with path.open("xb") as destination:
            destination.write(payload)
    return sha256_file(path)


def _local_provider_row(
    raw_path: Path,
    ticker: str,
    session_date: pd.Timestamp,
) -> dict[str, object] | None:
    if not raw_path.exists():
        return None
    frame = pd.read_parquet(raw_path)
    row = _canonical_provider_row(frame, ticker, session_date)
    if row is None:
        return None
    return _normalized_row(
        ticker,
        session_date,
        row,
        source="YAHOO_YFINANCE_RAW_OHLCV",
        source_ref=f"https://finance.yahoo.com/quote/{ticker}.JK/history",
        source_sha256=sha256_file(raw_path),
        observed_retrieved_at_utc=None,
    )


def enrich_session_ohlcv(
    runtime_root: str | Path,
    session_date: str | pd.Timestamp,
    *,
    fetch_missing: bool = False,
    batch_size: int = 100,
) -> dict[str, Any]:
    """Local-first enrichment for a legacy DATA_READY session.

    Network recovery is opt-in. The default audit path never fetches and never
    writes an incomplete canonical artifact.
    """

    root = Path(runtime_root).expanduser().resolve()
    session = pd.Timestamp(session_date).normalize()
    session_key = session.date().isoformat()
    session_dir = root / "forward_monitoring" / "sessions" / session_key
    snapshot_path = session_dir / "model_input.parquet"
    manifest_path = session_dir / "manifest.json"
    if not snapshot_path.exists() or not manifest_path.exists():
        raise FileNotFoundError(f"legacy DATA_READY artifacts missing for {session_key}")
    model_input = pd.read_parquet(snapshot_path)
    raw_root = root / "prices" / "raw"
    accepted: dict[str, dict[str, object]] = {}
    diagnostics: list[dict[str, object]] = []
    missing_tickers: list[str] = []
    for ticker in sorted(model_input["ticker"].astype(str).str.upper().unique()):
        try:
            row = _local_provider_row(raw_root / f"{ticker}.parquet", ticker, session)
        except Exception as error:
            missing_tickers.append(ticker)
            diagnostics.append({"ticker": ticker, "status": "INVALID_LOCAL_ROW", "detail": str(error)})
            continue
        if row is None:
            missing_tickers.append(ticker)
            diagnostics.append({"ticker": ticker, "status": "MISSING_LOCAL_ROW"})
        else:
            accepted[ticker] = row

    if fetch_missing and missing_tickers:
        downloaded, errors = _download_in_batches(
            missing_tickers,
            session.date().isoformat(),
            (session + pd.Timedelta(days=1)).date().isoformat(),
            downloader=download_daily,
            batch_size=batch_size,
        )
        observed = _utc_now()
        for ticker in missing_tickers:
            if ticker in errors:
                diagnostics.append({"ticker": ticker, "status": "DOWNLOAD_ERROR", "detail": errors[ticker]})
                continue
            frame = downloaded.get(ticker, pd.DataFrame())
            try:
                row = _canonical_provider_row(frame, ticker, session)
            except ValueError as error:
                diagnostics.append({"ticker": ticker, "status": "INVALID_PROVIDER_ROW", "detail": str(error)})
                continue
            if row is None:
                diagnostics.append({"ticker": ticker, "status": "NO_PROVIDER_ROWS"})
                continue
            try:
                accepted[ticker] = _normalized_row(
                    ticker,
                    session,
                    row,
                    source="YAHOO_YFINANCE_AUTO_ADJUST_FALSE",
                    source_ref=f"https://finance.yahoo.com/quote/{ticker}.JK/history",
                    source_sha256=provider_row_evidence_sha256(ticker, session, row),
                    observed_retrieved_at_utc=observed,
                )
            except ValueError as error:
                diagnostics.append({"ticker": ticker, "status": "INVALID_PROVIDER_ROW", "detail": str(error)})

    frame = pd.DataFrame(list(accepted.values()), columns=SESSION_OHLCV_COLUMNS)
    if not frame.empty:
        frame = frame.sort_values("ticker").reset_index(drop=True)
    missing_after = sorted(set(model_input["ticker"].astype(str).str.upper()) - set(accepted))
    result: dict[str, Any] = {
        "status": "OPEN_COMPLETE" if not missing_after else "OPEN_INCOMPLETE",
        "session_date": session_key,
        "requested_rows": len(model_input),
        "accepted_rows": len(frame),
        "missing_rows": len(missing_after),
        "missing_tickers": missing_after,
        "diagnostics": diagnostics,
        "fetch_missing": fetch_missing,
        "historical_publication_time_claim": False,
    }
    if missing_after:
        return result

    validate_ohlcv_against_model_input(frame, model_input, session, compare_volume=False)
    artifact_path = session_dir / "session_ohlcv.parquet"
    artifact_sha = write_immutable_ohlcv(frame, artifact_path)
    original_manifest_sha = sha256_file(manifest_path)
    enrichment_manifest = {
        "schema_version": 1,
        "status": "OPEN_COMPLETE",
        "session_date": session_key,
        "session_ohlcv_path": str(artifact_path),
        "session_ohlcv_sha256": artifact_sha,
        "original_manifest_path": str(manifest_path),
        "original_manifest_sha256": original_manifest_sha,
        "requested_rows": len(model_input),
        "accepted_rows": len(frame),
        "recovered_at_utc": _utc_now(),
        "observed_retrieved_at_utc_is_not_historical_publication_time": True,
        "source_counts": frame["source"].value_counts().to_dict(),
        "volume_reconciliation": "NOT_REQUIRED_FOR_LEGACY_OPEN_REPAIR",
        "source_artifact_sha256": {
            str(path): sha256_file(path)
            for path in sorted(raw_root.glob("*.parquet"))
            if path.stem.upper() in set(frame["ticker"])
        },
    }
    enrichment_path = session_dir / "open_enrichment_manifest.json"
    if enrichment_path.exists():
        existing = json.loads(enrichment_path.read_text(encoding="utf-8"))
        if existing != enrichment_manifest:
            raise RuntimeError(f"immutable Open enrichment manifest conflict: {enrichment_path}")
    else:
        write_manifest_atomic(enrichment_path, enrichment_manifest)
    result.update(
        {
            "session_ohlcv_path": str(artifact_path),
            "session_ohlcv_sha256": artifact_sha,
            "enrichment_manifest_path": str(enrichment_path),
            "enrichment_manifest_sha256": sha256_file(enrichment_path),
        }
    )
    return result
