from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "research" / "alpha_eligibility_policy_scenario_v1.py"
SPEC = importlib.util.spec_from_file_location("alpha_eligibility_policy_scenario_v1", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_policy_fingerprint_differs_without_selecting_policy() -> None:
    assert MODULE.policy_sha(20) != MODULE.policy_sha(60)
    assert MODULE.WINDOW == 60


def test_top_k_summary_is_structural_and_rank_based() -> None:
    import pandas as pd

    rows = []
    for date in pd.date_range("2026-01-01", periods=31, freq="D"):
        for index in range(30):
            rows.append({"ticker": f"T{index:02d}", "date": date, "eligible_decision_universe": True, "rank_C1": 1.0 - index / 30.0})
    frame = pd.DataFrame(rows)
    dates = pd.Index(pd.date_range("2026-01-01", periods=31, freq="D"), name="date")
    summary = MODULE.top_k_summary(frame, "C1", dates, frozen_only=True)
    assert summary["selection_dates"] == 31
    assert summary["selection_slots"] == 31 * 30
    assert summary["mean_top_k_overlap"] == 1.0
    assert summary["mean_top_k_turnover"] == 0.0
