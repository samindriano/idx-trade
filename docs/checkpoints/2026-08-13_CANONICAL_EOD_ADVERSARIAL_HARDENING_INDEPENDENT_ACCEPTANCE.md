# Canonical EOD Adversarial Hardening — Independent Acceptance

Date: 2026-08-13 (Asia/Jakarta)
Branch: `codex/idx-eod-adversarial-tests-v1`
Reviewed HEAD: `7b21c50d278b13c8e94cdebddd4ca35765d7274e`
Implementation commit: `0aac752bc1cb46ca3203e76751a9bd17eee8672a`
Canonical runtime base: `b94b272eddede0432e2fbe4acb2915e57a716bcb`
Decision: `CANONICAL_EOD_ADVERSARIAL_HARDENING_ACCEPTED_NOT_YET_DEPLOYED`

## Independent review verdict

The bounded engineering hardening is accepted.

The reviewed code closes the principal adversarial gaps identified in this lane without changing frozen model/scientific semantics:

- the EOD catch-up runner requires the returned `DATA_READY.session_date` to equal the requested earliest official session and fails on no chronological progress;
- `DATA_READY` rows are semantically and hash verified before they can be reused or passed into model fan-out;
- stale capture reconciliation verifies complete canonical artifacts and uses the original lease owner/heartbeat in the update predicate, preventing a stale worker from overwriting a newer lease;
- stale model recovery promotes a result to `DONE` only after semantic artifact/manifest validation rather than mere file existence;
- model result validation checks manifest status, exact session, model ID, generation, model fingerprint, artifact path/hash, score support/schema/row counts, and protected outcome flags;
- duplicate/ambiguous source rows and ambiguous canonical table selection fail closed;
- provider/session adapters reject malformed dates, null identities, duplicate normalized rows, non-finite numeric values, and invalid completeness counts covered by this lane;
- O2 counter registration is atomic/idempotent for retry of the same official session and verifies the expected transition;
- model worker lock release is owner checked.

The adversarial tests directly cover wrong-session `DATA_READY` returns, no-progress loops, stale/corrupt context artifacts, stale lease replacement, duplicate raw price rows, invalid/duplicate session calendars, model fingerprint mismatch, O2 counter idempotency, and non-owner lock release.

## Validation evidence

The implementation checkpoint reports:

- focused EOD/source suite: `69 passed`;
- full repository suite on this branch/base: `286 passed`, `0 failed`, `3 existing warnings`;
- `git diff --check`: PASS;
- no provider/network calls;
- no protected outcome access;
- no model execution/retraining;
- no scientific/model behavior changes.

## Accepted boundary

This acceptance is for the engineering branch and its tests only.

It does **not** mean the installed scheduled canonical checkout is already hardened. The installed `IDXTrade-ForwardEOD` runtime was previously audited on `integration/forward-eod-automation-monitoring@b94b272`; the accepted hardening branch is three commits ahead of that base. A separate controlled integration/deployment step is required before these protections govern future scheduled EOD runs.

This acceptance also does not close the repository-wide reproducibility NO-GO. The known strict boolean/date/PIT/source-authority/provenance/immutable-publication issues remain owned by the provenance/P1 remediation lanes. In particular, this branch intentionally does not claim to fix every P1 from the repository scientific-integrity audit.

No protected outcomes, forward evaluator gates, O2/V2/V3-B model identities, or scientific decision rules are changed or authorized by this acceptance.

## Next boundary

Before the hardening is considered operationally active, integrate the accepted branch into the canonical EOD runtime checkout, rerun focused/full tests, verify the scheduled task points to the integrated commit, and perform a no-provider dry/status verification. Do not trigger provider capture merely to prove deployment.
