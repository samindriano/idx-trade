# Handoff — LBRE / Market-Wide Free-Float Reconciliation V1

from: ChatGPT/LBRE-Reconciliation-Prep
to: Codex/LBRE-Market-Anchor-Reconciliation
scientific parent: `data/idx-lbre-monthly-free-float-history-v1@bf0648c9dd37ad4a25e2de42d6f4a18fd19f857d`
status: `PREPARED_NEW_BRANCH_REQUIRED`

## Purpose

Resolve the meaning of the 2025-12-31 cross-source reconciliation result from the accepted monthly LBRE history:

- AGREE: 260
- CONFLICT: 625
- SINGLE_SOURCE: 38

This lane is diagnostic/reconciliation only. It must determine whether the 625 conflicts are mostly percentage-reporting/rounding differences with identical free-float share counts, or genuine free-float share-count conflicts.

## Mandatory first action

1. Fetch latest `origin/main:coordination/TEAM_STATUS.md`.
2. Confirm no active lane already owns LBRE vs market-wide free-float reconciliation.
3. Create/checkout branch `data/idx-lbre-market-anchor-reconciliation-v1` from parent HEAD `bf0648c9dd37ad4a25e2de42d6f4a18fd19f857d`.
4. Claim the lane on canonical main before analysis.

Suggested row:

`LBRE / market-wide FF reconciliation V1 | ACTIVE | Codex/LBRE-Market-Anchor-Reconciliation | data/idx-lbre-market-anchor-reconciliation-v1 | offline 2025-12-31 reconciliation forensic over immutable monthly-history + market-anchor artifacts; classify share-count vs percentage-only conflicts; no acquisition/daily state/features/models`

## Immutable parent artifacts

Monthly history root:
`D:\Documents\Project\idx-lbre-monthly-free-float-history-20260815-v1`

Monthly history manifest SHA-256:
`e134809a1f1b745daf2f21c33ab7db78c38d1d5d520f5320564359d5b865bd86`

Historical snapshot root:
`D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`

Historical snapshot manifest SHA-256:
`7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`

Verify exact parent manifests before analysis. No network/provider calls are authorized.

## Required classification

For every ticker in 2025-12-31 reconciliation, classify into exactly one of:

- `EXACT_AGREE`: shares identical and official percentages within existing tolerance.
- `SHARES_AGREE_PCT_DIFF`: shares identical, percentages differ beyond tolerance.
- `SHARES_DIFF_PCT_AGREE`: share counts differ, percentages within tolerance.
- `SHARES_AND_PCT_DIFF`: both share counts and percentages materially differ.
- `LBRE_ONLY`.
- `MARKET_ONLY`.

Do not collapse any category into another.

## Required diagnostics

For overlap rows compute only diagnostic quantities:

- `share_delta = lbre_ff_shares - market_ff_shares`
- `share_delta_abs`
- `share_delta_pct_of_lbre`
- `pct_delta_pp = lbre_ff_pct - market_ff_pct`
- if LBRE listed shares is available, `lbre_implied_pct = lbre_ff_shares / lbre_total_listed_shares * 100`
- `lbre_reported_minus_implied_pp`

The implied percentage is diagnostic only. Never replace either official reported percentage.

For share-count conflicts, report distributions and top absolute/relative differences. Inspect a bounded stratified sample of official evidence for each conflict class to identify whether differences plausibly reflect reporting convention, timing/versioning, denominator changes, or unresolved source semantics. Do not infer a cause without evidence.

## Critical questions

1. Of the 625 prior `CONFLICT` rows, how many have identical FF share counts?
2. How many have genuine FF share-count differences?
3. For identical-share conflicts, what is the distribution of percentage deltas?
4. For share-count conflicts, are differences small rounding artifacts or economically meaningful?
5. Does either source appear systematically earlier/later in publication time for the same 2025-12-31 position?
6. Is LBRE safe to use as the primary denominator source for `free_float_shares`, with market-wide data retained as validation/anchor evidence?

## Acceptance logic

A positive denominator-readiness conclusion is allowed only if the evidence shows that share-count agreement is sufficiently strong and any residual share-count conflicts remain explicit/fail-closed.

Do not invent a universal numeric threshold after seeing the data. Report raw class counts and distributions. If a source-preference policy is proposed, it must be semantic/provenance-based, not optimized from conflict frequency.

## Hard boundaries

Do NOT:
- download/redownload any source;
- modify the monthly-history artifact;
- change parser/lineage rules;
- resolve a conflict by silently preferring LBRE or market-wide;
- build daily FF state;
- forward-fill/interpolate;
- use holder/HSC/>=1% reconstruction;
- compute effective supply or Foreign Flow normalized features;
- fit models or access outcomes;
- touch unrelated lanes.

## Outputs

Create a new immutable external root, e.g.:
`D:\Documents\Project\idx-lbre-market-anchor-reconciliation-20260816-v1`

Include:
- parent manifest verification;
- full classified reconciliation table;
- class counts;
- share/pct delta distributions;
- bounded evidence-review table for representative conflict rows;
- source publication-time comparison;
- conclusion on denominator readiness;
- deterministic manifest + SHA-256.

Add repo docs:
- `docs/checkpoints/2026-08-16_LBRE_MARKET_ANCHOR_RECONCILIATION_RESULT.md`
- `coordination/handoffs/IDX-LBRE-MARKET-ANCHOR-RECONCILIATION-V1-RESULT.md`

Run focused tests if code is added, full pytest, and `git diff --check`.
Update canonical TEAM_STATUS to REVIEW at completion, commit, push, and stop.

Allowed verdicts:
- `LBRE_FF_SHARES_DENOMINATOR_READY_WITH_EXPLICIT_GAPS`
- `LBRE_FF_SHARES_DENOMINATOR_PARTIAL_CONFLICT_REVIEW_REQUIRED`
- `LBRE_FF_SHARES_DENOMINATOR_NOT_READY_SOURCE_SEMANTICS_CONFLICT`
