# V4-3 CA Schedule-80 — Real Adjudication Training-Domain Replay Prep

Date: 2026-08-19
Branch: `research/idx-ranking-v4-3-ca-schedule80-replay-v1`
Status: `READY_FOR_OUTCOME_BLIND_REAL_EVIDENCE_REPLAY`

## Accepted immutable inputs

### Parent full training-domain replay

Manifest SHA-256:

`c115ea0bec59cab4da0cda45ee66ba2be5814e0bb9e854e3f7ecd616edc83861`

Status:

`V4_3_CA_TRAINING_DOMAIN_KSEI_129_OFFLINE_REPLAY_BLOCKED_REVIEW_REQUIRED`

Relevant frozen state:

- 740 CA coverage-census identities;
- 695 coverage-certified tickers total;
- 45 coverage-unresolved decision tickers;
- 0 missing historical decision tickers;
- 0 cross-source conflicts;
- no target/model/performance/protected-forward access.

### Schedule-80 adjudication

Manifest SHA-256:

`13f4e84d8586c22e100382071f0b4cd4cdbb87e3099b7f0526f844a495ab1fd0`

Status:

`V4_3_CA_SCHEDULE_80_OFFLINE_ADJUDICATION_COMPLETE`

Observed result over the exact 80-event frozen schedule inventory:

- exact transitions: 1;
- exact non-blocking voluntary cash/tender events: 20;
- resolved total: 21;
- conflicts: 0;
- unresolved: 59;
- verified successful raw official-KSEI documents: 89;
- missing raw candidate links: 0.

Event inventory SHA-256:

`f89cd1e86b1de5f88792551a993311700e4ab15db19f8447e6e8dd61dec3594d`

This result was produced by the hardened layout-bound adjudication path. No
new provider call or parser relaxation is authorized by this replay.

## Replay contract

The replay does not rebuild or recrawl providers. It consumes the parent replay
support/event artifacts and changes only exact `event_id + ticker` identities
present in the frozen adjudication result.

Rules:

1. parent `SCHEDULE_REQUIRED` + adjudication `UNRESOLVED` -> unchanged,
   fail-closed;
2. parent `SCHEDULE_REQUIRED` + `EXACT_NON_BLOCKING` -> `NON_BLOCKING` only
   when the parent source type is `Voluntary Conversion` and exact official
   KSEI provenance remains present;
3. parent `SCHEDULE_REQUIRED` + `EXACT` -> `EXACT_TRANSITION` only with an
   accepted Regular-Market transition semantic, transition date, KSEI
   reference, and source SHA;
4. any adjudication `CONFLICT` fails the runner;
5. the one newly exact transition remains subject to normal event-window
   crossing exclusion. It is not converted into globally resolved continuity;
6. all 59 unresolved schedule events remain unresolved;
7. the 45 coverage-unresolved tickers remain unchanged;
8. the 90% gate and frozen fold identities remain unchanged.

## Inputs reused from the parent replay

The runner verifies the parent manifest and child hashes before loading:

- `v4_3_ca_training_domain_ksei129_continuity.csv`;
- `v4_3_full_target_support_rows_ksei129.csv`;
- `v4_3_full_target_support_per_date_ksei129.csv`;
- `v4_3_training_date_sets_ksei129.csv`;
- `v4_3_ca_training_event_semantics_ksei129.csv`;
- `summary.json`.

Only binary price-observability support columns are reused from the combined
row ledger. The replay explicitly parses CSV booleans so string `False` cannot
be interpreted as truthy.

Frozen validation folds remain repository-pinned at SHA-256:

`91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915`.

## PASS definition

PASS requires all of the following under the unchanged 0.90 gate:

- all frozen 600 dates H5/H10/consensus eligible;
- eligible consensus tail remains the exact frozen 600 identity;
- zero newly eligible sessions after the frozen validation end;
- all 6 folds x 2 heads have non-empty preregistered training-date sets.

PASS verdict:

`V4_3_CA_SCHEDULE_80_REPLAY_PASS_READY_FOR_HISTORICAL_EXECUTION_PIN`

A PASS still must be hash-pinned/documented before any historical target/model
execution is allowed.

BLOCK verdict:

`V4_3_CA_SCHEDULE_80_REPLAY_BLOCKED_REVIEW_REQUIRED`

A BLOCK does not authorize threshold lowering, ticker/event exclusions, source
substitution, price/date inference, provider retry based on gate contribution,
or historical target/model access.

## Outputs

- `v4_3_ca_training_domain_schedule80_continuity.csv`;
- `v4_3_full_target_support_rows_schedule80.csv`;
- `v4_3_full_target_support_per_date_schedule80.csv`;
- `v4_3_training_date_sets_schedule80.csv`;
- `v4_3_ca_training_event_semantics_schedule80.csv`;
- `schedule_80_adjudication_replay_overlay.csv`;
- `summary.json`;
- `MANIFEST.json`.

## Scientific firewall

The runner performs no network/provider call, no document discovery, no price
inference, no target or rank materialization, no model fit/prediction, no
performance/bootstrap evaluation, and no protected/fresh-forward outcome
access.

## Coordination note

Canonical `origin/main:coordination/TEAM_STATUS.md` was read before this
material continuation and the visible live-lane section showed no overlapping
active schedule-80 replay lane. The canonical ledger has not been rewritten by
this ChatGPT session because the connector write path requires replacing the
full large shared file; this checkpoint records branch-local ownership without
claiming a canonical TEAM_STATUS update.
