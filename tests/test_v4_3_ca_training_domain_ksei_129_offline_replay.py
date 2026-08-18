from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ksei_129_config_pins_observed_acquisition_manifest() -> None:
    config = json.loads(
        (ROOT / "config" / "v4_3_ca_training_domain_ksei_129_v1.json").read_text(
            encoding="utf-8"
        )
    )
    delta = config["accepted_delta"]
    assert delta["manifest_sha256"] == (
        "bb1043f36f20cd418be1b602ce9204cfcf8ca7ec546c57d913590b3898ea4976"
    )
    assert delta["coverage_certified_tickers"] == 93
    assert delta["coverage_unresolved_tickers"] == 36
    assert delta["history_rows"] == 2065
    assert delta["failure_class_counts"] == {"HTTP_NON_200_OR_EMPTY": 36}


def test_offline_replay_source_has_no_provider_or_target_execution_path() -> None:
    source = (
        ROOT / "scripts" / "run_v4_3_ca_training_domain_ksei_129_offline_replay.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "recover_ticker(",
        "requests.get",
        ".get(KSEI_",
        "materialize_v4_target_ledger",
        "fit_v4_head",
        "score_v4_head",
        "ranking_v4_3_model_eval",
    )
    for token in forbidden:
        assert token not in source
    assert '"provider_calls": False' in source
    assert '"network_calls": False' in source
    assert '"historical_target_loaded": False' in source
    assert '"historical_model_fit": False' in source
    assert '"historical_performance_computed": False' in source


def test_offline_replay_keeps_observed_unresolved_count_fail_closed() -> None:
    source = (
        ROOT / "scripts" / "run_v4_3_ca_training_domain_ksei_129_offline_replay.py"
    ).read_text(encoding="utf-8")
    assert "expected_delta_tickers=129" in source
    assert "expected_delta_certified=93" in source
    assert "expected_delta_unresolved=36" in source
    assert "coverage_unresolved_decision_tickers" in source
