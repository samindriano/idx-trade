from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_v4_x1_decision_v1_temporal_persistence_diagnosis.py"
spec = importlib.util.spec_from_file_location("temporal_diag", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_run_length_resets() -> None:
    got = mod._run_length(pd.Series([True, True, False, True, True, True])).tolist()
    assert got == [1, 2, 0, 1, 2, 3]


def test_summary_distinguishes_persistent_from_fresh() -> None:
    rows = []
    dates = pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"])
    for d_i, d in enumerate(dates):
        for rank in range(1, 26):
            ticker = f"T{rank:02d}"
            consensus_rank = rank
            if ticker == "T05":
                consensus_rank = [5, 7, 8, 23][d_i]
            rows.append(
                {
                    "ticker": ticker,
                    "date": d,
                    "rank_consensus": consensus_rank,
                    "rank_h5": consensus_rank,
                    "rank_h10": consensus_rank,
                }
            )
    frame = pd.DataFrame(rows)
    panel = mod.build_panel(frame)
    t05 = panel.loc[panel["ticker"].eq("T05")].sort_values("date")
    assert t05["top10_run"].tolist() == [1, 2, 3, 0]
    assert bool(t05.iloc[2]["prev_consensus_le10"])
    assert int(t05.iloc[2]["next1_rank_consensus"]) == 23

    summary = mod.summarize(panel)
    assert summary["reference_counts"]["dates"] == 4
    assert summary["top10_candidate_strata"]["TOP10_RUN_GE3"]["n"] >= 1
    assert summary["top10_candidate_strata"]["TOP10_RUN_GE3"]["next1_gt20_rate"] is not None
