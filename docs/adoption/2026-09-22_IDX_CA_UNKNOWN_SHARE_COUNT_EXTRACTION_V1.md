# IDX-Trade CA Unknown Share-Count Extraction V1

Date: 2026-09-22 (Asia/Jakarta)

Status: **EXTRACTED ON AUTHORITATIVE ADOPTION LINEAGE / LOCAL TEST PASS**

## Scope

This is a narrow extraction of the isolated shadow fix from commit
`5c14b036ee179532903e1d0fd32d486db06cf3c7` onto the authoritative adoption
candidate lineage at `codex/idx-authoritative-runtime-adoption-20260921`.
The shadow documentation branch was not merged.

Only these runtime/test files changed:

- `src/idx_trade/providers/idx_corporate_actions.py`
- `tests/test_idx_corporate_actions_provider.py`

## Semantics

`_parse_share_count` now treats scalar pandas `NaN` in optional
`old_shares`/`new_shares` fields as unknown (`None`). It does not fabricate a
share count or ratio. Non-scalar values still pass through the existing
fail-closed invalid-field path.

This preserves the distinction between unavailable optional CA mechanics and
malformed input.

## Real copied-evidence provenance

The behavior was checked against the immutable copied CA registry, not a
provider call:

- source: `C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-extended-evidence\inputs\corporate_actions\idx_actions.csv`
- copied-evidence package aggregate SHA-256:
  `be2276257e47bd378d22f8e9b71afcaf19231eec6772dbd8e3917cdf685847af`
- rows: 38
- tickers: 35
- parsed rows: 38
- known ratios: 22
- unknown ratios: 16
- provider/network access: none

## Validation

- focused provider file: `8 passed`
- full candidate suite: `906 passed`, exit code `0`
- warnings: the same three pre-existing pandas `FutureWarning`s
- source/candidate worktree was isolated from the active runtime and scheduler

The extracted change is implementation evidence only. It does not authorize
canonical-data mutation, provider access, migration, canary, or production.
