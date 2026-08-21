# Decision V3 Graded Evidence V2 — Independent Structural Replay Runner Audit

Date: 2026-08-21 Asia/Jakarta

Status: `RUNNER_AUDIT_ACCEPTED_READY_FOR_SINGLE_LOCAL_600_OOS_REPLAY`

This audit reviews the Decision V3 structural replay **runner**, not the historical Decision V3 result. No Decision V3 600-OOS historical replay was executed during this audit.

Reviewed Decision lineage:

- preregistration branch `research/idx-decision-v3-graded-evidence-prereg-v2`;
- preregistration HEAD `e9882e1b436f19e860d826a9c02a6bb3f1d46dcc`;
- implementation rule ID `V4_X1_DECISION_V3_GRADED_EVIDENCE_V2`;
- implementation validated code HEAD `c89ecb4f88e98cc23c140f15dee13ca423a92f5c`;
- implementation audit verdict `IMPLEMENTATION_AUDIT_ACCEPTED_REPLAY_RUNNER_PREP_ONLY`.

Reviewed runner lineage:

- branch `research/idx-decision-v3-graded-evidence-structural-replay-runner-v2`;
- validated runner code HEAD `c8c964a65d43c343803125f398c0665e6cc5cdf9`;
- runner checkpoint/docs HEAD `2c9fff1c3729d93283d774fba2d5c9f7529016e8`;
- implementation PR #55;
- GitHub Actions run #1128: `526 passed`, `26 warnings`, `0 failed`.

Frozen replay contract:

- `docs/specs/decision_v3_graded_evidence_structural_replay_contract_v2.json`;
- status `FROZEN_BEFORE_FIRST_REPLAY`;
- canonical JSON SHA-256 `4d16f2f8ca1a274e7d98cc8be24daaa0f4eb77bfc6e56ecf90c6f42f1b13239f`;
- `execution_authorized=false` remains unchanged in the frozen scientific artifact.

Audit verdict authorizes exactly **one local execution of the frozen historical 600-OOS Decision V3 structural replay** using the audited CLI/interlock and a fresh output directory. It does not authorize policy modification, threshold variants, rescue experiments, returns/PnL inspection for tuning, or downstream paper/live activation.

## 1. Lineage and immutability — PASS

Comparison from the accepted Decision V3 implementation branch to the runner checkpoint shows runner work is additive only:

- claim/handoff/checkpoint/contract;
- strict source loader;
- replay orchestration;
- post-replay integrity guard;
- descriptive reporting;
- guarded CLI;
- synthetic/adversarial tests.

No Decision V3 policy engine, Decision V2 engine/result, V4-X1 alpha model, scoring code, frozen alpha artifact, sizing/execution logic, or existing scientific data artifact was modified by runner work.

The runner therefore cannot silently redefine Decision V3 through mutation of the accepted policy implementation.

## 2. Preregistration ↔ machine profile ↔ replay contract ↔ runtime gates — PASS

The runner preserves the exact hard structural gates frozen before the V3 result exists:

- mean replacements `<=2.25`;
- turnover versus naive exact daily Top10 `<=0.50`;
- share of transitions with at least three replacements `<=0.35`;
- median completed holding spell `>=3`;
- one-session completed holding share `<=0.35`;
- mean current Top10 overlap on full targets `>=6`;
- mean target rank `<=12`;
- mean target size `>=9`;
- share target-size 10 `>=0.70`;
- share target-size `<=8` `<=0.10`;
- zero processed targets above rank 50;
- zero second-consecutive retained observations in rank 21..50;
- zero post-bootstrap previous-absent entrants;
- immediate universe-exit integrity.

Tests pin numeric threshold parity and exact inclusive boundary behavior. No threshold is relaxed or conditionally rewritten based on a V3 historical result.

Tier-C lifecycle and high-churn mechanism diagnostics are explicitly descriptive-only and are not included in acceptance-gate computation.

## 3. Frozen historical source identity — PASS

The authorized source path requires:

- source manifest SHA-256 `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`;
- score parquet SHA-256 `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`;
- exactly 600 sessions;
- exactly 172,697 score rows;
- exactly one fold and one mode per score session;
- frozen naive Top10 replacement comparator exactly `3127`.

