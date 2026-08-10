# Yahoo Historical Open Semantics Follow-up — Ready

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-yahoo-semantics-v1`
Parent: `data/idx-open-backfill-tier2-audit-v1` at independent-review commit `d00c8d74f2728836ed842ba545034e07b10e5405`.

## Decision

**`OPEN_BACKFILL_YAHOO_SEMANTICS_BROAD_COVERAGE_AUDIT_READY`**

The prior bounded Tier-2 pilot is accepted as useful source evidence but is insufficient for bulk ingestion. Yahoo showed three directly admissible missing-Open sample rows and one exact 5x BBCA price-scale mismatch. The next authorized step is therefore a broader deterministic Yahoo audit that explicitly separates direct raw-price compatibility from independently verified stock-split scale reconstruction.

## Frozen guardrails

- immutable panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- unresolved Open baseline: `446,843`;
- existing Open immutable;
- raw Yahoo only, `auto_adjust=False`;
- no `Adj Close`/dividend execution adjustment;
- split factor may be used only when independently verified, never fitted from provider mismatch;
- transformed H/L/C must equal certified H/L/C exactly;
- no bulk panel write in this phase;
- `execution_grade_promoted=false`;
- no Ranking/Stage-5/execution-PnL/paper/live-trading work.

## Required runtime

Run a deterministic broad sample with >=120 unique tickers and >=240 rows, preserve sample hash, measure direct and split-reconstructed agreement separately, characterize provider coverage/errors, and stop for independent review before any bulk backfill.

Read `docs/OPEN_BACKFILL_YAHOO_SEMANTICS_V1.md` and the runtime handoff before execution.
