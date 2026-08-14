# Handoff: Financial PIT Alpha V1 18:00 cutoff remediation

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-ALPHA-V1-1800-CUTOFF-REMEDIATION
model_used: GPT-5 Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 13ad4b999c55af91faa2411e28d29303431a6add
branch: research/idx-financial-pit-alpha-v1
head_commit: 58c59d81b05c88adf3cdb181442af9617eb5e27c

## Scope

Remediate the Financial Alpha V1 outcome-blind support contract from the
end-of-civil-day cutoff to exactly 18:00 Asia/Jakarta on session `t`, freeze the
52-slot candidate matrix and missing handling, and audit inherited V2F1–V2F6
support. No fitting or outcome access is included.

## Files changed

- `src/idx_trade/financial_pit_alpha.py`
- `tests/test_financial_pit_alpha.py`
- `docs/FINANCIAL_PIT_ALPHA_V1_PREREGISTRATION.md`
- `docs/checkpoints/2026-08-15_FINANCIAL_PIT_ALPHA_V1_1800_CUTOFF_SUPPORT_REMEDIATION.md`
- this handoff

## Result

- Previous 23:59 support: 70,556 rows / 321 tickers.
- New 18:00 support: 70,520 rows / 321 tickers.
- Rows gained: 0.
- Rows lost: 36; tickers lost: 36; tickers gained: 0.
- Previous same-day publication rows: 1,377.
- Same-day rows after 18:00: 411; retained under 18:00: 966.
- New knowledge-time violations: 0.
- Source timestamp conflict keys: 6.
- Selected 52-slot matrix ambiguous joins: 0.

Exact support identity and artifact hashes are in the dated checkpoint and
external census root:
`D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-census-1800`.

## Frozen contract

- Financial raw slots: exactly 13 features × `Q1/H1/9M/FY` = 52.
- Candidates: exact 25-feature `CONTROL`, exact 52-feature `FINANCIAL_ONLY`,
  exact 77-feature `V2_PLUS_FINANCIAL`.
- Clean V2 HGB identity and hyperparameters remain unchanged.
- Missing handling: fold-local median imputation with missing indicators and
  `keep_empty_features=True`, training-fold only.
- Session-`t` Financial state is for the 18:00 EOD ranking and is first
  actionable from the next official session.
- Survivor rule is inherited clean-V2 paired methodology and is frozen in the
  materialized model-matrix contract; no post-result rescue is allowed.

## Inherited-fold blocker

The support audit uses the exact inherited V2 folds with no redefinition.
`V2F1` has zero Financial-supported rows in train and validation. `V2F2` has
zero Financial-supported training rows and only 388 supported validation rows.
Therefore the Financial-only challenger is not scientifically usable across
the inherited fold set, and the combined challenger is blocked pending review.
No labels, outcomes, scores, or performance metrics were loaded.

## Validation

- Focused Financial Alpha tests: passed.
- Full pytest: one unrelated existing failure in
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflict`;
  the current revision audit correctly reports independent `raw_close` and
  `vendor_adj_close` conflicts, while that legacy fixture expects one.
- `git diff --check`: passed.

## Decision needed

ChatGPT review is required before any run-spec authorization or outcome access.
The correct next decision is whether the inherited-fold support blocker should
end this challenger or whether a separately preregistered fold/support policy
is warranted. This handoff does not authorize new folds.
