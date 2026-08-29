"""Create-only bootstrap for the canonical cloud tradability evidence set.

The cloud runner starts from an ephemeral filesystem.  Frozen
``forward_monitoring`` deliberately treats tradability tables as optional, but
the Path-A admission boundary requires the exact three canonical artifacts to
exist and be hash-bound.  This module supplies that outer operational bridge
without changing the frozen monitor, scorer, or model inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

import pandas as pd

from .forward_monitoring import _candidate_tables, _table_columns
from .provenance import sha256_file
from .security_master import (
    COVERAGE_WINDOW_COLUMNS,
    TRADABILITY_ANCHOR_COLUMNS,
    TRADABILITY_COLUMNS,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
)


TRADABILITY_RUNTIME_READY = "TRADABILITY_RUNTIME_READY"
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class _FamilySpec:
    family: str
    required_columns: tuple[str, ...]
    seed_name: str
    target_name: str
    keywords: tuple[str, ...]


_FAMILIES = (
    _FamilySpec(
        "tradability_intervals",
        TRADABILITY_COLUMNS,
        "curated_tradability_intervals.csv",
        "tradability_intervals.csv",
        ("tradability_intervals", "interval"),
    ),
    _FamilySpec(
        "tradability_coverage",
        COVERAGE_WINDOW_COLUMNS,
        "tradability_coverage_windows.csv",
        "tradability_coverage_window.csv",
        ("tradability_coverage", "coverage_window", "coverage"),
    ),
    _FamilySpec(
        "tradability_anchors",
        TRADABILITY_ANCHOR_COLUMNS,
        "tradability_anchors.csv",
        "tradability_anchor.csv",
        ("tradability_anchors", "tradability_anchor", "anchor"),
    ),
)


class TradabilityBootstrapError(RuntimeError):
    """Raised when canonical runtime tradability evidence is not provable."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_table(path: Path, family: str) -> pd.DataFrame:
    try:
        if path.suffix.lower() == ".csv":
            return pd.read_csv(path)
        return pd.read_parquet(path)
    except Exception as exc:  # pragma: no cover - exact parser varies by engine
        raise TradabilityBootstrapError(f"{family.upper()}_ARTIFACT_MALFORMED:{path}") from exc


def _canonicalize(frame: pd.DataFrame, spec: _FamilySpec, path: Path) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise TradabilityBootstrapError(f"{spec.family.upper()}_ARTIFACT_MALFORMED:{path}")
    required = set(spec.required_columns)
    if not required.issubset(frame.columns):
        raise TradabilityBootstrapError(f"{spec.family.upper()}_ARTIFACT_MALFORMED:{path}")
    try:
        if spec.family == "tradability_intervals":
            canonical = canonicalize_tradability_intervals(frame)
        elif spec.family == "tradability_coverage":
            canonical = canonicalize_coverage_windows(frame)
        else:
            canonical = canonicalize_tradability_anchors(frame)
    except (TypeError, ValueError, KeyError) as exc:
        raise TradabilityBootstrapError(f"{spec.family.upper()}_ARTIFACT_MALFORMED:{path}") from exc
    # Canonicalizers intentionally drop unusable rows for general callers.
    # Bootstrap must fail closed instead of silently repairing a runtime file.
    if len(canonical) != len(frame):
        raise TradabilityBootstrapError(f"{spec.family.upper()}_ARTIFACT_MALFORMED:{path}")
    return canonical


def _looks_like_family(path: Path, spec: _FamilySpec) -> bool:
    name = path.name.lower()
    return any(keyword in name for keyword in spec.keywords)


def _ranking(path: Path, spec: _FamilySpec) -> tuple[int, int, str, str]:
    return (
        0 if _looks_like_family(path, spec) else 1,
        len(path.parts),
        path.name.lower(),
        str(path).lower(),
    )


def _discover_existing(root: Path, spec: _FamilySpec) -> Path | None:
    candidates = _candidate_tables(root)
    named = [path for path in candidates if _looks_like_family(path, spec)]
    matches = [
        path
        for path in candidates
        if set(spec.required_columns).issubset(_table_columns(path))
    ]
    malformed_named = [path for path in named if path not in matches]
    if malformed_named:
        raise TradabilityBootstrapError(
            f"{spec.family.upper()}_ARTIFACT_MALFORMED:{malformed_named[0]}"
        )
    if not matches:
        return None
    matches.sort(key=lambda path: _ranking(path, spec))
    if len(matches) > 1 and _ranking(matches[0], spec)[:2] == _ranking(matches[1], spec)[:2]:
        raise TradabilityBootstrapError(
            f"{spec.family.upper()}_ARTIFACT_AMBIGUOUS:{matches[0]}:{matches[1]}"
        )
    return matches[0]


