from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "run_v4_x1_decision_v1_rank_dynamics_diagnosis.py"
spec = importlib.util.spec_from_file_location("rank_diag", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _block(date: str, order: list[str], fold: int = 1) -> pd.DataFrame:
    rows = []
    n = len(order)
    for rank, ticker in enumerate(order, start=1):
        alpha = 1.0 - (rank - 1) / max(n - 1, 1)
        rows.append({
            "ticker": ticker,
            "date": pd.Timestamp(date),
            "fold": fold,
            "mode": "CHALLENGER",
            "raw_h5": alpha * 2.0 - 0.4,
            "raw_h10": alpha * 1.5 + 0.2,
            "alpha_h5": alpha,
            "alpha_h10": alpha,
            "alpha_consensus": alpha,
            "rank_consensus": rank,
        })
    return pd.DataFrame(rows)


def test_hard_exit_whipsaw_is_detected(tmp_path: Path) -> None:
    names = [f"T{i:02d}" for i in range(1, 26)]
    d1 = names.copy()
    # T01 goes from rank 1 to rank 21; T11 is promoted into rank 1.
    d2 = ["T11"] + [x for x in names if x not in {"T11", "T01"}][:19] + ["T01"] + [x for x in names if x not in {"T11", "T01"}][19:]
    # Return to original ranking next session.
    d3 = names.copy()
    frame = pd.concat([
        _block("2024-01-02", d1),
        _block("2024-01-03", d2),
        _block("2024-01-04", d3),
    ], ignore_index=True)

    trans, top10, hard = mod.diagnose(frame, tmp_path / "m.json", tmp_path / "s.parquet")
    summary = mod.summarize(trans, top10, hard)

    first = top10[(top10["date_0"] == "2024-01-02") & (top10["ticker"] == "T01")].iloc[0]
    assert first["state_1"] == "GT20"
    assert int(first["rank_1"]) == 21
    assert len(hard) == 1
    assert hard.iloc[0]["ticker"] == "T01"
    assert int(hard.iloc[0]["previous_rank"]) == 1
    assert int(hard.iloc[0]["current_rank"]) == 21
    assert int(hard.iloc[0]["rank_next_session"]) == 1
    assert summary["hard_exit_whipsaw"]["next_session_back_top10_rate"] == 1.0


def test_fold_boundary_is_separated_from_within_fold(tmp_path: Path) -> None:
    names = [f"T{i:02d}" for i in range(1, 26)]
    frame = pd.concat([
        _block("2024-01-02", names, fold=1),
        _block("2024-01-03", names, fold=1),
        _block("2024-01-04", names, fold=2),
    ], ignore_index=True)
    trans, top10, hard = mod.diagnose(frame, tmp_path / "m.json", tmp_path / "s.parquet")
    summary = mod.summarize(trans, top10, hard)
    assert len(trans) == 2
    assert int(trans["fold_boundary"].sum()) == 1
    assert summary["fold_boundary_forensics"]["boundary_transitions"] == 1
    assert summary["fold_boundary_forensics"]["within_fold_transitions"] == 1
    assert hard.empty
