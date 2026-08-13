from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.financial_feature_panel import materialize_financial_feature_panel


def _write_jsonl(path: Path, rows: list[dict]) -> str:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _diagnostic(version: str, knowledge: str, sha: str) -> dict:
    return {
        "version_id": version,
        "ticker": "TEST",
        "fiscal_year": 2025,
        "fiscal_period": "tw1",
        "industry_class": "GENERAL",
        "representation_format": "XLSX",
        "scope": "CONSOLIDATED",
        "publication_at_utc": knowledge,
        "source_attachment_sha256": sha,
    }


def _fact(version: str, knowledge: str, sha: str, identity: str, value: str, shape: str) -> dict:
    return {
        "ticker": "TEST",
        "fiscal_year": 2025,
        "fiscal_period": "tw1",
        "statement_scope": "CONSOLIDATED",
        "publication_at_utc": knowledge,
        "knowledge_at_utc": knowledge,
        "attachment_sha256": sha,
        "source_ref": f"IDX/{version}",
        "representation_format": "XLSX",
        "statement_identity": "statement_of_financial_position" if shape == "instant" else "income_statement",
        "fact_identity": identity,
        "value": value,
        "currency": "IDR",
        "unit": "IDR",
        "scale": 1,
        "fiscal_period_covered": {
            "period_kind": shape,
            "report_period": "tw1",
            "report_year": 2025,
            "period_start": "2025-01-01" if shape == "duration" else None,
            "period_end": "2025-03-31",
            "instant_date": "2025-03-31" if shape == "instant" else None,
        },
        "source_location": f"sheet=1000000;cell={identity}",
        "fact_status": "EXTRACTED",
        "extraction_status": "EXTRACTED",
        "taxonomy": "GENERAL",
        "taxonomy_version": "fixture",
        "version_id": version,
    }


def _sidecar_row(version: str, sha: str) -> dict:
    return {
        "version_id": version,
        "ticker": "TEST",
        "fiscal_year": 2025,
        "fiscal_period": "tw1",
        "industry_class": "GENERAL",
        "representation_format": "XLSX",
        "statement_scope": "CONSOLIDATED",
        "attachment_sha256": sha,
        "source_file_sha256": sha,
        "normalized_period": "Q1",
        "period_start": "2025-01-01",
        "period_end": "2025-03-31",
        "instant_date": "2025-03-31",
        "instant_status": "RECOVERED",
        "duration_status": "RECOVERED",
        "instant_evidence": [{"source_location": "sheet=1000000;B24"}],
        "duration_evidence": [{"source_location": "sheet=1000000;B23"}],
    }


def _inputs(tmp_path: Path, revisions: bool = False) -> tuple[Path, Path, Path, Path]:
    sha_old = "a" * 64
    sha_new = "b" * 64
    diagnostics_rows = [_diagnostic("old", "2025-05-01T02:00:00Z", sha_old)]
    facts_rows = [
        _fact("old", "2025-05-01T02:00:00Z", sha_old, "total_assets", "100", "instant"),
        _fact("old", "2025-05-01T02:00:00Z", sha_old, "total_liabilities", "50", "instant"),
        _fact("old", "2025-05-01T02:00:00Z", sha_old, "revenue", "10", "duration"),
    ]
    sidecar_rows = [_sidecar_row("old", sha_old)]
    if revisions:
        diagnostics_rows.append(_diagnostic("new", "2025-06-01T02:00:00Z", sha_new))
        facts_rows.extend([
            _fact("new", "2025-06-01T02:00:00Z", sha_new, "total_assets", "200", "instant"),
            _fact("new", "2025-06-01T02:00:00Z", sha_new, "total_liabilities", "50", "instant"),
            _fact("new", "2025-06-01T02:00:00Z", sha_new, "revenue", "20", "duration"),
        ])
        sidecar_rows.append(_sidecar_row("new", sha_new))
    diagnostics = tmp_path / "diagnostics.jsonl"
    facts = tmp_path / "facts.jsonl"
    sidecar = tmp_path / "period_boundaries.jsonl"
    manifest = tmp_path / "period_boundaries.MANIFEST.json"
    diagnostics_sha = _write_jsonl(diagnostics, diagnostics_rows)
    facts_sha = _write_jsonl(facts, facts_rows)
    sidecar_sha = _write_jsonl(sidecar, sidecar_rows)
    manifest.write_text(json.dumps({
        "files": {"period_boundaries.jsonl": {"sha256": sidecar_sha}},
        "source_diagnostics": {"sha256": diagnostics_sha},
        "source_fact_records": {"sha256": facts_sha},
    }, sort_keys=True), encoding="utf-8")
    return facts, diagnostics, sidecar, manifest


def test_materialization_is_pit_safe_revision_aware_and_deterministic(tmp_path: Path) -> None:
    facts, diagnostics, sidecar, manifest = _inputs(tmp_path, revisions=True)
    first = tmp_path / "first"
    second = tmp_path / "second"
    result_first = materialize_financial_feature_panel(facts, diagnostics, sidecar, manifest, first)
    result_second = materialize_financial_feature_panel(facts, diagnostics, sidecar, manifest, second)

    assert result_first["manifest_sha256"] == result_second["manifest_sha256"]
    assert result_first["artifact_hashes"] == result_second["artifact_hashes"]
    panel = pd.read_parquet(first / "feature_panel.parquet")
    assert panel[["ticker", "as_of_timestamp_utc", "feature_id", "fiscal_period"]].duplicated().sum() == 0
    assert set(panel["feature_contract_version"]) == {"financial_feature_contract_v1"}
    old = panel[(panel.as_of_timestamp_utc == "2025-05-01T02:00:00Z") & (panel.feature_id == "size_log_total_assets")]
    new = panel[(panel.as_of_timestamp_utc == "2025-06-01T02:00:00Z") & (panel.feature_id == "size_log_total_assets")]
    assert set(old.reporting_version_id) == {"old"}
    assert set(new.reporting_version_id) == {"new"}
    assert float(old.feature_value.iloc[0]) == pytest.approx(math.log(100.0))
    assert float(new.feature_value.iloc[0]) == pytest.approx(math.log(200.0))
    assert int(result_first["audit"]["as_of_contract"]["knowledge_time_violations"]) == 0
    assert result_first["audit"]["revision_audit"]["transition_count"] == 1


def test_unresolved_period_row_stays_explicit_without_blocking_valid_instant_feature(tmp_path: Path) -> None:
    facts, diagnostics, sidecar, manifest = _inputs(tmp_path)
    row = json.loads(sidecar.read_text(encoding="utf-8").splitlines()[0])
    row["duration_status"] = "UNRESOLVED"
    row["period_start"] = None
    _write_jsonl(sidecar, [row])
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_data["files"]["period_boundaries.jsonl"]["sha256"] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(manifest_data, sort_keys=True), encoding="utf-8")
    output = tmp_path / "output"
    result = materialize_financial_feature_panel(facts, diagnostics, sidecar, manifest, output)
    panel = pd.read_parquet(output / "feature_panel.parquet")
    assets = panel[panel.feature_id == "size_log_total_assets"].iloc[0]
    revenue = panel[panel.feature_id == "size_log_revenue"].iloc[0]
    assert assets.availability_status == "AVAILABLE"
    assert revenue.availability_status == "UNRESOLVED_PERIOD"
    assert pd.isna(revenue.feature_value)
    assert result["audit"]["coverage"]["knowledge_time_violations"] == 0
