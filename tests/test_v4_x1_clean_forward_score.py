from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from idx_trade import v4_x1_clean_forward_score as clean
from idx_trade import v4_x1_forward_score as legacy


def _write_master(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False, lineterminator="\n")


def test_clean_model_namespace_and_freeze_are_distinct_from_legacy() -> None:
    assert clean.MODEL_ID == "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1"
    assert clean.MODEL_ID != legacy.MODEL_ID
    assert clean.GENERATION == "V4-X1-CLEAN"
    assert clean.EXPECTED_MODEL_MANIFEST_SHA256 == (
        "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf"
    )
    assert clean.DEFAULT_OBSERVED_BY == "2026-08-20T12:08:44+00:00"
    assert clean.PHASE_B_ACCEPTANCE_COMMIT == "ec9e8dc55ccdf458a67b63f612c8eb06660cf829"


def test_clean_model_files_and_training_contract_are_exact() -> None:
    assert clean.MODEL_FILES == {
        "control_h5": "v4_x1_clean_control_h5_final.joblib",
        "control_h10": "v4_x1_clean_control_h10_final.joblib",
        "challenger_h5": "v4_x1_clean_challenger_h5_final.joblib",
        "challenger_h10": "v4_x1_clean_challenger_h10_final.joblib",
    }
    assert clean.EXPECTED_TRAINING[("CONTROL", "H5")][:2] == (239648, 978)
    assert clean.EXPECTED_TRAINING[("CONTROL", "H10")][:2] == (237976, 974)
    assert clean.EXPECTED_TRAINING[("CHALLENGER", "H5")][:2] == (239648, 978)
    assert clean.EXPECTED_TRAINING[("CHALLENGER", "H10")][:2] == (237976, 974)
    assert len(clean.EXPECTED_TRAINING[("CONTROL", "H5")][2]) == 25
    assert len(clean.EXPECTED_TRAINING[("CHALLENGER", "H5")][2]) == 28


def test_security_master_allows_only_strictly_post_freeze_additions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = tmp_path / "baseline.csv"
    current = tmp_path / "current.csv"
    _write_master(
        baseline,
        [{"ticker": "AAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    _write_master(
        current,
        [
            {"ticker": "AAA", "listed_from": "1999-01-01", "listed_to": ""},
            {"ticker": "NEW", "listed_from": "2026-08-21", "listed_to": ""},
        ],
    )
    monkeypatch.setattr(clean, "_ACTIVE_CLEAN_PANEL", tmp_path / "unused.parquet")
    monkeypatch.setattr(clean, "_ACTIVE_CLEAN_SECURITY_MASTER", baseline)
    monkeypatch.setattr(clean, "_LEGACY_SECURITY_MASTER_PATH", lambda _paths: current)
    paths = SimpleNamespace(monitor_root=tmp_path / "monitor")

    result = clean._merged_security_master_path(paths)
    merged = pd.read_csv(result)
    assert set(merged["ticker"]) == {"AAA", "NEW"}
    # Shared baseline identity stays authoritative despite mutable current data.
    assert merged.loc[merged["ticker"].eq("AAA"), "listed_from"].iloc[0] == "2020-01-01"


def test_security_master_rejects_pre_freeze_extra_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = tmp_path / "baseline.csv"
    current = tmp_path / "current.csv"
    _write_master(
        baseline,
        [{"ticker": "AAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    _write_master(
        current,
        [
            {"ticker": "AAA", "listed_from": "2020-01-01", "listed_to": ""},
            {"ticker": "OLD", "listed_from": "2026-08-20", "listed_to": ""},
        ],
    )
    monkeypatch.setattr(clean, "_ACTIVE_CLEAN_PANEL", tmp_path / "unused.parquet")
    monkeypatch.setattr(clean, "_ACTIVE_CLEAN_SECURITY_MASTER", baseline)
    monkeypatch.setattr(clean, "_LEGACY_SECURITY_MASTER_PATH", lambda _paths: current)
    paths = SimpleNamespace(monitor_root=tmp_path / "monitor")

    with pytest.raises(RuntimeError, match="PRE_FREEZE_ADDITION"):
        clean._merged_security_master_path(paths)


def test_clean_layer_contains_no_fit_or_target_materialization_path() -> None:
    source = Path(clean.__file__).read_text(encoding="utf-8")
    assert "fit_v4_head" not in source
    assert "materialize_v4_target_ledger" not in source
    assert "evaluate_head_by_date" not in source
    assert "historical_performance_computed" not in source
