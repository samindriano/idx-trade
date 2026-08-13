# Handoff — IDX Ranking V3-A Recency F1-F4 Result

from: Codex local runner
to: ChatGPT review
task_id: IDX-RANKING-V3-RECENCY-F1-F4-DISCOVERY
model_used: Codex
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `362510997e3db41e81b21ec8e7422308338fbef1`
branch: `research/idx-ranking-v2-spec-v1`
head_commit: `362510997e3db41e81b21ec8e7422308338fbef1` (execution source; final documentation commit is reported in the task handoff)
scope: Run the existing V3-A recency runner on the exact frozen prepared cache and immutable V2 HGB_XS_MARKET reference artifacts, limited to V2F1-V2F4.
files_changed: `docs/CURRENT_STATUS.md`, `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`, this handoff, and `docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_F1_F4_RESULT.md`
findings: |
  Full repo pytest passed 240 tests with 3 existing pandas FutureWarnings in 19.04 seconds.
  Prepared table and manifest hashes matched the frozen contract. The exact V2 HGB_XS_MARKET summary and predictions were found and hash-verified.
  Control equivalence passed on 84,732 V2F1-V2F4 rows with zero score and metric differences. H252 and H504 both passed absolute discovery sanity but failed paired promotion, so both are KEEP_DIAGNOSTIC. The deterministic result is V3_A_RECENCY_KILL_KEEP_V2_CONTROL.
decisions_made: |
  Retain exact uniform V2 HGB_XS_MARKET as the reference. Do not promote either recency candidate. Update ledger ordinals 001-003 and cumulative count to 3. Stop after F1-F4 review.
decisions_needed: ChatGPT review of the documented V3-A discovery result before any separately authorized later V3 specification or run.
blocking_risks: |
  Windows core.autocrlf caused the runner's raw addendum Git-blob check to fail against the working-tree line endings. The run used a runtime-only copy reconstructed from the exact committed Git blob; no source implementation or repository doc was changed. Runtime artifacts remain outside Git.
validation_run: |
  `python -m pytest -c pyproject.toml --rootdir <idx-trade> <idx-trade>\tests`: 240 passed, 3 warnings.
  `python -m idx_trade.ranking_v3_recency` with exact prepared table/manifest, immutable V2 reference directory, frozen implementation code commit `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f`, V2F1-V2F4 only, sequential reference mode: control-equivalence PASS; deterministic result `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`.
recommended_next_action: Review `docs/checkpoints/2026-08-10_RANKING_V3_RECENCY_F1_F4_RESULT.md`; do not start V3-B, F5/F6, fresh-forward outcome access, calibration, Stage 6, IDX-VAL-002, execution-PnL, paper/live, or main merge.
