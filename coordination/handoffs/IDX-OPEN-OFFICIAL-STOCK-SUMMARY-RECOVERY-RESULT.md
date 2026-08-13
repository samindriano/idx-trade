# Handoff

from: Codex / Official Stock Summary Recovery  
to: ChatGPT independent review  
task_id: IDX-OPEN-OFFICIAL-STOCK-SUMMARY-RECOVERY-V1  
model_used: Codex Luna xhigh, Orchestra LIGHT  
reasoning_level: high  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: `76e784e0101e1821bc16e099eb31810ab9cfb125` (latest `origin/main` at audit start)  
branch: `data/idx-open-official-stock-summary-recovery-v1`  
head_commit: documented in the final push report after this handoff commit  

## Scope

Offline audit and derivative-only recovery census using the accepted official
IDX Stock Summary archive at:

`D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1`

No provider/network calls were made. No canonical panel, Foreign Flow
normalized artifact, Corporate Action lane, Financial PIT lane, Intraday,
Frontend, O2, model, outcome, or forward-counter artifact was touched.

## Files changed

- `docs/checkpoints/2026-08-14_IDX_OFFICIAL_STOCK_SUMMARY_OPEN_RECOVERY_RESULT.md`
- `coordination/handoffs/IDX-OPEN-OFFICIAL-STOCK-SUMMARY-RECOVERY-RESULT.md`

External audit artifacts are outside Git under:

`D:\Documents\Project\idx-open-official-stock-summary-recovery-20260814-v1`

## Findings

1. The archive contains 1,288 SHA-verified official `TradingSummary/GetStockSummary`
   sessions from 2021-04-01 through 2026-08-13, with 1,129,024 unique
   ticker/session rows and complete `recordsTotal`/`recordsFiltered` agreement.
2. Positive `OpenPrice` agrees exactly with canonical known Open in 258,514 of
   261,155 positive candidates (98.9887%), with exact canonical H/L/C agreement
   in 258,638 rows (99.0362%).
3. `FirstTrade` agrees exactly in only 147,619 of 261,058 positive candidates
   (56.5464%); it is not an admitted fallback.
4. The global panel has 43,800 missing Open rows. All 43,800 have a raw exact
   key, but all are blocked by `OPENPRICE_NONPOSITIVE_OR_INVALID`.
5. The clean V3-B universe has 12,589 missing Open rows. All 12,589 have the
   same blocking reason. Admitted recovery rows: zero in both scopes.
6. The two derivative overlays are empty and the immutable canonical panel is
   unchanged.

## Key external hashes

- Archive manifest: `fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334`
- Semantic audit summary: `a7ee5341151184f84bf6a7e8be723e635120fcbbcad12d5651f5d7246a510708`
- Recovery census summary: `7276c1e486baddb80d5faf5e577a5d1b434d06d9cc4f2461e787726417b7da58`
- External artifact manifest: `e631686e7b9d296d29ba17adda534d53befdf4cab17d35288283c9bd2056d5d0`

## Decision / blocker

Decision: `OFFICIAL_STOCK_SUMMARY_OPEN_RECOVERY_NO_ROWS_ADMITTED`.

The archive validates `OpenPrice` as the only plausible raw field for future
admission, but it does not supply a positive Open for the current missing rows.
Residual rows remain missing rather than being filled from `FirstTrade`,
provider guesses, forward fill, or corporate-action arithmetic.

## Validation

- Focused: **10 passed**.
- Full: **39 passed, 1 failed, 0 reported warnings** out of 40 collected.
- Unrelated failure: `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` expects one conflict but current shared storage reports independent `raw_close` and `vendor_adj_close` conflicts. No storage changes were made.

## Decisions needed

ChatGPT review should decide whether to retain this lane as a documented
`OpenPrice`-only candidate source and whether any future source may be
considered for the remaining rows. This audit does not authorize reopening
Yahoo/TradingView, Corporate Actions reconstruction, provider calls, or panel
mutation.

## Recommended next action

Keep the empty overlays as the complete derivative result. Treat the remaining
43,800 global / 12,589 V3-B rows as source-unresolved. Resolve the unrelated
storage test in its owning lane separately; do not change it here merely to
make this audit's full-suite result green.
