from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_v4_x1_decision_v1_trajectory_audit.py"
spec = importlib.util.spec_from_file_location("decision_trajectory_audit", RUNNER)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _scores(days: int = 20) -> pd.DataFrame:
    rows = []
    tickers = [f"T{i:02d}" for i in range(1, 26)]
    dates = pd.bdate_range("2024-01-02", periods=days)
    for day in dates:
        for rank, ticker in enumerate(tickers, start=1):
            alpha = 1.0 - (rank - 1) / 100.0
            rows.append({
                "ticker": ticker,
                "date": day,
                "alpha_h5": alpha,
                "alpha_h10": alpha,
                "alpha_consensus": alpha,
                "rank_consensus": rank,
            })
    return pd.DataFrame(rows)


def test_stable_ranking_bootstraps_then_never_churns(tmp_path: Path) -> None:
    scores = _scores(20)
    daily, spells, sell_reasons, buy_reasons = mod.run_trajectory(
        scores,
        tmp_path / "source_manifest.json",
        tmp_path / "scores.parquet",
        "m" * 64,
        "s" * 64,
    )
    summary = mod.summarize(daily, spells, sell_reasons, buy_reasons)
    assert daily.iloc[0]["decision_buys"] == 10
    assert daily.iloc[1:]["decision_buys"].sum() == 0
    assert daily.iloc[1:]["decision_sells"].sum() == 0
    assert summary["turnover"]["decision_total_replacements_ex_bootstrap"] == 0
    assert summary["turnover"]["decision_zero_change_sessions"] == 19
    assert summary["portfolio_rank_quality"]["top10_overlap"]["median"] == 10.0
    assert len(spells) == 10
    assert spells["right_censored"].all()
    assert set(buy_reasons) == {"FILL_VACANCY_TOP10"}
    assert not sell_reasons


def test_gap_five_replacement_is_counted(tmp_path: Path) -> None:
    scores = _scores(3)
    day2 = scores["date"].drop_duplicates().iloc[1]
    # Force T10 from rank 10 -> 15 and T11 from rank 11 -> 10 on day 2.
    mask2 = scores["date"].eq(day2)
    block = scores.loc[mask2].copy()
    mapping = {ticker: rank for ticker, rank in zip(block["ticker"], block["rank_consensus"], strict=True)}
    mapping["T10"] = 15
    mapping["T11"] = 10
    # Shift T12..T15 upward to keep ranks contiguous.
    mapping["T12"] = 11
    mapping["T13"] = 12
    mapping["T14"] = 13
    mapping["T15"] = 14
    for ticker, rank in mapping.items():
        idx = mask2 & scores["ticker"].eq(ticker)
        alpha = 1.0 - (rank - 1) / 100.0
        scores.loc[idx, ["rank_consensus", "alpha_h5", "alpha_h10", "alpha_consensus"]] = [rank, alpha, alpha, alpha]

    daily, spells, sell_reasons, buy_reasons = mod.run_trajectory(
        scores,
        tmp_path / "source_manifest.json",
        tmp_path / "scores.parquet",
        "m" * 64,
        "s" * 64,
    )
    assert int(daily.iloc[1]["decision_buys"]) == 1
    assert int(daily.iloc[1]["decision_sells"]) == 1
    assert sell_reasons["RANK_GAP_REPLACEMENT"] == 1
    assert buy_reasons["RANK_GAP_REPLACEMENT"] == 1
    exited = spells.loc[~spells["right_censored"]]
    assert len(exited) >= 1
