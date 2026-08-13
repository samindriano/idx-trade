from __future__ import annotations

import hashlib
import json
from pathlib import Path

from idx_trade.financial_fact_table import run_marketwide_census

from test_financial_fact_table import _xlsx_fixture


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_marketwide_census_streams_pit_ready_rows_and_keeps_exclusions(tmp_path: Path) -> None:
    reclassification_root = tmp_path / "reclassification"
    attachments_root = tmp_path / "attachments-root"
    output_root = tmp_path / "output"
    (attachments_root / "attachments").mkdir(parents=True)
    reclassification_root.mkdir()

    payload = _xlsx_fixture()
    relative_attachment = "attachments/report_TEST_2025_tw1.xlsx"
    (attachments_root / relative_attachment).write_bytes(payload)
    rows = [
        {
            "ticker": "TEST",
            "year": 2025,
            "period": "tw1",
            "scope": "CONSOLIDATED",
            "pit_ready": True,
            "prior_chain_gates_pass": True,
            "file_hash_matches_chain": True,
            "representation_format": "XLSX",
            "publication_at_utc": "2025-05-01T02:00:00Z",
            "source_attachment_path": relative_attachment,
            "source_attachment_sha256": _sha256(payload),
            "source_refs": ["IDX/TEST/1"],
        },
        {
            "ticker": "BLOCKED",
            "year": 2025,
            "period": "tw1",
            "scope": "UNRESOLVED",
            "pit_ready": False,
            "prior_chain_gates_pass": False,
            "file_hash_matches_chain": True,
            "representation_format": "XLSX",
            "resolver_detail": "scope evidence absent",
        },
    ]
    rows_bytes = ("".join(json.dumps(row) + "\n" for row in rows)).encode("utf-8")
    (reclassification_root / "scope_reclassification_rows.jsonl").write_bytes(rows_bytes)

    result = run_marketwide_census(
        reclassification_root,
        attachments_root,
        output_root,
        expected_pit_ready_count=1,
        expected_source_row_count=2,
        expected_source_rows_sha256=_sha256(rows_bytes),
    )
    assert result["pit_ready_filings_processed"] == 1
    assert result["network_calls"] == 0
    assert result["protected_outcomes_accessed"] is False
    assert result["exclusions"] == {"SCOPE_UNRESOLVED": 1}
    assert result["fact_status_counts"]["EXTRACTED"] == 2
    coverage = json.loads((output_root / "coverage.json").read_text(encoding="utf-8"))
    assert coverage["by_fact"]["total_assets"]["extracted"] == 1
    assert coverage["by_fact"]["revenue"]["missing"] == 1
    manifest = json.loads((output_root / "MANIFEST.json").read_text(encoding="utf-8"))
    assert set(manifest["files"]) == {
        "fact_records.jsonl",
        "filing_diagnostics.jsonl",
        "coverage.json",
        "exclusions.json",
        "summary.json",
    }
