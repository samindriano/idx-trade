"""Read-only adjudication of residual Open price-basis forensic exceptions.

No Open repair, panel mutation, model fit/scoring/tuning, target access,
protected-forward access, or provider calls occur here.
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

from idx_trade.price_basis_open_residual_adjudication import (  # noqa: E402
    classify_residuals,
    summarize,
    ticker_mechanism_summary,
)

PROJECT = Path(r"D:\Documents\Project")
DEFAULT_FORENSIC_ROOT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_open_forensic_v1_20260820"
DEFAULT_OUTPUT = PROJECT / "idx-trade-data-gate-20260808v" / "price_basis_open_residual_adjudication_v1_20260820"
FORENSIC_MANIFEST_SHA256 = "4538f4d35d042e7e3257b746a56065702463cf8393b1ae922db473a8b355724e"
EXPECTED_ROWS = 1657
EXPECTED_TICKERS = 12
EXPECTED_FORENSIC_STATUS = "OPEN_BASIS_FORENSIC_UNRESOLVED_REFIT_BLOCKED"
EXPECTED_OFFICIAL_POSITIVE = 1216
EXPECTED_FACTOR_WITHIN = 1654
EXPECTED_FACTOR_EQUALS_OFFICIAL = 1214


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_EXPECTED:{path}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forensic-root", type=Path, default=DEFAULT_FORENSIC_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.forensic_root.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"REFUSE_OVERWRITE_NONEMPTY_OUTPUT:{output}")

    manifest_path = root / "MANIFEST.json"
    if sha256_file(manifest_path) != FORENSIC_MANIFEST_SHA256:
        raise RuntimeError("OPEN_FORENSIC_MANIFEST_SHA_MISMATCH")
    manifest = read_json(manifest_path)
    summary = read_json(root / "summary.json")
    if manifest.get("status") != EXPECTED_FORENSIC_STATUS or summary.get("status") != EXPECTED_FORENSIC_STATUS:
        raise RuntimeError("OPEN_FORENSIC_STATUS_CHANGED")
    totals = summary.get("totals") or {}
    expected_totals = {
        "rows": EXPECTED_ROWS,
        "official_open_positive": EXPECTED_OFFICIAL_POSITIVE,
        "factor_up_within_corrected_hlc": EXPECTED_FACTOR_WITHIN,
        "factor_up_equals_official": EXPECTED_FACTOR_EQUALS_OFFICIAL,
    }
    for key, expected in expected_totals.items():
        if int(totals.get(key, -1)) != expected:
            raise RuntimeError(f"OPEN_FORENSIC_TOTAL_CHANGED:{key}:{totals.get(key)}!={expected}")

    hashes = manifest.get("output_hashes") or {}
    rows_path = root / "open_basis_forensic_rows.csv"
    expected_rows_sha = str(hashes.get("rows") or "")
    if not expected_rows_sha or sha256_file(rows_path) != expected_rows_sha:
        raise RuntimeError("OPEN_FORENSIC_ROWS_SHA_MISMATCH")
    rows = pd.read_csv(rows_path, low_memory=False)
    if len(rows) != EXPECTED_ROWS or rows["ticker"].astype(str).nunique() != EXPECTED_TICKERS:
        raise RuntimeError("OPEN_FORENSIC_POPULATION_CHANGED")

    classified = classify_residuals(rows)
    result_summary = summarize(classified)
    ticker_summary = ticker_mechanism_summary(classified)

    # These are evidence classes only, not repair authorization.
    # A later preregistered remediation may use official OpenPrice as primary,
    # CA-factor reconstruction only when official OpenPrice is unavailable,
    # and must leave unsupported rows fail-closed.
    covered_candidate_rows = int(
        classified["official_primary_candidate"].astype(bool).sum()
        + classified["factor_fallback_candidate"].astype(bool).sum()
    )
    unresolved = int(classified["unresolved_no_official_no_factor"].astype(bool).sum())
    if covered_candidate_rows + unresolved != EXPECTED_ROWS:
        verdict = "OPEN_BASIS_RESIDUAL_ADJUDICATION_IDENTITY_UNRESOLVED"
    else:
        verdict = "OPEN_BASIS_RESIDUALS_CLASSIFIED_SEPARATE_REMEDIATION_PREREG_READY"

    exception_mask = (
        classified["official_factor_disagreement"].astype(bool)
        | classified["factor_range_failure"].astype(bool)
        | classified["unresolved_no_official_no_factor"].astype(bool)
    )
    exceptions = classified.loc[exception_mask].copy()

    output.mkdir(parents=True, exist_ok=True)
    rows_out = output / "open_basis_residual_adjudication_rows.csv"
    exception_out = output / "open_basis_residual_exceptions.csv"
    ticker_out = output / "open_basis_residual_by_ticker.csv"
    classified.to_csv(rows_out, index=False, lineterminator="\n")
    exceptions.to_csv(exception_out, index=False, lineterminator="\n")
    ticker_summary.to_csv(ticker_out, index=False, lineterminator="\n")

    result = {
        "schema_version": "price_basis_open_residual_adjudication_v1",
        "status": verdict,
        "parent_forensic_manifest_sha256": FORENSIC_MANIFEST_SHA256,
        "population": {"rows": EXPECTED_ROWS, "tickers": EXPECTED_TICKERS},
        "adjudication": result_summary,
        "candidate_coverage": {
            "official_primary_rows": int(classified["official_primary_candidate"].astype(bool).sum()),
            "factor_fallback_rows": int(classified["factor_fallback_candidate"].astype(bool).sum()),
            "candidate_rows_total": covered_candidate_rows,
            "unresolved_rows": unresolved,
        },
        "exception_rows": int(len(exceptions)),
        "repair_authorized": False,
        "clean_refit_authorized": False,
        "guardrails": {
            "repair_performed": False,
            "panel_mutated": False,
            "model_fit": False,
            "model_scoring": False,
            "model_tuning": False,
            "target_values_accessed": False,
            "protected_forward_accessed": False,
            "provider_calls": False,
        },
        "next": "FREEZE_SEPARATE_OPEN_REMEDIATION_CONTRACT; KEEP_MODEL_REFIT_WAITING_FOR_CROSS_LANE_DATA_CONSOLIDATION",
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs = {"rows": rows_out, "exceptions": exception_out, "by_ticker": ticker_out, "summary": summary_path}
    out_manifest = {
        "schema_version": "price_basis_open_residual_adjudication_manifest_v1",
        "status": verdict,
        "parent_forensic_manifest_sha256": FORENSIC_MANIFEST_SHA256,
        "guardrails": result["guardrails"],
        "output_hashes": {name: sha256_file(path) for name, path in outputs.items()},
    }
    out_manifest_path = output / "MANIFEST.json"
    out_manifest_path.write_text(json.dumps(out_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**result, "manifest": str(out_manifest_path), "manifest_sha256": sha256_file(out_manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
