"""Outcome-blind offline materialization runner for Foreign Flow V2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .foreign_flow_features_v2 import FEATURE_COLUMNS_V2, build_foreign_flow_representation_v2


PRIMARY_VALUE_THRESHOLD_IDR = 1_000_000_000.0
PRIMARY_LIQUIDITY_LOOKBACK = 60
PRIMARY_MIN_ACTIVE_OBSERVATIONS = 20

RANK_FEATURES = {
    "xs_rank_foreign_flow_shock_1",
    "xs_rank_foreign_flow_shock_mean_5",
    "xs_rank_foreign_flow_shock_mean_20",
}

RANK_DERIVED_FEATURES = {
    "foreign_flow_price_divergence_5",
    "foreign_flow_price_divergence_20",
}

WARMUP_INDEX = {
    "foreign_participation_1": 0,
    "foreign_participation_mean_5": 4,
    "foreign_flow_shock_1": 10,
    "foreign_flow_shock_mean_5": 14,
    "foreign_flow_shock_mean_20": 29,
    "foreign_flow_shock_percentile_120": 70,
    "xs_rank_foreign_flow_shock_1": 10,
    "xs_rank_foreign_flow_shock_mean_5": 14,
    "xs_rank_foreign_flow_shock_mean_20": 29,
    "foreign_weighted_persistence_5": 14,
    "foreign_weighted_persistence_20": 29,
    "foreign_signed_streak_10": 0,
    "foreign_flow_acceleration_5_20": 29,
    "foreign_flow_price_divergence_5": 14,
    "foreign_flow_price_divergence_20": 29,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dates(values: pd.Series, *, name: str) -> pd.Series:
    raw = pd.Series(values)
    parsed = pd.to_datetime(raw, errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"{name} contains malformed dates")
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        parsed = parsed.dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
    return parsed.dt.normalize()


def _hash_pin(path: Path, expected: str, *, label: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    actual = sha256_file(path)
    if actual.lower() != expected.lower():
        raise RuntimeError(f"{label} SHA-256 mismatch: expected {expected}, got {actual}")
    return actual


def _normalize_master(master: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "listed_from", "listed_to"}
    missing = required - set(master.columns)
    if missing:
        raise ValueError(f"security master missing columns: {sorted(missing)}")
    out = master[["ticker", "listed_from", "listed_to"]].copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    out["listed_from"] = _dates(out["listed_from"], name="listed_from")
    out["listed_to"] = pd.to_datetime(out["listed_to"], errors="coerce")
    if isinstance(out["listed_to"].dtype, pd.DatetimeTZDtype):
        out["listed_to"] = out["listed_to"].dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
    out["listed_to"] = out["listed_to"].dt.normalize()
    if out["ticker"].eq("").any() or (~out["ticker"].str.fullmatch(r"[A-Z0-9]{4}")).any():
        raise ValueError("security master contains invalid tickers")
    if out.duplicated(["ticker", "listed_from"]).any():
        raise ValueError("security master contains duplicate listing identities")
    if (out["listed_to"].notna() & out["listed_to"].lt(out["listed_from"])).any():
        raise ValueError("security master contains invalid listing intervals")
    return out.sort_values(["ticker", "listed_from"], kind="mergesort").reset_index(drop=True)


def _listing_filter(
    panel: pd.DataFrame,
    master: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"ticker", "date", "close", "volume", "regular_market_value"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"market panel missing columns: {sorted(missing)}")
    data = panel.copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["date"] = _dates(data["date"], name="market panel date")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("market panel has duplicate ticker/date rows")
    if not data["date"].isin(set(sessions)).all():
        raise ValueError("market panel contains dates outside official sessions")
    unknown = sorted(set(data["ticker"]) - set(master["ticker"]))
    if unknown:
        raise ValueError(f"market panel contains tickers absent from security master: {unknown[:10]}")
    for column in ("close", "volume", "regular_market_value"):
        values = pd.to_numeric(data[column], errors="coerce")
        if values.notna().any() and (~np.isfinite(values.dropna())).any():
            raise ValueError(f"market panel has non-finite {column}")
        data[column] = values
    if (data["close"].dropna() <= 0).any():
        raise ValueError("market panel has non-positive close")
    if (data[["volume", "regular_market_value"]].dropna() < 0).any().any():
        raise ValueError("market panel has negative volume/value")

    intervals = {ticker: group for ticker, group in master.groupby("ticker", sort=False)}
    keep = pd.Series(False, index=data.index, dtype=bool)
    for ticker, indices in data.groupby("ticker", sort=False).groups.items():
        dates = data.loc[indices, "date"]
        match = pd.Series(False, index=indices, dtype=bool)
        for interval in intervals[ticker].itertuples(index=False):
            match |= dates.ge(interval.listed_from) & (
                pd.isna(interval.listed_to) | dates.le(interval.listed_to)
            )
        keep.loc[indices] = match.to_numpy(dtype=bool)
    removed = data.loc[~keep, ["ticker", "date"]].sort_values(["date", "ticker"], kind="mergesort")
    filtered = data.loc[keep].sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    return filtered, removed.reset_index(drop=True)


def build_causal_market_context(
    panel: pd.DataFrame,
    master: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build only the clean-V2 context fields needed by the V2 builder.

    The primary-liquid rule matches the clean-V2 causal rule: a ticker needs at
    least 20 finite regular-market-value observations in the trailing 60 official
    sessions and a median value of at least IDR 1 billion. Listing filtering is
    applied before any rolling state is constructed.
    """

    data, removed = _listing_filter(panel, master, sessions)
    session_index = {day: index for index, day in enumerate(sessions)}
    pieces: list[pd.DataFrame] = []
    for ticker, group in data.groupby("ticker", sort=False):
        frame = group.sort_values("date", kind="mergesort").copy()
        frame["close_return_5"] = frame["close"] / frame["close"].shift(5) - 1.0
        frame["close_return_20"] = frame["close"] / frame["close"].shift(20) - 1.0
        frame["_session_index"] = frame["date"].map(session_index).astype(int)
        counts: list[int] = []
        medians: list[float] = []
        session_indices = frame["_session_index"].to_numpy(dtype=int)
        values = frame["regular_market_value"].to_numpy(dtype=float)
        left = 0
        for right, index in enumerate(session_indices):
            lower = index - PRIMARY_LIQUIDITY_LOOKBACK + 1
            while left <= right and session_indices[left] < lower:
                left += 1
            window = values[left : right + 1]
            finite = window[np.isfinite(window)]
            counts.append(int(len(finite)))
            medians.append(float(np.median(finite)) if len(finite) else np.nan)
        frame["_liquidity_observations_60"] = counts
        frame["_median_regular_value_60"] = medians
        frame["universe_primary_liquid"] = (
            frame["_liquidity_observations_60"].ge(PRIMARY_MIN_ACTIVE_OBSERVATIONS)
            & frame["_median_regular_value_60"].notna()
            & frame["_median_regular_value_60"].ge(PRIMARY_VALUE_THRESHOLD_IDR)
        )
        pieces.append(frame)
    if not pieces:
        raise ValueError("listing-filtered market panel is empty")
    context = pd.concat(pieces, ignore_index=True, sort=False)
    context = context.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    context = context[
        [
            "ticker",
            "date",
            "universe_primary_liquid",
            "close",
            "regular_market_value",
            "close_return_5",
            "close_return_20",
        ]
    ]
    return context, removed


