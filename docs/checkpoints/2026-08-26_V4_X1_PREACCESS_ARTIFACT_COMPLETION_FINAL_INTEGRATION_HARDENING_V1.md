# V4-X1 Pre-Access Artifact Completion — Final Integration Hardening V1

Status: `CODE_HARDENED_CI_GREEN_REAL_LOCAL_REPLAY_PENDING`

Date: 2026-08-26 (Asia/Jakarta)

This checkpoint records the independent hardening pass performed after review of PR #89. It does not reopen protected outcomes and does not change the frozen V4-X1 model, target semantics, Decision, sizing, execution science, runtime counter, active runtime, scheduler, or providers.

## Parent/dependent lineage

- Parent PR #88: `ops/v4-x1-prospective-preaccess-readiness-v1` -> `main`.
- Parent reviewed head: `b12a8d46b5356985a49fde4dc745bb9fc28cf586`.
- Parent CI: `32878882601`, PASS.
- Independent parent verdict: `V4_X1_PREACCESS_ADAPTER_V1_APPROVED_FOR_MERGE`.
- Dependent PR #89: `ops/v4-x1-preaccess-artifact-completion-v1` -> parent branch.
- Hardened implementation head before this documentation commit: `29e9f3fb6676031e0768085feed315496a2cc490`.
- Hardened implementation CI: `32915265242`, PASS.
- Full merge-tree pytest at that head: `242 passed, 4 existing warnings`.

Neither PR was merged by this hardening pass.

## Review defects closed

### 1. Race-safe immutable publication

Completion artifacts no longer use a pre-check followed by `os.replace()` for final publication. The writer now stages bytes, fsyncs them, and publishes by exclusive hard-link creation. An identical already-published object is idempotent; conflicting bytes fail closed. A second writer cannot silently replace an existing final artifact.

Tests cover equal-byte and conflicting publish races.

### 2. Score validation before final publication

A projected score is now built in memory and validated through the existing frozen score-manifest and score-artifact validators in a private candidate tree before the final projected artifact/manifest are published. Source manifest/artifact bytes are rehashed again immediately before final publication, followed by post-publication frozen-gate revalidation.

The producer remains exact column selection only: `date,ticker,alpha_consensus`; it does not rerank, transform, refit, retune, or contact a provider.

### 3. Canonical inventory promotion is gate-owned

`build_admitted_inventory()` always produces a partial admitted inventory identity and never declares a canonical 100-session identity merely because row count reaches 100.

A separate `finalize_canonical_admitted_inventory()` invokes the frozen `validate_session_inventory()` over the actual 100 projected artifacts/manifests, rehashes child evidence, reruns final validation, and only then exposes `canonical_admitted_gate_inventory_sha256`.

### 4. Counter attestation requires finalized canonical inventory

The counter reconciler now requires target exactly 100, valid internal counts, unique chronological sessions, and exact equality to admitted inventory sessions. At 100/100 it will not publish a counter attestation unless supplied the explicit frozen-gate-validated canonical inventory identity, which it revalidates before attestation.

### 5. Isolated staging-root guard

Real write modes require an isolated pre-access staging root. Source/output overlap, repo/data/runtime overlap, and protected-semantic paths fail closed before publication.

### 6. Prior-access semantics corrected

An explicitly configured canonical real evaluation root is considered clean only when the existing frozen status-only inspector returns `PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT`. `SYNTHETIC_REHEARSAL_COMPLETE` is not accepted as proof of a pristine real root; real-completed, orphan/interrupted, and integrity-failure states are provenance-invalid. No protected loader is called.

### 7. Session Audit/PaperState bridge is source-bound

The PaperState assembler no longer treats a free-form caller assertion such as `continuity_valid=true` as authority. The public bridge must identify persisted Session Audit V1 ledgers by path/SHA. The consumer revalidates source audit schema/session/anchor/guards/overall status, exact predecessor snapshot identity, PaperState parent chain, and terminal execution/missed-execution runtime-snapshot cross-binding.

A legitimate `MISSED_EXECUTION_NO_CERTIFIED_OPEN` remains a preclassified operational invalidity rather than being relabeled as an implementation defect.

### 8. Benchmark readiness uses the evaluation boundary

Benchmark readiness is evaluated against the exact PaperState predecessor plus admitted prospective sessions, not all dates in the local calendar archive. Calendar archive coverage is retained only as a separate diagnostic. Audit-only mode is read-only even if the evaluation boundary eventually reaches 100 sessions.

### 9. Real report status is causal

