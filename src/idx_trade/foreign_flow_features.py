"""Causal, scale-normalized Foreign Flow feature contract and audit helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


FEATURE_SCHEMA_VERSION = 1
WINDOWS = (3, 5, 10, 20)
FEATURE_COLUMNS = (
    "foreign_net_to_volume_1",
    "foreign_net_to_volume_sum_3",
    "foreign_net_to_volume_sum_5",
    "foreign_net_to_volume_sum_10",
    "foreign_net_to_volume_sum_20",
    "foreign_sign_consistency_3",
    "foreign_sign_consistency_5",
    "foreign_sign_consistency_10",
    "foreign_sign_consistency_20",
    "foreign_flow_acceleration_3_20",
    "foreign_gross_to_volume_1",
)
OUTPUT_COLUMNS = (
    "ticker",
    "feature_session",
    "flow_through_session",
    "listed_at_feature_session",
    *FEATURE_COLUMNS,
    "feature_status",
    "missing_reasons",
)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _date(value: object) -> pd.Timestamp:
    # IDX Stock Summary caches encode ``as_of_date`` as epoch milliseconds.
    # Treat numeric values explicitly; pandas otherwise interprets them as
    # nanoseconds and silently maps an official 2021 date into 1970.
    if isinstance(value, (int, float, np.integer, np.floating)) and not pd.isna(value):
        numeric = float(value)
        if not np.isfinite(numeric):
            raise ValueError(f"invalid date: {value!r}")
        unit = "ms" if abs(numeric) >= 1e11 else "s"
        parsed = pd.to_datetime(numeric, unit=unit, utc=True)
    else:
        parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"invalid date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


def _canonical_sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    parsed = pd.DatetimeIndex([_date(value) for value in values])
    if len(parsed) == 0 or parsed.has_duplicates:
        raise ValueError("official sessions are empty or duplicated")
    return parsed.sort_values()


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")


def _normalise_flow(frame: pd.DataFrame) -> pd.DataFrame:
    _require_columns(
        frame,
        {
            "ticker",
            "session_date",
            "foreign_buy",
            "foreign_sell",
            "foreign_net",
            "unit",
        },
        "foreign flow",
    )
    output = frame.copy()
    output["ticker"] = output["ticker"].astype("string").str.strip().str.upper()
    output["session_date"] = [_date(value) for value in output["session_date"]]
    if output.duplicated(["ticker", "session_date"]).any():
        raise ValueError("foreign flow has duplicate ticker/session rows")
    for column in ("foreign_buy", "foreign_sell", "foreign_net"):
        values = pd.to_numeric(output[column], errors="coerce")
        if values.isna().any() or (~np.isfinite(values)).any():
            raise ValueError(f"foreign flow has invalid {column}")
        if (values % 1 != 0).any():
            raise ValueError(f"foreign flow has fractional {column}")
        output[column] = values.astype("int64")
    if (output[["foreign_buy", "foreign_sell"]] < 0).any().any():
        raise ValueError("foreign flow has negative buy/sell")
    if not output["foreign_net"].eq(output["foreign_buy"] - output["foreign_sell"]).all():
        raise ValueError("foreign flow net identity mismatch")
    if not output["unit"].astype(str).eq("SHARES").all():
        raise ValueError("foreign flow unit is not SHARES")
    return output.sort_values(["ticker", "session_date"]).reset_index(drop=True)


def _normalise_volume(frame: pd.DataFrame) -> pd.DataFrame:
    # ``raw_volume`` is the internal canonical name.  The accepted official
    # Stock Summary cache uses ``as_of_date`` + regular-market ``volume``.
    if {"ticker", "date", "raw_volume"}.issubset(frame.columns):
        date_column = "date"
        volume_column = "raw_volume"
    elif {"ticker", "as_of_date", "volume"}.issubset(frame.columns):
        date_column = "as_of_date"
        volume_column = "volume"
    else:
        raise ValueError(
            "price volume missing canonical (ticker,date,raw_volume) or "
            "official (ticker,as_of_date,volume) columns"
        )
    output = frame.loc[:, ["ticker", date_column, volume_column]].rename(
        columns={date_column: "date", volume_column: "raw_volume"}
    ).copy()
    output["ticker"] = output["ticker"].astype("string").str.strip().str.upper()
    output["date"] = [_date(value) for value in output["date"]]
    if output.duplicated(["ticker", "date"]).any():
        raise ValueError("price volume has duplicate ticker/session rows")
    values = pd.to_numeric(output["raw_volume"], errors="coerce")
    output["raw_volume"] = values
    output["volume_valid"] = values.notna() & np.isfinite(values) & values.ge(0)
    return output.sort_values(["ticker", "date"]).reset_index(drop=True)


def _normalise_master(frame: pd.DataFrame) -> pd.DataFrame:
    _require_columns(frame, {"ticker", "listed_from", "listed_to"}, "security master")
    output = frame.copy()
    output["ticker"] = output["ticker"].astype("string").str.strip().str.upper()
    output["listed_from"] = [_date(value) for value in output["listed_from"]]
    output["listed_to"] = [
        pd.NaT
        if value is None or pd.isna(value) or str(value).strip() == ""
        else _date(value)
        for value in output["listed_to"]
    ]
    invalid = output["listed_to"].notna() & output["listed_to"].lt(output["listed_from"])
    if invalid.any():
        raise ValueError("security master has invalid listing interval")
    return output


def _listed_on(master_rows: pd.DataFrame, session: pd.Timestamp) -> bool:
    starts = master_rows["listed_from"].le(session)
    ends = master_rows["listed_to"].isna() | master_rows["listed_to"].ge(session)
    return bool((starts & ends).any())


def _flow_window_reason(
    *,
    flow_values: pd.DataFrame,
    window: int,
    start: int,
    end: int,
    listed: list[bool],
) -> str | None:
    if end - start < window:
        return "INSUFFICIENT_HISTORY"
    if not all(listed[start:end]):
        return "LISTING_INTERVAL_GAP"
    flow_slice = flow_values.iloc[start:end]
    if flow_slice["foreign_net"].isna().any():
        return "MISSING_FLOW_SESSION"
    return None


def _volume_window_reason(
    *,
    volume_values: pd.Series,
    start: int,
    end: int,
) -> str | None:
    volume_slice = volume_values.iloc[start:end]
    if volume_slice.isna().any():
        return "MISSING_VOLUME"
    if (~np.isfinite(volume_slice)).any() or volume_slice.lt(0).any():
        return "INVALID_VOLUME"
    if float(volume_slice.sum()) <= 0:
        return "INVALID_ZERO_DENOMINATOR"
    return None


def _window_reason(
    *,
    flow_values: pd.DataFrame,
    volume_values: pd.Series,
    window: int,
    start: int,
    end: int,
    listed: list[bool],
) -> str | None:
    return _flow_window_reason(
        flow_values=flow_values,
        window=window,
        start=start,
        end=end,
        listed=listed,
    ) or _volume_window_reason(volume_values=volume_values, start=start, end=end)


def _rolling_ticker_frame(
    *,
    ticker: str,
    sessions: pd.DatetimeIndex,
    flow_series: pd.DataFrame,
    volume_series: pd.Series,
    listed: list[bool],
    material_mask: np.ndarray,
    reasons: Counter[str],
) -> pd.DataFrame:
    """Build one ticker with numpy rolling arrays, preserving fail-closed reasons."""

    count = len(sessions)
    net = pd.to_numeric(flow_series["foreign_net"], errors="coerce").to_numpy(dtype=float)
    buy = pd.to_numeric(flow_series["foreign_buy"], errors="coerce").to_numpy(dtype=float)
    sell = pd.to_numeric(flow_series["foreign_sell"], errors="coerce").to_numpy(dtype=float)
    volume = pd.to_numeric(volume_series, errors="coerce").to_numpy(dtype=float)
    listed_array = np.asarray(listed, dtype=bool)
    candidate = material_mask & listed_array
    candidate[:1] = False
    indices = np.flatnonzero(candidate)
    if len(indices) == 0:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    flow_bad = ~np.isfinite(net)
    listing_bad = ~listed_array
    volume_missing = np.isnan(volume)
    volume_invalid = ~np.isfinite(volume) | (volume < 0)
    volume_zero_or_negative_sum = np.zeros(count, dtype=bool)

    def rolling_count(mask: np.ndarray, window: int) -> np.ndarray:
        cumulative = np.concatenate(([0], np.cumsum(mask.astype(np.int64))))
        output = np.zeros(count, dtype=np.int64)
        if window <= count:
            output[window:] = cumulative[window:count] - cumulative[: count - window]
        return output

    def rolling_sum(values: np.ndarray, window: int) -> np.ndarray:
        cumulative = np.concatenate(([0.0], np.cumsum(np.where(np.isfinite(values), values, 0.0))))
        output = np.zeros(count, dtype=float)
        if window <= count:
            output[window:] = cumulative[window:count] - cumulative[: count - window]
        return output

    def window_arrays(window: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        flow_reason = np.full(count, None, dtype=object)
        flow_reason[:window] = "INSUFFICIENT_HISTORY"
        valid_start = np.arange(count) >= window
        listing_gap = rolling_count(listing_bad, window) > 0
        flow_gap = rolling_count(flow_bad, window) > 0
        flow_reason[valid_start & listing_gap] = "LISTING_INTERVAL_GAP"
        flow_reason[valid_start & ~listing_gap & flow_gap] = "MISSING_FLOW_SESSION"

        volume_reason = np.full(count, None, dtype=object)
        volume_reason[:window] = "INSUFFICIENT_HISTORY"
        volume_missing_window = rolling_count(volume_missing, window) > 0
        volume_invalid_window = rolling_count(volume_invalid, window) > 0
        volume_sums = rolling_sum(volume, window)
        volume_zero_or_negative_sum[:] = volume_sums <= 0
        volume_reason[valid_start & volume_missing_window] = "MISSING_VOLUME"
        volume_reason[valid_start & ~volume_missing_window & volume_invalid_window] = "INVALID_VOLUME"
        volume_reason[
            valid_start
            & ~volume_missing_window
            & ~volume_invalid_window
            & (volume_sums <= 0)
        ] = "INVALID_ZERO_DENOMINATOR"

        ratio_reason = np.where(flow_reason != None, flow_reason, volume_reason)  # noqa: E711
        ratio = np.full(count, np.nan, dtype=float)
        ratio[ratio_reason == None] = (  # noqa: E711
            rolling_sum(net, window)[ratio_reason == None]
            / volume_sums[ratio_reason == None]
        )
        sign = np.full(count, np.nan, dtype=float)
        signs = np.sign(np.where(np.isfinite(net), net, 0.0))
        sign_sum = rolling_sum(signs, window)
        sign[flow_reason == None] = sign_sum[flow_reason == None]  # noqa: E711
        sign[flow_reason == None] /= float(window)  # noqa: E711
        return flow_reason, ratio_reason, ratio, sign

    ratio_by_window: dict[int, np.ndarray] = {}
    flow_reason_by_window: dict[int, np.ndarray] = {}
    ratio_reason_by_window: dict[int, np.ndarray] = {}
    sign_by_window: dict[int, np.ndarray] = {}
    for window in WINDOWS:
        flow_reason, ratio_reason, ratio, sign = window_arrays(window)
        flow_reason_by_window[window] = flow_reason
        ratio_reason_by_window[window] = ratio_reason
        ratio_by_window[window] = ratio
        sign_by_window[window] = sign

    flow_reason_1, ratio_reason_1, ratio_1, _ = window_arrays(1)
    one_day_volume = volume
    gross = buy + sell
    gross_ratio = np.full(count, np.nan, dtype=float)
    one_day_valid = ratio_reason_1 == None  # noqa: E711
    gross_ratio[one_day_valid] = gross[one_day_valid] / one_day_volume[one_day_valid]

    rows: list[dict[str, object]] = []
    for index in indices:
        row_reasons: set[str] = set()
        values: dict[str, object] = {
            "ticker": ticker,
            "feature_session": sessions[index],
            "flow_through_session": sessions[index - 1],
            "listed_at_feature_session": True,
        }
        for window in WINDOWS:
            ratio_name = f"foreign_net_to_volume_sum_{window}"
            persistence_name = f"foreign_sign_consistency_{window}"
            ratio_reason = ratio_reason_by_window[window][index]
            flow_reason = flow_reason_by_window[window][index]
            values[ratio_name] = ratio_by_window[window][index]
            values[persistence_name] = sign_by_window[window][index]
            if ratio_reason is not None:
                row_reasons.add(str(ratio_reason))
                reasons[f"{ratio_name}:{ratio_reason}"] += 1
            if flow_reason is not None:
                row_reasons.add(str(flow_reason))
                reasons[f"{persistence_name}:{flow_reason}"] += 1

        one_day_reason = ratio_reason_1[index]
        values["foreign_net_to_volume_1"] = ratio_1[index]
        values["foreign_gross_to_volume_1"] = gross_ratio[index]
        if one_day_reason is not None:
            row_reasons.add(str(one_day_reason))
            reasons[f"foreign_net_to_volume_1:{one_day_reason}"] += 1
            reasons[f"foreign_gross_to_volume_1:{one_day_reason}"] += 1

        if np.isfinite(ratio_by_window[3][index]) and np.isfinite(ratio_by_window[20][index]):
            values["foreign_flow_acceleration_3_20"] = (
                ratio_by_window[3][index] - ratio_by_window[20][index]
            )
        else:
            acceleration_reason = "INSUFFICIENT_HISTORY" if index < 20 else "MISSING_WINDOW_INPUT"
            values["foreign_flow_acceleration_3_20"] = np.nan
            row_reasons.add(acceleration_reason)
            reasons[f"foreign_flow_acceleration_3_20:{acceleration_reason}"] += 1

        available = [pd.notna(values[column]) for column in FEATURE_COLUMNS]
        values["feature_status"] = (
            "AVAILABLE" if all(available) else "PARTIAL" if any(available) else "MISSING"
        )
        values["missing_reasons"] = ";".join(sorted(row_reasons))
        rows.append(values)
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def materialize_foreign_flow_features(
    foreign_flow: pd.DataFrame,
    price_volume: pd.DataFrame,
    official_sessions: Iterable[object],
    security_master: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Materialize features at session t+1 from flow and volume through t.

    The output contains one candidate row for each listed ticker/session in the
    canonical volume-session intersection. Missing inputs remain NaN and are
    labeled; no input is forward-filled. Only ``raw_volume`` is consumed from
    the price panel. OHLC and same-session close are intentionally excluded.
    """

    sessions = _canonical_sessions(official_sessions)
    flow = _normalise_flow(foreign_flow)
    volume = _normalise_volume(price_volume)
    master = _normalise_master(security_master)
    price_sessions = pd.DatetimeIndex(sorted(volume["date"].unique()))
    material_sessions = sessions[sessions.isin(price_sessions)]
    if len(material_sessions) < 2:
        raise ValueError("fewer than two sessions have canonical volume")

    flow_by_ticker = {
        ticker: group.set_index("session_date").reindex(sessions)
        for ticker, group in flow.groupby("ticker", sort=True)
    }
    volume_by_ticker = {
        ticker: group.set_index("date")["raw_volume"].reindex(sessions)
        for ticker, group in volume.groupby("ticker", sort=True)
    }
    master_by_ticker = {
        ticker: group.reset_index(drop=True)
        for ticker, group in master.groupby("ticker", sort=True)
    }

    reasons = Counter()
    material_mask = np.asarray(sessions.isin(material_sessions), dtype=bool)
    frames: list[pd.DataFrame] = []
    for ticker, master_rows in master_by_ticker.items():
        if ticker not in flow_by_ticker or ticker not in volume_by_ticker:
            continue
        flow_series = flow_by_ticker[ticker]
        volume_series = volume_by_ticker[ticker]
        listed = [_listed_on(master_rows, day) for day in sessions]
        frame = _rolling_ticker_frame(
            ticker=ticker,
            sessions=sessions,
            flow_series=flow_series,
            volume_series=volume_series,
            listed=listed,
            material_mask=material_mask,
            reasons=reasons,
        )
        if not frame.empty:
            frames.append(frame)

    output = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=OUTPUT_COLUMNS)
    if not output.empty:
        output = output.sort_values(["feature_session", "ticker"]).reset_index(drop=True)
    feature_counts = {
        column: int(output[column].notna().sum()) if not output.empty else 0
        for column in FEATURE_COLUMNS
    }
    summary = {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "status": "OFFLINE_FEATURE_MATERIALIZATION_COMPLETE",
        "official_sessions": len(sessions),
        "canonical_volume_sessions": len(material_sessions),
        "sessions_without_canonical_volume": int(len(sessions) - len(material_sessions)),
        "first_material_session": material_sessions.min().date().isoformat(),
        "last_material_session": material_sessions.max().date().isoformat(),
        "candidate_rows": int(len(output)),
        "candidate_tickers": int(output["ticker"].nunique()) if not output.empty else 0,
        "feature_available_rows": int(output["feature_status"].eq("AVAILABLE").sum()) if not output.empty else 0,
        "feature_partial_rows": int(output["feature_status"].eq("PARTIAL").sum()) if not output.empty else 0,
        "feature_missing_rows": int(output["feature_status"].eq("MISSING").sum()) if not output.empty else 0,
        "feature_available_counts": feature_counts,
        "missing_reason_counts": dict(sorted(reasons.items())),
        "causality": "FEATURE_SESSION_S_USES_ONLY_FOREIGN_FLOW_AND_VOLUME_THROUGH_PREVIOUS_OFFICIAL_SESSION_T",
        "price_columns_consumed": ["ticker", "date", "raw_volume"],
        "price_columns_not_consumed": ["raw_open", "raw_high", "raw_low", "raw_close"],
        "zero_flow_is_valid": True,
        "forward_fill_used": False,
        "corporate_action_dependency": "NONE; share-normalized ratios use same-session raw ForeignBuy/ForeignSell and raw_volume",
        "clipping_or_winsorization": "NONE",
        "ranking_or_performance_selection": "NONE",
    }
    return output, summary


