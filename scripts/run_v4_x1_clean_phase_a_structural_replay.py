"""Outcome-blind structural replay for clean V4-X1 Phase A.

This runner compares the frozen old V4-X1 representation/support lineage with
one accepted clean-data bundle. It never materializes numeric target returns or
ranks, never fits/scores a model, never computes historical performance, and
never accesses protected/fresh-forward outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

DEFAULT_CONFIG = REPO_ROOT / "config" / "ranking_v4_x1_clean_phase_a_structural_replay_v1.json"
PIT_SUPPORT_RUNNER = REPO_ROOT / "scripts" / "run_v4_3_pit_support_refresh.py"

from idx_trade.ranking_v4_3_ca_training_domain import (  # noqa: E402
    attach_continuity,
    build_training_date_sets,
    build_window_skeleton,
    combine_target_support,
    validate_frozen_tail,
)
from idx_trade.ranking_v4_3_features import (  # noqa: E402
    V4_CONTROL_FEATURE_COLUMNS,
    build_v4_control_feature_table,
)
from idx_trade.ranking_v4_3_preregistration import (  # noqa: E402
    SESSION_GEOMETRY_FEATURE_COLUMNS,
)
from idx_trade.ranking_v4_3_target_execution import (  # noqa: E402
    build_geometry_from_accepted_open,
)
from idx_trade.ranking_v4_3r_support import (  # noqa: E402
    GATE_RATE as CA80_GATE_RATE,
    frozen_support_bucket_counts,
    rethreshold_per_date_support,
)


def _load_pit_support_runner():
    spec = importlib.util.spec_from_file_location(
        "v4_x1_clean_phase_a_pit_support_frozen", PIT_SUPPORT_RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_PIT_SUPPORT_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pit_support = _load_pit_support_runner()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-lock-manifest", type=Path, required=True)
    parser.add_argument("--clean-bundle-manifest", type=Path, required=True)
    parser.add_argument("--clean-panel", type=Path, required=True)
    parser.add_argument("--clean-security-master", type=Path, required=True)
    parser.add_argument("--field-provenance", type=Path, required=True)
    parser.add_argument("--stage-c-root", type=Path, required=True)
    parser.add_argument("--parent-combined-replay-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--open-derivative-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    parser.add_argument("--old-security-master", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"V4_X1_CLEAN_PHASE_A_INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_INVALID:{path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def git_output(repo_root: Path, *args: str, text: bool = True):
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return completed.stdout.strip() if text else completed.stdout


def normalize_identity(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
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


def verify_git_blobs(repo_root: Path, mapping: dict[str, str]) -> dict[str, str]:
    actual: dict[str, str] = {}
    for relative, expected in mapping.items():
        blob = git_output(repo_root, "rev-parse", f"HEAD:{relative}")
        if blob != expected:
            raise RuntimeError(
                f"V4_X1_CLEAN_PHASE_A_GIT_BLOB_CHANGED:{relative}:{blob}!={expected}"
            )
        actual[relative] = blob
    return actual


def verify_execution_lock(path: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    actual = sha256_file(path)
    expected = str(cfg["accepted_execution_lock"]["manifest_sha256"])
    if actual != expected:
        raise RuntimeError(f"V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK_SHA_MISMATCH:{actual}!={expected}")
    data = read_json(path, "V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK")
    if data.get("status") != "V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK_CAPTURED_REPLAY_NOT_RUN":
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK_STATUS_CHANGED")
    runtime = data.get("runtime") or {}
    if runtime.get("exact_match") is not True:
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK_RUNTIME_NOT_EXACT")
    required_false = (
        "provider_calls",
        "network_calls",
        "numeric_target_accessed",
        "model_fit",
        "model_scoring",
        "historical_prediction_generated",
        "historical_performance_computed",
        "protected_forward_outcomes_accessed",
        "forward_counter_mutated",
        "phase_a_replay_run",
    )
    for key in required_false:
        if data.get(key) is not False:
            raise RuntimeError(f"V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK_GUARD_CHANGED:{key}")
    return data


def require_sha(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"V4_X1_CLEAN_PHASE_A_SHA_MISMATCH:{label}:{actual}!={expected}")
    return actual


def verify_stage_c(root: Path, cfg: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    spec = cfg["stage_c_oracle"]
    manifest_path = root / "MANIFEST.json"
    h5_path = root / "h5_support_identities.csv"
    h10_path = root / "h10_support_identities.csv"
    hashes = {
        "manifest": require_sha(manifest_path, str(spec["manifest_sha256"]), "stage_c_manifest"),
        "h5_support": require_sha(h5_path, str(spec["h5_support_sha256"]), "stage_c_h5_support"),
        "h10_support": require_sha(h10_path, str(spec["h10_support_sha256"]), "stage_c_h10_support"),
    }
    manifest = read_json(manifest_path, "V4_X1_CLEAN_PHASE_A_STAGE_C_MANIFEST")
    if manifest.get("status") != "PIT_SECURITY_IDENTITY_STAGE_C_COMPLETE":
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_STAGE_C_STATUS_CHANGED")
    if manifest.get("decision") != "V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION":
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_STAGE_C_DECISION_CHANGED")
    outputs = manifest.get("output_hashes") or {}
    if outputs.get("h5_support_identities.csv") != hashes["h5_support"]:
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_STAGE_C_H5_CHILD_NOT_PINNED")
    if outputs.get("h10_support_identities.csv") != hashes["h10_support"]:
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_STAGE_C_H10_CHILD_NOT_PINNED")
    h5 = normalize_identity(pd.read_csv(h5_path), label="STAGE_C_H5_SUPPORT")[["ticker", "date"]]
    h10 = normalize_identity(pd.read_csv(h10_path), label="STAGE_C_H10_SUPPORT")[["ticker", "date"]]
    if len(h5) != int(spec["expected_h5_rows"]) or len(h10) != int(spec["expected_h10_rows"]):
        raise RuntimeError(
            f"V4_X1_CLEAN_PHASE_A_STAGE_C_SUPPORT_COUNT_CHANGED:{len(h5)}:{len(h10)}"
        )
    return h5, h10, hashes


def load_parent_continuity(root: Path, cfg: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    expected_manifest = str(cfg["corporate_action_parent"]["manifest_sha256"])
    manifest_path = root / "MANIFEST.json"
    actual_manifest = require_sha(manifest_path, expected_manifest, "parent_combined_manifest")
    manifest = read_json(manifest_path, "V4_X1_CLEAN_PHASE_A_PARENT_CA_MANIFEST")
    continuity_path = root / "v4_3_ca_training_domain_idx_combined_continuity.csv"
    continuity_sha = sha256_file(continuity_path)
    expected_child = str((manifest.get("output_hashes") or {}).get("continuity") or "")
    if not expected_child or continuity_sha != expected_child:
        raise RuntimeError(
            f"V4_X1_CLEAN_PHASE_A_PARENT_CA_CHILD_SHA_MISMATCH:{continuity_sha}!={expected_child}"
        )
    continuity = pd.read_csv(continuity_path)
    return continuity, {"manifest": actual_manifest, "continuity": continuity_sha}


def load_calendar(path: Path) -> pd.DataFrame:
    calendar = pd.read_csv(path)
    if "date" not in calendar.columns:
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_CALENDAR_MISSING_DATE")
    calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if calendar["date"].isna().any() or calendar["date"].duplicated().any():
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_CALENDAR_INVALID")
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)
    return calendar


def build_state_map(anchors: pd.DataFrame, intervals: pd.DataFrame, calendar: pd.DataFrame):
    anchors = anchors.copy()
    intervals = intervals.copy()
    anchors["market"] = anchors["market"].astype(str).str.upper()
    anchors["state"] = anchors["state"].astype(str).str.upper()
    intervals["market"] = intervals["market"].astype(str).str.upper()
    intervals["state"] = intervals["state"].astype(str).str.upper()
    return pit_support.state_map_from_inputs(anchors, intervals, calendar)


def _normalize_price_inputs(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    out = normalize_identity(frame, label=label)
    return out


def build_old_price_evidence(
    panel: pd.DataFrame,
    calendar: pd.DataFrame,
    derivative: pd.DataFrame,
    overlay: pd.DataFrame,
    anchors: pd.DataFrame,
    intervals: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    panel = _normalize_price_inputs(panel, label="OLD_PANEL")
    derivative = _normalize_price_inputs(derivative, label="OLD_OPEN_DERIVATIVE")
    overlay = _normalize_price_inputs(overlay, label="OLD_OPEN_OVERLAY")
    if len(derivative) != len(panel):
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_OLD_OPEN_DERIVATIVE_ROW_COUNT_MISMATCH")
    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))
    base = panel[["ticker", "date", "close"]].copy()
    base["session_index"] = base["date"].map(date_to_index)
    if base["session_index"].isna().any():
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_OLD_PANEL_DATE_OUTSIDE_CALENDAR")
    base["session_index"] = base["session_index"].astype(int)
    if "open" not in derivative.columns or "recovered_open" not in overlay.columns:
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_OLD_OPEN_COLUMNS_MISSING")
    base = base.merge(
        derivative[["ticker", "date", "open"]].rename(columns={"open": "derivative_open"}),
        on=["ticker", "date"], how="left", validate="one_to_one"
    )
    base = base.merge(
        overlay[["ticker", "date", "recovered_open"]],
        on=["ticker", "date"], how="left", validate="one_to_one"
    )
    derivative_open = pd.to_numeric(base["derivative_open"], errors="coerce").astype(float)
    recovered_open = pd.to_numeric(base["recovered_open"], errors="coerce").astype(float)
    derivative_valid = np.isfinite(derivative_open) & derivative_open.gt(0.0)
    recovered_valid = np.isfinite(recovered_open) & recovered_open.gt(0.0)
    both = derivative_valid & recovered_valid
    if both.any() and not np.allclose(
        derivative_open[both].to_numpy(dtype=float),
        recovered_open[both].to_numpy(dtype=float),
        rtol=0.0,
        atol=1e-9,
    ):
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_OLD_OPEN_DERIVATIVE_OVERLAY_CONFLICT")
    accepted_open = derivative_open.where(derivative_valid, recovered_open)
    close = pd.to_numeric(base["close"], errors="coerce").astype(float)
    states, conflicts = build_state_map(anchors, intervals, calendar)
    market_state = [
        states.get((ticker, int(index)), "UNKNOWN")
        for ticker, index in base[["ticker", "session_index"]].itertuples(index=False)
    ]
    result = pd.DataFrame(
        {
            "ticker": base["ticker"],
            "date": base["date"],
            "session_index": base["session_index"],
            "market_state": market_state,
            "accepted_open": accepted_open,
            "open_admitted": np.isfinite(accepted_open) & accepted_open.gt(0.0),
            "close": close,
            "close_admitted": np.isfinite(close) & close.gt(0.0),
        }
    )
    return result, {
        "rows": int(len(result)),
        "derivative_open_admitted": int(derivative_valid.sum()),
        "overlay_open_admitted": int(recovered_valid.sum()),
        "final_open_admitted": int(result["open_admitted"].sum()),
        "close_admitted": int(result["close_admitted"].sum()),
        "state_conflicts": int(conflicts),
    }


def build_clean_price_evidence(
    panel: pd.DataFrame,
    calendar: pd.DataFrame,
    anchors: pd.DataFrame,
    intervals: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    panel = _normalize_price_inputs(panel, label="CLEAN_PANEL")
    if "open" not in panel.columns or "close" not in panel.columns:
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_CLEAN_PANEL_MISSING_OPEN_CLOSE")
    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))
    panel["session_index"] = panel["date"].map(date_to_index)
    if panel["session_index"].isna().any():
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_CLEAN_PANEL_DATE_OUTSIDE_CALENDAR")
    panel["session_index"] = panel["session_index"].astype(int)
    accepted_open = pd.to_numeric(panel["open"], errors="coerce").astype(float)
    close = pd.to_numeric(panel["close"], errors="coerce").astype(float)
    states, conflicts = build_state_map(anchors, intervals, calendar)
    market_state = [
        states.get((ticker, int(index)), "UNKNOWN")
        for ticker, index in panel[["ticker", "session_index"]].itertuples(index=False)
    ]
    result = pd.DataFrame(
        {
            "ticker": panel["ticker"],
            "date": panel["date"],
            "session_index": panel["session_index"],
            "market_state": market_state,
            "accepted_open": accepted_open,
            "open_admitted": np.isfinite(accepted_open) & accepted_open.gt(0.0),
            "close": close,
            "close_admitted": np.isfinite(close) & close.gt(0.0),
        }
    )
    return result, {
        "rows": int(len(result)),
        "final_open_admitted": int(result["open_admitted"].sum()),
        "close_admitted": int(result["close_admitted"].sum()),
        "state_conflicts": int(conflicts),
    }


def build_primary_model_frame(
    panel: pd.DataFrame,
    calendar: pd.DataFrame,
    security_master: pd.DataFrame,
    price_evidence: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    features, diagnostics = build_v4_control_feature_table(
        panel, calendar["date"], security_master
    )
    primary = features.loc[features["universe_primary_liquid"].astype(bool)].copy()
    wanted = [
        "ticker", "date", "session_index", "high", "low", "close",
        *V4_CONTROL_FEATURE_COLUMNS,
    ]
    missing = set(wanted) - set(primary.columns)
    if missing:
        raise RuntimeError(f"V4_X1_CLEAN_PHASE_A_PRIMARY_FEATURE_COLUMNS_MISSING:{sorted(missing)}")
    frame = primary[wanted].copy()
    geometry = build_geometry_from_accepted_open(
        frame[["ticker", "date", "high", "low", "close"]],
        price_evidence,
    )
    frame = frame.merge(
        geometry[["ticker", "date", *SESSION_GEOMETRY_FEATURE_COLUMNS]],
        on=["ticker", "date"], how="left", validate="one_to_one"
    )
    if frame.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_MODEL_FRAME_DUPLICATE_IDENTITY")
    frame = frame.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    return frame, {
        "listing_diagnostics": diagnostics.__dict__,
        "primary_rows": int(len(frame)),
        "primary_tickers": int(frame["ticker"].nunique()),
        "primary_dates": int(frame["date"].nunique()),
    }


def decision_support_from_model_frame(
    model_frame: pd.DataFrame,
    price_evidence: pd.DataFrame,
    *,
    frozen_end_index: int,
) -> pd.DataFrame:
    decision = model_frame[["ticker", "date", "session_index"]].copy()
    decision = decision.loc[decision["session_index"].le(int(frozen_end_index))].copy()
    lookup = price_evidence.set_index(["ticker", "session_index"])[
        ["market_state", "open_admitted", "close_admitted"]
    ]

    def status(ticker: str, index: int, offset: int, field: str) -> Any:
        key = (ticker, int(index) + int(offset))
        try:
            return lookup.at[key, field]
        except KeyError:
            return None

    entry: list[bool] = []
    h5: list[bool] = []
    h10: list[bool] = []
    for ticker, index in decision[["ticker", "session_index"]].itertuples(index=False):
        entry.append(
            status(ticker, index, 1, "market_state") == "ACTIVE"
            and status(ticker, index, 1, "open_admitted") is not None
            and bool(status(ticker, index, 1, "open_admitted"))
        )
        h5.append(
            status(ticker, index, 5, "market_state") == "ACTIVE"
            and status(ticker, index, 5, "close_admitted") is not None
            and bool(status(ticker, index, 5, "close_admitted"))
        )
        h10.append(
            status(ticker, index, 10, "market_state") == "ACTIVE"
            and status(ticker, index, 10, "close_admitted") is not None
            and bool(status(ticker, index, 10, "close_admitted"))
        )
    decision["entry_open_support"] = entry
    decision["h5_close_support"] = h5
    decision["h10_close_support"] = h10
    return decision


def replay_support(
    model_frame: pd.DataFrame,
    price_evidence: pd.DataFrame,
    continuity: pd.DataFrame,
    calendar: pd.DataFrame,
    validation_folds: pd.DataFrame,
) -> dict[str, Any]:
    frozen_end_index = int(validation_folds["session_index"].max())
    decision = decision_support_from_model_frame(
        model_frame, price_evidence, frozen_end_index=frozen_end_index
    )
    windows = build_window_skeleton(
        decision,
        calendar["date"],
        max_signal_session_index=frozen_end_index,
    )
    continuity_windows = attach_continuity(windows, continuity)
    rows, per_date_v4_3 = combine_target_support(decision, continuity_windows)
    per_date = rethreshold_per_date_support(per_date_v4_3, gate_rate=CA80_GATE_RATE)
    frozen_check = validate_frozen_tail(per_date, validation_folds)
    buckets = frozen_support_bucket_counts(per_date, validation_folds)
    training_dates = build_training_date_sets(per_date, validation_folds)
    counts = {
        f"F{int(fold)}_{head}": int(value)
        for (fold, head), value in training_dates.groupby(["fold", "head"]).size().items()
    }
    expected_keys = {f"F{fold}_{head}" for fold in range(1, 7) for head in ("H5", "H10")}
    all_12_nonempty = set(counts) == expected_keys and all(value > 0 for value in counts.values())

    eligible_h5 = set(per_date.loc[per_date["h5_eligible"].astype(bool), "date"])
    eligible_h10 = set(per_date.loc[per_date["h10_eligible"].astype(bool), "date"])
    h5_support = rows.loc[
        rows["h5_full_target_support"].astype(bool) & rows["date"].isin(eligible_h5),
        ["ticker", "date"],
    ].copy()
    h10_support = rows.loc[
        rows["h10_full_target_support"].astype(bool) & rows["date"].isin(eligible_h10),
        ["ticker", "date"],
    ].copy()
    h5_support = normalize_identity(h5_support, label="REDERIVED_H5_SUPPORT")
    h10_support = normalize_identity(h10_support, label="REDERIVED_H10_SUPPORT")
    return {
        "rows": rows,
        "per_date": per_date,
        "training_dates": training_dates,
        "training_date_counts": counts,
        "all_12_training_sets_nonempty": bool(all_12_nonempty),
        "frozen_check": frozen_check,
        "support_buckets": buckets,
        "h5_support": h5_support,
        "h10_support": h10_support,
    }


def canonical_identity(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        normalize_identity(frame, label="CANONICAL_IDENTITY")[["ticker", "date"]]
        .sort_values(["date", "ticker"], kind="mergesort")
        .reset_index(drop=True)
    )


def assert_same_identity(actual: pd.DataFrame, expected: pd.DataFrame, *, label: str) -> None:
    left = canonical_identity(actual)
    right = canonical_identity(expected)
    if not left.equals(right):
        left_keys = set(map(tuple, left[["ticker", "date"]].itertuples(index=False, name=None)))
        right_keys = set(map(tuple, right[["ticker", "date"]].itertuples(index=False, name=None)))
        raise RuntimeError(
            f"V4_X1_CLEAN_PHASE_A_{label}_MISMATCH:"
            f"actual={len(left)} expected={len(right)} "
            f"add={len(left_keys-right_keys)} drop={len(right_keys-left_keys)}"
        )


def support_delta(old: pd.DataFrame, clean: pd.DataFrame, *, head: str) -> tuple[pd.DataFrame, dict[str, int]]:
    old_keys = set(map(tuple, canonical_identity(old).itertuples(index=False, name=None)))
    clean_keys = set(map(tuple, canonical_identity(clean).itertuples(index=False, name=None)))
    add = sorted(clean_keys - old_keys, key=lambda value: (value[1], value[0]))
    drop = sorted(old_keys - clean_keys, key=lambda value: (value[1], value[0]))
    rows = [
        {"head": head, "ticker": ticker, "date": day, "change": "ADD"}
        for ticker, day in add
    ] + [
        {"head": head, "ticker": ticker, "date": day, "change": "DROP"}
        for ticker, day in drop
    ]
    delta = pd.DataFrame(rows, columns=["head", "ticker", "date", "change"])
    summary = {
        "old_rows": int(len(old_keys)),
        "clean_rows": int(len(clean_keys)),
        "shared_rows": int(len(old_keys & clean_keys)),
        "added_rows": int(len(add)),
        "dropped_rows": int(len(drop)),
        "added_tickers": int(len({ticker for ticker, _ in add})),
        "dropped_tickers": int(len({ticker for ticker, _ in drop})),
        "added_dates": int(len({day for _, day in add})),
        "dropped_dates": int(len({day for _, day in drop})),
    }
    return delta, summary


def feature_delta_summary(
    old_frame: pd.DataFrame,
    clean_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, int]]:
    features = [*V4_CONTROL_FEATURE_COLUMNS, *SESSION_GEOMETRY_FEATURE_COLUMNS]
    old_keys = old_frame[["ticker", "date"]].copy()
    clean_keys = clean_frame[["ticker", "date"]].copy()
    outer = old_keys.merge(clean_keys, on=["ticker", "date"], how="outer", indicator=True)
    identity_delta = outer.loc[outer["_merge"].ne("both")].copy()
    identity_delta["change"] = identity_delta["_merge"].map(
        {"left_only": "PRIMARY_DROP", "right_only": "PRIMARY_ADD"}
    ).astype(str)
    identity_delta = identity_delta[["ticker", "date", "change"]]

    shared = old_frame[["ticker", "date", *features]].merge(
        clean_frame[["ticker", "date", *features]],
        on=["ticker", "date"], how="inner", validate="one_to_one", suffixes=("_old", "_clean")
    )
    feature_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    for feature in features:
        old = pd.to_numeric(shared[f"{feature}_old"], errors="coerce").astype(float)
        clean = pd.to_numeric(shared[f"{feature}_clean"], errors="coerce").astype(float)
        old_finite = np.isfinite(old)
        clean_finite = np.isfinite(clean)
        both = old_finite & clean_finite
        diffs = np.abs(old[both].to_numpy(dtype=float) - clean[both].to_numpy(dtype=float))
        changed = int(np.count_nonzero(diffs != 0.0))
        feature_rows.append(
            {
                "feature": feature,
                "shared_rows": int(len(shared)),
                "old_finite": int(old_finite.sum()),
                "clean_finite": int(clean_finite.sum()),
                "both_finite": int(both.sum()),
                "finite_value_changed_exact": changed,
                "finite_value_changed_fraction": float(changed / int(both.sum())) if int(both.sum()) else 0.0,
                "abs_delta_p50": float(np.quantile(diffs, 0.50)) if len(diffs) else np.nan,
                "abs_delta_p95": float(np.quantile(diffs, 0.95)) if len(diffs) else np.nan,
                "abs_delta_p99": float(np.quantile(diffs, 0.99)) if len(diffs) else np.nan,
                "abs_delta_max": float(np.max(diffs)) if len(diffs) else np.nan,
            }
        )
        missing_rows.append(
            {
                "feature": feature,
                "shared_rows": int(len(shared)),
                "finite_to_missing": int((old_finite & ~clean_finite).sum()),
                "missing_to_finite": int((~old_finite & clean_finite).sum()),
                "both_missing": int((~old_finite & ~clean_finite).sum()),
                "both_finite": int(both.sum()),
            }
        )
    feature_summary = pd.DataFrame(feature_rows)
    missing_summary = pd.DataFrame(missing_rows)
    primary_summary = {
        "old_primary_rows": int(len(old_frame)),
        "clean_primary_rows": int(len(clean_frame)),
        "shared_primary_rows": int(len(shared)),
        "primary_added_rows": int(identity_delta["change"].eq("PRIMARY_ADD").sum()) if len(identity_delta) else 0,
        "primary_dropped_rows": int(identity_delta["change"].eq("PRIMARY_DROP").sum()) if len(identity_delta) else 0,
    }
    return feature_summary, missing_summary, identity_delta, primary_summary


def json_safe(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config
    if output_dir.exists():
        raise RuntimeError(f"V4_X1_CLEAN_PHASE_A_REFUSE_OVERWRITE:{output_dir}")
    if git_output(repo_root, "status", "--porcelain"):
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_GIT_WORKTREE_NOT_CLEAN")

    cfg = read_json(config_path, "V4_X1_CLEAN_PHASE_A_CONFIG")
    if cfg.get("schema_version") != "ranking_v4_x1_clean_phase_a_structural_replay_v1":
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_CONFIG_SCHEMA_INVALID")
    if cfg.get("generation_id") != "V4_X1_CLEAN_REMEDIATED_PROSPECTIVE_V1":
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_GENERATION_INVALID")
    if float(cfg.get("ca80_gate_rate", -1.0)) != float(CA80_GATE_RATE) or float(CA80_GATE_RATE) != 0.80:
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_CA80_GATE_CHANGED")
    scientific_blobs = verify_git_blobs(repo_root, cfg["pinned_git_blobs"])
    execution_lock = verify_execution_lock(args.execution_lock_manifest.resolve(), cfg)

    paths = {
        "calendar": args.artifact_root / "official_exchange_sessions_1260.csv",
        "old_panel": args.artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet",
        "anchors": args.artifact_root / "tradability_anchors_1260.csv",
        "intervals": args.artifact_root / "tradability_intervals_1260.csv",
        "old_open_derivative": args.open_derivative_root / "execution_open_candidate_panel_yahoo_tradingview.parquet",
        "old_open_derivative_manifest": args.open_derivative_root / "artifact_manifest.json",
        "old_open_overlay": args.overlay_root / "open_recovery_overlay.parquet",
        "old_open_overlay_manifest": args.overlay_root / "manifest.json",
        "old_security_master": args.old_security_master.resolve(),
        "clean_bundle_manifest": args.clean_bundle_manifest.resolve(),
        "clean_panel": args.clean_panel.resolve(),
        "clean_security_master": args.clean_security_master.resolve(),
        "field_provenance": args.field_provenance.resolve(),
    }
    expected_hashes = cfg["input_sha256"]
    input_hashes: dict[str, str] = {}
    for name, path in paths.items():
        input_hashes[name] = require_sha(path, str(expected_hashes[name]), name)

    clean_bundle = read_json(paths["clean_bundle_manifest"], "V4_X1_CLEAN_PHASE_A_CLEAN_BUNDLE")
    if clean_bundle.get("stage_a_panel_rewritten") is True or clean_bundle.get("stage_a_hlc_open_changed") is True:
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_CLEAN_BUNDLE_UNEXPECTED_STAGE_A_REWRITE")

    old_h5_oracle, old_h10_oracle, stage_c_hashes = verify_stage_c(args.stage_c_root.resolve(), cfg)
    continuity, ca_hashes = load_parent_continuity(args.parent_combined_replay_root.resolve(), cfg)

    validation_path = repo_root / cfg["validation_folds"]["path"]
    validation_raw = git_output(repo_root, "show", f"HEAD:{cfg['validation_folds']['path']}", text=False)
    validation_sha = sha256_bytes(validation_raw)
    if validation_sha != str(cfg["validation_folds"]["sha256"]):
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_VALIDATION_FOLDS_SHA_CHANGED")
    validation_folds = pd.read_csv(validation_path)
    validation_folds["date"] = pd.to_datetime(validation_folds["date"], errors="coerce").dt.normalize()
    if len(validation_folds) != 600 or validation_folds["date"].isna().any() or validation_folds["date"].duplicated().any():
        raise RuntimeError("V4_X1_CLEAN_PHASE_A_VALIDATION_FOLDS_INVALID")

    calendar = load_calendar(paths["calendar"])
    anchors = pd.read_csv(paths["anchors"])
    intervals = pd.read_csv(paths["intervals"])
    old_panel = pd.read_parquet(paths["old_panel"])
    clean_panel = pd.read_parquet(paths["clean_panel"])
    old_master = pd.read_csv(paths["old_security_master"])
    clean_master = pd.read_csv(paths["clean_security_master"])
    derivative = pd.read_parquet(paths["old_open_derivative"])
    overlay = pd.read_parquet(paths["old_open_overlay"])

    old_price, old_price_stats = build_old_price_evidence(
        old_panel, calendar, derivative, overlay, anchors, intervals
    )
    clean_price, clean_price_stats = build_clean_price_evidence(
        clean_panel, calendar, anchors, intervals
    )
    old_model_frame, old_frame_stats = build_primary_model_frame(
        old_panel, calendar, old_master, old_price
    )
    clean_model_frame, clean_frame_stats = build_primary_model_frame(
        clean_panel, calendar, clean_master, clean_price
    )

    old_support = replay_support(
        old_model_frame, old_price, continuity, calendar, validation_folds
    )
    assert_same_identity(old_support["h5_support"], old_h5_oracle, label="OLD_H5_ORACLE")
    assert_same_identity(old_support["h10_support"], old_h10_oracle, label="OLD_H10_ORACLE")

    clean_support = replay_support(
        clean_model_frame, clean_price, continuity, calendar, validation_folds
    )
    h5_delta, h5_delta_summary = support_delta(old_h5_oracle, clean_support["h5_support"], head="H5")
    h10_delta, h10_delta_summary = support_delta(old_h10_oracle, clean_support["h10_support"], head="H10")
    support_delta_frame = pd.concat([h5_delta, h10_delta], ignore_index=True)

    feature_summary, missing_summary, primary_delta, primary_summary = feature_delta_summary(
        old_model_frame, clean_model_frame
    )

    clean_frozen = clean_support["frozen_check"]
    ca80_pass = bool(
        clean_frozen.get("all_frozen_600_full_target_eligible") is True
        and clean_frozen.get("tail_600_identity_unchanged") is True
        and int(clean_frozen.get("eligible_sessions_after_frozen_end", -1)) == 0
        and clean_support["all_12_training_sets_nonempty"] is True
    )
    status = (
        "V4_X1_CLEAN_PHASE_A_STRUCTURAL_REPLAY_COMPLETE_INDEPENDENT_REVIEW_REQUIRED"
        if ca80_pass
        else "V4_X1_CLEAN_PHASE_A_CA80_SUPPORT_FAIL_REVIEW_REQUIRED"
    )

    output_dir.mkdir(parents=True, exist_ok=False)
    outputs = {
        "clean_h5_support": output_dir / "clean_h5_support_identities.csv",
        "clean_h10_support": output_dir / "clean_h10_support_identities.csv",
        "support_delta": output_dir / "old_vs_clean_support_delta.csv",
        "primary_delta": output_dir / "old_vs_clean_primary_identity_delta.csv",
        "feature_delta": output_dir / "old_vs_clean_feature_delta_summary.csv",
        "missingness": output_dir / "old_vs_clean_missingness_transition_summary.csv",
        "per_date": output_dir / "clean_ca80_support_per_date.csv",
        "training_counts": output_dir / "clean_training_date_counts.csv",
        "summary": output_dir / "summary.json",
        "manifest": output_dir / "MANIFEST.json",
    }
    canonical_identity(clean_support["h5_support"]).to_csv(outputs["clean_h5_support"], index=False, date_format="%Y-%m-%d", lineterminator="\n")
    canonical_identity(clean_support["h10_support"]).to_csv(outputs["clean_h10_support"], index=False, date_format="%Y-%m-%d", lineterminator="\n")
    support_delta_frame.to_csv(outputs["support_delta"], index=False, date_format="%Y-%m-%d", lineterminator="\n")
    primary_delta.to_csv(outputs["primary_delta"], index=False, date_format="%Y-%m-%d", lineterminator="\n")
    feature_summary.to_csv(outputs["feature_delta"], index=False, lineterminator="\n")
    missing_summary.to_csv(outputs["missingness"], index=False, lineterminator="\n")
    clean_support["per_date"].to_csv(outputs["per_date"], index=False, date_format="%Y-%m-%d", lineterminator="\n")
    training_counts = pd.DataFrame(
        [
            {"fold_head": key, "clean_training_dates": value, "old_training_dates": int(cfg["old_training_date_counts"].get(key, -1))}
            for key, value in sorted(clean_support["training_date_counts"].items())
        ]
    )
    training_counts.to_csv(outputs["training_counts"], index=False, lineterminator="\n")

    summary = {
        "schema_version": "v4_x1_clean_phase_a_structural_replay_summary_v1",
        "status": status,
        "generation_id": cfg["generation_id"],
        "outcome_blind": True,
        "old_support_oracle_exact_match": True,
        "ca80_gate_rate": float(CA80_GATE_RATE),
        "clean_ca80_gate_pass": ca80_pass,
        "clean_frozen_support": clean_frozen,
        "clean_support_buckets": clean_support["support_buckets"],
        "old_training_date_counts": old_support["training_date_counts"],
        "clean_training_date_counts": clean_support["training_date_counts"],
        "all_12_clean_training_sets_nonempty": clean_support["all_12_training_sets_nonempty"],
        "support_delta": {"H5": h5_delta_summary, "H10": h10_delta_summary},
        "primary_identity": primary_summary,
        "old_price_evidence": old_price_stats,
        "clean_price_evidence": clean_price_stats,
        "old_model_frame": old_frame_stats,
        "clean_model_frame": clean_frame_stats,
        "scientific_git_blobs": scientific_blobs,
        "execution_lock_manifest_sha256": cfg["accepted_execution_lock"]["manifest_sha256"],
        "input_hashes": input_hashes,
        "stage_c_hashes": stage_c_hashes,
        "corporate_action_hashes": ca_hashes,
        "validation_folds_sha256": validation_sha,
        "provider_calls": False,
        "network_calls": False,
        "numeric_target_values_accessed": False,
        "target_returns_accessed": False,
        "target_ranks_accessed": False,
        "model_fit": False,
        "model_scoring": False,
        "historical_predictions_accessed": False,
        "historical_performance_accessed": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
        "counter_mutated": False,
        "data_mutated": False,
        "ca_semantics_changed": False,
        "session_semantics_changed": False,
        "phase_b_refit_authorized": False,
        "next": "INDEPENDENT_REVIEW_ONLY; DO_NOT REFIT AUTOMATICALLY",
    }
    outputs["summary"].write_text(
        json.dumps(json_safe(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output_hashes = {
        name: sha256_file(path)
        for name, path in outputs.items()
        if name != "manifest" and path.is_file()
    }
    manifest = {
        "schema_version": "v4_x1_clean_phase_a_structural_replay_manifest_v1",
        "status": status,
        "generation_id": cfg["generation_id"],
        "outcome_blind": True,
        "input_hashes": input_hashes,
        "stage_c_hashes": stage_c_hashes,
        "corporate_action_hashes": ca_hashes,
        "execution_lock_manifest_sha256": cfg["accepted_execution_lock"]["manifest_sha256"],
        "scientific_git_blobs": scientific_blobs,
        "output_hashes": output_hashes,
        "old_support_oracle_exact_match": True,
        "clean_ca80_gate_pass": ca80_pass,
        "numeric_target_values_accessed": False,
        "model_fit": False,
        "model_scoring": False,
        "historical_performance_accessed": False,
        "provider_calls": False,
        "network_calls": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
        "counter_mutated": False,
        "phase_b_refit_authorized": False,
    }
    outputs["manifest"].write_text(
        json.dumps(json_safe(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": status,
                "manifest": str(outputs["manifest"]),
                "manifest_sha256": sha256_file(outputs["manifest"]),
                "clean_ca80_gate_pass": ca80_pass,
                "support_delta": {"H5": h5_delta_summary, "H10": h10_delta_summary},
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
