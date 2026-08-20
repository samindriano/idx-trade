from __future__ import annotations

import json
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "config" / "ranking_v4_x1_clean_prospective_score_v1.json"


def _git_blob(path: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", f"HEAD:{path}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_preparation_is_readiness_only_not_deployed() -> None:
    cfg = _cfg()
    assert cfg["schema_version"] == "ranking_v4_x1_clean_prospective_score_v1"
    assert cfg["status"] == "V4_X1_CLEAN_PROSPECTIVE_SCORE_PREPARED_LOCAL_VALIDATION_REQUIRED"
    assert cfg["deployment_authorized"] is False
    assert cfg["score_capture_authorized"] is False
    assert cfg["forward_counter_target"] == 100
    assert cfg["forward_counter_initial_expected"] == 0


def test_clean_model_and_freeze_identity_are_exact() -> None:
    cfg = _cfg()
    accepted = cfg["phase_b_acceptance"]
    assert accepted["commit"] == "ec9e8dc55ccdf458a67b63f612c8eb06660cf829"
    assert accepted["checkpoint_blob"] == "666ca21ce26248b17328d56e0505e362b2814db5"
    assert accepted["accepted_model_manifest_sha256"] == (
        "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf"
    )
    assert accepted["conservative_forward_freeze_boundary"] == "2026-08-20T12:08:44+00:00"
    assert cfg["prospective_preregistration"]["git_blob_sha1"] == (
        "f33663bc7e4d14941a12974cc453ab90ac5b85ba"
    )
    assert cfg["accepted_models"] == {
        "control_h5": "f727b10c6ea72c9ca7b447977ed4fa9cd3b5b32adb81793921c425d9085665b2",
        "control_h10": "737be8c47fe2d689dab09950a931c1339039ed8ae379b79f0bfd5a8c2e7605db",
        "challenger_h5": "d8a73d03ff72ab82826ef4e1be5e2073f6a61a5bb01b4e4268428436dc5eb082",
        "challenger_h10": "935a6f9aeaa2ca30a4016819e3848d284eb677e38153a7bd3126da0c33a9f95d",
    }


def test_representation_and_backfill_guards_are_frozen() -> None:
    cfg = _cfg()
    rep = cfg["representation"]
    boundary = cfg["prospective_boundary"]
    assert rep["clean_historical_panel_sha256"] == (
        "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e"
    )
    assert rep["clean_security_master_baseline_sha256"] == (
        "51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e"
    )
    assert boundary["canonical_eod_and_data_ready_must_both_be_strictly_after_freeze"] is True
    assert boundary["same_jakarta_date_score_required"] is True
    assert boundary["late_catchup_counter_eligible"] is False
    assert boundary["pre_freeze_backscore_authorized"] is False
    assert boundary["historical_backscore_authorized"] is False
    assert boundary["do_not_infer_first_calendar_date"] is True
    assert rep["v4_x2_session_alignment"] is False


def test_all_pinned_git_blobs_match_current_head() -> None:
    cfg = _cfg()
    mismatches = {
        path: {"actual": _git_blob(path), "expected": expected}
        for path, expected in cfg["pinned_git_blobs"].items()
        if _git_blob(path) != expected
    }
    assert mismatches == {}


def test_score_layer_hard_guards_remain_closed() -> None:
    guards = _cfg()["hard_guards"]
    assert all(value is False for value in guards.values())
