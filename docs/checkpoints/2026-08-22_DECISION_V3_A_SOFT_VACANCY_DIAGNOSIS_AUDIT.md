# Decision V3 A-Soft vs A-Vacancy Diagnosis V1 — Independent Audit

Date: 2026-08-22 Asia/Jakarta

Reviewed implementation HEAD: `85670497e025b409f3d8f5bce4339a6467dd2e31`

Frozen contract canonical SHA-256: `f3d549cafb04fb66735f7a668f6094b800c5354b148361c5d9ba4d9773a57663`

CI run #1149: **542 passed, 38 warnings, 0 failed**.

Verdict: `A_SOFT_VACANCY_DIAGNOSIS_RUNNER_AUDIT_ACCEPTED_SINGLE_LOCAL_EXECUTION_AUTHORIZED`

## What was audited

The implementation is additive relative to the accepted quality-supply diagnosis head. It adds one claim, one frozen contract, one descriptive diagnosis module, one guarded CLI, tests, and an implementation checkpoint. No Decision V3 engine, replay planner, alpha model, source artifact, or prior scientific result is modified.

The runner reads only:

1. the immutable rejected V3 structural replay artifacts through the existing hash-pinned loader;
2. the exact historical consensus-rank projection through the existing strict source loader (`ticker/date/fold/mode/alpha_consensus` only);
3. the already-consumed quality-supply diagnosis `MANIFEST.json` solely for SHA verification.

No return/label/PnL/protected-forward column is read. No provider/network path or model fit/refit path is imported.

## Boundary audit

- CLI authorization is checked before contract or local scientific-artifact access.
- Exact A-entry counts are fail-closed at 721 `A_VACANCY` and 422 `A_SOFT`.
- Both classes are independently revalidated as current Top10 and previous rank <=20.
- Soft replacement peer and inclusive rank-gap >=5 are revalidated from emitted intent plus rank source.
- Candidate evidence uses only rank history available at the entry session or earlier.
- Cross-sectional Top10/Top20 overlap uses only current/prior rank snapshots and is descriptive session context.
- Next-session severe-exit rates exclude terminal entries with no t+1 observation.
- Eventual severe-exit rates use completed holding spells only; right-censored spells do not become false non-severe observations.
- Fixed rank/persistence/stress bins exactly match the preregistered reporting strata.
- The stratified direction summary is descriptive only; sparse cells are not filtered into a policy rule and no minimum-cell threshold is invented.
- Output is fail-closed on existing final or staging directories and SHA-manifested.

## Adversarial interpretation risks retained

### 1. Selection-mechanism confounding

`A_SOFT` is not a randomized version of `A_VACANCY`. Soft replacement requires a >=5-rank advantage over an acceptable incumbent and occurs only after mandatory exits and vacancy fills have already been processed. The diagnosis can show whether candidate-history or session-stress differences explain the observed durability gap, but it cannot establish that converting a vacancy fill into a soft-replacement-style rule would causally reproduce the lower severe-exit rate.

### 2. Session-context imbalance

A-vacancy entries are expected to be concentrated on mandatory-exit/severe sessions. The implementation explicitly reports severe-session-only comparisons plus fixed severe-count and cross-sectional-overlap strata. These reduce descriptive ambiguity but are not causal matching.

### 3. Rank-path selection

Because the V3 policy consumes Tier-A candidates for vacancy fill before using remaining Tier-A candidates for soft replacement, current-rank ordering can differ mechanically between the two entry classes. The diagnosis therefore reports current rank, previous rank, rank delta, and persistence separately rather than assuming one class has stronger raw rank evidence.

### 4. No automatic Decision V4 implication

A result showing A-soft superiority does not authorize a soft-only policy, a vacancy ban, a new persistence threshold, a score-margin rule, or any Decision V4 replay. A successor rule still requires separate brainstorming/preregistration.

## Audit verdict

`A_SOFT_VACANCY_DIAGNOSIS_RUNNER_AUDIT_ACCEPTED_SINGLE_LOCAL_EXECUTION_AUTHORIZED`

Exactly one local descriptive execution is authorized on the reviewed implementation HEAD using a fresh output directory and token:

`DECISION_V3_A_SOFT_VACANCY_DIAGNOSIS_AUDIT_ACCEPTED_V1`

If execution fails after source access, do not automatically rerun; inspect the failure first. A successful execution consumes this diagnosis run. No Decision V4 implementation/replay, PnL inspection, or protected-forward access is authorized by this audit.