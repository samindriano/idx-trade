# Handoff — IDX Ranking V3-D Sector-Relative Pre-Run Review

Date: 2026-08-10 (Asia/Jakarta)

Status: **PRE-RUN REVIEW / DATA-GATE WORK ONLY — V3-D OUTCOME SCORING NOT AUTHORIZED**

## Objective

Continue the already-implemented provisional V3-D Sector-Relative lane after the V3-C result is independently reviewed. The next operator may inspect V3-C and perform outcome-blind V3-D amendments/data-gate work, but must not score V3-D until a separate final authorization JSON is created and pinned.

## Required reads

1. `docs/CURRENT_STATUS.md`
2. `docs/RANKING_V3_SECTOR_RELATIVE_SPEC_V1.md`
3. `docs/RANKING_V3_SECTOR_RELATIVE_SPEC_REVIEW_ADDENDUM_V1.md`
4. `docs/checkpoints/2026-08-10_RANKING_V3_SECTOR_PROVISIONAL_IMPLEMENTED.md`
5. newest V3-C result/review checkpoint if available
6. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
7. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`
8. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`
9. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
10. `src/idx_trade/research_v3_sector.py`
11. `src/idx_trade/ranking_v3_sector.py`
12. `tests/test_ranking_v3_sector.py`

## Current provisional hypothesis

Exact V2 global control vs exact V2 + six PIT sector-relative features:

1. `sector_rank_close_return_5`
2. `sector_rank_close_return_20`
3. `sector_rank_close_position_20`
4. `sector_relative_close_return_5`
5. `sector_relative_close_return_20`
6. `sector_relative_close_position_20`

No Structure-Lite or Regime is inherited into this discovery candidate.

## Phase A — V3-C-informed pre-outcome review

After V3-C returns:

- review V3-C independently first;
- do not use V3-C result to stack experts into V3-D;
- if V3-C exposes useful state dependence, one V3-D pre-outcome amendment may add frozen regime-stratified diagnostics using the already-frozen V3-C state definition;
- if no useful V3-C implication exists, keep V3-D exactly as implemented;
- any amendment must occur before V3-D cache/outcome authorization and must receive a new documented hash/review.

## Phase B — full pytest before sector data work

From the explicit repo root run full pytest and record pass/fail/warnings/duration.

If tests fail, fix only engineering defects that do not alter the research hypothesis. Research-semantic changes require ChatGPT review before proceeding.

## Phase C — real PIT sector-history provenance gate

Do not fabricate sector history from a current sector snapshot.

A candidate history artifact must include:

- `ticker`
- `sector_code`
- `effective_from`
- `effective_to_exclusive`
- `available_at`
- `source_id`
- `source_sha256`

For every unique `(source_id, source_sha256)`, independently verify actual immutable source bytes or a trusted immutable archive identity. Record source location/archive identity, taxonomy/version, and hash verification.

Then run the implemented PIT validator. Fail closed on invalid intervals, overlap, untraceable tickers, invalid hashes, or unsupported availability/effective-date provenance.

## Phase D — outcome-independent V3-D cache prepare

Only after a defensible PIT history exists, run:

`python -m idx_trade.ranking_v3_sector prepare ...`

using exact frozen signal panel/calendar/security master/V2 prepared artifacts and a new empty output directory.

The prepare stage must remain outcome-independent and physically limited to session <=984.

Required pre-score gate for every F1-F4 train/validation block:

- PIT sector assignment >=90%;
- each six feature finite >=80%;
- validation >=8 sectors;
- no invalid assignment/no silent row drop;
- exact recomputed V2 25-feature equality <=1e-12;
- F5/F6 not materialized;
- outcome metrics not computed.

If gate fails, document `V3_D_SECTOR_BLOCKED_KEEP_V2_CONTROL` and stop. Do not weaken thresholds or backfill sector history.

## Phase E — stop for final authorization

Even after the data gate passes, do **not** run V3-D outcomes automatically.

Return to ChatGPT with:

- V3-C final reviewed verdict;
- full pytest result;
- sector-history SHA and normalized-history SHA;
- source-document/archive hash-verification inventory;
- sector taxonomy/version;
- PIT assignment coverage per F1-F4 train/validation;
- six feature finite coverage;
- sector counts/group-size diagnostics;
- prepared cache/manifest SHA;
- exact V2 recomputation diff;
- confirmation F5/F6 and fresh-forward outcomes untouched.

ChatGPT will then decide whether to create the final `V3_D_OUTCOME_RUN_AUTHORIZED` JSON and an outcome-run handoff.

## Hard prohibitions

Do not:

- score V3-D without the separate authorization JSON;
- use current-sector backfill;
- alter group-size/coverage gates to force PASS;
- add sector experts/model zoo;
- include V3-B or V3-C architecture in the V3-D discovery candidate;
- access V2F5/V2F6;
- access reserved V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start V3-E/integration/calibration/Stage6/IDX-VAL-002/execution/paper/live/main automatically.
