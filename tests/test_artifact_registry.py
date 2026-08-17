import json
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