The CLI no longer hard-codes a development `REVIEW_READY` verdict as the prospective experiment state. Component/overall provenance-invalid or implementation/access-contamination states propagate monotonically. A healthy partial run remains `ACCUMULATING_OUTCOME_BLIND`; real protected preflight remains `PRE_FLIGHT_BLOCKED` while required final evidence is absent.

### 10. Full synthetic producer-path rehearsal

The synthetic test no longer starts from hand-crafted final score/paper/benchmark/access attestations.

It now exercises:

`100 production-shaped 14-column synthetic scores`

`-> actual score projection producer`

`-> partial admitted inventory`

`-> frozen-gate canonical inventory finalizer`

`-> actual counter reconciliation/attestation`

`-> persisted synthetic Session Audit ledgers + PaperState chain`

`-> actual PaperState attestation assembler`

`-> explicit clean prior-access root + actual prior-access producer`

`-> predecessor + 100 synthetic local IDX Composite source files`

`-> actual benchmark producer`

`-> synthetic-only target attestation`

`-> candidate preflight validation`

`-> immutable final preflight bundle`

`-> existing safe evaluator CLI --preflight-only`.

Required final synthetic result is reached in the test suite:

`PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT`

No real target/outcome values are used.

## Real evidence boundary

The previously recorded real, outcome-blind source evidence remains:

- production score sessions: `2026-08-21`, `2026-08-24` (`2/100`);
- runtime counter: `2/100`, `ACCUMULATING`;
- raw rolling inventory SHA: `3510e5b73189e97bc6f40fd96190164d193aceb45d969d55099e0e70221b89ee`;
- raw production-source gate-shape SHA: `5d829936646e2cf2acc1e2ea3d8c8352fd2bf9e18e10c1d858244d869e6d8cff`;
- canonical admitted 100-session inventory: `NOT_AVAILABLE`;
- code-pin manifest SHA: `0012dc4822f676388c427e018c63873b9450ee6cc6067cd67638a439a7f0f65b`;
- sealed target attestation/materializer: `NOT_AVAILABLE`;
- real final preflight: `PRE_FLIGHT_BLOCKED`.

The hardened code was changed through GitHub and validated by merge-tree CI. It has **not** been rerun against the user's Windows-local D: production evidence root in this checkpoint. The earlier two-session projected artifact hashes therefore remain historical evidence from the pre-hardening producer run, not a claim that the hardened producer has regenerated those files. A fresh isolated staging root should be used for the local outcome-blind replay to avoid conflating historical staging bytes with the hardened producer lineage.

## Validation

- GitHub merge-tree CI run `32915265242`: PASS.
- Full pytest: `242 passed`, `4 existing NumPy timedelta deprecation warnings`.
- The full producer-path synthetic rehearsal is included in the passing suite.
- No changed file outside the six-file PR #89 scope plus this checkpoint was introduced by the implementation hardening.

## Guards

- `PROTECTED_OUTCOMES_ACCESSED = FALSE`
- `TARGET_VALUES_LOADED = FALSE`
- `REAL_PROTECTED_LOADER_CALLED = FALSE`
- `REAL_OUTCOME_ACCESS_MARKER_WRITTEN = FALSE`
- `FORWARD_COUNTER_CHANGED = FALSE`
- `MODEL_CHANGED = FALSE`
- `MODEL_REFIT = FALSE`
- `MODEL_RETUNED = FALSE`
- `DECISION_CHANGED = FALSE`
- `SIZING_CHANGED = FALSE`
- `EXECUTION_SCIENCE_CHANGED = FALSE`
- `ACTIVE_RUNTIME_CHANGED = FALSE`
- `SCHEDULER_CHANGED = FALSE`
- `PROVIDER_CAPTURE_TRIGGERED = FALSE`
- `TARGET_MATERIALIZATION_EXECUTED = FALSE`
- `MONTE_CARLO_REOPENED = FALSE`

## Remaining verification before merge approval

One local-only step remains because the production evidence root is not available to the GitHub editing environment: run the hardened outcome-blind producer/audit on a **fresh isolated pre-access staging root** against the two existing production score sessions and current safe metadata, without provider calls or protected access. Confirm deterministic rerun hashes, `2/100 ACCUMULATING_OUTCOME_BLIND`, and no runtime/counter/scheduler mutation.

After that local replay and exact-head CI on the final documentation head, the lane may be presented for independent merge review as:

`V4_X1_PREACCESS_ARTIFACT_COMPLETION_V1_FINAL_REVIEW_READY`