def _safe_relative_path(root: Path, relative: str) -> Path:
    path = (root / Path(relative)).resolve()
    if root.resolve() not in path.parents:
        raise RuntimeError(f"archive artifact escapes archive root: {relative}")
    return path


def read_verified_flow_archive(
    archive_root: Path,
    expected_manifest_sha256: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest_path = archive_root / "archive_manifest.json"
    manifest_sha = _hash_pin(manifest_path, expected_manifest_sha256, label="Foreign Flow archive manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "HISTORICAL_FOREIGN_FLOW_ARCHIVE_VERIFIED":
        raise ValueError("Foreign Flow archive manifest is not verified")
    normalized = [entry for entry in manifest.get("artifacts", []) if entry.get("kind") == "NORMALIZED_FOREIGN_FLOW"]
    expected_sessions = int(manifest.get("coverage_census", {}).get("expected_sessions", 0) or 0)
    if not expected_sessions:
        expected_sessions = len({Path(entry["path"]).parent.name for entry in normalized})
    if len(normalized) != expected_sessions:
        raise RuntimeError("archive normalized-flow artifact count is incomplete")

    frames: list[pd.DataFrame] = []
    session_dates: set[str] = set()
    normalized_hashes: list[dict[str, Any]] = []
    for entry in normalized:
        relative = str(entry["path"])
        path = _safe_relative_path(archive_root, relative)
        session_date = path.parent.name
        if session_date in session_dates:
            raise RuntimeError(f"duplicate archive flow session: {session_date}")
        session_dates.add(session_date)
        actual_sha = sha256_file(path)
        if actual_sha.lower() != str(entry["sha256"]).lower():
            raise RuntimeError(f"archive normalized-flow hash mismatch: {relative}")
        if path.stat().st_size != int(entry["bytes"]):
            raise RuntimeError(f"archive normalized-flow byte count mismatch: {relative}")
        frame = pd.read_parquet(path)
        if frame.empty:
            raise RuntimeError(f"archive normalized-flow file is empty: {relative}")
        if "session_date" not in frame.columns:
            raise ValueError(f"archive normalized-flow missing session_date: {relative}")
        actual_dates = set(_dates(frame["session_date"], name=f"{relative} session_date").dt.strftime("%Y-%m-%d"))
        if actual_dates != {session_date}:
            raise RuntimeError(f"archive normalized-flow date mismatch: {relative}")
        frames.append(frame)
        normalized_hashes.append({"path": relative, "sha256": actual_sha, "rows": int(len(frame))})
    flow = pd.concat(frames, ignore_index=True, sort=False)
    flow["session_date"] = _dates(flow["session_date"], name="archive session_date")
    return flow, {
        "archive_root": str(archive_root),
        "archive_manifest_path": str(manifest_path),
        "archive_manifest_sha256": manifest_sha,
        "archive_normalized_session_count": len(session_dates),
        "archive_normalized_row_count": int(len(flow)),
        "archive_normalized_artifact_count": len(normalized_hashes),
        "archive_normalized_first_session": min(session_dates) if session_dates else None,
        "archive_normalized_last_session": max(session_dates) if session_dates else None,
        "archive_normalized_artifacts": normalized_hashes,
        "archive_status": manifest.get("status"),
    }


def _restrict_flow_to_official_sessions(
    flow: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Keep only source sessions represented by the pinned research calendar.

    The accepted historical archive can extend beyond the clean-V2 research
    window.  Those rows remain part of the verified archive provenance but
    cannot be passed to the causal builder without a matching official
    next-session mapping.  Record the excluded boundary explicitly instead of
    silently dropping it.
    """
    allowed = set(sessions)
    outside = ~flow["session_date"].isin(allowed)
    excluded = flow.loc[outside, "session_date"]
    kept = flow.loc[~outside].copy().reset_index(drop=True)
    dates = pd.DatetimeIndex(excluded.drop_duplicates().sort_values())
    return kept, {
        "flow_rows_used": int(len(kept)),
        "flow_sessions_used": int(kept["session_date"].nunique()),
        "flow_rows_outside_official_calendar": int(outside.sum()),
        "flow_sessions_outside_official_calendar": int(len(dates)),
        "flow_sessions_outside_official_calendar_range": (
            [dates.min().date().isoformat(), dates.max().date().isoformat()] if len(dates) else []
        ),
    }


def _write_csv(frame: pd.DataFrame, path: Path) -> str:
    frame.to_csv(path, index=False)
    return sha256_file(path)


def _feature_availability(features: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    numeric = features[list(FEATURE_COLUMNS_V2)].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric.to_numpy(dtype=float))
    counts = finite.sum(axis=1)
    row_status = pd.Series(
        np.where(counts == len(FEATURE_COLUMNS_V2), "FULLY_AVAILABLE", np.where(counts == 0, "ALL_MISSING", "PARTIAL")),
        index=features.index,
    )
    row_availability = features[["ticker", "feature_session", "flow_through_session"]].copy()
    row_availability["finite_feature_count"] = counts
    row_availability["availability_status"] = row_status.to_numpy()
    report = {
        "fully_available_rows": int((row_status == "FULLY_AVAILABLE").sum()),
        "partial_rows": int((row_status == "PARTIAL").sum()),
        "all_missing_rows": int((row_status == "ALL_MISSING").sum()),
        "finite_counts": {column: int(finite[:, index].sum()) for index, column in enumerate(FEATURE_COLUMNS_V2)},
    }
    return row_availability, report


def _distribution(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in FEATURE_COLUMNS_V2:
        values = pd.to_numeric(features[column], errors="coerce")
        finite = values[np.isfinite(values)]
        rows.append(
            {
                "feature": column,
                "finite_count": int(len(finite)),
                "missing_count": int(values.isna().sum()),
                "min": None if finite.empty else float(finite.min()),
                "p01": None if finite.empty else float(finite.quantile(0.01)),
                "q25": None if finite.empty else float(finite.quantile(0.25)),
                "median": None if finite.empty else float(finite.median()),
                "q75": None if finite.empty else float(finite.quantile(0.75)),
                "p99": None if finite.empty else float(finite.quantile(0.99)),
                "max": None if finite.empty else float(finite.max()),
            }
        )
    return pd.DataFrame(rows)


def _missingness_diagnostics(features: pd.DataFrame, context: pd.DataFrame, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    session_index = {day: index for index, day in enumerate(sessions)}
    lookup = context.set_index(["ticker", "date"])["universe_primary_liquid"]
    rows: list[dict[str, Any]] = []
    for feature in FEATURE_COLUMNS_V2:
        missing = features[feature].isna()
        primary = features.apply(
            lambda row: bool(lookup.get((row["ticker"], row["flow_through_session"]), False)), axis=1
        )
        indices = features["flow_through_session"].map(session_index).astype(int)
        warmup = missing & indices.lt(WARMUP_INDEX[feature])
        not_primary = (
            missing & ~primary
            if feature in (RANK_FEATURES | RANK_DERIVED_FEATURES)
            else pd.Series(False, index=features.index)
        )
        rows.append(
            {
                "feature": feature,
                "rows": int(len(features)),
                "finite_rows": int((~missing).sum()),
                "missing_rows": int(missing.sum()),
                "warmup_missing_rows": int((warmup & ~not_primary).sum()),
                "not_primary_not_applicable_rows": int(not_primary.sum()),
                "source_data_or_invalid_rows": int((missing & ~warmup & ~not_primary).sum()),
                "warmup_index_threshold": WARMUP_INDEX[feature],
            }
        )
    return pd.DataFrame(rows)


def _coverage_by_year(features: pd.DataFrame) -> pd.DataFrame:
    data = features.copy()
    data["year"] = pd.to_datetime(data["feature_session"]).dt.year
    numeric = data[list(FEATURE_COLUMNS_V2)].apply(pd.to_numeric, errors="coerce")
    data["finite_feature_count"] = np.isfinite(numeric.to_numpy(dtype=float)).sum(axis=1)
    data["availability_status"] = np.where(
        data["finite_feature_count"].eq(len(FEATURE_COLUMNS_V2)), "FULLY_AVAILABLE",
        np.where(data["finite_feature_count"].eq(0), "ALL_MISSING", "PARTIAL"),
    )
    rows: list[dict[str, Any]] = []
    for (year, feature), group in (
        data.melt(id_vars=["year", "availability_status"], value_vars=list(FEATURE_COLUMNS_V2), var_name="feature", value_name="value")
        .groupby(["year", "feature"], sort=True)
    ):
        rows.append(
            {
                "year": int(year),
                "feature": feature,
                "rows": int(len(group)),
                "finite_rows": int(np.isfinite(pd.to_numeric(group["value"], errors="coerce")).sum()),
                "fully_available_rows": int((group["availability_status"] == "FULLY_AVAILABLE").sum()),
                "partial_rows": int((group["availability_status"] == "PARTIAL").sum()),
                "all_missing_rows": int((group["availability_status"] == "ALL_MISSING").sum()),
            }
        )
    return pd.DataFrame(rows)


def _coverage_by_source_session(features: pd.DataFrame, context: pd.DataFrame, flow: pd.DataFrame) -> pd.DataFrame:
    numeric = features[list(FEATURE_COLUMNS_V2)].apply(pd.to_numeric, errors="coerce")
    status = pd.Series(
        np.where(
            np.isfinite(numeric.to_numpy(dtype=float)).sum(axis=1) == len(FEATURE_COLUMNS_V2), "FULLY_AVAILABLE",
            np.where(np.isfinite(numeric.to_numpy(dtype=float)).sum(axis=1) == 0, "ALL_MISSING", "PARTIAL"),
        ), index=features.index,
    )
    feature = features.copy()
    feature["availability_status"] = status.to_numpy()
    context_summary = context.groupby("date", sort=True).agg(
        context_rows=("ticker", "size"),
        primary_liquid_rows=("universe_primary_liquid", "sum"),
    ).reset_index().rename(columns={"date": "flow_through_session"})
    flow_summary = flow.groupby("session_date", sort=True).agg(
        flow_rows=("ticker", "size"),
        flow_tickers=("ticker", "nunique"),
    ).reset_index().rename(columns={"session_date": "flow_through_session"})
    output_summary = feature.groupby("flow_through_session", sort=True).agg(
        output_rows=("ticker", "size"),
        output_tickers=("ticker", "nunique"),
        fully_available_rows=("availability_status", lambda s: int((s == "FULLY_AVAILABLE").sum())),
        partial_rows=("availability_status", lambda s: int((s == "PARTIAL").sum())),
        all_missing_rows=("availability_status", lambda s: int((s == "ALL_MISSING").sum())),
    ).reset_index()
    return context_summary.merge(flow_summary, on="flow_through_session", how="outer").merge(
        output_summary, on="flow_through_session", how="outer"
    ).sort_values("flow_through_session", kind="mergesort").reset_index(drop=True)


def _verify_rank_scope(features: pd.DataFrame, context: pd.DataFrame) -> tuple[bool, dict[str, int]]:
    source_scope = features[["ticker", "flow_through_session"]].merge(
        context[["ticker", "date", "universe_primary_liquid"]].rename(
            columns={"date": "flow_through_session"}
        ),
        on=["ticker", "flow_through_session"],
        how="left",
        validate="one_to_one",
    )
    source_primary = (
        source_scope["universe_primary_liquid"].astype("boolean").fillna(False).to_numpy(dtype=bool)
    )
    valid = True
    bad_rows: dict[str, int] = {}
    for column in RANK_FEATURES | RANK_DERIVED_FEATURES:
        values = pd.to_numeric(features[column], errors="coerce")
        finite = values.notna().to_numpy()
        bad = int((finite & ~source_primary).sum())
        bad_rows[column] = bad
        if bad:
            valid = False
    for column in RANK_FEATURES:
        values = pd.to_numeric(features[column], errors="coerce").dropna()
        if not values.empty and ((values < 0).any() or (values > 1).any()):
            valid = False
    return valid, bad_rows


def run_offline_materialization(
    *,
    archive_root: Path,
    panel_path: Path,
    official_session_csv: Path,
    security_master_csv: Path,
    output_root: Path,
    expected_archive_manifest_sha256: str,
    expected_panel_sha256: str,
    expected_calendar_sha256: str,
    expected_security_master_sha256: str,
) -> dict[str, Any]:
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError(f"output directory must be new or empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    panel_sha = _hash_pin(panel_path, expected_panel_sha256, label="canonical market panel")
    calendar_sha = _hash_pin(official_session_csv, expected_calendar_sha256, label="official session calendar")
    master_sha = _hash_pin(security_master_csv, expected_security_master_sha256, label="security master")
    sessions_frame = pd.read_csv(official_session_csv)
    if "date" not in sessions_frame.columns:
        raise ValueError("official session calendar must contain date")
    sessions = pd.DatetimeIndex(_dates(sessions_frame["date"], name="official session"))
    if sessions.has_duplicates:
        raise ValueError("official session calendar contains duplicates")

    master = _normalize_master(pd.read_csv(security_master_csv))
    panel = pd.read_parquet(panel_path)
    context, listing_removed = build_causal_market_context(panel, master, sessions)
    flow, archive_meta = read_verified_flow_archive(archive_root, expected_archive_manifest_sha256)
    flow, calendar_scope = _restrict_flow_to_official_sessions(flow, sessions)
    if flow.empty:
        raise RuntimeError("Foreign Flow archive has no rows inside the official research calendar")
    archive_meta.update(calendar_scope)
    volume = context[["ticker", "date"]].merge(
        panel[["ticker", "date", "volume"]].assign(
            ticker=lambda frame: frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip(),
            date=lambda frame: _dates(frame["date"], name="panel volume date"),
        ),
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )[["ticker", "date", "volume"]].rename(columns={"volume": "raw_volume"})

    features = build_foreign_flow_representation_v2(
        flow_frame=flow,
        volume_frame=volume,
        market_context=context,
        security_master=master,
        official_sessions=sessions,
    )
    feature_path = output_root / "foreign_flow_representation_v2.parquet"
    features.to_parquet(feature_path, index=False)

    context_path = output_root / "causal_market_context.parquet"
    context.to_parquet(context_path, index=False)
    listing_path = output_root / "listing_interval_exclusions.csv"
    listing_sha = _write_csv(listing_removed, listing_path)
    row_availability, availability = _feature_availability(features)
    row_path = output_root / "row_availability.csv"
    row_sha = _write_csv(row_availability, row_path)
    year_frame = _coverage_by_year(features)
    year_path = output_root / "coverage_by_year.csv"
    year_sha = _write_csv(year_frame, year_path)
    session_frame = _coverage_by_source_session(features, context, flow)
    session_path = output_root / "coverage_by_source_session.csv"
    session_sha = _write_csv(session_frame, session_path)
    distribution_frame = _distribution(features)
    distribution_path = output_root / "feature_distribution.csv"
    distribution_sha = _write_csv(distribution_frame, distribution_path)
    missingness_frame = _missingness_diagnostics(features, context, sessions)
    missingness_path = output_root / "missingness_diagnostics.csv"
    missingness_sha = _write_csv(missingness_frame, missingness_path)

    feature_dates = pd.to_datetime(features["feature_session"])
    through_dates = pd.to_datetime(features["flow_through_session"])
    next_session = {sessions[index]: sessions[index + 1] for index in range(len(sessions) - 1)}
    next_ok = all(next_session.get(day) == feature_day for day, feature_day in zip(through_dates, feature_dates, strict=True))
    rank_scope_ok, rank_scope_bad_rows = _verify_rank_scope(features, context)
    if not next_ok:
        raise RuntimeError("feature_session is not the next official session for every row")
    if not rank_scope_ok:
        raise RuntimeError("cross-sectional rank scope is not primary-liquid-only")

    finite_matrix = np.isfinite(features[list(FEATURE_COLUMNS_V2)].to_numpy(dtype=float))
    if features.duplicated(["ticker", "feature_session"]).any():
        raise RuntimeError("V2 output has duplicate ticker/feature-session rows")
    if finite_matrix.size and np.isinf(features[list(FEATURE_COLUMNS_V2)].to_numpy(dtype=float)).any():
        raise RuntimeError("V2 output contains infinity")

    input_manifest = {
        "status": "FOREIGN_FLOW_V2_INPUTS_HASH_VERIFIED",
        "archive_manifest": archive_meta,
        "market_panel": {"path": str(panel_path), "sha256": panel_sha},
        "official_sessions": {"path": str(official_session_csv), "sha256": calendar_sha, "rows": int(len(sessions)), "first": sessions.min().date().isoformat(), "last": sessions.max().date().isoformat()},
        "security_master": {"path": str(security_master_csv), "sha256": master_sha, "rows": int(len(master)), "tickers": int(master["ticker"].nunique())},
        "panel_rows_before_listing_filter": int(len(panel)),
        "panel_rows_after_listing_filter": int(len(context)),
        "listing_excluded_rows": int(len(listing_removed)),
        "flow_rows_used": calendar_scope["flow_rows_used"],
        "flow_sessions_used": calendar_scope["flow_sessions_used"],
        "flow_rows_outside_official_calendar": calendar_scope["flow_rows_outside_official_calendar"],
        "flow_sessions_outside_official_calendar": calendar_scope["flow_sessions_outside_official_calendar"],
        "flow_sessions_outside_official_calendar_range": calendar_scope[
            "flow_sessions_outside_official_calendar_range"
        ],
        "no_provider_calls": True,
        "outcome_blind": True,
    }
    input_manifest_path = output_root / "input_manifest.json"
    input_manifest_path.write_text(json.dumps(input_manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    summary = {
        "status": "FOREIGN_FLOW_REPRESENTATION_V2_OFFLINE_CENSUS_COMPLETE",
        "feature_columns": list(FEATURE_COLUMNS_V2),
        "feature_rows": int(len(features)),
        "feature_tickers": int(features["ticker"].nunique()),
        "feature_sessions": int(features["feature_session"].nunique()),
        "flow_through_session_range": [through_dates.min().date().isoformat(), through_dates.max().date().isoformat()] if len(features) else [],
        "feature_session_range": [feature_dates.min().date().isoformat(), feature_dates.max().date().isoformat()] if len(features) else [],
        "archive_normalized_session_range": [
            archive_meta["archive_normalized_first_session"], archive_meta["archive_normalized_last_session"]
        ] if archive_meta.get("archive_normalized_first_session") else [],
        "materialized_flow_session_range": [
            flow["session_date"].min().date().isoformat(), flow["session_date"].max().date().isoformat()
        ] if len(flow) else [],
        "flow_rows_outside_official_calendar": calendar_scope["flow_rows_outside_official_calendar"],
        "flow_sessions_outside_official_calendar": calendar_scope["flow_sessions_outside_official_calendar"],
        "availability": availability,
        "finite_availability_verified": True,
        "duplicate_rows": int(features.duplicated(["ticker", "feature_session"]).sum()),
        "infinity_values": 0,
        "listing_interval_excluded_rows": int(len(listing_removed)),
        "listing_interval_excluded_tickers": int(listing_removed["ticker"].nunique()),
        "causality_next_official_verified": bool(next_ok),
        "own_history_current_observation_excluded_by_frozen_builder": True,
        "cross_sectional_rank_primary_liquid_only_verified": bool(rank_scope_ok),
        "rank_scope_bad_rows_by_feature": rank_scope_bad_rows,
        "primary_liquid_context_rows": int(context["universe_primary_liquid"].sum()),
        "primary_liquid_context_tickers": int(context.loc[context["universe_primary_liquid"], "ticker"].nunique()),
        "input_manifest_path": str(input_manifest_path),
        "input_manifest_sha256": sha256_file(input_manifest_path),
        "artifacts": {
            "foreign_flow_representation_v2.parquet": sha256_file(feature_path),
            "causal_market_context.parquet": sha256_file(context_path),
            "listing_interval_exclusions.csv": listing_sha,
            "row_availability.csv": row_sha,
            "coverage_by_year.csv": year_sha,
            "coverage_by_source_session.csv": session_sha,
            "feature_distribution.csv": distribution_sha,
            "missingness_diagnostics.csv": missingness_sha,
            "input_manifest.json": input_manifest["input_manifest_sha256"] if "input_manifest_sha256" in input_manifest else sha256_file(input_manifest_path),
        },
        "prohibited_actions": {
            "provider_calls": False,
            "model_fit": False,
            "model_scoring": False,
            "outcomes_or_labels_accessed": False,
            "fresh_forward_accessed": False,
            "v1_alpha_artifacts_accessed": False,
            "free_float_or_effective_supply_used": False,
        },
    }
    summary_path = output_root / "audit_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    manifest = {
        "status": "FOREIGN_FLOW_REPRESENTATION_V2_OFFLINE_CENSUS_COMPLETE",
        "schema": "idx-trade/foreign-flow-representation-v2-offline-census-v1",
        "inputs": input_manifest,
        "summary": summary,
        "artifacts": {
            **summary["artifacts"],
            "audit_summary.json": sha256_file(summary_path),
        },
        "feature_builder": "idx_trade.foreign_flow_features_v2.build_foreign_flow_representation_v2",
        "primary_liquid_rule": {
            "lookback_official_sessions": PRIMARY_LIQUIDITY_LOOKBACK,
            "minimum_finite_observations": PRIMARY_MIN_ACTIVE_OBSERVATIONS,
            "median_regular_market_value_idr": PRIMARY_VALUE_THRESHOLD_IDR,
        },
        "no_performance_selection": True,
        "no_provider_calls": True,
        "outcome_blind": True,
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return {
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "summary_path": str(summary_path),
        **summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--official-session-csv", required=True, type=Path)
    parser.add_argument("--security-master", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--expected-archive-manifest-sha256", required=True)
    parser.add_argument("--expected-panel-sha256", required=True)
    parser.add_argument("--expected-calendar-sha256", required=True)
    parser.add_argument("--expected-security-master-sha256", required=True)
    args = parser.parse_args()
    result = run_offline_materialization(
        archive_root=args.archive_root,
        panel_path=args.panel,
        official_session_csv=args.official_session_csv,
        security_master_csv=args.security_master,
        output_root=args.output_root,
        expected_archive_manifest_sha256=args.expected_archive_manifest_sha256,
        expected_panel_sha256=args.expected_panel_sha256,
        expected_calendar_sha256=args.expected_calendar_sha256,
        expected_security_master_sha256=args.expected_security_master_sha256,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
