from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from research.alpha_official_idx_directory_audit_v1 import (
    audit_official_profiles,
    load_anchor_tickers,
    load_prior_official,
    load_ticker_files,
)


def _write_profile(path: Path, code: str, name: str, date: str) -> None:
    path.write_text(
        json.dumps(
            {
                "recordsTotal": 2,
                "recordsFiltered": 2,
                "data": [
                    {"KodeEmiten": code, "NamaEmiten": name, "TanggalPencatatan": date, "Status": 0, "Sektor": "X"},
                    {"KodeEmiten": "BBB", "NamaEmiten": "Beta", "TanggalPencatatan": "2020-01-02T00:00:00", "Status": 0, "Sektor": "Y"},
                ],
            }
        ),
        encoding="utf-8",
    )


def test_official_profile_shape_and_dates_are_audited(tmp_path: Path) -> None:
    path = tmp_path / "profiles.json"
    _write_profile(path, "AAA", "Alpha", "2020-01-01T00:00:00")
    result = audit_official_profiles(path)
    assert result["codes"] == {"AAA", "BBB"}
    assert result["listing_min"] == "2020-01-01"
    assert result["listing_max"] == "2020-01-02"
    assert result["duplicate_codes"] == []
    assert result["status_values"] == ["0"]


def test_comparison_surfaces_are_normalized_to_uppercase(tmp_path: Path) -> None:
    ticker_root = tmp_path / "eod"
    ticker_root.mkdir()
    (ticker_root / "aaa.csv").write_text("Date,Ticker\n2020-01-01,AAA\n", encoding="utf-8")
    (ticker_root / "BBB.csv").write_text("Date,Ticker\n2020-01-01,BBB\n", encoding="utf-8")
    assert load_ticker_files(ticker_root) == {"AAA", "BBB"}

    anchor = tmp_path / "anchor.csv"
    pd.DataFrame({"ticker": ["aaa", "Cntx"]}).to_csv(anchor, index=False)
    assert load_anchor_tickers(anchor) == {"AAA", "CNTX"}

    prior = tmp_path / "prior.json"
    prior.write_text(
        json.dumps(
            {
                "data": [
                    {"Code": "aaa", "ListingDate": "2020-01-01T00:00:00"},
                    {"Code": "BBB", "ListingDate": "2020-01-02T00:00:00"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load_prior_official(prior)["codes"] == {"AAA", "BBB"}
