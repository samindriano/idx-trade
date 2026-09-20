from __future__ import annotations

from pathlib import Path

import pandas as pd

from research.alpha_public_eod_source_coverage_v1 import (
    exact_key_coverage,
    summarize_dataset_saham,
    summarize_ipo,
    summarize_pholenk,
)


def test_pholenk_inventory_exposes_snapshot_sparsity_and_zero_volume(tmp_path: Path) -> None:
    root = tmp_path / "pholenk"
    root.mkdir()
    (root / "AAA.csv").write_text(
        "Date,Ticker,Name,Volume,Open,High,Low,Close,ListedShares,Remarks\n"
        "2025-01-02,AAA,Alpha,0,0,10,0,10,100,X\n"
        "2025-01-03,AAA,Alpha,2,10,11,9,10,200,Y\n",
        encoding="utf-8",
    )
    result, dates = summarize_pholenk(root)
    assert result["file_count"] == 1
    assert result["row_count"] == 2
    assert result["zero_volume_rows"] == 1
    assert result["any_zero_ohlc_rows"] == 1
    assert result["files_with_listed_share_changes"] == 1
    assert dates["AAA"] == {"2025-01-02", "2025-01-03"}


def test_dataset_saham_inventory_is_explicitly_scoped_to_one_folder(tmp_path: Path) -> None:
    root = tmp_path / "semua"
    root.mkdir()
    (root / "AAA.csv").write_text(
        "date,delisting_date\n2024-01-02,\n2024-01-03,\n",
        encoding="utf-8",
    )
    result, dates = summarize_dataset_saham(root)
    assert result["file_count"] == 1
    assert result["row_count"] == 2
    assert result["non_null_delisting_date_cells"] == 0
    assert dates["AAA"] == {"2024-01-02", "2024-01-03"}


def test_exact_key_coverage_does_not_convert_source_absence_into_population_claim() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB"],
            "date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-01"]),
        }
    )
    result = exact_key_coverage(frame, "ticker", "date", {"AAA": {"2025-01-01"}})
    assert result == {"rows": 3, "found": 1, "missing": 2, "fraction": 1 / 3}


def test_ipo_metadata_can_explain_a_snapshot_gap_without_becoming_a_universe_contract(tmp_path: Path) -> None:
    root = tmp_path / "stock"
    root.mkdir()
    (root / "BACH.json").write_text(
        '{"ipo_status":"Waiting For Offering","company_name":"PT Bach Multi Global Tbk.",'
        '"book_building_opening":"22/06/2026","book_building_closing":"24/06/2026",'
        '"listing_date":""}',
        encoding="utf-8",
    )
    info = tmp_path / "information.json"
    info.write_text(
        '{"updated_at":"28 June 2026","count":{"stocks":1},"new":{"stocks":["BACH"]}}',
        encoding="utf-8",
    )
    result = summarize_ipo(root, info)
    assert result["declared_new_stocks"] == ["BACH"]
    assert result["rows"]["BACH"]["listing_date"] == ""
