from __future__ import annotations

import pytest

import scripts.run_stockbit_intraday_cloud_v1 as runner


def test_real_cloud_runner_requires_exact_implementation_pin(monkeypatch):
    monkeypatch.setattr(runner, "_git_head", lambda: "a" * 40)
    monkeypatch.delenv("STOCKBIT_INTRADAY_EXPECTED_IMPLEMENTATION_REF", raising=False)
    with pytest.raises(RuntimeError, match="IMPLEMENTATION_REF_REQUIRED"):
        runner._verify_code_pin()

    monkeypatch.setenv("STOCKBIT_INTRADAY_EXPECTED_IMPLEMENTATION_REF", "not-a-sha")
    with pytest.raises(RuntimeError, match="IMPLEMENTATION_REF_INVALID"):
        runner._verify_code_pin()

    monkeypatch.setenv("STOCKBIT_INTRADAY_EXPECTED_IMPLEMENTATION_REF", "b" * 40)
    with pytest.raises(RuntimeError, match="IMPLEMENTATION_REF_MISMATCH"):
        runner._verify_code_pin()

    monkeypatch.setenv("STOCKBIT_INTRADAY_EXPECTED_IMPLEMENTATION_REF", "a" * 40)
    assert runner._verify_code_pin() == "a" * 40
