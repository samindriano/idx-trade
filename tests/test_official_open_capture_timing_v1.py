from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from idx_trade.official_open_capture_timing_v1 import (
    OfficialOpenCaptureTimingError,
    require_timestamp_in_slot_window,
    validate_source_manifest_timing,
)
from idx_trade.official_open_evidence_v1 import JAKARTA


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_official_open_cloud_capture_v3.py"


def _dt(hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(2026, 9, 2, hour, minute, second, tzinfo=JAKARTA)


def test_slot_window_accepts_due_and_rejects_pre_due_or_cutoff() -> None:
    assert require_timestamp_in_slot_window(
        session_date="2026-09-02", slot="0902", observed_at=_dt(9, 2)
    ) == _dt(9, 2)
    assert require_timestamp_in_slot_window(
        session_date="2026-09-02", slot="0902", observed_at=_dt(9, 7, 59)
    ) == _dt(9, 7, 59)

    with pytest.raises(OfficialOpenCaptureTimingError, match="BEFORE_SLOT_DUE"):
        require_timestamp_in_slot_window(
            session_date="2026-09-02", slot="0902", observed_at=_dt(9, 1, 59)
        )
    with pytest.raises(OfficialOpenCaptureTimingError, match="WINDOW_EXPIRED"):
        require_timestamp_in_slot_window(
            session_date="2026-09-02", slot="0902", observed_at=_dt(9, 8)
        )


def test_final_0922_window_is_bounded_to_0923() -> None:
    assert require_timestamp_in_slot_window(
        session_date="2026-09-02", slot="0922", observed_at=_dt(9, 22, 59)
    ) == _dt(9, 22, 59)
    with pytest.raises(OfficialOpenCaptureTimingError, match="WINDOW_EXPIRED"):
        require_timestamp_in_slot_window(
            session_date="2026-09-02", slot="0922", observed_at=_dt(9, 23)
        )


def test_source_manifest_timing_is_checked_before_archive_handoff(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "session_date": "2026-09-02",
                "capture_timestamp_jakarta": "2026-09-02T09:18:00+07:00",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(OfficialOpenCaptureTimingError, match="WINDOW_EXPIRED"):
        validate_source_manifest_timing(
            manifest_path=manifest,
            session_date="2026-09-02",
            slot="0912",
        )


def test_runner_orders_provenance_and_timing_before_store_and_provider_archive() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    provenance = text.index("provenance = trusted_runner_provenance")
    runner_timing = text.index("require_runner_start_in_slot_window")
    archive_call = text.index("result = capture_and_archive_official_open")
    store = text.index("store=build_official_open_store_from_env()")
    assert provenance < runner_timing < archive_call < store
    assert "capture_fn=timely_capture" in text
    assert "validate_source_manifest_timing" in text
