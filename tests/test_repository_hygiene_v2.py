from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "repository_hygiene_v2.py"
SPEC = importlib.util.spec_from_file_location("repository_hygiene_v2", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_archive_tag_name_is_deterministic_and_ref_safe() -> None:
    assert (
        MODULE._tag_name("research/foo/bar v1", "0123456789abcdef")
        == "archive/hygiene-v2/research-foo-bar-v1-0123456789ab"
    )


def test_deletion_plan_tag_is_bound_to_plan_sha() -> None:
    assert (
        MODULE._plan_tag_name("abcdef0123456789deadbeef")
        == "archive/hygiene-v2/deletion-plan-abcdef0123456789"
    )


def test_classification_is_explicit_keep_then_archive_then_default_delete() -> None:
    config = {
        "keep_branches": ["main", "live"],
        "archive_tag_then_delete": ["anchor"],
    }
    assert MODULE._classify("live", config)[0] == "KEEP"
    assert MODULE._classify("anchor", config)[0] == "ARCHIVE_TAG_THEN_DELETE"
    assert MODULE._classify("obsolete", config)[0] == "TOMBSTONE_THEN_DELETE"


def test_apply_uses_single_atomic_push_and_never_legacy_delete_push() -> None:
    source = inspect.getsource(MODULE._apply_command)
    assert '"push", "--atomic", "origin"' in source
    assert '"push", "origin", "--delete"' not in source
    assert "refspecs" in source


def test_archive_and_plan_tag_creation_are_semantically_hardened() -> None:
    lightweight_source = inspect.getsource(MODULE._prepare_local_lightweight_tag)
    plan_source = inspect.getsource(MODULE._prepare_local_plan_tag)
    assert '"update-ref"' in lightweight_source
    assert '"--cleanup=verbatim"' in plan_source
    assert "expected_message" in plan_source
