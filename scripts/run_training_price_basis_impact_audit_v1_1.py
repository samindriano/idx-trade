"""Step-2 training price-basis audit runner v1.1.

This is a narrow correction to v1's V2 clean-replay discovery.  The prior
runner accidentally treated the documented corrected-V2 *key* SHA as if it
were the parquet file SHA and pointed at the replay-output root rather than the
immutable corrected-input root.

No scientific thresholds or adjudication rules are changed.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = REPO_ROOT / "scripts" / "run_training_price_basis_impact_audit_v1.py"

spec = importlib.util.spec_from_file_location("training_price_basis_impact_audit_v1_impl", ORIGINAL)
if spec is None or spec.loader is None:
    raise RuntimeError("STEP2_V1_RUNNER_IMPORT_FAILED")
impl = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = impl
spec.loader.exec_module(impl)

# Exact immutable clean-lineage input documented by
# IDX-PIT-SAFE-V2-V3B-O2-REPRODUCTION.
impl.DEFAULT_V2_REPLAY_ROOT = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_v2_v3b_o2_reproduction_v1_20260813_002_fast_h10"
)

# File SHA and key SHA are different contracts.  v1 incorrectly used the key
# SHA as the file SHA.  Keep both pinned and verify both.
V2_CLEAN_REPLAY_FILE_SHA256 = "b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8"
V2_CLEAN_REPLAY_KEY_SHA256 = "79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826"
impl.V2_CLEAN_REPLAY_TABLE_SHA256 = V2_CLEAN_REPLAY_FILE_SHA256

_original_loader = impl.load_v2_replay_table


def _stable_key_hash(frame: pd.DataFrame) -> str:
    required = {"ticker", "date", "signal_session_index"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"V2_CLEAN_REPLAY_KEY_COLUMNS_MISSING:{sorted(missing)}")
    keys = frame[["ticker", "date", "signal_session_index"]].copy()
    keys["ticker"] = keys["ticker"].astype(str)
    keys["date"] = pd.to_datetime(keys["date"], errors="raise").dt.strftime("%Y-%m-%d")
    keys["signal_session_index"] = pd.to_numeric(
        keys["signal_session_index"], errors="raise"
    ).astype(int)
    lines = (
        keys.sort_values(
            ["ticker", "date", "signal_session_index"], kind="mergesort"
        )
        .astype(str)
        .agg("|".join, axis=1)
    )
    return hashlib.sha256(("\n".join(lines.tolist()) + "\n").encode("utf-8")).hexdigest()


def _load_v2_replay_table_v1_1(root: Path):
    frame, path = _original_loader(root)
    key_sha = _stable_key_hash(frame)
    if key_sha != V2_CLEAN_REPLAY_KEY_SHA256:
        raise RuntimeError(
            "V2_CLEAN_REPLAY_KEY_SHA_MISMATCH:"
            f"{key_sha}!={V2_CLEAN_REPLAY_KEY_SHA256}:{path}"
        )
    if len(frame) != 292_631 or frame["ticker"].nunique() != 737:
        raise RuntimeError(
            "V2_CLEAN_REPLAY_POPULATION_MISMATCH:"
            f"rows={len(frame)}:tickers={frame['ticker'].nunique()}"
        )
    return frame, path


impl.load_v2_replay_table = _load_v2_replay_table_v1_1


def main() -> int:
    return impl.main()


if __name__ == "__main__":
    raise SystemExit(main())
