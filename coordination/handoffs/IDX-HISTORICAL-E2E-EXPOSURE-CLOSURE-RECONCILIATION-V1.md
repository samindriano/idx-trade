# Handoff

from: Codex
to: ChatGPT / MAIN
task_id: IDX-HISTORICAL-E2E-EXPOSURE-CLOSURE-RECONCILIATION-V1
model_used: GPT-5.6
reasoning_level: high
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-historical-e2e`
source_commit: `8250b5b4a89a5e5275804fa079ecc1226a076c22`
branch: `research/idx-historical-e2e-replay-v1`
head_commit: `8250b5b4a89a5e5275804fa079ecc1226a076c22`

## Scope

Outcome-blind offline reconciliation only. No labels, returns, fills, NAV,
performance, Monte Carlo, protected outcomes, or provider calls were used.

## Files changed

- `docs/checkpoints/2026-08-24_HISTORICAL_E2E_EXPOSURE_CLOSURE_RECONCILIATION_V1.md`
- `coordination/handoffs/IDX-HISTORICAL-E2E-EXPOSURE-CLOSURE-RECONCILIATION-V1.md`

External-only derived artifact:

- `D:\Documents\Project\idx-historical-e2e-dividend-closure-20260824-v1\DIVIDEND_EXPOSURE_CLOSURE_V1.csv`
  SHA-256 `c4d6a73d876cf92695944c2b8d941db4dbcff822558afd2c0e383f8d2664af4c`.

## Findings

- Raw dividend source bytes are complete for 347/347 ticker files. The parent
  manifest's `INCOMPLETE` status is parser-stage only for BBTN/BJTM/CYBR/RAJA;
  the normalized derivative is complete and those bytes were not reacquired.
- Closure table: 5,693 exposure rows / 1,297 spells / 347 tickers.
- Accepted certified dividend overlap: 11 rows.
- Candidate announcements lacking attachment-level event semantics: 4,384
  exposure rows.
- No candidate title but no authorized no-event proof: 1,298 rows.
- No-event proof remains fail-closed because full attachment semantics/content
  are not preserved for the corpus.
- Existing KSEI evidence supports NISP 2024-09-06 and TPIA 2024-05-20 as
  security-to-IDR cash conversions. These are proposed non-blocking CA
  dispositions, not yet promoted to the accepted event-window ledger.
- Sensitivity only: treating those two IDs as non-blocking would produce
  5,113/5,693 rows and 205/600 CA-ready sessions, with provisional longest
  runs up to 96 sessions. The strict scope remains unchanged at zero.

## Decisions made

- Did not reacquire BBTN/BJTM/CYBR/RAJA because raw bytes were present and the
  normalized offline derivative reconciled the parser status.
- Did not promote title absence to a dividend no-event proof.
- Did not rewrite or substitute any pinned readiness, CA, dividend, model,
  outcome, or replay artifact.
- Did not edit `coordination/TEAM_STATUS.md`; MAIN owns that file.

## Blocking risks

- Dividend market-wide no-event proof is incomplete for all 600 candidate
  sessions.
- CA exposure ledger still has 1,222 unresolved rows and must be rebuilt only
  from exact official evidence if dispositions are promoted.
- Strict scope recompute v9 remains `STRICT_SCOPE_EMPTY_BLOCKED`.

## Validation run

- Offline raw/normalized manifest and exposure closure checks: PASS.
- No network/provider calls: PASS.
- No protected outcome access: PASS.
- Worktree was clean before documentation changes.

## Recommended next action

Review the NISP/TPIA non-blocking evidence as a separate CA ledger input, then
perform one manifest-pinned CA recomputation. Independently decide whether an
official attachment-level dividend corpus can be made complete enough for
no-event proof; otherwise keep the full economic replay blocked.
