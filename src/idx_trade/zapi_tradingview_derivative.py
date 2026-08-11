from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .provenance import sha256_file
from .security_master import normalise_ticker


BASE_ROOT = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v")
IMMUTABLE_PANEL_PATH = (
    BASE_ROOT
    / "research_feasibility_1260_20260809"
    / "unknown_state_diagnostic_1260_20260809"
    / "model_safe_signal_research_panel_1260.parquet"
)
YAHOO_ROOT = BASE_ROOT / "open_backfill_yahoo_census_v1_20260810"
TV_ROOT = BASE_ROOT / "open_backfill_zapi_tradingview_targeted_census_v1_20260811"
OUTPUT_ROOT = BASE_ROOT / "open_backfill_zapi_tradingview_derivative_v1_20260811"

YAHOO_PANEL_PATH = YAHOO_ROOT / "execution_open_candidate_panel.parquet"
YAHOO_PROVENANCE_PATH = YAHOO_ROOT / "execution_open_candidate_provenance.parquet"
YAHOO_MANIFEST_PATH = YAHOO_ROOT / "artifact_manifest.json"
TV_AUDIT_PATH = TV_ROOT / "tradingview_combined_row_audit.csv"
TV_ROWS_PATH = TV_ROOT / "tradingview_combined_rows_with_provenance.csv"
TV_MANIFEST_PATH = TV_ROOT / "artifact_manifest.json"

EXPECTED_IMMUTABLE_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
EXPECTED_YAHOO_PANEL_SHA256 = "d8d3463362a8c43bdb9e8d3aaba5e66ceffe86803b76979d18e3e2e71a276ea4"
EXPECTED_YAHOO_PROVENANCE_SHA256 = "1c11b832c9a8b049202547e8b76c1a4972e9177afefd9a02deb3ca49795bb17d"
EXPECTED_YAHOO_MANIFEST_SHA256 = "b6e47c98ac256cb07ac0441be41f599ba21481a5340c6b306b5f3301e207da2f"
EXPECTED_TV_AUDIT_SHA256 = "1c05a53155ed52783f112f58babc363e4ee081180542be71a9dfa1bd3ba4c5cd"
EXPECTED_TV_ROWS_SHA256 = "0453776a87995cb32a2a1da9b662bc4eb33e7318f6c53181d33a47130d2da87f"
EXPECTED_TV_MANIFEST_SHA256 = "d0f5899310f9bf37d9f2f726be440fa11a8dcbf7de6703dde068a18009290bf1"
EXPECTED_ACCEPTED_CANDIDATES = 5_675
EXPECTED_INITIAL_NULL_OPEN = 446_843
EXPECTED_YAHOO_DERIVATIVE_NULL_OPEN = 49_476


def _write_json(value: object, path: Path) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[column]):
            data[column] = data[column].dt.strftime("%Y-%m-%d")
    data.to_csv(path, index=False, lineterminator="\n")


