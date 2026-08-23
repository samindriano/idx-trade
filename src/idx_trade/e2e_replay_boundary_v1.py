"""Static boundary evidence for outcome-blind E2E replay entrypoints.

This audit is intentionally narrow.  It does not claim to instrument an
arbitrary process; it proves that the replay entrypoint and the frozen
verifier/orchestrator modules it invokes contain no direct provider, protected
outcome, or model-fit/rescore import/call surface.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Iterable


_PROVIDER_IMPORT_PREFIXES = (
    "idx_trade.providers",
    "requests",
    "httpx",
    "urllib.request",
    "websocket",
)
_OUTCOME_IMPORT_PREFIXES = (
    "idx_trade.outcomes",
    "idx_trade.forward_outcome",
)
_MODEL_IMPORT_PREFIXES = (
    "xgboost",
    "sklearn",
    "lightgbm",
)
_PROTECTED_MARKERS = ("FORWARD_OUTCOME_ACCESS_STARTED",)
_MODEL_CALL_NAMES = {"fit", "refit", "rescore", "predict"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_name(node: ast.AST) -> str:
    if isinstance(node, ast.Import):
        return ",".join(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return node.module or ""
    return ""


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def replay_boundary_static_audit_v1(
    source_paths: Iterable[str | Path],
    *,
    source_kind: str,
) -> dict[str, object]:
    """Return hash-pinned, AST-derived replay boundary evidence."""

    paths = tuple(sorted({Path(path).expanduser().resolve() for path in source_paths}))
    files: list[dict[str, object]] = []
    violations: list[dict[str, str]] = []
    for path in paths:
        if not path.is_file():
            violations.append({"category": "missing_source", "path": str(path)})
            continue
        text = path.read_text(encoding="utf-8")
        files.append({"path": str(path), "sha256": _sha256(path)})
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            violations.append({
                "category": "syntax_error",
                "path": str(path),
                "detail": str(exc),
            })
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = _module_name(node)
                if module.startswith(_PROVIDER_IMPORT_PREFIXES):
                    violations.append({
                        "category": "provider_import",
                        "path": str(path),
                        "detail": module,
                    })
                if module.startswith(_OUTCOME_IMPORT_PREFIXES):
                    violations.append({
                        "category": "protected_outcome_import",
                        "path": str(path),
                        "detail": module,
                    })
                if module.startswith(_MODEL_IMPORT_PREFIXES):
                    violations.append({
                        "category": "model_import",
                        "path": str(path),
                        "detail": module,
                    })
            elif isinstance(node, ast.Call):
                name = _call_name(node)
                if name in _MODEL_CALL_NAMES:
                    violations.append({
                        "category": "model_call",
                        "path": str(path),
                        "detail": name,
                    })
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if any(marker in node.value for marker in _PROTECTED_MARKERS):
                    violations.append({
                        "category": "protected_outcome_marker",
                        "path": str(path),
                        "detail": "FORWARD_OUTCOME_ACCESS_STARTED",
                    })

    counts = {
        "provider_call_count": sum(
            row["category"] == "provider_import" for row in violations
        ),
        "protected_outcome_read_count": sum(
            row["category"] in {"protected_outcome_import", "protected_outcome_marker"}
            for row in violations
        ),
        "model_refit_count": sum(
            row["category"] == "model_call" and row["detail"] in {"fit", "refit"}
            for row in violations
        ),
        "model_rescore_count": sum(
            row["category"] == "model_call" and row["detail"] in {"predict", "rescore"}
            for row in violations
        ),
    }
    evidence = {
        "schema_version": "idx_trade_e2e_replay_boundary_static_audit_v1",
        "method": "AST_IMPORT_CALL_AND_MARKER_AUDIT",
        "source_kind": source_kind,
        "audited_files": files,
        "violations": violations,
        **counts,
        "by_construction": not violations,
    }
    evidence["audit_sha256"] = hashlib.sha256(
        (json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    if violations:
        raise RuntimeError("E2E_REPLAY_BOUNDARY_STATIC_AUDIT_FAILED")
    return evidence


__all__ = ["replay_boundary_static_audit_v1"]
