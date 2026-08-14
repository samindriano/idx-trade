from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.financial_pit_alpha import (
    CANDIDATE_FEATURE_COLUMNS,
    FINANCIAL_FEATURE_IDS,
    FINANCIAL_SLOT_COLUMNS,
    FinancialAlphaContractError,
    freeze_comparison_support,
    load_v2_common_support,
    run_support_census,
    session_decision_cutoff_utc,
    sha256_file,
)


PERIODS = {"Q1": "tw1", "H1": "tw2", "9M": "tw3", "FY": "audit"}


def _financial_rows(*, available: tuple[str, str] | None = None, conflict: bool = False) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for feature_id in FINANCIAL_FEATURE_IDS:
        for period_key, fiscal_period in PERIODS.items():
            values = [1.0]
            if conflict and feature_id == FINANCIAL_FEATURE_IDS[0] and period_key == "Q1":
                values = [1.0, 2.0]
            for idx, value in enumerate(values):
                status = "AVAILABLE" if available == (feature_id, period_key) else "MISSING_INPUT"
                rows.append(
                    {
                        "ticker": "AAA",
                        "as_of_timestamp_utc": "2025-01-01T15:00:00Z",
                        "fiscal_year": 2024,
                        "fiscal_period": fiscal_period,
                        "period_stratification_key": period_key,
                        "statement_scope": "CONSOLIDATED",
                        "industry_class": "GENERAL",
                        "representation_format": "XLSX",
                        "reporting_version_id": f"AAA-2024-{period_key}-{idx}",
                        "reporting_attachment_sha256": f"sha-{feature_id}-{period_key}-{idx}",
                        "reporting_publication_at_utc": "2025-01-01T10:00:00Z",
                        "reporting_knowledge_at_utc": "2025-01-01T10:00:00Z",
                        "reporting_period_start": "2024-01-01",
                        "reporting_period_end": "2024-12-31",
                        "reporting_instant_date": "",
                        "reporting_period_evidence_kind": "XLSX_CELL",
                        "reporting_period_evidence_location": "Sheet1!A1",
                        "feature_id": feature_id,
                        "feature_family": "TEST",
                        "feature_formula": "test",
                        "feature_value": value if status == "AVAILABLE" else None,
                        "availability_status": status,
                        "availability_reason": "test",
                        "current_filing_age_days": 0.0,
                        "input_version_ids_json": "[]",
                        "input_attachment_sha256s_json": "[]",
                        "input_publication_at_utc_json": "[]",
                        "input_knowledge_at_utc_json": "[]",
                        "input_period_boundaries_json": "[]",
                        "input_fact_identities_json": "[]",
                        "input_source_refs_json": "[\"ref\"]",
                        "input_source_locations_json": "[\"Sheet1!A1\"]",
                        "input_fact_provenance_json": "[]",
                        "feature_contract_version": "TEST",
                    }
                )
    return pd.DataFrame(rows)


def _write_inputs(tmp_path: Path, financial: pd.DataFrame, *, outcome: bool = False) -> tuple[Path, Path]:
    v2 = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": [pd.Timestamp("2025-01-01")],
            "signal_session_index": [100],
        }
    )
    if outcome:
        v2["binary_target"] = [1]
    v2_path = tmp_path / "v2.parquet"
    financial_path = tmp_path / "financial.parquet"
    v2.to_parquet(v2_path, index=False)
    financial.to_parquet(financial_path, index=False)
    return v2_path, financial_path


def test_cutoff_is_explicit_utc_timestamp_not_date_join() -> None:
    result = session_decision_cutoff_utc(pd.Series([pd.Timestamp("2025-01-01")]))
    assert result.iloc[0].isoformat() == "2025-01-01T11:00:00+00:00"


def test_support_census_uses_latest_eligible_state_and_preserves_strata(tmp_path: Path) -> None:
    v2_path, financial_path = _write_inputs(
        tmp_path,
        _financial_rows(available=(FINANCIAL_FEATURE_IDS[0], "Q1")),
    )
    output = tmp_path / "out"
    summary = run_support_census(
        v2_path,
        financial_path,
        output,
        v2_sha256=sha256_file(v2_path),
        financial_sha256=sha256_file(financial_path),
    )
    assert summary["v2_rows"] == 1
    assert summary["financial_any_feature_rows"] == 1
    support = pd.read_csv(output / "feature_support.csv")
    q1 = support[(support.feature_id == FINANCIAL_FEATURE_IDS[0]) & (support.period_stratum == "Q1")]
    h1 = support[(support.feature_id == FINANCIAL_FEATURE_IDS[0]) & (support.period_stratum == "H1")]
    assert int(q1.iloc[0].rows_available) == 1
    assert int(h1.iloc[0].rows_available) == 0
    selected = pd.read_parquet(output / "selected_feature_states.parquet")
    provenance = selected[
        (selected.feature_id == FINANCIAL_FEATURE_IDS[0]) & (selected.period_stratum == "Q1")
    ].iloc[0]
    assert provenance.period_stratum == "Q1"
    assert provenance.reporting_attachment_sha256
    slot_matrix = pd.read_parquet(output / "selected_slot_matrix.parquet")
    assert not slot_matrix.duplicated(["row_id", "feature_id", "period_stratum"]).any()


