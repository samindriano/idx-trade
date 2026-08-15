from __future__ import annotations

import csv
from pathlib import Path

import pytest

from idx_trade.historical_statutory_free_float import (
    FreeFloatSourceFamily,
    replay_historical_free_float,
)
from idx_trade.historical_statutory_free_float_io import (
    HISTORICAL_FF_COLUMNS,
    load_historical_ff_csv,
)


def _row() -> dict[str, str]:
    return {
        "record_id": "bbca-2026q1-market",
        "ticker": "BBCA",
        "as_of_date": "2026-03-31",
        "published_at": "2026-05-07T12:00:00+07:00",
        "free_float_shares": "424000000",
        "free_float_pct": "42.4",
        "total_listed_shares": "1000000000",
        "source_family": "IDX_MARKET_WIDE_FF_STATUS",
        "revision_kind": "ORIGINAL",
        "supersedes_record_id": "",
        "announcement_no": "Peng-S-00011/BEI.PLP/04-2026",
        "source_url": "https://www.idx.id/StaticData/market.pdf",
        "source_sha256": "a" * 64,
        "metadata_source_sha256": "b" * 64,
        "source_row_key": "BBCA",
    }


def _write(path: Path, rows: list[dict[str, str]], header=HISTORICAL_FF_COLUMNS) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in header})


def test_loader_requires_exact_header_and_nonempty_file(tmp_path: Path) -> None:
    bad_header = tmp_path / "bad_header.csv"
    _write(bad_header, [_row()], header=HISTORICAL_FF_COLUMNS[:-1])
    with pytest.raises(ValueError, match="header mismatch"):
        load_historical_ff_csv(bad_header)

    empty = tmp_path / "empty.csv"
    _write(empty, [])
    with pytest.raises(ValueError, match="CSV is empty"):
        load_historical_ff_csv(empty)


def test_loader_preserves_market_wide_source_identity(tmp_path: Path) -> None:
    path = tmp_path / "history.csv"
    _write(path, [_row()])
    rows = load_historical_ff_csv(path)
    assert len(rows) == 1
    assert rows[0].source_family is FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS
    assert rows[0].source_row_key == "BBCA"
    assert rows[0].free_float_shares == 424_000_000
    assert replay_historical_free_float(rows).current


def test_loader_rejects_naive_knowledge_time(tmp_path: Path) -> None:
    path = tmp_path / "naive.csv"
    row = _row()
    row["published_at"] = "2026-05-07T12:00:00"
    _write(path, [row])
    with pytest.raises(ValueError, match="explicit timezone offset"):
        load_historical_ff_csv(path)


def test_loader_allows_missing_total_but_not_missing_explicit_ff(tmp_path: Path) -> None:
    path = tmp_path / "missing_total.csv"
    row = _row()
    row["total_listed_shares"] = ""
    _write(path, [row])
    parsed = load_historical_ff_csv(path)
    assert parsed[0].total_listed_shares is None

    bad = tmp_path / "missing_ff.csv"
    row = _row()
    row["free_float_shares"] = ""
    _write(bad, [row])
    with pytest.raises(ValueError, match="free_float_shares"):
        load_historical_ff_csv(bad)
