from __future__ import annotations

from pathlib import Path

import pandas as pd

import idx_trade.decision_v3_structural_replay as replay_module
from idx_trade.decision_v3_structural_replay import replay_once
from idx_trade.decision_v3_structural_source import PinnedReplaySource


def _synthetic_source(tmp_path: Path) -> PinnedReplaySource:
    rows = []
    dates = pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-06"])
    names = [f"A{i:02d}" for i in range(1, 31)]
    orders = [
        names,
        names[1:10] + [names[10]] + [names[0]] + names[11:],
        names[1:9] + [names[10], names[11]] + [names[0], names[9]] + names[12:],
    ]
    for session_index, (day, order) in enumerate(zip(dates, orders)):
        for rank, ticker in enumerate(order, start=1):
            rows.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "fold": "F1",
                    "mode": "OOS",
                    "alpha_consensus": float(100 - rank),
                    "rank_consensus": rank,
                }
            )
    manifest = tmp_path / "MANIFEST.json"
    score = tmp_path / "scores.parquet"
    manifest.write_text("{}", encoding="utf-8")
    score.write_bytes(b"synthetic")
    return PinnedReplaySource(pd.DataFrame(rows), manifest, score)


def test_replay_once_synthetic_path_preserves_bootstrap_and_continuous_state(
    tmp_path: Path, monkeypatch
) -> None:
    source = _synthetic_source(tmp_path)
    monkeypatch.setattr(replay_module, "EXPECTED_SCORE_SESSIONS", 3)
    monkeypatch.setattr(replay_module, "EXPECTED_SCORE_ROWS", 90)
    trace = replay_once(source)
    assert len(trace.session_ledger) == 3
    assert trace.session_ledger.loc[0, "bootstrap"]
    assert not trace.session_ledger.loc[1, "bootstrap"]
    assert trace.correctness["bootstrap_wrong_index_count"] == 0
    assert trace.correctness["row_order_nondeterministic_count"] == 0
    assert trace.correctness["rule_id_mismatch_count"] == 0
    assert trace.plan_digest
