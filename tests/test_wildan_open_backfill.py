import json

import pandas as pd

from idx_trade.wildan_open_backfill import (
    WILDAN_SOURCE_ID,
    apply_accepted_open_backfill,
    audit_existing_open_overlap,
    load_wildan_archive,
    official_missing_open_evidence,
    parse_wildan_stock_csv,
    read_wildan_archive_info,
)
from idx_trade.secondary_open_witness import cross_validate_secondary_open_witness


def _write_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)


def _panel():
    return pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "date": "2025-02-20",
                "open": 100.0,
                "high": 110.0,
                "low": 95.0,
                "close": 105.0,
                "volume": 1000.0,
                "open_available": True,
                "open_evidence_status": "IDX_PUBLIC_STOCK_SUMMARY_OPEN_OPTIONAL",
                "price_provenance": "idx://20250220",
            },
            {
                "ticker": "TEST",
                "date": "2025-02-21",
                "open": None,
                "high": 112.0,
                "low": 101.0,
                "close": 108.0,
                "volume": 1200.0,
                "open_available": False,
                "open_evidence_status": "OPEN_UNAVAILABLE",
                "price_provenance": "idx://20250221",
            },
        ]
    )


def test_parse_wildan_stock_csv_supports_current_open_price_schema(tmp_path):
    path = tmp_path / "TEST.csv"
    _write_csv(
        path,
        [
            {
                "date": "2025-02-21",
                "open_price": 104,
                "high": 112,
                "low": 101,
                "close": 108,
            }
        ],
    )
    parsed = parse_wildan_stock_csv(path, ticker="test", source_commit="abc123")
    assert parsed.loc[0, "ticker"] == "TEST"
    assert parsed.loc[0, "secondary_open"] == 104
    assert parsed.loc[0, "secondary_high"] == 112
    assert "abc123" in parsed.loc[0, "secondary_source_ref"]


def test_archive_info_is_metadata_not_hard_coverage_boundary(tmp_path):
    root = tmp_path / "wildan"
    data_root = root / "Saham" / "Semua"
    data_root.mkdir(parents=True)
    (root / "info.json").write_text(json.dumps({"last_update": "2024-07-19"}), encoding="utf-8")
    _write_csv(
        data_root / "TEST.csv",
        [
            {
                "date": "2025-02-21",
                "open_price": 104,
                "high": 112,
                "low": 101,
                "close": 108,
            }
        ],
    )
    assert read_wildan_archive_info(root)["last_update"] == "2024-07-19"
    rows, coverage = load_wildan_archive(
        root,
        {"TEST"},
        source_commit="abc123",
        start="2021-04-29",
        end="2026-07-31",
    )
    assert len(rows) == 1
    assert rows.loc[0, "date"] == pd.Timestamp("2025-02-21")
    assert coverage.loc[0, "last_date"] == pd.Timestamp("2025-02-21")


def test_exact_hlc_secondary_open_fills_only_missing_open():
    panel = _panel()
    secondary = pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "date": pd.Timestamp("2025-02-21"),
                "secondary_open": 104.0,
                "secondary_high": 112.0,
                "secondary_low": 101.0,
                "secondary_close": 108.0,
                "secondary_source_ref": "wildan://TEST/20250221",
            }
        ]
    )
    official = official_missing_open_evidence(panel)
    accepted, diagnostics = cross_validate_secondary_open_witness(official, secondary)
    assert len(accepted) == 1
    assert diagnostics.loc[0, "status"] == "ACCEPTED"

    filled = apply_accepted_open_backfill(panel, accepted, source_commit="abc123")
    first = filled[filled["date"].eq(pd.Timestamp("2025-02-20"))].iloc[0]
    second = filled[filled["date"].eq(pd.Timestamp("2025-02-21"))].iloc[0]
    assert first["open"] == 100.0
    assert first["open_source"] == "EXISTING_PANEL"
    assert second["open"] == 104.0
    assert second["open_available"]
    assert second["open_source"] == WILDAN_SOURCE_ID
    assert second["open_validation_status"] == "HLC_EXACT_AND_OPEN_IN_RANGE"


def test_hlc_mismatch_is_rejected_and_open_stays_null():
    panel = _panel()
    secondary = pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "date": pd.Timestamp("2025-02-21"),
                "secondary_open": 104.0,
                "secondary_high": 113.0,
                "secondary_low": 101.0,
                "secondary_close": 108.0,
                "secondary_source_ref": "wildan://TEST/20250221",
            }
        ]
    )
    official = official_missing_open_evidence(panel)
    accepted, diagnostics = cross_validate_secondary_open_witness(official, secondary)
    assert accepted.empty
    assert diagnostics.loc[0, "diagnostic"] == "CROSS_SOURCE_PRICE_MISMATCH_HIGH"
    filled = apply_accepted_open_backfill(panel, accepted, source_commit="abc123")
    assert pd.isna(filled.loc[filled["date"].eq(pd.Timestamp("2025-02-21")), "open"].iloc[0])


def test_known_open_overlap_audit_reports_open_and_hlc_match():
    panel = _panel()
    secondary = pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "date": pd.Timestamp("2025-02-20"),
                "secondary_open": 100.0,
                "secondary_high": 110.0,
                "secondary_low": 95.0,
                "secondary_close": 105.0,
                "secondary_source_ref": "wildan://TEST/20250220",
            }
        ]
    )
    audit = audit_existing_open_overlap(panel, secondary)
    assert len(audit) == 1
    assert bool(audit.loc[0, "hlc_exact"])
    assert bool(audit.loc[0, "open_exact"])


def test_missing_archive_file_is_reported_not_fabricated(tmp_path):
    root = tmp_path / "wildan"
    (root / "Saham" / "Semua").mkdir(parents=True)
    rows, coverage = load_wildan_archive(root, {"NOPE"}, source_commit="abc123")
    assert rows.empty
    assert coverage.loc[0, "status"] == "FILE_MISSING"
