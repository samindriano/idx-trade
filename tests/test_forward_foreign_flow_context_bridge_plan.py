from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import idx_trade.forward_foreign_flow_context_bridge_plan as planner
from idx_trade.provenance import sha256_file


def test_planner_separates_bridge_gap_from_post_monitor_canonical_need(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calendar = tmp_path / "calendar.csv"
    calendar.write_text(
        "date\n2026-07-31\n2026-08-03\n2026-08-04\n2026-08-10\n2026-08-11\n",
        encoding="utf-8",
    )

    def fake_market(_root: Path, key: str):
        if key == "2026-08-11":
            raise RuntimeError("canonical absent")
        return pd.DataFrame(), {}

    def fake_flow(_root: Path, key: str):
        return pd.DataFrame(), {}

    monkeypatch.setattr(planner, "_read_verified_forward_market", fake_market)
    monkeypatch.setattr(planner, "_read_verified_forward_flow", fake_flow)
    monkeypatch.setattr(
        planner,
        "verify_context_bridge_session",
        lambda _root, day, **_kwargs: pd.Timestamp(day).date().isoformat() == "2026-08-10",
    )

    # Mark only Aug-11 as a present-but-invalid canonical directory.
    (tmp_path / "forward_monitoring" / "sessions" / "2026-08-11").mkdir(parents=True)

    result = planner.plan_context_bridge(
        tmp_path,
        historical_cutoff="2026-07-31",
        source_session="2026-08-11",
        official_sessions_path=calendar,
        official_sessions_sha256=sha256_file(calendar),
    )

    assert result["status"] == "CONTEXT_BRIDGE_ACTION_REQUIRED"
    assert result["bridge_capture_required"] == ["2026-08-03", "2026-08-04"]
    assert result["canonical_eod_required"] == ["2026-08-11"]
    assert result["invalid_canonical_sessions"] == ["2026-08-11"]
    aug10 = next(row for row in result["sessions"] if row["session_date"] == "2026-08-10")
    assert aug10["status"] == "BRIDGE_READY"
    assert result["provider_calls"] == 0
    assert result["writes"] == 0
    assert result["operator_counter_modified"] is False
