from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.v4_x_clean_data_stage_b import (
    ACCEPTANCE_SCHEMA,
    ACCEPTANCE_STATUS,
    ACTION_APPLY,
    ACTION_PRESERVE,
    BLOCKED_STAGE_C_DECISION,
    REQUIRED_FALSE_GUARDRAILS,
    STAGE_C_STATUS,
    materialize_final_security_master,
    validate_acceptance_contract,
    validate_stage_c_manifest,
)


def identity_row(
    security_id: str,
    ticker: str,
    *,
    listed_from: str = "2020-01-01",
    listed_to: str | None = None,
) -> dict[str, object]:
    return {
        "security_id": security_id,
        "ticker": ticker,
        "company_name": f"Company {ticker}",
        "listed_from": listed_from,
        "listed_to": listed_to,
        "source": "TEST_AUTHORITY",
    }


def guardrails() -> dict[str, bool]:
    return {key: False for key in REQUIRED_FALSE_GUARDRAILS}


def acceptance(action: str = ACTION_APPLY) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": ACCEPTANCE_SCHEMA,
        "status": ACCEPTANCE_STATUS,
        "stage_c_status": STAGE_C_STATUS,
        "stage_c_decision": "V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION",
        "stage_c_manifest_sha256": "a" * 64,
        "independent_review_accepted": True,
        "clean_consolidation_action": action,
        "accepted_identity_policy": "TEST_ACCEPTED_RIGHT_ONLY_V1",
        "guardrails": guardrails(),
    }
    if action == ACTION_APPLY:
        value.update(
            {
                "identity_overlay_sha256": "b" * 64,
                "expected_identity_overlay_rows": 1,
                "expected_identity_overlay_tickers": 1,
            }
        )
    else:
        value.update(
            {
                "identity_overlay_sha256": None,
                "expected_identity_overlay_rows": 0,
                "expected_identity_overlay_tickers": 0,
            }
        )
    return value


def test_apply_materializes_only_right_only_security_master_addition() -> None:
    frozen = pd.DataFrame([identity_row("SEC-A", "AAA")])
    overlay = pd.DataFrame([identity_row("SEC-B", "BBB", listed_from="2021-02-03")])

    result = materialize_final_security_master(frozen, overlay, acceptance())

    assert result.final_security_master["ticker"].tolist() == ["AAA", "BBB"]
    assert result.identity_ledger["ticker"].tolist() == ["BBB"]
    assert result.summary["identity_overlay_rows"] == 1
    assert result.summary["stage_a_panel_rewritten"] is False
    assert result.summary["model_refit_authorized"] is False


def test_apply_rejects_replacement_of_existing_ticker() -> None:
    frozen = pd.DataFrame([identity_row("SEC-A", "AAA")])
    overlay = pd.DataFrame([identity_row("SEC-B", "AAA")])

    with pytest.raises(ValueError, match="replaces existing ticker"):
        materialize_final_security_master(frozen, overlay, acceptance())


def test_apply_rejects_replacement_of_existing_security_id() -> None:
    frozen = pd.DataFrame([identity_row("SEC-A", "AAA")])
    overlay = pd.DataFrame([identity_row("SEC-A", "BBB")])

    with pytest.raises(ValueError, match="replaces existing security_id"):
        materialize_final_security_master(frozen, overlay, acceptance())


def test_preserve_action_requires_no_identity_overlay() -> None:
    frozen = pd.DataFrame([identity_row("SEC-A", "AAA")])
    result = materialize_final_security_master(frozen, None, acceptance(ACTION_PRESERVE))
    assert result.final_security_master["ticker"].tolist() == ["AAA"]
    assert result.identity_ledger.empty

    overlay = pd.DataFrame([identity_row("SEC-B", "BBB")])
    with pytest.raises(ValueError, match="non-empty identity overlay"):
        materialize_final_security_master(frozen, overlay, acceptance(ACTION_PRESERVE))


def test_acceptance_rejects_blocked_stage_c() -> None:
    contract = acceptance()
    contract["stage_c_decision"] = BLOCKED_STAGE_C_DECISION
    with pytest.raises(ValueError, match="blocked Stage-C"):
        validate_acceptance_contract(contract)


def test_acceptance_rejects_guardrail_true() -> None:
    contract = acceptance()
    contract["guardrails"]["model_fit"] = True  # type: ignore[index]
    with pytest.raises(ValueError, match="model_fit"):
        validate_acceptance_contract(contract)


def test_stage_c_manifest_must_remain_outcome_blind_and_no_fit() -> None:
    manifest = {
        "status": STAGE_C_STATUS,
        "stage": "C",
        "decision": "V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION",
        "outcome_blind": True,
        "target_numeric_values_accessed": False,
        "provider_calls": False,
        "model_fit": False,
        "model_scoring": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
    }
    validate_stage_c_manifest(manifest, accepted_manifest_sha256="a" * 64)

    manifest["model_fit"] = True
    with pytest.raises(ValueError, match="model_fit"):
        validate_stage_c_manifest(manifest, accepted_manifest_sha256="a" * 64)
