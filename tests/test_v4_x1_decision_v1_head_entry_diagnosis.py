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
    for alpha, rank in (("alpha_h5", "rank_h5"), ("alpha_h10", "rank_h10"), ("alpha_consensus", "rank_consensus")):
        order = frame.sort_values([alpha, "ticker"], ascending=[False, True], kind="mergesort").index
        frame.loc[order, rank] = range(1, len(frame) + 1)
        frame[rank] = frame[rank].astype(int)
    return frame


def _base_rows(n: int = 25) -> list[tuple[str, float, float]]:
    return [(f"T{i:02d}", 1.0 - i / 100.0, 1.0 - i / 100.0) for i in range(1, n + 1)]


def test_detects_nonbootstrap_immediate_hard_exit_and_head_state(tmp_path: Path) -> None:
    d1 = _base_rows()
    # Day 2: remove T10 from Top-10 so T11 becomes a genuine non-bootstrap buy.
    d2 = [(t, 0.01, 0.01) if t == "T10" else (t, a5, a10) for t, a5, a10 in _base_rows()]
    # Day 3: restore T10 and crash newly bought T11 in both heads.
    d3 = [(t, 0.01, 0.01) if t == "T11" else (t, a5, a10) for t, a5, a10 in _base_rows()]
    frame = pd.concat([
        _block("2024-01-02", d1),
        _block("2024-01-03", d2),
        _block("2024-01-04", d3),
    ], ignore_index=True)

    entries, hard = mod.diagnose(frame, tmp_path / "m.json", tmp_path / "s.parquet")
    summary = mod.summarize(entries, hard)

    t11_hard = hard.loc[hard["ticker"].eq("T11")]
    assert len(t11_hard) == 1
    assert int(t11_hard.iloc[0]["holding_age"]) == 1
    assert bool(t11_hard.iloc[0]["both_heads_gt20"])
    assert summary["entries"]["immediate_hard_exit_count"] >= 1


def test_entry_support_class_detects_head_disagreement(tmp_path: Path) -> None:
    rows = _base_rows()
    # T11 is made H5-dominant but H10 stays outside Top-10; consensus is still strong enough to enter Top-10.
    rows = [(t, 1.30, 0.89) if t == "T11" else (t, a5, a10) for t, a5, a10 in rows]
    frame = _block("2024-01-02", rows)
    entries, hard = mod.diagnose(frame, tmp_path / "m.json", tmp_path / "s.parquet")
    t11 = entries.loc[entries["ticker"].eq("T11")]
    assert len(t11) == 1
    assert int(t11.iloc[0]["rank_h5"]) <= 10
    assert int(t11.iloc[0]["rank_h10"]) > 10
    assert str(t11.iloc[0]["support10"]) == "H5_ONLY_LE10"
    assert hard.empty
