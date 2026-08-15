from __future__ import annotations

from pathlib import Path

import pandas as pd

from idx_trade.financial_representation_v2 import (
    CANDIDATE_FEATURES,
    _build_bundle_rows,
    _prepare_candidate_states,
    _select_latest_bundle,
)


PERIODS = {"Q1": 1, "H1": 2, "9M": 3, "FY": 4}


def _state_rows(*, newest_yoy: bool = False, conflicting: bool = False) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    features = list(CANDIDATE_FEATURES)
    for fiscal_year, period, version, knowledge, available_yoy in (
        (2024, "FY", "old", "2025-03-01T10:00:00Z", True),
        (2025, "Q1", "new", "2025-05-15T10:00:00Z", newest_yoy),
    ):
        for feature in features:
            rows.append(
                {
                    "row_id": 0,
                    "ticker": "AAA",
                    "fiscal_year": fiscal_year,
                    "feature_id": feature,
                    "period_stratum": period,
                    "feature_value": 1.0 if feature not in {"yoy_revenue", "yoy_total_assets"} or available_yoy else None,
                    "availability_status": "AVAILABLE" if feature not in {"yoy_revenue", "yoy_total_assets"} or available_yoy else "MISSING_INPUT",
                    "reporting_version_id": version,
                    "reporting_attachment_sha256": f"sha-{version}",
                    "reporting_publication_at_utc": knowledge,
                    "reporting_knowledge_at_utc": knowledge,
                    "reporting_period_start": f"{fiscal_year}-01-01",
                    "reporting_period_end": f"{fiscal_year}-03-31" if period == "Q1" else f"{fiscal_year}-12-31",
                    "reporting_instant_date": "",
                    "reporting_period_evidence_kind": "TEST",
                    "reporting_period_evidence_location": "Sheet1!A1",
                    "representation_format": "XLSX",
                    "input_source_refs_json": '["ref"]',
                    "input_source_locations_json": '["Sheet1!A1"]',
                    "input_fact_identities_json": '["fact"]',
                }
            )
    if conflicting:
        extra = rows[-1].copy()
        extra["reporting_version_id"] = "new-conflict"
        extra["reporting_attachment_sha256"] = "sha-conflict"
        rows.append(extra)
    return pd.DataFrame(rows)


def _support() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "row_id": [0],
            "ticker": ["AAA"],
            "date": [pd.Timestamp("2025-06-01")],
            "signal_session_index": [900],
            "decision_timestamp_utc": ["2025-06-01T11:00:00Z"],
        }
    )


def test_latest_period_bundle_does_not_fallback_to_older_period() -> None:
    states, _ = _prepare_candidate_states(_state_rows(newest_yoy=False))
    chosen, diagnostics = _select_latest_bundle(states)
    rows, _, _ = _build_bundle_rows(_support(), states, chosen, diagnostics)

    assert rows.loc[0, "bundle_fiscal_year"] == 2025
    assert rows.loc[0, "bundle_period_stratum"] == "Q1"
    assert not bool(rows.loc[0, "yoy_revenue__available"])
    assert not bool(rows.loc[0, "all_five_available"])


def test_same_bundle_conflict_fails_closed() -> None:
    states, _ = _prepare_candidate_states(_state_rows(newest_yoy=True, conflicting=True))
    chosen, diagnostics = _select_latest_bundle(states)
    rows, _, summary = _build_bundle_rows(_support(), states, chosen, diagnostics)

    assert summary["ambiguous_same_bundle_rows"] == 1
    assert bool(rows.loc[0, "same_bundle_violation"])
    assert not bool(rows.loc[0, "core3_available"])


def test_candidate_values_require_explicit_available_status() -> None:
    states, _ = _prepare_candidate_states(_state_rows(newest_yoy=True))
    states.loc[states.feature_id.eq("yoy_revenue"), "feature_value"] = None
    states.loc[states.feature_id.eq("yoy_revenue"), "availability_status"] = "MISSING_INPUT"
    chosen, diagnostics = _select_latest_bundle(states)
    rows, _, _ = _build_bundle_rows(_support(), states, chosen, diagnostics)

    assert rows.loc[0, "yoy_revenue__missing_class"] == "DECLARED_MISSING_INPUT"
    assert not bool(rows.loc[0, "yoy_revenue__available"])

