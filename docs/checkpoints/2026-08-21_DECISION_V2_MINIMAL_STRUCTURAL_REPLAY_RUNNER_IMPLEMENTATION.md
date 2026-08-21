# Decision V2 Minimal — Structural Replay Runner Implementation

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTED_AUDITED_SINGLE_REPLAY_COMPLETED_STRUCTURAL_REJECT`

Branch: `research/idx-decision-v2-minimal-structural-replay-runner-v1`

Parent implementation: `research/idx-decision-v2-minimal-implementation-v1`

## Scope completed

Implemented and independently audited the outcome-blind structural replay orchestration for the already-preregistered Decision V2 Minimal policy.

The single authorized historical structural replay has now been executed exactly once against the pinned 600-session V4-X1 score path. The frozen result is `DECISION_V2_MINIMAL_STRUCTURAL_REJECT` and is recorded in:

`docs/checkpoints/2026-08-21_DECISION_V2_MINIMAL_STRUCTURAL_RESULT.md`

Result artifact root:

`D:\Documents\Project\idx-v4-x1-decision-v2-minimal-structural-replay-20260821-v1`

Result manifest SHA-256:

`a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`

The exact audited executable head used for the replay was:

`044e8e9a3190935848938ca19d5ea3c9f7c98c01`

Any later commits on this branch are documentation-only result recording and do not retroactively alter the executed runner identity.

## Implemented runner contract

Components:

- machine-readable frozen replay contract at `docs/specs/decision_v2_minimal_structural_replay_contract_v1.json`;
- pinned source loader with exact source hashes, 600-session / 172,697-row identity, source guard checks, deterministic rank reconstruction, and frozen naive Top-10 comparator verification;
- projected score-only Parquet reads, leaving any extra return/target columns unread;
- exact adjacent `(t-1,t)` score-session iteration across the complete ledger;
- bootstrap only at ledger index 0, with no pre-roll and no fold reset;
- Decision shadow state advanced only through `DecisionV2ShadowState.from_plan(...)` and required to remain bound to the frozen rule ID;
- deterministic second in-memory pass solely for the preregistered determinism gate;
- structural ledgers for sessions, target membership, intents, Decision states, holding spells, and fold-boundary transitions;
- preregistered churn, holding, rank-quality, state-behavior, capacity, 100-date block, fold-segment, and fold-boundary metrics;
- hard-gate evaluator emitting only `DECISION_V2_MINIMAL_STRUCTURAL_ACCEPT` or `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`;
- descriptive rank>20 distribution reporting downstream of the frozen gate evaluator;
- fail-closed atomic output directory creation and SHA-pinned output manifest;
- canonical JSON replay-contract hash, portable across Windows LF/CRLF differences;
- CLI execution lock requiring post-review authorization token before any local source is loaded.

## Frozen replacement metric interpretation

Because V2 may be temporarily underfilled, the runner freezes the structural replacement count as:

`max(sell_intent_count,buy_intent_count)` per non-bootstrap transition.

This is intentionally conservative. A paired sell+buy counts as one changed seat, while an exit-only or fill-only transition also counts as one rather than allowing underfill to artificially reduce measured churn.

The source reproduced the already-observed naive exact daily Top-10 comparator of `3,127` replacements before Decision V2 evaluation.

## Scientific boundary preserved

The completed replay did not access or use:

- realized returns;
- historical portfolio PnL;
- historical target/outcome ledgers;
- protected or fresh-forward outcomes;
- provider/network calls;
- model refit/retune;
- Decision parameter sweep;
- alternative rank thresholds, confirmation lengths, or gap thresholds;
- post-result rescue variants.

The second in-memory Decision pass was not an alternative policy replay; it used the exact same pinned score frame only to satisfy the deterministic-rerun correctness gate.

## Validation

Independent audit accepted the exact implementation head before execution.

Full repository CI on the audited runner/test head:

- `447 passed`;
- `26 warnings`;
- `0 failed`.

The replay itself passed all source/correctness/determinism guards and emitted the frozen structural reject without any rescue rerun.

## Next action

Do not rerun Decision V2 Minimal and do not alter its thresholds.

Next authorized work is the outcome-blind Decision V2 failure-mechanism diagnosis specified in the result checkpoint. No successor Decision rule should be implemented before that diagnosis is frozen.
