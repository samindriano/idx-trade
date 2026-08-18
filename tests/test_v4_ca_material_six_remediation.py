from __future__ import annotations

import pandas as pd

from idx_trade.v4_ca_event_windows import classify_event
from idx_trade.v4_ca_material_six_remediation import (
    EXPECTED_AFTER_AVIA_SMAR_UNRESOLVED,
    EXPECTED_PARENT_UNRESOLVED,
    FREN_EFFECTIVE_DATE,
    MEGA_REGULAR_EX_BONUS_DATE,
    new_fren_coverage_row,
    normalize_source_action_id,
    synthetic_fren_event,
    synthetic_mega_event,
    validate_scma_halo_only,
)


def test_aviasmar_only_reduce_expected_parent_unresolved_set() -> None:
    assert EXPECTED_AFTER_AVIA_SMAR_UNRESOLVED == EXPECTED_PARENT_UNRESOLVED - {"AVIA", "SMAR"}
    assert len(EXPECTED_AFTER_AVIA_SMAR_UNRESOLVED) == 9


def test_fren_unavailable_history_is_explicit_unresolved_611_row() -> None:
    columns = [
        "ticker", "coverage_status", "coverage_certified", "attempt_count",
        "final_http_status", "source_url", "source_sha256", "ca_rows",
        "active_ca_rows", "active_mechanical_rows", "active_unknown_rows",
        "earliest_ca_date", "latest_ca_date", "failure_reason",
    ]
    row = new_fren_coverage_row(
        columns,
        success_record=None,
        security_attempt_count=2,
        stats=None,
        failure_reason="HTTP_NON_200_OR_EMPTY",
    )
    assert row["ticker"] == "FREN"
    assert row["coverage_certified"] is False
    assert row["coverage_status"] == "COVERAGE_UNRESOLVED"
    assert row["failure_reason"] == "HTTP_NON_200_OR_EMPTY"


def test_fren_synthetic_event_is_exact_cessation_without_excl_stitching() -> None:
    event = synthetic_fren_event("abc123")
    assert event.ticker == "FREN"
    assert event.semantic_class == "EXACT_TRANSITION"
    assert event.transition_date == FREN_EFFECTIVE_DATE
    assert "NO_EXCL_PRICE_STITCHING" in event.reason


def test_mega_synthetic_event_uses_exact_regular_ex_bonus_date() -> None:
    event = synthetic_mega_event("abc123")
    assert event.ticker == "MEGA"
    assert event.semantic_class == "EXACT_TRANSITION"
    assert event.transition_date == MEGA_REGULAR_EX_BONUS_DATE
    assert event.transition_date == pd.Timestamp("2026-04-10")


def test_scma_20260810_is_halo_only_after_frozen_terminal() -> None:
    prior = pd.DataFrame(
        {
            "ticker": ["SCMA"],
            "candidate_date": ["2026-08-10"],
            "source_action_id": ["82840"],
        }
    )
    result = validate_scma_halo_only(prior, max_terminal=pd.Timestamp("2026-07-31"))
    assert result["classification"] == "OUTSIDE_FROZEN_TARGET_PERIOD_NONBLOCKING_HALO_ONLY"


def test_scma_numeric_csv_action_id_normalizes_losslessly() -> None:
    assert normalize_source_action_id(82840.0) == "82840"
    assert normalize_source_action_id("82840.0") == "82840"
    assert normalize_source_action_id("IDX-82840") == "IDX-82840"
    prior = pd.DataFrame(
        {
            "ticker": ["SCMA"],
            "candidate_date": ["2026-08-10"],
            "source_action_id": [82840.0],
        }
    )
    result = validate_scma_halo_only(prior, max_terminal=pd.Timestamp("2026-07-31"))
    assert result["source_action_id"] == "82840"


def test_scma_cannot_be_halo_cleared_if_any_candidate_is_in_period() -> None:
    prior = pd.DataFrame(
        {
            "ticker": ["SCMA", "SCMA"],
            "candidate_date": ["2026-08-10", "2026-07-01"],
            "source_action_id": ["82840", "X"],
        }
    )
    try:
        validate_scma_halo_only(prior, max_terminal=pd.Timestamp("2026-07-31"))
    except RuntimeError as exc:
        assert "SCMA_HAS_IN_PERIOD_PRIOR_CANDIDATE" in str(exc)
    else:
        raise AssertionError("SCMA in-period candidate must fail closed")


def test_adro_blank_cum_right_distribution_never_infers_record_or_distribution_as_ex_date() -> None:
    row = {
        "ticker": "ADRO",
        "row_index": 1,
        "event_family_source": "Right Distribution",
        "cum_date": "",
        "record_date": "2024-11-29",
        "distribution_date": "2024-12-02",
        "status": "Active",
        "ratio_raw": "(4389 ADRO : 1000 ADRO-H )",
        "source_sha256": "abc123",
    }
    sessions = pd.date_range("2024-11-20", "2024-12-05", freq="B")
    event = classify_event(row, official_sessions=sessions)
    assert event.semantic_class == "SCHEDULE_REQUIRED"
    assert event.transition_date is None
    assert event.reason == "SOURCE_NATIVE_CUM_MISSING_OR_NOT_OFFICIAL_SESSION"
