# Decision V2 Minimal — Structural Replay Runner Independent Audit

Date: 2026-08-21 Asia/Jakarta

Status: `RUNNER_AUDIT_ACCEPTED_SINGLE_LOCAL_REPLAY_AUTHORIZED`

Audited implementation PR: `#43`

Audited implementation head: `044e8e9a3190935848938ca19d5ea3c9f7c98c01`

Audit branch: `audit/idx-decision-v2-minimal-structural-replay-runner-v1-final`

## Verdict

The Decision V2 Minimal structural replay runner is accepted for exactly one local outcome-blind execution on the pinned 600-OOS V4-X1 historical score path.

This audit authorizes the runner, not the scientific result. The replay has not been executed as part of this audit.

## Audit scope

The audit reviewed the runner against the frozen Decision V2 Minimal preregistration and machine replay contract, including:

- exact source identity and row/session guards;
- score-only projected Parquet reads;
- no realized-return / target-column read path;
- deterministic consensus-rank reconstruction and naive Top-10 comparator guard;
- bootstrap only at ledger index 0;
- exact adjacent `(t-1,t)` session chaining;
- no pre-roll and no fold reset;
- Decision state advancement only through `DecisionV2ShadowState.from_plan(...)`;
- Decision rule-ID binding across sessions;
- replacement/churn accounting under temporary underfill;
- holding-spell accounting;
- rank-quality, state-behavior, capacity, block/fold and fold-boundary reporting;
- all preregistered hard-gate thresholds and gate directions;
- hidden stale-state detection;
- second identical in-memory pass for determinism only;
- fail-closed output staging / overwrite protection;
- SHA-manifested artifacts;
- CLI authorization interlock before historical-source loading;
- cross-platform canonical JSON replay-contract pinning.

## Findings

### 1. No rule drift found

The runner does not introduce a new Decision rule, threshold sweep, H5/H10 rescue logic, score smoothing, minimum holding period, turnover cap, or performance-aware logic.

The Decision V2 Minimal policy remains the frozen profile:

- target capacity 10;
- entry/current strong zone `<=10`;
- prior-session entry confirmation `<=20`;
- retention zone `<=20`;
- confirmed exit only after two consecutive available-session observations `>20`;
- immediate universe exit;
- soft replacement gap `>=5`;
- qualified challengers only;
- temporary underfill allowed when no qualified challenger exists.

### 2. Outcome-blind read boundary is acceptable

The executable source path uses Parquet metadata to validate row count and explicitly projects only:

- `ticker`
- `date`
- `fold`
- `mode`
- `alpha_h5`
- `alpha_h10`
- `alpha_consensus`

Extra Parquet columns, including return/target columns if present, are not loaded by the strict execution path.

### 3. Historical state semantics are preserved

The replay uses one empty bootstrap at the first of the exact 600 score sessions and then carries state continuously. Fold changes are reporting boundaries only; they do not reset the portfolio or previous-session score input.

### 4. Acceptance gates are frozen before result access

The implementation encodes the preregistered hard gates before the first replay. The final audit tests bind all numeric gate thresholds to the machine contract and verify the required comparison directions.

No post-result rescue rule or alternative parameter path exists in the authorized runner invocation.

### 5. Output handling is fail-closed

Existing final output directories and existing staging directories are rejected. A successful run writes a new immutable result directory with summary, structural ledgers and a SHA manifest.

### 6. CI

GitHub Actions run `32494630484` on the audited head completed successfully:

- `447 passed`
- `26 warnings`
- `0 failed`

Warnings are existing deprecation/future warnings and are not Decision V2 runner failures.

## Authorization boundary

Exactly one local historical structural replay is now authorized using the audited head and the existing runner authorization token:

`DECISION_V2_MINIMAL_STRUCTURAL_REPLAY_REVIEW_ACCEPTED_V1`

The replay must use the pinned source root containing:

- source manifest SHA-256 `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`;
- score Parquet SHA-256 `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`;
- exactly `600` score sessions;
- exactly `172,697` score rows.

The output directory must not already exist.

## Still forbidden

This authorization does not permit:

- realized return inspection;
- historical PnL inspection;
- protected/fresh-forward outcome access;
- provider/network calls;
- model refit/retune;
- Decision parameter sweep;
- alternate entry/exit/rank-gap thresholds;
- H5/H10 rescue variants;
- post-result parameter adjustment in the same evaluation.

If the structural result is `REJECT`, the rejection must be frozen as-is before any separately named next preregistration.

If the structural result is `ACCEPT`, the next step is to freeze Decision V2 Minimal and prepare the prospective outcome-blind Decision shadow. Historical PnL is not required for mechanical acceptance.
