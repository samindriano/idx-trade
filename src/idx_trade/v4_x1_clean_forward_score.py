"""Clean V4-X1 prospective score-only compatibility layer.

This module deliberately reuses the already reviewed V4-X1 prospective scorer.
It changes only lineage bindings required by the accepted clean refit:

* clean four-model manifest/fingerprint and model filenames;
* accepted clean historical feature panel;
* accepted clean security-master baseline, with only strictly post-freeze new
  listing identities admitted from the canonical runtime master;
* a new model id/generation namespace so the clean 100-session counter starts
  from zero.

No provider path, target/outcome path, feature formula, learner, score formula,
or operational anti-backfill rule is added here.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from . import v4_x1_forward_score as legacy
from .provenance import sha256_file


MODEL_ID = "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1"
GENERATION = "V4-X1-CLEAN"
EXPECTED_MODEL_MANIFEST_SHA256 = "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf"
EXPECTED_MODEL_STATUS = "V4_X1_CLEAN_PHASE_B_FINAL_REFIT_COMPLETE_INDEPENDENT_REVIEW_REQUIRED"
DEFAULT_OBSERVED_BY = "2026-08-20T12:08:44+00:00"
FREEZE_LOCAL_DATE = pd.Timestamp("2026-08-20")
PHASE_B_ACCEPTANCE_COMMIT = "ec9e8dc55ccdf458a67b63f612c8eb06660cf829"
PHASE_B_ACCEPTANCE_CHECKPOINT_BLOB = "666ca21ce26248b17328d56e0505e362b2814db5"
PROSPECTIVE_PREREGISTRATION_BLOB = "f33663bc7e4d14941a12974cc453ab90ac5b85ba"
EXPECTED_CLEAN_PANEL_SHA256 = "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e"
EXPECTED_CLEAN_SECURITY_MASTER_SHA256 = "51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e"
EXPECTED_FEATURE_BUILDER_BLOB_SHA1 = "59ad05f815870ae00480dc7945fe18371d8eff9c"
EXPECTED_PREREGISTRATION_BLOB_SHA1 = "cc1308feb51bbed16606bf7bded1ca0111644326"

MODEL_FILES = {
    "control_h5": "v4_x1_clean_control_h5_final.joblib",
    "control_h10": "v4_x1_clean_control_h10_final.joblib",
    "challenger_h5": "v4_x1_clean_challenger_h5_final.joblib",
    "challenger_h10": "v4_x1_clean_challenger_h10_final.joblib",
}
MODEL_OUTPUT_KEYS = {key: f"model_{key}" for key in MODEL_FILES}
EXPECTED_MODEL_HASHES = {
    "control_h5": "f727b10c6ea72c9ca7b447977ed4fa9cd3b5b32adb81793921c425d9085665b2",
    "control_h10": "737be8c47fe2d689dab09950a931c1339039ed8ae379b79f0bfd5a8c2e7605db",
    "challenger_h5": "d8a73d03ff72ab82826ef4e1be5e2073f6a61a5bb01b4e4268428436dc5eb082",
    "challenger_h10": "935a6f9aeaa2ca30a4016819e3848d284eb677e38153a7bd3126da0c33a9f95d",
}
FIT_LOG_FILENAME = "v4_x1_clean_final_refit_log.json"
EXPECTED_TRAINING = {
    ("CONTROL", "H5"): (239648, 978, tuple(legacy.CONTROL_FEATURES)),
    ("CONTROL", "H10"): (237976, 974, tuple(legacy.CONTROL_FEATURES)),
    ("CHALLENGER", "H5"): (239648, 978, tuple(legacy.CHALLENGER_FEATURES)),
    ("CHALLENGER", "H10"): (237976, 974, tuple(legacy.CHALLENGER_FEATURES)),
}

_LEGACY_FRESH_SESSIONS = legacy._fresh_sessions
_LEGACY_VERIFY_EXISTING_DONE = legacy._verify_existing_done
_LEGACY_SCORE_SESSION = legacy.score_v4_x1_session
_LEGACY_SECURITY_MASTER_PATH = legacy._security_master_path

_ACTIVE_CLEAN_PANEL: Path | None = None
_ACTIVE_CLEAN_SECURITY_MASTER: Path | None = None


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return payload


def _verify_exact_file(path: Path, expected: str, label: str) -> Path:
    resolved = path.expanduser().resolve()
    actual = sha256_file(resolved)
    if actual != expected:
        raise RuntimeError(f"{label}_SHA_MISMATCH:{actual}!={expected}")
    return resolved


def configure_clean_inputs(clean_panel: str | Path, clean_security_master: str | Path) -> None:
    """Bind accepted clean external inputs for one process/deployment."""

    global _ACTIVE_CLEAN_PANEL, _ACTIVE_CLEAN_SECURITY_MASTER
    _ACTIVE_CLEAN_PANEL = _verify_exact_file(
        Path(clean_panel), EXPECTED_CLEAN_PANEL_SHA256, "V4_X1_CLEAN_PANEL"
    )
    _ACTIVE_CLEAN_SECURITY_MASTER = _verify_exact_file(
        Path(clean_security_master),
        EXPECTED_CLEAN_SECURITY_MASTER_SHA256,
        "V4_X1_CLEAN_SECURITY_MASTER",
    )


def _require_clean_inputs() -> tuple[Path, Path]:
    if _ACTIVE_CLEAN_PANEL is None or _ACTIVE_CLEAN_SECURITY_MASTER is None:
        raise RuntimeError("V4_X1_CLEAN_INPUTS_NOT_CONFIGURED")
    return _ACTIVE_CLEAN_PANEL, _ACTIVE_CLEAN_SECURITY_MASTER


def _verify_model_bundle(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    manifest_path = root / "MANIFEST.json"
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != EXPECTED_MODEL_MANIFEST_SHA256:
        raise RuntimeError(
            f"V4_X1_CLEAN_MODEL_MANIFEST_SHA_MISMATCH:{manifest_sha}!={EXPECTED_MODEL_MANIFEST_SHA256}"
        )
    manifest = _read_json(manifest_path, "V4_X1_CLEAN_MODEL_MANIFEST")
    if manifest.get("status") != EXPECTED_MODEL_STATUS:
        raise RuntimeError("V4_X1_CLEAN_MODEL_STATUS_CHANGED")
    if int(manifest.get("required_fit_count", -1)) != 4:
        raise RuntimeError("V4_X1_CLEAN_MODEL_FIT_COUNT_CHANGED")
    for key in (
        "historical_prediction_generated",
        "historical_performance_computed",
        "model_scoring_performed",
        "protected_forward_accessed",
        "fresh_forward_accessed",
        "provider_calls",
        "network_calls",
        "forward_counter_mutated",
        "prospective_scoring_authorized",
        "fresh_forward_training_target_accessed",
    ):
        if manifest.get(key) is not False:
            raise RuntimeError(f"V4_X1_CLEAN_MODEL_GUARD_CHANGED:{key}")

    outputs = manifest.get("output_hashes") or {}
    model_paths: dict[str, Path] = {}
    model_hashes: dict[str, str] = {}
    for key, filename in MODEL_FILES.items():
        output_key = MODEL_OUTPUT_KEYS[key]
        declared = str(outputs.get(output_key) or "")
        expected = EXPECTED_MODEL_HASHES[key]
        if declared != expected:
            raise RuntimeError(
                f"V4_X1_CLEAN_MODEL_MANIFEST_CHILD_CHANGED:{key}:{declared}!={expected}"
            )
        path = root / filename
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(
                f"V4_X1_CLEAN_MODEL_FILE_SHA_MISMATCH:{key}:{actual}!={expected}"
            )
        model_paths[key] = path
        model_hashes[key] = actual

    fit_log_path = root / FIT_LOG_FILENAME
    declared_fit_log = str(outputs.get("fit_log") or "")
    actual_fit_log = sha256_file(fit_log_path)
    if not declared_fit_log or actual_fit_log != declared_fit_log:
        raise RuntimeError(
            f"V4_X1_CLEAN_FIT_LOG_SHA_MISMATCH:{actual_fit_log}!={declared_fit_log}"
        )
    fit_log = json.loads(fit_log_path.read_text(encoding="utf-8"))
    if not isinstance(fit_log, list) or len(fit_log) != 4:
        raise RuntimeError("V4_X1_CLEAN_FIT_LOG_STRUCTURE_CHANGED")
    seen: set[tuple[str, str]] = set()
    for row in fit_log:
        identity = (str(row.get("mode") or ""), str(row.get("head") or ""))
        if identity not in EXPECTED_TRAINING or identity in seen:
            raise RuntimeError(f"V4_X1_CLEAN_FIT_LOG_IDENTITY_CHANGED:{identity}")
        expected_rows, expected_dates, expected_features = EXPECTED_TRAINING[identity]
        if int(row.get("training_rows", -1)) != expected_rows:
            raise RuntimeError(f"V4_X1_CLEAN_FIT_LOG_ROWS_CHANGED:{identity}")
        if int(row.get("training_dates", -1)) != expected_dates:
            raise RuntimeError(f"V4_X1_CLEAN_FIT_LOG_DATES_CHANGED:{identity}")
        features = tuple(row.get("feature_columns") or ())
        if features != expected_features or int(row.get("feature_count", -1)) != len(expected_features):
            raise RuntimeError(f"V4_X1_CLEAN_FIT_LOG_FEATURES_CHANGED:{identity}")
        seen.add(identity)
    if seen != set(EXPECTED_TRAINING):
        raise RuntimeError("V4_X1_CLEAN_FIT_LOG_INCOMPLETE")

    return {
        "root": root,
        "manifest_path": manifest_path,
        "manifest_sha256": manifest_sha,
        "manifest": manifest,
        "model_paths": model_paths,
        "model_hashes": model_hashes,
        "fit_log_path": fit_log_path,
        "fit_log_sha256": actual_fit_log,
    }


def _normalize_master(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    required = {"ticker", "listed_from", "listed_to"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"{label}_MISSING_COLUMNS:{sorted(missing)}")
    out = frame.loc[:, ["ticker", "listed_from", "listed_to"]].copy()
    out["ticker"] = (
        out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    out["listed_from"] = pd.to_datetime(out["listed_from"], errors="coerce").dt.tz_localize(None).dt.normalize()
    raw_to = out["listed_to"]
    out["listed_to"] = pd.to_datetime(raw_to, errors="coerce").dt.tz_localize(None).dt.normalize()
    if out["ticker"].eq("").any() or out["ticker"].duplicated().any() or out["listed_from"].isna().any():
        raise RuntimeError(f"{label}_INVALID_IDENTITY")
    malformed_to = raw_to.notna() & raw_to.astype(str).str.strip().ne("") & out["listed_to"].isna()
    if malformed_to.any():
        raise RuntimeError(f"{label}_INVALID_LISTED_TO")
    return out.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def _merged_security_master_path(paths) -> Path:
    """Materialize baseline clean identity plus strictly post-freeze additions.

    Shared identities always come from the accepted clean baseline. Mutable
    runtime files can only contribute tickers absent from that baseline and
    whose listed_from is strictly after the model-freeze local date. This
    preserves the clean historical representation while allowing genuinely new
    future IPOs to enter the causal universe once they satisfy liquidity history.
    """

    _, baseline_path = _require_clean_inputs()
    baseline = _normalize_master(pd.read_csv(baseline_path), label="V4_X1_CLEAN_BASELINE_MASTER")
    current_path = _LEGACY_SECURITY_MASTER_PATH(paths)
    current = _normalize_master(pd.read_csv(current_path), label="V4_X1_RUNTIME_MASTER")
    baseline_tickers = set(baseline["ticker"])
    additions = current.loc[~current["ticker"].isin(baseline_tickers)].copy()
    if not additions.empty:
        invalid = additions["listed_from"].le(FREEZE_LOCAL_DATE)
        if invalid.any():
            bad = additions.loc[invalid, ["ticker", "listed_from"]].copy()
            bad["listed_from"] = bad["listed_from"].dt.strftime("%Y-%m-%d")
            raise RuntimeError(
                "V4_X1_CLEAN_RUNTIME_MASTER_PRE_FREEZE_ADDITION:" +
                json.dumps(bad.to_dict("records"), sort_keys=True)
            )
    merged = pd.concat([baseline, additions], ignore_index=True, sort=False)
    if merged["ticker"].duplicated().any():
        raise RuntimeError("V4_X1_CLEAN_MERGED_MASTER_DUPLICATE")
    merged = merged.sort_values("ticker", kind="mergesort").reset_index(drop=True)

    serial = merged.copy()
    serial["listed_from"] = serial["listed_from"].dt.strftime("%Y-%m-%d")
    serial["listed_to"] = serial["listed_to"].dt.strftime("%Y-%m-%d").fillna("")
    buffer = io.StringIO()
    serial.to_csv(buffer, index=False, lineterminator="\n")
    payload = buffer.getvalue().encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    output = (
        paths.monitor_root
        / "v4_x1_clean_inputs"
        / "security_master"
        / f"security_master_{digest}.csv"
    )
    legacy._immutable_bytes(output, payload)
    if sha256_file(output) != digest:
        raise RuntimeError("V4_X1_CLEAN_MERGED_MASTER_WRITE_SHA_MISMATCH")
    return output


def _fresh_sessions(paths, observed_by, historical_end, fingerprint):
    old_id = legacy.MODEL_ID
    try:
        legacy.MODEL_ID = MODEL_ID
        return _LEGACY_FRESH_SESSIONS(paths, observed_by, historical_end, fingerprint)
    finally:
        legacy.MODEL_ID = old_id


def _verify_existing_done(row: dict[str, Any]) -> dict[str, Any]:
    old_id = legacy.MODEL_ID
    try:
        legacy.MODEL_ID = MODEL_ID
        return _LEGACY_VERIFY_EXISTING_DONE(row)
    finally:
        legacy.MODEL_ID = old_id


@contextmanager
def _legacy_clean_context(clean_panel: Path) -> Iterator[None]:
    saved = {
        "MODEL_ID": legacy.MODEL_ID,
        "GENERATION": legacy.GENERATION,
        "EXPECTED_MODEL_MANIFEST_SHA256": legacy.EXPECTED_MODEL_MANIFEST_SHA256,
        "EXPECTED_MODEL_STATUS": legacy.EXPECTED_MODEL_STATUS,
        "DEFAULT_OBSERVED_BY": legacy.DEFAULT_OBSERVED_BY,
        "MODEL_FILES": legacy.MODEL_FILES,
        "MODEL_OUTPUT_KEYS": legacy.MODEL_OUTPUT_KEYS,
        "_verify_model_bundle": legacy._verify_model_bundle,
        "_historical_panel_path": legacy._historical_panel_path,
        "_security_master_path": legacy._security_master_path,
        "_fresh_sessions": legacy._fresh_sessions,
    }
    try:
        legacy.MODEL_ID = MODEL_ID
        legacy.GENERATION = GENERATION
        legacy.EXPECTED_MODEL_MANIFEST_SHA256 = EXPECTED_MODEL_MANIFEST_SHA256
        legacy.EXPECTED_MODEL_STATUS = EXPECTED_MODEL_STATUS
        legacy.DEFAULT_OBSERVED_BY = DEFAULT_OBSERVED_BY
        legacy.MODEL_FILES = dict(MODEL_FILES)
        legacy.MODEL_OUTPUT_KEYS = dict(MODEL_OUTPUT_KEYS)
        legacy._verify_model_bundle = _verify_model_bundle
        legacy._historical_panel_path = lambda _paths: clean_panel
        legacy._security_master_path = _merged_security_master_path
        # Read the current module attribute so the EOD pipeline can temporarily
        # wrap it with the existing same-day anti-backfill policy.
        legacy._fresh_sessions = globals()["_fresh_sessions"]
        yield
    finally:
        for key, value in saved.items():
            setattr(legacy, key, value)


def score_v4_x1_session(
    runtime_root: str | Path,
    model_root: str | Path,
    *,
    repo_root: str | Path,
    clean_panel: str | Path | None = None,
    clean_security_master: str | Path | None = None,
    session_date: str | None = None,
    observed_by: str = DEFAULT_OBSERVED_BY,
) -> dict[str, Any]:
    """Score exactly one fresh clean session using the accepted clean lineage."""

    if clean_panel is not None or clean_security_master is not None:
        if clean_panel is None or clean_security_master is None:
            raise RuntimeError("V4_X1_CLEAN_PARTIAL_INPUT_CONFIGURATION")
        configure_clean_inputs(clean_panel, clean_security_master)
    panel_path, _ = _require_clean_inputs()
    with _legacy_clean_context(panel_path):
        result = _LEGACY_SCORE_SESSION(
            runtime_root,
            model_root,
            repo_root=repo_root,
            session_date=session_date,
            observed_by=observed_by,
        )
    result = dict(result)
    result["clean_generation"] = GENERATION
    result["clean_model_id"] = MODEL_ID
    result["prospective_freeze_boundary"] = DEFAULT_OBSERVED_BY
    result["historical_clean_panel_sha256"] = EXPECTED_CLEAN_PANEL_SHA256
    result["clean_security_master_baseline_sha256"] = EXPECTED_CLEAN_SECURITY_MASTER_SHA256
    return result
