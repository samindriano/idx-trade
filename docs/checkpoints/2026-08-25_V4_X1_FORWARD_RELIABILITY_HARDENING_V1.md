# V4-X1 Prospective Gate Resolution + Forward Reliability Hardening V1

Date: 2026-08-25 Asia/Jakarta
Repository: `samindriano/idx-trade`
Origin main at audit: `2be7160f20184e489f7a9f82a0d6aac890622c7e`

## Board

- Phase A — prospective target identity: **PASS for metadata resolution; real access remains blocked**.
- Phase B — forward reliability: **PARTIAL**. Engineering remediations are tested and separated; deployed runtime/task still needs integration before live proof.
- Phase C — evidence completeness: **PASS** for the outcome-blind metadata/hash layer; the observed 2026-08-24 session is correctly `PENDING_EXPECTED`.
- Phase D — fault injection: **PASS for the covered synthetic matrix**; no provider or protected-outcome run was used.
- Phase E — genuine scheduled proof: **NOT_YET_OCCURRED** at 08:14 WIB. The next natural Official Open trigger was 09:02 WIB; no trigger was forced.

## Phase A — canonical target identity

Resolved identity:
`CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1`

The retained pre-prospective lineage proves:

- prediction: `alpha_consensus`, ranked `DESC`, ticker `ASC` tie-break;
- H5: `Close_(t+5) / Open_(t+1) - 1`;
- H10: `Close_(t+10) / Open_(t+1) - 1`;
- within-session average-tie ascending percentile ranks;
- realized consensus: equal-weight H5/H10 ranks, requiring both finite values;
- final evaluator: Spearman on the canonical realized consensus, with the
  frozen common-support/session rules.

Pinned provenance includes:

| Role | Source | Commit | Blob SHA-1 | SHA-256 |
|---|---|---|---|---|
| V4-1 contract | `docs/checkpoints/2026-08-16_RANKING_V4_1_TARGET_CONTRACT_LOCKED.md` | `199d770520edcd4a7b4537c75d5edaba2b0aa349` | `afc4d171cf4f735839782d31256c8894283701f4` | `db756c12574541c434e65866f2a0fd9c639c1e2c227d97cc402d6c02a049e59c` |
| target construction | `src/idx_trade/ranking_v4_3_target_execution.py` | `08233877eb1f94e0ddefcd4f35409923f1c7dda5` | `9b82a0fe8bf06134a06e4a4bfdec15fd10b2bdf4` | `f344874c3619c08605d97058edb8331814cd74c430c60a275a5f96ca48899002` |
| preregistration | `config/ranking_v4_x1_prospective_preregistration_v1.json` | `3db072a7852e7781d49491d91e939cf844c73352` | `a483ebf8ea6618dbadf54b223b54a77435581b8e` | `43cb147e7979cc77575d1fc28893519682e4476af3ff809cb6bd730ac1127750` |
| frozen protocol | `docs/checkpoints/2026-08-24_V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1.md` | `ed719dd67ae93b6b20f02579df80fd67eec331dd` | `f76af5733db3c6a2c7a99b1e80268004ece1e616` | `f17bb558ee50ba8411fd63804c9eef8b984794e39d1a845a6794a144a32566c1` |
| accepted clean OOS review | `docs/checkpoints/2026-08-20_V4_X1_CLEAN_HISTORICAL_OOS_REPLAY_INDEPENDENT_REVIEW.md` | `c4089a4d2e0a4ba8f3cd4e5312bc98c9381902fc` | `442b9b438e1400dd77102cfef24bc8ab0eb3a02c` | `34e701ee02c8de8534b41d8873be246099303dbda3a440165a064b7adf903892` |

Historical IC values are not interchangeable identities:

- `0.097554036`: clean common-support Spearman over 600 dates;
- `0.09805414600339561`: frozen evaluator headline fold-mean statistic;
- `0.099248615`: mean frozen-formula IC over the 600-date slice;
- `0.0980538834688018`: retained prospective point estimate whose exact
  provenance was not recoverable.

The last value remains `UNRESOLVED_CONTEXT_ONLY`; it was not substituted or
used to select the target. Therefore the target identity is resolved while
the historical reference provenance is honestly marked unresolved. PR #83 is
ready for review, not merged, and no protected access was performed.

## Phase B — reliability remediations

