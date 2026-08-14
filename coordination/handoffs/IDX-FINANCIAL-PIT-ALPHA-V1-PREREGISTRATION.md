# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-ALPHA-V1-PREREGISTRATION
model_used: GPT-5.6 Luna xhigh orchestra
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: d9e0cd8a75026a56f341e3aa51015c70ac5fdfad
branch: research/idx-financial-pit-alpha-v1
head_commit: pending final commit

## Scope

Created and froze the Financial PIT Alpha V1 preregistration and exact
knowledge-time join contract. Ran only the outcome-blind support census using
the pinned clean V2 common-support parent and accepted GENERAL + CONSOLIDATED
Financial PIT feature panel. No model, target, outcome, provider, or fresh-
forward access occurred.

## Files changed

- `src/idx_trade/financial_pit_alpha.py`
- `tests/test_financial_pit_alpha.py`
- `docs/FINANCIAL_PIT_ALPHA_V1_PREREGISTRATION.md`
- `docs/checkpoints/2026-08-14_FINANCIAL_PIT_ALPHA_V1_SUPPORT_CENSUS.md`
- this handoff

## Inputs

- Clean V2 common support: SHA-256
  `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6`.
- Accepted Financial feature panel: SHA-256
  `1d60ee69070546d21040af8c61f2170c5cca2254f131626a19bf4c1d59f3f023`.
- Financial panel manifest: SHA-256
  `639fc6e6fe3f7f853d23b6f5244c98ec8ed5c63b219aa59e698c8db908fb2140`.

## Findings

- V2 parent: 277,244 rows / 729 tickers / 2021-06-02..2026-07-17.
- Financial panel: 258,401 rows / 531 tickers / 7,722 unique
  ticker/fiscal-year/as-of states.
- Any Financial state: 90,526 rows; any available feature: 70,556 rows / 321
  tickers.
- 52 rows are ambiguous because 6 same-knowledge-time keys conflict; they are
  fail-closed and do not fall back.
- Knowledge-time violations: 0; same-day publication rows: 1,377.
- Support key SHA-256:
  `fbb78032a9ce00f79dbc933ce0a806af36f1ebcef7a3352598f0e60e7d4de303`.

## Frozen decisions

- Eligibility is strictly `reporting_knowledge_at_utc <=` the exact after-
  close Asia/Jakarta-derived UTC cutoff. Calendar date alone is not used.
- Latest eligible state is selected per ticker/fiscal-year/feature/period
  stratum. Q1/H1/9M/FY are not pooled.
- Missing, unresolved, denominator-invalid, unit-mismatch, and conflicting
  inputs remain unavailable; no zero-fill, interpolation, carry-forward,
  annualization, TTM, or synthetic value is allowed.
- All later candidates must use the identical frozen support row identities.
- Later performance work requires separate ChatGPT authorization.

## Decisions needed

Review whether the support set and missingness/strata contract are sufficient
to authorize a separate, pre-registered model run. In particular, review the
52 fail-closed ambiguity rows and the absence of Financial states in 2021-2023.

## Blocking risks

- Financial support is sparse before 2024 and feature availability differs by
  family and period stratum.
- The current V2 parent stores session dates, so the cutoff is a deterministic
  after-close timestamp contract rather than an observed intraday decision time.
- This handoff contains no performance evidence.

## Validation

- Focused tests: `python -m pytest tests/test_financial_pit_alpha.py -q` — 7
  passed.
- Full repository tests: `python -m pytest -q` — 57 passed, 1 failed. The
  failure is the pre-existing `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expectation (current storage returns two independently surfaced conflicts,
  `raw_close` and `vendor_adj_close`, while the old test expects one). No
  storage file or test was changed in this lane.
- `git diff --check` is clean before commit.
- Census: external root
  `D:\Documents\Project\idx-financial-pit-alpha-20260814-v1-census-v4`.
- Later full repository pytest is required before final push; unrelated
  starting-branch failures, if any, will be reported rather than masked.

## Recommended next action

Independent ChatGPT review of this preregistration and support census. Do not
fit or score until the support identity set, missing-value handling, and future
comparison candidates are explicitly accepted.