def _write_create_only(path: Path, payload: bytes) -> bool:
    """Publish bytes without ever overwriting an existing target.

    A same-directory hard-link publishes a fully written temporary file.  A
    platform that does not support that operation falls back to an exclusive
    target create; both paths reject a concurrent different revision.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise TradabilityBootstrapError(
                f"{path.name.upper().replace('.', '_')}_IMMUTABLE_CONFLICT:{path}"
            )
        return False

    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
            return True
        except FileExistsError:
            if path.read_bytes() != payload:
                raise TradabilityBootstrapError(
                    f"{path.name.upper().replace('.', '_')}_IMMUTABLE_CONFLICT:{path}"
                )
            return False
        except OSError:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            try:
                descriptor = os.open(path, flags, 0o600)
            except FileExistsError:
                if path.read_bytes() != payload:
                    raise TradabilityBootstrapError(
                        f"{path.name.upper().replace('.', '_')}_IMMUTABLE_CONFLICT:{path}"
                    )
                return False
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            return True
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _entry(
    spec: _FamilySpec,
    *,
    resolution: str,
    selected: Path,
    canonical: pd.DataFrame,
    code_commit: str,
    seed: Path | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "family": spec.family,
        "resolution": resolution,
        "selected_runtime_path": str(selected.resolve()),
        "selected_runtime_sha256": sha256_file(selected),
        "row_count": int(len(canonical)),
        "code_commit": code_commit,
    }
    if seed is not None:
        result["repo_source_path"] = str(seed.resolve())
        result["repo_source_sha256"] = sha256_file(seed)
    return result


def ensure_runtime_tradability_artifacts(
    runtime_root: str | Path,
    *,
    repo_root: str | Path,
    code_commit: str,
) -> dict[str, Any]:
    """Ensure all three canonical tradability artifacts exist in the runtime.

    Existing valid artifacts win and are never rewritten.  Missing families
    are copied byte-for-byte from the pinned checkout's seed.  Invalid,
    ambiguous, missing, or conflicting evidence is a hard failure.
    """

    commit = str(code_commit or "").strip().lower()
    if not _GIT_SHA_RE.fullmatch(commit):
        raise TradabilityBootstrapError("TRADABILITY_BOOTSTRAP_CODE_COMMIT_INVALID")
    runtime = Path(runtime_root).expanduser().resolve()
    tradability_root = runtime / "tradability"
    repository = Path(repo_root).expanduser().resolve()
    entries: list[dict[str, Any]] = []

    for spec in _FAMILIES:
        selected = _discover_existing(tradability_root, spec)
        if selected is not None:
            canonical = _canonicalize(_read_table(selected, spec.family), spec, selected)
            entries.append(
                _entry(
                    spec,
                    resolution="EXISTING_RUNTIME",
                    selected=selected,
                    canonical=canonical,
                    code_commit=commit,
                )
            )
            continue

        seed = repository / "config" / spec.seed_name
        if not seed.is_file():
            raise TradabilityBootstrapError(
                f"{spec.family.upper()}_SEED_MISSING:{seed}"
            )
        try:
            seed_bytes = seed.read_bytes()
        except OSError as exc:
            raise TradabilityBootstrapError(
                f"{spec.family.upper()}_SEED_READ_FAILED:{seed}"
            ) from exc
        _canonicalize(_read_table(seed, spec.family), spec, seed)
        target = tradability_root / spec.target_name
        _write_create_only(target, seed_bytes)
        selected = _discover_existing(tradability_root, spec)
        if selected is None:
            raise TradabilityBootstrapError(
                f"{spec.family.upper()}_ARTIFACT_NOT_PUBLISHED:{target}"
            )
        if selected.resolve() != target.resolve():
            raise TradabilityBootstrapError(
                f"{spec.family.upper()}_ARTIFACT_DISCOVERY_RACE:{selected}"
            )
        if selected.read_bytes() != seed_bytes:
            raise TradabilityBootstrapError(
                f"{spec.family.upper()}_ARTIFACT_HASH_MISMATCH:{selected}"
            )
        canonical = _canonicalize(_read_table(selected, spec.family), spec, selected)
        entries.append(
            _entry(
                spec,
                resolution="SEEDED_FROM_PINNED_REPO",
                selected=selected,
                canonical=canonical,
                code_commit=commit,
                seed=seed,
            )
        )

    return {
        "status": TRADABILITY_RUNTIME_READY,
        "runtime_root": str(runtime),
        "tradability_root": str(tradability_root),
        "code_commit": commit,
        "families": entries,
        "guards": {
            "outcome_accessed": False,
            "provider_accessed": False,
            "paper_state_mutated": False,
            "counter_mutated": False,
        },
    }


__all__ = [
    "TRADABILITY_RUNTIME_READY",
    "TradabilityBootstrapError",
    "ensure_runtime_tradability_artifacts",
]
