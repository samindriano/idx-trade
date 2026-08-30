from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from idx_trade import v4_x1_population_admission_v1 as gate


SESSION = "2026-08-28"
BASELINE = "a" * 64


def _h(char: str) -> str:
    return char * 64


def _identity(*, ticker: str = "AAAA", listed_from: str = "2020-01-01", listed_to=None, source: str = "IDX") -> pd.DataFrame:
    return pd.DataFrame(
        [{"ticker": ticker, "listed_from": listed_from, "listed_to": listed_to, "source": source}]
    )


def _points(*, state: str = "ACTIVE", ticker: str = "AAAA") -> pd.DataFrame:
    return pd.DataFrame(
        [{"ticker": ticker, "session_date": SESSION, "point_state": state}]
    )


def _eod() -> dict[str, object]:
    return {
        "status": "DATA_READY",
        "session_date": SESSION,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
    }


def _evaluate(**overrides) -> gate.PopulationAdmission:
    values = {
        "session_date": SESSION,
        "baseline_identity": _identity(),
        "current_identity": _identity(),
        "point_evidence": _points(),
        "model_input": pd.DataFrame({"ticker": ["AAAA"], "date": [SESSION]}),
        "eod_manifest": _eod(),
        "frozen_baseline_sha256": BASELINE,
        "current_identity_sha256": _h("b"),
        "eod_manifest_sha256": _h("c"),
        "input_manifest_sha256": _h("d"),
        "calendar_sha256": _h("e"),
        "model_manifest_sha256": _h("f"),
        "model_fingerprint": _h("f"),
        "code_identity": {"commit": "1" * 40, "runner_sha256": _h("0")},
        "observed_at": "2026-08-28T18:35:00+07:00",
        "gate_sha256": _h("9"),
        "expected_frozen_science_blobs": {"frozen.py": "a" * 40},
        "actual_frozen_science_blobs": {"frozen.py": "a" * 40},
    }
    values.update(overrides)
    return gate.evaluate_population_admission(**values)


def test_unchanged_baseline_is_safe_and_uses_independent_expected_population() -> None:
    result = _evaluate()
    assert result.status == gate.SAFE_V1_POPULATION
    assert result.expected_identity_tickers == ("AAAA",)
    assert result.observed_model_input_tickers == ("AAAA",)
    assert result.metadata["listed_to_overlay_applied"] is False
    assert result.metadata["population_source"].startswith("FROZEN_BASELINE")
    assert result.metadata["population_proof_scope"] == "IDENTITY_TRADABILITY_COMPATIBILITY_ONLY"
    assert result.metadata["final_scoring_population_attested"] is False
    assert "expected_ticker_set_sha256" not in result.to_dict()


def test_blank_listed_to_is_null_not_a_malformed_delisting() -> None:
    result = _evaluate(
        baseline_identity=_identity(listed_to=""),
        current_identity=_identity(listed_to=""),
    )
    assert result.status == gate.SAFE_V1_POPULATION


def test_verified_post_freeze_delisting_of_shared_baseline_is_not_provable() -> None:
    result = _evaluate(
        current_identity=_identity(listed_to="2026-08-27"),
        point_evidence=pd.DataFrame(columns=["ticker", "session_date", "point_state"]),
        model_input=pd.DataFrame(columns=["ticker", "date"]),
    )
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert "SHARED_IDENTITY_CURRENT_CONFLICT:AAAA" in result.reason_codes
    assert result.expected_identity_tickers == ("AAAA",)


def test_frozen_listed_to_is_compatible_only_when_current_identity_matches_exactly() -> None:
    result = _evaluate(
        baseline_identity=_identity(listed_to="2026-08-27"),
        current_identity=_identity(listed_to="2026-08-27"),
        point_evidence=pd.DataFrame(columns=["ticker", "session_date", "point_state"]),
        model_input=pd.DataFrame(columns=["ticker", "date"]),
    )
    assert result.status == gate.SAFE_V1_POPULATION
    assert result.expected_identity_tickers == ()


