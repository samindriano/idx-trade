from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_inc001_vendor_sample_contract_v1 import VendorSampleContractError, validate_sample


SHA = "a" * 64


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sample(tmp_path: Path) -> Path:
    scope = [
        {"identity_id": "SEC-A", "event_family": "STOCK_SPLIT", "interval_start": "2021-01-01", "interval_end": "2021-12-31"},
        {"identity_id": "SEC-B", "event_family": "STOCK_SPLIT", "interval_start": "2021-01-01", "interval_end": "2021-12-31"},
    ]
    coverage = [
        {**scope[0], "coverage_status": "EVENTS_PRESENT", "knowledge_asof": "2022-01-01T00:00:00Z", "observed_through": "2022-01-02T00:00:00Z", "source_ref": "vendor://coverage/a", "source_sha256": SHA},
        {**scope[1], "coverage_status": "NO_EVENT", "knowledge_asof": "2022-01-01T00:00:00Z", "observed_through": "2022-01-02T00:00:00Z", "source_ref": "vendor://coverage/b", "source_sha256": SHA},
    ]
    snapshot = [
        {"identity_id": "SEC-A", "event_id": "EV-1", "event_family": "STOCK_SPLIT", "version": "1", "announcement_time": "2021-06-01T00:00:00Z", "effective_date": "2021-06-10", "source_ref": "vendor://event/1", "source_sha256": SHA}
    ]
    final_snapshot = list(snapshot)
    deltas = [
        {"sequence": "1", "op": "U", "event_id": "EV-1", "identity_id": "SEC-A", "event_family": "STOCK_SPLIT", "version": "2", "previous_version": "1", "announcement_time": "2021-06-02T00:00:00Z", "effective_date": "2021-06-11", "source_ref": "vendor://event/1-v2", "source_sha256": SHA},
        {"sequence": "2", "op": "D", "event_id": "EV-1", "identity_id": "SEC-A", "event_family": "STOCK_SPLIT", "version": "3", "previous_version": "2", "announcement_time": "2021-06-03T00:00:00Z", "effective_date": "2021-06-12", "source_ref": "vendor://event/1-v3", "source_sha256": SHA},
        {"sequence": "3", "op": "I", "event_id": "EV-1", "identity_id": "SEC-A", "event_family": "STOCK_SPLIT", "version": "1", "previous_version": "", "announcement_time": "2021-06-04T00:00:00Z", "effective_date": "2021-06-10", "source_ref": "vendor://event/1-reinsert", "source_sha256": SHA},
    ]
    # The final state is the reinserted version, so the sample exercises U/D/I
    # while retaining deterministic full-to-delta replay.
    final_snapshot = [dict(deltas[-1], op=None, sequence=None, previous_version=None)]
    for row in final_snapshot:
        row.pop("op", None)
        row.pop("sequence", None)
        row.pop("previous_version", None)
    for name, rows in {"scope.csv": scope, "coverage.csv": coverage, "snapshot.csv": snapshot, "final_snapshot.csv": final_snapshot, "deltas.csv": deltas}.items():
        _write_csv(tmp_path / name, rows)
    manifest = {
        "schema_version": "INC001_VENDOR_SAMPLE_CONTRACT_V1",
        "source_id": "VENDOR-FIXTURE",
        "source_version": "fixture-1",
        "coverage_start": "2021-01-01",
        "coverage_end": "2021-12-31",
        "observed_through": "2022-01-02T00:00:00Z",
        "knowledge_asof": "2022-01-01T00:00:00Z",
        "coverage_complete": True,
    }
    for stem, filename, rows in (("scope", "scope.csv", scope), ("coverage", "coverage.csv", coverage), ("snapshot", "snapshot.csv", snapshot), ("final_snapshot", "final_snapshot.csv", final_snapshot), ("deltas", "deltas.csv", deltas)):
        manifest[f"{stem}_sha256"] = _sha(tmp_path / filename)
        manifest[f"{stem}_row_count"] = len(rows)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return tmp_path


def test_valid_sample_checks_scope_no_event_and_replay(tmp_path: Path) -> None:
    result = validate_sample(_sample(tmp_path))
    assert result["status"] == "PASS"
    assert result["explicit_no_event_units"] == 1
    assert result["delta_rows"] == 3
    assert result["final_snapshot_events"] == 1


def test_empty_delta_stream_is_valid_when_snapshot_is_unchanged(tmp_path: Path) -> None:
    root = _sample(tmp_path)
    snapshot = list(csv.DictReader((root / "snapshot.csv").open(encoding="utf-8")))
    delta_columns = list(csv.DictReader((root / "deltas.csv").open(encoding="utf-8")).fieldnames or [])
    _write_csv(root / "final_snapshot.csv", snapshot)
    _write_csv(root / "deltas.csv", [], fieldnames=delta_columns)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["final_snapshot_sha256"] = _sha(root / "final_snapshot.csv")
    manifest["final_snapshot_row_count"] = len(snapshot)
    manifest["deltas_sha256"] = _sha(root / "deltas.csv")
    manifest["deltas_row_count"] = 0
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = validate_sample(root)
    assert result["status"] == "PASS"
    assert result["delta_rows"] == 0


def test_missing_coverage_unit_fails_closed(tmp_path: Path) -> None:
    root = _sample(tmp_path)
    rows = list(csv.DictReader((root / "coverage.csv").open(encoding="utf-8")))[:1]
    _write_csv(root / "coverage.csv", rows)
    with pytest.raises(VendorSampleContractError, match="MANIFEST_HASH_MISMATCH:coverage.csv"):
        validate_sample(root)


def test_no_event_without_provenance_fails_closed(tmp_path: Path) -> None:
    root = _sample(tmp_path)
    rows = list(csv.DictReader((root / "coverage.csv").open(encoding="utf-8")))
    rows[1]["source_sha256"] = ""
    _write_csv(root / "coverage.csv", rows)
    with pytest.raises(VendorSampleContractError, match="MANIFEST_HASH_MISMATCH:coverage.csv"):
        validate_sample(root)


def test_future_announcement_is_not_admitted(tmp_path: Path) -> None:
    root = _sample(tmp_path)
    rows = list(csv.DictReader((root / "snapshot.csv").open(encoding="utf-8")))
    rows[0]["announcement_time"] = "2022-01-02T00:00:00Z"
    _write_csv(root / "snapshot.csv", rows)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["snapshot_sha256"] = _sha(root / "snapshot.csv")
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(VendorSampleContractError, match="EVENT_PUBLISHED_AFTER_KNOWLEDGE_ASOF"):
        validate_sample(root)


def test_delta_precondition_and_revision_lineage_fail_closed(tmp_path: Path) -> None:
    root = _sample(tmp_path)
    rows = list(csv.DictReader((root / "deltas.csv").open(encoding="utf-8")))
    rows[0]["previous_version"] = "7"
    _write_csv(root / "deltas.csv", rows)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["deltas_sha256"] = _sha(root / "deltas.csv")
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(VendorSampleContractError, match="INVALID_DELTA_PRECONDITION"):
        validate_sample(root)


def test_naive_timestamp_fails_closed(tmp_path: Path) -> None:
    root = _sample(tmp_path)
    rows = list(csv.DictReader((root / "coverage.csv").open(encoding="utf-8")))
    rows[0]["knowledge_asof"] = "2022-01-01T00:00:00"
    _write_csv(root / "coverage.csv", rows)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["coverage_sha256"] = _sha(root / "coverage.csv")
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(VendorSampleContractError, match="NAIVE_TIMESTAMP"):
        validate_sample(root)
