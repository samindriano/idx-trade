"""Pure preparation, normalization, and gate logic for TradingView Price-Path V2."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

import pandas as pd


UTC = timezone.utc
WIB = ZoneInfo("Asia/Jakarta")
REGULAR_START = time(9, 0)
REGULAR_END = time(16, 30)
OHLCV = ("open", "high", "low", "close", "volume")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def _normalise_ticker(value: object) -> str:
    return str(value).upper().replace(".JK", "").strip()


def load_official_sessions(path: Path, start: str, end: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise ValueError("official session file must contain date")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    frame = frame.dropna(subset=["date"])
    frame = frame[frame["date"].between(pd.Timestamp(start), pd.Timestamp(end))]
    if frame["date"].duplicated().any():
        raise ValueError("official sessions contain duplicate dates")
    return frame.sort_values("date").reset_index(drop=True)


def _listed_on(master: pd.DataFrame, ticker: str, sessions: pd.Series) -> pd.Series:
    rows = master[master["ticker"].eq(ticker)]
    listed = pd.Series(False, index=sessions.index)
    for row in rows.itertuples(index=False):
        start = pd.Timestamp(row.listed_from)
        end = pd.Timestamp(row.listed_to) if pd.notna(row.listed_to) else pd.Timestamp.max
        listed |= sessions.ge(start) & sessions.le(end)
    return listed


def build_common_universe(
    security_master_path: Path,
    scope_exclusions_path: Path,
    curated_identities_path: Path | None,
    start: str,
    end: str,
) -> pd.DataFrame:
    master = pd.read_csv(security_master_path, dtype=str)
    if curated_identities_path and curated_identities_path.exists():
        curated = pd.read_csv(curated_identities_path, dtype=str)
        curated = curated.rename(columns={"security_type": "security_type"})
        curated = curated[curated.get("security_type", pd.Series(index=curated.index, dtype=str)).str.contains("Biasa|Common", case=False, na=False)]
        if not curated.empty:
            curated["security_id"] = "IDX:" + curated["ticker"].map(_normalise_ticker) + ":" + pd.to_datetime(curated["listed_from"]).dt.strftime("%Y%m%d")
            curated["source"] = curated.get("source", "CURATED_SECURITY_IDENTITY")
            curated = curated[["security_id", "ticker", "company_name", "listed_from", "listed_to", "source"]]
            master = pd.concat([master, curated], ignore_index=True)
    exclusions = pd.read_csv(scope_exclusions_path, dtype=str) if scope_exclusions_path.exists() else pd.DataFrame(columns=["ticker"])
    excluded = set(exclusions.get("ticker", pd.Series(dtype=str)).map(_normalise_ticker))
    master["ticker"] = master["ticker"].map(_normalise_ticker)
    master["listed_from"] = pd.to_datetime(master["listed_from"], errors="coerce").dt.normalize()
    master["listed_to"] = pd.to_datetime(master.get("listed_to"), errors="coerce").dt.normalize()
    master = master.dropna(subset=["ticker", "listed_from"])
    master = master[~master["ticker"].isin(excluded)]
    master = master.drop_duplicates(["ticker", "listed_from"], keep="last")
    master = master[master["listed_from"].le(pd.Timestamp(end)) & (master["listed_to"].isna() | master["listed_to"].ge(pd.Timestamp(start)))]
    master["scope"] = "COMMON_STOCK"
    return master.sort_values(["ticker", "listed_from"]).reset_index(drop=True)


def build_expected_sessions(universe: pd.DataFrame, sessions: pd.DataFrame) -> pd.DataFrame:
    dates = sessions["date"].reset_index(drop=True)
    rows: list[dict[str, Any]] = []
    for ticker, group in universe.groupby("ticker", sort=True):
        identity_by_date: dict[str, Any] = {}
        # Build the interval map once per ticker. The previous implementation
        # filtered a DataFrame for every ticker-session pair, which made a
        # million-row historical universe unnecessarily quadratic.
        for identity in group.sort_values("listed_from").itertuples(index=False):
            start = pd.Timestamp(identity.listed_from)
            end = pd.Timestamp(identity.listed_to) if pd.notna(identity.listed_to) else pd.Timestamp.max
            for session in dates[(dates >= start) & (dates <= end)]:
                identity_by_date[session.date().isoformat()] = identity
        for session in dates:
            identity = identity_by_date.get(session.date().isoformat())
            if identity is None:
                continue
            rows.append({
                "ticker": ticker,
                "session_date": session.date().isoformat(),
                "security_id": identity.security_id,
                "listed_from": pd.Timestamp(identity.listed_from).date().isoformat(),
                "listed_to": pd.Timestamp(identity.listed_to).date().isoformat() if pd.notna(identity.listed_to) else "",
                "expected": True,
            })
    return pd.DataFrame(rows).sort_values(["ticker", "session_date"]).reset_index(drop=True)


def _numeric(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _raw_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("data", [])
    return rows if isinstance(rows, list) else []


def classify_official_activity(expected: pd.DataFrame, stock_summary_root: Path) -> pd.DataFrame:
    by_date: dict[str, dict[str, dict[str, Any]]] = {}
    for path in sorted(stock_summary_root.glob("sessions/*/stock_summary.raw.json")):
        session_date = path.parent.name
        by_date[session_date] = {_normalise_ticker(row.get("StockCode")): row for row in _raw_rows(path)}
    records: list[dict[str, Any]] = []
    for row in expected.itertuples(index=False):
        source = by_date.get(row.session_date, {}).get(row.ticker)
        if source is None:
            records.append({"ticker": row.ticker, "session_date": row.session_date, "activity_state": "UNKNOWN", "evidence_present": False, "volume": None, "value": None, "frequency": None, "source": "IDX_PUBLIC_STOCK_SUMMARY"})
            continue
        volume, value, frequency = (_numeric(source.get(key)) for key in ("Volume", "Value", "Frequency"))
        if None in (volume, value, frequency):
            state = "UNKNOWN"
        elif volume > 0 or value > 0 or frequency > 0:
            state = "ACTIVE"
        elif volume == 0 and value == 0 and frequency == 0:
            state = "NO_TRADE"
        else:
            state = "UNKNOWN"
        records.append({"ticker": row.ticker, "session_date": row.session_date, "activity_state": state, "evidence_present": True, "volume": volume, "value": value, "frequency": frequency, "source": "IDX_PUBLIC_STOCK_SUMMARY"})
    return pd.DataFrame(records).sort_values(["ticker", "session_date"]).reset_index(drop=True)


def build_request_manifest(universe: pd.DataFrame, sessions: pd.DataFrame, config: Mapping[str, Any]) -> pd.DataFrame:
    start = pd.Timestamp(config["window"]["start"])
    end = pd.Timestamp(config["window"]["end"])
    rows: list[dict[str, Any]] = []
    for index, (ticker, group) in enumerate(universe.groupby("ticker", sort=True), start=1):
        required = sessions[(sessions["date"] >= group["listed_from"].min()) & (sessions["date"] <= (group["listed_to"].max() if group["listed_to"].notna().any() else end))]
        required = required[required["date"].between(start, end)]
        if required.empty:
            continue
        required_start, required_end = required["date"].min(), required["date"].max()
        to_epoch = int(datetime(required_end.year, required_end.month, required_end.day, 23, 59, 59, tzinfo=WIB).timestamp())
        rows.append({
            "request_index": index,
            "ticker": ticker,
            "security_id": str(group.iloc[0].get("security_id", "")),
            "symbol": f"IDX:{ticker}",
            "server": config["provider"]["server"],
            "timeframe": config["provider"]["timeframe"],
            "session": config["provider"]["session"],
            "adjustment": config["provider"]["adjustment"],
            "required_start": required_start.date().isoformat(),
            "required_end": required_end.date().isoformat(),
            "initial_range": config["acquisition"]["initial_range"],
            "fetch_more_steps": config["acquisition"]["fetch_more_steps"],
            "fetch_more_batch": config["acquisition"]["fetch_more_batch"],
            "fetch_more_wait_ms": config["acquisition"]["fetch_more_wait_ms"],
            "timeout_ms": config["acquisition"]["timeout_ms"],
            "to": to_epoch,
        })
    return pd.DataFrame(rows).sort_values("request_index").reset_index(drop=True)


def _period_timestamp(period: Mapping[str, Any]) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(period["time"]), tz=UTC).astimezone(WIB)
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return None


def normalize_response(payload: Mapping[str, Any], request: Mapping[str, Any], official_sessions: set[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    response = payload.get("response", payload)
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    malformed = duplicates = invalid = leakage = contamination = 0
    periods = response.get("periods") or []
    for period in periods:
        try:
            epoch = int(period["time"])
            values = {field: float(period[field]) for field in OHLCV}
            if not math.isfinite(epoch) or any(not math.isfinite(value) for value in values.values()):
                raise ValueError
        except (KeyError, TypeError, ValueError, OverflowError):
            malformed += 1
            continue
        if epoch in seen:
            duplicates += 1
            continue
        seen.add(epoch)
        timestamp = _period_timestamp(period)
        if timestamp is None:
            malformed += 1
            continue
        session_date = timestamp.date().isoformat()
        in_window = request["required_start"] <= session_date <= request["required_end"]
        session_ok = session_date in official_sessions
        regular_ok = REGULAR_START <= timestamp.time() < REGULAR_END
        # Bars outside the requested range are retained for historical-depth
        # diagnostics; they are not contamination. Only a timestamp inside
        # the requested range can violate the official-session contract.
        if in_window and not session_ok:
            leakage += 1
        if in_window and timestamp.time() < REGULAR_START:
            contamination += 1
        if values["volume"] < 0 or min(values[field] for field in ("open", "high", "low", "close")) <= 0 or values["high"] < values["low"] or not values["low"] <= values["open"] <= values["high"] or not values["low"] <= values["close"] <= values["high"]:
            invalid += 1
            continue
        rows.append({"ticker": request["ticker"], "security_id": request.get("security_id", ""), "raw_epoch": epoch, "timestamp_utc": timestamp.astimezone(UTC).isoformat(), "timestamp_wib": timestamp.isoformat(), "session_date": session_date, "open": values["open"], "high": values["high"], "low": values["low"], "close": values["close"], "volume": values["volume"], "provider_session": request["session"], "session_admissible": bool(in_window and session_ok and regular_ok), "source_request_index": request["request_index"], "source_page_count": len((response.get("fetch_more") or {}).get("steps") or [])})
    return pd.DataFrame(rows), {"raw_rows": len(periods), "valid_rows": len(rows), "malformed_rows": malformed, "duplicate_rows": duplicates, "invalid_ohlcv_rows": invalid, "session_date_leakage_rows": leakage, "extended_preopen_contamination_rows": contamination, "status": response.get("status"), "errors": response.get("errors", []), "completion_reason": (response.get("fetch_more") or {}).get("completion_reason")}


def aggregate_daily(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return pd.DataFrame(columns=["ticker", "session_date", *OHLCV, "bar_count"])
    usable = bars[bars["session_admissible"]].sort_values(["ticker", "session_date", "raw_epoch"])
    if usable.empty:
        return pd.DataFrame(columns=["ticker", "session_date", *OHLCV, "bar_count"])
    return usable.groupby(["ticker", "session_date"], sort=True).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), volume=("volume", "sum"), bar_count=("raw_epoch", "size")).reset_index()


def load_canonical(canonical_root: Path, tickers: Iterable[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for ticker in sorted(set(tickers)):
        path = canonical_root / f"{ticker}.parquet"
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        frame["ticker"] = ticker
        frame["session_date"] = pd.to_datetime(frame["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        frame = frame.rename(columns={"raw_open": "canonical_open", "raw_high": "canonical_high", "raw_low": "canonical_low", "raw_close": "canonical_close", "raw_volume": "canonical_volume"})
        frames.append(frame[["ticker", "session_date", "canonical_open", "canonical_high", "canonical_low", "canonical_close", "canonical_volume"]])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def fidelity_report(daily: pd.DataFrame, activity: pd.DataFrame, canonical: pd.DataFrame, ca: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if daily.empty or canonical.empty:
        return pd.DataFrame(), {"matched_rows": 0, "non_ca_rows": 0, "hlc_exact_rate": None, "volume_within_5_rate": None, "by_year": {}}
    active = activity[activity["activity_state"].eq("ACTIVE")][["ticker", "session_date"]]
    merged = daily.merge(active, on=["ticker", "session_date"], how="inner").merge(canonical, on=["ticker", "session_date"], how="inner")
    ca_keys = {(str(row.ticker).upper(), pd.Timestamp(row.effective_date).date().isoformat()) for row in ca.itertuples()} if not ca.empty else set()
    merged["corporate_action_quarantined"] = merged.apply(lambda row: any(row.ticker == ticker and abs((pd.Timestamp(row.session_date) - pd.Timestamp(action_date)).days) <= 1 for ticker, action_date in ca_keys), axis=1)
    clean = merged[~merged["corporate_action_quarantined"]].copy()
    for field in ("high", "low", "close"):
        clean[f"{field}_exact"] = clean[field].eq(clean[f"canonical_{field}"])
    clean["hlc_exact"] = clean[["high_exact", "low_exact", "close_exact"]].all(axis=1)
    clean["volume_within_5"] = (clean["volume"] - clean["canonical_volume"]).abs() <= clean["canonical_volume"].abs().clip(lower=1.0) * 0.05
    by_year = {}
    clean["year"] = pd.to_datetime(clean["session_date"]).dt.year
    for year, group in clean.groupby("year", sort=True):
        by_year[str(year)] = {"rows": int(len(group)), "hlc_exact_rate": float(group["hlc_exact"].mean()), "volume_within_5_rate": float(group["volume_within_5"].mean())}
    return merged, {"matched_rows": int(len(merged)), "non_ca_rows": int(len(clean)), "corporate_action_quarantined_rows": int(merged["corporate_action_quarantined"].sum()), "hlc_exact_rate": float(clean["hlc_exact"].mean()) if not clean.empty else None, "volume_within_5_rate": float(clean["volume_within_5"].mean()) if not clean.empty else None, "by_year": by_year}


def evaluate_gates(expected: pd.DataFrame, activity: pd.DataFrame, bars: pd.DataFrame, diagnostics: pd.DataFrame, fidelity: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    active = activity[activity["activity_state"].eq("ACTIVE")]
    usable_keys = bars[bars.get("session_admissible", pd.Series(dtype=bool)).eq(True)][["ticker", "session_date"]].drop_duplicates() if not bars.empty else pd.DataFrame(columns=["ticker", "session_date"])
    covered = active.merge(usable_keys, on=["ticker", "session_date"], how="inner")
    coverage = len(covered) / len(active) if len(active) else 0.0
    coverage_by_year = {}
    for year, group in active.assign(year=active["session_date"].str[:4]).groupby("year", sort=True):
        covered_year = covered[covered["session_date"].str.startswith(str(year))]
        coverage_by_year[str(year)] = {"active": int(len(group)), "covered": int(len(covered_year)), "coverage": float(len(covered_year) / len(group)) if len(group) else 0.0}
    unknown_rate = float(activity["activity_state"].eq("UNKNOWN").mean()) if len(activity) else 1.0
    structural = {"malformed_ohlcv": int(diagnostics.get("malformed_rows", pd.Series(dtype=int)).sum()) if not diagnostics.empty else 0, "invalid_ohlcv": int(diagnostics.get("invalid_ohlcv_rows", pd.Series(dtype=int)).sum()) if not diagnostics.empty else 0, "duplicate_ticker_timestamp": int(diagnostics.get("duplicate_rows", pd.Series(dtype=int)).sum()) if not diagnostics.empty else 0, "session_date_leakage": int(diagnostics.get("session_date_leakage_rows", pd.Series(dtype=int)).sum()) if not diagnostics.empty else 0, "extended_preopen_contamination": int(diagnostics.get("extended_preopen_contamination_rows", pd.Series(dtype=int)).sum()) if not diagnostics.empty else 0}
    gates = {"overall_active_coverage": coverage >= config["gates"]["active_coverage_overall"], "yearly_active_coverage": all(value["coverage"] >= config["gates"]["active_coverage_year"] for value in coverage_by_year.values()), "activity_unknown": unknown_rate <= config["gates"]["unknown_activity_rate_max"], "structural_integrity": all(value == 0 for value in structural.values()), "hlc_fidelity": fidelity.get("hlc_exact_rate") is not None and fidelity["hlc_exact_rate"] >= config["gates"]["hlc_exact_overall"], "volume_fidelity": fidelity.get("volume_within_5_rate") is not None and fidelity["volume_within_5_rate"] >= config["gates"]["volume_within_5_overall"]}
    yearly_fidelity = all(value["hlc_exact_rate"] >= config["gates"]["hlc_exact_year"] and value["volume_within_5_rate"] >= config["gates"]["volume_within_5_year"] for value in fidelity.get("by_year", {}).values())
    gates["yearly_fidelity"] = yearly_fidelity
    return {"expected_sessions": int(len(expected)), "active_sessions": int(len(active)), "covered_active_sessions": int(len(covered)), "true_provider_misses": int(len(active) - len(covered)), "unknown_sessions": int(activity["activity_state"].eq("UNKNOWN").sum()), "no_trade_sessions": int(activity["activity_state"].eq("NO_TRADE").sum()), "active_coverage": coverage, "active_coverage_by_year": coverage_by_year, "unknown_rate": unknown_rate, "structural": structural, "gates": gates, "all_gates_pass": bool(all(gates.values()))}