def _normalise_keys(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    return (
        frame["ticker"].map(normalise_ticker),
        pd.to_datetime(frame["date"], errors="coerce").dt.normalize(),
    )


def _key_index(frame: pd.DataFrame) -> pd.MultiIndex:
    ticker, date = _normalise_keys(frame)
    return pd.MultiIndex.from_arrays([ticker, date], names=["ticker", "date"])


def _verify_artifact_manifest(path: Path, expected_sha256: str) -> dict[str, Any]:
    if sha256_file(path) != expected_sha256:
        raise RuntimeError(f"Artifact manifest SHA mismatch: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for name, expected in manifest.get("files", {}).items():
        artifact = path.parent / name
        if not artifact.is_file() or sha256_file(artifact) != expected:
            raise RuntimeError(f"Artifact hash mismatch in {path.name}: {name}")
    return manifest


def load_accepted_tradingview_candidates(
    *,
    audit_path: str | Path = TV_AUDIT_PATH,
    rows_path: str | Path = TV_ROWS_PATH,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    audit_file = Path(audit_path)
    rows_file = Path(rows_path)
    if sha256_file(audit_file) != EXPECTED_TV_AUDIT_SHA256:
        raise RuntimeError("TradingView audit SHA mismatch")
    if sha256_file(rows_file) != EXPECTED_TV_ROWS_SHA256:
        raise RuntimeError("TradingView combined-row SHA mismatch")
    audit = pd.read_csv(audit_file)
    accepted = audit.loc[audit["provider_class"].eq("TV_RECOVERY_CANDIDATE")].copy()
    if len(accepted) != EXPECTED_ACCEPTED_CANDIDATES:
        raise RuntimeError(f"Accepted TradingView candidate count mismatch: {len(accepted)}")
    if accepted.duplicated(["ticker", "date"]).any():
        raise RuntimeError("Accepted TradingView candidates contain duplicate ticker/date keys")
    accepted["ticker"] = accepted["ticker"].map(normalise_ticker)
    accepted["date"] = pd.to_datetime(accepted["date"], errors="coerce").dt.normalize()
    if accepted["date"].isna().any():
        raise RuntimeError("Accepted TradingView candidates contain invalid dates")
    if accepted["residual_problem_class"].str.startswith("CORPORATE_ACTION").any():
        raise RuntimeError("Corporate-action row entered the accepted TradingView derivative")

    provider = pd.read_csv(rows_file)
    provider["ticker"] = provider["ticker"].map(normalise_ticker)
    provider["date"] = pd.to_datetime(provider["date"], errors="coerce").dt.normalize()
    provider = provider.drop_duplicates(["ticker", "date"], keep="first")
    selected = accepted[
        [
            "sample_id",
            "ticker",
            "date",
            "panel_high",
            "panel_low",
            "panel_close",
            "raw_open",
            "raw_high",
            "raw_low",
            "raw_close",
            "residual_problem_class",
            "provider_class",
        ]
    ].merge(
        provider[
            [
                "ticker",
                "date",
                "source_ref",
                "provenance",
                "raw_open",
                "raw_high",
                "raw_low",
                "raw_close",
            ]
        ],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
        suffixes=("_audit", "_provider"),
    )
    if selected["raw_open_provider"].isna().any():
        raise RuntimeError("Accepted TradingView candidate lacks combined provider row")
    for field in ("raw_open", "raw_high", "raw_low", "raw_close"):
        if not selected[f"{field}_audit"].eq(selected[f"{field}_provider"]).all():
            raise RuntimeError(f"TradingView audit/provider mismatch: {field}")
    numeric_open = pd.to_numeric(selected["raw_open_provider"], errors="coerce")
    numeric_low = pd.to_numeric(selected["panel_low"], errors="coerce")
    numeric_high = pd.to_numeric(selected["panel_high"], errors="coerce")
    if not numeric_open.gt(0).all() or not numeric_open.between(numeric_low, numeric_high).all():
        raise RuntimeError("Accepted TradingView candidate failed positive/in-range Open gate")
    selected = selected.rename(
        columns={
            "raw_open_provider": "tradingview_open",
            "raw_high_provider": "tradingview_high",
            "raw_low_provider": "tradingview_low",
            "raw_close_provider": "tradingview_close",
            "source_ref": "tradingview_source_ref",
            "provenance": "tradingview_provenance",
        }
    )
    selected = selected.sort_values(["ticker", "date", "sample_id"], kind="mergesort").reset_index(drop=True)
    return selected, {
        "audit_path": str(audit_file),
        "audit_sha256": sha256_file(audit_file),
        "rows_path": str(rows_file),
        "rows_sha256": sha256_file(rows_file),
        "accepted_candidates": int(len(selected)),
        "accepted_tickers": int(selected["ticker"].nunique()),
        "provenance_counts": {str(k): int(v) for k, v in selected["tradingview_provenance"].value_counts().items()},
        "residual_class_counts": {
            str(k): int(v) for k, v in selected["residual_problem_class"].value_counts().items()
        },
    }


def apply_tradingview_candidates(
    yahoo_panel: pd.DataFrame,
    yahoo_provenance: pd.DataFrame,
    candidates: pd.DataFrame,
    *,
    tv_artifact_sha256: str = EXPECTED_TV_MANIFEST_SHA256,
    expected_candidate_count: int = EXPECTED_ACCEPTED_CANDIDATES,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    panel = yahoo_panel.copy()
    provenance = yahoo_provenance.copy()
    if list(panel.columns) != list(yahoo_panel.columns):
        raise RuntimeError("Unexpected Yahoo derivative column mutation")
    required_panel = {"ticker", "date", "open", "high", "low", "close"}
    required_provenance = {"ticker", "date", "open_source", "open_evidence_class", "validation_status"}
    if not required_panel.issubset(panel.columns) or not required_provenance.issubset(provenance.columns):
        raise ValueError("Yahoo derivative inputs are missing required columns")
    if len(panel) != len(provenance) or _key_index(panel).duplicated().any() or _key_index(provenance).duplicated().any():
        raise ValueError("Yahoo derivative panel/provenance keys are not unique and aligned")
    if not _key_index(panel).equals(_key_index(provenance)):
        raise ValueError("Yahoo derivative panel and provenance key order differ")

    candidate_keys = _key_index(candidates)
    panel_keys = _key_index(panel)
    if candidate_keys.duplicated().any() or not candidate_keys.isin(panel_keys).all():
        raise RuntimeError("TradingView candidates do not map one-to-one into Yahoo derivative")
    positions = panel_keys.get_indexer(candidate_keys)
    if (positions < 0).any():
        raise RuntimeError("TradingView candidate key missing from Yahoo derivative")
    original_open = panel["open"].copy()
    existing_at_candidate = original_open.iloc[positions].notna()
    if existing_at_candidate.any():
        raise RuntimeError("Attempted to overwrite an existing non-null Open")

    updated_open = panel["open"].to_numpy(copy=True)
    updated_open[positions] = pd.to_numeric(candidates["tradingview_open"], errors="raise").to_numpy()
    panel["open"] = updated_open
    if not original_open[original_open.notna()].equals(panel.loc[original_open.notna(), "open"]):
        raise RuntimeError("Existing non-null Open changed during TradingView application")

    tv_columns = {
        "tradingview_census_id": candidates["sample_id"].to_numpy(),
        "tradingview_provider_class": candidates["provider_class"].to_numpy(),
        "tradingview_residual_problem_class": candidates["residual_problem_class"].to_numpy(),
        "tradingview_provenance": candidates["tradingview_provenance"].to_numpy(),
        "tradingview_source_ref": candidates["tradingview_source_ref"].to_numpy(),
        "tradingview_open": candidates["tradingview_open"].to_numpy(),
        "tradingview_high": candidates["tradingview_high"].to_numpy(),
        "tradingview_low": candidates["tradingview_low"].to_numpy(),
        "tradingview_close": candidates["tradingview_close"].to_numpy(),
        "tradingview_validation_status": np.array(["ACCEPTED"] * len(candidates), dtype=object),
        "tradingview_artifact_manifest_sha256": np.array([tv_artifact_sha256] * len(candidates), dtype=object),
    }
    for column in tv_columns:
        provenance[column] = pd.NA
    for column, values in tv_columns.items():
        target = provenance[column].to_numpy(dtype=object, copy=True)
        target[positions] = values
        provenance[column] = target

    canonical_updates = {
        "open_source": "ZAPI_TRADINGVIEW",
        "open_evidence_class": "TV_RECOVERY_CANDIDATE",
        "validation_status": "ACCEPTED",
    }
    for column, value in canonical_updates.items():
        target = provenance[column].to_numpy(dtype=object, copy=True)
        target[positions] = value
        provenance[column] = target
    source_refs = provenance["source_cache_ref"].to_numpy(dtype=object, copy=True)
    source_refs[positions] = candidates["tradingview_source_ref"].to_numpy()
    provenance["source_cache_ref"] = source_refs

    summary = {
        "candidate_rows_requested": int(len(candidates)),
        "additional_null_open_values_filled": int(len(positions)),
        "existing_non_null_open_overwrites": 0,
        "yahoo_derivative_null_open_before": int(original_open.isna().sum()),
        "derivative_null_open_after": int(panel["open"].isna().sum()),
        "all_original_panel_columns_preserved": list(panel.columns) == list(yahoo_panel.columns),
        "all_yahoo_provenance_rows_preserved": len(provenance) == len(yahoo_provenance),
    }
    if summary["additional_null_open_values_filled"] != expected_candidate_count:
        raise RuntimeError(
            f"TradingView application filled {summary['additional_null_open_values_filled']} rows; "
            f"expected {expected_candidate_count}"
        )
    return panel, provenance, summary


def _execution_grade_diagnostics(
    *,
    immutable_panel: pd.DataFrame,
    yahoo_panel: pd.DataFrame,
    derivative: pd.DataFrame,
    application: dict[str, Any],
) -> dict[str, Any]:
    immutable_null = int(immutable_panel["open"].isna().sum())
    yahoo_null = int(yahoo_panel["open"].isna().sum())
    derivative_null = int(derivative["open"].isna().sum())
    original_nonnull = yahoo_panel["open"].notna()
    if not yahoo_panel.loc[original_nonnull, "open"].equals(derivative.loc[original_nonnull, "open"]):
        raise RuntimeError("Yahoo derivative non-null Open values changed")
    return {
        "execution_grade_promoted": False,
        "execution_grade_status": "NOT_PROMOTED_REMAINS_UNRESOLVED",
        "immutable_panel_rows": int(len(immutable_panel)),
        "immutable_panel_null_open": immutable_null,
        "yahoo_derivative_null_open_before_tradingview": yahoo_null,
        "derivative_null_open_after_tradingview": derivative_null,
        "yahoo_open_fills_retained": int(immutable_null - yahoo_null),
        "accepted_tradingview_open_fills": int(yahoo_null - derivative_null),
        "cumulative_open_gap_closure": int(immutable_null - derivative_null),
        "cumulative_open_gap_closure_rate": float((immutable_null - derivative_null) / immutable_null),
        "remaining_non_ca_residual": 33_144,
        "remaining_corporate_action_residual": 10_657,
        "remaining_total_null_open": derivative_null,
        "open_coverage_before_tradingview": float(yahoo_panel["open"].notna().mean()),
        "open_coverage_after_tradingview": float(derivative["open"].notna().mean()),
        "existing_non_null_open_overwrites": application["existing_non_null_open_overwrites"],
        "all_original_panel_columns_preserved": application["all_original_panel_columns_preserved"],
        "provenance_rows": int(application["candidate_rows_requested"]),
    }


def run_derivative_application(
    *,
    immutable_panel_path: str | Path = IMMUTABLE_PANEL_PATH,
    yahoo_panel_path: str | Path = YAHOO_PANEL_PATH,
    yahoo_provenance_path: str | Path = YAHOO_PROVENANCE_PATH,
    output_dir: str | Path = OUTPUT_ROOT,
) -> dict[str, Any]:
    immutable_file = Path(immutable_panel_path)
    yahoo_file = Path(yahoo_panel_path)
    yahoo_prov_file = Path(yahoo_provenance_path)
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output}")
    for file in (immutable_file, yahoo_file, yahoo_prov_file, YAHOO_MANIFEST_PATH, TV_AUDIT_PATH, TV_ROWS_PATH, TV_MANIFEST_PATH):
        if not file.is_file():
            raise FileNotFoundError(file)
    if sha256_file(immutable_file) != EXPECTED_IMMUTABLE_PANEL_SHA256:
        raise RuntimeError("Immutable panel SHA mismatch before derivative application")
    if sha256_file(yahoo_file) != EXPECTED_YAHOO_PANEL_SHA256 or sha256_file(yahoo_prov_file) != EXPECTED_YAHOO_PROVENANCE_SHA256:
        raise RuntimeError("Accepted Yahoo derivative SHA mismatch")
    yahoo_manifest = _verify_artifact_manifest(YAHOO_MANIFEST_PATH, EXPECTED_YAHOO_MANIFEST_SHA256)
    tv_manifest = _verify_artifact_manifest(TV_MANIFEST_PATH, EXPECTED_TV_MANIFEST_SHA256)
    candidates, candidate_input = load_accepted_tradingview_candidates()
    immutable_panel = pd.read_parquet(immutable_file)
    yahoo_panel = pd.read_parquet(yahoo_file)
    yahoo_provenance = pd.read_parquet(yahoo_prov_file)
    if int(immutable_panel["open"].isna().sum()) != EXPECTED_INITIAL_NULL_OPEN:
        raise RuntimeError("Immutable panel null Open baseline mismatch")
    if int(yahoo_panel["open"].isna().sum()) != EXPECTED_YAHOO_DERIVATIVE_NULL_OPEN:
        raise RuntimeError("Accepted Yahoo derivative null Open baseline mismatch")
    derivative, provenance, application = apply_tradingview_candidates(yahoo_panel, yahoo_provenance, candidates)
    diagnostics = _execution_grade_diagnostics(
        immutable_panel=immutable_panel,
        yahoo_panel=yahoo_panel,
        derivative=derivative,
        application=application,
    )
    panel_after = sha256_file(immutable_file)
    if panel_after != EXPECTED_IMMUTABLE_PANEL_SHA256:
        raise RuntimeError("Immutable panel changed during derivative application")
    output.mkdir(parents=True, exist_ok=True)
    derivative_path = output / "execution_open_candidate_panel_yahoo_tradingview.parquet"
    provenance_path = output / "execution_open_candidate_provenance_yahoo_tradingview.parquet"
    candidates_path = output / "accepted_tradingview_open_candidates.csv"
    source_manifest = {
        "immutable_panel": {"path": str(immutable_file), "sha256": sha256_file(immutable_file)},
        "yahoo_derivative_panel": {"path": str(yahoo_file), "sha256": sha256_file(yahoo_file)},
        "yahoo_derivative_provenance": {"path": str(yahoo_prov_file), "sha256": sha256_file(yahoo_prov_file)},
        "yahoo_artifact_manifest": {"path": str(YAHOO_MANIFEST_PATH), "sha256": sha256_file(YAHOO_MANIFEST_PATH)},
        "tradingview_audit": {"path": str(TV_AUDIT_PATH), "sha256": sha256_file(TV_AUDIT_PATH)},
        "tradingview_combined_rows": {"path": str(TV_ROWS_PATH), "sha256": sha256_file(TV_ROWS_PATH)},
        "tradingview_artifact_manifest": {"path": str(TV_MANIFEST_PATH), "sha256": sha256_file(TV_MANIFEST_PATH)},
        "accepted_candidate_input": candidate_input,
        "execution_grade_promoted": False,
    }
    derivative.to_parquet(derivative_path, index=False)
    provenance.to_parquet(provenance_path, index=False)
    _write_csv(candidates, candidates_path)
    _write_json(source_manifest, output / "source_input_manifest.json")
    _write_json(diagnostics, output / "execution_grade_diagnostics.json")
    summary: dict[str, Any] = {
        "status": "ZAPI_TRADINGVIEW_DERIVATIVE_APPLICATION_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "derivative_application": application,
        "execution_grade_diagnostics": diagnostics,
        "candidate_input": candidate_input,
        "source_input_manifest": source_manifest,
        "yahoo_artifact_manifest_sha256": sha256_file(YAHOO_MANIFEST_PATH),
        "tradingview_artifact_manifest_sha256": sha256_file(TV_MANIFEST_PATH),
        "immutable_panel_sha256_before": EXPECTED_IMMUTABLE_PANEL_SHA256,
        "immutable_panel_sha256_after": panel_after,
        "immutable_panel_unchanged": panel_after == EXPECTED_IMMUTABLE_PANEL_SHA256,
        "derivative_panel_rows": int(len(derivative)),
        "derivative_panel_tickers": int(derivative["ticker"].nunique()),
        "execution_grade_promoted": False,
        "corporate_action_repair_performed": False,
        "modeling_performed": False,
        "ranking_work_performed": False,
        "execution_pnl_performed": False,
    }
    _write_json(summary, output / "derivative_application_summary.json")
    artifact_files = sorted(
        path
        for path in output.iterdir()
        if path.is_file() and path.name not in {"artifact_manifest.json", "derivative_application_summary.json"}
    )
    artifact_manifest = {
        "runtime": "open_backfill_zapi_tradingview_derivative_v1_20260811",
        "files": {path.name: sha256_file(path) for path in artifact_files},
        "execution_grade_promoted": False,
    }
    _write_json(artifact_manifest, output / "artifact_manifest.json")
    summary["artifact_manifest_sha256"] = sha256_file(output / "artifact_manifest.json")
    summary["derivative_panel_sha256"] = sha256_file(derivative_path)
    summary["provenance_sha256"] = sha256_file(provenance_path)
    _write_json(summary, output / "derivative_application_summary.json")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply accepted TradingView Open candidates to the accepted Yahoo derivative")
    parser.add_argument("--output-dir", default=str(OUTPUT_ROOT))
    args = parser.parse_args()
    print(json.dumps(run_derivative_application(output_dir=args.output_dir), ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