def test_current_listed_to_cannot_rewrite_shared_frozen_identity() -> None:
    result = _evaluate(current_identity=_identity(listed_to="2026-08-27"))
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert result.identity_cases["shared_identity_conflicts"] == ["AAAA"]
    assert result.expected_identity_tickers == ("AAAA",)


@pytest.mark.parametrize(
    ("current", "reasons"),
    [
        (_identity(ticker="BBBB"), "BASELINE_IDENTITY_NOT_PROVABLE"),
        (_identity(listed_to="2026-08-19"), "SHARED_IDENTITY_CURRENT_CONFLICT"),
        (_identity(ticker="NEWW", listed_from="2026-08-29"), "FUTURE_IDENTITY"),
        (
            pd.concat([_identity(), _identity(ticker="AAAA")], ignore_index=True),
            "CURRENT_IDENTITY_DUPLICATE_TICKER",
        ),
        (
            _identity(listed_to="not-a-date"),
            "CURRENT_IDENTITY_LISTED_TO_MALFORMED",
        ),
    ],
)
def test_identity_failures_are_not_provable(current: pd.DataFrame, reasons: str) -> None:
    result = _evaluate(current_identity=current)
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert any(reasons in reason for reason in result.reason_codes)


def test_post_freeze_ipo_follows_only_the_frozen_identity_rule() -> None:
    current = pd.concat(
        [_identity(), _identity(ticker="NEWW", listed_from="2026-08-21")],
        ignore_index=True,
    )
    points = pd.concat([_points(), _points(ticker="NEWW")], ignore_index=True)
    model = pd.DataFrame({"ticker": ["AAAA", "NEWW"], "date": [SESSION, SESSION]})
    safe = _evaluate(
        current_identity=current,
        point_evidence=points,
        model_input=model,
    )
    assert safe.status == gate.SAFE_V1_POPULATION
    blocked = _evaluate(
        current_identity=pd.concat(
            [_identity(), _identity(ticker="NEWW", listed_from="2026-08-20")],
            ignore_index=True,
        ),
        point_evidence=points,
        model_input=model,
    )
    assert blocked.status == gate.V1_POPULATION_NOT_PROVABLE
    assert "POST_FREEZE_RULE_VIOLATION:NEWW" in blocked.reason_codes


def test_post_freeze_ipo_delisted_before_target_follows_frozen_builder_semantics() -> None:
    current = pd.concat(
        [_identity(), _identity(ticker="NEWW", listed_from="2026-08-21", listed_to="2026-08-25")],
        ignore_index=True,
    )
    result = _evaluate(current_identity=current)

    assert result.status == gate.SAFE_V1_POPULATION
    assert result.expected_identity_tickers == ("AAAA", "NEWW")
    assert result.observed_model_input_tickers == ("AAAA",)
    assert result.identity_removed_tickers == ("NEWW",)
    assert result.identity_cases["post_freeze_additions_excluded_by_listed_to"] == ["NEWW"]


def test_tradability_active_vs_non_active_conflict_fails_whole_session() -> None:
    intervals = pd.DataFrame(
        [{
            "ticker": "AAAA",
            "market": "REGULAR",
            "state": "SUSPENDED",
            "effective_from": SESSION,
            "effective_to": None,
            "source": "IDX",
        }]
    )
    result = _evaluate(
        security_master_evidence={"tradability_intervals": intervals}
    )
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert "TRADABILITY_CONFLICT:AAAA" in result.reason_codes


