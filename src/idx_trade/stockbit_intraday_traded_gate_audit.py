from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from .provenance import sha256_file
from .security_master import normalise_ticker
from .stockbit_intraday_capture import _safe_headers
from .stockbit_intraday_farm import _atomic_csv, _atomic_json, _load_frozen_day
from .tier2_open_audit import redact_secrets


IDX_STOCK_SUMMARY_ENDPOINT = "https://api.zpi.web.id/v1/finance:idx/stock-summary"
EXPECTED_BROAD_MANIFEST_SHA256 = "c59949645e88e71fb72c5bbec53fca43b0ef1d62dd70f3960299b3d695a9807a"
EXPECTED_UNIVERSE_ROWS = 962


@dataclass(frozen=True)
class GateConfusion:
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int

    @property
    def precision(self) -> float | None:
        denominator = self.true_positive + self.false_positive
        return self.true_positive / denominator if denominator else None

    @property
    def recall(self) -> float | None:
        denominator = self.true_positive + self.false_negative
        return self.true_positive / denominator if denominator else None


def _number(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def _provider_date(value: object) -> date | None:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).date()


def parse_stock_summary_payload(payload: object, *, expected_date: date) -> pd.DataFrame:
    if not isinstance(payload, dict):
        raise ValueError("IDX stock-summary payload must be an object")
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError("IDX stock-summary payload missing data list")

    records_total = payload.get("recordsTotal")
    if records_total not in (None, ""):
        try:
            total = int(records_total)
        except (TypeError, ValueError) as error:
            raise ValueError("IDX stock-summary recordsTotal is invalid") from error
        if total > len(rows):
            raise ValueError(
                f"IDX stock-summary response appears truncated: data={len(rows)} recordsTotal={total}"
            )

    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = normalise_ticker(row.get("StockCode") or "")
        if not ticker or not pd.Series([ticker]).str.fullmatch(r"[A-Z0-9]{4}", na=False).iloc[0]:
            continue
        row_date = _provider_date(row.get("Date"))
        if row_date != expected_date:
            raise ValueError(
                f"IDX stock-summary wrong/ambiguous session for {ticker}: {row.get('Date')}"
            )
        normalized.append(
            {
                "ticker": ticker,
                "session_date": row_date.isoformat(),
                "volume": _number(row.get("Volume")),
                "value": _number(row.get("Value")),
                "frequency": _number(row.get("Frequency")),
                "raw_close": _number(row.get("Close")),
                "raw_high": _number(row.get("High")),
                "raw_low": _number(row.get("Low")),
            }
        )

    frame = pd.DataFrame(normalized)
    if frame.empty:
        raise ValueError("IDX stock-summary normalized snapshot is empty")

    duplicates = frame[frame.duplicated("ticker", keep=False)].copy()
    if not duplicates.empty:
        value_columns = ["session_date", "volume", "value", "frequency", "raw_close", "raw_high", "raw_low"]
        conflicts = duplicates.groupby("ticker", dropna=False)[value_columns].nunique(dropna=False)
        if bool((conflicts > 1).any(axis=None)):
            bad = sorted(conflicts[(conflicts > 1).any(axis=1)].index.astype(str).tolist())
            raise ValueError(f"conflicting duplicate IDX stock-summary ticker rows: {bad[:20]}")
        frame = frame.drop_duplicates("ticker", keep="first")

    return frame.sort_values("ticker").reset_index(drop=True)


