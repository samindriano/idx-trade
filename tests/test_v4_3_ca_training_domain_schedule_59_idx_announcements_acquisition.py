from __future__ import annotations

import importlib.util
import json
from pathlib import Path


RUNNER = Path("scripts/run_v4_3_ca_training_domain_schedule_59_idx_announcements_acquisition.py")


def _load_runner():
    spec = importlib.util.spec_from_file_location("idx_announcement_runner", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_api_payload_requires_idx_reply_shape() -> None:
    runner = _load_runner()
    value = runner.parse_api_payload(
        json.dumps({"ResultCount": 1, "Replies": [{"pengumuman": {}, "attachments": []}]}).encode()
    )
    assert len(value["Replies"]) == 1


def test_announcement_identity_uses_official_fields() -> None:
    runner = _load_runner()
    item = {
        "pengumuman": {
            "NoPengumuman": "001/BEI/2024",
            "Kode_Emiten": "ABCD",
            "TglPengumuman": "2024-01-02T00:00:00",
        }
    }
    assert runner.announcement_identity(item) == (
        "001/BEI/2024",
        "ABCD",
        "2024-01-02T00:00:00",
    )


def test_runner_is_non_admissive_and_has_no_model_or_target_materializer() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    forbidden = (
        "materialize_v4_target_ledger",
        "HistGradientBoostingRegressor",
        "fit_v4_head(",
        "score_v4_head(",
        "compute_v4_3_model_eval",
        "window_continuity(",
        "resolve_event_document_evidence(",
    )
    for token in forbidden:
        assert token not in source
    assert "IDX_GET_ANNOUNCEMENT" in source
    assert '"semantic_admission_performed": False' in source


def test_runner_refuses_existing_output_before_provider_session_creation() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    refusal = source.index("REFUSE_OVERWRITE_EXISTING_OUTPUT")
    session = source.index("session = make_session(config)")
    assert refusal < session
