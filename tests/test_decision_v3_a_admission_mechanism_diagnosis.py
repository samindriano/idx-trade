from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import idx_trade.decision_v3_a_admission_mechanism_diagnosis as diag
from idx_trade.decision_v3_structural_source import sha256_file


def _row(**overrides):
    base = {
        "ticker": "AAA",
        "entry_index": 10,
        "entry_date": "2026-01-10",
        "entry_class": "A_SOFT",
        "current_rank": 7,
        "previous_rank": 13,
        "rank_delta_current_minus_previous": -6,
        "rank_t_minus_2": 18,
        "rank_t_minus_3": 20,
        "top10_run_including_entry": 1,
        "top20_run_including_entry": 3,
        "last3_top10_count": 1,
        "last3_top20_count": 3,
        "soft_rank_gap": 9,
        "duration_sessions": 4,
        "one_session_holding": False,
        "completed": True,
        "right_censored": False,
        "eventual_severe_exit": False,
        "next_session_observable": True,
        "next_session_severe_exit": False,
        "current_rank_bucket": "7-10",
        "previous_rank_bucket": "11-20",
        "top10_run_bucket": "1",
        "top20_run_bucket": ">=3",
    }
    base.update(overrides)
    return base


def test_contract_is_frozen_and_hash_pinned():
    repo_root = Path(__file__).resolve().parents[1]
    path = diag.verify_admission_mechanism_contract(repo_root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["execution_authorized"] is False
    assert payload["forbidden"]["gap_threshold_search_or_sweep"] is True
    assert payload["forbidden"]["new_gap_cutoff_recommendation"] is True


def test_conditional_gap_summary_uses_protective_sign_convention():
    frame = pd.DataFrame(
        [
            _row(soft_rank_gap=12, next_session_severe_exit=False),
            _row(ticker="BBB", soft_rank_gap=10, next_session_severe_exit=False),
            _row(ticker="CCC", soft_rank_gap=5, next_session_severe_exit=True),
            _row(ticker="DDD", soft_rank_gap=7, next_session_severe_exit=True),
        ]
    )
    result = diag._conditional_gap_summary(frame, "next_session_severe_exit")
    assert result["nonsevere"]["mean"] == pytest.approx(11.0)
    assert result["severe"]["mean"] == pytest.approx(6.0)
    assert result["severe_minus_nonsevere_mean_gap"] == pytest.approx(-5.0)


def test_within_session_concordance_counts_larger_gap_on_nonsevere_as_protective():
    frame = pd.DataFrame(
        [
            _row(ticker="AAA", soft_rank_gap=12, next_session_severe_exit=False),
            _row(ticker="BBB", soft_rank_gap=8, next_session_severe_exit=False),
            _row(ticker="CCC", soft_rank_gap=6, next_session_severe_exit=True),
        ]
    )
    result = diag._build_within_session_concordance(frame)
    assert len(result) == 1
    row = result.iloc[0]
    assert int(row["discordant_outcome_pairs"]) == 2
    assert int(row["larger_gap_on_nonsevere_pairs"]) == 2
    assert float(row["protective_pair_share_excluding_ties"]) == pytest.approx(1.0)


def test_stratified_gap_outcomes_preserves_censoring_denominators():
    frame = pd.DataFrame(
        [
            _row(ticker="AAA", soft_rank_gap=12, next_session_severe_exit=False),
            _row(ticker="BBB", soft_rank_gap=6, next_session_severe_exit=True),
            _row(
                ticker="CCC",
                soft_rank_gap=11,
                next_session_observable=False,
                next_session_severe_exit=None,
                completed=False,
                right_censored=True,
                eventual_severe_exit=None,
            ),
        ]
    )
    result = diag._build_stratified_gap_outcomes(frame)
    block = result.loc[
        result["dimension"].eq("current_rank") & result["stratum"].eq("7-10")
    ].iloc[0]
    assert int(block["entries"]) == 3
    assert int(block["next_observable"]) == 2
    assert int(block["completed"]) == 2
    assert float(block["next_severe_minus_nonsevere_mean_gap"]) == pytest.approx(-6.0)


def test_load_parent_verifies_manifest_and_artifact_hashes(tmp_path, monkeypatch):
    frame = pd.DataFrame(
        [
            _row(ticker="AAA", entry_class="A_SOFT", soft_rank_gap=9),
            _row(
                ticker="BBB",
                entry_class="A_VACANCY",
                current_rank=3,
                previous_rank=10,
                rank_delta_current_minus_previous=-7,
                soft_rank_gap=None,
                current_rank_bucket="1-3",
                previous_rank_bucket="1-10",
            ),
        ]
    )
    csv_path = tmp_path / "paired_entries.csv"
    frame.to_csv(csv_path, index=False)
    manifest = {
        "status": diag.EXPECTED_PARENT_STATUS,
        "scientific_boundary": {
            "decision_v4_implemented_or_replayed": False,
            "returns_or_outcomes_accessed": False,
        },
        "artifacts": {"paired_entries.csv": sha256_file(csv_path)},
    }
    manifest_path = tmp_path / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    monkeypatch.setattr(diag, "EXPECTED_PARENT_MANIFEST_SHA256", sha256_file(manifest_path))
    monkeypatch.setattr(diag, "EXPECTED_COUNTS", {"A_SOFT": 1, "A_VACANCY": 1})
    monkeypatch.setattr(diag, "EXPECTED_PAIRED_SESSIONS", 1)

    loaded, loaded_manifest = diag.load_same_session_parent(tmp_path)
    assert len(loaded) == 2
    assert loaded_manifest["status"] == diag.EXPECTED_PARENT_STATUS

    csv_path.write_text(csv_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(Exception, match="A_ADMISSION_PARENT_ENTRIES_SHA_CHANGED"):
        diag.load_same_session_parent(tmp_path)
