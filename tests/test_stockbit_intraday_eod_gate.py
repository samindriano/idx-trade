from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.provenance import sha256_file
from idx_trade.stockbit_intraday_eod_gate import (
    EXPECTED_COMPLETENESS,
    StockbitIntradayGateError,
    gate_skip_evidence,
    load_verified_eod_gate,
)


SESSION = date(2026, 8, 26)


def _universe() -> pd.DataFrame:
    return pd.DataFrame({"ticker": ["BBCA", "ZERO", "BMRI"]})


def _raw(*, total: int = 2, row_date: str = "2026-08-26") -> dict[str, object]:
    return {
        "data": [
            {
                "StockCode": "BBCA",
                "Date": row_date,
                "Volume": 100,
                "Frequency": 4,
                "Value": 1_000_000,
            },
            {
                "StockCode": "ZERO",
                "Date": row_date,
                "Volume": 0,
                "Frequency": 0,
                "Value": 0,
            },
        ],
        "recordsTotal": total,
        "recordsFiltered": total,
    }


def _summary(*, negative: bool = False, row_date: str = "2026-08-26") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBCA", "ZERO"],
            "as_of_date": [row_date, row_date],
            "volume": [100, -1 if negative else 0],
            "frequency": [4, 0],
            "regular_value": [1_000_000, 0],
        }
    )


def _write_fixture(
    root: Path,
    *,
    raw: dict[str, object] | None = None,
    summary: pd.DataFrame | None = None,
    source: str = "IDX_OFFICIAL",
    completeness: str = EXPECTED_COMPLETENESS,
    declared_count: int = 2,
) -> Path:
    root.mkdir(parents=True)
    raw_path = root / "idx_stock_summary.raw.json"
    summary_path = root / "idx_stock_summary.csv"
    manifest_path = root / "manifest.json"
    raw_path.write_text(json.dumps(raw or _raw(), sort_keys=True) + "\n", encoding="utf-8")
    (summary if summary is not None else _summary()).to_csv(summary_path, index=False, lineterminator="\n")
    raw_sha = sha256_file(raw_path)
    summary_sha = sha256_file(summary_path)
    manifest = {
        "schema_version": 1,
        "status": "DATA_READY",
        "session_date": SESSION.isoformat(),
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "stock_summary_sha256": summary_sha,
        "stock_summary_raw_sha256": raw_sha,
        "stock_summary_meta": {
            "requested_date": SESSION.isoformat(),
            "source_ref": "https://www.idx.id/primary/TradingSummary/GetStockSummary?date=20260826",
            "records_total": declared_count,
            "records_filtered": declared_count,
            "rows": declared_count,
            "raw_sha256": raw_sha,
            "completeness_status": completeness,
        },
        "stock_summary_source": {
            "source": source,
            "source_ref": "https://www.idx.id/primary/TradingSummary/GetStockSummary?date=20260826",
            "session_date": SESSION.isoformat(),
            "row_count": declared_count,
            "records_total": declared_count,
            "records_filtered": declared_count,
            "completeness_status": completeness,
            "observed_available_at_utc": "2026-08-26T11:30:00+00:00",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def test_verified_eod_gate_produces_conservative_decisions(tmp_path: Path):
    root = tmp_path / "session"
    manifest_path = _write_fixture(root)
    gate = load_verified_eod_gate(
        root,
        expected_date=SESSION,
        universe=_universe(),
        expected_manifest_sha256=sha256_file(manifest_path),
    )
    decisions = gate.decisions.set_index("ticker")
    assert decisions.loc["BBCA", "gate_decision"] == "FETCH_TRADED"
    assert decisions.loc["ZERO", "gate_decision"] == "SKIP_NO_ACTIVITY"
    assert decisions.loc["BMRI", "gate_decision"] == "FETCH_MISSING_SUMMARY"
    assert bool(decisions.loc["BMRI", "would_fetch_stockbit"])
    assert gate.records_total == 2


def test_gate_skip_evidence_is_hash_bound_to_canonical_eod(tmp_path: Path):
    root = tmp_path / "session"
    _write_fixture(root)
    gate = load_verified_eod_gate(root, expected_date=SESSION, universe=_universe())
    row = gate.decisions.set_index("ticker").loc["ZERO"].to_dict()
    evidence = gate_skip_evidence(gate, row)
    assert evidence["activity_or"] is False
    assert evidence["eod_manifest_sha256"] == gate.manifest_sha256
    assert evidence["stock_summary_sha256"] == gate.stock_summary_sha256
    assert evidence["stock_summary_raw_sha256"] == gate.stock_summary_raw_sha256


def test_tampered_child_hash_fails_closed(tmp_path: Path):
    root = tmp_path / "session"
    _write_fixture(root)
    with (root / "idx_stock_summary.csv").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(StockbitIntradayGateError, match="NORMALIZED_SHA_MISMATCH"):
        load_verified_eod_gate(root, expected_date=SESSION, universe=_universe())


def test_raw_records_total_mismatch_fails_even_when_manifest_matches_new_bytes(tmp_path: Path):
    root = tmp_path / "session"
    _write_fixture(root, raw=_raw(total=3), declared_count=3)
    with pytest.raises(StockbitIntradayGateError, match="RAW_INCOMPLETE"):
        load_verified_eod_gate(root, expected_date=SESSION, universe=_universe())


def test_negative_activity_fails_closed(tmp_path: Path):
    root = tmp_path / "session"
    _write_fixture(root, summary=_summary(negative=True))
    with pytest.raises(StockbitIntradayGateError, match="ACTIVITY_NEGATIVE"):
        load_verified_eod_gate(root, expected_date=SESSION, universe=_universe())


def test_stale_raw_or_normalized_date_fails_closed(tmp_path: Path):
    raw_root = tmp_path / "raw-stale"
    _write_fixture(raw_root, raw=_raw(row_date="2026-08-25"))
    with pytest.raises(StockbitIntradayGateError, match="RAW_DATE_MISMATCH"):
        load_verified_eod_gate(raw_root, expected_date=SESSION, universe=_universe())

    normalized_root = tmp_path / "normalized-stale"
    _write_fixture(normalized_root, summary=_summary(row_date="2026-08-25"))
    with pytest.raises(StockbitIntradayGateError, match="NORMALIZED_DATE_MISMATCH"):
        load_verified_eod_gate(normalized_root, expected_date=SESSION, universe=_universe())


def test_nonofficial_or_incomplete_source_is_rejected(tmp_path: Path):
    wrong_source = tmp_path / "wrong-source"
    _write_fixture(wrong_source, source="SOMETHING_ELSE")
    with pytest.raises(StockbitIntradayGateError, match="SOURCE_IDENTITY_MISMATCH"):
        load_verified_eod_gate(wrong_source, expected_date=SESSION, universe=_universe())

    incomplete = tmp_path / "incomplete"
    _write_fixture(incomplete, completeness="UNVERIFIED")
    with pytest.raises(StockbitIntradayGateError, match="SOURCE_COMPLETENESS_INVALID"):
        load_verified_eod_gate(incomplete, expected_date=SESSION, universe=_universe())
