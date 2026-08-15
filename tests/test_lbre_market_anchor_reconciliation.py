from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_lbre_market_anchor_reconciliation.py"
SPEC = importlib.util.spec_from_file_location("run_lbre_market_anchor_reconciliation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _row(shares: int, pct: float) -> dict[str, object]:
    return {"free_float_shares": shares, "free_float_pct": pct}


def test_classification_keeps_share_and_percentage_axes_separate() -> None:
    assert MODULE.classify_overlap(_row(100, 10.0), _row(100, 10.0)) == "EXACT_AGREE"
    assert MODULE.classify_overlap(_row(100, 10.2), _row(100, 10.0)) == "SHARES_AGREE_PCT_DIFF"
    assert MODULE.classify_overlap(_row(101, 10.0), _row(100, 10.0)) == "SHARES_DIFF_PCT_AGREE"
    assert MODULE.classify_overlap(_row(101, 10.2), _row(100, 10.0)) == "SHARES_AND_PCT_DIFF"


def test_diagnostic_does_not_replace_reported_percentage() -> None:
    lbre = {
        **_row(250, 24.0),
        "total_listed_shares": 1000,
        "published_at": "2026-01-01T10:00:00+07:00",
        "announcement_no": "LBRE-1",
        "source_url": "https://www.idx.co.id/StaticData/fixture.pdf",
        "source_sha256": "a" * 64,
    }
    market = {
        **_row(200, 25.0),
        "source_url": "https://www.idx.co.id/StaticData/fixture-market.pdf",
        "source_sha256": "b" * 64,
    }
    result = MODULE.diagnostic_row("TEST", lbre, market)
    assert result["classification"] == "SHARES_AND_PCT_DIFF"
    assert result["lbre_free_float_pct"] == 24.0
    assert result["lbre_implied_pct"] == 25.0
    assert result["lbre_reported_minus_implied_pp"] == -1.0


def test_expected_class_inventory_includes_zero_count_classes() -> None:
    expected = set(MODULE.CLASSIFICATIONS)
    observed = {"EXACT_AGREE": 2, "MARKET_ONLY": 1}
    counts = {name: observed.get(name, 0) for name in expected}
    assert set(counts) == expected
    assert counts["LBRE_ONLY"] == 0
    assert counts["SHARES_DIFF_PCT_AGREE"] == 0
