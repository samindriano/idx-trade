from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_lbre_monthly_free_float_history.py"
SPEC = importlib.util.spec_from_file_location("run_lbre_monthly_free_float_history", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def _report() -> str:
    return "\n".join(
        [
            "Berakhir pada akhir bulan Juni - 2026",
            "Jumlah saham Free Float                         2.310.345.900       2.310.408.900",
            "Jumlah saham tercatat di Bursa per akhir bulan  7.626.663.000       7.626.663.000",
            "% Saham Free Float                              30,29                30,29",
        ]
    )


def test_position_date_requires_one_deterministic_month() -> None:
    as_of, evidence = RUNNER.parse_position_date(_report())
    assert as_of.isoformat() == "2026-06-30"
    assert evidence == ("Berakhir pada akhir bulan Juni - 2026",)

    ambiguous, _ = RUNNER.parse_position_date(
        _report() + "\nBerakhir pada akhir bulan Mei - 2026"
    )
    assert ambiguous is None


def test_parallel_document_worker_preserves_exact_parser_contract(tmp_path: Path, monkeypatch) -> None:
    text_path = tmp_path / "fixture.txt"
    text_path.write_text(_report(), encoding="utf-8")
    monkeypatch.setattr(RUNNER, "text_for_pdf", lambda _pdf, _output: text_path)
    row = {
        "candidate_id": "candidate-1",
        "ticker": "TEST",
        "announcement_no": "001/TEST/VI/2026",
        "announced_at": "2026-07-10T09:00:00",
        "title": RUNNER.KEYWORD,
        "source_url": "https://www.idx.co.id/fixture.pdf",
        "source_sha256": "a" * 64,
        "metadata_sha256": "b" * 64,
        "path": str(tmp_path / "fixture.pdf"),
        "status": "DOWNLOADED",
    }
    index, exact, audit = RUNNER._parse_one_document(7, row, tmp_path)
    assert index == 7
    assert audit is None
    assert exact is not None
    assert exact["as_of_date"] == "2026-06-30"
    assert exact["free_float_shares"] == 2_310_408_900
    assert exact["free_float_pct"] == 30.29
    assert exact["total_listed_shares"] == 7_626_663_000

