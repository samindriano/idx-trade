from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_v4_3_ca_training_domain_residual_attribution.py"
spec = importlib.util.spec_from_file_location("v4_3_ca_residual_attribution", SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _continuity() -> pd.DataFrame:
    day = pd.Timestamp("2024-01-02")
    rows = []
    reasons = {
        "AAA": (mod.RESOLVED, "NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL"),
        "BBB": (mod.UNRESOLVED_COVERAGE, mod.REASON_COVERAGE),
        "CCC": (mod.UNRESOLVED_EVENT, mod.REASON_SCHEDULE),
        "DDD": (mod.UNRESOLVED_EVENT, mod.REASON_CROSSING),
    }
    for ticker, (status, reason) in reasons.items():
        for horizon in (5, 10):
            rows.append(
                {
                    "ticker": ticker,
                    "signal_date": day,
                    "horizon": horizon,
                    "continuity_status": status,
                    "continuity_reason": reason,
                    "blocking_event_ids": "evt" if ticker in {"CCC", "DDD"} else "",
                }
            )
    return pd.DataFrame(rows)


def _combined() -> pd.DataFrame:
    day = pd.Timestamp("2024-01-02")
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "DDD"],
            "date": day,
            "session_index": 100,
            "entry_open_support": True,
            "h5_close_support": True,
            "h10_close_support": True,
            "h5_full_target_support": [True, False, False, False],
            "h10_full_target_support": [True, False, False, False],
            "consensus_full_target_support": [True, False, False, False],
        }
    )


def test_counterfactuals_never_waive_exact_crossing_in_admissible_ceilings() -> None:
    continuity = _continuity()
    combined = _combined()

    baseline = mod.build_scenario_rows(combined, continuity, "BASELINE")
    coverage = mod.build_scenario_rows(
        combined, continuity, "COVERAGE_ONLY_CEILING"
    )
    schedule = mod.build_scenario_rows(
        combined, continuity, "SCHEDULE_ONLY_CEILING"
    )
    both = mod.build_scenario_rows(
        combined, continuity, "COVERAGE_PLUS_SCHEDULE_CEILING"
    )
    price_only = mod.build_scenario_rows(
        combined, continuity, "PRICE_OBSERVABILITY_ONLY_UPPER_BOUND"
    )

    assert int(baseline["scenario_consensus_support"].sum()) == 1
    assert int(coverage["scenario_consensus_support"].sum()) == 2
    assert int(schedule["scenario_consensus_support"].sum()) == 2
    assert int(both["scenario_consensus_support"].sum()) == 3
    assert not bool(
        both.loc[both["ticker"].eq("DDD"), "scenario_consensus_support"].iloc[0]
    )
    assert int(price_only["scenario_consensus_support"].sum()) == 4


def test_aggregate_gate_is_exactly_point_nine() -> None:
    day = pd.Timestamp("2024-01-02")
    rows = pd.DataFrame(
        {
            "ticker": [f"T{i:02d}" for i in range(10)],
            "date": day,
            "session_index": 100,
            "scenario_h5_support": [True] * 9 + [False],
            "scenario_h10_support": [True] * 9 + [False],
            "scenario_consensus_support": [True] * 9 + [False],
        }
    )
    result = mod.aggregate_per_date(rows, 0.90).iloc[0]
    assert result["h5_rate"] == 0.9
    assert result["h10_rate"] == 0.9
    assert result["consensus_rate"] == 0.9
    assert bool(result["h5_eligible"])
    assert bool(result["h10_eligible"])
    assert bool(result["consensus_eligible"])


def _scenario(all_pass: bool) -> dict[str, object]:
    return {
        "frozen_600": {
            "all_600_h5": all_pass,
            "all_600_h10": all_pass,
            "all_600_consensus": all_pass,
        }
    }


def test_verdict_prefers_full_coverage_remediation_not_subset_selection() -> None:
    summaries = {
        "BASELINE": _scenario(False),
        "COVERAGE_ONLY_CEILING": _scenario(True),
        "SCHEDULE_ONLY_CEILING": _scenario(False),
        "COVERAGE_PLUS_SCHEDULE_CEILING": _scenario(True),
        "PRICE_OBSERVABILITY_ONLY_UPPER_BOUND": _scenario(True),
    }
    verdict, next_action = mod.determine_verdict(summaries)
    assert verdict == "V4_3_CA_RESIDUAL_ATTRIBUTION_COVERAGE_ONLY_SUFFICIENT"
    assert next_action == "REMEDIATE_ALL_45_UNRESOLVED_COVERAGE_TICKERS_THEN_REPLAY"


def test_runner_source_has_no_provider_retry_or_model_execution() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    forbidden = (
        "requests.get",
        "curl_cffi",
        "recover_ticker(",
        "materialize_v4_target_ledger",
        "fit_v4_head(",
        "score_v4_head(",
    )
    for token in forbidden:
        assert token not in source
    assert '"network_calls": False' in source
    assert '"provider_calls": False' in source
    assert '"pass_preserving_subset_selection": False' in source
    assert '"waive_exact_mechanical_crossings": False' in source