def test_tradability_ambiguity_and_interval_anchor_conflict_fail() -> None:
    ambiguous = pd.DataFrame(
        [
            {"ticker": "AAAA", "market": "REGULAR", "state": "ACTIVE", "effective_from": SESSION, "source": "A"},
            {"ticker": "AAAA", "market": "REGULAR", "state": "SUSPENDED", "effective_from": SESSION, "source": "B"},
        ]
    )
    result = _evaluate(security_master_evidence={"tradability_intervals": ambiguous})
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert any("TRADABILITY_INTERVAL" in reason for reason in result.reason_codes)

    intervals = pd.DataFrame(
        [{"ticker": "AAAA", "market": "REGULAR", "state": "SUSPENDED", "effective_from": SESSION, "source": "A"}]
    )
    anchors = pd.DataFrame(
        [{"ticker": "AAAA", "market": "REGULAR", "as_of_date": SESSION, "state": "ACTIVE", "source": "B", "source_ref": "test://anchor", "evidence_type": "POINT"}]
    )
    result = _evaluate(
        security_master_evidence={
            "tradability_intervals": intervals,
            "tradability_anchors": anchors,
        }
    )
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert "TRADABILITY_CONFLICT:AAAA" in result.reason_codes


def test_model_input_negative_market_value_is_not_admitted() -> None:
    result = _evaluate(
        model_input=pd.DataFrame(
            {"ticker": ["AAAA"], "date": [SESSION], "regular_market_value": [-1.0]}
        )
    )
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert "model input regular_market_value must be finite and non-negative" in result.reason_codes


def test_malformed_interval_or_anchor_evidence_fails_closed() -> None:
    interval = pd.DataFrame(
        [{
            "ticker": "AAAA",
            "market": "REGULAR",
            "state": "ACTIVE",
            "effective_from": SESSION,
            "effective_to": "not-a-date",
            "source": "IDX",
        }]
    )
    result = _evaluate(security_master_evidence={"tradability_intervals": interval})
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert "TRADABILITY_INTERVAL_END_DATE_INVALID" in result.reason_codes

    anchor = pd.DataFrame(
        [{
            "ticker": "AAAA",
            "market": "REGULAR",
            "as_of_date": SESSION,
            "state": "ACTIVE",
            "source": "",
            "source_ref": "idx://anchor",
            "evidence_type": "POINT",
        }]
    )
    result = _evaluate(security_master_evidence={"tradability_anchors": anchor})
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert "TRADABILITY_ANCHOR_SOURCE_MISSING" in result.reason_codes


@pytest.mark.parametrize("state", ["NO_TRADE", "SUSPENDED"])
def test_non_active_state_does_not_shrink_expected_population(state: str) -> None:
    result = _evaluate(
        point_evidence=_points(state=state),
        model_input=pd.DataFrame(columns=["ticker", "date"]),
    )
    assert result.status == gate.SAFE_V1_POPULATION
    assert result.expected_identity_tickers == ("AAAA",)
    assert result.observed_model_input_tickers == ()
    assert result.identity_removed_tickers == ("AAAA",)


def test_model_input_is_a_subset_and_non_active_expected_identity_is_omitted() -> None:
    baseline = pd.concat(
        [_identity(), _identity(ticker="BBBB")],
        ignore_index=True,
    )
    result = _evaluate(
        baseline_identity=baseline,
        current_identity=baseline,
        point_evidence=pd.concat(
            [_points(), _points(ticker="BBBB", state="NO_TRADE")],
            ignore_index=True,
        ),
        model_input=pd.DataFrame({"ticker": ["AAAA"], "date": [SESSION]}),
    )

    assert result.status == gate.SAFE_V1_POPULATION
    assert result.expected_identity_tickers == ("AAAA", "BBBB")
    assert result.observed_model_input_tickers == ("AAAA",)
    assert result.identity_removed_tickers == ("BBBB",)
    assert result.metadata["model_input_identity_subset"] is True
    assert result.metadata["model_input_identity_equality"] is False


def test_non_active_expected_identity_cannot_have_model_input() -> None:
    result = _evaluate(
        point_evidence=_points(state="SUSPENDED"),
    )
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert "MODEL_INPUT_NON_ACTIVE_STATE:AAAA:SUSPENDED" in result.reason_codes


