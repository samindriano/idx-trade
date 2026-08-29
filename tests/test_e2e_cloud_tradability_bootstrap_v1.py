from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.e2e_cloud_tradability_bootstrap_v1 import (
    TRADABILITY_RUNTIME_READY,
    TradabilityBootstrapError,
    ensure_runtime_tradability_artifacts,
)
from idx_trade.e2e_paper_cloud_runtime_v1 import (
    build_runtime_snapshot,
    restore_runtime_snapshot,
)
from idx_trade.security_master import (
    COVERAGE_WINDOW_COLUMNS,
    TRADABILITY_ANCHOR_COLUMNS,
    TRADABILITY_COLUMNS,
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
    existence_state,
    tradability_state,
)
from idx_trade.states import ExistenceState, TradabilityState


REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_COMMIT = "a" * 40


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frame_payload(columns: tuple[str, ...], rows: list[dict[str, object]]) -> bytes:
    return pd.DataFrame(rows, columns=list(columns)).to_csv(index=False).encode("utf-8")


def _valid_payload(family: str) -> bytes:
    if family == "tradability_intervals":
        return _frame_payload(
            TRADABILITY_COLUMNS,
            [
                {
                    "ticker": "AAAA",
                    "market": "REGULAR",
                    "state": "ACTIVE",
                    "effective_from": "2020-01-01",
                    "effective_to": "",
                    "announced_at": "2020-01-01",
                    "source": "TEST",
                    "source_ref": "test://interval",
                }
            ],
        )
    if family == "tradability_coverage":
        return _frame_payload(
            COVERAGE_WINDOW_COLUMNS,
            [
                {
                    "market": "REGULAR",
                    "effective_from": "2020-01-01",
                    "effective_to": "2026-12-31",
                    "source": "TEST",
                    "is_complete": True,
                    "discovery_basis": "TEST_COMPLETE",
                    "left_boundary_basis": "TEST_BOUNDARY",
                }
            ],
        )
    return _frame_payload(
        TRADABILITY_ANCHOR_COLUMNS,
        [
            {
                "ticker": "AAAA",
                "market": "REGULAR",
                "as_of_date": "2026-08-28",
                "state": "ACTIVE",
                "source": "TEST",
                "source_ref": "test://anchor",
                "evidence_type": "TEST_SNAPSHOT",
            }
        ],
    )


def _result_by_family(result: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(item["family"]): item for item in result["families"]}  # type: ignore[index]


