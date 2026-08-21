from __future__ import annotations

import json
from pathlib import Path

import pytest

from idx_trade.stockbit_stream_archive import StreamArchiveError
from scripts.run_stockbit_stream_capture_v2 import _validated_identity_roster_as_of


def _manifest(as_of: str) -> dict:
    return {"derivation": {"as_of_panel_date": as_of}}


def test_current_pinned_identity_roster_is_accepted() -> None:
    assert _validated_identity_roster_as_of(_manifest("2026-07-31"), "2026-08-21") == "2026-07-31"


def test_stale_identity_roster_fails_closed_before_provider_capture() -> None:
    with pytest.raises(StreamArchiveError, match="identity roster is stale"):
        _validated_identity_roster_as_of(_manifest("2026-06-01"), "2026-08-21")


def test_future_or_missing_identity_as_of_fails_closed() -> None:
    with pytest.raises(StreamArchiveError, match="after capture date"):
        _validated_identity_roster_as_of(_manifest("2026-08-22"), "2026-08-21")
    with pytest.raises(StreamArchiveError, match="as_of_panel_date"):
        _validated_identity_roster_as_of({}, "2026-08-21")


def test_production_runner_passes_validated_roster_date_to_universe_builder() -> None:
    source = Path("scripts/run_stockbit_stream_capture_v2.py").read_text(encoding="utf-8")
    assert "identity_roster_as_of = _validated_identity_roster_as_of" in source
    assert "identity_roster_as_of=identity_roster_as_of" in source
    assert '"identity_roster_age_days"' in source
    assert '"identity_roster_status"' in source


def test_repository_identity_manifest_has_current_as_of_contract() -> None:
    manifest = json.loads(Path("config/stockbit_stream_universe_v1.json").read_text(encoding="utf-8"))
    as_of = manifest["derivation"]["as_of_panel_date"]
    assert _validated_identity_roster_as_of(manifest, "2026-08-21") == as_of
