# Handoff

from: MAIN / ChatGPT ARCHITECT
to: LOCAL / Codex Luna xhigh
task_id: `IDX-RANKING-V2-CHAMPION-FREEZE-FORWARD-SPEC`
branch: `research/idx-ranking-v2-spec-v1`
scope: Freeze the selected Ranking-V2 historical-development champion and design/implement the exact final-refit + fresh-forward validation contract **without inspecting fresh-forward outcomes**.

## Required first reads

Read and explicitly confirm before doing substantive work:

1. `AGENTS.md`;
2. `docs/CURRENT_STATUS.md`;
3. `docs/checkpoints/2026-08-10_RANKING_V2_HISTORICAL_CHAMPION_REVIEW.md`;
4. `docs/RANKING_V2_RESEARCH_SPEC_V1.md`;
5. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
6. this handoff.

The performance note is mandatory. State which recommendations are relevant before creating/changing any next runtime implementation.

## Accepted parent result

- integrator status: `RANKING_V2_HISTORICAL_CHAMPION_SELECTED`;
- historical-development champion: `HGB_XS_MARKET`;
- champion features: exact frozen 25-feature `HGB_XS_MARKET` set;
- champion model hyperparameters: exact frozen HGB parameters already defined in V2;
- prepared cache SHA-256: `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- integration summary SHA-256: `3facb4468caafab8cf19f368cf5ef04f36dac052089d2ecb810b683c851ec705`;
- all historical data through `2026-07-31` is development knowledge, not independent validation.

## Required design decisions to freeze

Produce a reviewable specification/checkpoint that freezes, before fresh-forward outcome access:

1. exact final-development training boundary and which resolved H10 rows are eligible for the final refit;
2. exact feature list/order and model hyperparameters, with no tuning/search;
3. exact model/preprocessing serialization + hashes/provenance;
4. exact causal method for producing the same V2 features for dates strictly after `2026-07-31`;
5. exact fresh-forward universe semantics;
6. exact H10 label maturity rule so no immature signal is scored as an observed outcome;
7. exact minimum forward sample/time requirement before the first independent verdict;
8. exact forward metrics and predeclared PASS/MIXED/FAIL decision rule;
9. whether evaluation is one-shot at a frozen horizon or sequential, and safeguards against repeated-peeking/adaptive rescue;
10. exact artifact/manifest/marker scheme proving the forward outcomes were not inspected before the architecture/final model/evaluation contract froze;
11. explicit handling of data revisions and immutable snapshots;
12. runtime/performance implementation plan consistent with `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`.

## Constraints

- `HGB_XS_MARKET` is the only Ranking-V2 historical-development champion; do not reopen candidate selection.
- No new model, feature family, hyperparameter search, pairwise rescue, sector-relative addition, label change, universe change, threshold search, or calibration may be added to improve historical outcomes.
- Do not rerun Stage 5.
- Do not use H5/H20 to rescue/select the champion.
- Do not inspect, summarize, score, or evaluate any fresh-forward outcome after `2026-07-31` during this task.
- Do not start Probability V2/V1 calibration.
- Do not start Stage 6 or `IDX-VAL-002`.
- Do not make execution-PnL, Kelly sizing, paper-trading, live-trading, or deployment claims.
- Do not merge to `main`.

## Performance rule

Do not rerun the five historical candidates merely to obtain runtime timings. If new profiling instrumentation is needed, design it for the next authorized workload or a semantics-safe benchmark. Prefer measured bounded scheduling/process parallelism over simply adding Codex agents.

Any optimized runtime must prove semantic equivalence before it is used to evaluate fresh-forward outcomes.

## Required handoff result

Return:

1. actual branch/HEAD and clean-tree status;
2. exact files changed;
3. tests/CI result if code changed;
4. explicit confirmation that `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` was read;
5. frozen champion/final-refit specification;
6. frozen forward-validation protocol and decision rule;
7. provenance/marker design proving no premature fresh-outcome access;
8. performance/runtime plan;
9. unresolved decisions/blockers, if any;
10. exact next action only.

STOP after the champion-freeze / forward-spec phase. Do not evaluate fresh-forward outcomes in the same task.
