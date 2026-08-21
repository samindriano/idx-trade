"""Fixed six-block robustness for the frozen Decision economic comparison.

Consumes only the already-produced economic-comparison artifact.  It does not
reload alpha targets, rerun policies, or access any additional outcomes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

EXPECTED_COMPARISON_MANIFEST_SHA256 = (
    "d33ec5ab0b6c4c7642c5faf42a7f5980f3d5e4d3d7668552d309aea0ed6e2622"
)
EXPECTED_SCHEMA = "decision_economic_target_outcome_comparison_manifest_v1"
EXPECTED_STATUS = "COMPLETE_DEVELOPMENT_ECONOMIC_TARGET_OUTCOME_COMPARISON_NOT_EXECUTABLE_PNL"
POLICIES = ("NAIVE_TOP10", "DECISION_V1", "DECISION_V2", "DECISION_V3")
PRIMARY_POLICIES = ("NAIVE_TOP10", "DECISION_V2", "DECISION_V3")
EXPECTED_SESSIONS = 600
BLOCK_SIZE = 100


class DecisionEconomicRobustnessError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dist(values: pd.Series) -> dict[str, Any]:
    clean = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if clean.empty:
        return {"n": 0, "mean": None, "median": None, "positive_share": None}
    return {
        "n": int(len(clean)),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "positive_share": float(clean.gt(0.0).mean()),
    }


def load_comparison(comparison_root: str | Path) -> pd.DataFrame:
    root = Path(comparison_root).expanduser().resolve()
    manifest_path = root / "MANIFEST.json"
    outcomes_path = root / "policy_signal_outcomes.csv"
    if not manifest_path.is_file() or not outcomes_path.is_file():
        raise DecisionEconomicRobustnessError("COMPARISON_INPUT_MISSING")
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != EXPECTED_COMPARISON_MANIFEST_SHA256:
        raise DecisionEconomicRobustnessError(
            f"COMPARISON_MANIFEST_SHA_MISMATCH:{manifest_sha}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != EXPECTED_SCHEMA:
        raise DecisionEconomicRobustnessError("COMPARISON_SCHEMA_CHANGED")
    if manifest.get("status") != EXPECTED_STATUS:
        raise DecisionEconomicRobustnessError("COMPARISON_STATUS_CHANGED")
    expected_outcome_sha = str(
        (manifest.get("artifacts") or {}).get("policy_signal_outcomes.csv") or ""
    )
    if sha256_file(outcomes_path) != expected_outcome_sha:
        raise DecisionEconomicRobustnessError("COMPARISON_OUTCOME_HASH_MISMATCH")

    frame = pd.read_csv(outcomes_path)
    required = {
        "policy", "date",
        "h5_complete_support", "h5_gross_basket_return", "h5_net_proxy_primary",
        "h10_complete_support", "h10_gross_basket_return", "h10_net_proxy_primary",
    }
    missing = required - set(frame.columns)
    if missing:
        raise DecisionEconomicRobustnessError(f"OUTCOME_COLUMNS_MISSING:{sorted(missing)}")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if frame.duplicated(["policy", "date"]).any():
        raise DecisionEconomicRobustnessError("OUTCOME_DUPLICATE_POLICY_DATE")
    if set(frame["policy"].astype(str)) != set(POLICIES):
        raise DecisionEconomicRobustnessError("OUTCOME_POLICY_SET_CHANGED")
    dates = pd.DatetimeIndex(frame["date"].unique()).sort_values()
    if len(dates) != EXPECTED_SESSIONS:
        raise DecisionEconomicRobustnessError(f"SESSION_COUNT_CHANGED:{len(dates)}")
    counts = frame.groupby("policy")["date"].nunique().to_dict()
    if any(int(counts.get(policy, 0)) != EXPECTED_SESSIONS for policy in POLICIES):
        raise DecisionEconomicRobustnessError("POLICY_DATE_COVERAGE_CHANGED")
    index_map = {pd.Timestamp(date): idx for idx, date in enumerate(dates)}
    frame["session_index"] = frame["date"].map(index_map).astype(int)
    frame["block"] = frame["session_index"].floordiv(BLOCK_SIZE).add(1).astype(int)
    if set(frame["block"]) != set(range(1, 7)):
        raise DecisionEconomicRobustnessError("FIXED_BLOCK_IDENTITY_CHANGED")
    return frame


def summarize_six_blocks(frame: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "decision_economic_fixed_6block_robustness_v1",
        "status": "COMPLETE_DEVELOPMENT_FIXED_6BLOCK_ROBUSTNESS",
        "interpretation_boundary": {
            "development_evidence_only": True,
            "executable_policy_pnl": False,
            "fixed_blocks": "six consecutive 100-session blocks from the frozen 600-session Decision development window",
            "new_outcomes_accessed": False,
            "policy_or_threshold_tuning": False,
        },
        "horizons": {},
    }

    for horizon in (5, 10):
        support_col = f"h{horizon}_complete_support"
        gross_col = f"h{horizon}_gross_basket_return"
        net_col = f"h{horizon}_net_proxy_primary"
        horizon_blocks: list[dict[str, Any]] = []

        for block_id in range(1, 7):
            block = frame.loc[frame["block"].eq(block_id)].copy()
            support = block.pivot(index="date", columns="policy", values=support_col)
            support = support.reindex(columns=POLICIES)
            common_dates = set(support.index[support.fillna(False).astype(bool).all(axis=1)])
            common = block.loc[block["date"].isin(common_dates)].copy()
            by_policy: dict[str, Any] = {}
            for policy in PRIMARY_POLICIES:
                subset = common.loc[common["policy"].eq(policy)]
                by_policy[policy] = {
                    "gross": _dist(subset[gross_col]),
                    "primary_net_proxy": _dist(subset[net_col]),
                }

            pivot_gross = common.pivot(index="date", columns="policy", values=gross_col)
            pivot_net = common.pivot(index="date", columns="policy", values=net_col)
            v2_v3_gross = pivot_gross.get("DECISION_V2", pd.Series(dtype=float)) - pivot_gross.get("DECISION_V3", pd.Series(dtype=float))
            v2_naive_gross = pivot_gross.get("DECISION_V2", pd.Series(dtype=float)) - pivot_gross.get("NAIVE_TOP10", pd.Series(dtype=float))
            v2_v3_net = pivot_net.get("DECISION_V2", pd.Series(dtype=float)) - pivot_net.get("DECISION_V3", pd.Series(dtype=float))
            v2_naive_net = pivot_net.get("DECISION_V2", pd.Series(dtype=float)) - pivot_net.get("NAIVE_TOP10", pd.Series(dtype=float))

            horizon_blocks.append({
                "block": block_id,
                "session_index_start": (block_id - 1) * BLOCK_SIZE,
                "session_index_end": block_id * BLOCK_SIZE - 1,
                "common_support_dates": len(common_dates),
                "policies": by_policy,
                "v2_minus_v3": {
                    "gross": _dist(v2_v3_gross),
                    "primary_net_proxy": _dist(v2_v3_net),
                },
                "v2_minus_naive": {
                    "gross": _dist(v2_naive_gross),
                    "primary_net_proxy": _dist(v2_naive_net),
                },
            })

        def _count_positive(path: tuple[str, str]) -> int:
            group, metric = path
            return sum(
                1 for item in horizon_blocks
                if item[group][metric]["mean"] is not None
                and float(item[group][metric]["mean"]) > 0.0
            )

        result["horizons"][f"H{horizon}"] = {
            "blocks": horizon_blocks,
            "robustness_counts": {
                "v2_beats_v3_gross_mean_blocks": _count_positive(("v2_minus_v3", "gross")),
                "v2_beats_v3_primary_mean_blocks": _count_positive(("v2_minus_v3", "primary_net_proxy")),
                "v2_beats_naive_gross_mean_blocks": _count_positive(("v2_minus_naive", "gross")),
                "v2_beats_naive_primary_mean_blocks": _count_positive(("v2_minus_naive", "primary_net_proxy")),
            },
            "block_common_support_counts": [item["common_support_dates"] for item in horizon_blocks],
        }
    return result


def run_six_block_robustness(comparison_root: str | Path) -> dict[str, Any]:
    return summarize_six_blocks(load_comparison(comparison_root))
