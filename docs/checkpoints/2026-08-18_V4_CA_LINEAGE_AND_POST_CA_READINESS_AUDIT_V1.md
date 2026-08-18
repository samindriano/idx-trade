# V4 CA Lineage + Post-CA Execution Readiness Audit V1

Date: 2026-08-18 (Asia/Jakarta)
Branch: `review/idx-v4-ca-lineage-readiness-audit-v1`
Parent: `data/idx-v4-ca-targeted-schedule-evidence-v1@a980d33e9e4ea63306c6af3cf174c329e58f49e6`
Status: `CA_LINEAGE_DECISION_VALID_TARGETED_ACQUISITION_SAFE_POST_CA_EXECUTION_NOT_YET_AUTHORIZED`

## Scope

Independent repository-only audit of the V4 corporate-action continuity lineage and the code path that would follow a future CA certification. No provider call, external `D:` artifact access, target/return/rank materialization, model fit, prediction, performance metric, bootstrap, protected outcome, or fresh-forward outcome access was performed.

The audit asks two separate questions:

1. Is there evidence that the CA work completed so far is decision-invalid because of a lineage, parser, event-identity, cross-source, date-binding, continuity, or attribution mistake?
2. If the pending targeted seven-event acquisition causes the frozen CA gate to certify, can V4 immediately materialize historical targets and fit/evaluate the frozen models without another preparation step?

## Executive verdict

### Scientific CA lineage

**No decision-invalidating error was found in the promoted/frozen CA lineage reviewed in this audit.** The current scientific state remains exactly what the latest replay says: CA continuity is still blocked pending the frozen seven-event targeted evidence run; none of the optimistic attribution exercises constitutes certification.

The prepared targeted acquisition itself is safe to execute under its frozen handoff. Its seven identities are exact and hash-pinned, including the corrected canonical PANI event ID. The NISP static-cash path is event-scoped and fail-closed; the six mechanical paths require explicit official regular-market transition evidence. The continuity replay rebuilds from the frozen base and can convert newly exact events into known mechanical crossings rather than waiving them.

### Post-CA execution readiness

**V4 must not jump directly from a future CA PASS to historical target/model execution.** Two P1 engineering/provenance bridges are still missing:

1. deterministic conversion of the final CA continuity ledger into the frozen target executor's exact provenance schema;
2. a separately frozen post-CA execution authorization/orchestrator that verifies the accepted CA result and execution-code/runtime identities before the first historical target access.

These are readiness blockers, not evidence that the CA results are wrong.

## CA lineage audit findings

### 1. Frozen event-window semantics remain fail-closed — PASS

The current event-window implementation admits only explicit accepted continuity states. Unknown/missing schedule evidence remains unresolved; exact mechanical transitions block only when `entry_date < transition_date <= terminal_date`; entry on the transition date is treated as already post-event basis. Missing KSEI coverage and cross-source conflicts remain fail-closed. No price-jump, adjusted-price, Record/Distribution fallback, or generic IDX `TanggalPencatatan` effective-date inference was found.

Known mechanical crossings are never waived by attribution scenarios. The latest accepted replay before the pending targeted lane preserves 240 crossing rows.

### 2. KSEI coverage-gap remediation lineage — PASS

The 43-ticker remediation recovered 31 tickers using the same strict KSEI registered-security parser and left 12 unresolved. Recovery exposed 24 active mechanical rows rather than treating recovered coverage as automatically harmless. This is evidence that the fail-closed design worked as intended.

Current accepted logical coverage remains 598/610 tickers; the 12 unresolved tickers remain explicit blockers. No 610-ticker recrawl, alias substitution, parser relaxation, or alternate provider was admitted.

### 3. Optimistic blocker attribution — PASS WITH WORDING BOUNDARY

Blocker Attribution V2 and Schedule Event Impact Attribution V1 are counterfactual diagnostics only. They correctly preserve known mechanical crossings and label their clearing scenarios as optimistic upper bounds.

The seven-event set `NISP, ISAT, ADRO, PANI, RAJA, PTRO, CUAN` is an inclusion-minimal deterministic acquisition-priority set under the frozen greedy/reverse-prune procedure. It is **not** proven to be the global minimum, and a 600/600/600 counterfactual is not a certification forecast because newly exact transitions may themselves cross target windows.