| Lane | Final head | PR | Scope | Validation |
|---|---|---|---|---|
| Stockbit | `fix/idx-forward-reliability-v1@2658a56dfe7a5c27f98ec2adaa95d89366f448ae` | [#84](https://github.com/samindriano/idx-trade/pull/84) | retry bookkeeping and resumed quota budget | 27 focused; 78 full |
| Official Open | `fix/idx-e2e-forward-reliability-v1@b9d3d267f87823fef36e7dc5318fbe6ae9935a59` | [#85](https://github.com/samindriano/idx-trade/pull/85) | transport retry/fallback boundary, idempotent verifier replay, runner binding | 61 focused; 760 full |
| Evidence health | `fix/idx-forward-evidence-health-v1@3bef0060ffaf7a480d9a627c24d492340442bd99` | [#86](https://github.com/samindriano/idx-trade/pull/86) | outcome-blind metadata/hash readiness report | 10 focused; 760 full |

### Stockbit incident and fix

The preserved 2026-08-24 shadow run had 962 planned rows, 833 activity-eligible
successes, 129 HTTP-404 no-activity skips, 120,251 normalized points, no 429,
no retries, no synthetic fill, and artifact manifest SHA
`0d4a878e92681dde6c82b0ddf7927502338082188ab301eeebba76e24ab8ac8e`.

The fix prevents verified resumed `OK` rows from consuming new call budget and
clears attempt-local response state before every physical call. A sequence of
retryable HTTP response followed by `RequestException` now yields one terminal
logical record, preserves all physical attempts, and cannot normalize stale
response bytes. The strict all-ticker `DATA_READY` contract is unchanged.

### Official Open fix

Authority remains IDX `TradingSummary/GetStockSummary`; the field remains
`OpenPrice`; transport remains `DIRECT_IDX_THEN_ZAPI_RAW_V1`. Direct capture
uses the accepted warmed `curl_cffi` Chrome transport. Only bounded request
errors and allowlisted transient 5xx statuses retry. Malformed, incomplete, or
empty direct HTTP 200 responses fail closed and do not fall through to Zapi.
Existing manifests are reverified through the real
`verify_open_execution_inputs()` path before `ALREADY_CAPTURED`.

An independent review found that the scheduler's existing headless runner was
still invoking runtime v1 while the remediation lived in runtime v2. The
runner was corrected and tested to invoke `official_open_capture_runtime_v2`;
the old v1 runtime is no longer the runner target in PR #85.

The deployed task still points to a separate runtime checkout. It was not
mutated during this task; integration/deployment must update that checkout
before claiming the next live run exercised the remediation.

### Scheduler and late-evidence policy

Read-only task evidence at 08:14 WIB:

- `IDXTrade-E2E-OfficialOpen`: enabled/Ready, last run 2026-08-24 15:10:52,
  result `4`, next 2026-08-25 09:02;
- triggers: 09:02/09:07/09:12/09:17/09:22 plus AtLogOn;
- `StartWhenAvailable`, `IgnoreNew`, and network requirement remain present;
- `IDXTrade-ForwardOpenArchive` remains disabled and untouched.

The execution-grade window remains 09:02–09:22 WIB. A late source observation
must never create or mutate a missed order. Existing paper orchestration
expires a missing-Open prepared order with zero fills/cost movement and an
explicit no-retroactive-execution record. No broader scheduler was installed
or forced; a separate post-window evidence-resolution contract would need an
already hash-bound pre-open prepared order and distinct processing/economic
timestamps before it could be added safely.

Dependency boundary:

`EOD(t) -> V4-X1 score -> Decision V2 -> prepared order -> Official Open
evidence -> sizing/execution/PaperState`, with Stockbit archive and CA/dividend
evidence as independent sidecars. Stockbit failure does not mutate model,
Decision, Official Open, PaperState, counter, or outcomes. Official Open failure
remains pending/fail-closed and creates no fabricated execution.

## Phase C — evidence health

The outcome-blind health layer reads only JSON metadata and file hashes. It does
not read parquet values, labels, realized outcomes, or protected vault paths.
Protected path tokens are refused; missing required evidence is
`PENDING_EXPECTED`; malformed/hash/identity/guard failures are
`PROVENANCE_INVALID`.

Report for existing 2026-08-24 artifacts:

- EOD and V4-X1 score: `COMPLETE`;
- Stockbit: `COMPLETE_SHADOW`;
- Official Open, Decision, prepared, execution, PaperState: `PENDING_EXPECTED`;
- CA/dividend: `PENDING_EXPECTED`;
- overall: `PENDING_EXPECTED`;
- protected outcomes: `{status: PROTECTED_NOT_READ, accessed: false, values_loaded: false}`;
- report SHA-256: `922163578e424c509981d39ce99e963b992e29be2a52ba4660884ee54f1a2560`.

## Phase D — fault matrix

The focused suites cover Stockbit immediate/retry/schema/auth/malformed/subset/
idempotency/raw/final-record/all-ticker gates; Official Open direct success,
bounded direct retry, transport fallback, malformed/incomplete direct 200,
Zapi retry/provenance mismatch/zero OpenPrice, immutable replay, same-session
idempotency, stale-session and scheduler guards; and paper pending-open,
late-open rejection, duplicate execution, fee/slippage/capacity, predecessor
binding, CA/dividend fail-closed, and crash-recovery paths. The full 760-test
suite also passed on the integration-based Official Open/health branches.

## Phase E — genuine operational proof

No 2026-08-25 scheduled run had occurred at the audit timestamp 08:14 WIB.
The 2026-08-24 Official Open run remains the preserved external failure:
`DIRECT_IDX_REQUEST_ERROR` followed by `ZAPI_RAW_REQUEST_ERROR`; no certified
Open artifact exists. The 2026-08-24 Stockbit shadow artifact is preserved,
but it ran before the new Stockbit branch head. No provider call or forced
capture was made. Verdict: `FORWARD_RELIABILITY_REMEDIATED_NEXT_GENUINE_SESSION_PROOF_PENDING`.

## CI and review state

- PR #83: ready for review; prior head CI success was `32793898183`, and the
  current consolidated-doc head has CI run `32797068204` in progress;
- PR #85: CI pytest success run `32796743113` at final head;
- PR #84: CI pytest success run `32796883273` at final head;
- PR #86: no GitHub check was reported; local focused/full validation passed.

No PR was merged. `coordination/TEAM_STATUS.md` was not edited because root
policy assigns it to MAIN only.

## Boundary assertions

All remain false: no protected loader, outcome marker, labels, model fit,
model/Decision/sizing/execution science, counter mutation, historical E2E
reopen, or Monte Carlo reopen occurred.

## Verdict

`PROSPECTIVE_EVAL_GATE_V1_AUDITED_TARGET_IDENTITY_RESOLVED_REAL_ACCESS_BLOCKED`

`FORWARD_RELIABILITY_REMEDIATED_NEXT_GENUINE_SESSION_PROOF_PENDING`
