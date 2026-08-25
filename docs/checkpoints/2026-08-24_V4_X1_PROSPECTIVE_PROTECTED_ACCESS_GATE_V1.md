# V4-X1 Prospective Protected Access Gate V1 — Checkpoint

Superseded for current audit status by
`docs/checkpoints/2026-08-25_V4_X1_PROSPECTIVE_EVALUATION_GATE_AUDIT_V1.md`.
The protected-access boundary remains outcome-blind and real access remains
blocked pending canonical target identity resolution.

Date: 2026-08-24 (Asia/Jakarta)

Status: `V4_X1_PROSPECTIVE_PROTECTED_GATE_V1_SYNTHETIC_VALIDATED_REAL_ACCESS_PENDING_100_OF_100`

## Controlling frozen science

- Model: `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`
- Generation: `V4-X1-CLEAN`
- Fingerprint: `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`
- Protocol: `V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1_FROZEN_OUTCOME_BLIND`
- Protocol commit: `ed719dd67ae93b6b20f02579df80fd67eec331dd`
- Protocol Git blob: `f76af5733db3c6a2c7a99b1e80268004ece1e616`
- Frozen evaluator implementation commit: `0bf9ff5bc4b3ef6639d48823c75437f0359c6bc7`
- Frozen evaluator Git blob: `ce7a6d356b0b1ab52277c50411fdfb86ac59ad4c`

The protected access adapter was implemented only after the protocol and metric engine were fixed. It does not modify any alpha, Decision, Sizing, Execution, metric, bootstrap, benchmark, or verdict definition.

## Implementation

Added:

- `src/idx_trade/prospective_evaluation_gate_v1.py`
- `tests/test_prospective_evaluation_gate_v1.py`

Final reviewed Git blobs at this checkpoint:

- protected gate: `cfbc7fa1c37cf6b68cfcddb4507bc7d6bb1fdc7a`
- protected gate tests: `157bf57c4a1df06a5aa8f46b3f530a7560dc3002`

The gate deliberately contains no provider call, network call, vault-path discovery, automatic unlock, scheduler mutation, or outcome source selection.

## Pre-outcome access gates

Before the injected protected loader can execute, the runner requires all of the following to pass:

1. access mode is known;
2. real mode has explicit final-access authorization;
3. protocol bytes match the frozen protocol Git blob;
4. evaluator bytes match the frozen evaluator Git blob and evaluator commit pin;
5. the immutable forward inventory contains exactly 100 positions numbered `1..100`;
6. session dates and official session indices are unique and strictly increasing;
7. every score artifact and manifest exists and matches its declared SHA-256;
8. every score manifest is `DONE` and binds exactly to the frozen model id, generation, fingerprint, session date and child score hash;
9. every frozen score-manifest guard confirms no prospective outcome access/refit/retune/science change;
10. the canonical counter attestation is exactly `100/100` and binds to the exact inventory hash;
11. the canonical target is uniquely resolved, has a nonblank resolution lineage, and is matured `100/100` over the same first/last session boundary;
12. the canonical target source manifest exists and matches its pre-access SHA-256;
13. PaperState/execution continuity is either valid or explicitly preclassified invalid with a reason before outcome access;
14. the PaperState attestation binds the exact predecessor + 100-session boundary;
15. the IHSG benchmark is either pre-pinned with exact artifact hash and evaluation-boundary coverage, or explicitly frozen as `UNAVAILABLE`;
16. the access audit is complete, says no unauthorized outcome access is known, and says no prior real access marker exists.

Any failure in those gates occurs before the protected loader callback and before an access marker is written.

## Marker-before-loader ordering

First-time successful access follows this order:

```text
validate all pre-outcome gates
    -> write immutable pre_outcome_access_attestation.json
    -> fsync
    -> write immutable outcome_access_marker.json
    -> fsync
    -> call injected loader
    -> bind loaded target/PaperState metadata back to pre-access hashes
    -> run frozen evaluator functions
    -> write immutable result
    -> write immutable final result manifest
```

The synthetic test suite asserts the exact event order:

`PREATTESTATION_WRITTEN -> MARKER_WRITTEN -> LOADER_CALLED -> FINAL_RESULT_WRITTEN`.

