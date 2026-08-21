# Decision V2 Minimal — Structural Replay Runner Implementation

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTED_TESTED_NOT_REPLAYED_INDEPENDENT_REVIEW_REQUIRED`

Branch: `research/idx-decision-v2-minimal-structural-replay-runner-v1`

Parent implementation: `research/idx-decision-v2-minimal-implementation-v1`

Validated code HEAD: `f211e604adf697b6a044f21fee7005f39f659848`

## Scope completed

Implemented the outcome-blind structural replay orchestration for the already-preregistered Decision V2 Minimal policy. No historical replay has been executed.

Components:

- machine-readable frozen replay contract at `docs/specs/decision_v2_minimal_structural_replay_contract_v1.json`;
- cross-platform canonical JSON contract identity SHA-256 `2f4e04fe060b43da6d555717a5aab687c10f40fa114ee954ae24082f912d455f`;
- strict source loader with exact source hashes, 600-session / 172,697-row identity, source guard checks, deterministic rank reconstruction, and frozen naive Top-10 comparator verification;
- parquet schema/row-count inspection through metadata before data load;
- projected score-only parquet read restricted to `ticker`, `date`, `fold`, `mode`, `alpha_h5`, `alpha_h10`, and `alpha_consensus`; extra target/return columns, if present, remain unread;
- exact adjacent `(t-1,t)` score-session iteration across the complete ledger;
- bootstrap only at ledger index 0, with no pre-roll and no fold reset;
- Decision shadow state advanced only through `DecisionV2ShadowState.from_plan(...)` and required to remain bound to the frozen rule ID;
- deterministic second in-memory pass solely for the preregistered determinism gate;
- structural ledgers for sessions, target membership, intents, Decision states, holding spells, and fold-boundary transitions;
- preregistered churn, holding, rank-quality, state-behavior, capacity, 100-date block, fold-segment, and fold-boundary metrics;
- explicit descriptive distribution of target ranks >20 and per-session stale-name counts, added downstream of the gate calculation without changing any gate value;
- hard-gate evaluator emitting only `DECISION_V2_MINIMAL_STRUCTURAL_ACCEPT` or `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`;
- fail-closed output directory creation and SHA-pinned output manifest;
- CLI execution lock requiring post-review authorization token before contract/source loading.

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

The CLI refuses execution unless the exact post-review token is supplied:

`DECISION_V2_MINIMAL_STRUCTURAL_REPLAY_REVIEW_ACCEPTED_V1`

The authorization check occurs before the replay contract and historical source are loaded. This token is an engineering process interlock, not a secret. This checkpoint does not authorize using it yet.

## Validation

GitHub Actions on code HEAD `f211e604adf697b6a044f21fee7005f39f659848`:

- `443 passed`;
- `26 warnings`;
- `0 failed`.

The warnings are pre-existing pandas/NumPy deprecation/future warnings unrelated to Decision V2.

Focused coverage includes:

- machine contract vs frozen runner constants;
- conservative replacement counting under underfill;
- continuous state across a fold boundary with no bootstrap/reset;
- exact 600-session requirement;
- all-hard-gates semantics where a single miss fails the relevant gate group;
- source column projection proving extra label/return columns remain unread;
- parquet metadata row-count guard;
- canonical contract hash invariance to LF/CRLF line endings;
- explicit rank>20 descriptive reporting without changing the gate verdict;
- CLI authorization failure before any historical source read.

## Known implementation boundary

`decision_v2_structural_replay.py` contains an earlier general loader helper that is not the authorized execution path. The guarded CLI imports and uses only `load_pinned_v4_x1_source_strict(...)` from `decision_v2_structural_source.py`. Independent review must verify this routing before replay authorization.

## Next action

1. independently audit PR #43 against the frozen preregistration and machine contract;
2. review source projection, contract/source identity, exact adjacency/state chaining, metric definitions, acceptance-gate mapping, output fail-closed behavior, and CLI lock ordering;
3. only after audit acceptance may the single exact 600-OOS structural evaluation be run locally.
