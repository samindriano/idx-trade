from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from .provenance import sha256_file
from .research_labels import BarrierLabelConfig, build_first_touch_labels
from .research_labels_fast import build_first_touch_labels_multi_horizon_fast
from .stage5_ranking_holdout import (
    FROZEN_CALENDAR_SHA256,
    FROZEN_PANEL_SHA256,
    _assert_environment,
    _calendar,
)
from .storage import write_parquet_atomic


HORIZONS = (5, 10, 20)
NUMERIC_COLUMNS = (
    "signal_reference_close",
    "atr",
    "sl_atr_multiple",
    "reward_risk",
    "tp_level",
    "sl_level",
    "binary_target",
    "mfe_h",
    "mae_h",
    "normalized_close_return_h",
    "research_r_h",
)
EXACT_COLUMNS = (
    "ticker",
    "signal_session_index",
    "horizon",
    "label_status",
    "path_complete",
)
DATE_COLUMNS = ("signal_date", "first_barrier_date", "unresolved_date")
FLOAT_ATOL = 1e-12


def _read_panel(path: Path) -> pd.DataFrame:
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("full-panel equivalence benchmark requires parquet panel")
    panel = pd.read_parquet(path)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if panel["date"].isna().any():
        raise ValueError("panel contains invalid dates")
    return panel


def _peak_working_set_bytes() -> int | None:
    if platform.system() == "Windows":
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            handle,
            ctypes.byref(counters),
            counters.cb,
        )
        if ok:
            return int(counters.PeakWorkingSetSize)
        return None
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if platform.system() == "Darwin":
            return value
        return value * 1024
    except Exception:
        return None


def _legacy_worker(panel_path: str, calendar_path: str, horizon: int, output_path: str) -> dict[str, object]:
    start = time.perf_counter()
    panel_file = Path(panel_path)
    calendar_file = Path(calendar_path)
    if sha256_file(panel_file) != FROZEN_PANEL_SHA256:
        raise RuntimeError("legacy worker panel hash mismatch")
    calendar = _calendar(calendar_file, "date")
    panel = _read_panel(panel_file)
    labels = build_first_touch_labels(panel, calendar, config=BarrierLabelConfig(horizon=horizon))
    out = Path(output_path)
    write_parquet_atomic(labels, out)
    return {
        "engine": "legacy",
        "horizon": int(horizon),
        "elapsed_seconds": float(time.perf_counter() - start),
        "peak_working_set_bytes": _peak_working_set_bytes(),
        "rows": int(len(labels)),
        "sha256": sha256_file(out),
        "path": str(out),
        "pid": int(os.getpid()),
    }


def _fast_worker(panel_path: str, calendar_path: str, output_dir: str) -> dict[str, object]:
    start = time.perf_counter()
    panel_file = Path(panel_path)
    calendar_file = Path(calendar_path)
    if sha256_file(panel_file) != FROZEN_PANEL_SHA256:
        raise RuntimeError("fast worker panel hash mismatch")
    calendar = _calendar(calendar_file, "date")
    panel = _read_panel(panel_file)
    outputs = build_first_touch_labels_multi_horizon_fast(panel, calendar, horizons=HORIZONS)
    details: dict[str, object] = {}
    root = Path(output_dir)
    for horizon in HORIZONS:
        out = root / f"fast_h{horizon}_labels.parquet"
        write_parquet_atomic(outputs[horizon], out)
        details[str(horizon)] = {
            "rows": int(len(outputs[horizon])),
            "sha256": sha256_file(out),
            "path": str(out),
        }
    return {
        "engine": "fast_multi_horizon",
        "horizons": list(HORIZONS),
        "elapsed_seconds": float(time.perf_counter() - start),
        "peak_working_set_bytes": _peak_working_set_bytes(),
        "outputs": details,
        "pid": int(os.getpid()),
    }


def _normalize_for_compare(frame: pd.DataFrame) -> pd.DataFrame:
    required = {*EXACT_COLUMNS, *DATE_COLUMNS, *NUMERIC_COLUMNS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"label comparison missing columns: {sorted(missing)}")
    data = frame.loc[:, [*EXACT_COLUMNS, *DATE_COLUMNS, *NUMERIC_COLUMNS]].copy()
    data["ticker"] = data["ticker"].astype(str)
    for column in DATE_COLUMNS:
        data[column] = pd.to_datetime(data[column], errors="coerce").dt.tz_localize(None)
    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce").astype(float)
    return data.sort_values(["ticker", "signal_date"], kind="mergesort").reset_index(drop=True)


