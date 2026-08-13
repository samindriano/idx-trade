from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .provenance import sha256_file
from .research_baselines import prepare_primary_model_table
from .research_features import BASELINE_FEATURE_COLUMNS, build_baseline_features
from .research_v2_features import V2_FULL_FEATURE_COLUMNS, build_v2_feature_table
from .stage5_postmortem import EXPECTED_SECURITY_MASTER_SHA256
from .stage5_ranking_holdout import (
    FROZEN_CALENDAR_SHA256,
    FROZEN_PANEL_SHA256,
    _assert_environment,
    _calendar,
    _listing_map,
    _read_table,
)
from .storage import write_parquet_atomic


REQUIRED_EQUIVALENCE_STATUS = "FULL_PANEL_LEGACY_FAST_EQUIVALENT"


def _assert_clean_output_dir(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise RuntimeError("Ranking V2 cache output directory must be new or empty")
    path.mkdir(parents=True, exist_ok=True)


def _verify_equivalence_report(
    path: Path,
    *,
    expected_h10_labels_sha256: str,
) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("status") != REQUIRED_EQUIVALENCE_STATUS:
        raise RuntimeError("fast-label equivalence report is not FULL_PANEL_LEGACY_FAST_EQUIVALENT")
    if report.get("panel_sha256") != FROZEN_PANEL_SHA256:
        raise RuntimeError("equivalence report panel hash mismatch")
    if report.get("calendar_sha256") != FROZEN_CALENDAR_SHA256:
        raise RuntimeError("equivalence report calendar hash mismatch")
    horizons = [int(value) for value in report.get("horizons", [])]
    if horizons != [5, 10, 20]:
        raise RuntimeError("equivalence report must cover exact horizons [5, 10, 20]")
    if not bool(report.get("legacy_fast_equal", False)):
        raise RuntimeError("equivalence report does not assert exact legacy/fast equality")
    if report.get("fast_h10_labels_sha256") != expected_h10_labels_sha256:
        raise RuntimeError("equivalence report H10 label hash mismatch")
    return report


def _validate_h10_labels(labels: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker",
        "signal_date",
        "signal_session_index",
        "horizon",
        "label_status",
        "binary_target",
    }
    missing = required - set(labels.columns)
    if missing:
        raise ValueError(f"Ranking V2 H10 labels missing {sorted(missing)}")
    data = labels.copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["signal_date"] = pd.to_datetime(data["signal_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if data["signal_date"].isna().any():
        raise ValueError("Ranking V2 H10 labels contain invalid signal dates")
    if data.duplicated(["ticker", "signal_date"]).any():
        raise ValueError("Ranking V2 H10 labels contain duplicate ticker/signal_date rows")
    if not pd.to_numeric(data["horizon"], errors="raise").eq(10).all():
        raise ValueError("Ranking V2 cache requires H10 labels only")
    return data.sort_values(["signal_date", "ticker"]).reset_index(drop=True)


def build_ranking_v2_cache(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    h10_labels_path: Path,
    expected_h10_labels_sha256: str,
    equivalence_report_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, object]:
    environment = _assert_environment()
    if sha256_file(panel_path) != FROZEN_PANEL_SHA256:
        raise RuntimeError("Ranking V2 frozen panel hash mismatch")
    if sha256_file(calendar_path) != FROZEN_CALENDAR_SHA256:
        raise RuntimeError("Ranking V2 frozen calendar hash mismatch")
    if sha256_file(security_master_path) != EXPECTED_SECURITY_MASTER_SHA256:
        raise RuntimeError("Ranking V2 frozen security-master hash mismatch")
    actual_h10_sha = sha256_file(h10_labels_path)
    if actual_h10_sha != expected_h10_labels_sha256:
        raise RuntimeError("Ranking V2 H10 label hash mismatch")
    equivalence = _verify_equivalence_report(
        equivalence_report_path,
        expected_h10_labels_sha256=expected_h10_labels_sha256,
    )
    _assert_clean_output_dir(output_dir)

    calendar = _calendar(calendar_path, "date")
    security_master = _read_table(security_master_path)
    listing_map = _listing_map(security_master_path, "ticker", "listed_from")
    panel = _read_table(panel_path)
    labels = _validate_h10_labels(_read_table(h10_labels_path))

    baseline_features = build_baseline_features(
        panel,
        calendar,
        listed_from=listing_map,
        security_master=security_master,
    )
    v2_features = build_v2_feature_table(baseline_features)
    model_table = prepare_primary_model_table(v2_features, labels)
    if "session_index_zero" not in model_table.columns:
        raise RuntimeError("Ranking V2 feature table lost official session index")
    model_table["signal_session_index"] = pd.to_numeric(
        model_table["session_index_zero"], errors="raise"
    ).astype(int) + 1
    model_table["binary_target"] = pd.to_numeric(model_table["binary_target"], errors="raise").astype(int)
    if model_table["signal_session_index"].min() < 1 or model_table["signal_session_index"].max() > 1250:
        raise RuntimeError("resolved H10 model rows extend outside signal sessions 1..1250")
    if not model_table["universe_primary_liquid"].astype(bool).all():
        raise RuntimeError("prepared model table contains non-primary rows")
    if not model_table["label_status"].isin(["TP_FIRST", "SL_FIRST"]).all():
        raise RuntimeError("prepared model table contains unresolved H10 rows")

    required_features = {*BASELINE_FEATURE_COLUMNS, *V2_FULL_FEATURE_COLUMNS}
    missing_features = required_features - set(model_table.columns)
    if missing_features:
        raise RuntimeError(f"prepared model table missing frozen features: {sorted(missing_features)}")

    keep = [
        "ticker",
        "date",
        "signal_session_index",
        "binary_target",
        "label_status",
        "universe_primary_liquid",
        *BASELINE_FEATURE_COLUMNS,
        *V2_FULL_FEATURE_COLUMNS,
    ]
    prepared = model_table.loc[:, keep].sort_values(
        ["signal_session_index", "ticker"], kind="mergesort"
    ).reset_index(drop=True)

    cache_path = output_dir / "ranking_v2_prepared_model_table.parquet"
    write_parquet_atomic(prepared, cache_path)
    cache_sha = sha256_file(cache_path)
    manifest = {
        "status": "RANKING_V2_PREPARED_CACHE_FROZEN",
        "code_commit": code_commit,
        "environment": environment,
        "panel_sha256": FROZEN_PANEL_SHA256,
        "calendar_sha256": FROZEN_CALENDAR_SHA256,
        "security_master_sha256": EXPECTED_SECURITY_MASTER_SHA256,
        "h10_labels_sha256": actual_h10_sha,
        "equivalence_report_path": str(equivalence_report_path),
        "equivalence_report_sha256": sha256_file(equivalence_report_path),
        "equivalence_status": equivalence.get("status"),
        "cache_path": str(cache_path),
        "cache_sha256": cache_sha,
        "rows": int(len(prepared)),
        "tickers": int(prepared["ticker"].nunique()),
        "first_signal_session_index": int(prepared["signal_session_index"].min()),
        "last_signal_session_index": int(prepared["signal_session_index"].max()),
        "positive_rate": float(prepared["binary_target"].mean()),
        "v1_feature_columns": list(BASELINE_FEATURE_COLUMNS),
        "v2_feature_columns": list(V2_FULL_FEATURE_COLUMNS),
        "historical_period_is_development_knowledge": True,
        "independent_validation_claim": False,
    }
    manifest_path = output_dir / "ranking_v2_prepared_cache_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build one immutable Ranking V2 prepared model cache")
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--h10-labels", type=Path, required=True)
    parser.add_argument("--expected-h10-labels-sha256", required=True)
    parser.add_argument("--equivalence-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = build_ranking_v2_cache(
        panel_path=args.panel,
        calendar_path=args.calendar,
        security_master_path=args.security_master,
        h10_labels_path=args.h10_labels,
        expected_h10_labels_sha256=args.expected_h10_labels_sha256,
        equivalence_report_path=args.equivalence_report,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
