# IDX Trade — Forward 100-Session Evaluator Synthetic Implementation

Date: 2026-08-13 (Asia/Jakarta)
Branch: `codex/idx-forward-100-evaluator-v1`
Decision: `FORWARD_100_SESSION_EVALUATOR_IMPLEMENTED_SYNTHETIC_ONLY_REVIEW_REQUIRED`

## Scope completed

Implemented the outcome evaluator required by the frozen Forward 100-Session
Evaluation Protocol V1 without reading or discovering the protected forward
outcome vault.

Controlling protocol:

- original protocol commit: `6c05499d01ba644c80f0c6bd6d621aac92ab2813`;
- protocol SHA-256: `526b69e46a8ffbebcc0e7ebd044e54333672cd24ee1c36cf5dca8752f100a8a3`;
- branch-local protocol import commit: `578017e00cf3dbf2da3b0277ab16527f08501cca`.

Implementation:

- `src/idx_trade/forward_100_evaluator.py`;
- `tests/test_forward_100_evaluator.py`.

## Frozen semantics implemented

### O2 primary

- exact 100-session identity and consecutive official-session-index contract;
- immutable first-50 / last-50 split;
- exact accepted row-level `o2_eligible=true` support with finite scores;
- unresolved H10 outcomes preserved with explicit reasons;
- prevalence, PR-AUC, PR-AUC minus prevalence, ROC-AUC, within-session Q1/Q5,
  Q5-minus-Q1, top-decile rate and lift;
- frozen `O2_FORWARD_PASS`, `O2_FORWARD_MIXED`, and `O2_FORWARD_FAIL`
  decision boundaries;
- top-decile evidence remains diagnostic-only.

### Reliability V1

- exact O2-scored and resolved-row support;
- exact local-pairwise-quality positive/negative/tie semantics;
- deterministic ticker-tiebroken Reliability quartiles, top-40 selection, O2
  score quintiles, and within-quintile Reliability halves;
- per-session minimum 30 rows and both classes;
- exact 80/100 and 40/50-per-half readiness boundaries;
- full/early/late aggregation semantics;
- frozen PASS / INCONCLUSIVE / FAIL / INCONCLUSIVE_DATA decisions.

### Anti-rescue and provenance

- Reliability cannot alter or rescue the controlling O2 verdict;
- O2.1 is explicitly absent from evaluation;
- input artifacts, O2 manifests, Reliability manifests, model and feature pins,
  sidecar-to-O2 source pins, and shared source revisions fail closed;
- required shared provenance roles cover model, model manifest, feature order,
  calendar, security master, tradability, corporate actions, and source snapshot;
- deterministic stable sorting and sorted-key JSON output;
- final output manifest SHA-pins every material artifact.

## One-shot ordering hardening

The only executable orchestration entry point is intentionally named
`run_synthetic_forward_evaluation()`.

It:

1. refuses any inventory row declared protected;
2. confines every source artifact to an explicit synthetic fixture root;
3. verifies the frozen protocol hash and all input hashes/semantic pins;
4. writes `pre_outcome_contract.json` before any loader is callable;
5. atomically writes `SYNTHETIC_FORWARD_OUTCOME_ACCESS_STARTED`;
6. calls the injected synthetic loader only after the marker exists;
7. leaves the synthetic block consumed after a crash;
8. refuses an existing synthetic marker before writing a new output;
9. refuses a location containing the real `FORWARD_OUTCOME_ACCESS_STARTED`
   marker;
10. never writes the real marker.

This deliberately avoids wiring a protected loader or discovering the real
forward runtime before a later `READY_TO_OPEN_VAULT` review.

## Test coverage

Focused:

- `python -m pytest tests/test_forward_100_evaluator.py -q`
- result: `11 passed, 0 failed`.

Full repository:

- `python -m pytest -q`
- result: `289 passed, 0 failed, 3 warnings, 24.95s`;
- all three warnings are existing pandas `FutureWarning` reports outside this
  evaluator lane.

Adversarial coverage includes:

- exact 100/50/50 boundaries and non-consecutive indices;
- O2 PASS/MIXED/FAIL equality boundaries and non-finite failure;
- local-pairwise tie half-credit;
- deterministic bucket behavior under input reordering and tied scores;
- Reliability 80/100 and 40/50 boundaries plus all four verdict states;
- no Reliability rescue and no O2.1 inclusion;
- malformed, incomplete, unresolved-without-reason, and unprovenanced outcomes;
- source hash, protected flag, partial sidecar, model pin, and shared-revision
  failures;
- pre-manifest → synthetic marker → loader ordering;
- existing-marker refusal and crash-after-marker consumed behavior;
- protocol hash mismatch before loader access.

## Protected-boundary confirmation

- Protected forward outcome files inspected: `0`.
- Actual forward evaluator runs: `0`.
- Actual O2/V3-B/Reliability artifacts loaded: `0`.
- Real `FORWARD_OUTCOME_ACCESS_STARTED` marker writes: `0`.
- Provider calls: `0`.
- Model refits/rescores: `0`.
- Counter, frozen protocol, model, or feature changes: `0`.

## Unresolved risks before eventual vault opening

These are deliberate final-integration tasks, not gaps to solve before the
counter is mature:

1. a separately reviewed protected-runtime adapter must locate the exact
   canonical counter/runtime root without changing the evaluator core;
2. the final pre-vault audit must prove `100/100`, consecutive sessions, H10
   maturity, and all real session/source revisions against the then-current
   immutable archive;
3. the protected outcome loader and real global marker root must be wired only
   after explicit `READY_TO_OPEN_VAULT` authorization;
4. crash handling must preserve the consumed real marker and forbid any rerun;
5. no threshold, metric, model, row support, half boundary, or Reliability
   formula may change during that adapter work.

No actual or synthetic result in this checkpoint is a scientific forward
verdict.
