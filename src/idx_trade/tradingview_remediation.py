"""Pure diagnostics for the bounded TradingView remediation audit."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import math
from pathlib import Path
from typing import Any

import pandas as pd


STATUS_TAXONOMY = (
    "AVAILABLE",
    "SERIES_COMPLETED_EMPTY",
    "SYMBOL_ERROR",
    "TRANSPORT_TIMEOUT",
    "TRANSPORT_ERROR",
    "ENTITLEMENT_OR_PERMISSION_ERROR",
    "PROVIDER_ERROR",
    "UNCLASSIFIED_NO_DATA",
)


def classify_observation(
    *,
    periods: int,
    event_trace: Iterable[str],
    errors: Iterable[str] = (),
    timed_out: bool = False,
) -> str:
    """Classify only observable protocol evidence; never infer entitlement."""
    trace = {str(value).lower() for value in event_trace}
    messages = " ".join(str(value).lower() for value in errors)
    if "symbol_error" in trace or "symbol error" in messages:
        return "SYMBOL_ERROR"
    if any(token in messages for token in ("permission", "entitlement", "not authorized", "auth")):
        return "ENTITLEMENT_OR_PERMISSION_ERROR"
    if "transport_error" in trace or "websocket_error" in trace:
        return "TRANSPORT_ERROR"
    if periods > 0:
        return "AVAILABLE"
    if "series_completed" in trace:
        return "SERIES_COMPLETED_EMPTY"
    if timed_out:
        return "TRANSPORT_TIMEOUT" if not trace else "UNCLASSIFIED_NO_DATA"
    if errors:
        return "PROVIDER_ERROR"
    return "UNCLASSIFIED_NO_DATA"


def listing_aware_denominators(
    requests: pd.DataFrame,
    security_master: pd.DataFrame,
    official_sessions: set[str] | None,
) -> dict[str, int | None]:
    """Return requested, listed, and certified-session denominators."""
    pairs = requests[["ticker", "year", "start", "end"]].drop_duplicates().copy()
    master = security_master.copy()
    master["ticker"] = master["ticker"].astype(str).str.upper()
    master["listed_from"] = pd.to_datetime(master["listed_from"], errors="coerce").dt.date
    master["listed_to"] = pd.to_datetime(master["listed_to"], errors="coerce").dt.date
    pairs["era_start"] = pd.to_datetime(pairs["start"]).dt.date
    pairs["era_end"] = pd.to_datetime(pairs["end"]).dt.date
    merged = pairs.merge(master[["ticker", "listed_from", "listed_to"]], on="ticker", how="left")
    listed = (
        merged["listed_from"].isna() | (merged["listed_to"].isna() | (merged["listed_to"] >= merged["era_start"]))
    ) & (merged["listed_from"].isna() | (merged["listed_from"] <= merged["era_end"]))
    certified = None
    if official_sessions is not None:
        session_dates = {str(value) for value in official_sessions}
        certified = int(
            sum(
                any(
                    date_value in session_dates
                    for date_value in pd.date_range(row.era_start, row.era_end).strftime("%Y-%m-%d")
                )
                for row in merged.itertuples()
            )
        )
    return {
        "requested_ticker_era_pairs": int(len(pairs)),
        "known_listed_ticker_era_pairs": int(listed.sum()),
        "certified_session_ticker_era_pairs": certified,
    }


def volume_ratio_diagnostics(ratios: pd.Series | Iterable[float]) -> dict[str, Any]:
    """Describe ratios without applying a correction or acceptance decision."""
    values = pd.to_numeric(pd.Series(ratios), errors="coerce")
    values = values[values.notna() & values.map(math.isfinite) & (values >= 0)]
    quantiles = {f"q{int(level * 100):02d}": float(values.quantile(level)) for level in (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)}
    tolerances = {}
    for tolerance in (0.005, 0.01, 0.02, 0.05, 0.10):
        tolerances[f"within_{tolerance:.3f}"] = int(((values >= 1 - tolerance) & (values <= 1 + tolerance)).sum())
    clusters = {}
    for center in (0.01, 0.1, 1.0, 10.0, 100.0):
        clusters[str(center)] = int(((values >= center / 1.5) & (values <= center * 1.5)).sum())
    return {
        "count": int(len(values)),
        "min": float(values.min()) if len(values) else None,
        "max": float(values.max()) if len(values) else None,
        "mean": float(values.mean()) if len(values) else None,
        "quantiles": quantiles,
        "within_tolerance_counts": tolerances,
        "multiplicative_cluster_counts": clusters,
    }


def _near(left: Any, right: Any, tolerance: float) -> bool:
    if pd.isna(left) or pd.isna(right):
        return False
    scale = max(abs(float(right)), 1.0)
    return abs(float(left) - float(right)) <= tolerance * scale


def three_way_reconciliation(
    tv60: pd.DataFrame,
    tv1d: pd.DataFrame,
    canonical: pd.DataFrame,
    *,
    tolerance: float = 0.05,
) -> pd.DataFrame:
    """Classify daily rows without rescaling or selecting a preferred source."""
    key = ["ticker", "session_date"]
    def prepare(frame: pd.DataFrame, suffix: str) -> pd.DataFrame:
        data = frame.copy()
        if "date" in data.columns and "session_date" not in data.columns:
            data["session_date"] = pd.to_datetime(data["date"]).dt.strftime("%Y-%m-%d")
        data["session_date"] = data["session_date"].astype(str)
        return data[key + ["open", "high", "low", "close", "volume"]].rename(
            columns={field: f"{field}_{suffix}" for field in ("open", "high", "low", "close", "volume")}
        )

    merged = prepare(tv60, "tv60").merge(prepare(tv1d, "tv1d"), on=key, how="outer")
    canonical_prepared = prepare(canonical, "canonical")
    merged = merged.merge(canonical_prepared, on=key, how="outer")
    fields = ("open", "high", "low", "close", "volume")
    for field in fields:
        merged[f"tv60_tv1d_{field}_near"] = [
            _near(left, right, tolerance) for left, right in zip(merged[f"{field}_tv60"], merged[f"{field}_tv1d"])
        ]
        merged[f"tv60_canonical_{field}_near"] = [
            _near(left, right, tolerance) for left, right in zip(merged[f"{field}_tv60"], merged[f"{field}_canonical"])
        ]
        merged[f"tv1d_canonical_{field}_near"] = [
            _near(left, right, tolerance) for left, right in zip(merged[f"{field}_tv1d"], merged[f"{field}_canonical"])
        ]
    tv60_tv1d = merged[[f"tv60_tv1d_{field}_near" for field in fields]].all(axis=1)
    tv60_canonical = merged[[f"tv60_canonical_{field}_near" for field in fields]].all(axis=1)
    tv1d_canonical = merged[[f"tv1d_canonical_{field}_near" for field in fields]].all(axis=1)
    merged["three_way_class"] = "UNRESOLVED"
    merged.loc[tv60_tv1d & tv60_canonical & tv1d_canonical, "three_way_class"] = "TV60_APPROX_TV1D_APPROX_CANONICAL"
    merged.loc[~tv60_tv1d & tv1d_canonical, "three_way_class"] = "TV60_DIFF_TV1D_APPROX_CANONICAL"
    merged.loc[tv60_tv1d & ~tv1d_canonical, "three_way_class"] = "TV60_APPROX_TV1D_DIFF_CANONICAL"
    merged.loc[tv60_canonical & ~tv1d_canonical & ~tv60_tv1d, "three_way_class"] = "TV60_APPROX_CANONICAL_TV1D_DIFF"
    return merged


def pagination_boundary(trace: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize whether bounded pagination stopped with a deterministic reason."""
    steps = trace.get("steps", [])
    reasons = [step.get("reason") for step in steps if step.get("reason")]
    return {
        "steps": len(steps),
        "extended_steps": int(sum(bool(step.get("extended")) for step in steps)),
        "deterministic_stop": bool(trace.get("completion_reason")) and bool(reasons or trace.get("completion_reason")),
        "completion_reason": trace.get("completion_reason"),
        "reasons": reasons,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
