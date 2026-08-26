from __future__ import annotations

from pathlib import Path

from idx_trade.e2e_paper_cloud_runtime_v1 import LocalConditionalStore
from scripts.smoke_e2e_cloud_conditional_s3_v1 import run_smoke


def test_conditional_s3_smoke_mechanism_preserves_create_only_contract(
    tmp_path: Path,
) -> None:
    result = run_smoke(LocalConditionalStore(tmp_path / "store"))
    assert result["status"] == "PASS"
    assert result["first_write_created"] is True
    assert result["identical_replay_created"] is False
    assert result["conflicting_write_rejected"] is True
