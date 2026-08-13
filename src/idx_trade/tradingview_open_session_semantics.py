"""Offline and bounded live forensics for TradingView IDX session semantics.

This module is an audit harness only. It never rewrites canonical prices or
changes the frozen TradingView admission verdict.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd


UTC = timezone.utc
WIB = ZoneInfo("Asia/Jakarta")
REQUIRED_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
REQUIRED_UPSTREAM_COMMIT = "5baea86c8c7e576f13464919c86c3b4c4b0ecf4c"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n").encode("utf-8")


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _wib_timestamp(epoch: Any) -> tuple[str | None, str | None]:
    try:
        instant = datetime.fromtimestamp(int(epoch), tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None, None
    return instant.isoformat(), instant.astimezone(WIB).isoformat()


def _raw_files(admission_root: Path) -> list[Path]:
    return sorted((admission_root / "raw" / "mathieu").glob("*.json"))


def inspect_market_info(admission_root: Path) -> pd.DataFrame:
    """Extract stored chart.info/session metadata and raw period boundaries."""
    rows: list[dict[str, Any]] = []
    for path in _raw_files(admission_root):
        payload = json.loads(path.read_text(encoding="utf-8"))
        request = payload.get("request") or {}
        response = payload.get("response") or {}
        info = response.get("market_info") or {}
        periods = response.get("periods") or []
        epochs = [p.get("time") for p in periods if isinstance(p, dict) and isinstance(p.get("time"), (int, float))]
        first_utc, first_wib = _wib_timestamp(min(epochs)) if epochs else (None, None)
        last_utc, last_wib = _wib_timestamp(max(epochs)) if epochs else (None, None)
        rows.append({
            "file": path.name,
            "ticker": request.get("ticker"),
            "phase": request.get("phase"),
            "era": request.get("era"),
            "timeframe": str(request.get("timeframe")),
            "server": response.get("server", request.get("server")),
            "status": response.get("status"),
            "market_info_present": bool(info),
            "timezone": info.get("timezone"),
            "session": info.get("session"),
            "session_display": info.get("session_display"),
            "subsession_id": info.get("subsession_id"),
            "subsessions": json.dumps(info.get("subsessions"), ensure_ascii=False, sort_keys=True),
            "has_extended_hours": _as_bool(info.get("has_extended_hours")),
            "has_intraday": _as_bool(info.get("has_intraday")),
            "bar_source": info.get("bar_source"),
            "bar_fillgaps": _as_bool(info.get("bar_fillgaps")),
            "exchange": info.get("exchange"),
            "pro_name": info.get("pro_name"),
            "raw_period_count": len(periods),
            "first_raw_epoch": min(epochs) if epochs else None,
            "last_raw_epoch": max(epochs) if epochs else None,
            "first_raw_timestamp_utc": first_utc,
            "first_raw_timestamp_wib": first_wib,
            "last_raw_timestamp_utc": last_utc,
            "last_raw_timestamp_wib": last_wib,
            "event_trace": json.dumps(response.get("event_trace") or [], sort_keys=True),
        })
    return pd.DataFrame(rows)


def _load_panel_previous_close(panel: Path) -> pd.DataFrame:
    frame = pd.read_parquet(panel, columns=["ticker", "date", "close"])
    frame["ticker"] = frame["ticker"].astype(str).str.upper()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"], keep="last")
    frame["previous_canonical_close"] = frame.groupby("ticker", sort=False)["close"].shift(1)
    return frame[["ticker", "date", "previous_canonical_close"]]


def build_session_forensics(admission_root: Path, panel: Path) -> pd.DataFrame:
    """Reconcile stored TV60 first bars, TV1D, canonical values, and prior close."""
    bars = pd.read_csv(admission_root / "normalized" / "mathieu_intraday_bars.csv", low_memory=False)
    bars = bars[(bars["phase"] == "fixed_60m") & (bars["timeframe"].astype(str) == "60")].copy()
    bars["session_admissible"] = bars["session_admissible"].astype(str).str.lower().eq("true")
    bars = bars[bars["in_requested_window"].astype(str).str.lower().eq("true") & bars["session_admissible"]]
    bars["raw_epoch"] = pd.to_numeric(bars["raw_epoch"], errors="coerce")
    bars = bars.dropna(subset=["raw_epoch"]).sort_values(["ticker", "session_date", "raw_epoch"])
    grouped = bars.groupby(["ticker", "session_date"], sort=True)
    first = grouped.head(2).copy()
    first["bar_rank"] = first.groupby(["ticker", "session_date"]).cumcount() + 1
    first_wide = first.pivot(index=["ticker", "session_date"], columns="bar_rank", values=["raw_epoch", "timestamp_wib", "open", "high", "low", "close", "volume"])
    first_wide.columns = [f"{field}_bar{rank}" for field, rank in first_wide.columns]
    first_wide = first_wide.reset_index()
    counts = grouped.size().rename("tv60_bar_count").reset_index()
    result = counts.merge(first_wide, on=["ticker", "session_date"], how="left")
    result["first_second_gap_minutes"] = (pd.to_numeric(result.get("raw_epoch_bar2"), errors="coerce") - pd.to_numeric(result.get("raw_epoch_bar1"), errors="coerce")) / 60.0

    daily = pd.read_csv(admission_root / "normalized" / "daily_comparison.csv", low_memory=False)
    keep = ["ticker", "session_date", "open", "high", "low", "close", "volume", "open_canonical", "high_canonical", "low_canonical", "close_canonical", "volume_canonical", "open_exact", "hlc_exact", "corporate_action_quarantined", "year"]
    daily = daily[keep].rename(columns={
        "open": "tv60_open", "high": "tv60_high", "low": "tv60_low", "close": "tv60_close", "volume": "tv60_volume",
    })
    result = result.merge(daily, on=["ticker", "session_date"], how="inner")

    tv1d = pd.read_csv(admission_root / "normalized" / "tv1d_comparison.csv", low_memory=False)
    tv1d = tv1d[tv1d["session_admissible"].astype(str).str.lower().eq("true")]
    tv1d = tv1d.drop_duplicates(["ticker", "session_date"], keep="first")
    tv1d = tv1d[["ticker", "session_date", "open", "high", "low", "close", "volume"]].rename(columns={
        "open": "tv1d_open", "high": "tv1d_high", "low": "tv1d_low", "close": "tv1d_close", "volume": "tv1d_volume",
    })
    result = result.merge(tv1d, on=["ticker", "session_date"], how="left")

    previous = _load_panel_previous_close(panel).rename(columns={"date": "session_date"})
    result["session_date"] = pd.to_datetime(result["session_date"]).dt.date
    result = result.merge(previous, on=["ticker", "session_date"], how="left")
    result["first_bar_open_vs_canonical_open"] = pd.to_numeric(result["open_bar1"], errors="coerce") - pd.to_numeric(result["open_canonical"], errors="coerce")
    result["first_bar_open_vs_previous_close"] = pd.to_numeric(result["open_bar1"], errors="coerce") - pd.to_numeric(result["previous_canonical_close"], errors="coerce")
    result["tv60_open_vs_tv1d_open"] = pd.to_numeric(result["tv60_open"], errors="coerce") - pd.to_numeric(result["tv1d_open"], errors="coerce")
    result["first_bar_timestamp_hour_wib"] = pd.to_datetime(result["timestamp_wib_bar1"], errors="coerce").dt.hour
    result["first_bar_timestamp_minute_wib"] = pd.to_datetime(result["timestamp_wib_bar1"], errors="coerce").dt.minute
    result["second_bar_timestamp_wib"] = result.get("timestamp_wib_bar2")
    return result.sort_values(["ticker", "session_date"]).reset_index(drop=True)


def offline_summary(metadata: pd.DataFrame, sessions: pd.DataFrame) -> dict[str, Any]:
    def counts(frame: pd.DataFrame) -> dict[str, int]:
        return {
            "rows": int(len(frame)),
            "market_info_present": int(frame["market_info_present"].fillna(False).sum()) if not frame.empty else 0,
            "has_extended_hours": int(frame["has_extended_hours"].fillna(False).sum()) if not frame.empty else 0,
        }

    mismatch = sessions["tv60_open_vs_tv1d_open"].notna() & sessions["tv60_open_vs_tv1d_open"].ne(0)
    return {
        "metadata": counts(metadata),
        "metadata_unique": {
            "timezone": sorted(metadata["timezone"].dropna().astype(str).unique().tolist()),
            "session": sorted(metadata["session"].dropna().astype(str).unique().tolist()),
            "subsession_id": sorted(metadata["subsession_id"].dropna().astype(str).unique().tolist()),
            "subsessions": sorted(metadata["subsessions"].dropna().astype(str).unique().tolist()),
            "bar_source": sorted(metadata["bar_source"].dropna().astype(str).unique().tolist()),
        },
        "fixed_60_sessions": {
            "rows": int(len(sessions)),
            "tickers": int(sessions["ticker"].nunique()),
            "dates": int(sessions["session_date"].nunique()),
            "bar_count_distribution": {str(k): int(v) for k, v in sessions["tv60_bar_count"].value_counts().sort_index().items()},
            "first_timestamp_wib": sorted(sessions["timestamp_wib_bar1"].dropna().astype(str).unique().tolist())[:20],
            "first_bar_hour_counts": {str(k): int(v) for k, v in sessions["first_bar_timestamp_hour_wib"].value_counts(dropna=False).sort_index().items()},
            "second_timestamp_available": int(sessions["timestamp_wib_bar2"].notna().sum()),
            "tv1d_open_available": int(sessions["tv1d_open"].notna().sum()),
            "tv60_open_vs_tv1d_mismatch": int(mismatch.sum()),
            "tv60_open_exact_vs_tv1d": int((~mismatch & sessions["tv1d_open"].notna()).sum()),
            "first_bar_open_equals_previous_close": int((sessions["first_bar_open_vs_previous_close"] == 0).sum()),
            "first_bar_open_equals_canonical_open": int((sessions["first_bar_open_vs_canonical_open"] == 0).sum()),
        },
    }


def classify_live_probe(rows: pd.DataFrame, config: dict[str, Any]) -> str:
    if rows.empty:
        return "INCONCLUSIVE"
    comparable = rows[rows["status"] == "AVAILABLE"].copy()
    if comparable.empty:
        return "INCONCLUSIVE"
    preopen = comparable["preopen_bar_count"].fillna(0).astype(int)
    regular_preopen = comparable[comparable["session"] == "regular"]["preopen_bar_count"].fillna(0).astype(int)
    extended_preopen = comparable[comparable["session"] == "extended"]["preopen_bar_count"].fillna(0).astype(int)
    paired = comparable.pivot_table(index=["ticker", "date", "timeframe"], columns="session", values="preopen_bar_count", aggfunc="first").dropna(how="any")
    if paired.empty:
        return "INCONCLUSIVE"
    qualifying = paired[(paired.get("extended", 0) > 0) & (paired.get("regular", 0) == 0)]
    contradictions = paired[paired.get("regular", 0) > 0]
    minimum = int(config["decision_rules"]["minimum_consistent_pairs_for_confirmed_exclusion"])
    if len(qualifying) >= minimum and contradictions.empty:
        return "TV60_OPEN_AUCTION_EXCLUSION_CONFIRMED"
    if len(qualifying) > 0:
        return "TV60_OPEN_BOUNDARY_PATTERN_FOUND_MEANING_UNPROVEN"
    if len(contradictions) > 0 and len(qualifying) == 0:
        return "TV60_NATIVE_EXTENDED_INCLUDES_OPENING_AUCTION"
    return "INCONCLUSIVE"


def summarize_live_response(request: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    periods = response.get("periods") or []
    target = date.fromisoformat(request["date"])
    values: list[tuple[datetime, dict[str, Any]]] = []
    for period in periods:
        try:
            ts = datetime.fromtimestamp(int(period["time"]), tz=UTC).astimezone(WIB)
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            continue
        if ts.date() == target:
            values.append((ts, period))
    values.sort(key=lambda item: item[0])
    preopen = [item for item in values if time(8, 45) <= item[0].time() < time(9, 0)]
    opening_window = [item for item in values if time(8, 45) <= item[0].time() <= time(9, 5)]
    return {
        "ticker": request["ticker"], "date": request["date"], "timeframe": str(request["timeframe"]), "session": request["session"],
        "status": response.get("status"), "error": response.get("errors") or response.get("error"),
        "event_trace": response.get("event_trace") or [], "elapsed_ms": response.get("elapsed_ms"),
        "market_timezone": (response.get("market_info") or {}).get("timezone"),
        "market_session": (response.get("market_info") or {}).get("session"),
        "has_extended_hours": (response.get("market_info") or {}).get("has_extended_hours"),
        "subsessions": (response.get("market_info") or {}).get("subsessions"),
        "date_bar_count": len(values), "preopen_bar_count": len(preopen), "opening_window_bar_count": len(opening_window),
        "first_date_timestamp_wib": values[0][0].isoformat() if values else None,
        "second_date_timestamp_wib": values[1][0].isoformat() if len(values) > 1 else None,
        "last_date_timestamp_wib": values[-1][0].isoformat() if values else None,
        "preopen_timestamps_wib": [item[0].isoformat() for item in preopen],
        "opening_window_timestamps_wib": [item[0].isoformat() for item in opening_window],
    }

