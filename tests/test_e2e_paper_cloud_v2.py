from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from scripts import run_e2e_paper_cloud_v1 as v1
from scripts import run_e2e_paper_cloud_v2 as v2


def test_v2_refreshes_runtime_master_before_canonical_eod_pipeline(
    tmp_path: Path, monkeypatch
) -> None:
    runtime_root = tmp_path / "forward"
    baseline = tmp_path / "baseline.csv"
    baseline.write_text("ticker,listed_from,listed_to\nAAAA,2020-01-01,\n", encoding="utf-8")
    events: list[str] = []

    def fake_refresh(runtime_root_arg, *, baseline_master, observed_at):
        assert Path(runtime_root_arg) == runtime_root
        assert Path(baseline_master) == baseline
        assert observed_at == datetime(2026, 8, 26, 11, 35, tzinfo=timezone.utc)
        output = runtime_root / "listings" / "security_master.csv"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "security_id,ticker,company_name,listed_from,listed_to,source\n"
            "IDX:AAAA:20200101,AAAA,AAAA,2020-01-01,,IDX_STOCK_LIST\n",
            encoding="utf-8",
        )
        events.append("refresh")
        return {
            "schema_version": "idx_e2e_cloud_runtime_security_master_v1",
            "security_master_path": str(output),
            "security_master_sha256": "a" * 64,
            "guards": {"outcome_accessed": False},
        }

    def fake_pipeline(runtime_root_arg, model_root_arg, **kwargs):
        del model_root_arg, kwargs
        assert (Path(runtime_root_arg) / "listings" / "security_master.csv").is_file()
        events.append("eod")
        return {"status": "PIPELINE_OK_NO_FRESH_SESSION"}

    monkeypatch.setattr(v2, "refresh_cloud_runtime_security_master", fake_refresh)
    result = v2._with_runtime_security_master(
        fake_pipeline,
        runtime_root,
        tmp_path / "model",
        clean_panel=tmp_path / "panel.parquet",
        clean_security_master=baseline,
        repo_root=tmp_path,
        observed_by="2026-08-26T11:35:00+00:00",
    )

    assert events == ["refresh", "eod"]
    assert result["status"] == "PIPELINE_OK_NO_FRESH_SESSION"


def test_v2_post_eod_result_payload_binds_refresh_evidence(monkeypatch) -> None:
    evidence = {
        "schema_version": "idx_e2e_cloud_runtime_security_master_v1",
        "security_master_sha256": "b" * 64,
        "guards": {"outcome_accessed": False},
    }
    monkeypatch.setattr(v2, "_LAST_SECURITY_MASTER_REFRESH", evidence)

    def original_builder(**kwargs):
        return {
            "stage": kwargs["stage"],
            "controller_status": "POST_EOD_PREPARED",
            "outcome_accessed": False,
        }

    result = v2._result_payload_with_refresh(
        original_builder,
        session="2026-08-26",
        stage="POST_EOD",
        started=datetime(2026, 8, 26, 11, 35, tzinfo=timezone.utc),
        finished=datetime(2026, 8, 26, 11, 36, tzinfo=timezone.utc),
        status={"controller_status": "POST_EOD_PREPARED"},
    )
    assert result["cloud_runtime_security_master_refresh"] == evidence


def test_v2_preopen_result_payload_is_unchanged_by_security_master_adapter(monkeypatch) -> None:
    monkeypatch.setattr(v2, "_LAST_SECURITY_MASTER_REFRESH", None)

    def original_builder(**kwargs):
        return {"stage": kwargs["stage"], "sentinel": 1}

    result = v2._result_payload_with_refresh(
        original_builder,
        session="2026-08-26",
        stage="PREOPEN",
        started=datetime(2026, 8, 26, 2, 3, tzinfo=timezone.utc),
        finished=datetime(2026, 8, 26, 2, 4, tzinfo=timezone.utc),
        status={"controller_status": "WAITING_OFFICIAL_OPEN"},
    )
    assert result == {"stage": "PREOPEN", "sentinel": 1}


def test_v2_run_once_restores_v1_functions_after_call(monkeypatch) -> None:
    original_pipeline = v1.run_clean_eod_pipeline
    original_result_builder = v1._result_payload

    def fake_run_once(*, phase=None, session_date=None):
        del phase, session_date
        assert v1.run_clean_eod_pipeline is not original_pipeline
        assert v1._result_payload is not original_result_builder
        return {"status": "WAITING", "controller_status": "WAITING_UPSTREAM_EOD_SCORE"}

    monkeypatch.setattr(v1, "run_once", fake_run_once)
    result = v2.run_once(phase="POST_EOD", session_date="2026-08-26")
    assert result["status"] == "WAITING"
    assert v1.run_clean_eod_pipeline is original_pipeline
    assert v1._result_payload is original_result_builder
