from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_replay_config_pins_real_adjudication_and_parent_replay() -> None:
    config = json.loads(
        Path("config/v4_3_ca_training_domain_schedule_80_replay_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert config["parent_replay"]["manifest_sha256"] == (
        "c115ea0bec59cab4da0cda45ee66ba2be5814e0bb9e854e3f7ecd616edc83861"
    )
    assert config["adjudication_parent"]["manifest_sha256"] == (
        "13f4e84d8586c22e100382071f0b4cd4cdbb87e3099b7f0526f844a495ab1fd0"
    )
    assert config["adjudication_parent"]["resolved_events"] == 21
    assert config["adjudication_parent"]["unresolved_events"] == 59
    assert config["gate_rate"] == 0.90
    assert all(value is False for value in config["hard_boundaries"].values())


def test_runner_is_offline_outcome_blind_and_uses_frozen_gate_helpers() -> None:
    source = Path(
        "scripts/run_v4_3_ca_training_domain_schedule_80_adjudication_replay.py"
    ).read_text(encoding="utf-8")
    required = (
        "apply_adjudication",
        "replay_continuity",
        "combine_target_support",
        "build_training_date_sets",
        "validate_frozen_tail",
        "GATE_RATE",
        "PIN_PASS_ARTIFACT_BEFORE_HISTORICAL_EXECUTION",
    )
    for token in required:
        assert token in source
    forbidden = (
        "curl_cffi",
        "requests.get",
        "urllib.request",
        "capture_request(",
        "materialize_v4_target_ledger",
        "HistGradientBoostingRegressor",
        "fit_v4_head",
        "score_v4_head",
    )
    for token in forbidden:
        assert token not in source


def test_strict_boolean_guard_does_not_treat_false_string_as_true() -> None:
    import importlib.util

    path = Path(
        "scripts/run_v4_3_ca_training_domain_schedule_80_adjudication_replay.py"
    )
    spec = importlib.util.spec_from_file_location("schedule80_replay", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.strict_bool_series(pd.Series(["True", "False", "1", "0"]), "x")
    assert result.tolist() == [True, False, True, False]