### 4. Seven-event identity and targeted-lane preparation — PASS

The selected-subset artifact is hash-pinned and the acquisition runner asserts the exact event IDs/tickers/source types. The canonical PANI event identity is:

`82e09144ecfe0d4375a9260156fe75dd74ed01a2cd72262f55e14cd85ce6ebc7`

The previously observed documentation transcription mistake was corrected before provider execution and is not present in the runtime identity contract.

The targeted runner verifies the selected-subset SHA and official-calendar SHA before creating the output root/provider sequence. The direct scripts bootstrap repository `src` themselves, closing the earlier PYTHONPATH failure class.

### 5. Cross-source conflict logic — CURRENT DATA DECISION-VALID, IMPLEMENTATION FRAGILE

The event-window runner currently defines a prior candidate ticker as represented when KSEI contains any mechanically relevant event for that ticker in the broad study period. That ticker-level rule is weaker than an explicit event-level reconciliation and could be unsafe on a different candidate set.

The promoted frozen candidate set was therefore independently reconciled in:

`docs/artifacts/v4_ca_lineage_readiness_audit_20260818_v1/cross_source_reconciliation.csv`.

Result:

- BBNI's 2023-10-06 IDX candidate lies outside the frozen selection halo and cannot cross a frozen target interval.
- ISAT, MLPT, and RAJA have temporally aligned KSEI source-native `Mandatory Conversion` counterparts to their IDX stock-split candidates.
- SINI has the same rights/HMETD family in KSEI within the same bounded issuance episode; the KSEI regular-market transition is used, while the later IDX `TanggalPencatatan` is not used as an effective-date fallback.
- MEGA and SCMA remain explicitly unrepresented and are still fail-closed cross-source conflicts.

Therefore no actual false-clear was identified in the frozen promoted population. **However, before final CA certification is accepted for target execution, an explicit event-level reconciliation assertion should replace or independently attest the current ticker-level representation shortcut.** This can be an outcome-blind offline bridge; it does not require changing V4 target/model contracts.

## Post-CA readiness audit findings

### 6. Frozen target/execution code identity — PASS

The current repository blobs for the frozen execution modules match the captured execution-code commit `7f6b90e0ed09347c5f0fa638b6c3ba3e73273d59`:

- `ranking_v4_3_features.py` Git blob `59ad05f815870ae00480dc7945fe18371d8eff9c`
- `ranking_v4_3_model_eval.py` Git blob `8aba40c32e6069d1f8bdf5b8b19bf41d2065c422`
- `ranking_v4_3_preregistration.py` Git blob `cc1308feb51bbed16606bf7bded1ca0111644326`
- `ranking_v4_3_target_execution.py` Git blob `9b82a0fe8bf06134a06e4a4bfdec15fd10b2bdf4`
- target-execution protocol Git blob `c3fab424c49022c8d6e223f3d722a3b3b55637f8`

The accepted local prefit validation recorded 40 focused tests passing, preserved frozen 6x100 validation identity, zero state-conflict keys, and an exact accepted runtime/code manifest. No silent execution-code drift was identified.

### 7. Frozen model/evaluator implementation — PASS ON REPOSITORY REVIEW

Repository review found the expected frozen mechanisms:

- causal trailing-60 primary-liquidity state;
- exact rank transform with average ties and singleton 0.5;
- tail-600 validation identity split into six 100-date folds;
- H10 purge maximum training signal index `validation_start - 10 - 1` (s-11);
- equal total learner weight per training date;
- fixed HGBR parameters/no hyperparameter search;
- Control versus Geometry3 challenger separation;
- score-percentile consensus fixed 0.5/0.5;
- date-centric observability gates;
- Top30/Bottom30 identities selected before target observability with no refill;
- moving 10-date block bootstrap, 2000 replications, seed 42;
- paired/common-support challenger comparisons.

No obvious leakage, post-hoc tuning, validation-row refill, or outcome-based contract rescue path was found.

### 8. P1 blocker: CA continuity provenance adapter is missing

The frozen target executor requires one unique continuity row per:

