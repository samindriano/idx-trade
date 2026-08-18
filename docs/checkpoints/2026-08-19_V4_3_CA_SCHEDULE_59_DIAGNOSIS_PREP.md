# V4-3 CA Training-Domain — Residual Schedule-59 Diagnosis Prep

Date: 2026-08-19
Branch: `research/idx-ranking-v4-3-ca-schedule59-diagnosis-v1`
Status: `READY_FOR_OUTCOME_BLIND_RESIDUAL_59_FAILURE_MODE_CENSUS`

## Controlling blocked replay

The accepted local schedule-80 adjudication replay is pinned at:

- manifest SHA-256: `aaaa39d5cb1da709c1c9f2214ea3c7955df29b4148899dff865ea3cc8e970810`;
- status: `V4_3_CA_SCHEDULE_80_REPLAY_BLOCKED_REVIEW_REQUIRED`;
- adjudication resolved: 21/80;
- adjudication unresolved: 59/80;
- replayed schedule-required events: 59;
- coverage-unresolved decision tickers: 45;
- historical target/model/performance/protected outcome access: false.

Actual frozen-600 support after the 21-event adjudication overlay is:

- H5 minimum: `0.8347457627118644`;
- H10 minimum: `0.831275720164609`;
- consensus minimum: `0.831275720164609`;
- H5/H10/consensus eligible sessions: 0/0/0;
- all fold-head training sets nonempty: false;
- frozen tail identity unchanged: false.

This is an improvement over the pre-adjudication baseline but remains a real
block. No historical target/model execution is authorized.

## Adjudication parent

The immutable schedule-80 adjudication is pinned at:

- manifest SHA-256: `13f4e84d8586c22e100382071f0b4cd4cdbb87e3099b7f0526f844a495ab1fd0`;
- 20 exact non-blocking events;
- 1 exact transition event;
- 59 unresolved events;
- 0 conflicts;
- 89 verified successful raw KSEI documents;
- 0 missing raw candidate links.

The hardened layout-bound date semantics remain controlling. They are not
relaxed in this lane.

## Purpose of this lane

Do **not** make another KSEI/provider acquisition yet. The first acquisition
already produced 89 raw documents and 74/80 events with candidate documents.
A repeated acquisition with the same scope would not explain why 59 events
remain unresolved.

This lane therefore performs a deterministic offline failure-mode census over
**all 59 residual events**. It mirrors the frozen adjudication contract and
classifies the first fail-closed stage for each event:

1. no frozen candidate document;
2. candidate does not evidence exact ticker;
3. voluntary conversion has no recognized official cash document;
4. voluntary cash document has no layout-bound cash date;
5. voluntary cash date does not link to frozen source date;
6. mechanical document family is incompatible;
7. frozen source date does not link to a layout-bound Record/Distribution date;
8. linked mechanical document lacks an explicit Regular-Market Ex/new-basis transition;
9. explicit transition is not an official exchange session;
10. otherwise unresolved under the frozen contract and retained for manual official-evidence review.

Record/Distribution dates remain linkage-only and can never become transition
fallbacks.

## Outputs

Runner:

`scripts/run_v4_3_ca_training_domain_schedule_59_diagnosis.py`

Expected outputs:

- `residual_59_failure_mode_census.csv`;
- `residual_59_failure_mode_counts.csv`;
- `residual_59_source_type_failure_counts.csv`;
- `residual_59_diagnostic_token_counts.csv`;
- `summary.json`;
- `MANIFEST.json`.

The full exact residual-59 `event_id + ticker` identity is hashed and retained.
No event may be removed because of its contribution to the 90% gate.

## Scientific firewall

This diagnosis has:

- no network/provider calls;
- no new document discovery;
- no source substitution;
- no parser/semantic relaxation;
- no fuzzy matching;
- no price inference;
- no Record/Distribution transition inference;
- no threshold change;
- no pass-preserving subset selection;
- no target/rank materialization;
- no historical target loading;
- no model fit, prediction, performance, bootstrap, or protected-forward access.

The next acquisition/remediation contract, if needed, must keep all 59 events in
scope and may vary only the official evidence-discovery path according to the
frozen diagnosis class. It may not target a minimum subset needed to pass.

## Coordination

Canonical `origin/main:coordination/TEAM_STATUS.md` was read before this
material continuation. No visible overlapping active schedule-59 diagnosis lane
was found. The canonical coordination ledger was not rewritten because the
available contents operation requires replacing the full large shared file; no
claim is made that TEAM_STATUS itself was updated.