def test_same_timestamp_conflict_fails_closed_without_falling_back(tmp_path: Path) -> None:
    v2_path, financial_path = _write_inputs(
        tmp_path,
        _financial_rows(conflict=True, available=(FINANCIAL_FEATURE_IDS[0], "Q1")),
    )
    output = tmp_path / "out"
    run_support_census(
        v2_path,
        financial_path,
        output,
        v2_sha256=sha256_file(v2_path),
        financial_sha256=sha256_file(financial_path),
    )
    diagnostic = pd.read_parquet(output / "join_diagnostics.parquet")
    assert bool(diagnostic.iloc[0].financial_ambiguous_join)
    assert not bool(diagnostic.iloc[0].financial_any_feature_available)


def test_v2_outcome_column_is_rejected_before_join(tmp_path: Path) -> None:
    v2_path, financial_path = _write_inputs(tmp_path, _financial_rows(), outcome=True)
    with pytest.raises(FinancialAlphaContractError, match="protected outcome"):
        load_v2_common_support(v2_path, sha256_file(v2_path))


def test_comparison_support_freezes_exact_identity_set(tmp_path: Path) -> None:
    v2_path, financial_path = _write_inputs(
        tmp_path,
        _financial_rows(available=(FINANCIAL_FEATURE_IDS[0], "Q1")),
    )
    census = tmp_path / "census"
    run_support_census(
        v2_path,
        financial_path,
        census,
        v2_sha256=sha256_file(v2_path),
        financial_sha256=sha256_file(financial_path),
    )
    frozen = freeze_comparison_support(census / "join_diagnostics.parquet", tmp_path / "support")
    assert frozen["rows"] == 1
    assert frozen["tickers"] == 1
    assert frozen["metrics_computed"] is False


def test_census_keeps_fiscal_years_separate_and_writes_support_breakdowns(tmp_path: Path) -> None:
    financial = _financial_rows(available=(FINANCIAL_FEATURE_IDS[0], "Q1"))
    prior = financial.copy()
    prior["fiscal_year"] = 2023
    prior["reporting_version_id"] = prior["reporting_version_id"].astype(str) + "-prior"
    financial = pd.concat([financial, prior], ignore_index=True)
    v2_path, financial_path = _write_inputs(tmp_path, financial)
    output = tmp_path / "out"

    summary = run_support_census(
        v2_path,
        financial_path,
        output,
        v2_sha256=sha256_file(v2_path),
        financial_sha256=sha256_file(financial_path),
    )

    selected = pd.read_parquet(output / "selected_feature_states.parquet")
    assert set(selected["fiscal_year"].dropna().astype(int)) == {2023, 2024}
    assert set(pd.read_csv(output / "coverage_by_period.csv")["period_stratum"]) == {
        "Q1",
        "H1",
        "9M",
        "FY",
    }
    ticker_coverage = pd.read_csv(output / "coverage_by_ticker.csv")
    assert set(ticker_coverage.columns) >= {
        "ticker",
        "rows_any_feature",
    }
    assert summary["knowledge_time_violations"] == 0


def test_asof_join_uses_knowledge_timestamp_not_panel_asof_timestamp(tmp_path: Path) -> None:
    financial = _financial_rows(available=(FINANCIAL_FEATURE_IDS[0], "Q1"))
    mask = (financial["feature_id"] == FINANCIAL_FEATURE_IDS[0]) & financial["period_stratification_key"].eq("Q1")
    financial.loc[mask, "as_of_timestamp_utc"] = "2025-01-01T17:00:00Z"
    financial.loc[mask, "reporting_knowledge_at_utc"] = "2025-01-01T10:00:00Z"
    v2_path, financial_path = _write_inputs(tmp_path, financial)
    output = tmp_path / "out"

    summary = run_support_census(
        v2_path,
        financial_path,
        output,
        v2_sha256=sha256_file(v2_path),
        financial_sha256=sha256_file(financial_path),
    )

    assert summary["financial_any_feature_rows"] == 1


def test_candidate_matrix_has_exact_25_52_77_raw_feature_slots() -> None:
    assert len(CANDIDATE_FEATURE_COLUMNS["CONTROL"]) == 25
    assert len(FINANCIAL_SLOT_COLUMNS) == 52
    assert len(CANDIDATE_FEATURE_COLUMNS["FINANCIAL_ONLY"]) == 52
    assert len(CANDIDATE_FEATURE_COLUMNS["V2_PLUS_FINANCIAL"]) == 77
    assert len(set(FINANCIAL_SLOT_COLUMNS)) == 52
