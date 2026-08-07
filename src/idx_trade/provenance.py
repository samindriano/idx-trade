from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Any, Iterable


DEFAULT_PACKAGES = ("numpy", "pandas", "pyarrow", "requests", "yfinance", "pytest")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def installed_versions(packages: Iterable[str] = DEFAULT_PACKAGES) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def source_fingerprints(paths: Iterable[Path]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for path in paths:
        resolved = Path(path)
        result[str(resolved)] = sha256_file(resolved) if resolved.exists() else None
    return result


def environment_manifest(
    source_paths: Iterable[Path] = (),
    config: dict[str, Any] | None = None,
    data_snapshots: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a reproducibility manifest for each research run.

    V1 froze model/config code but not the Python/dependency environment. V2
    records exact installed versions and hashes of every supplied code/data
    snapshot used by a run.
    """

    manifest: dict[str, Any] = {
        "python": {
            "version": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "packages": installed_versions(),
        "source_sha256": source_fingerprints(source_paths),
        "config": config or {},
        "data_snapshot_sha256": data_snapshots or {},
    }
    canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    manifest["manifest_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return manifest


def write_manifest_atomic(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    temporary.replace(path)
