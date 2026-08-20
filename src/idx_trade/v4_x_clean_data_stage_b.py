"""Generic, outcome-blind Stage-B clean-data consolidation helpers.

This module deliberately does not derive or adjudicate security identities.
It only validates an independently accepted identity action and deterministically
materializes the corresponding final security master while keeping Stage-A
panel bytes immutable by reference.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import pandas as pd

IDENTITY_COLUMNS = (
    "security_id",
    "ticker",
    "company_name",
    "listed_from",
    "listed_to",
    "source",
)

ACCEPTANCE_SCHEMA = "v4_x_clean_identity_acceptance_v1"
ACCEPTANCE_STATUS = "IDENTITY_ADJUDICATION_ACCEPTED_FOR_CLEAN_CONSOLIDATION"
STAGE_C_STATUS = "PIT_SECURITY_IDENTITY_STAGE_C_COMPLETE"
BLOCKED_STAGE_C_DECISION = "STAGE_C_BLOCKED_EXACT_SUPPORT_NOT_PRESENT_IN_PRIMARY_MODEL_FRAME"
ACTION_APPLY = "APPLY_CERTIFIED_IDENTITY_OVERLAY"
ACTION_PRESERVE = "PRESERVE_FROZEN_SECURITY_MASTER"
ALLOWED_ACTIONS = frozenset({ACTION_APPLY, ACTION_PRESERVE})
MATERIALIZATION_POLICY = "REFERENCE_STAGE_A_BYTES_PLUS_ACCEPTED_SECURITY_MASTER_V1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_FALSE_GUARDRAILS = (
    "provider_calls",
    "target_numeric_values_accessed",
    "returns_or_ranks_accessed",
    "protected_forward_accessed",
    "fresh_forward_accessed",
    "model_fit",
    "model_scoring",
    "model_tuning",
    "stage_a_panel_rewritten",
    "stage_a_hlc_open_changed",
    "session_semantics_changed",
    "primary_liquidity_definition_changed",
    "forward_counter_mutated",
    "identity_decision_inferred_by_this_lane",
)


@dataclass(frozen=True)
class StageBIdentityResult:
    final_security_master: pd.DataFrame
    identity_ledger: pd.DataFrame
    summary: dict[str, Any]


def _require_sha256(value: object, label: str) -> str:
    text = str(value or "").strip().lower()
    if not SHA256_RE.fullmatch(text):
        raise ValueError(f"{label} must be a lowercase SHA-256 hex digest")
    return text


def _normalize_identity_frame(
    frame: pd.DataFrame,
    *,
    label: str,
    allow_empty: bool = False,
) -> pd.DataFrame:
    missing = set(IDENTITY_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {sorted(missing)}")
    out = frame.loc[:, IDENTITY_COLUMNS].copy()
    if out.empty:
        if allow_empty:
            return out
        raise ValueError(f"{label} is empty")

    for column in ("security_id", "ticker", "company_name", "source"):
        out[column] = out[column].astype(str).str.strip()
    out["ticker"] = out["ticker"].str.upper().str.replace(".JK", "", regex=False)
    if out[["security_id", "ticker", "company_name", "source"]].eq("").any().any():
        raise ValueError(f"{label} contains empty identity metadata")

    out["listed_from"] = pd.to_datetime(out["listed_from"], errors="coerce").dt.tz_localize(None).dt.normalize()
    out["listed_to"] = pd.to_datetime(out["listed_to"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if out["listed_from"].isna().any():
        raise ValueError(f"{label} contains invalid listed_from")
    if (out["listed_to"].notna() & out["listed_to"].lt(out["listed_from"])).any():
        raise ValueError(f"{label} contains listed_to before listed_from")
    if out["security_id"].duplicated().any():
        raise ValueError(f"{label} contains duplicate security_id")
    if out["ticker"].duplicated().any():
        raise ValueError(f"{label} contains duplicate ticker")
    return out.sort_values(["ticker", "listed_from"], kind="mergesort").reset_index(drop=True)


def validate_acceptance_contract(contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise ValueError("identity acceptance must be a JSON object")
    if contract.get("schema_version") != ACCEPTANCE_SCHEMA:
        raise ValueError("identity acceptance schema changed")
    if contract.get("status") != ACCEPTANCE_STATUS:
        raise ValueError("identity acceptance status changed")
    if contract.get("stage_c_status") != STAGE_C_STATUS:
        raise ValueError("identity acceptance Stage-C status changed")
    stage_c_decision = str(contract.get("stage_c_decision") or "").strip()
    if not stage_c_decision:
        raise ValueError("identity acceptance missing Stage-C decision")
    if stage_c_decision == BLOCKED_STAGE_C_DECISION:
        raise ValueError("blocked Stage-C result cannot enter clean consolidation")
    if contract.get("independent_review_accepted") is not True:
        raise ValueError("identity acceptance lacks independent review")

    action = str(contract.get("clean_consolidation_action") or "").strip()
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"unsupported clean-consolidation action: {action}")
    stage_c_sha = _require_sha256(contract.get("stage_c_manifest_sha256"), "stage_c_manifest_sha256")

    policy = str(contract.get("accepted_identity_policy") or "").strip()
    if not policy:
        raise ValueError("identity acceptance missing accepted_identity_policy")

    guardrails = contract.get("guardrails")
    if not isinstance(guardrails, dict):
        raise ValueError("identity acceptance missing guardrails")
    for key in REQUIRED_FALSE_GUARDRAILS:
        if key not in guardrails:
            raise ValueError(f"identity acceptance guardrail missing: {key}")
        if guardrails[key] is not False:
            raise ValueError(f"identity acceptance guardrail must be false: {key}")

    overlay_sha = contract.get("identity_overlay_sha256")
    expected_rows = contract.get("expected_identity_overlay_rows")
    expected_tickers = contract.get("expected_identity_overlay_tickers")
    if action == ACTION_APPLY:
        overlay_sha = _require_sha256(overlay_sha, "identity_overlay_sha256")
        if not isinstance(expected_rows, int) or expected_rows <= 0:
            raise ValueError("APPLY action requires positive expected_identity_overlay_rows")
        if not isinstance(expected_tickers, int) or expected_tickers <= 0:
            raise ValueError("APPLY action requires positive expected_identity_overlay_tickers")
    else:
        if overlay_sha not in (None, ""):
            raise ValueError("PRESERVE action must not pin an identity overlay")
        if expected_rows not in (None, 0) or expected_tickers not in (None, 0):
            raise ValueError("PRESERVE action requires zero identity-overlay counts")
        overlay_sha = None
        expected_rows = 0
        expected_tickers = 0

    return {
        "action": action,
        "stage_c_manifest_sha256": stage_c_sha,
        "stage_c_decision": stage_c_decision,
        "accepted_identity_policy": policy,
        "identity_overlay_sha256": overlay_sha,
        "expected_identity_overlay_rows": int(expected_rows),
        "expected_identity_overlay_tickers": int(expected_tickers),
    }


def validate_stage_c_manifest(
    manifest: dict[str, Any],
    *,
    accepted_manifest_sha256: str,
) -> None:
    _require_sha256(accepted_manifest_sha256, "accepted Stage-C manifest SHA")
    if manifest.get("status") != STAGE_C_STATUS:
        raise ValueError("Stage-C manifest status changed")
    if manifest.get("stage") != "C":
        raise ValueError("Stage-C manifest stage changed")
    if manifest.get("outcome_blind") is not True:
        raise ValueError("Stage-C manifest is not outcome-blind")
    if manifest.get("decision") == BLOCKED_STAGE_C_DECISION:
        raise ValueError("blocked Stage-C manifest cannot enter Stage B")
    for key in (
        "target_numeric_values_accessed",
        "provider_calls",
        "model_fit",
        "model_scoring",
        "protected_forward_accessed",
        "fresh_forward_accessed",
    ):
        if manifest.get(key) is not False:
            raise ValueError(f"Stage-C manifest guard changed: {key}")


def materialize_final_security_master(
    frozen_security_master: pd.DataFrame,
    identity_overlay: pd.DataFrame | None,
    acceptance_contract: dict[str, Any],
) -> StageBIdentityResult:
    """Materialize only the independently accepted security-master action.

    The function never derives identities from panel data or ticker names. The
    overlay, if authorized, must be supplied explicitly by upstream acceptance.
    """

    accepted = validate_acceptance_contract(acceptance_contract)
    frozen = _normalize_identity_frame(frozen_security_master, label="frozen security master")
    action = accepted["action"]

    if action == ACTION_PRESERVE:
        if identity_overlay is not None:
            overlay = _normalize_identity_frame(
                identity_overlay, label="identity overlay", allow_empty=True
            )
            if not overlay.empty:
                raise ValueError("PRESERVE action received non-empty identity overlay")
        final_master = frozen.copy()
        ledger = pd.DataFrame(columns=[*IDENTITY_COLUMNS, "stage_b_action", "identity_policy"])
    else:
        if identity_overlay is None:
            raise ValueError("APPLY action requires identity overlay bytes")
        overlay = _normalize_identity_frame(identity_overlay, label="identity overlay")
        if len(overlay) != accepted["expected_identity_overlay_rows"]:
            raise ValueError("accepted identity-overlay row count changed")
        if int(overlay["ticker"].nunique()) != accepted["expected_identity_overlay_tickers"]:
            raise ValueError("accepted identity-overlay ticker count changed")

        overlapping_security_ids = sorted(set(frozen["security_id"]) & set(overlay["security_id"]))
        overlapping_tickers = sorted(set(frozen["ticker"]) & set(overlay["ticker"]))
        if overlapping_security_ids:
            raise ValueError("identity overlay replaces existing security_id")
        if overlapping_tickers:
            raise ValueError("identity overlay replaces existing ticker")

        final_master = pd.concat([frozen, overlay], ignore_index=True)
        final_master = _normalize_identity_frame(final_master, label="final security master")
        ledger = overlay.copy()
        ledger["stage_b_action"] = ACTION_APPLY
        ledger["identity_policy"] = accepted["accepted_identity_policy"]

    summary = {
        "status": "STAGE_B_SECURITY_MASTER_MATERIALIZED_REFIT_NOT_AUTHORIZED",
        "materialization_policy": MATERIALIZATION_POLICY,
        "clean_consolidation_action": action,
        "identity_policy": accepted["accepted_identity_policy"],
        "frozen_security_master_rows": int(len(frozen)),
        "frozen_security_master_tickers": int(frozen["ticker"].nunique()),
        "identity_overlay_rows": int(len(ledger)),
        "identity_overlay_tickers": int(ledger["ticker"].nunique()) if not ledger.empty else 0,
        "final_security_master_rows": int(len(final_master)),
        "final_security_master_tickers": int(final_master["ticker"].nunique()),
        "stage_a_panel_rewritten": False,
        "identity_decision_inferred_by_this_lane": False,
        "model_refit_authorized": False,
    }
    return StageBIdentityResult(final_master, ledger, summary)
