"""Read-only audit of frozen V4-3R market/Open inputs used by V4-X evidence.

No provider calls, model fitting/scoring, target materialization, or outcome
access. This verifies exact frozen file hashes and audits row-level semantics
that can otherwise silently distort causal feature/entry interpretation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPECTED = {
    "calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "panel": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
    "open_derivative_panel": "a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab",
    "open_derivative_manifest": "1a6bcc9c7fbbd967cdc69f8876fe1d4aa94b46c0e466469a9643da59251deb14",
    "overlay_parquet": "2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41",
    "overlay_manifest": "dfb7219bddec77ced3e3aadfaa2d85d04c19e1d9fd9a8af1badba523ecf91977",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    out["date"] = pd.to_datetime(out["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    return out


def verify(path: Path, key: str) -> str:
    actual = sha256_file(path)
    expected = EXPECTED[key]
    if actual != expected:
        raise RuntimeError(f"FROZEN_HASH_MISMATCH:{key}:{actual}!={expected}")
    return actual


def rolling_span_audit(panel: pd.DataFrame, calendar: pd.DataFrame) -> dict[str, Any]:
    index_by_date = dict(zip(calendar["date"], calendar["session_index"], strict=True))
    work = panel[["ticker", "date"]].copy()
    work["session_index"] = work["date"].map(index_by_date)
    if work["session_index"].isna().any():
        raise RuntimeError("PANEL_DATE_OUTSIDE_FROZEN_CALENDAR")
    work["session_index"] = work["session_index"].astype(int)

    output: dict[str, Any] = {}
    for lag in (5, 20, 60):
        spans: list[np.ndarray] = []
        for _, block in work.groupby("ticker", sort=False):
            ordered = block.sort_values("session_index", kind="mergesort")
            idx = ordered["session_index"].to_numpy(dtype=int)
            if len(idx) <= lag:
                continue
            spans.append(idx[lag:] - idx[:-lag])
        values = np.concatenate(spans) if spans else np.array([], dtype=int)
        output[f"row_lag_{lag}"] = {
            "comparisons": int(len(values)),
            "exact_official_session_span": int((values == lag).sum()),
            "longer_than_intended_span": int((values > lag).sum()),
            "longer_than_intended_rate": float((values > lag).mean()) if len(values) else None,
            "max_official_session_span": int(values.max()) if len(values) else None,
            "p99_official_session_span": float(np.quantile(values, 0.99)) if len(values) else None,
        }
    return output


def value_field_audit(panel: pd.DataFrame) -> dict[str, Any]:
    required = {"close", "volume", "regular_market_value"}
    missing = required - set(panel.columns)
    if missing:
        raise RuntimeError(f"PANEL_VALUE_FIELD_COLUMNS_MISSING:{sorted(missing)}")
    close = pd.to_numeric(panel["close"], errors="coerce").to_numpy(dtype=float)
    volume = pd.to_numeric(panel["volume"], errors="coerce").to_numpy(dtype=float)
    value = pd.to_numeric(panel["regular_market_value"], errors="coerce").to_numpy(dtype=float)
    expected_traded_value = close * volume
    mask = (
        np.isfinite(expected_traded_value)
        & np.isfinite(value)
        & (expected_traded_value > 0.0)
        & (value > 0.0)
    )
    ratio = value[mask] / expected_traded_value[mask]
    if not len(ratio):
        return {"comparable_rows": 0, "interpretation": "NO_COMPARABLE_POSITIVE_ROWS"}
    log_abs = np.abs(np.log(ratio))
    return {
        "comparable_rows": int(len(ratio)),
        "median_regular_market_value_over_close_x_volume": float(np.median(ratio)),
        "p01_ratio": float(np.quantile(ratio, 0.01)),
        "p99_ratio": float(np.quantile(ratio, 0.99)),
        "exact_close_x_volume_rows": int(np.isclose(ratio, 1.0, rtol=1e-12, atol=1e-12).sum()),
        "within_1pct_of_close_x_volume_rate": float((log_abs <= np.log(1.01)).mean()),
        "note": "Descriptive only. If ratio is ~1, regular_market_value behaves as same-session traded value (Close x Volume), not shares-outstanding market cap. Material deviations require provenance review before interpreting liquidity features.",
    }


def open_range_audit(name: str, opens: pd.DataFrame, panel: pd.DataFrame, value_column: str) -> dict[str, Any]:
    source = normalize_identity(opens[["ticker", "date", value_column]])
    if source.duplicated(["ticker", "date"]).any():
        raise RuntimeError(f"{name.upper()}_DUPLICATE_IDENTITY")
    merged = source.merge(
        panel[["ticker", "date", "low", "high"]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    finite = pd.to_numeric(merged[value_column], errors="coerce")
    finite_mask = np.isfinite(finite)
    missing_panel = finite_mask & merged["_merge"].ne("both")
    low = pd.to_numeric(merged["low"], errors="coerce")
    high = pd.to_numeric(merged["high"], errors="coerce")
    invalid_positive = finite_mask & finite.le(0.0)
    outside = finite_mask & merged["_merge"].eq("both") & ((finite < low) | (finite > high))
    return {
        "rows": int(len(source)),
        "finite_open_rows": int(finite_mask.sum()),
        "finite_rows_missing_canonical_panel_identity": int(missing_panel.sum()),
        "non_positive_finite_open_rows": int(invalid_positive.sum()),
        "finite_open_outside_canonical_low_high": int(outside.sum()),
        "first_outside_examples": merged.loc[outside, ["ticker", "date", value_column, "low", "high"]].head(10).astype(str).to_dict("records"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--open-derivative-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_root = args.artifact_root.resolve()
    open_root = args.open_derivative_root.resolve()
    overlay_root = args.overlay_root.resolve()

    paths = {
        "calendar": artifact_root / "official_exchange_sessions_1260.csv",
        "panel": artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet",
        "open_derivative_panel": open_root / "execution_open_candidate_panel_yahoo_tradingview.parquet",
        "open_derivative_manifest": open_root / "artifact_manifest.json",
        "overlay_parquet": overlay_root / "open_recovery_overlay.parquet",
        "overlay_manifest": overlay_root / "manifest.json",
    }
    hashes = {key: verify(path, key) for key, path in paths.items()}

    calendar = pd.read_csv(paths["calendar"])
    calendar["date"] = pd.to_datetime(calendar["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)
    if calendar["date"].duplicated().any():
        raise RuntimeError("FROZEN_CALENDAR_DUPLICATE_DATE")
    calendar["session_index"] = np.arange(len(calendar), dtype=int)

    panel = normalize_identity(pd.read_parquet(paths["panel"]))
    if panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("FROZEN_PANEL_DUPLICATE_IDENTITY")
    for column in ("low", "high", "close"):
        panel[column] = pd.to_numeric(panel[column], errors="coerce")
    invalid_hlc = (
        ~np.isfinite(panel["low"])
        | ~np.isfinite(panel["high"])
        | ~np.isfinite(panel["close"])
        | panel["low"].le(0.0)
        | panel["high"].le(0.0)
        | panel["close"].le(0.0)
        | panel["high"].lt(panel["low"])
        | panel["close"].lt(panel["low"])
        | panel["close"].gt(panel["high"])
    )

    derivative = pd.read_parquet(paths["open_derivative_panel"])
    if "open" not in derivative.columns:
        raise RuntimeError("DERIVATIVE_OPEN_COLUMN_MISSING")
    overlay = pd.read_parquet(paths["overlay_parquet"])
    recovered_column = "recovered_open" if "recovered_open" in overlay.columns else "open"
    if recovered_column not in overlay.columns:
        raise RuntimeError("OVERLAY_OPEN_COLUMN_MISSING")

    derivative_audit = open_range_audit("derivative", derivative, panel, "open")
    overlay_audit = open_range_audit("overlay", overlay, panel, recovered_column)

    derivative_view = normalize_identity(derivative[["ticker", "date", "open"]]).rename(columns={"open": "derivative_open"})
    overlay_view = normalize_identity(overlay[["ticker", "date", recovered_column]]).rename(columns={recovered_column: "overlay_open"})
    both = derivative_view.merge(overlay_view, on=["ticker", "date"], how="inner", validate="one_to_one")
    d = pd.to_numeric(both["derivative_open"], errors="coerce")
    o = pd.to_numeric(both["overlay_open"], errors="coerce")
    both_finite = np.isfinite(d) & np.isfinite(o)
    # Match the frozen historical runner's overlap consistency tolerance exactly.
    conflicts = both_finite & ~np.isclose(d, o, rtol=0.0, atol=1e-9)

    status = "V4X_FROZEN_MARKET_INPUT_AUDIT_PASS"
    critical_counts = {
        "invalid_canonical_hlc": int(invalid_hlc.sum()),
        "derivative_open_outside_range": int(derivative_audit["finite_open_outside_canonical_low_high"]),
        "overlay_open_outside_range": int(overlay_audit["finite_open_outside_canonical_low_high"]),
        "derivative_overlay_finite_conflicts": int(conflicts.sum()),
    }
    if any(critical_counts.values()):
        status = "V4X_FROZEN_MARKET_INPUT_AUDIT_CRITICAL_ERROR"

    output = {
        "schema_version": "v4x_frozen_market_input_audit_v2",
        "status": status,
        "hashes": hashes,
        "provider_calls": False,
        "target_accessed": False,
        "model_fit": False,
        "model_scored": False,
        "calendar_sessions": int(len(calendar)),
        "panel_rows": int(len(panel)),
        "panel_tickers": int(panel["ticker"].nunique()),
        "panel_columns": sorted(str(column) for column in panel.columns),
        "invalid_canonical_hlc_rows": int(invalid_hlc.sum()),
        "regular_market_value_semantics": value_field_audit(panel),
        "rolling_row_lag_semantics": rolling_span_audit(panel, calendar),
        "derivative_open": derivative_audit,
        "overlay_open": overlay_audit,
        "derivative_overlay_overlap_rows": int(len(both)),
        "derivative_overlay_both_finite_rows": int(both_finite.sum()),
        "derivative_overlay_finite_conflicts": int(conflicts.sum()),
        "critical_counts": critical_counts,
        "interpretation": {
            "rolling_lag_note": "V4 control uses ticker-row shift/rolling windows. Any longer-than-intended official-session spans are a semantic horizon drift, not future leakage, but can matter if frequent.",
            "open_note": "Any finite accepted Open outside the frozen canonical Low/High range is critical because V4 target entry trusts the derivative/overlay admission boundary.",
            "raw_price_note": "Repository canonicalization explicitly preserves vendor raw OHLC separately from adjusted close; this audit reports frozen panel columns and range semantics but does not independently reconstruct vendor raw bytes.",
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False))
    return 0 if status.endswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
