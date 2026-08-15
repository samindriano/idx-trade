from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import idx_trade.forward_foreign_flow_context_bridge_run as bridge_run
from idx_trade.provenance import sha256_file


def test_post_monitor_session_cannot_fallback_to_bridge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    day = pd.Timestamp("2026-08-11")
    calendar = tmp_path / "calendar.csv"
    calendar.write_text("date\n2026-08-10\n2026-08-11\n2026-08-12\n", encoding="utf-8")

    monkeypatch.setattr(bridge_run, "verify_context_bridge_session", lambda *_a, **_k: True)
    monkeypatch.setattr(
        bridge_run,
        "load_context_bridge_session",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("bridge must not be loaded")),
    )

    with pytest.raises(RuntimeError, match="POST_MONITOR_SESSION_REQUIRES_CANONICAL_EOD"):
        bridge_run._resolve_extension_session(
            tmp_path,
            day,
            calendar_path=calendar.resolve(),
            calendar_sha256=sha256_file(calendar),
        )
