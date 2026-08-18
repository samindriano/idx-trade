from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pandas as pd
import pytest


SCRIPT = Path("scripts/run_v4_3_ca_training_domain_schedule_80_ksei_acquisition.py")
spec = importlib.util.spec_from_file_location("schedule80_ksei", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _identity(frame: pd.DataFrame) -> str:
    return module.event_inventory_identity(frame[["event_id", "ticker"]])


def test_frozen_config_is_outcome_blind_and_all_80() -> None:
    config = json.loads(
        Path("config/v4_3_ca_training_domain_schedule_80_ksei_v1.json").read_text(
            encoding="utf-8"
        )
    )
    module.verify_config(config)
    assert config["reuse_parent"]["event_count"] == 80
    assert config["acquisition_scope"]["all_80_events"] is True
    assert config["acquisition_scope"]["parse_diagnostics_are_non_admissive"] is True
    assert config["hard_boundaries"]["pass_preserving_subset_selection"] is False


def test_scope_requires_exact_event_metadata_and_source_dates() -> None:
    residual = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "ticker": ["AAA", "BBB"],
            "source_type": ["Stock Split", "Right Distribution"],
            "family": ["STOCK_SPLIT", "RIGHTS_HMETD"],
        }
    )
    audit = pd.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "ticker": ["AAA", "BBB"],
            "source_type": ["Stock Split", "Right Distribution"],
            "family": ["STOCK_SPLIT", "RIGHTS_HMETD"],
            "semantic_class": ["SCHEDULE_REQUIRED", "SCHEDULE_REQUIRED"],
            "source_dates": ["2024-01-15|2024-01-17", "2024-03-01"],
        }
    )
    config = {
        "reuse_parent": {
            "event_count": 2,
            "event_identity_sha256": _identity(residual),
        }
    }
    scope = module.build_scope(residual, audit, config)
    assert len(scope) == 2
    assert [stamp.date().isoformat() for stamp in scope[0].source_dates] == [
        "2024-01-15",
        "2024-01-17",
    ]


def test_scope_fails_closed_when_source_dates_missing() -> None:
    residual = pd.DataFrame(
        {
            "event_id": ["e1"],
            "ticker": ["AAA"],
            "source_type": ["Stock Split"],
            "family": ["STOCK_SPLIT"],
        }
    )
    audit = pd.DataFrame(
        {
            "event_id": ["e1"],
            "ticker": ["AAA"],
            "source_type": ["Stock Split"],
            "family": ["STOCK_SPLIT"],
            "semantic_class": ["SCHEDULE_REQUIRED"],
            "source_dates": [""],
        }
    )
    config = {
        "reuse_parent": {
            "event_count": 1,
            "event_identity_sha256": _identity(residual),
        }
    }
    with pytest.raises(RuntimeError, match="SCHEDULE_EVENT_SOURCE_DATES_MISSING"):
        module.build_scope(residual, audit, config)


def test_query_months_are_only_fixed_halo_around_source_dates() -> None:
    event = module.ScopedEvent(
        event_id="e1",
        ticker="AAA",
        source_type="Stock Split",
        family="STOCK_SPLIT",
        semantic_class="SCHEDULE_REQUIRED",
        source_dates=(pd.Timestamp("2024-01-15"),),
    )
    assert module.event_months(event) == [
        (2023, 11),
        (2023, 12),
        (2024, 1),
        (2024, 2),
        (2024, 3),
    ]


def test_live_runner_does_not_admit_semantics_or_import_target_model() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    forbidden = (
        "exact_source_date_link(",
        "compatible_family(",
        "materialize_v4_target_ledger",
        "HistGradientBoostingRegressor",
        "fit_v4_head",
        "score_v4_head",
    )
    for token in forbidden:
        assert token not in source
    assert '"semantic_admission_performed": False' in source