Decision lineage comparators are also pinned before V3 execution:

- Decision V1 replacements `2686`;
- Decision V2 replacements `1435`;
- Decision V2 result manifest SHA-256 `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`;
- Decision V2 plan digest `51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4`.

This prevents comparator drift after seeing the V3 result.

## 4. Outcome-blind source projection — PASS

The strict parquet reader first inspects schema/metadata and then reads only:

- `ticker`;
- `date`;
- `fold`;
- `mode`;
- `alpha_consensus`.

It does **not** read `alpha_h5`, `alpha_h10`, realized returns, target labels, or any other extra parquet column. A test constructs a parquet containing head-specific alpha values and fake return/target columns and verifies those columns remain outside the projected frame.

`alpha_consensus` is used only to deterministically reconstruct `rank_consensus` by descending consensus alpha with ticker ascending as tie-break. The Decision policy adapter receives only `ticker` and `rank_consensus`.

No provider call, network call, score regeneration, return/PnL access, protected-forward access, or fresh-forward access exists in the audited CLI path.

## 5. Replay chronology and state continuity — PASS

The runner enforces:

- empty shadow state at replay index 0;
- exact current Top10 bootstrap on index 0 only;
- no pre-roll;
- each later `previous_verified` date equals exact score date `index-1`;
- state `as_of_session_date` equals the exact immediately previous score session;
- bound state `rule_id` equals `V4_X1_DECISION_V3_GRADED_EVIDENCE_V2`;
- state advances only through `DecisionV3ShadowState.from_plan(plan)`;
- fold boundaries are recorded but never reset Decision state.

The runner therefore preserves one continuous path through all 600 exact OOS score sessions rather than restarting around folds.

## 6. Independent Decision permission validation — PASS

The replay does not rely solely on the Decision engine declaring its own behavior valid. `_validate_plan_permissions` independently reconstructs and checks:

- target ceiling and uniqueness;
- bootstrap index/rule identity;
- every non-bootstrap buy is current Top10;
- previous-absent entry prohibition;
- Tier-A previous-rank `<=20` permission;
- Tier-B previous-rank `21..50` permission;
- Tier-C previous-rank `>50` permission;
- Tier B/C never soft-replace;
- mandatory-exit count and resulting vacancy count;
- expected deterministic vacancy sequence A -> B -> C;
- first mild deterioration is retained;
- severe rank `>50` is not retained;
- second-consecutive mild rank `21..50` is not retained;
- universe/mandatory exits are not retained;
- soft replacement uses Tier A and inclusive rank gap `>=5`;
- row-order permutation produces an identical plan.

Synthetic tampering tests confirm the validator detects illegal Tier-B soft-replacement behavior.

## 7. Adversarial post-replay target/intent integrity — PASS AFTER HARDENING

During review, one fail-closed coverage gap was identified: the per-plan validator primarily reasoned from engine observations/intents, so an impossible-but-corrupted emitted ledger could theoretically contain a phantom target not represented by the expected plan pathway.

This did **not** indicate a Decision policy bug; the accepted engine itself does not manufacture such targets. The runner was nevertheless hardened before audit acceptance with a second independent check over emitted ledgers plus the full pinned rank path.

Before any reporting/artifact promotion, the CLI now aborts if it observes:

- target ticker missing from current rank universe;
- target rank `>50` after processing;
- non-bootstrap target entry outside current Top10;
- non-bootstrap target entry absent from the previous universe;
- target entry with no corresponding BUY intent;
- BUY intent not present in final target;
- missing `UNIVERSE_EXIT` sell intent for an incumbent disappearing from the next universe;
- disappeared incumbent retained in target.

This layer cannot relax a gate or convert REJECT to ACCEPT. It can only abort artifact promotion. Dedicated tampering tests cover target-without-buy, buy-without-target, and missing-universe-exit cases.

## 8. Determinism — PASS

Two independent determinism checks are present:

1. every session is replanned with reversed score-row ordering and must match the primary plan exactly;
2. the entire replay is run twice using the same already-loaded pinned rank path and the exact same frozen Decision policy.

The second pass is not an alternative Decision policy, threshold, or source access. Plan digests and emitted ledgers must match exactly.

