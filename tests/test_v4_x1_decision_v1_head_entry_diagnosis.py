from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "run_v4_x1_decision_v1_head_entry_diagnosis.py"
spec = importlib.util.spec_from_file_location("head_entry_diag", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _block(date: str, rows: list[tuple[str, float, float]], fold: int = 1) -> pd.DataFrame:
    out = []
    for ticker, a5, a10 in rows:
        out.append({
            "ticker": ticker,
            "date": pd.Timestamp(date),
            "fold": fold,
            "mode": "CHALLENGER",
            "raw_h5": a5,
            "raw_h10": a10,
            "alpha_h5": a5,
            "alpha_h10": a10,
            "alpha_consensus": 0.5 * (a5 + a10),
        })
    frame = pd.DataFrame(out)
    parts = []
    for alpha, rank in (("alpha_h5", "rank_h5"), ("alpha_h10", "rank_h10"), ("alpha_consensus", "rank_consensus")):
        order = frame.sort_values([alpha, "ticker"], ascending=[False, True], kind="mergesort").index
        frame.loc[order, rank] = range(1, len(frame) + 1)
        frame[rank] = frame[rank].astype(int)
    return frame


def _base_rows(n: int = 25) -> list[tuple[str, float, float]]:
    return [(f"T{i:02d}", 1.0 - i / 100.0, 1.0 - i / 100.0) for i in range(1, n + 1)]


def test_detects_immediate_hard_exit_and_head_state(tmp_path: Path) -> None:
    d1 = _base_rows()
    d2 = _base_rows()
    # Crash T01 in both heads so consensus rank moves well beyond 20.
    d2 = [(t, 0.01, 0.01) if t == "T01" else (t, a5, a10) for t, a5, a10 in d2]
    frame = pd.concat([
        _block("2024-01-02", d1),
        _block("2024-01-03", d2),
    ], ignore_index=True)

    entries, hard = mod.diagnose(frame, tmp_path / "m.json", tmp_path / "s.parquet")
    summary = mod.summarize(entries, hard)

    assert len(hard) == 1
    assert hard.iloc[0]["ticker"] == "T01"
    assert int(hard.iloc[0]["holding_age"]) == 1
    assert bool(hard.iloc[0]["both_heads_gt20"])
    assert summary["entries"]["immediate_hard_exit_count"] == 1


def test_entry_support_class_detects_head_disagreement(tmp_path: Path) -> None:
    rows = _base_rows()
    # Make T10 excellent on H5 but weak on H10 while consensus remains buy-eligible.
    rows = [(t, 1.20, 0.40) if t == "T10" else (t, a5, a10) for t, a5, a10 in rows]
    frame = _block("2024-01-02", rows)
    entries, hard = mod.diagnose(frame, tmp_path / "m.json", tmp_path / "s.parquet")
    t10 = entries.loc[entries["ticker"].eq("T10")]
    assert len(t10) == 1
    assert int(t10.iloc[0]["rank_h5"]) <= 10
    assert int(t10.iloc[0]["rank_h10"]) > 10
    assert str(t10.iloc[0]["support10"]) == "H5_ONLY_LE10"
    assert hard.empty
