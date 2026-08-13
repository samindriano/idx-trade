# Handoff

from: Codex / Financial PIT Feature Contract V1
to: ChatGPT independent review
task_id: IDX-FINANCIAL-PIT-FEATURE-CONTRACT-V1
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `135de5acd121a1673e984bb38846e7fd30f7530a` coordination claim; accepted Financial PIT foundation imported at `dd820f8fc2f7cbd350596a25bf3539b44d61c316`
branch: `data/financial-pit-feature-contract-v1`
head_commit: final branch tip is reported with the push result; this handoff is part of that tip

## Scope

Design a bounded PIT-safe Financial PIT feature contract over accepted
immutable fact artifacts. No provider/network call, feature materialization,
model fit, alpha metric, O2 change, protected outcome access, or forward-vault
access.

## Files changed

- `src/idx_trade/financial_feature_contract.py`
- `tests/test_financial_feature_contract.py`
- `tests/test_financial_fact_table.py` (comma + scientific-notation regression)
- `docs/FINANCIAL_PIT_FEATURE_CONTRACT_V1.md`
- `docs/checkpoints/2026-08-14_FINANCIAL_PIT_FEATURE_CONTRACT_DESIGN_REVIEW.md`
- this handoff

## Findings and decisions

- Contract families: size, leverage/capital structure, liquidity,
  profitability, cash-flow quality, margins, and same-period YoY growth.
- Instant facts require explicit instant evidence; duration facts require
  explicit start/end evidence. Q1/H1/9M/FY remain cumulative source periods;
  they are never summed.
- Revision selection is as-of and append-only. Same-time conflicting hashes,
  incomplete inputs, unit mismatches, unsupported applicability, and invalid
  denominators fail closed.
- Financial/sharia revenue/OCF/margin candidates are not assumed comparable;
  the applicability matrix marks them not applicable. Unknown applicability is
  unresolved. Separate scope remains tracked but needs future explicit
  model-safe approval.
- `1,2E3` is locked by test to `12000` under the accepted comma-grouping
  grammar; no locale guessing was added.

## Offline dry-run result

Source corpus: `5,965` filing versions and `37,246` fact rows from the accepted
scientific-notation remediation root. Shape counts were `20,471 INSTANT` and
`16,775 DURATION`; explicit valid boundaries were `0/37,246`. The run marked
`0` candidate rows available and returned
`BLOCKED_UNRESOLVED_PERIOD_METADATA`. This is a readiness blocker, not a
performance result.

External output root:
`D:\Documents\Project\idx-financial-pit-feature-contract-20260814-v2`

- `availability.json`:
  `3e035b3576dfc36eff51a150271cd49a0721f9ade5b064e7ab172df465a9d97c`
- `MANIFEST.json`:
  `2d998548c1da15862c78f4bdf36b46707a14b21d65532507dbf641ae55d62d70`

## Validation

- focused Financial PIT/feature tests: `42 passed`
- full repository pytest and final branch SHA: to be filled in after final validation
- `git diff --check`: to be filled in after final validation

## Blocking risks

The accepted fact artifact lacks explicit period boundary fields. Do not
materialize ratios or build a model until the fact contract is extended or an
equivalent context-to-boundary mapping is independently proven. Do not infer
boundaries from filenames, report period labels, or fiscal year alone.

## Recommended next action

ChatGPT review. If accepted, authorize a separate offline metadata repair/audit
that preserves exact source evidence and reruns availability. No model or
protected-outcome work follows automatically.
