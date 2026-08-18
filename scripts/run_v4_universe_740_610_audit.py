"""Outcome-blind exact diff audit: V4 primary-liquid 740 vs CA-support 610.

Reads only frozen identity/liquidity/tradability/security-master inputs and the
frozen CA continuity ledger. It never reads targets, returns, ranks, model
artifacts, predictions, performance, or protected-forward data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.ranking_v4_3_preregistration import build_primary_liquid_state
from idx_trade.v4_universe_740_610_audit import build_diff_audit, normalize_date, normalize_ticker


PINNED = {
    "calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "panel": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
    "security_master": "9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9",
    "anchors": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
    "continuity_ledger": "52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb",
}
EXPECTED_PRIMARY_TICKERS = 740
EXPECTED_CA_TICKERS = 610
EXPECTED_DIFF_TICKERS = 130
EXPECTED_VALIDATION_DATES = 600
EXPECTED_VALIDATION_START = pd.Timestamp("2023-12-28")
EXPECTED_VALIDATION_END = pd.Timestamp("2026-07-17")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise RuntimeError(f"REQUIRED_INPUT_MISSING:{label}:{path}")
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"PINNED_INPUT_HASH_MISMATCH:{label}:{actual}")
    return actual


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def count_dict(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts(dropna=False).sort_index().items()}


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    paths = {
        "calendar": args.artifact_root / "official_exchange_sessions_1260.csv",
        "panel": args.artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet",
        "security_master": args.artifact_root / "security_master_1260.csv",
        "anchors": args.artifact_root / "tradability_anchors_1260.csv",
        "continuity_ledger": args.continuity_ledger,
    }
    hashes = {name: verify(path, PINNED[name], name) for name, path in paths.items()}

    calendar = pd.read_csv(paths["calendar"])
    if "date" not in calendar.columns:
        raise RuntimeError("OFFICIAL_CALENDAR_DATE_MISSING")
    calendar["date"] = normalize_date(calendar["date"], "calendar.date")
    if calendar["date"].duplicated().any():
        raise RuntimeError("OFFICIAL_CALENDAR_DUPLICATE_DATE")
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)

    panel = pd.read_parquet(paths["panel"])
    required_panel = {"ticker", "date", "regular_market_value"}
    if required_panel - set(panel.columns):
        raise RuntimeError(f"SIGNAL_PANEL_COLUMNS_MISSING:{sorted(required_panel - set(panel.columns))}")
    panel["ticker"] = normalize_ticker(panel["ticker"])
    panel["date"] = normalize_date(panel["date"], "panel.date")
    if panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("SIGNAL_PANEL_DUPLICATE_IDENTITY")

    ledger = pd.read_csv(paths["continuity_ledger"], usecols=["ticker", "signal_date"])
    ledger["ticker"] = normalize_ticker(ledger["ticker"])
    ledger["signal_date"] = normalize_date(ledger["signal_date"], "continuity.signal_date")
    ca_tickers = set(ledger["ticker"].unique())
    validation_dates_sorted = sorted(set(ledger["signal_date"]))
    validation_dates = set(validation_dates_sorted)
    if len(ca_tickers) != EXPECTED_CA_TICKERS:
        raise RuntimeError(f"CA_TICKER_COUNT_CHANGED:{len(ca_tickers)}")
    if len(validation_dates_sorted) != EXPECTED_VALIDATION_DATES:
        raise RuntimeError(f"VALIDATION_DATE_COUNT_CHANGED:{len(validation_dates_sorted)}")
    if validation_dates_sorted[0] != EXPECTED_VALIDATION_START or validation_dates_sorted[-1] != EXPECTED_VALIDATION_END:
        raise RuntimeError(
            "VALIDATION_DATE_BOUNDARY_CHANGED:"
            f"{validation_dates_sorted[0].date()}:{validation_dates_sorted[-1].date()}"
        )

    primary_state = build_primary_liquid_state(panel, calendar["date"])
    primary_true = primary_state[primary_state["universe_primary_liquid"].astype(bool)]
    primary_tickers = set(primary_true["ticker"].unique())
    if len(primary_tickers) != EXPECTED_PRIMARY_TICKERS:
        raise RuntimeError(f"PRIMARY_TICKER_COUNT_CHANGED:{len(primary_tickers)}")
    if not ca_tickers.issubset(primary_tickers):
        extra = sorted(ca_tickers - primary_tickers)
        raise RuntimeError(f"CA_TICKERS_OUTSIDE_PRIMARY_740:{extra}")
    missing = primary_tickers - ca_tickers
    if len(missing) != EXPECTED_DIFF_TICKERS:
        raise RuntimeError(f"PRIMARY_MINUS_CA_COUNT_CHANGED:{len(missing)}")

    anchors = pd.read_csv(paths["anchors"])
    security_master = pd.read_csv(paths["security_master"])
    audit, master_meta = build_diff_audit(
        primary_state=primary_state,
        panel=panel,
        ca_tickers=ca_tickers,
        validation_dates=validation_dates,
        anchors=anchors,
        security_master=security_master,
        frozen_end=validation_dates_sorted[-1],
    )
    if len(audit) != EXPECTED_DIFF_TICKERS or audit["ticker"].nunique() != EXPECTED_DIFF_TICKERS:
        raise RuntimeError("AUDIT_DIFF_IDENTITY_INVALID")

    args.output_dir.mkdir(parents=True)
    full_path = args.output_dir / "v4_primary740_minus_ca610.csv"
    priority_path = args.output_dir / "v4_primary740_minus_ca610_priority.csv"
    text_path = args.output_dir / "v4_primary740_minus_ca610_tickers.txt"
    audit.to_csv(full_path, index=False, lineterminator="\n")
    priority = audit[audit["needs_manual_priority_review"].astype(bool)].copy()
    priority.to_csv(priority_path, index=False, lineterminator="\n")
    text_path.write_text("\n".join(sorted(audit["ticker"].tolist())) + "\n", encoding="utf-8")

    summary = {
        "schema_version": "v4_primary740_minus_ca610_universe_audit_v1",
        "status": "V4_PRIMARY740_MINUS_CA610_AUDIT_COMPLETE",
        "outcome_blind": True,
        "provider_calls": False,
        "model_fit": False,
        "performance_computed": False,
        "prediction_generated": False,
        "target_or_rank_materialized": False,
        "protected_forward_accessed": False,
        "primary_liquid_unique_tickers": len(primary_tickers),
        "ca_support_unique_tickers": len(ca_tickers),
        "primary_minus_ca_unique_tickers": len(audit),
        "validation_dates": len(validation_dates_sorted),
        "validation_start": validation_dates_sorted[0].date().isoformat(),
        "validation_end": validation_dates_sorted[-1].date().isoformat(),
        "potential_ca_support_data_gap_tickers": sorted(
            audit.loc[audit["ca_absence_class"].eq("POTENTIAL_CA_SUPPORT_DATA_GAP"), "ticker"].tolist()
        ),
        "priority_review_tickers": sorted(priority["ticker"].tolist()),
        "presence_class_counts": count_dict(audit["presence_class"]),
        "ca_absence_class_counts": count_dict(audit["ca_absence_class"]),
        "latest_liquidity_band_counts": count_dict(audit["latest_liquidity_band"]),
        "security_master_detection": master_meta,
        "input_hashes": hashes,
        "output_hashes": {
            "full_audit": sha256(full_path),
            "priority_audit": sha256(priority_path),
            "ticker_list": sha256(text_path),
        },
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_primary740_minus_ca610_universe_audit_manifest_v1",
        "status": summary["status"],
        "outcome_blind": True,
        "summary_sha256": sha256(summary_path),
        "output_hashes": summary["output_hashes"],
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    display_columns = [
        "ticker",
        "presence_class",
        "ca_absence_class",
        "primary_first_date",
        "primary_last_date",
        "primary_rows_validation_600",
        "primary_rows_2026",
        "panel_rows_2026",
        "latest_anchor_date",
        "latest_anchor_state",
        "security_master_delisting_date",
        "security_master_status",
        "latest_median_regular_value_60",
        "latest_liquidity_band",
        "peak_median_regular_value_60",
        "peak_liquidity_band",
        "needs_manual_priority_review",
    ]
    print(json.dumps({**summary, "manifest_sha256": sha256(manifest_path)}, indent=2, sort_keys=True))
    print("\n=== FULL_130_COMPACT_CSV ===")
    print(audit[display_columns].to_csv(index=False, lineterminator="\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
