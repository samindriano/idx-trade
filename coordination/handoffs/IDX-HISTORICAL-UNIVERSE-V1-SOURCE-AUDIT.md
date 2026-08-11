# Handoff

from: Codex MAIN
to: ChatGPT reviewer
task_id: IDX-HISTORICAL-UNIVERSE-V1-SOURCE-AUDIT
model_used: GPT-5.6 Luna xhigh with Orchestra read-only explorers
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `952c68c1ef5cf7a25e5b130f4fc8db3c65250af1`
branch: `data/historical-universe-v1`
head_commit: see final commit  

## Scope

Bounded official IDX/Zapi lifecycle-source acquisition and audit for
Historical Universe V1. Zapi API access used `ZAPI_API_KEY` from the process
environment only. Raw captures and runtime price-panel inputs remained
outside Git.

## Files changed

- `docs/HISTORICAL_UNIVERSE_V1_SPEC.md`
- `docs/checkpoints/2026-08-11_HISTORICAL_UNIVERSE_V1_SOURCE_AUDIT.md`
- this handoff

No source/model/data artifact was changed.

## Findings

- 962 current official IDX securities; direct/Zapi current code set exact.
- 440 official monthly delisting requests for 1990-01 through 2026-08;
  zero request errors; 163 rows / 159 codes.
- Zapi raw passthrough matched direct IDX core delisting rows for sampled
  2000-01 and 2025-07 periods.
- Strict lifecycle canonicalization is blocked by six conflicting
  four-character tickers: `BUKK`, `INRU`, `ITMA`, `KIAS`, `SKBM`, `UNTX`.
- `MAMIP` and `MYRXP` are explicit non-standard preferred/Series B codes and
  are not silently coerced into the four-character V1 contract.
- Existing price panel has 922 tickers / 450,893 rows from 2024-06-21 to
  2026-07-31; it covers 921/962 current codes, has 41 current codes absent,
  one historical extra (`MFIN`), and five conflict tickers contribute 2,280
  ambiguous rows.
- Current snapshot structural mismatch is 0, but this does not overcome the
  canonical interval conflicts.

## Decisions made

- Direct IDX remains canonical.
- Zapi is accepted as an access/discovery transport only, not an independent
  authority.
- No relisting date is inferred from current status, price presence, or a
  stale `ListingDate` field.
- No complete bounded historical research window is promoted.
- Final verdict: `FAIL` / `HISTORICAL_UNIVERSE_V1_FAIL_BLOCKED_LIFECYCLE_PROVENANCE`.

## Blocking risks

An authoritative historical listing/relisting archive or issuer/exchange
evidence is still required to reconcile the six lifecycle conflicts and prove
an extinct-security-complete window. The 1990 query start is not proof of
pre-1990 completeness.

## Validation

- `tests/test_historical_universe.py`: `8 passed, 0 failed` (2.17s).
- Full pytest: `479 passed, 0 failed, 3 warnings` (20.19s).

## Recommended next action

Do not use this table as a promoted historical universe. Escalate only to an
official archive or targeted official issuer/exchange evidence for the six
blocked tickers; otherwise keep the historical-universe gate fail-closed.
