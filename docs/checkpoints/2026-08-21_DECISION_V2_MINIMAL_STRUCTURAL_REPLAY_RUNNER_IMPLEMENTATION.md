# Decision V2 Minimal — Structural Replay Runner Implementation

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTED_NOT_REPLAYED_REVIEW_REQUIRED`

Branch: `research/idx-decision-v2-minimal-structural-replay-runner-v1`

Parent implementation: `research/idx-decision-v2-minimal-implementation-v1`

## Scope completed

Implemented the outcome-blind structural replay orchestration for the already-preregistered Decision V2 Minimal policy. No historical replay has been executed.

Components:

- machine-readable frozen replay contract at `docs/specs/decision_v2_minimal_structural_replay_contract_v1.json`;
- pinned source loader with exact source hashes, 600-session / 172,697-row identity, source guard checks, deterministic rank reconstruction, and frozen naive Top-10 comparator verification;
- exact adjacent `(t-1,t)` score-session iteration across the complete ledger;
- bootstrap only at ledger index 0, with no pre-roll and no fold reset;
- Decision shadow state advanced only through `DecisionV2ShadowState.from_plan(...)` and required to remain bound to the frozen rule ID;
- deterministic second in-memory pass solely for the preregistered determinism gate;
- structural ledgers for sessions, target membership, intents, Decision states, holding spells, and fold-boundary transitions;
- preregistered churn, holding, rank-quality, state-behavior, capacity, 100-date block, fold-segment, and fold-boundary metrics;
- hard-gate evaluator emitting only `DECISION_V2_MINIMAL_STRUCTURAL_ACCEPT` or `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`;
- fail-closed atomic output directory creation and SHA-pinned output manifest;
- CLI execution lock requiring post-review authorization token before any local source is loaded.

## Frozen replacement metric interpretation

Because V2 may be temporarily underfilled, the runner freezes the structural replacement count as:

`max(sell_intent_count, buy_intent_count)` per non-bootstrap transition.

This is intentionally conservative. A paired sell+buy counts as one changed seat, while an exit-only or fill-only transition also counts as one rather than allowing underfill to artificially reduce measured churn.

The source itself must reproduce the already-observed naive exact daily Top-10 comparator of `3,127` replacements before Decision V2 replay is allowed.

## Scientific boundary

Still forbidden and not accessed:

- realized returns;
- historical portfolio PnL;
- historical target/outcome ledgers;
- protected or fresh-forward outcomes;
- provider/network calls;
- model refit/retune;
- Decision parameter sweep;
- alternative rank thresholds, confirmation lengths, or gap thresholds;
- post-result rescue variants.

The second in-memory Decision pass is not an alternative replay or policy variant; it uses the exact same already-loaded pinned score frame and exists only to satisfy the preregistered deterministic-rerun correctness gate.

## Execution lock

The CLI refuses to load the historical source unless the exact post-review token is supplied:

`DECISION_V2_MINIMAL_STRUCTURAL_REPLAY_REVIEW_ACCEPTED_V1`

That token is an engineering interlock only. This checkpoint does not authorize using it yet.

## Validation boundary

Tests cover:

- machine contract vs frozen runner constants;
- conservative replacement counting under underfill;
- continuous state across a fold boundary with no bootstrap/reset;
- exact 600-session requirement;
- all-hard-gates semantics where a single miss fails the relevant gate group.

The runner must receive independent/adversarial review and CI validation before the first exact 600-OOS execution.

## Next action

1. open draft PR against the audited Decision V2 implementation branch;
2. run full repository CI;
3. independently audit source guards, adjacency/state chaining, metrics, acceptance-gate mappings, output atomicity, and the execution lock;
4. only after review acceptance may the user run the single exact 600-OOS structural evaluation locally.
