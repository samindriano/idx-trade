# OHLCV O2 Forward Readiness — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Reviewed branch: `research/idx-ranking-ohlcv-o2-forward-v1`
Reviewed HEAD: `137d1007d935efe5f53fb12b1ce609a933d9540a`
Decision: `O2_FORWARD_READINESS_BLOCKED_RESUME_MANIFEST_FIX_REQUIRED`

## Accepted findings

The overall O2 forward-scoring design is accepted in principle:

- frozen O2 and canonical V3-B model identities/hashes are pinned;
- no official O2 score artifact or counter entry has been created;
- no protected forward outcome was accessed;
- no provider call, retraining, tuning, calibration, or pre-freeze backdating occurred;
- post-close eligibility, exact O2 geometry validation, paired V3-B scoring, outcome guards, gap detection, and monotonic counter semantics are implemented;
- focused and full tests pass on the submitted implementation.

## Blocking issue found in independent code review

`persist_session_score_artifact(...)` writes the JSON manifest to disk and only afterward adds `manifest_sha256` to the in-memory dictionary returned to the caller.

Therefore the persisted JSON file itself does not contain `manifest_sha256`.

On the first process, `OfficialO2Counter.register(...)` can succeed because it receives the augmented in-memory dictionary. However, after a process restart, a call that encounters the already-existing session artifact loads and returns the persisted JSON manifest, which lacks `manifest_sha256`. `OfficialO2Counter.register(...)` requires both `artifact_sha256` and `manifest_sha256`, so the same valid immutable session can fail registration on the resume/recovery path.

The current tests cover write-and-register in one process but do not cover:

`write -> restart/reload existing artifact -> register/resume counter`.

This is a forward-ledger reliability blocker because the 100-session program must be restart-safe and cannot depend on one uninterrupted process.

## Required bounded fix

Before official O2 scoring begins:

1. make reloading an existing immutable session artifact produce a verifiable manifest hash in the same semantic form expected by the counter;
2. do not weaken overwrite refusal or outcome guards;
3. add an explicit restart/resume test covering an already-persisted session artifact;
4. verify counter persistence/reload remains monotonic and cannot rewind or change the first-post-freeze boundary;
5. keep official score artifacts/counter entries at zero during this fix;
6. no provider calls or protected outcomes.

No redesign of the model, features, gate length, or forward evaluation contract is authorized.

## Authorization boundary

Official O2 forward scoring remains **not authorized** until this bounded resume-path fix is implemented, tested, pushed, and independently reviewed.

The historical O2 candidate and final-refit certification remain accepted; this blocker concerns only forward-ledger operational correctness.
