from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_v4_3_ca_training_domain_residual_attribution as v1  # noqa: E402
from run_v4_3_ca_training_domain_residual_attribution_v2 import (  # noqa: E402
    prepare_inputs_compact,
    schedule_event_impact_from_audit,
)


def test_prepare_inputs_compact_accepts_parent_without_blocking_ids() -> None:
    combined = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": ["2024-01-02"],
            "session_index": [1],
            "entry_open_support": [True],
            "h5_close_support": [True],
            "h10_close_support": [True],
            "h5_full_target_support": [False],
            "h10_full_target_support": [False],
            "consensus_full_target_support": [False],
        }
    )
    continuity = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "signal_date": ["2024-01-02", "2024-01-02"],
            "horizon": [5, 10],
            "continuity_status": [v1.UNRESOLVED_EVENT, v1.UNRESOLVED_EVENT],
            "continuity_reason": [v1.REASON_SCHEDULE, v1.REASON_SCHEDULE],
        }
    )
    if not hasattr(v1, "_prepare_inputs_original"):
        v1._prepare_inputs_original = v1.prepare_inputs
    c, w = prepare_inputs_compact(combined, continuity)
    assert len(c) == 1
    assert len(w) == 2
    assert "blocking_event_ids" in w.columns
    assert w["blocking_event_ids"].eq("").all()


def test_schedule_impact_reconstructs_event_ids_from_audit() -> None:
    continuity = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB"],
            "signal_date": pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-02"]),
            "horizon": [5, 10, 5],
            "continuity_status": [
                v1.UNRESOLVED_EVENT,
                v1.UNRESOLVED_EVENT,
                v1.RESOLVED,
            ],
            "continuity_reason": [
                v1.REASON_SCHEDULE,
                v1.REASON_SCHEDULE,
                "NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL",
            ],
        }
    )
    audit = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3"],
            "ticker": ["AAA", "AAA", "BBB"],
            "source_type": ["Stock Split", "Merger", "Stock Split"],
            "family": ["STOCK_SPLIT", "MERGER", "STOCK_SPLIT"],
            "semantic_class": ["SCHEDULE_REQUIRED", "SCHEDULE_REQUIRED", "EXACT_TRANSITION"],
            "reason": ["needs schedule", "needs schedule", "exact"],
        }
    )
    folds = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"])})
    result = schedule_event_impact_from_audit(continuity, audit, folds)
    assert set(result["event_id"]) == {"e1", "e2"}
    assert result["affected_windows"].eq(2).all()
    assert result["affected_frozen_windows"].eq(2).all()
    assert result["affected_signal_dates"].eq(1).all()


def test_schedule_impact_fails_if_reason_has_no_event_audit_identity() -> None:
    continuity = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "signal_date": pd.to_datetime(["2024-01-02"]),
            "horizon": [5],
            "continuity_status": [v1.UNRESOLVED_EVENT],
            "continuity_reason": [v1.REASON_SCHEDULE],
        }
    )
    audit = pd.DataFrame(
        {
            "event_id": ["e1"],
            "ticker": ["BBB"],
            "semantic_class": ["SCHEDULE_REQUIRED"],
        }
    )
    folds = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"])})
    try:
        schedule_event_impact_from_audit(continuity, audit, folds)
    except RuntimeError as exc:
        assert "SCHEDULE_WINDOW_WITHOUT_SCHEDULE_EVENT_AUDIT:AAA" in str(exc)
    else:
        raise AssertionError("expected fail-closed missing schedule identity")


def test_v2_wrapper_does_not_relax_scientific_scenarios() -> None:
    source = (
        ROOT / "scripts" / "run_v4_3_ca_training_domain_residual_attribution_v2.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "requests.get",
        "curl_cffi",
        "materialize_v4_target_ledger",
        "fit_v4_head",
        "score_v4_head",
        "GATE_RATE =",
    )
    for token in forbidden:
        assert token not in source
