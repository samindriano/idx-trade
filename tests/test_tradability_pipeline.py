from pathlib import Path

import pandas as pd

from idx_trade.tradability_pipeline import run_tradability_ingestion


def _write_manifest(path: Path, refs: list[str]) -> None:
    pd.DataFrame(
        [{"source_ref": ref, "announced_at": "2025-01-01"} for ref in refs]
    ).to_csv(path, index=False)


def test_clean_suspend_resume_pipeline_passes_integrity_but_not_coverage(tmp_path):
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, ["idx://suspend", "idx://resume"])

    documents = {
        "idx://suspend": (
            "Peng-SPT-00001/BEI.WAS/01-2025 Bursa melakukan penghentian sementara perdagangan "
            "saham PT Example Tbk (TEST) di Pasar Reguler dan Pasar Tunai mulai sesi I "
            "tanggal 2 Januari 2025."
        ),
        "idx://resume": (
            "Peng-UPT-00001/BEI.WAS/01-2025 Suspensi saham PT Example Tbk (TEST) di Pasar "
            "Reguler dan Pasar Tunai dibuka kembali mulai sesi I tanggal 6 Januari 2025."
        ),
    }

    def fetcher(url: str):
        return documents[url], f"hash-{url.rsplit('/', 1)[-1]}"

    output_dir = tmp_path / "out"
    report = run_tradability_ingestion(manifest_path, output_dir, fetcher=fetcher)

    assert report["passed"] is True
    assert report["coverage_complete"] is False
    assert report["event_rows"] == 4
    assert report["interval_rows"] == 2

    intervals = pd.read_csv(output_dir / "tradability_intervals.csv")
    assert set(intervals["market"]) == {"REGULAR", "CASH"}
    assert set(intervals["effective_from"]) == {"2025-01-02"}
    assert set(intervals["effective_to"]) == {"2025-01-05"}

    for name in (
        "tradability_events.csv",
        "tradability_parse_diagnostics.csv",
        "tradability_intervals.csv",
        "tradability_compile_diagnostics.csv",
        "tradability_ingestion_report.json",
    ):
        assert (output_dir / name).exists()


def test_manual_review_document_keeps_integrity_gate_closed(tmp_path):
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, ["idx://complex"])

    text = (
        "Bursa membuka penghentian sementara perdagangan saham PT Example Tbk (TEST) hanya di "
        "Pasar Negosiasi tanggal 18 Juli 2025 pukul 14.00 WIB. Selanjutnya Bursa melakukan "
        "Suspensi kembali di Seluruh Pasar pukul 14.30 WIB."
    )

    def fetcher(url: str):
        return text, "hash-complex"

    output_dir = tmp_path / "out"
    report = run_tradability_ingestion(manifest_path, output_dir, fetcher=fetcher)

    assert report["passed"] is False
    assert report["coverage_complete"] is False
    assert report["unresolved_parse_rows"] == 1
    diagnostics = pd.read_csv(output_dir / "tradability_parse_diagnostics.csv")
    assert diagnostics.loc[0, "status"] == "MANUAL_REVIEW"
    assert diagnostics.loc[0, "diagnostic"] == "MULTI_ACTION_INTRADAY_DOCUMENT"


def test_unmatched_resume_is_an_integrity_failure(tmp_path):
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(manifest_path, ["idx://resume-only"])

    text = (
        "Peng-UPT-00001/BEI.WAS/01-2025 Suspensi saham PT Example Tbk (TEST) di Pasar Reguler "
        "dibuka kembali mulai sesi I tanggal 6 Januari 2025."
    )

    def fetcher(url: str):
        return text, "hash-resume-only"

    report = run_tradability_ingestion(manifest_path, tmp_path / "out", fetcher=fetcher)
    assert report["passed"] is False
    assert report["compile_issue_rows"] == 1