def compare_label_frames(legacy: pd.DataFrame, fast: pd.DataFrame) -> dict[str, object]:
    left = _normalize_for_compare(legacy)
    right = _normalize_for_compare(fast)
    result: dict[str, object] = {
        "rows_legacy": int(len(left)),
        "rows_fast": int(len(right)),
        "row_count_equal": bool(len(left) == len(right)),
        "exact_columns": {},
        "date_columns": {},
        "numeric_columns": {},
    }
    if len(left) != len(right):
        result["equal"] = False
        return result

    exact_ok = True
    for column in EXACT_COLUMNS:
        equal = bool(left[column].equals(right[column]))
        result["exact_columns"][column] = equal
        exact_ok &= equal

    date_ok = True
    for column in DATE_COLUMNS:
        equal = bool(left[column].equals(right[column]))
        result["date_columns"][column] = equal
        date_ok &= equal

    numeric_ok = True
    for column in NUMERIC_COLUMNS:
        a = left[column].to_numpy(dtype=float)
        b = right[column].to_numpy(dtype=float)
        finite_both = np.isfinite(a) & np.isfinite(b)
        nan_equal = np.array_equal(np.isnan(a), np.isnan(b))
        inf_equal = np.array_equal(np.isposinf(a), np.isposinf(b)) and np.array_equal(
            np.isneginf(a), np.isneginf(b)
        )
        max_abs = float(np.max(np.abs(a[finite_both] - b[finite_both]))) if finite_both.any() else 0.0
        equal = bool(nan_equal and inf_equal and np.allclose(a, b, rtol=0.0, atol=FLOAT_ATOL, equal_nan=True))
        result["numeric_columns"][column] = {
            "equal_with_atol": equal,
            "atol": FLOAT_ATOL,
            "max_abs_diff": max_abs,
        }
        numeric_ok &= equal

    result["equal"] = bool(exact_ok and date_ok and numeric_ok)
    return result


def run_full_panel_benchmark(*, panel_path: Path, calendar_path: Path, output_dir: Path, code_commit: str) -> dict[str, object]:
    environment = _assert_environment()
    if sha256_file(panel_path) != FROZEN_PANEL_SHA256:
        raise RuntimeError("benchmark frozen panel hash mismatch")
    if sha256_file(calendar_path) != FROZEN_CALENDAR_SHA256:
        raise RuntimeError("benchmark frozen calendar hash mismatch")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("benchmark output directory must be new or empty")
    output_dir.mkdir(parents=True, exist_ok=True)

    legacy_details: dict[str, object] = {}
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                _legacy_worker,
                str(panel_path),
                str(calendar_path),
                horizon,
                str(output_dir / f"legacy_h{horizon}_labels.parquet"),
            ): horizon
            for horizon in HORIZONS
        }
        for future in as_completed(futures):
            horizon = futures[future]
            legacy_details[str(horizon)] = future.result()

    with ProcessPoolExecutor(max_workers=1) as executor:
        fast_detail = executor.submit(_fast_worker, str(panel_path), str(calendar_path), str(output_dir)).result()

    comparisons: dict[str, object] = {}
    all_equal = True
    for horizon in HORIZONS:
        legacy_path = output_dir / f"legacy_h{horizon}_labels.parquet"
        fast_path = output_dir / f"fast_h{horizon}_labels.parquet"
        comparison = compare_label_frames(pd.read_parquet(legacy_path), pd.read_parquet(fast_path))
        comparisons[str(horizon)] = comparison
        all_equal &= bool(comparison.get("equal", False))

    fast_h10 = output_dir / "fast_h10_labels.parquet"
    report = {
        "status": "FULL_PANEL_LEGACY_FAST_EQUIVALENT" if all_equal else "FULL_PANEL_LEGACY_FAST_MISMATCH",
        "legacy_fast_equal": bool(all_equal),
        "code_commit": code_commit,
        "environment": environment,
        "panel_sha256": FROZEN_PANEL_SHA256,
        "calendar_sha256": FROZEN_CALENDAR_SHA256,
        "horizons": list(HORIZONS),
        "legacy_parallel_workers": 3,
        "legacy_runs": legacy_details,
        "fast_run": fast_detail,
        "comparisons": comparisons,
        "fast_h10_labels_sha256": sha256_file(fast_h10),
        "fast_h10_labels_path": str(fast_h10),
    }
    report_path = output_dir / "research_label_full_panel_equivalence_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    report["report_sha256"] = sha256_file(report_path)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Full frozen-panel legacy-vs-fast label equivalence and performance benchmark")
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_full_panel_benchmark(
        panel_path=args.panel,
        calendar_path=args.calendar,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return 0 if report["legacy_fast_equal"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
