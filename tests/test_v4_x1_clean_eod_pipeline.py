from __future__ import annotations

from pathlib import Path

from idx_trade import v4_x1_clean_eod_pipeline as clean_pipeline
from idx_trade import v4_x1_clean_forward_score as clean_x1
from idx_trade import v4_x1_eod_pipeline as legacy_pipeline


def test_clean_pipeline_swaps_score_namespace_process_locally(monkeypatch, tmp_path: Path) -> None:
    original = legacy_pipeline.x1
    configured: list[tuple[object, object]] = []

    monkeypatch.setattr(
        clean_x1,
        "configure_clean_inputs",
        lambda panel, master: configured.append((panel, master)),
    )

    def fake_run(runtime_root, model_root, *, repo_root, batch_size, observed_by):
        assert legacy_pipeline.x1 is clean_x1
        assert observed_by == clean_x1.DEFAULT_OBSERVED_BY
        return {"status": "PIPELINE_OK_NO_ELIGIBLE_SAME_DAY_X1_SCORE"}

    monkeypatch.setattr(legacy_pipeline, "run_eod_v4_x1_pipeline", fake_run)
    result = clean_pipeline.run_clean_eod_pipeline(
        tmp_path / "runtime",
        tmp_path / "models",
        clean_panel=tmp_path / "panel.parquet",
        clean_security_master=tmp_path / "master.csv",
        repo_root=tmp_path / "repo",
    )
    assert configured == [(tmp_path / "panel.parquet", tmp_path / "master.csv")]
    assert result["clean_model_id"] == clean_x1.MODEL_ID
    assert result["clean_generation"] == clean_x1.GENERATION
    assert legacy_pipeline.x1 is original


def test_clean_pipeline_preserves_existing_100_session_counter_contract() -> None:
    assert legacy_pipeline.X1_FORWARD_TARGET == 100
    assert clean_x1.MODEL_ID != "V4_X1_GEOMETRY3_PROSPECTIVE"


def test_clean_pipeline_has_no_second_provider_or_capture_implementation() -> None:
    source = Path(clean_pipeline.__file__).read_text(encoding="utf-8")
    assert "run_eod_catchup" not in source
    assert "requests." not in source
    assert "httpx." not in source
    assert "yfinance" not in source.lower()
    assert "fit_v4_head" not in source