def test_explicit_non_active_state_without_point_or_model_is_valid_domain() -> None:
    intervals = pd.DataFrame(
        [{
            "ticker": "AAAA",
            "market": "REGULAR",
            "state": "SUSPENDED",
            "effective_from": SESSION,
            "effective_to": None,
            "source": "IDX",
        }]
    )
    result = _evaluate(
        point_evidence=pd.DataFrame(columns=["ticker", "session_date", "point_state"]),
        model_input=pd.DataFrame(columns=["ticker", "date"]),
        security_master_evidence={"tradability_intervals": intervals},
    )

    assert result.status == gate.SAFE_V1_POPULATION
    assert result.identity_removed_tickers == ("AAAA",)


def test_missing_explicit_tradability_state_is_not_provable() -> None:
    result = _evaluate(
        point_evidence=pd.DataFrame(columns=["ticker", "session_date", "point_state"])
    )
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert "TRADABILITY_STATE_NOT_EXPLICIT:AAAA" in result.reason_codes


def test_model_input_identity_mismatch_is_not_a_final_scoring_denominator_claim() -> None:
    result = _evaluate(model_input=pd.DataFrame(columns=["ticker", "date"]))
    assert result.status == gate.V1_POPULATION_NOT_PROVABLE
    assert "MODEL_INPUT_ACTIVE_TICKER_MISSING:AAAA" in result.reason_codes
    assert result.metadata["population_proof_scope"] == "IDENTITY_TRADABILITY_COMPATIBILITY_ONLY"
    assert result.metadata["final_scoring_population_authority"] == (
        "PINNED_V4_X1_FEATURE_BUILDER_UNIVERSE_PRIMARY_LIQUID"
    )
    assert result.metadata["final_scoring_population_attested"] is False
    assert "final_scoring_tickers" not in result.metadata


def test_immutable_attestation_is_idempotent_and_conflicting_retry_fails(tmp_path: Path) -> None:
    admission = _evaluate()
    first = gate.persist_population_attestation(tmp_path, admission)
    second = gate.persist_population_attestation(tmp_path, admission)
    assert first.attestation_path == second.attestation_path
    assert first.attestation_sha256 == second.attestation_sha256

    changed = _evaluate(model_input=pd.DataFrame(columns=["ticker", "date"]))
    with pytest.raises(gate.PopulationAdmissionConflict, match="IDENTITY_CONFLICT"):
        gate.persist_population_attestation(tmp_path, changed)