`(ticker, signal_date, horizon)`

with required fields:

`ticker, signal_date, horizon, continuity_status, policy_id, evidence_id, evidence_sha256`.

`prepare_continuity_evidence()` explicitly rejects missing provenance, duplicate identities, malformed SHA, or unsupported continuity states.

The current CA event-window ledger/replays output identity/status/reason/blocking-event fields and `policy_id`, but do **not** output `evidence_id` and `evidence_sha256` in the target-executor contract shape. No existing deterministic bridge/materializer was found in the repository.

Required remediation before historical target access:

- freeze a deterministic outcome-blind continuity-provenance adapter;
- derive `evidence_id` from immutable final CA result identity/policy and row identity;
- bind `evidence_sha256` to the exact accepted CA evidence/result bytes under a documented canonicalization rule;
- assert exact 344,790 horizon-row identity and exact H5/H10 ticker-set symmetry;
- synthetic-test missing, duplicate, mutated, unsupported, and stale-result cases;
- do not materialize R5/R10 while building/testing the adapter.

### 9. P1 blocker: historical execution authorization/orchestrator is missing

The frozen target-execution protocol still truthfully states:

- `target_materialization=false`
- `model_fit=false`
- blocker = CA continuity not yet accepted.

The repository contains the frozen modules and support/runtime/code-capture scripts, but no one-shot historical runner that safely performs the complete post-gate sequence. There is also no separate post-CA authorization artifact that proves the blocker was cleared while preserving the immutable target/evaluator/preregistration contracts.

Before first historical target access, freeze one execution generation that verifies at minimum:

1. accepted final CA continuity summary/manifest and exact 600-date gate pass;
2. explicit event-level cross-source attestation;
3. deterministic continuity-provenance adapter output;
4. frozen 600 validation identity and PIT support identity;
5. accepted prefit runtime manifest;
6. exact execution-code manifest/source hashes;
7. exact preregistration SHA;
8. fresh output roots and no protected-forward access;
9. target materialization exactly once, then frozen Control/Challenger execution/evaluation without tuning or rerun rescue.

The old protocol should not be edited to pretend it was always authorized. A new post-gate authorization/run manifest should reference the immutable old protocol and the accepted CA gate.

### 10. Hardening: H5/H10 CA population symmetry should be asserted explicitly

The CA per-date consensus calculation uses the H5 decision population as denominator and intersects H5/H10 resolved ticker sets. Current frozen ledger construction produces exactly two horizon rows per decision identity, and prior row counts/duplicate checks are consistent with symmetric H5/H10 populations. No current result discrepancy was identified.

Nevertheless, the final provenance bridge should assert that H5 and H10 ticker sets are identical for every signal date before consensus certification is admitted. This closes a silent denominator-drift failure class.

## Non-scientific hygiene observation

A four-byte temporary checkpoint file `docs/checkpoints/__tmp_should_not_create.md` is present in the branch tree. It has no scientific effect and was not touched in this audit. Repository hygiene may remove it separately; it must not be mixed into CA scientific remediation.

## Ordered next actions

1. **Do not reopen prior broad CA acquisition.** Existing lineage remains decision-valid under this audit.
2. Execute the already frozen seven-event targeted KSEI acquisition/replay when local capacity is available; no design change is required for the acquisition itself.
3. If the replay remains blocked, continue only with outcome-blind blocker attribution/evidence work; do not touch V4 target/model.
4. If the replay reports CA certification, do **not** materialize targets yet. First freeze/validate:
   - event-level cross-source attestation;
   - continuity provenance adapter;
   - post-CA historical execution authorization/orchestrator.
5. Only after those review gates pass may the first historical R5/R10 materialization and frozen V4-3 Control/Geometry3 6x100 execution occur.

## Final audit verdict

`CA_LINEAGE_DECISION_VALID_TARGETED_ACQUISITION_SAFE_POST_CA_EXECUTION_NOT_YET_AUTHORIZED`

This verdict does not predict that the seven-event run will certify continuity. It says the work completed so far does not need to be discarded or rerun based on repository evidence reviewed here, while also preventing a premature jump from a future CA PASS into historical target/model execution.