def _read_archive(root: Path) -> tuple[pd.DataFrame, pd.DatetimeIndex, dict[str, object]]:
    manifest_path = root / "archive_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "HISTORICAL_FOREIGN_FLOW_ARCHIVE_VERIFIED":
        raise ValueError("foreign-flow archive manifest is not verified")
    sessions = _canonical_sessions(pd.read_csv(root / "calendar" / "official_exchange_sessions.csv")["date"])
    frames = []
    for day in sessions:
        path = root / "sessions" / day.date().isoformat() / "foreign_flow.parquet"
        if not path.exists():
            raise FileNotFoundError(f"missing accepted foreign-flow session: {day.date()}")
        frames.append(pd.read_parquet(path))
    return pd.concat(frames, ignore_index=True), sessions, {
        "archive_manifest_path": str(manifest_path),
        "archive_manifest_sha256": sha256_file(manifest_path),
        "archive_calendar_sha256": sha256_file(root / "calendar" / "official_exchange_sessions.csv"),
    }


def _read_volume(root: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    files = [root] if root.is_file() else sorted(root.glob("*.parquet"))
    if not files:
        raise ValueError("canonical volume source contains no parquet files")
    frames = []
    hashes = []
    source_format = "CANONICAL_INTERNAL_VOLUME_PARQUET"
    for path in files:
        hashes.append({"path": str(path), "sha256": sha256_file(path)})
        frame = pd.read_parquet(path)
        if {"ticker", "as_of_date", "volume"}.issubset(frame.columns):
            source_format = "IDX_STOCK_SUMMARY_PARQUET"
        frames.append(_normalise_volume(frame))
    return pd.concat(frames, ignore_index=True), {
        "volume_file_count": len(files),
        "volume_files": hashes,
        "volume_source_format": source_format,
        "volume_source_field": "volume",
        "volume_source_semantics": "OFFICIAL_IDX_STOCK_SUMMARY_REGULAR_MARKET_VOLUME",
    }


def write_offline_audit_artifacts(
    features: pd.DataFrame,
    *,
    output_root: str | Path,
    metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Write deterministic coverage, missingness, and distribution diagnostics."""

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    frame = features.copy()
    frame["feature_session"] = pd.to_datetime(frame["feature_session"])
    frame = frame.sort_values(["feature_session", "ticker"]).reset_index(drop=True)

    session_rows = []
    for session, group in frame.groupby("feature_session", sort=True):
        session_rows.append(
            {
                "feature_session": session.date().isoformat(),
                "candidate_rows": len(group),
                "candidate_tickers": group["ticker"].nunique(),
                "available_rows": int(group["feature_status"].eq("AVAILABLE").sum()),
                "partial_rows": int(group["feature_status"].eq("PARTIAL").sum()),
                "missing_rows": int(group["feature_status"].eq("MISSING").sum()),
            }
        )
    session_path = output_root / "coverage_by_session.csv"
    pd.DataFrame(session_rows).to_csv(session_path, index=False)

    ticker_rows = []
    for ticker, group in frame.groupby("ticker", sort=True):
        ticker_rows.append(
            {
                "ticker": ticker,
                "first_feature_session": group["feature_session"].min().date().isoformat(),
                "last_feature_session": group["feature_session"].max().date().isoformat(),
                "candidate_rows": len(group),
                "available_rows": int(group["feature_status"].eq("AVAILABLE").sum()),
                "partial_rows": int(group["feature_status"].eq("PARTIAL").sum()),
                "missing_rows": int(group["feature_status"].eq("MISSING").sum()),
            }
        )
    ticker_path = output_root / "coverage_by_ticker.csv"
    pd.DataFrame(ticker_rows).to_csv(ticker_path, index=False)

    distribution_rows = []
    for column in FEATURE_COLUMNS:
        values = pd.to_numeric(frame[column], errors="coerce")
        finite = values[np.isfinite(values)]
        distribution_rows.append(
            {
                "feature": column,
                "finite_count": len(finite),
                "missing_count": int(values.isna().sum()),
                "min": float(finite.min()) if len(finite) else None,
                "p01": float(finite.quantile(0.01)) if len(finite) else None,
                "q25": float(finite.quantile(0.25)) if len(finite) else None,
                "median": float(finite.median()) if len(finite) else None,
                "q75": float(finite.quantile(0.75)) if len(finite) else None,
                "p99": float(finite.quantile(0.99)) if len(finite) else None,
                "max": float(finite.max()) if len(finite) else None,
                "zero_denominator_rows": int(
                    frame["missing_reasons"].fillna("").str.contains("INVALID_ZERO_DENOMINATOR").sum()
                )
                if column.startswith("foreign_net_to_volume") or column == "foreign_gross_to_volume_1"
                else 0,
            }
        )
    distribution_path = output_root / "feature_distribution.csv"
    pd.DataFrame(distribution_rows).to_csv(distribution_path, index=False)

    audit = {
        "status": "OFFLINE_FOREIGN_FLOW_FEATURE_AUDIT_COMPLETE",
        "schema_version": FEATURE_SCHEMA_VERSION,
        "feature_rows": int(len(frame)),
        "feature_tickers": int(frame["ticker"].nunique()),
        "feature_sessions": int(frame["feature_session"].nunique()),
        "first_feature_session": frame["feature_session"].min().date().isoformat(),
        "last_feature_session": frame["feature_session"].max().date().isoformat(),
        "feature_columns": list(FEATURE_COLUMNS),
        "coverage_by_session_path": str(session_path),
        "coverage_by_session_sha256": sha256_file(session_path),
        "coverage_by_ticker_path": str(ticker_path),
        "coverage_by_ticker_sha256": sha256_file(ticker_path),
        "feature_distribution_path": str(distribution_path),
        "feature_distribution_sha256": sha256_file(distribution_path),
        "metadata": dict(metadata or {}),
    }
    audit_path = output_root / "offline_feature_audit_manifest.json"
    audit["audit_manifest_path"] = str(audit_path)
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    audit["audit_manifest_sha256"] = sha256_file(audit_path)
    return audit


def run_offline_materialization(
    *,
    archive_root: str | Path,
    price_root: str | Path,
    official_session_csv: str | Path,
    security_master_csv: str | Path,
    output_root: str | Path,
) -> dict[str, object]:
    archive_root, price_root, output_root = map(Path, (archive_root, price_root, output_root))
    output_root.mkdir(parents=True, exist_ok=True)
    flow, archive_sessions, archive_meta = _read_archive(archive_root)
    sessions = _canonical_sessions(pd.read_csv(official_session_csv)["date"])
    volume, price_meta = _read_volume(price_root)
    master = pd.read_csv(security_master_csv)
    features, summary = materialize_foreign_flow_features(flow, volume, sessions, master)
    feature_path = output_root / "foreign_flow_features.parquet"
    features.to_parquet(feature_path, index=False)
    by_year = []
    for year, group in features.assign(year=features["feature_session"].dt.year).groupby("year"):
        by_year.append({
            "year": int(year),
            "candidate_rows": len(group),
            "available_rows": int(group["feature_status"].eq("AVAILABLE").sum()),
            "partial_rows": int(group["feature_status"].eq("PARTIAL").sum()),
            "missing_rows": int(group["feature_status"].eq("MISSING").sum()),
            "available_rate": float(group["feature_status"].eq("AVAILABLE").mean()),
        })
    coverage_path = output_root / "coverage_by_year.csv"
    pd.DataFrame(by_year).to_csv(coverage_path, index=False)
    reason_rows = []
    for row in summary["missing_reason_counts"].items():
        feature_reason, count = row
        feature, reason = feature_reason.split(":", 1)
        reason_rows.append({"feature": feature, "reason": reason, "rows": count})
    reasons_path = output_root / "missing_reason_counts.csv"
    pd.DataFrame(reason_rows).to_csv(reasons_path, index=False)
    report = {
        **summary,
        "archive": archive_meta,
        "archive_sessions": len(archive_sessions),
        "materialization_session_source": str(official_session_csv),
        "security_master_path": str(security_master_csv),
        "security_master_sha256": sha256_file(security_master_csv),
        "canonical_volume_source": str(price_root),
        **price_meta,
        "price_columns_consumed": ["ticker", "as_of_date", "volume"],
        "price_columns_not_consumed": [
            "nonregular_volume",
            "frequency",
            "regular_value",
            "raw_open",
            "raw_high",
            "raw_low",
            "raw_close",
        ],
        "feature_path": str(feature_path),
        "feature_sha256": sha256_file(feature_path),
        "coverage_by_year_path": str(coverage_path),
        "coverage_by_year_sha256": sha256_file(coverage_path),
        "missing_reason_counts_path": str(reasons_path),
        "missing_reason_counts_sha256": sha256_file(reasons_path),
        "contract_verdict": "FEATURE_CONTRACT_FROZEN_OFFLINE_ONLY_NO_PERFORMANCE_SELECTION",
    }
    (output_root / "materialization_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return report


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", required=True)
    parser.add_argument("--price-root", required=True)
    parser.add_argument("--official-session-csv", required=True)
    parser.add_argument("--security-master-csv", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    report = run_offline_materialization(
        archive_root=args.archive_root,
        price_root=args.price_root,
        official_session_csv=args.official_session_csv,
        security_master_csv=args.security_master_csv,
        output_root=args.output_root,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
