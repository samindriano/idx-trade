# Ranking V2 Forward Specification — Independent Review PASS

Date: 2026-08-10 (Asia/Jakarta)
Status: **`RANKING_V2_FORWARD_SPEC_REVIEW_PASS`**
Reviewed by: ChatGPT architect

## Decision

The champion/final-refit/fresh-forward specification is accepted after one pre-outcome semantic clarification.

Frozen champion remains:

`HGB_XS_MARKET`

Corrected controlling specification:

`docs/RANKING_V2_CHAMPION_FORWARD_SPEC_V1.md`

Corrected spec blob SHA-256 / Git blob identity:

`77b2d74c9d5f28460037c11cd3a134c6b6cc9d3d`

Clarification commit:

`333acfcd3c7585dd68c4912468d80d8b8e3fbe54`

No fresh-forward outcome was inspected before or during this review.

## Review clarification

The submitted draft described forward Q5-Q1 as a mean-return spread, while the frozen historical Ranking-V2 evaluator defines Q5-Q1 as the within-date TP-rate spread:

`Q5 TP rate - Q1 TP rate`

The forward specification has therefore been clarified before any outcome access to preserve metric semantics. It now also explicitly defines top-decile lift as top-decile TP rate minus block prevalence and states that no realized-return Q5-Q1 metric is part of the first independent verdict.

This clarification changes no champion, model parameter, feature, training row, universe, label, historical outcome, candidate result, or observed forward outcome.

## Final-refit authorization

Implementation and execution of the frozen final-development refit are now authorized.

The final fit must use exactly:

- champion: `HGB_XS_MARKET`;
- prepared-cache SHA `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- 292,633 eligible rows;
- 737 tickers;
- signal-session index `20..1250`;
- exact frozen 25-feature order;
- exact frozen HGB preprocessing/model settings;
- one fit only, no tuning, search, candidate comparison, calibration, or outcome-dependent filtering.

The final model and manifest must be serialized and SHA-256 pinned.

## Forward-runtime implementation authorization

Engineering implementation of the fresh-forward runtime is authorized now, including:

- immutable source-snapshot and provenance validation;
- causal feature/universe construction;
- H10 maturity checks;
- pre-outcome manifest construction;
- global one-shot access marker logic;
- fixed 100-session and 50/50 stability evaluation logic;
- exact historical metric semantics;
- deterministic artifact hashing;
- profiling and engineering-only optimization under `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
- reference-versus-optimized equivalence tests that do not inspect fresh-forward outcomes.

Historical fixtures/synthetic/adversarial data may be used to validate code semantics, but historical candidate selection must not be rerun or reopened.

## Fresh-outcome access remains blocked

This review does **not** authorize writing `FORWARD_OUTCOME_ACCESS_STARTED` or reading the one-shot fresh-forward outcome block yet.

Outcome access requires all of the following first:

1. final model artifact and manifest frozen;
2. forward runtime implementation complete and tested;
3. optimized path, if used, proven semantically equivalent before outcome access;
4. immutable post-2026-07-31 source evidence snapshot complete and hash-pinned;
5. the first fixed block of 100 consecutive forward signal sessions exists and its 100th session is fully H10-mature;
6. pre-outcome manifest validates the intended block and all provenance;
7. a separate MAIN/ChatGPT authorization to consume the one-shot block.

Because the project date is only 2026-08-10, the required 100-session forward block cannot yet be mature. The actual independent verdict is therefore necessarily a later event, not something the current runtime implementation can legitimately produce now.

## Still prohibited

- inspect or summarize fresh-forward labels/outcomes now;
- write the global outcome-access marker now;
- reopen/tune V2 candidates or champion selection;
- probability calibration claims;
- Stage 6;
- `IDX-VAL-002`;
- execution-PnL claims;
- Kelly sizing;
- paper/live trading;
- merge to `main`.

## Next action

Implement and freeze the final-refit artifact plus outcome-blind fresh-forward runtime. Profile and optimize only under semantic-equivalence gates. Stop before global forward-outcome access and return to MAIN/ChatGPT with code/test/model/provenance hashes and evidence-window readiness status.
