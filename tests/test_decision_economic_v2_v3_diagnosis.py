from pathlib import Path

import pandas as pd

from idx_trade.decision_economic_comparison import HistoricalSource, PolicyMembership
from idx_trade.decision_economic_v2_v3_diagnosis import diagnose_loaded


def test_full_target_substitution_is_separate_from_underfill_cash() -> None:
    dates = tuple(pd.bdate_range("2026-01-05", periods=3))
    tickers = list("ABCDEFGHIJKL")
    score_rows = []
    target_rows = []
    for date in dates:
        for idx, ticker in enumerate(tickers):
            score_rows.append(
                {"date": date, "ticker": ticker, "alpha_consensus": 1.0 - idx / 100.0}
            )
            ret = 0.0
            if date == dates[1] and ticker in {"I", "J"}:
                ret = 0.10
            if date == dates[1] and ticker in {"K", "L"}:
                ret = -0.05
            if date == dates[2] and ticker == "K":
                ret = -0.10
            target_rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "target_state_h5": "TARGET_H5_AVAILABLE",
                    "r5": ret,
                    "target_state_h10": "TARGET_H10_AVAILABLE",
                    "r10": ret,
                    "h5_continuity_resolved": True,
                    "h10_continuity_resolved": True,
                }
            )

    source = HistoricalSource(
        root=Path("."),
        manifest_path=Path("MANIFEST.json"),
        score_path=Path("scores.parquet"),
        target_path=Path("targets.parquet"),
        manifest_sha256="m",
        score_sha256="s",
        target_sha256="t",
        scores=pd.DataFrame(score_rows),
        targets=pd.DataFrame(target_rows),
        dates=dates,
    )
    v2 = PolicyMembership(
        "DECISION_V2",
        {
            dates[0]: tuple("ABCDEFGHIJ"),
            dates[1]: tuple("ABCDEFGHIJ"),
            dates[2]: tuple("ABCDEFGHI"),
        },
        "v2",
        "v2sha",
    )
    v3 = PolicyMembership(
        "DECISION_V3",
        {
            dates[0]: tuple("ABCDEFGHKL"),
            dates[1]: tuple("ABCDEFGHKL"),
            dates[2]: tuple("ABCDEFGHIK"),
        },
        "v3",
        "v3sha",
    )

    summary, sessions, details = diagnose_loaded(source, v2, v3)
    h5 = summary["horizons"]["H5"]
    assert h5["pairwise_complete_support_dates"] == 3
    assert h5["full_target_pure_substitution"]["dates"] == 2
    assert h5["v2_underfill_mixed"]["dates"] == 1
    assert abs(h5["full_target_pure_substitution"]["v2_minus_v3_gross"]["mean"] - 0.015) < 1e-12
    assert abs(h5["v2_underfill_mixed"]["v2_minus_v3_gross"]["mean"] - 0.01) < 1e-12
    assert h5["full_target_pure_substitution"]["v2_only_retained"]["entries"] == 2
    assert h5["full_target_pure_substitution"]["v3_only_new"]["entries"] == 2
    assert len(sessions) == 6
    assert not details.empty
