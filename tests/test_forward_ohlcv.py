from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import idx_trade.forward_ohlcv as forward_ohlcv_module
from idx_trade.forward_ohlcv import (
    SESSION_OHLCV_COLUMNS,
    _local_provider_row,
    enrich_session_ohlcv,
    validate_ohlcv_against_model_input,
)
from idx_trade.storage import write_parquet_atomic


SESSION = pd.Timestamp("2026-08-10")


def _model_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAAA"],
            "date": [SESSION],
            "high": [105.0],
            "low": [99.0],
            "close": [103.0],
            "volume": [1000.0],
            "regular_market_value": [103000.0],
        }
    )


def _raw_price() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAAA"],
            "date": [SESSION],
            "raw_open": [100.0],
            "raw_high": [105.0],
            "raw_low": [99.0],
            "raw_close": [103.0],
            "raw_volume": [1000.0],
        }
    )


def test_legacy_enrichment_uses_local_raw_price_and_preserves_model_input(tmp_path: Path) -> None:
    session_dir = tmp_path / "forward_monitoring" / "sessions" / SESSION.date().isoformat()
    session_dir.mkdir(parents=True)
    write_parquet_atomic(_model_input(), session_dir / "model_input.parquet")
    (session_dir / "manifest.json").write_text(
        '{"status":"DATA_READY","session_date":"2026-08-10"}',
        encoding="utf-8",
    )
    raw_dir = tmp_path / "prices" / "raw"
    raw_dir.mkdir(parents=True)
    write_parquet_atomic(_raw_price(), raw_dir / "AAAA.parquet")

    result = enrich_session_ohlcv(tmp_path, SESSION)

    assert result["status"] == "OPEN_COMPLETE"
    assert result["accepted_rows"] == 1
    artifact = pd.read_parquet(session_dir / "session_ohlcv.parquet")
    assert list(artifact.columns) == list(SESSION_OHLCV_COLUMNS)
    assert artifact.loc[0, "open"] == 100.0
    assert artifact.loc[0, "source"] == "YAHOO_YFINANCE_RAW_OHLCV"
    assert "open" not in _model_input().columns
    assert (session_dir / "open_enrichment_manifest.json").exists()


def test_legacy_enrichment_reports_missing_local_open_without_writing_partial_artifact(tmp_path: Path) -> None:
    session_dir = tmp_path / "forward_monitoring" / "sessions" / SESSION.date().isoformat()
    session_dir.mkdir(parents=True)
    write_parquet_atomic(_model_input(), session_dir / "model_input.parquet")
    (session_dir / "manifest.json").write_text(
        '{"status":"DATA_READY","session_date":"2026-08-10"}',
        encoding="utf-8",
    )

    result = enrich_session_ohlcv(tmp_path, SESSION)

    assert result["status"] == "OPEN_INCOMPLETE"
    assert result["missing_rows"] == 1
    assert result["missing_tickers"] == ["AAAA"]
    assert not (session_dir / "session_ohlcv.parquet").exists()
    assert not (session_dir / "open_enrichment_manifest.json").exists()


def test_ohlcv_validation_fails_closed_on_hlc_disagreement() -> None:
    model = _model_input()
    ohlcv = pd.DataFrame(
        [
            {
                "ticker": "AAAA",
                "session_date": SESSION,
                "open": 100.0,
                "high": 106.0,
                "low": 99.0,
                "close": 103.0,
                "volume": 1000.0,
                "source": "TEST",
                "source_ref": "test://row",
                "source_sha256": "a" * 64,
                "observed_retrieved_at_utc": None,
            }
        ]
    )

    with pytest.raises(ValueError, match="high disagrees"):
        validate_ohlcv_against_model_input(ohlcv, model, SESSION)


@pytest.mark.parametrize("reverse", [False, True])
def test_local_provider_selection_rejects_conflicting_same_session_rows(tmp_path: Path, reverse: bool) -> None:
    raw_dir = tmp_path / "prices" / "raw"
    raw_dir.mkdir(parents=True)
    rows = pd.DataFrame(
        [
            {"ticker": "AAAA", "date": SESSION, "raw_open": 100.0, "raw_high": 105.0, "raw_low": 95.0, "raw_close": 102.0, "raw_volume": 1000.0},
            {"ticker": "AAAA", "date": SESSION, "raw_open": 200.0, "raw_high": 205.0, "raw_low": 195.0, "raw_close": 202.0, "raw_volume": 2000.0},
        ]
    )
    if reverse:
        rows = rows.iloc[::-1]
    path = raw_dir / "AAAA.parquet"
    write_parquet_atomic(rows, path)
    with pytest.raises(ValueError, match="Conflicting OHLCV observations"):
        _local_provider_row(path, "AAAA", SESSION)


def test_downloaded_provider_selection_rejects_conflicting_same_session_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_dir = tmp_path / "forward_monitoring" / "sessions" / SESSION.date().isoformat()
    session_dir.mkdir(parents=True)
    write_parquet_atomic(_model_input(), session_dir / "model_input.parquet")
    (session_dir / "manifest.json").write_text(
        '{"status":"DATA_READY","session_date":"2026-08-10"}',
        encoding="utf-8",
    )
    downloaded = pd.DataFrame(
        [
            {"date": SESSION, "open": 100.0, "high": 105.0, "low": 95.0, "close": 102.0, "volume": 1000.0},
            {"date": SESSION, "open": 200.0, "high": 205.0, "low": 195.0, "close": 202.0, "volume": 2000.0},
        ]
    )
    monkeypatch.setattr(
        forward_ohlcv_module,
        "_download_in_batches",
        lambda *args, **kwargs: ({"AAAA": downloaded}, {}),
    )

    result = enrich_session_ohlcv(tmp_path, SESSION, fetch_missing=True)

    assert result["status"] == "OPEN_INCOMPLETE"
    assert result["missing_tickers"] == ["AAAA"]
    invalid = [row for row in result["diagnostics"] if row["status"] == "INVALID_PROVIDER_ROW"]
    assert len(invalid) == 1
    assert "Conflicting OHLCV observations" in invalid[0]["detail"]


def test_legacy_open_repair_allows_volume_revision_but_not_hlc_revision() -> None:
    model = _model_input()
    ohlcv = pd.DataFrame(
        [
            {
                "ticker": "AAAA",
                "session_date": SESSION,
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 103.0,
                "volume": 2000.0,
                "source": "TEST",
                "source_ref": "test://row",
                "source_sha256": "a" * 64,
                "observed_retrieved_at_utc": None,
            }
        ]
    )

    validate_ohlcv_against_model_input(ohlcv, model, SESSION, compare_volume=False)
    with pytest.raises(ValueError, match="close disagrees"):
        validate_ohlcv_against_model_input(
            ohlcv.assign(close=104.0), model, SESSION, compare_volume=False
        )