def test_fresh_runtime_seeds_exact_bytes_without_inventing_rows(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    result = ensure_runtime_tradability_artifacts(
        runtime,
        repo_root=REPO_ROOT,
        code_commit=CODE_COMMIT,
    )

    assert result["status"] == TRADABILITY_RUNTIME_READY
    families = _result_by_family(result)
    expected_rows = {
        "tradability_intervals": 1,
        "tradability_coverage": 0,
        "tradability_anchors": 0,
    }
    for family, seed_name in (
        ("tradability_intervals", "curated_tradability_intervals.csv"),
        ("tradability_coverage", "tradability_coverage_windows.csv"),
        ("tradability_anchors", "tradability_anchors.csv"),
    ):
        seed = REPO_ROOT / "config" / seed_name
        item = families[family]
        selected = Path(str(item["selected_runtime_path"]))
        assert item["resolution"] == "SEEDED_FROM_PINNED_REPO"
        assert selected.read_bytes() == seed.read_bytes()
        assert item["selected_runtime_sha256"] == _sha(selected)
        assert item["repo_source_sha256"] == _sha(seed)
        assert item["row_count"] == expected_rows[family]
    assert families["tradability_coverage"]["row_count"] == 0
    assert families["tradability_anchors"]["row_count"] == 0


@pytest.mark.parametrize(
    "family,columns",
    [
        ("tradability_intervals", TRADABILITY_COLUMNS),
        ("tradability_coverage", COVERAGE_WINDOW_COLUMNS),
        ("tradability_anchors", TRADABILITY_ANCHOR_COLUMNS),
    ],
)
def test_existing_valid_runtime_artifact_is_preserved(
    tmp_path: Path, family: str, columns: tuple[str, ...]
) -> None:
    runtime = tmp_path / "runtime"
    target = runtime / "tradability" / "existing.csv"
    payload = _valid_payload(family)
    target.parent.mkdir(parents=True)
    target.write_bytes(payload)

    result = ensure_runtime_tradability_artifacts(
        runtime,
        repo_root=REPO_ROOT,
        code_commit=CODE_COMMIT,
    )
    item = _result_by_family(result)[family]
    assert item["resolution"] == "EXISTING_RUNTIME"
    assert Path(str(item["selected_runtime_path"])) == target.resolve()
    assert target.read_bytes() == payload
    assert item["selected_runtime_sha256"] == _sha(target)
    assert set(columns)  # documents the canonical schema used by this case


def test_ambiguous_runtime_candidates_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "tradability"
    root.mkdir(parents=True)
    payload = _valid_payload("tradability_intervals")
    (root / "a.csv").write_bytes(payload)
    (root / "b.csv").write_bytes(payload)

    with pytest.raises(TradabilityBootstrapError, match="TRADABILITY_INTERVALS_ARTIFACT_AMBIGUOUS"):
        ensure_runtime_tradability_artifacts(
            tmp_path / "runtime",
            repo_root=REPO_ROOT,
            code_commit=CODE_COMMIT,
        )


def test_malformed_runtime_artifact_is_not_replaced_by_seed(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "tradability"
    root.mkdir(parents=True)
    (root / "tradability_intervals.csv").write_text("ticker,wrong\nAAAA,bad\n", encoding="utf-8")

    with pytest.raises(TradabilityBootstrapError, match="TRADABILITY_INTERVALS_ARTIFACT_MALFORMED"):
        ensure_runtime_tradability_artifacts(
            tmp_path / "runtime",
            repo_root=REPO_ROOT,
            code_commit=CODE_COMMIT,
        )
    assert (root / "tradability_intervals.csv").read_text(encoding="utf-8") == "ticker,wrong\nAAAA,bad\n"


def test_missing_seed_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(TradabilityBootstrapError, match="TRADABILITY_INTERVALS_SEED_MISSING"):
        ensure_runtime_tradability_artifacts(
            tmp_path / "runtime",
            repo_root=tmp_path / "empty-repo",
            code_commit=CODE_COMMIT,
        )


def test_cntb_suspended_fallback_uses_seeded_interval_without_point_row(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    result = ensure_runtime_tradability_artifacts(
        runtime,
        repo_root=REPO_ROOT,
        code_commit=CODE_COMMIT,
    )
    families = _result_by_family(result)
    intervals = canonicalize_tradability_intervals(
        pd.read_csv(Path(str(families["tradability_intervals"]["selected_runtime_path"])))
    )
    coverage = canonicalize_coverage_windows(
        pd.read_csv(Path(str(families["tradability_coverage"]["selected_runtime_path"])))
    )
    anchors = canonicalize_tradability_anchors(
        pd.read_csv(Path(str(families["tradability_anchors"]["selected_runtime_path"])))
    )
    master = build_security_master(
        pd.DataFrame([{"ticker": "CNTB", "listed_from": "2010-01-01", "listed_to": pd.NaT}]),
        pd.DataFrame(columns=["ticker", "listed_from", "listed_to"]),
    )

    assert existence_state(master, "CNTB", pd.Timestamp("2026-08-28")) is ExistenceState.LISTED
    assert tradability_state(
        intervals,
        coverage,
        "CNTB",
        pd.Timestamp("2026-08-28"),
        anchors=anchors,
    ) is TradabilityState.SUSPENDED


def test_same_session_active_point_precedes_empty_propagation_tables(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    root = runtime / "tradability"
    root.mkdir(parents=True)
    (root / "tradability_intervals.csv").write_bytes(_valid_payload("tradability_intervals"))
    result = ensure_runtime_tradability_artifacts(
        runtime,
        repo_root=REPO_ROOT,
        code_commit=CODE_COMMIT,
    )
    families = _result_by_family(result)
    intervals = canonicalize_tradability_intervals(
        pd.read_csv(Path(str(families["tradability_intervals"]["selected_runtime_path"])))
    )
    coverage = canonicalize_coverage_windows(
        pd.read_csv(Path(str(families["tradability_coverage"]["selected_runtime_path"])))
    )
    anchors = canonicalize_tradability_anchors(
        pd.read_csv(Path(str(families["tradability_anchors"]["selected_runtime_path"])))
    )
    assert coverage.empty and anchors.empty
    assert tradability_state(
        intervals,
        coverage,
        "AAAA",
        pd.Timestamp("2026-08-28"),
        anchors=anchors,
    ) is TradabilityState.ACTIVE


def test_snapshot_restore_preserves_bootstrapped_artifacts_byte_identically(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    ensure_runtime_tradability_artifacts(runtime, repo_root=REPO_ROOT, code_commit=CODE_COMMIT)
    source_files = sorted((runtime / "tradability").iterdir())
    expected = {path.name: path.read_bytes() for path in source_files}
    snapshot, snapshot_sha, _ = build_runtime_snapshot({"forward": runtime})

    restored = tmp_path / "restored"
    restore_runtime_snapshot(snapshot, {"forward": restored}, expected_sha256=snapshot_sha)
    actual = {
        path.name: path.read_bytes() for path in sorted((restored / "tradability").iterdir())
    }
    assert actual == expected
    assert all(path.stat().st_size >= 0 for path in source_files)
