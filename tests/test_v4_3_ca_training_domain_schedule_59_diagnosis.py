from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_v4_3_ca_training_domain_schedule_59_diagnosis as diag  # noqa: E402


def test_config_freezes_outcome_blind_all_residual_diagnosis() -> None:
    config = json.loads(
        Path("config/v4_3_ca_training_domain_schedule_59_diagnosis_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert config["outcome_blind"] is True
    assert config["parent_replay"]["required_schedule_required_events"] == 59
    assert config["adjudication_parent"]["unresolved_events"] == 59
    for value in config["hard_boundaries"].values():
        assert value is False


def test_no_candidate_is_discovery_gap() -> None:
    event = pd.Series(
        {
            "event_id": "e1",
            "ticker": "AAA",
            "source_type": "Stock Split",
            "family": "STOCK_SPLIT",
            "source_dates": "2024-01-10",
        }
    )
    evidence = pd.Series(
        {
            "frozen_candidate_document_count": "0",
            "parsed_candidate_document_count": "0",
        }
    )
    result = diag.diagnose_event(event, evidence, pd.DataFrame(), {"2024-01-11"})
    assert result["failure_mode"] == "NO_FROZEN_CANDIDATE_DOCUMENT"
    assert result["remediation_class"] == "SECONDARY_OFFICIAL_DOCUMENT_DISCOVERY"


def test_mechanical_candidate_without_explicit_transition_is_not_inferred() -> None:
    event = pd.Series(
        {
            "event_id": "e2",
            "ticker": "BBB",
            "source_type": "Stock Split",
            "family": "STOCK_SPLIT",
            "source_dates": "2024-01-10",
        }
    )
    evidence = pd.Series(
        {
            "frozen_candidate_document_count": "1",
            "parsed_candidate_document_count": "1",
        }
    )
    audit = pd.DataFrame(
        [
            {
                "event_id": "e2",
                "ticker": "BBB",
                "raw_available": "True",
                "diagnostics": "NO_LAYOUT_EXPLICIT_TRANSITION",
                "document_class": "NONE",
                "event_family": "STOCK_SPLIT",
                "payment_dates": "",
                "settlement_dates": "",
                "cash_purchase_dates": "",
                "record_date": "2024-01-10",
                "distribution_date": "2024-01-15",
                "transition_date": "",
                "transition_semantic": "",
            }
        ]
    )
    result = diag.diagnose_event(event, evidence, audit, {"2024-01-11"})
    assert result["failure_mode"] == "MECHANICAL_NO_EXPLICIT_REGULAR_MARKET_TRANSITION"
    assert "2024-01-15" not in result.get("qualifying_rows_after_diagnosis", "") if isinstance(result.get("qualifying_rows_after_diagnosis"), str) else True


def test_voluntary_cash_source_date_must_match_layout_bound_cash_date() -> None:
    event = pd.Series(
        {
            "event_id": "e3",
            "ticker": "CCC",
            "source_type": "Voluntary Conversion",
            "family": "VOLUNTARY_CONVERSION",
            "source_dates": "2024-02-01",
        }
    )
    evidence = pd.Series(
        {
            "frozen_candidate_document_count": "1",
            "parsed_candidate_document_count": "1",
        }
    )
    audit = pd.DataFrame(
        [
            {
                "event_id": "e3",
                "ticker": "CCC",
                "raw_available": "True",
                "diagnostics": "",
                "document_class": "VOLUNTARY_TENDER_OFFER",
                "event_family": "UNKNOWN",
                "payment_dates": "2024-02-05",
                "settlement_dates": "",
                "cash_purchase_dates": "",
                "record_date": "",
                "distribution_date": "",
                "transition_date": "",
                "transition_semantic": "",
            }
        ]
    )
    result = diag.diagnose_event(event, evidence, audit, set())
    assert result["failure_mode"] == "VOLUNTARY_CASH_DATE_NOT_LINKED_TO_SOURCE_DATE"


def test_runner_has_no_provider_target_model_or_threshold_relaxation_path() -> None:
    source = Path(
        "scripts/run_v4_3_ca_training_domain_schedule_59_diagnosis.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "curl_cffi",
        "requests.get",
        "urllib.request",
        "materialize_v4_target_ledger",
        "HistGradientBoostingRegressor",
        "fit_v4_head",
        "score_v4_head",
        "GATE_RATE =",
    )
    for token in forbidden:
        assert token not in source
