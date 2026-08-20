# V4-X1 Clean Prospective Score — Preparation Frozen

Date: 2026-08-20 (Asia/Jakarta)  
Branch: `integration/v4-x1-clean-prospective-score-v1`

## Decision

`V4_X1_CLEAN_PROSPECTIVE_SCORE_PREPARED_READONLY_LOCAL_READINESS_AUTHORIZED`

The clean V4-X1 prospective score-only successor has been prepared by reusing the existing canonical EOD + V4-X1 prospective automation. This checkpoint authorizes local focused validation and a **read-only readiness audit only**.

It does **not** authorize scheduled-task mutation, score capture, model scoring, manual counter mutation, outcome access, historical/backfill scoring, provider acquisition, or a second EOD path.

## Scientific parent

Accepted clean Phase-B refit:

- acceptance commit: `ec9e8dc55ccdf458a67b63f612c8eb06660cf829`
- acceptance checkpoint blob: `666ca21ce26248b17328d56e0505e362b2814db5`
- accepted model manifest SHA-256: `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`
- conservative prospective freeze boundary: `2026-08-20T12:08:44+00:00` (`2026-08-20T19:08:44+07:00`)
- prospective preregistration blob: `f33663bc7e4d14941a12974cc453ab90ac5b85ba`

The freeze boundary is deliberately the acceptance timestamp, not the historical training cutoff. A session may count only if both its canonical EOD availability and actual canonical `DATA_READY` completion are strictly after this timestamp.

Therefore the 2026-08-20 session cannot be retroactively credited merely because a later process sees it: its conservative canonical EOD availability predates the accepted clean model freeze.

## Accepted clean model identity

Exactly these model bytes are allowed:

- CONTROL H5 `f727b10c6ea72c9ca7b447977ed4fa9cd3b5b32adb81793921c425d9085665b2`
- CONTROL H10 `737be8c47fe2d689dab09950a931c1339039ed8ae379b79f0bfd5a8c2e7605db`
- CHALLENGER H5 `d8a73d03ff72ab82826ef4e1be5e2073f6a61a5bb01b4e4268428436dc5eb082`
- CHALLENGER H10 `935a6f9aeaa2ca30a4016819e3848d284eb677e38153a7bd3126da0c33a9f95d`

The clean score namespace is:

`V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`

This is intentionally distinct from the older V4-X1 prospective model id/fingerprint, so the clean forward counter starts independently from zero.

## Prospective contract preserved

Inherited preregistration remains unchanged:

- fresh-only capture;
- 100 prospective score sessions;
- full decision-population score storage;
- CONTROL Context25 and CHALLENGER Geometry3 feature definitions unchanged;
- H5/H10 within-date percentile ranks;
- consensus `0.5 * H5 + 0.5 * H10`;
- no historical/backfill scoring;
- no outcome access during score capture;
- outcome vault remains closed until `100/100` accepted prospective score sessions are captured and H10 for session 100 is mature under official-session semantics.

V4-X2 exact-session semantics are not admitted into V4-X1.

## Clean representation migration

The existing prospective scorer is reused; only the accepted clean lineage is rebound.

Historical feature state:

- accepted clean historical panel SHA-256 `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- accepted clean security-master baseline SHA-256 `51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e`

Forward identity policy:

1. any ticker already present in the accepted clean baseline keeps the accepted baseline identity; a mutable runtime master may not rewrite it;
2. a runtime-only ticker may be added only when `listed_from` is strictly after `2026-08-20`;
3. any runtime-only ticker with `listed_from <= 2026-08-20` fails closed as a retroactive identity addition;
4. a genuinely post-freeze new listing still needs the unchanged causal primary-liquidity history before it can enter the decision universe.

Candidate Geometry3 Open remains sourced only from immutable canonical sibling `session_ohlcv.parquet`, after exact candidate H/L/C/V reconciliation against the canonical model-input snapshot.

## Operational reuse

No second data capture system was created.

The successor reuses:

- canonical `IDXTrade-ForwardEOD` EOD engine;
- existing immutable session snapshot registry;
- existing candidate OHLCV contract;
- existing same-Jakarta-date anti-backfill rule;
- existing late-catchup policy (`causal history only`, never prospective counter credit);
- existing 100-session counter mechanics;
- existing calendar-parent compatibility checks.

The future deployment is intended to update the **existing** scheduled task only, after a separate acceptance checkpoint.

## Prepared files / exact Git blobs

Machine contract:

- `config/ranking_v4_x1_clean_prospective_score_v1.json`
- frozen preparation config blob: `38a0357d9b039c651003354f4894add3f82d156a`

Clean adapters:

- `src/idx_trade/v4_x1_clean_forward_score.py` — `f00528422a42835e5a969bfe503e29f91e0bf957`
- `src/idx_trade/v4_x1_clean_eod_pipeline.py` — `2ce4fbcb9baec5c39ced4fadaaf58dc4d73a6216`
- `src/idx_trade/v4_x1_clean_eod_legacy_compat.py` — `b78f020992e36fd1ba68027911e79bdb07e4da08`
- `scripts/run_v4_x1_clean_forward_score.py` — `c63e1a3e36f34dd4210e9dbb951dda9ae90a64ec`
- `scripts/run_v4_x1_clean_forward_readiness.py` — `07c38a0e27a0acfb7f5af49a7ea9b8b8fb822e1d`
- `scripts/run_forward_eod_v4_x1_clean_pipeline.ps1` — `5b3c3939ae87ce666bb9b1cd02ae4689d743122d`
- `scripts/update_forward_eod_task_v4_x1_clean.ps1` — `7b06fa4914c090a5aa76f767347de71bd9dd95a1`

Focused new tests:

- `tests/test_v4_x1_clean_forward_score.py` — `c89bfab7173cd0355739cb3ec7960d5d3ea58f8a`
- `tests/test_v4_x1_clean_eod_pipeline.py` — `778fb2d2b2027b84510a3d1db608e0c09c29ae51`
- `tests/test_v4_x1_clean_prospective_contract.py` — `77582e2ff068897fbe8f0d3779216aebc9bf54b8`

Reused operational/scientific blobs are pinned in the machine contract and must remain exact during local validation.

## Local readiness authorization

Authorized locally:

1. checkout/fetch this branch;
2. verify exact Git blobs;
3. run focused new + inherited V4-X1/EOD regression tests;
4. run `py_compile` and `git diff --check`;
5. resolve and hash-verify the accepted clean model root, clean panel, and clean security master;
6. run `scripts/run_v4_x1_clean_forward_readiness.py` exactly as a read-only audit;
7. report clean counter state, possible first candidate, history gaps, ignored backfills, and all safety flags;
8. stop for independent review.

Expected initial counter is `0`. Any nonzero clean counter before deployment acceptance is a review blocker.

## Still prohibited

Until an independent post-readiness checkpoint:

- do not update `IDXTrade-ForwardEOD` scheduled task;
- do not invoke the clean score CLI on a real session;
- do not invoke the clean EOD pipeline in a way that can commit a score;
- do not manually insert/edit/delete model-run registry rows;
- do not credit old V4-X1 forward observations to the clean counter;
- do not score 2026-08-20 or any other pre-freeze/backfill session;
- do not access realized H5/H10 outcomes;
- do not open the outcome vault;
- do not refit/retune models;
- do not alter feature/session/CA80/universe semantics;
- do not call a new provider or create a second EOD path.

## Next

`LOCAL_VALIDATION_AND_READONLY_READINESS_ONLY; THEN_INDEPENDENT_REVIEW_BEFORE_DEPLOYMENT`
