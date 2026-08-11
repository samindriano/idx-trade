from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade import path_risk_v2_discovery_run as run
from idx_trade.path_risk_v2 import (
    PATH_RISK_V2_CANDIDATES,
    PATH_RISK_V2_FEATURE_COLUMNS,
    PR002_CANDIDATE,
    PR003_CANDIDATE,
)
from idx_trade.provenance import sha256_file, write_manifest_atomic


def _row(
    session: int,
    *,
    ticker: str = "AAA",
    date: pd.Timestamp | None = None,
    status: str = "NO_BARRIER_HIT",
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "date": date if date is not None else pd.Timestamp("2026-01-02") + pd.Timedelta(days=session),
        "signal_session_index": session,
        "label_status": status,
        "first_barrier_date": pd.NaT,
        "adverse_excursion_r": 0.5 if status in {"TP_FIRST", "NO_BARRIER_HIT"} else 1.0,
        **{column: 1.0 for column in PATH_RISK_V2_FEATURE_COLUMNS},
    }


def _write_table(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_parquet(path, index=False)


def test_runner_import_resolves_from_this_checkout() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    expected = repo_root / "src" / "idx_trade" / "path_risk_v2_discovery_run.py"
    resolved = Path(run.__file__).resolve()

    assert resolved == expected
    assert repo_root in resolved.parents


def test_frozen_spec_and_identity_constants_are_exact() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    spec_path = repo_root / "docs" / "PATH_RISK_V2_SPEC.md"

    assert run.PATH_RISK_V2_V1_MODEL_TABLE_SHA256 == (
        "b66fc7e40f18940ae9db418331a421e0f36d23b86597500b1d3ba73a8e3777fe"
    )
    assert run.PATH_RISK_V2_CALENDAR_SHA256 == (
        "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
    )
    assert run.PATH_RISK_V2_SPEC_GIT_BLOB == "6d171d3f492b9cd15e0a176428eb9d6e4f6c20c5"
    assert run.PATH_RISK_V2_FEATURE_ORDER_SHA256 == (
        "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"
    )
    assert run._assert_spec(spec_path) == run.PATH_RISK_V2_SPEC_GIT_BLOB


def test_spec_blob_change_is_rejected(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("frozen spec\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="spec Git blob mismatch"):
        run._assert_spec(spec)


def test_model_table_requires_parquet_and_exact_sha(tmp_path: Path) -> None:
    non_parquet = tmp_path / "model_table.csv"
    non_parquet.write_text("ticker\nAAA\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frozen V1 Parquet"):
        run._read_v1_model_table(non_parquet)

    parquet = tmp_path / "model_table.parquet"
    _write_table(parquet, [_row(1)])
    with pytest.raises(RuntimeError, match="V1-model-table SHA mismatch"):
        run._read_v1_model_table(parquet)


def test_model_table_row_count_and_session_985_boundary_are_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    valid = tmp_path / "valid.parquet"
    _write_table(valid, [_row(983), _row(984, ticker="BBB")])
    monkeypatch.setattr(run, "PATH_RISK_V2_V1_MODEL_TABLE_SHA256", sha256_file(valid))
    monkeypatch.setattr(run, "PATH_RISK_V2_MODEL_TABLE_ROWS", 2)

    loaded = run._read_v1_model_table(valid)
    assert loaded["signal_session_index"].tolist() == [983, 984]

    wrong_count = tmp_path / "wrong_count.parquet"
    _write_table(wrong_count, [_row(983)])
    monkeypatch.setattr(run, "PATH_RISK_V2_V1_MODEL_TABLE_SHA256", sha256_file(wrong_count))
    with pytest.raises(RuntimeError, match="row mismatch"):
        run._read_v1_model_table(wrong_count)

    future = tmp_path / "future.parquet"
    _write_table(future, [_row(984), _row(985, ticker="BBB")])
    monkeypatch.setattr(run, "PATH_RISK_V2_V1_MODEL_TABLE_SHA256", sha256_file(future))
    monkeypatch.setattr(run, "PATH_RISK_V2_MODEL_TABLE_ROWS", 2)
    with pytest.raises(RuntimeError, match="985"):
        run._read_v1_model_table(future)


def test_model_table_duplicate_normalized_identity_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    duplicate = tmp_path / "duplicate.parquet"
    same_date = pd.Timestamp("2026-01-02")
    _write_table(
        duplicate,
        [
            _row(1, ticker="AAA", date=same_date),
            _row(2, ticker="AAA.JK", date=same_date),
        ],
    )
    monkeypatch.setattr(run, "PATH_RISK_V2_V1_MODEL_TABLE_SHA256", sha256_file(duplicate))
    monkeypatch.setattr(run, "PATH_RISK_V2_MODEL_TABLE_ROWS", 2)

    with pytest.raises(RuntimeError, match="duplicate identities"):
        run._read_v1_model_table(duplicate)


@pytest.mark.parametrize("schema_case", ["missing", "extra", "reordered"])
def test_model_table_schema_must_reject_missing_extra_or_reordered_features(
    schema_case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    columns = [
        "ticker",
        "date",
        "signal_session_index",
        "label_status",
        "first_barrier_date",
        "adverse_excursion_r",
        *PATH_RISK_V2_FEATURE_COLUMNS,
    ]
    frame = pd.DataFrame([_row(1)])
    if schema_case == "missing":
        frame = frame.drop(columns=[PATH_RISK_V2_FEATURE_COLUMNS[-1]])
    elif schema_case == "extra":
        frame["unexpected_feature"] = 1.0
    elif schema_case == "reordered":
        frame = frame[
            [
                *columns[:6],
                *reversed(PATH_RISK_V2_FEATURE_COLUMNS),
            ]
        ]
    else:  # pragma: no cover - guarded by parametrization
        raise AssertionError(schema_case)

    path = tmp_path / f"{schema_case}.parquet"
    frame.to_parquet(path, index=False)
    monkeypatch.setattr(run, "PATH_RISK_V2_V1_MODEL_TABLE_SHA256", sha256_file(path))
    monkeypatch.setattr(run, "PATH_RISK_V2_MODEL_TABLE_ROWS", 1)

    try:
        run._read_v1_model_table(path)
    except Exception:
        return
    pytest.fail(f"{schema_case} model-table schema was accepted")


def test_calendar_sha_and_coverage_are_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "calendar.csv"
    pd.DataFrame({"date": pd.date_range("2026-01-01", periods=994, freq="D")}).to_csv(
        path, index=False
    )

    monkeypatch.setattr(run, "PATH_RISK_V2_CALENDAR_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="calendar SHA mismatch"):
        run._read_calendar(path)

    monkeypatch.setattr(run, "PATH_RISK_V2_CALENDAR_SHA256", sha256_file(path))
    sessions = run._read_calendar(path)
    assert len(sessions) == 994


def test_calendar_requires_one_date_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "ambiguous_calendar.csv"
    pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=2),
            "session_date": pd.date_range("2026-01-01", periods=2),
        }
    ).to_csv(path, index=False)
    monkeypatch.setattr(run, "PATH_RISK_V2_CALENDAR_SHA256", sha256_file(path))

    with pytest.raises(ValueError, match="one date column"):
        run._read_calendar(path)


def test_output_directory_never_silently_overwrites_or_reruns(tmp_path: Path) -> None:
    output = tmp_path / "output"
    run._assert_new_or_empty(output)
    (output / ".partial.json").write_text("partial", encoding="utf-8")

    with pytest.raises(RuntimeError, match="new or empty"):
        run._assert_new_or_empty(output)

    output_file = tmp_path / "output_file"
    output_file.write_text("not a directory", encoding="utf-8")
    with pytest.raises(Exception):
        run._assert_new_or_empty(output_file)


def test_runner_candidate_and_fold_sets_are_exact() -> None:
    assert PATH_RISK_V2_CANDIDATES == (PR002_CANDIDATE, PR003_CANDIDATE)
    assert run.PATH_RISK_V2_DISCOVERY_FOLDS == ("V2F1", "V2F2", "V2F3", "V2F4")

    folds = run._folds()
    assert [fold.name for fold in folds] == ["V2F1", "V2F2", "V2F3", "V2F4"]
    assert [(fold.train_end, fold.gap_start, fold.gap_end, fold.validation_end) for fold in folds] == [
        (504, 505, 524, 624),
        (624, 625, 644, 744),
        (744, 745, 764, 864),
        (864, 865, 884, 984),
    ]
    assert not {fold.name for fold in folds} & {"V2F5", "V2F6"}


def test_runner_source_has_no_forbidden_artifact_loads() -> None:
    source_path = Path(run.__file__).resolve()
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if isinstance(owner, ast.Name) and owner.id == "joblib" and node.func.attr == "load":
            forbidden_calls.append("joblib.load")
        if isinstance(owner, ast.Name) and owner.id == "pd" and node.func.attr in {
            "read_pickle",
            "read_feather",
            "read_hdf",
        }:
            forbidden_calls.append(f"pd.{node.func.attr}")

    assert not forbidden_calls
    assert "FORWARD_OUTCOME_ACCESS_STARTED" not in source
    assert "raw H10" not in source
    assert "F5/F6" in source


def test_summary_seal_flags_and_candidate_outputs_are_false_or_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    table = pd.DataFrame(
        [
            _row(1, ticker="AAA", status="TP_FIRST"),
            _row(2, ticker="BBB", status="SL_FIRST"),
        ]
    )
    table["stop_touch_h10"] = [0, 1]
    fold = run.RankingV2Fold("V2F1", 1, 1, 2, 2, 3, 3)

    class _FakeModel:
        def fit(self, frame: pd.DataFrame, target: np.ndarray) -> "_FakeModel":
            return self

    def _fake_dump(_value: object, path: Path) -> None:
        path.write_bytes(b"synthetic model")

    def _fake_metrics(_frame: pd.DataFrame) -> dict[str, float]:
        return {
            "log_loss": 0.5,
            "brier": 0.25,
            "roc_auc": 0.6,
            "pr_auc": 0.6,
            "ece": 0.0,
        }

    def _fake_pr003_profile(_model: object, validation: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "stop_probability_h3": np.full(len(validation), 0.1),
                "stop_probability_h5": np.full(len(validation), 0.2),
                "tp_probability_h10": np.full(len(validation), 0.3),
                "survival_probability_h10": np.full(len(validation), 0.5),
                "mass_error_h10": np.zeros(len(validation)),
                "stop_probability_h10": np.full(len(validation), 0.2),
            }
        )

    monkeypatch.setattr(run, "_read_v1_model_table", lambda _path: table.copy())
    monkeypatch.setattr(run, "_read_calendar", lambda _path: pd.DatetimeIndex([]))
    monkeypatch.setattr(run, "_assert_spec", lambda _path: run.PATH_RISK_V2_SPEC_GIT_BLOB)
    monkeypatch.setattr(run, "add_stop_touch_target", lambda frame: frame.copy())
    monkeypatch.setattr(run, "add_competing_risk_event_metadata", lambda frame, _sessions: frame.copy())
    monkeypatch.setattr(run, "_folds", lambda: (fold,))
    monkeypatch.setattr(run, "_split", lambda frame, _fold: (frame.iloc[:1].copy(), frame.iloc[1:].copy()))
    monkeypatch.setattr(run, "_base_rate_predictions", lambda _train, validation: np.full(len(validation), 0.5))
    monkeypatch.setattr(
        run,
        "_fit_alpha_only_baseline",
        lambda _train, validation: (np.full(len(validation), 0.5), {"synthetic": True}),
    )
    monkeypatch.setattr(run, "probability_metrics", _fake_metrics)
    monkeypatch.setattr(run, "build_pr002_model", _FakeModel)
    monkeypatch.setattr(run, "predict_pr002_probability", lambda _model, validation: np.full(len(validation), 0.5))
    monkeypatch.setattr(
        run,
        "expand_competing_risk_training",
        lambda _train: pd.DataFrame({"cr_target": [0, 1, 2]}),
    )
    monkeypatch.setattr(run, "build_pr003_model", _FakeModel)
    monkeypatch.setattr(run, "score_pr003_cumulative_risk", _fake_pr003_profile)
    monkeypatch.setattr(run.joblib, "dump", _fake_dump)
    monkeypatch.setattr(
        run,
        "select_path_risk_v2_candidate",
        lambda _metrics: ("PATH_RISK_V2_DISCOVERY_FAIL_CLOSE", None, {"candidates": [PR002_CANDIDATE, PR003_CANDIDATE]}),
    )

    summary = run.run_discovery(
        v1_model_table_path=tmp_path / "synthetic.parquet",
        calendar_path=tmp_path / "synthetic-calendar.csv",
        spec_path=tmp_path / "synthetic-spec.md",
        output_dir=tmp_path / "output",
        code_commit="synthetic-commit",
    )

    assert summary["candidate_selection"]["candidates"] == [PR002_CANDIDATE, PR003_CANDIDATE]
    assert summary["f5_f6_path_risk_accessed"] is False
    assert summary["fresh_forward_accessed"] is False
    assert summary["forward_marker_written"] is False
    assert summary["final_ranker_modified"] is False
    assert summary["risk_integration_created"] is False
    assert summary["code_commit"] == "synthetic-commit"


def test_synthetic_manifest_and_hashes_are_deterministic(tmp_path: Path) -> None:
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(b"alpha\nbeta\n")
    crlf.write_bytes(b"alpha\r\nbeta\r\n")
    assert run._normalized_git_blob_sha1(lf) == run._normalized_git_blob_sha1(crlf)
    assert sha256_file(lf) != sha256_file(crlf)

    manifest = {"config": {"folds": ["V2F1", "V2F4"]}, "sealed": True}
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_manifest_atomic(first, manifest)
    write_manifest_atomic(second, manifest)
    assert first.read_bytes() == second.read_bytes()
    assert sha256_file(first) == sha256_file(second)
