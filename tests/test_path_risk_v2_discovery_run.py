from __future__ import annotations

import pandas as pd
import pytest

from idx_trade import path_risk_v2_discovery_run as run
from idx_trade.provenance import sha256_file


def _row(session: int) -> dict[str, object]:
    return {
        "ticker": f"T{session:03d}",
        "date": pd.Timestamp("2026-01-02") + pd.Timedelta(days=session),
        "signal_session_index": session,
        "universe_primary_liquid": True,
        **{column: 1.0 for column in run.PATH_RISK_V2_FEATURE_COLUMNS},
        "label_status": "NO_BARRIER_HIT",
        "first_barrier_date": pd.NaT,
        "target_tau_date": pd.NaT,
        "adverse_excursion_r": 0.5,
    }


def test_discovery_folds_are_exact_f1_to_f4() -> None:
    folds = run._folds()
    assert [fold.name for fold in folds] == ["V2F1", "V2F2", "V2F3", "V2F4"]
    assert max(fold.validation_end for fold in folds) == 984


def test_v1_model_table_hash_and_session_boundary(tmp_path, monkeypatch) -> None:
    path = tmp_path / "model_table.parquet"
    pd.DataFrame([_row(983), _row(984)]).to_parquet(path, index=False)
    monkeypatch.setattr(run, "PATH_RISK_V2_V1_MODEL_TABLE_SHA256", sha256_file(path))
    monkeypatch.setattr(run, "PATH_RISK_V2_MODEL_TABLE_ROWS", 2)
    loaded = run._read_v1_model_table(path)
    assert loaded["signal_session_index"].tolist() == [983, 984]

    bad = tmp_path / "bad.parquet"
    pd.DataFrame([_row(984), _row(985)]).to_parquet(bad, index=False)
    monkeypatch.setattr(run, "PATH_RISK_V2_V1_MODEL_TABLE_SHA256", sha256_file(bad))
    with pytest.raises(RuntimeError, match="985"):
        run._read_v1_model_table(bad)


def test_spec_blob_is_fail_closed(tmp_path, monkeypatch) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("frozen spec\n", encoding="utf-8")
    actual = run._normalized_git_blob_sha1(spec)
    monkeypatch.setattr(run, "PATH_RISK_V2_SPEC_GIT_BLOB", actual)
    assert run._assert_spec(spec) == actual
    spec.write_text("changed after freeze\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="blob mismatch"):
        run._assert_spec(spec)


def test_output_directory_is_fail_closed(tmp_path) -> None:
    output = tmp_path / "out"
    run._assert_new_or_empty(output)
    (output / "partial.txt").write_text("partial", encoding="utf-8")
    with pytest.raises(RuntimeError, match="new or empty"):
        run._assert_new_or_empty(output)
