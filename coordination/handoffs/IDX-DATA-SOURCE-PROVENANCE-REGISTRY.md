# Handoff
from: Codex/Provenance-Registry (Luna xhigh)
to: ChatGPT independent review
task_id: IDX-DATA-SOURCE-PROVENANCE-REGISTRY
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 639fcb8
branch: codex/data-source-provenance-registry-v1
head_commit: c6839f4
scope: canonical machine-readable source registry, JSON Schema, fail-closed validator, focused tests, and maintenance docs only
files_changed:
  - config/data_source_provenance_registry.v1.json
  - config/data_source_provenance_schema.v1.json
  - src/idx_trade/source_registry.py
  - tests/test_source_registry.py
  - docs/DATA_SOURCE_PROVENANCE_REGISTRY.md
  - docs/checkpoints/2026-08-13_DATA_SOURCE_PROVENANCE_REGISTRY_V1.md
  - coordination/handoffs/IDX-DATA-SOURCE-PROVENANCE-REGISTRY.md
findings:
  - 18 source-family entries are linked to 20 accepted checkpoint pins.
  - The registry explicitly records UNKNOWN, BLOCKED, SHADOW, PIT_UNRESOLVED, and conditional states.
  - Official authority and transport parity are not treated as PIT or revision certification.
  - Corporate Actions remains revision-sensitive and record/publication dates are not promoted to market-effective dates.
  - Stockbit remains SHADOW/non-canonical EOD.
  - Open derivatives remain bounded research common-support and not execution-grade.
  - Historical and publication uncertainties remain unresolved rather than normalized.
decisions_made:
  - Validator rejects malformed/unknown fields, unsupported enums, duplicate IDs, stale reviews, contradictory timing/use policy, non-PIT replay permissions, non-controlling checkpoints, and checkpoint blob mismatches.
  - Runtime data/user-specific paths are not committed; artifact hashes are included only when the accepted evidence supplied a complete hash.
decisions_needed:
  - Independent review of schema strictness and source-entry wording.
  - Separate owner decision for the existing storage-test expectation mismatch.
blocking_risks:
  - Full pytest is not green because an untouched storage test expects one revision conflict but current behavior returns two (`raw_close` and `vendor_adj_close`).
  - This lane does not resolve the repository-wide scientific-integrity audit's remediation findings.
validation_run:
  - focused `pytest -q tests/test_source_registry.py`: 9 passed
  - registry JSON/schema JSON parse: PASS
  - validator with local checkpoint git verification: PASS (18 sources, 20 checkpoint pins)
  - full `pytest -q`: one pre-existing failure in `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  - `git diff --check`: PASS
recommended_next_action: ChatGPT review the pushed branch; if accepted, keep the registry as a representation layer and route any scientific/code remediation to its active owner.