def test_existing_attestation_content_and_identity_hash_are_verified(tmp_path: Path) -> None:
    admission = _evaluate()
    persisted = gate.persist_population_attestation(tmp_path, admission)
    path = Path(persisted.attestation_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["observed_model_input_tickers"] = []
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(gate.PopulationAdmissionConflict, match="EXISTING_INVALID"):
        gate.persist_population_attestation(tmp_path, admission)

    path.write_text(json.dumps(admission.to_dict()), encoding="utf-8")
    with pytest.raises(gate.PopulationAdmissionConflict, match="EXISTING_INVALID"):
        gate.persist_population_attestation(tmp_path, admission)


@pytest.mark.parametrize("stage", ["temp_created", "temp_fsynced", "promotion"])
def test_attestation_crash_before_promotion_leaves_no_final_or_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    admission = _evaluate()

    def fail_at(current: str, temporary: Path, target: Path) -> None:
        del temporary, target
        if current == stage:
            raise RuntimeError("INJECTED_ATTESTATION_CRASH")

    monkeypatch.setattr(gate, "_attestation_stage_hook", fail_at)
    with pytest.raises(RuntimeError, match="INJECTED_ATTESTATION_CRASH"):
        gate.persist_population_attestation(tmp_path, admission)
    target = tmp_path / "forward_monitoring" / "population_admission" / f"{SESSION}.json"
    assert not target.exists()
    assert not list(target.parent.glob(".*.tmp"))


def test_identical_and_conflicting_create_races_are_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    admission = _evaluate()
    target = tmp_path / "forward_monitoring" / "population_admission" / f"{SESSION}.json"
    original_link = gate.os.link
    calls = 0

    def identical_race(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            raise FileExistsError(destination)
        original_link(source, destination)

    monkeypatch.setattr(gate.os, "link", identical_race)
    first = gate.persist_population_attestation(tmp_path, admission)
    assert first.attestation_path == str(target)
    assert first.attestation_sha256 == gate.sha256_file(target)

    changed = _evaluate(model_input=pd.DataFrame(columns=["ticker", "date"]))
    with pytest.raises(gate.PopulationAdmissionConflict, match="IDENTITY_CONFLICT"):
        gate.persist_population_attestation(tmp_path, changed)


def test_retained_2_of_100_classifier_does_not_promote_incomplete_history() -> None:
    # This is deliberately an old/incomplete retained record, not a newly
    # manufactured attestation.  Historical 2/100 evidence without the exact
    # current schema and immutable content binding is not proof.
    retained = {
        "schema_version": "idx_trade_v4_x1_population_admission_legacy",
        "status": gate.SAFE_V1_POPULATION,
        "session_date": SESSION,
        "metadata": {"frozen_baseline_sha256": BASELINE},
    }
    assert (
        gate.classify_retained_population_attestation(
            retained,
            expected_session_date=SESSION,
            expected_baseline_sha256=BASELINE,
        )
        == gate.NOT_PROVABLE_FROM_RETAINED_EVIDENCE
    )


def test_retained_classifier_recomputes_content_and_bound_hashes(tmp_path: Path) -> None:
    admission = _evaluate()
    persisted = gate.persist_population_attestation(tmp_path, admission)
    retained = json.loads(Path(persisted.attestation_path).read_text(encoding="utf-8"))
    retained["expected_identity_tickers"] = ["BBBB"]
    assert (
        gate.classify_retained_population_attestation(
            retained,
            expected_session_date=SESSION,
            expected_baseline_sha256=BASELINE,
        )
        == gate.NOT_PROVABLE_FROM_RETAINED_EVIDENCE
    )
    retained = json.loads(Path(persisted.attestation_path).read_text(encoding="utf-8"))
    retained["metadata"]["calendar_sha256"] = _h("0")
    assert (
        gate.classify_retained_population_attestation(
            retained,
            expected_session_date=SESSION,
            expected_baseline_sha256=BASELINE,
        )
        == gate.NOT_PROVABLE_FROM_RETAINED_EVIDENCE
    )


def test_score_gate_calls_scorer_once_only_after_safe_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = SimpleNamespace()
    calls: list[str] = []

    def scorer(*args, **kwargs):
        del args, kwargs
        calls.append("score")
        return {"status": "SCORED"}

    module.score_v4_x1_session = scorer
    safe = _evaluate()
    monkeypatch.setattr(gate, "build_runtime_population_admission", lambda **kwargs: safe)
    with gate.PopulationScoreGate(module, runtime_root=tmp_path) as installed:
        result = module.score_v4_x1_session("ignored")
    assert result["status"] == "SCORED"
    assert calls == ["score"]
    assert installed.last_admission is not None

    calls.clear()
    blocked = _evaluate(
        point_evidence=pd.DataFrame(columns=["ticker", "session_date", "point_state"])
    )
    monkeypatch.setattr(gate, "build_runtime_population_admission", lambda **kwargs: blocked)
    with pytest.raises(gate.V1PopulationNotProvable):
        with gate.PopulationScoreGate(module, runtime_root=tmp_path / "blocked"):
            module.score_v4_x1_session("ignored")
    assert calls == []


def test_shared_delisting_veto_never_invokes_scorer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = SimpleNamespace()
    calls: list[str] = []
    module.score_v4_x1_session = lambda: calls.append("score")
    blocked = _evaluate(current_identity=_identity(listed_to="2026-08-27"))
    monkeypatch.setattr(gate, "build_runtime_population_admission", lambda **kwargs: blocked)
    with pytest.raises(gate.V1PopulationNotProvable):
        with gate.PopulationScoreGate(module, runtime_root=tmp_path):
            module.score_v4_x1_session()
    assert calls == []


def test_eod_ready_evidence_survives_score_veto_without_done_or_counter(tmp_path: Path, monkeypatch) -> None:
    module = SimpleNamespace()
    calls: list[str] = []
    module.score_v4_x1_session = lambda: calls.append("score")
    blocked = _evaluate(
        point_evidence=pd.DataFrame(columns=["ticker", "session_date", "point_state"])
    )
    monkeypatch.setattr(gate, "build_runtime_population_admission", lambda **kwargs: blocked)
    ready = tmp_path / "DATA_READY.json"
    ready.write_text('{"status":"DATA_READY"}\n', encoding="utf-8")
    with pytest.raises(gate.V1PopulationNotProvable):
        with gate.PopulationScoreGate(module, runtime_root=tmp_path):
            module.score_v4_x1_session()
    assert json.loads(ready.read_text(encoding="utf-8"))["status"] == "DATA_READY"
    assert calls == []
    assert not (tmp_path / "DONE").exists()
    assert not (tmp_path / "COUNTER_MUTATION").exists()


def test_cloud_v2_wrapper_preserves_eod_failure_boundary_before_paper_controller(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import run_e2e_paper_cloud_v2 as cloud_v2

    baseline = tmp_path / "baseline.csv"
    baseline.write_text("ticker,listed_from,listed_to\nAAAA,2020-01-01,\n", encoding="utf-8")
    blocked = _evaluate(
        point_evidence=pd.DataFrame(columns=["ticker", "session_date", "point_state"])
    )
    monkeypatch.setattr(
        cloud_v2,
        "refresh_cloud_runtime_security_master",
        lambda *args, **kwargs: {"guards": {"outcome_accessed": False}},
    )
    monkeypatch.setattr(
        cloud_v2,
        "ensure_runtime_tradability_artifacts",
        lambda *args, **kwargs: {"status": "TRADABILITY_RUNTIME_READY"},
    )
    monkeypatch.setattr(gate, "build_runtime_population_admission", lambda **kwargs: blocked)
    score_calls: list[str] = []

    def scorer(*args, **kwargs):
        del args, kwargs
        score_calls.append("score")
        return {"status": "DONE"}

    monkeypatch.setattr(cloud_v2.clean_x1, "score_v4_x1_session", scorer)

    def fake_pipeline(runtime_root, model_root, **kwargs):
        del model_root, kwargs
        (Path(runtime_root) / "DATA_READY.json").parent.mkdir(parents=True, exist_ok=True)
        (Path(runtime_root) / "DATA_READY.json").write_text("ready\n", encoding="utf-8")
        return cloud_v2.clean_x1.score_v4_x1_session()

    result = cloud_v2._with_runtime_security_master(
        fake_pipeline,
        tmp_path / "runtime",
        tmp_path / "models",
        clean_panel=tmp_path / "panel.parquet",
        clean_security_master=baseline,
        repo_root=tmp_path,
        observed_by="2026-08-28T18:35:00+00:00",
        population_input_manifest_sha256=_h("d"),
    )
    assert result["status"] == "PIPELINE_FAILED"
    assert result["x1_score_attempted"] is False
    assert result["population_admission"]["status"] == gate.V1_POPULATION_NOT_PROVABLE
    assert score_calls == []
    assert (tmp_path / "runtime" / "DATA_READY.json").is_file()


def test_same_session_active_point_preserves_frozen_precedence_without_explicit_state() -> None:
    result = _evaluate(security_master_evidence={})
    assert result.status == gate.SAFE_V1_POPULATION
    assert result.observed_model_input_tickers == ("AAAA",)
    assert not any(reason.startswith("TRADABILITY_CONFLICT:AAAA") for reason in result.reason_codes)


def test_no_trade_without_model_input_preserves_frozen_valid_domain_without_explicit_propagation() -> None:
    result = _evaluate(
        point_evidence=_points(state="NO_TRADE"),
        model_input=pd.DataFrame(columns=["ticker", "date"]),
        security_master_evidence={},
    )
    assert result.status == gate.SAFE_V1_POPULATION
    assert result.expected_identity_tickers == ("AAAA",)
    assert result.observed_model_input_tickers == ()
