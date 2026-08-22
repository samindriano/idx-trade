import json
from pathlib import Path

import pytest

import idx_trade.official_open_evidence_v1 as module


def _payload():
    return json.dumps(
        {
            "data": [
                {
                    "StockCode": "AAA",
                    "Date": "2026-08-24T00:00:00",
                    "OpenPrice": 1000,
                    "FirstTrade": 1010,
                }
            ],
            "recordsTotal": 1,
            "recordsFiltered": 1,
        }
    ).encode()


def test_certification_crash_does_not_leave_partial_final_session(monkeypatch, tmp_path):
    final = tmp_path / "official_open" / "2026-08-24"

    def fail_parquet(frame, path):
        raise RuntimeError("synthetic parquet crash")

    monkeypatch.setattr(module, "write_parquet_atomic", fail_parquet)
    with pytest.raises(RuntimeError, match="synthetic parquet crash"):
        module.certify_official_open_raw_response(
            _payload(),
            session_date="2026-08-24",
            output_dir=final,
        )

    assert not final.exists()
    assert list(final.parent.glob(".2026-08-24.*.stage")) == []
