import hashlib
import json
import csv
from pathlib import Path


ROOT = Path(__file__).parents[1]
REGISTRY = ROOT / "artifacts" / "registry" / "ARTIFACT_REGISTRY_V1.json"
SCHEMA = ROOT / "artifacts" / "registry" / "ARTIFACT_REGISTRY_V1.schema.json"


def test_artifact_registry_is_self_consistent_and_path_safe():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert registry["registry_id"] == schema["$id"]
    assert registry["schema_version"] == 1
    assert len(registry["groups"]) > 0
    actions = {"PUSH_TO_GIT", "KEEP_EXTERNAL", "PUSH_SUMMARY_OR_MANIFEST_ONLY"}
    assert {group["recommended_action"] for group in registry["groups"]} <= actions
    serialized = json.dumps(registry)
    assert "D:\\" not in serialized
    assert "C:\\Users\\" not in serialized
    assert registry["inventory_snapshot"]["primary_worktree_untracked_frontend_excluded"] is True


def test_artifact_drop_zones_are_documented():
    for relative in (
        "artifacts/README.md",
        "artifacts/manifests/README.md",
        "artifacts/schemas/README.md",
        "artifacts/fixtures/README.md",
    ):
        assert (ROOT / relative).is_file()


def test_promoted_artifacts_are_tracked_hash_pinned_and_payload_safe():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    promoted = registry["promoted_artifacts"]

    assert len(promoted) == registry["promotion_run"]["promoted_count"]
    assert len({entry["git_path"] for entry in promoted}) == len(promoted)
    assert sum(entry["promoted_size_bytes"] for entry in promoted) == registry["promotion_run"]["promoted_bytes"]

    forbidden_suffixes = (".parquet", ".pkl", ".joblib", ".bin", ".zip", ".xlsx", ".xls", ".db", ".sqlite")
    for entry in promoted:
        git_path = entry["git_path"]
        source_path = entry["source_relative_path"]
        assert not Path(git_path).is_absolute()
        assert not Path(source_path).is_absolute()
        assert ":\\" not in git_path and ":/" not in git_path
        assert ":\\" not in source_path and ":/" not in source_path
        assert not git_path.lower().endswith(forbidden_suffixes)

        artifact_path = ROOT / git_path
        assert artifact_path.is_file()
        assert artifact_path.stat().st_size == entry["promoted_size_bytes"]
        digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        assert digest == entry["promoted_sha256"]
        assert len(entry["source_sha256"]) == 64
        assert len(entry["promoted_sha256"]) == 64

        if entry["promotion_method"] == "EXACT_COPY":
            assert entry["source_size_bytes"] == entry["promoted_size_bytes"]
            assert entry["source_sha256"] == entry["promoted_sha256"]


def test_promotion_csv_matches_registry_paths_and_hashes():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = list(csv.DictReader((ROOT / "docs/artifact_governance/ARTIFACT_PROMOTION_V1.csv").open(encoding="utf-8", newline="")))
    assert len(rows) == len(registry["promoted_artifacts"])

    registry_by_path = {entry["git_path"]: entry for entry in registry["promoted_artifacts"]}
    for row in rows:
        entry = registry_by_path[row["git_path"]]
        assert row["classification"] == entry["classification"]
        assert row["source_sha256"].lower() == entry["source_sha256"]
        assert row["promoted_sha256"].lower() == entry["promoted_sha256"]
        assert int(row["bytes"]) == entry["promoted_size_bytes"]
