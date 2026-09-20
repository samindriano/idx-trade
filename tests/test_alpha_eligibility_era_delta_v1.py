from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "research" / "alpha_eligibility_era_delta_v1.py"
SPEC = importlib.util.spec_from_file_location("alpha_eligibility_era_delta_v1", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_summarize_reports_mask_delta_without_policy_selection() -> None:
    base = pd.DataFrame(
        [
            {"ticker": "AAA", "date": "2025-01-02", "eligible_decision_universe": True},
            {"ticker": "BBB", "date": "2025-01-02", "eligible_decision_universe": True},
            {"ticker": "AAA", "date": "2026-01-02", "eligible_decision_universe": True},
        ]
    )
    relaxed = base.copy()
    strict = base.copy()
    strict.loc[(strict["ticker"] == "BBB") & (strict["date"] == "2025-01-02"), "eligible_decision_universe"] = False
    result = MODULE.summarize(relaxed, strict)
    assert result["overall_newly_admitted_rows"] == 1
    assert result["by_year"]["2025"]["newly_admitted_tickers"] == 1


def test_summarize_rejects_misaligned_masks() -> None:
    left = pd.DataFrame([{"ticker": "AAA", "date": "2025-01-02", "eligible_decision_universe": True}])
    right = pd.DataFrame([{"ticker": "BBB", "date": "2025-01-02", "eligible_decision_universe": True}])
    with pytest.raises(ValueError, match="same ticker/date index"):
        MODULE.summarize(left, right)