## 9. Structural metrics and V3-specific diagnostics — PASS

The runner records full session, membership, intent, state, holding-spell, and fold-boundary ledgers.

Core structural metrics cover:

- replacement counts/distribution and comparator ratios;
- holding-spell distribution including right censoring;
- Top10/Top20 overlap and target-rank quality;
- target-size/capacity distribution;
- mild pending/recovery and exit-state attribution;
- Tier A/B/C vacancy fills and Tier-A soft replacements;
- Tier-D rejection count;
- six fixed 100-session blocks and fold segments.

V3-specific descriptive diagnostics include:

- Tier-C entrant count;
- Tier-C completed holding duration distribution;
- Tier-C one-session holding share;
- next-session Tier-C state distribution;
- Tier-C next-session severe-exit count and unique sessions;
- replacement-seat changes on those severe-exit sessions;
- component-wise high-churn attribution for transitions with replacement count `>=3`.

High-churn attribution intentionally reports overlapping mechanism components rather than inventing a post-hoc single causal class.

## 10. Reporting cannot tune gates — PASS

Reporting enrichment runs after gate evaluation and:

- re-verifies the canonical replay-contract hash;
- records `gate_values_changed=false`;
- adds rank `>20` / `>50` distributions and per-session count distributions;
- marks Tier-C/high-churn diagnostics descriptive-only.

Tests confirm reporting enrichment leaves the existing gates and verdict unchanged.

## 11. Artifact output is fail-closed — PASS

The writer:

- refuses an existing destination;
- refuses an existing `.staging` directory;
- writes into a fresh staging directory;
- hashes each emitted artifact;
- writes `MANIFEST.json` with source guards, plan digest and artifact hashes;
- only then renames staging to the final destination.

An interrupted write may conservatively leave staging that must be inspected/removed manually; the runner will not silently overwrite it. This is fail-closed behavior.

## 12. CLI authorization ordering — PASS

The audited CLI checks the exact process-interlock token:

`DECISION_V3_GRADED_EVIDENCE_STRUCTURAL_REPLAY_RUNNER_AUDIT_ACCEPTED_V2`

before contract verification or historical source access. A bad-token test supplies a nonexistent historical source and verifies authorization failure occurs first and creates no output.

The token is a process interlock, not a cryptographic secret. Scientific one-shot discipline remains procedural and is now authorized only by this accepted audit.

## 13. CI — PASS

Final code validation after all runner hardening:

- GitHub Actions run #1128;
- `526 passed`;
- `26 warnings`;
- `0 failed`.

Warnings are pre-existing pandas/NumPy and GitHub Actions Node deprecation warnings unrelated to the Decision V3 runner.

## 14. Non-blocking scientific risks preserved for replay

The audit deliberately does not patch the following mechanisms because their empirical magnitude is exactly what the preregistered structural replay must measure:

1. Tier-C residual vacancy filling may create delayed churn if distant candidates collapse severely on the next session.
2. Immediate severe exits may cluster and produce high-churn sessions even while improving rank quality.
3. A/B/C vacancy permission may materially improve capacity while still failing rank-quality or churn gates.

These are scientific outcome risks, not runner correctness defects. No threshold, tier boundary, confirmation length, gap, or gate may be changed before the single replay based on anticipation of these risks.

## 15. Final verdict and authorization boundary

Verdict:

`RUNNER_AUDIT_ACCEPTED_READY_FOR_SINGLE_LOCAL_600_OOS_REPLAY`

Authorized next action:

- execute the frozen CLI **once** against the exact pinned historical source;
- use a fresh output directory;
- preserve all emitted artifacts and hashes whether verdict is ACCEPT or REJECT;
- inspect the frozen structural verdict and preregistered diagnostics only after output is sealed.

Still prohibited:

- rerunning parameter/policy variants;
- changing severe threshold 50, Tier boundaries, gap 5, or confirmation length after seeing the result;
- H5/H10 rescue in the same Decision V3 result;
- return/PnL/outcome-driven Decision tuning;
- alpha V4-X2 refit as a rescue reaction;
- activating sizing/execution/paper/live solely because the runner audit passed.

The historical replay itself is the next scientific event; this audit contains no Decision V3 historical outcome.
