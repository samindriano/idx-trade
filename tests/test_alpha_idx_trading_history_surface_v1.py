import json
from pathlib import Path

import pytest

from research.alpha_idx_trading_history_surface_v1 import (
    audit_raw_file,
    discover_codes,
    summarize_raw,
)


def _write_raw(root: Path, code: str = "TEST") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{code}.json"
    path.write_text(
        json.dumps(
            {
                "KodeEmiten": code,
                "replies": [
                    {
                        "Date": "2024-01-02T00:00:00",
                        "StockCode": code,
                        "Previous": 10,
                        "OpenPrice": 0,
                        "High": 11,
                        "Low": 9,
                        "Close": 10,
                        "Volume": 0,
                        "Value": 0,
                        "Frequency": 0,
                        "ListedShares": 100,
                        "TradebleShares": 80,
                        "ForeignBuy": 1,
                        "ForeignSell": 2,
                        "Remarks": "X",
                        "DelistingDate": "",
                    },
                    {
                        "Date": "2024-01-03T00:00:00",
                        "StockCode": code,
                        "Previous": 10,
                        "OpenPrice": 10,
                        "High": 12,
                        "Low": 10,
                        "Close": 11,
                        "Volume": 100,
                        "Value": 1100,
                        "Frequency": 3,
                        "ListedShares": 120,
                        "TradebleShares": 90,
                        "ForeignBuy": 0,
                        "ForeignSell": 0,
                        "Remarks": "X",
                        "DelistingDate": "",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_audit_preserves_zero_trade_and_share_transition_semantics(tmp_path: Path):
    result = audit_raw_file(_write_raw(tmp_path))
    assert result["rows"] == 2
    assert result["unique_dates"] == 2
    assert result["zero_volume_rows"] == 1
    assert result["zero_open_rows"] == 1
    assert result["foreign_nonzero_rows"] == 1
    assert result["listed_shares_distinct"] == 2
    assert result["missing_required_field_rows"] == 0


def test_summarize_requires_raw_json(tmp_path: Path):
    with pytest.raises(ValueError):
        summarize_raw(tmp_path)


def test_discover_codes_rejects_non_ticker_files(tmp_path: Path):
    (tmp_path / "BBCA.csv").write_text("x", encoding="utf-8")
    (tmp_path / "bad-name.csv").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        discover_codes(tmp_path)
