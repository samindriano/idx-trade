from __future__ import annotations

import copy

import pandas as pd
import pytest

from idx_trade.prospective_preaccess_readiness_v1 import (
    CANONICAL_TARGET_ID,
    MODEL_FINGERPRINT,
    MODEL_GENERATION,
    MODEL_NAME,
    PreAccessReadinessError,
    RANKING_SEMANTICS,
    build_readiness_report,
    calendar_eligibility,
    inspect_access_state,
    render_readiness_text,
    validate_outcome_blind_metadata,
    validate_partial_session_inventory,
)


def _sha(i: int) -> str:
    return f"{i:064x}"[-64:]


def _inventory(n: int) -> pd.DataFrame:
    dates = pd.bdate_range("2026-08-26", periods=max(n, 1))
    rows = []
    for idx in range(n):
        rows.append(
            {
                "forward_position": idx + 1,
                "session_index": 2000 + idx,
                "session_date": dates[idx].date().isoformat(),
                "score_artifact_path": f"safe/scores/{idx+1:03d}.csv",
                "score_artifact_sha256": _sha(idx + 1),
                "score_manifest_path": f"safe/manifests/{idx+1:03d}.json",
                "score_manifest_sha256": _sha(idx + 1001),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "forward_position",
            "session_index",
            "session_date",
            "score_artifact_path",
            "score_artifact_sha256",
            "score_manifest_path",
            "score_manifest_sha256",
        ],
    )


def _contract() -> dict:
    return {
        "model": {
            "model_id": MODEL_NAME,
            "generation": MODEL_GENERATION,
            "fingerprint": MODEL_FINGERPRINT,
            "ranking": RANKING_SEMANTICS,
        },
        "target_identity": {"status": "RESOLVED", "target_id": CANONICAL_TARGET_ID},
        "scientific_boundary": {
            "protected_outcomes_accessed": False,
            "real_loader_called": False,
            "real_marker_written": False,
        },
    }


def _ready_component() -> dict:
    return {"status": "READY", "guards": {"protected_outcome_accessed": False}}


def test_empty_partial_inventory_is_accumulating() -> None:
    result = validate_partial_session_inventory(_inventory(0))
    assert result["status"] == "ACCUMULATING"
    assert result["observed_sessions"] == 0
    assert result["remaining_sessions"] == 100


def test_partial_inventory_accepts_contiguous_prefix_only() -> None:
    result = validate_partial_session_inventory(_inventory(3))
    assert result["observed_sessions"] == 3
    assert result["rows"][-1]["forward_position"] == 3

    bad = _inventory(3)
    bad.loc[2, "forward_position"] = 4
    with pytest.raises(PreAccessReadinessError, match="POSITIONS_NOT_CONTIGUOUS"):
        validate_partial_session_inventory(bad)


def test_partial_inventory_rejects_duplicate_and_wrong_order() -> None:
    duplicate = _inventory(3)
    duplicate.loc[2, "session_index"] = duplicate.loc[1, "session_index"]
    with pytest.raises(PreAccessReadinessError, match="DUPLICATE_SESSION_IDENTITY"):
        validate_partial_session_inventory(duplicate)

    wrong = _inventory(3)
    wrong.loc[2, "session_index"] = 1999
    with pytest.raises(PreAccessReadinessError, match="INDEX_ORDER_INVALID"):
        validate_partial_session_inventory(wrong)


def test_partial_inventory_rejects_protected_reference_before_read() -> None:
    bad = _inventory(1)
    bad.loc[0, "score_artifact_path"] = "some/outcome_vault/score.csv"
    with pytest.raises(PreAccessReadinessError, match="PROTECTED_REFERENCE_REFUSED"):
        validate_partial_session_inventory(bad)


def test_calendar_eligibility_counts_successors_not_target_values() -> None:
    official = pd.bdate_range("2026-08-26", periods=14)
    signals = [official[0], official[3], official[8]]
    result = calendar_eligibility(signals, official, as_of_session=official[-1])
    assert result["h5_calendar_eligible_count"] == 3
    assert result["h10_calendar_eligible_count"] == 2
    assert all(row["target_values"] == "PROTECTED_NOT_READ" for row in result["rows"])


def test_calendar_eligibility_preserves_civil_date() -> None:
    official = [
        "2026-08-26",
        "2026-08-27",
        "2026-08-28",
        "2026-08-31",
        "2026-09-01",
        "2026-09-02",
    ]
    result = calendar_eligibility(
        ["2026-08-26T00:00:00+07:00"], official, as_of_session="2026-09-02"
    )
    assert result["rows"][0]["session_date"] == "2026-08-26"
    assert result["rows"][0]["h5_calendar_eligible"] is True


def test_metadata_rejects_nonfalse_access_guards_and_protected_paths() -> None:
    with pytest.raises(PreAccessReadinessError, match="OUTCOME_GUARD_NOT_CLEAN"):
        validate_outcome_blind_metadata({"guards": {"protected_outcome_accessed": True}})
    with pytest.raises(PreAccessReadinessError, match="PROTECTED_REFERENCE_REFUSED"):
        validate_outcome_blind_metadata({"artifact_path": "D:/protected/realized_returns.json"})


def test_access_state_maps_clean_orphan_and_contamination() -> None:
    clean = inspect_access_state(
        persisted_status="PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT"
    )
    assert clean["status"] == "READY"
    orphan = inspect_access_state(persisted_status="ORPHAN_OR_INTERRUPTED_STATE")
    assert orphan["status"] == "PROVENANCE_INVALID"
    contaminated = inspect_access_state(
        persisted_status="REAL_ACCESS_ALREADY_COMPLETED",
        protected_outcomes_accessed=True,
    )
    assert contaminated["status"] == "ACCESS_CONTAMINATION"


