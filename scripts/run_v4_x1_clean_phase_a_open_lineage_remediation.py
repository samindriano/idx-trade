"""Outcome-blind remediation wrapper for V4-X1 clean Phase-A Open lineage.

The first Phase-A replay incorrectly treated the Stage-A panel ``open`` column
as a complete executable-Open evidence layer.  This wrapper keeps the original
Phase-A runner immutable, replaces only its clean Open-evidence constructor,
and preserves the parent executable-Open evidence exactly outside the accepted
Stage-A Open-remediation population.

No numeric targets, returns/ranks, model fit/scoring, historical performance,
protected/fresh-forward outcomes, provider calls, or Phase-B work are allowed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_RUNNER_PATH = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_a_structural_replay.py"
EXPECTED_PARENT_RUNNER_BLOB = "352e331439dd89c8d66d6b36f98997d3b667e2c0"
EXPECTED_FIRST_FAILED_MANIFEST_SHA256 = "1dedb76db7c1fc620e4feb286e409d0266bf367581cbf7dab28bc862f298787c"
EXPECTED_FIELD_PROVENANCE_SHA256 = "cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28"
EXPECTED_CANDIDATE_ROWS = 1657
EXPECTED_ADMITTED_ROWS = 1655
EXPECTED_FAIL_CLOSED_ROWS = 2
POLICY_ID = "PRESERVE_PARENT_EXECUTABLE_OPEN_EXCEPT_ACCEPTED_STAGE_A_CANDIDATES_V1"


_PARENT_OLD_PRICE: pd.DataFrame | None = None
_PARENT_OLD_PRICE_STATS: dict[str, Any] | None = None
_FIELD_PROVENANCE_PATH: Path | None = None


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"V4_X1_CLEAN_OPEN_REMEDIATION_INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob(path: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", f"HEAD:{path}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _load_parent_runner():
    spec = importlib.util.spec_from_file_location(
        "v4_x1_clean_phase_a_parent_frozen", PARENT_RUNNER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_PARENT_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _normalize_identity(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    required = {"ticker", "date"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"{label}_MISSING_IDENTITY_COLUMNS:{sorted(missing)}")
    out = frame.copy()
    out["ticker"] = (
        out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if out["ticker"].eq("").any() or out["date"].isna().any():
        raise RuntimeError(f"{label}_INVALID_IDENTITY")
    if out.duplicated(["ticker", "date"]).any():
        raise RuntimeError(f"{label}_DUPLICATE_IDENTITY")
    return out


def _strict_bool(series: pd.Series, *, label: str) -> pd.Series:
    if series.isna().any():
        raise RuntimeError(f"{label}_NULL_BOOLEAN")
    values = set(series.tolist())
    if not values.issubset({True, False, np.bool_(True), np.bool_(False)}):
        raise RuntimeError(f"{label}_NOT_BOOLEAN")
    return series.astype(bool)


def apply_clean_open_lineage(
    parent_price_evidence: pd.DataFrame,
    clean_panel: pd.DataFrame,
    field_provenance: pd.DataFrame,
    *,
    expected_candidate_rows: int = EXPECTED_CANDIDATE_ROWS,
    expected_admitted_rows: int = EXPECTED_ADMITTED_ROWS,
    expected_fail_closed_rows: int = EXPECTED_FAIL_CLOSED_ROWS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Preserve parent executable Open outside exact Stage-A candidates."""

    parent = _normalize_identity(parent_price_evidence, label="PARENT_EXECUTABLE_OPEN")
    clean = _normalize_identity(clean_panel, label="CLEAN_PANEL")
    provenance = _normalize_identity(field_provenance, label="FIELD_PROVENANCE")

    parent_required = {
        "ticker", "date", "session_index", "market_state",
        "accepted_open", "open_admitted", "close", "close_admitted",
    }
    clean_required = {"ticker", "date", "open", "close"}
    provenance_required = {
        "ticker", "date", "open_repaired", "open_fail_closed_candidate",
    }
    for label, frame, required in (
        ("PARENT_EXECUTABLE_OPEN", parent, parent_required),
        ("CLEAN_PANEL", clean, clean_required),
        ("FIELD_PROVENANCE", provenance, provenance_required),
    ):
        missing = required - set(frame.columns)
        if missing:
            raise RuntimeError(f"{label}_MISSING_COLUMNS:{sorted(missing)}")

    parent_index = pd.MultiIndex.from_frame(parent[["ticker", "date"]])
    clean_index = pd.MultiIndex.from_frame(clean[["ticker", "date"]])
    provenance_index = pd.MultiIndex.from_frame(provenance[["ticker", "date"]])
    if not parent_index.equals(clean_index):
        if set(parent_index.tolist()) != set(clean_index.tolist()):
            raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_CLEAN_PANEL_IDENTITY_SET_CHANGED")
        clean = clean.set_index(["ticker", "date"]).loc[parent_index].reset_index()
        clean_index = pd.MultiIndex.from_frame(clean[["ticker", "date"]])
    if not parent_index.equals(provenance_index):
        if set(parent_index.tolist()) != set(provenance_index.tolist()):
            raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_PROVENANCE_IDENTITY_SET_CHANGED")
        provenance = provenance.set_index(["ticker", "date"]).loc[parent_index].reset_index()
        provenance_index = pd.MultiIndex.from_frame(provenance[["ticker", "date"]])
    if not parent_index.equals(clean_index) or not parent_index.equals(provenance_index):
        raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_IDENTITY_ALIGNMENT_FAILED")

    open_repaired = _strict_bool(provenance["open_repaired"], label="OPEN_REPAIRED")
    fail_closed = _strict_bool(
        provenance["open_fail_closed_candidate"], label="OPEN_FAIL_CLOSED_CANDIDATE"
    )
    if bool((open_repaired & fail_closed).any()):
        raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_ADMITTED_FAIL_OVERLAP")
    candidate = open_repaired | fail_closed

    if "hlc_repaired" in provenance.columns:
        hlc_repaired = _strict_bool(provenance["hlc_repaired"], label="HLC_REPAIRED")
        if not bool(candidate.equals(hlc_repaired)):
            raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_CANDIDATE_HLC_IDENTITY_DRIFT")

    counts = {
        "candidate_rows": int(candidate.sum()),
        "admitted_rows": int(open_repaired.sum()),
        "fail_closed_rows": int(fail_closed.sum()),
    }
    expected_counts = {
        "candidate_rows": int(expected_candidate_rows),
        "admitted_rows": int(expected_admitted_rows),
        "fail_closed_rows": int(expected_fail_closed_rows),
    }
    if counts != expected_counts:
        raise RuntimeError(
            f"V4_X1_CLEAN_OPEN_REMEDIATION_POPULATION_CHANGED:{counts}!={expected_counts}"
        )

    if "open_source" in provenance.columns:
        source = provenance["open_source"].astype(str)
        admitted_sources = set(source.loc[open_repaired].unique())
        allowed_admitted = {"IDX_OFFICIAL_OPENPRICE", "CA_FACTOR_RECONSTRUCTION"}
        if not admitted_sources.issubset(allowed_admitted):
            raise RuntimeError(
                f"V4_X1_CLEAN_OPEN_REMEDIATION_ADMITTED_SOURCE_CHANGED:{sorted(admitted_sources)}"
            )
        if not source.loc[fail_closed].eq("FAIL_CLOSED_UNAVAILABLE").all():
            raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_FAIL_CLOSED_SOURCE_CHANGED")

    parent_open = pd.to_numeric(parent["accepted_open"], errors="coerce").astype(float)
    parent_admitted = _strict_bool(parent["open_admitted"], label="PARENT_OPEN_ADMITTED")
    clean_panel_open = pd.to_numeric(clean["open"], errors="coerce").astype(float)
    clean_close = pd.to_numeric(clean["close"], errors="coerce").astype(float)

    admitted_values = clean_panel_open.loc[open_repaired]
    if not bool((np.isfinite(admitted_values) & admitted_values.gt(0.0)).all()):
        raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_ADMITTED_OPEN_INVALID")
    if clean_panel_open.loc[fail_closed].notna().any():
        raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_FAIL_CLOSED_PANEL_OPEN_FINITE")

    accepted_open = parent_open.copy()
    open_admitted = parent_admitted.copy()
    accepted_open.loc[open_repaired] = admitted_values
    open_admitted.loc[open_repaired] = True
    accepted_open.loc[fail_closed] = np.nan
    open_admitted.loc[fail_closed] = False

    non_candidate = ~candidate
    if not np.array_equal(
        accepted_open.loc[non_candidate].to_numpy(dtype=float),
        parent_open.loc[non_candidate].to_numpy(dtype=float),
        equal_nan=True,
    ):
        raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_NONCANDIDATE_VALUE_DRIFT")
    if not bool(open_admitted.loc[non_candidate].equals(parent_admitted.loc[non_candidate])):
        raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_NONCANDIDATE_ADMISSION_DRIFT")

    result = pd.DataFrame(
        {
            "ticker": parent["ticker"],
            "date": parent["date"],
            "session_index": parent["session_index"].astype(int),
            "market_state": parent["market_state"].astype(str),
            "accepted_open": accepted_open,
            "open_admitted": open_admitted,
            "close": clean_close,
            "close_admitted": np.isfinite(clean_close) & clean_close.gt(0.0),
        }
    )

    stats: dict[str, Any] = {
        "policy_id": POLICY_ID,
        **counts,
        "non_candidate_rows": int(non_candidate.sum()),
        "parent_non_candidate_open_admitted": int(parent_admitted.loc[non_candidate].sum()),
        "clean_non_candidate_open_admitted": int(open_admitted.loc[non_candidate].sum()),
        "parent_candidate_open_admitted": int(parent_admitted.loc[candidate].sum()),
        "clean_candidate_open_admitted": int(open_admitted.loc[candidate].sum()),
        "final_open_admitted": int(open_admitted.sum()),
        "close_admitted": int(result["close_admitted"].sum()),
        "non_candidate_open_value_exact_parity": True,
        "non_candidate_open_admission_exact_parity": True,
        "market_state_reused_exactly_from_parent_executable_evidence": True,
    }
    return result, stats


