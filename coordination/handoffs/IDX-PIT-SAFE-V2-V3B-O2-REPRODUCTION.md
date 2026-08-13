# Handoff

from: Codex/PIT-Safe-Lineage-Reproduction
to: MAIN / ChatGPT independent review
task_id: IDX-PIT-SAFE-V2-V3B-O2-REPRODUCTION
model_used: Codex Luna xhigh root with bounded Luna xhigh workers
reasoning_level: xhigh
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: 0aaeb1777b613a9d3c9ed6c8e15c04353d116657
branch: codex/pit-safe-v2-v3b-o2-reproduction-research-v1
head_commit: 9eedff931fc682a26b8c4f7c408d6afd606d0e62
scope: Preregistered generic PIT/listing-safe historical remediation and, only if authorized by the frozen boundary decision, clean V2/V3-B/O2 historical reproduction.
files_changed:
- docs/checkpoints/2026-08-13_PIT_SAFE_V2_V3B_O2_REMEDIATION_PROTOCOL.md
- docs/checkpoints/2026-08-13_PIT_SAFE_V2_V3B_O2_RECONSTRUCTION_RUNTIME.md
- coordination/handoffs/IDX-PIT-SAFE-V2-V3B-O2-REPRODUCTION.md
- src/idx_trade/research_features.py
- src/idx_trade/ranking_v2_prepare_cache.py
- src/idx_trade/pit_safe_reproduction.py
- tests/test_research_features.py
- tests/test_pit_safe_reproduction.py
decisions_made:
- Frozen old lineage remains immutable.
- Listing-domain filtering must precede all causal feature construction.
- Malformed non-null listing dates, conflicting duplicates, and invalid boolean verification values fail closed.
- No model fitting occurs before corrected inputs and the explicit reproduction-boundary decision.
- The corrected panel removes exactly KOCI 2023-10-06 and preserves the generic interval contract.
- Corrected V2/V3-B/O2 inputs changed the historical identity/feature population; boundary is HISTORICAL_LADDER_REPLAY_REQUIRED.
- Current executable status is REPRODUCTION_BLOCKED because the available H10 labels end on 2025-03-20 while old development artifacts extend to 2026-07-17, and the corrected comparison population is not the old one.
decisions_needed:
- Determine `EXACT_REPRODUCTION_ALLOWED`, `HISTORICAL_LADDER_REPLAY_REQUIRED`, or `REPRODUCTION_BLOCKED` after corrected input reconstruction.
blocking_risks:
- Existing source authority, raw fingerprint completeness, and immutable publication-history gaps may block a defensible reproduction even if local transformations are deterministic.
- Replaying the ladder would be a new historical evaluation on a materially changed population and must not be represented as exact reproduction.
- Full pytest: passed, exit code 0; existing non-blocking warnings only.
- External reconstruction root: D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_v2_v3b_o2_reproduction_v1_20260813_001.
- Corrected panel: 981,939 rows / 945 tickers; V2: 208,373 / 668; V3-B: 208,373 / 668; O2: 194,989 / 658.
- KOCI 2023-10-06 removed; 826 shared V2 identity rows changed across 281 tickers and 9 sessions; 632 market-context rows changed.
- Manifest SHA-256: 34049ae3e74019219dd323a2993ab273e1fb4abb64f12e6560faf8769628107f.
recommended_next_action: Stop for independent ChatGPT review. Do not fit models or start ladder replay until the changed-population boundary and label/provenance availability are explicitly authorized.