The real marker string is `V4_X1_PROTECTED_OUTCOME_ACCESS_STARTED`. Synthetic rehearsal uses the distinct marker `V4_X1_PROTECTED_OUTCOME_REHEARSAL_STARTED`, and rehearsal output/artifacts are confined below the explicit synthetic fixture root.

No real marker has been written by this work.

## Post-access binding

After the marker and only after the injected loader returns, the runner still fails closed unless:

- loader metadata repeats the exact canonical-target id;
- target-source-manifest hash matches the pre-access target attestation;
- PaperState-attestation hash matches the pre-access attestation;
- counter-attestation hash matches;
- session-inventory hash matches;
- protected target rows exactly match the immutable frozen score `(session, ticker)` keys;
- all targets are finite;
- score/date/index alignment matches the frozen 100-session inventory;
- evaluation ledger exactly covers the same 100 sessions;
- a valid PaperState path contains exactly one predecessor mark plus the 100 prospective marks;
- execution/order diagnostics are available for an operationally valid PAPER path.

A PaperState break that was explicitly classified before access can still permit alpha evaluation, but the overall result is forced to `PROSPECTIVE_INVALID_OPERATIONAL`; weak performance cannot be relabeled operational invalidity after the fact.

## One-shot / idempotency contract

- A successful first run writes immutable preaccess, marker, result and final-manifest files.
- A rerun with a complete hash-valid result returns the persisted result without calling the protected loader again.
- Marker + missing/corrupt result, post-access failure evidence, or any other partial prior state fails closed for manual forensic recovery.
- A post-marker provenance/target mismatch writes `post_access_failure.json` and does not silently retry/reopen outcomes.
- Existing immutable files are never overwritten by the runner.

This prevents duplicate outcome opening and prevents a failed post-access run from being silently turned into a second discretionary evaluation.

## Validation

Draft PR #83 was used only to exercise the full repository merge-tree CI. GitHub Actions run `32748811644` completed successfully:

```text
........................................................................ [ 63%]
..........................................                               [100%]
114 passed, 4 warnings in 37.83s
```

The four warnings are pre-existing NumPy timedelta deprecation warnings in tradability tests, not evaluation-gate failures.

The new gate test matrix covers, among other cases:

- exact protocol blob pin;
- marker-before-loader ordering;
- `99/100` counter pre-access block;
- non-100 session inventory pre-access block;
- score-manifest outcome-guard tamper;
- score-manifest fingerprint tamper;
- target maturity `99/100`;
- unresolved canonical target;
- unclassified PaperState invalidity;
- preclassified PaperState invalidity forcing overall operational invalidity;
- known prior outcome-access contamination;
- protocol/evaluator byte tampering;
- explicit real-access authorization boundary;
- benchmark hash tampering;
- pre-frozen `BENCHMARK_UNAVAILABLE` handling;
- post-access metadata binding failure;
- post-access target-key mismatch;
- successful idempotent replay without loader re-entry;
- orphan/partial marker state fail-closed behavior.

## Scientific and operational boundary

At this checkpoint:

- `PROSPECTIVE_OUTCOMES_ACCESSED = FALSE`
- `REAL_PROTECTED_LOADER_CALLED = FALSE`
- `REAL_OUTCOME_ACCESS_MARKER_WRITTEN = FALSE`
- `SYNTHETIC_REHEARSAL_ONLY = TRUE`
- `MODEL_RETUNED = FALSE`
- `DECISION_CHANGED = FALSE`
- `SIZING_CHANGED = FALSE`
- `EXECUTION_CHANGED = FALSE`
- `SCHEDULER_CHANGED = FALSE`
- `FORWARD_COUNTER_CHANGED = FALSE`

The code is prepared before outcome access, but the real runner is not authorized to run merely because it exists. The actual 100/100 evaluation remains contingent on the frozen final-access gates and explicit final authorization at maturity.

Final checkpoint verdict:

`V4_X1_PROSPECTIVE_PROTECTED_GATE_V1_SYNTHETIC_VALIDATED_REAL_ACCESS_PENDING_100_OF_100`
