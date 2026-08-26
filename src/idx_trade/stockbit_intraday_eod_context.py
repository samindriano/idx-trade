from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

import pandas as pd

from .provenance import sha256_file
from .security_master import normalise_ticker
from .stockbit_intraday_eod_gate import (
    StockbitIntradayGateError,
    VerifiedEodGate,
    load_verified_eod_gate,
)


@dataclass(frozen=True)
class VerifiedIntradayEodContext:
    session_date: str
    session_dir: Path
    eod_manifest_sha256: str
    universe_evidence_path: Path
    universe_evidence_sha256: str
    universe: pd.DataFrame
    gate: VerifiedEodGate


def _manifest(root: Path) -> tuple[dict[str, object], str]:
    path = root / "manifest.json"
    if not path.is_file():
        raise StockbitIntradayGateError("EOD_CONTEXT_MANIFEST_MISSING")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StockbitIntradayGateError("EOD_CONTEXT_MANIFEST_INVALID") from exc
    if not isinstance(value, dict):
        raise StockbitIntradayGateError("EOD_CONTEXT_MANIFEST_NOT_OBJECT")
    return value, sha256_file(path)


def load_verified_intraday_eod_context(
    session_dir: str | Path,
    *,
    expected_date: date,
    expected_manifest_sha256: str | None = None,
) -> VerifiedIntradayEodContext:
    """Use canonical EOD session evidence as the only cloud intraday universe."""

    root = Path(session_dir).expanduser().resolve()
    manifest, manifest_sha = _manifest(root)
    session = expected_date.isoformat()
    if manifest.get("status") != "DATA_READY" or manifest.get("session_date") != session:
        raise StockbitIntradayGateError("EOD_CONTEXT_NOT_DATA_READY")
    if expected_manifest_sha256 is not None:
        expected = str(expected_manifest_sha256).strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected) or manifest_sha != expected:
            raise StockbitIntradayGateError("EOD_CONTEXT_MANIFEST_SHA_MISMATCH")

    evidence_path = root / "session_evidence.parquet"
    declared_evidence_sha = str(manifest.get("evidence_sha256") or "").strip().lower()
    if (
        not re.fullmatch(r"[0-9a-f]{64}", declared_evidence_sha)
        or not evidence_path.is_file()
        or sha256_file(evidence_path) != declared_evidence_sha
    ):
        raise StockbitIntradayGateError("EOD_CONTEXT_EVIDENCE_SHA_MISMATCH")

    evidence = pd.read_parquet(evidence_path)
    required = {"ticker", "session_date"}
    if evidence.empty or required - set(evidence.columns):
        raise StockbitIntradayGateError("EOD_CONTEXT_EVIDENCE_SCHEMA_INVALID")
    dates = pd.to_datetime(evidence["session_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if dates.isna().any() or not dates.eq(pd.Timestamp(expected_date)).all():
        raise StockbitIntradayGateError("EOD_CONTEXT_EVIDENCE_DATE_MISMATCH")

    tickers = evidence["ticker"].map(normalise_ticker).astype(str).str.upper().str.strip()
    if tickers.eq("").any() or not tickers.str.fullmatch(r"[A-Z0-9]{4}").all():
        raise StockbitIntradayGateError("EOD_CONTEXT_EVIDENCE_TICKER_INVALID")
    if tickers.duplicated().any():
        raise StockbitIntradayGateError("EOD_CONTEXT_EVIDENCE_TICKER_DUPLICATE")
    universe = pd.DataFrame({"ticker": tickers}).sort_values("ticker").reset_index(drop=True)

    declared_rows = manifest.get("point_evidence_rows")
    declared_listed = manifest.get("listed_tickers")
    try:
        if int(declared_rows) != len(universe) or int(declared_listed) != len(universe):
            raise StockbitIntradayGateError("EOD_CONTEXT_UNIVERSE_ROW_COUNT_MISMATCH")
    except (TypeError, ValueError) as exc:
        if isinstance(exc, StockbitIntradayGateError):
            raise
        raise StockbitIntradayGateError("EOD_CONTEXT_UNIVERSE_ROW_COUNT_INVALID") from exc

    gate = load_verified_eod_gate(
        root,
        expected_date=expected_date,
        universe=universe,
        expected_manifest_sha256=manifest_sha,
    )
    return VerifiedIntradayEodContext(
        session_date=session,
        session_dir=root,
        eod_manifest_sha256=manifest_sha,
        universe_evidence_path=evidence_path,
        universe_evidence_sha256=declared_evidence_sha,
        universe=universe,
        gate=gate,
    )
