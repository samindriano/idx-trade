from pathlib import Path


def test_official_open_task_has_only_post_auction_retry_triggers_and_logon_catchup():
    root = Path(__file__).parents[1]
    text = (root / "scripts" / "install_official_open_capture_task.ps1").read_text(
        encoding="utf-8"
    )
    for clock in ("09:02", "09:07", "09:12", "09:17", "09:22"):
        assert f'-At "{clock}"' in text
    assert "New-ScheduledTaskTrigger -AtLogOn" in text
    assert "StartWhenAvailable" in text
    assert "MultipleInstances IgnoreNew" in text
    assert "IDXTrade-E2E-OfficialOpen" in text
    assert "IDXTrade-ForwardOpenArchive" not in text
    assert "DIRECT_IDX_THEN_ZAPI_RAW_V1" in text
    assert "Zapi raw IDX passthrough only on direct transport failure" in text


def test_headless_runner_invokes_only_same_session_official_open_runtime():
    root = Path(__file__).parents[1]
    text = (root / "scripts" / "run_official_open_capture.ps1").read_text(encoding="utf-8")
    assert "idx_trade.official_open_capture_runtime_v2" in text
    assert "idx_trade.official_open_capture_runtime_v1" not in text
    assert "finance:idx" not in text
    assert "finance:stockbit" not in text
    assert "forward_open_archive" not in text
