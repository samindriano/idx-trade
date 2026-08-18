from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_v4_ca_fren_ksei_exact_replay as replay


def _rights() -> dict[str, object]:
    return {
        "transition_date": "2024-04-17",
        "transition_semantic": "OFFICIAL_KSEI_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE",
        "cum_regular_negotiated": "2024-04-16",
        "record_date": "2024-04-18",
        "distribution_date": "2024-04-19",
        "trading_start": "2024-04-22",
        "trading_end": "2024-05-06",
        "ratio": "178_OLD_TO_75_HMETD",
        "reference_no": "KSEI-7000/JKU/0424",
        "source_url": replay.KSEI_RIGHTS_SCHEDULE_URL,
        "source_sha256": replay.EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256,
    }


def _make_root(tmp_path: Path, *, transition: str = "2024-04-17") -> Path:
    root = tmp_path / "evidence"
    official = root / "raw" / "official_archive"
    ksei = root / "raw" / "ksei_rights_schedule_probe"
    official.mkdir(parents=True)
    ksei.mkdir(parents=True)
    for name in (
        "corporate_action_2024.html",
        "disclosure_2024.html",
        "merger_archive.html",
        "investor_about.html",
    ):
        (official / name).write_bytes(name.encode())
    (ksei / "ksei_rights_april_2024.html").write_bytes(b"index")
    (ksei / "fren_ksei_schedule_01.pdf").write_bytes(b"pdf")
    semantics = _rights()
    semantics["transition_date"] = transition
    (root / "fren_ksei_rights_schedule_probe.json").write_text(
        json.dumps(
            {
                "schema_version": replay.EXPECTED_PROBE_SCHEMA,
                "verified": True,
                "verified_pdf": {
                    "url": replay.KSEI_RIGHTS_SCHEDULE_URL,
                    "sha256": replay.EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256,
                    "semantics": semantics,
                },
            }
        ),
        encoding="utf-8",
    )
    return root


def _fake_sha(path: Path) -> str:
    if path.name == "ksei_rights_april_2024.html":
        return replay.EXPECTED_KSEI_RIGHTS_INDEX_SHA256
    if path.name == "fren_ksei_schedule_01.pdf":
        return replay.EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256
    return "a" * 64


def test_saved_evidence_contract_is_offline_and_exact(tmp_path, monkeypatch) -> None:
    root = _make_root(tmp_path)
    monkeypatch.setattr(replay, "sha256_file", _fake_sha)
    monkeypatch.setattr(
        replay,
        "verify_smartfren_archive_pages",
        lambda *args: {
            "mechanical_census_method": "old",
            "issuer_2024_mechanical_families": ["PMHMETD_V_RIGHTS_ISSUE"],
            "issuer_2025_terminal_family": "MERGER_SECURITY_CESSATION",
        },
    )
    monkeypatch.setattr(replay, "verify_ksei_fren_rights_schedule_pdf", lambda payload: _rights())
    monkeypatch.setattr(replay, "combined_evidence_sha", lambda payloads: "b" * 64)
    result = replay.verify_saved_evidence(root)
    assert result["rights_semantics"]["transition_date"] == "2024-04-17"
    assert result["rights_semantics"]["transition_semantic"] == "OFFICIAL_KSEI_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE"
    assert result["issuer_semantics"]["mechanical_census_method"].endswith("KSEI_OFFICIAL_RIGHTS_SCHEDULE")
    assert result["combined_evidence_sha256"] == "b" * 64


def test_saved_probe_semantic_mismatch_fails_closed(tmp_path, monkeypatch) -> None:
    root = _make_root(tmp_path, transition="2024-04-18")
    monkeypatch.setattr(replay, "sha256_file", _fake_sha)
    monkeypatch.setattr(replay, "verify_smartfren_archive_pages", lambda *args: {"mechanical_census_method": "old"})
    monkeypatch.setattr(replay, "verify_ksei_fren_rights_schedule_pdf", lambda payload: _rights())
    with pytest.raises(RuntimeError, match="PROBE_SEMANTIC_MISMATCH:transition_date"):
        replay.verify_saved_evidence(root)


def test_final_replay_expected_coverage_delta_is_frozen() -> None:
    assert replay.EXPECTED_COVERAGE_CERTIFIED == 602
    assert replay.EXPECTED_COVERAGE_UNRESOLVED == 9
    assert replay.EXPECTED_FREN_ROWS == 604