def _activity_columns(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data["volume_gt0"] = pd.to_numeric(data["volume"], errors="coerce").gt(0)
    data["value_gt0"] = pd.to_numeric(data["value"], errors="coerce").gt(0)
    data["frequency_gt0"] = pd.to_numeric(data["frequency"], errors="coerce").gt(0)
    data["activity_or"] = data[["volume_gt0", "value_gt0", "frequency_gt0"]].any(axis=1)
    return data


def confusion_for_rule(comparison: pd.DataFrame, rule: str) -> GateConfusion:
    if rule not in comparison.columns:
        raise KeyError(rule)
    observed_success = comparison["stockbit_status"].eq("SUCCESS")
    predicted = comparison[rule].fillna(False).astype(bool)
    return GateConfusion(
        true_positive=int((predicted & observed_success).sum()),
        false_positive=int((predicted & ~observed_success).sum()),
        false_negative=int((~predicted & observed_success).sum()),
        true_negative=int((~predicted & ~observed_success).sum()),
    )


def build_comparison(
    universe: pd.DataFrame,
    broad_status: pd.DataFrame,
    idx_summary: pd.DataFrame,
) -> pd.DataFrame:
    required_status = {"ticker", "status"}
    if not required_status.issubset(broad_status.columns):
        raise ValueError("broad Stockbit status artifact missing ticker/status")

    status = broad_status.copy()
    status["ticker"] = status["ticker"].map(normalise_ticker)
    if status["ticker"].duplicated().any():
        raise ValueError("broad Stockbit status artifact has duplicate tickers")
    observed = set(status["status"].dropna().astype(str))
    if not observed.issubset({"SUCCESS", "REQUEST_ERROR"}):
        raise ValueError(f"unexpected broad Stockbit statuses: {sorted(observed)}")

    base = universe[["ticker"]].copy()
    base["ticker"] = base["ticker"].map(normalise_ticker)
    merged = base.merge(
        status[["ticker", "status"]].rename(columns={"status": "stockbit_status"}),
        on="ticker",
        how="left",
        validate="one_to_one",
    )
    if merged["stockbit_status"].isna().any():
        missing = merged.loc[merged["stockbit_status"].isna(), "ticker"].tolist()
        raise ValueError(f"missing broad Stockbit statuses for: {missing[:20]}")

    summary = _activity_columns(idx_summary)
    merged = merged.merge(summary, on="ticker", how="left", validate="one_to_one")
    merged["idx_summary_present"] = merged["session_date"].notna()
    for column in ("volume_gt0", "value_gt0", "frequency_gt0", "activity_or"):
        merged[column] = merged[column].fillna(False).astype(bool)
    return merged.sort_values("ticker").reset_index(drop=True)


def _request_summary(session: requests.Session, api_key: str, *, expected_date: date) -> tuple[object, dict[str, Any]]:
    try:
        response = session.get(
            IDX_STOCK_SUMMARY_ENDPOINT,
            params={"length": 1000, "start": 0, "date": expected_date.isoformat()},
            headers={"x-api-key": api_key},
            timeout=60,
        )
    except Exception as error:
        raise RuntimeError(
            str(redact_secrets(f"IDX stock-summary request failed: {type(error).__name__}: {error}", (api_key,)))
        ) from error
    safe = _safe_headers(response)
    if response.status_code != 200:
        raise RuntimeError(f"IDX stock-summary HTTP_{response.status_code}")
    try:
        payload = response.json()
    except Exception as error:
        raise RuntimeError("IDX stock-summary returned invalid JSON") from error
    return payload, safe


def _manifest(root: Path, files: list[Path]) -> dict[str, Any]:
    hashes = {path.name: sha256_file(path) for path in files}
    payload = {"files": hashes}
    path = root / "artifact_manifest.json"
    _atomic_json(path, payload)
    payload["manifest_sha256"] = sha256_file(path)
    return payload


def run_audit(
    broad_root: Path,
    output_root: Path,
    *,
    expected_date: date,
    api_key: str,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    broad_manifest = broad_root / "artifact_manifest.json"
    if sha256_file(broad_manifest) != EXPECTED_BROAD_MANIFEST_SHA256:
        raise ValueError("broad-census artifact manifest hash mismatch")

    universe, metadata = _load_frozen_day(broad_root, expected_date=expected_date)
    if len(universe) != EXPECTED_UNIVERSE_ROWS:
        raise ValueError(f"unexpected frozen universe size: {len(universe)}")

    broad_status_path = broad_root / "final" / "stockbit_intraday_ticker_status.csv"
    broad_status = pd.read_csv(broad_status_path)
    if len(broad_status) != len(universe):
        raise ValueError("broad Stockbit status row count does not match frozen universe")

    if output_root.exists():
        if not output_root.is_dir() or any(output_root.iterdir()):
            raise FileExistsError("refusing to overwrite non-empty traded-gate audit root")
    else:
        output_root.mkdir(parents=True, exist_ok=False)

    payload, quota = _request_summary(session or requests.Session(), api_key, expected_date=expected_date)
    raw_path = output_root / "idx_stock_summary_raw.json"
    _atomic_json(raw_path, payload)
    idx_summary = parse_stock_summary_payload(payload, expected_date=expected_date)
    summary_rows_path = output_root / "idx_stock_summary_normalized.csv"
    _atomic_csv(summary_rows_path, idx_summary)

    comparison = build_comparison(universe, broad_status, idx_summary)
    comparison_path = output_root / "stockbit_idx_activity_comparison.csv"
    _atomic_csv(comparison_path, comparison)

    rule_metrics: dict[str, Any] = {}
    for rule in ("volume_gt0", "frequency_gt0", "value_gt0", "activity_or"):
        confusion = confusion_for_rule(comparison, rule)
        predicted_calls = int(comparison[rule].sum())
        rule_metrics[rule] = {
            "true_positive": confusion.true_positive,
            "false_positive": confusion.false_positive,
            "false_negative": confusion.false_negative,
            "true_negative": confusion.true_negative,
            "precision": confusion.precision,
            "recall": confusion.recall,
            "predicted_stockbit_chart_calls": predicted_calls,
            "stockbit_calls_saved_vs_all_962": len(comparison) - predicted_calls,
            "false_negative_tickers": comparison.loc[
                ~comparison[rule] & comparison["stockbit_status"].eq("SUCCESS"), "ticker"
            ].tolist(),
            "false_positive_tickers": comparison.loc[
                comparison[rule] & ~comparison["stockbit_status"].eq("SUCCESS"), "ticker"
            ].tolist(),
        }

    selected = rule_metrics["activity_or"]
    predicted = int(selected["predicted_stockbit_chart_calls"])
    burden = {
        str(sessions): {
            "stockbit_chart_calls": predicted * sessions,
            "idx_gate_calls": sessions,
            "total_calls": (predicted + 1) * sessions,
        }
        for sessions in (20, 21, 22)
    }

    report: dict[str, Any] = {
        "expected_date": expected_date.isoformat(),
        "frozen_universe_rows": len(universe),
        "ticker_list_sha256": metadata.get("ticker_list_sha256"),
        "universe_snapshot_sha256": metadata.get("universe_snapshot_sha256"),
        "broad_manifest_sha256": EXPECTED_BROAD_MANIFEST_SHA256,
        "idx_summary_rows": len(idx_summary),
        "idx_summary_coverage_of_universe": int(comparison["idx_summary_present"].sum()),
        "stockbit_success": int(comparison["stockbit_status"].eq("SUCCESS").sum()),
        "stockbit_non_success": int((~comparison["stockbit_status"].eq("SUCCESS")).sum()),
        "field_non_null": {
            column: int(idx_summary[column].notna().sum())
            for column in ("volume", "value", "frequency")
        },
        "rules": rule_metrics,
        "activity_or_monthly_burden": burden,
        "quota_headers": quota,
        "accepted_zero_false_negative_gate": int(selected["false_negative"]) == 0,
    }
    report_path = output_root / "run_summary.json"
    _atomic_json(report_path, report)
    manifest = _manifest(output_root, [raw_path, summary_rows_path, comparison_path, report_path])
    report["artifact_manifest_sha256"] = manifest["manifest_sha256"]
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit an IDX traded-today gate for Stockbit intraday capture")
    parser.add_argument("--broad-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.execute:
        print(
            json.dumps(
                {
                    "mode": "DRY_RUN",
                    "expected_date": args.expected_date,
                    "estimated_billable_idx_summary_calls": 1,
                    "broad_root": str(args.broad_root),
                    "output_root": str(args.output_root),
                },
                indent=2,
            )
        )
        return 0

    api_key = os.environ.get("ZAPI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ZAPI_API_KEY is required for --execute")
    report = run_audit(
        args.broad_root,
        args.output_root,
        expected_date=date.fromisoformat(args.expected_date),
        api_key=api_key,
    )
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
