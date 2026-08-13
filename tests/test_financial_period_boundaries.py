from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from idx_trade.financial_period_boundaries import (
    _xbrl_boundaries,
    validate_period_sidecar,
)
from idx_trade.financial_feature_contract import _period_metadata


def _write_jsonl(path: Path, rows: list[dict]) -> str:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path, dict]:
    attachment_sha = "a" * 64
    version = "v1"
    diagnostic = {
        "version_id": version,
        "ticker": "TEST",
        "fiscal_year": 2025,
        "fiscal_period": "tw1",
        "scope": "CONSOLIDATED",
        "representation_format": "XLSX",
        "industry_class": "GENERAL",
        "source_attachment_sha256": attachment_sha,
    }
    fact = {
        "version_id": version,
        "ticker": "TEST",
        "fiscal_year": 2025,
        "fiscal_period": "tw1",
        "statement_scope": "CONSOLIDATED",
        "attachment_sha256": attachment_sha,
        "knowledge_at_utc": "2025-05-01T02:00:00Z",
        "fact_identity": "total_assets",
    }
    diagnostics = tmp_path / "diagnostics.jsonl"
    facts = tmp_path / "facts.jsonl"
    sidecar = tmp_path / "period_boundaries.jsonl"
    manifest = tmp_path / "MANIFEST.json"
    diagnostic_sha = _write_jsonl(diagnostics, [diagnostic])
    fact_sha = _write_jsonl(facts, [fact])
    sidecar_row = {
        **diagnostic,
        "attachment_sha256": attachment_sha,
        "normalized_period": "Q1",
        "statement_scope": "CONSOLIDATED",
        "source_file_sha256": attachment_sha,
        "instant_date": "2025-03-31",
        "period_start": "2025-01-01",
        "period_end": "2025-03-31",
        "instant_status": "RECOVERED",
        "duration_status": "RECOVERED",
        "instant_evidence": [{"source_location": "sheet=1000000;B24"}],
        "duration_evidence": [{"source_location": "sheet=1000000;B23"}],
    }
    sidecar_sha = _write_jsonl(sidecar, [sidecar_row])
    manifest.write_text(
        json.dumps(
            {
                "files": {"period_boundaries.jsonl": {"sha256": sidecar_sha}},
                "source_diagnostics": {"sha256": diagnostic_sha},
                "source_fact_records": {"sha256": fact_sha},
            }
        ),
        encoding="utf-8",
    )
    return diagnostics, facts, sidecar, manifest, sidecar_row


def test_manifest_pinned_sidecar_accepts_exact_boundary_join(tmp_path: Path) -> None:
    diagnostics, facts, sidecar, manifest, _ = _fixture_inputs(tmp_path)
    result = validate_period_sidecar(sidecar, manifest, diagnostics, facts)
    assert result["total_versions"] == 1
    assert result["fully_recovered_duration_versions"] == 1


def test_sidecar_rejects_missing_or_extra_filing_keys(tmp_path: Path) -> None:
    diagnostics, facts, sidecar, manifest, row = _fixture_inputs(tmp_path)
    sidecar.write_text(json.dumps(row) + "\n" + json.dumps({**row, "version_id": "extra"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate|key-set|manifest"):
        validate_period_sidecar(sidecar, manifest, diagnostics, facts)


def test_sidecar_rejects_reversed_boundaries(tmp_path: Path) -> None:
    diagnostics, facts, sidecar, manifest, row = _fixture_inputs(tmp_path)
    row = {**row, "period_start": "2025-04-01", "period_end": "2025-03-31"}
    _write_jsonl(sidecar, [row])
    with pytest.raises(ValueError, match="chronology"):
        validate_period_sidecar(sidecar, manifest, diagnostics, facts)


def test_xbrl_requires_exact_idx_dei_namespace_and_concept() -> None:
    body = """<html xmlns:idx-dei="http://www.idx.co.id/xbrl/taxonomy/2020-01-01/dei">
      <ix:nonNumeric name="idx-dei:CurrentPeriodStartDate" contextRef="CurrentYearInstant">January 01, 2025</ix:nonNumeric>
      <ix:nonNumeric name="idx-dei:CurrentPeriodEndDate" contextRef="CurrentYearInstant">March 31, 2025</ix:nonNumeric>
    </html>"""
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("1000000.html", body)
    result = _xbrl_boundaries(payload.getvalue())
    assert result["period_start"] == "2025-01-01"
    assert result["period_end"] == "2025-03-31"


def test_xbrl_plain_or_non_idx_dei_date_labels_are_unresolved() -> None:
    body = """<html xmlns:foo="https://example.invalid/dei">
      <ix:nonNumeric name="foo:CurrentPeriodStartDate" contextRef="CurrentYearInstant">January 01, 2025</ix:nonNumeric>
      <ix:nonNumeric name="foo:CurrentPeriodEndDate" contextRef="CurrentYearInstant">March 31, 2025</ix:nonNumeric>
    </html>"""
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("1000000.html", body)
    result = _xbrl_boundaries(payload.getvalue())
    assert result["period_start"] is None
    assert result["period_end"] is None


def test_xbrl_impossible_duration_is_fail_closed_but_instant_is_retained() -> None:
    body = """<html xmlns:idx-dei="https://www.idx.co.id/xbrl/taxonomy/2020-01-01/dei">
      <ix:nonNumeric name="idx-dei:CurrentPeriodStartDate" contextRef="CurrentYearInstant">September 27, 2024</ix:nonNumeric>
      <ix:nonNumeric name="idx-dei:CurrentPeriodEndDate" contextRef="CurrentYearInstant">June 30, 2024</ix:nonNumeric>
    </html>"""
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("1000000.html", body)
    result = _xbrl_boundaries(payload.getvalue())
    assert result["instant_date"] == "2024-06-30"
    assert result["period_start"] is None
    assert result["period_end"] == "2024-06-30"
    assert result["duration_status"] == "INVALID_BOUNDARY_CHRONOLOGY"


def test_unresolved_sidecar_never_falls_back_to_untrusted_inline_duration() -> None:
    row = {
        "fiscal_period_covered": {
            "period_kind": "duration",
            "period_start": "2025-01-01",
            "period_end": "2025-03-31",
        }
    }
    boundary = {
        "duration_status": "INVALID_BOUNDARY_CHRONOLOGY",
        "period_start": None,
        "period_end": "2025-03-31",
    }
    start, end, instant, verified, _, _ = _period_metadata(row, boundary)
    assert (start, end, instant, verified) == (None, None, None, False)