def _arg_value(argv: list[str], flag: str) -> str:
    try:
        index = argv.index(flag)
    except ValueError as exc:
        raise RuntimeError(f"V4_X1_CLEAN_OPEN_REMEDIATION_REQUIRED_ARG_MISSING:{flag}") from exc
    if index + 1 >= len(argv):
        raise RuntimeError(f"V4_X1_CLEAN_OPEN_REMEDIATION_REQUIRED_ARG_VALUE_MISSING:{flag}")
    return argv[index + 1]


def _postprocess_output(output_dir: Path, wrapper_blob: str, failed_manifest_sha: str) -> str:
    summary_path = output_dir / "summary.json"
    manifest_path = output_dir / "MANIFEST.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    remediation = {
        "policy_id": POLICY_ID,
        "first_failed_replay_manifest_sha256": failed_manifest_sha,
        "wrapper_git_blob": wrapper_blob,
        "parent_runner_git_blob": EXPECTED_PARENT_RUNNER_BLOB,
        "reason": "FIRST_PHASE_A_RUN_MIXED_PARENT_EXECUTABLE_OPEN_WITH_INCOMPLETE_STAGE_A_PANEL_OPEN",
    }
    summary["schema_version"] = "v4_x1_clean_phase_a_structural_replay_open_lineage_remediated_v1"
    summary["open_lineage_remediation"] = remediation
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest["schema_version"] = "v4_x1_clean_phase_a_structural_replay_open_lineage_remediated_manifest_v1"
    manifest["open_lineage_remediation"] = remediation
    manifest.setdefault("output_hashes", {})["summary"] = sha256_file(summary_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return sha256_file(manifest_path)


def main() -> int:
    if git_blob("scripts/run_v4_x1_clean_phase_a_structural_replay.py") != EXPECTED_PARENT_RUNNER_BLOB:
        raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_PARENT_RUNNER_CHANGED")

    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--failed-replay-manifest", type=Path, required=True)
    known, remaining = pre.parse_known_args()
    failed_manifest = known.failed_replay_manifest.resolve()
    failed_sha = sha256_file(failed_manifest)
    if failed_sha != EXPECTED_FIRST_FAILED_MANIFEST_SHA256:
        raise RuntimeError(
            f"V4_X1_CLEAN_OPEN_REMEDIATION_FIRST_FAIL_SHA_MISMATCH:{failed_sha}!={EXPECTED_FIRST_FAILED_MANIFEST_SHA256}"
        )

    field_provenance_path = Path(_arg_value(remaining, "--field-provenance")).resolve()
    if sha256_file(field_provenance_path) != EXPECTED_FIELD_PROVENANCE_SHA256:
        raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_FIELD_PROVENANCE_SHA_MISMATCH")
    output_dir = Path(_arg_value(remaining, "--output-dir")).resolve()

    parent_runner = _load_parent_runner()
    original_old_builder = parent_runner.build_old_price_evidence

    def capture_old_builder(*args, **kwargs):
        global _PARENT_OLD_PRICE, _PARENT_OLD_PRICE_STATS
        frame, stats = original_old_builder(*args, **kwargs)
        _PARENT_OLD_PRICE = frame.copy(deep=True)
        _PARENT_OLD_PRICE_STATS = dict(stats)
        return frame, stats

    def remediated_clean_builder(panel, calendar, anchors, intervals):
        del calendar, anchors, intervals
        if _PARENT_OLD_PRICE is None:
            raise RuntimeError("V4_X1_CLEAN_OPEN_REMEDIATION_PARENT_EVIDENCE_NOT_CAPTURED")
        provenance = pd.read_parquet(field_provenance_path)
        frame, stats = apply_clean_open_lineage(
            _PARENT_OLD_PRICE,
            panel,
            provenance,
        )
        if _PARENT_OLD_PRICE_STATS is not None:
            stats["parent_state_conflicts"] = int(_PARENT_OLD_PRICE_STATS.get("state_conflicts", 0))
        return frame, stats

    parent_runner.build_old_price_evidence = capture_old_builder
    parent_runner.build_clean_price_evidence = remediated_clean_builder

    wrapper_blob = git_blob("scripts/run_v4_x1_clean_phase_a_open_lineage_remediation.py")
    sys.argv = [sys.argv[0], *remaining]
    result = int(parent_runner.main())
    if result != 0:
        return result

    final_manifest_sha = _postprocess_output(output_dir, wrapper_blob, failed_sha)
    final_manifest = json.loads((output_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "status": final_manifest.get("status"),
                "manifest": str(output_dir / "MANIFEST.json"),
                "manifest_sha256": final_manifest_sha,
                "open_lineage_remediation_policy": POLICY_ID,
                "first_failed_replay_manifest_sha256": failed_sha,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
