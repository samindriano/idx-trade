from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _calls(path: Path, function_name: str) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == function_name
    ]


def test_phase_scripts_pass_attestation_only_to_phase_verifier() -> None:
    for name in ("run_e2e_paper_post_eod_v1.py", "run_e2e_paper_preopen_v1.py"):
        path = REPO_ROOT / "scripts" / name
        attest_calls = _calls(path, "attest_deployment")
        phase_calls = _calls(path, "require_phase_attestation")
        assert len(attest_calls) == 1
        assert len(phase_calls) == 1
        assert not any(keyword.arg == "attestation_path" for keyword in attest_calls[0].keywords)
        assert any(keyword.arg == "attestation_path" for keyword in phase_calls[0].keywords)


def test_phase_scripts_bind_runtime_identity_into_orchestration() -> None:
    expected = {
        "implementation_branch",
        "implementation_commit",
        "runtime_config_sha256",
        "entrypoint_sha256",
    }
    for name, function_name in (
        ("run_e2e_paper_post_eod_v1.py", "prepare_post_eod"),
        ("run_e2e_paper_preopen_v1.py", "execute_preopen"),
        ("run_e2e_paper_post_eod_v2.py", "prepare_post_eod"),
        ("run_e2e_paper_preopen_v2.py", "execute_preopen"),
    ):
        calls = _calls(REPO_ROOT / "scripts" / name, function_name)
        assert len(calls) == 1
        assert expected <= {keyword.arg for keyword in calls[0].keywords}
