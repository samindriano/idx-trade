# Historical E2E Final Blocker Closeout V1

Date: 2026-08-24  
Branch: `research/idx-historical-e2e-replay-v1`  
Parent: `935e2264c4c4027b7391b9149bf48c00453fb590`

## Verdict

`TRUE_HISTORICAL_E2E_REPLAY_BLOCKED`

This closeout is outcome-blind. No labels, returns, fills, NAV, P&L,
performance metrics, Monte Carlo, protected forward outcomes, model fitting,
or provider calls were performed in this pass.

The mission cannot safely proceed to a real historical paper replay because
the longest exact strict scope is zero. The result is not a failure of the
replay engine; it is a fail-closed refusal to invent missing economic state.

## Scope result

Fresh recompute:

- root: `D:\Documents\Project\idx-historical-e2e-scope-recompute-20260824-v9`
- `REPLAY_SCOPE.json` SHA-256:
  `cb765a5f1675ea35c2a4d075302c64fd6ac09d413ba8edb4a8198079ed203ae0`
- scope payload SHA-256:
  `f75cf7302f4bd27927e36e296634c7ae9adfcd32849ed8fc78555a9e27dc6fd7`
- candidate sessions: 600
- strict sessions: 0
- status: `STRICT_SCOPE_EMPTY_BLOCKED`
- blockers: `NO_CONTIGUOUS_EXPOSURE_COMPLETE_RANGE`,
  `DIVIDEND_EXPOSURE_WINDOW_PROOF_INCOMPLETE`

The scope was not selected or shortened using any outcome or performance
information.

## Corporate-action evidence

The accepted event-window ledger remains the final-v3 artifact:

- root: `D:\Documents\Project\idx-v4-ca-event-window-final-20260818-v3`
- manifest SHA-256:
  `c635ee354c923eebdb586bc4d82a6693d230e1a347df50879dda4c1f5f56bff4`
- ledger SHA-256:
  `0c48aa4d12a66241378e1b95e2f51615b5ca3469a4c63692c5d9e7b8818a337f`
- exposure rows: 5,693
- exact resolved rows: 4,471
- unresolved effective-date rows: 41,993 across H5/H10 ledger rows
- unresolved coverage rows: 29,084 across H5/H10 ledger rows
- sessions with every exposure row exact-resolved: 0

An offline sensitivity using the earlier material-six ledger was also checked
without changing the accepted ledger:

- root: `D:\Documents\Project\idx-v4-ca-material-six-remediation-20260818-v4`
- per-date rates: H5 minimum `0.910256...`, H10 minimum `0.907051...`
- exact all-exposure sessions: 0
- exact contiguous all-exposure run: 0

The material-six >=90% per-date sensitivity is not sufficient for a true
historical accounting replay: unresolved exposure rows could change share
transforms, holdings, cash, or subsequent sizing.

## Dividend evidence

The complete metadata corpus was reused as an immutable source audit, but it
does not establish a market-wide no-event ledger:

- raw manifest:
  `D:\Documents\Project\idx-historical-e2e-dividend-corpus-batch-20260824-v1\DISCOVERY_MANIFEST.json`
  SHA-256 `9c89e0e089827a46c51a18ee3d2ddba36861fc02660f677942315d9d367e25bf`
- normalized manifest:
  `D:\Documents\Project\idx-historical-e2e-dividend-corpus-normalized-20260824-v1\NORMALIZED_MANIFEST.json`
  SHA-256 `a94a04b7d8c2dcefafbd8397e03e36059efbdeaab609068644d53371d1b6b167`
- 347/347 ticker response files are present in the raw corpus;
- 53,637 official announcement rows are present;
- 921 candidates: 844 cash, 60 ambiguous, 17 unsupported/non-cash;
- 2,023 candidate attachment references exist;
- 0 historical PDFs are preserved in this corpus;
- 11 bounded certified positive overlaps remain valid for BBCA/BBRI;
- 4,384 exposure rows require attachment-level dividend semantics;
- 1,298 exposure rows remain `NO_EVENT_PROOF_NOT_AUTHORIZED`;
- the closure artifact SHA-256 is
  `c4d6a73d876cf92695944c2b8d941db4dbcff822558afd2c0e383f8d2664af4c`.

Absence of a dividend keyword in metadata is not promoted to no-event proof
without the accepted complete-source/no-event contract. The bounded positive
event dispositions are not a substitute for the missing market-wide state.

## Decision-input readiness

The current structural decision bundle is outcome-blind and hash-pinned, but
it is explicitly a structural reject and is not a complete historical sizing
/ execution bundle:

- root: `D:\Documents\Project\idx-v4-x1-decision-v2-minimal-structural-replay-20260821-v1`
- status: `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`
- score source SHA-256:
  `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`
- 600 session trajectory rows and 5,693 exposure rows exist;
- no pinned 600-session sizing/execution ledger or generator artifact is
  accepted by the readiness contract.

This is a separate readiness blocker. It must be resolved from an accepted,
outcome-blind decision/sizing lineage before the replay can claim exact
production-path accounting, even if the CA and dividend gates are later fixed.

## Open and deterministic checks

The Open/panel path is not the limiting blocker in this closeout:

- 600/600 historical official-Open session manifests are certified;
- BUY identity rows: 1,297, with 905 positive and 392 certified non-positive;
- SELL identity rows: 1,287, with 895 positive and 392 certified non-positive;
- certified non-positive Open remains pending under frozen execution semantics;
- no FirstTrade substitution or synthetic Open is admitted.

Validation on the research branch:

- focused scope/replay tests: `32 passed`;
- full pytest: `745 passed, 0 failed` with 3 existing pandas FutureWarnings;
- `git diff --check`: PASS.

## Stop condition

No replay, performance, NAV, or Monte Carlo was started because there is no
non-empty exact strict scope. The smallest scientifically valid next action is
external evidence work that can produce both:

1. an all-exposure exact CA continuity ledger for a contiguous range of at
   least 20 sessions; and
2. attachment-backed dividend event/no-event evidence for every holding spell
   in that same range;

followed by an accepted 600-session decision/sizing input bundle. Until those
conditions are met, any historical E2E NAV or Monte Carlo would mix unknown
portfolio state into the result and is rejected.