def test_accumulating_report_never_promotes_missing_attestations() -> None:
    inventory = _inventory(3)
    official = pd.bdate_range("2026-08-26", periods=20)
    report = build_readiness_report(
        inventory=inventory,
        official_trading_sessions=official,
        as_of_session=official[-1],
        access_state=inspect_access_state(
            persisted_status="PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT"
        ),
        contract_identity=_contract(),
    )
    assert report["overall_status"] == "ACCUMULATING_OUTCOME_BLIND"
    assert report["components"]["target_attestation"]["status"] == "NOT_AVAILABLE"
    assert report["components"]["target_attestation"]["target_values"] == "PROTECTED_NOT_READ"
    assert report["guards"]["forward_counter_changed"] is False


def test_complete_calendar_but_missing_attestation_is_incomplete() -> None:
    inventory = _inventory(100)
    official = pd.bdate_range("2026-08-26", periods=115)
    report = build_readiness_report(
        inventory=inventory,
        official_trading_sessions=official,
        as_of_session=official[-1],
        access_state=inspect_access_state(
            persisted_status="PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT"
        ),
        contract_identity=_contract(),
        counter=_ready_component(),
        paper_attestation=_ready_component(),
        benchmark_attestation=_ready_component(),
        prior_access_audit=_ready_component(),
        code_pins=_ready_component(),
    )
    assert report["calendar_eligibility"]["h10_calendar_eligible_count"] == 100
    assert report["overall_status"] == "PREACCESS_REQUIREMENTS_INCOMPLETE"


def test_full_ready_report_still_does_not_access_targets() -> None:
    inventory = _inventory(100)
    official = pd.bdate_range("2026-08-26", periods=115)
    report = build_readiness_report(
        inventory=inventory,
        official_trading_sessions=official,
        as_of_session=official[-1],
        access_state=inspect_access_state(
            persisted_status="PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT"
        ),
        contract_identity=_contract(),
        counter=_ready_component(),
        target_attestation=_ready_component(),
        paper_attestation=_ready_component(),
        benchmark_attestation=_ready_component(),
        prior_access_audit=_ready_component(),
        code_pins=_ready_component(),
    )
    assert report["overall_status"] == "PREACCESS_READY_FOR_EXISTING_GATE"
    assert report["protected_outcomes"]["status"] == "PROTECTED_NOT_READ"
    assert report["protected_outcomes"]["accessed"] is False
    assert report["protected_outcomes"]["values_loaded"] is False
    assert report["existing_gate_preflight_eligible"] is True


def test_identity_drift_is_provenance_invalid() -> None:
    contract = _contract()
    contract["model"] = dict(contract["model"])
    contract["model"]["fingerprint"] = "0" * 64
    report = build_readiness_report(
        inventory=_inventory(1),
        official_trading_sessions=pd.bdate_range("2026-08-26", periods=12),
        as_of_session="2026-09-10",
        access_state=inspect_access_state(
            persisted_status="PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT"
        ),
        contract_identity=contract,
    )
    assert report["overall_status"] == "PREACCESS_PROVENANCE_INVALID"


def test_access_contamination_dominates_overall() -> None:
    report = build_readiness_report(
        inventory=_inventory(1),
        official_trading_sessions=pd.bdate_range("2026-08-26", periods=12),
        as_of_session="2026-09-10",
        access_state=inspect_access_state(
            persisted_status="REAL_ACCESS_ALREADY_COMPLETED",
            real_outcome_access_marker_written=True,
        ),
        contract_identity=_contract(),
    )
    assert report["overall_status"] == "PREACCESS_ACCESS_CONTAMINATED"


def test_renderer_is_operational_only() -> None:
    report = build_readiness_report(
        inventory=_inventory(2),
        official_trading_sessions=pd.bdate_range("2026-08-26", periods=15),
        as_of_session="2026-09-15",
        access_state=inspect_access_state(
            persisted_status="PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT"
        ),
        contract_identity=_contract(),
    )
    text = render_readiness_text(report)
    assert "PROTECTED_NOT_READ" in text
    assert "Sharpe" not in text
    assert "IC" not in text


def test_readiness_is_deterministic_for_same_inputs() -> None:
    kwargs = dict(
        inventory=_inventory(3),
        official_trading_sessions=list(pd.bdate_range("2026-08-26", periods=20)),
        as_of_session="2026-09-22",
        access_state=inspect_access_state(
            persisted_status="PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT"
        ),
        contract_identity=_contract(),
    )
    first = build_readiness_report(**kwargs)
    second = build_readiness_report(**copy.deepcopy(kwargs))
    assert first == second


def test_calendar_requires_as_of_cutoff_so_future_schedule_cannot_fake_maturity() -> None:
    with pytest.raises(PreAccessReadinessError, match="AS_OF_SESSION_REQUIRED"):
        calendar_eligibility(
            ["2026-08-26"],
            pd.bdate_range("2026-08-26", periods=20),
            as_of_session=None,
        )


def test_contract_alias_access_guards_are_enforced() -> None:
    with pytest.raises(PreAccessReadinessError, match="OUTCOME_GUARD_NOT_CLEAN"):
        validate_outcome_blind_metadata(
            {"scientific_boundary": {"real_loader_called": True}}
        )
    with pytest.raises(PreAccessReadinessError, match="OUTCOME_GUARD_NOT_CLEAN"):
        validate_outcome_blind_metadata(
            {"scientific_boundary": {"real_marker_written": True}}
        )
