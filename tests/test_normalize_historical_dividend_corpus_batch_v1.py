from __future__ import annotations

import json
from pathlib import Path

from scripts.normalize_historical_dividend_corpus_batch_v1 import normalize


def test_normalization_reuses_raw_bytes_and_pins_source_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "raw").mkdir(parents=True)
    payload = {
        "ResultCount": 1,
        "Replies": [
            {
                "pengumuman": {
                    "Kode_Emiten": "BBCA",
                    "Id2": "A1",
                    "NoPengumuman": "N1",
                    "TglPengumuman": "2026-01-01T10:00:00",
                    "JudulPengumuman": "Jadwal Dividen Tunai",
                    "Form_Id": "11000",
                },
                "attachments": [],
            }
        ],
    }
    raw_path = source / "raw" / "BBCA_p001.json"
    raw_path.write_text(json.dumps(payload), encoding="utf-8")
    source_manifest = {
        "schema_version": "idx_trade_historical_dividend_corpus_batch_v1",
        "status": "INCOMPLETE",
        "date_from": "2023-12-28",
        "date_to": "2026-07-17",
        "required_tickers": ["BBCA"],
    }
    (source / "DISCOVERY_MANIFEST.json").write_text(
        json.dumps(source_manifest), encoding="utf-8"
    )

    result = normalize(input_root=source, output_root=tmp_path / "normalized")
    assert result["status"] == "COMPLETE"
    assert result["source_manifest_sha256"]
    assert result["candidate_count"] == 1
    assert result["ticker_results"][0]["source_raw_sha256"]
