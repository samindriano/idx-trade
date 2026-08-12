# IDX Trade V0 status

Only MAIN may edit this file.

`docs/CURRENT_STATUS.md` is authoritative. This coordination view must be refreshed when it diverges.

- **Phase:** `FINAL_ALPHA_FROZEN__PATH_RISK_V2_PRE_OUTCOME`
- **Operating mode:** `EXPLORATORY_RESEARCH_ONLY`
- **Current working branch:** `research/idx-ranking-v2-spec-v1`
- **Status refreshed:** `2026-08-11T04:46:00Z`
- **Market / venue:** `IDX listed equities / REGULAR / daily-EOD`
- **Orchestration default:** `LIGHT_PARALLEL_FIRST`
- **Root / workers:** `Luna xhigh / Luna xhigh`
- **Escalation:** `Sol High bounded checkpoint only`
- **Alpha architecture search:** `CLOSED`
- **Final alpha ranker:** `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`
- **Final model SHA-256:** `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6`
- **Feature-order SHA-256:** `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`
- **Path Risk V1:** `PATH_RISK_A_DISCOVERY_FAIL_CLOSE`
- **Path Risk V2:** `FROZEN_IMPLEMENTED_PRE_OUTCOME`
- **PR-002 viewed:** `false`
- **PR-003 viewed:** `false`
- **Path Risk F5/F6:** `SEALED`
- **Fresh-forward post-2026-07-31 realized outcomes:** `LOCKED_NOT_ACCESSED`
- **Calibration / alpha+risk integration / execution-PnL / Kelly / paper/live:** `NOT_AUTHORIZED_AUTOMATICALLY`
- **Execution frontier:** `import/check-out verification + full tests + independent frozen-spec/seal audit; then one serialized PR-002/PR-003 F1-F4 discovery run`
- **Parallel-safe work now:** `test/import diagnosis and read-only spec/provenance/seal audit when isolated`
- **Scientifically sequential boundary:** `the evidence-producing PR-002/PR-003 run and any later candidate/confirmation decision`
- **MAIN-retained work:** `gate protection, authoritative run authorization, integration, verdict, status continuity`
- **Current blocker:** `local full-suite/preflight result for current checkout not yet returned`
- **Next integration action:** after preflight PASS, execute exactly one frozen Path Risk V2 F1-F4 discovery run from `coordination/handoffs/IDX-PATH-RISK-V2-DISCOVERY-F1-F4-RUN.md`, then return evidence without touching F5/F6.

## PIT sector history revival lane update (branch-local)

- **Status:** `REVIEW`
- **Owner:** `ChatGPT/PIT-sector-revival`
- **Branch / HEAD:** `data/idx-pit-sector-history-revival-v1` / `a2bf035`
- **Result:** One bounded recovery attempt completed. Canonical inventory remains 5 ready / 3 discovery-blocked: 2022 reference unresolved; 2023 `Peng-00158` found only through a mirror and the direct IDX path is an empty ZIP; 2026 `Peng-00100` effective date unresolved.
- **Checkpoint:** `docs/checkpoints/2026-08-13_PIT_SECTOR_HISTORY_REVIVAL_RECOVERY.md`
- **Guardrail:** No config promotion, sector model, retraining, forward outcomes, or dependent outcome access; awaiting independent review.

For future meaningful engineering work, MAIN must run the parallelism preflight and should not keep independent critical-path scopes sequential merely because one Luna can perform them all.
