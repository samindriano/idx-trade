# V4-3 CA Training-Domain Schedule-80 — Offline Reuse Prep

Date: 2026-08-19
Branch: `data/v4-3-ca-training-domain-schedule-80-v1`
Status: `OUTCOME_BLIND_OFFLINE_REUSE_CENSUS_READY`

## Parent result

The accepted local residual-attribution result is pinned at manifest SHA-256:

`7b5663bba944c039ed881d1fd71e7e3b80765c46013792fde5790fb6fa45ec4d`

with parent replay manifest:

`c115ea0bec59cab4da0cda45ee66ba2be5814e0bb9e854e3f7ecd616edc83861`.

Its verdict is:

`V4_3_CA_RESIDUAL_ATTRIBUTION_SCHEDULE_ONLY_SUFFICIENT`.

Frozen-600 counterfactual diagnostics under the unchanged 90% gate:

- baseline: 0/600 consensus, minimum 0.7942386831;
- coverage-only ceiling: 0/600 consensus, minimum 0.8065843621;
- schedule-only ceiling: 600/600 consensus, minimum 0.9300411523;
- coverage+schedule ceiling: 600/600 consensus, minimum 0.9423868313;
- price-observability-only upper bound: 600/600 consensus, minimum 0.9423868313.

There are 45 coverage-unresolved decision tickers and exactly 80
`SCHEDULE_REQUIRED` events. Exact mechanical crossing rows remain blocked and
were never waived. The result therefore authorizes evidence work on all 80
schedule events; it does not authorize a pass-preserving event subset or a
coverage-45 retry.

## Why reuse comes before provider acquisition

Official KSEI bytes/documents were already acquired in prior CA lanes. Before
making any new provider call, this lane performs an exact-identity reuse census
against already-promoted immutable evidence.

Two evidence parents are pinned by SHA:

1. `docs/artifacts/v4_ca_schedule_evidence_20260818_v3/`
   - manifest `5073adb3178a90e71ea9105ddb6ff737896e86a709d1998eefbdb14ca12b6f8c`
   - schedule evidence `c9f396951ae82f2526c6e7943bff2ed359aa488697d3086f1afdb64127e8d3b4`
2. `docs/artifacts/v4_ca_residual_document_semantics_20260818_v1/`
   - manifest `6f2070dbd89307c39579aa9617807c2c8ae746390466476f29504b31ae4988a5`
   - event evidence `6be49b4fc8a930c9bc61fde64a0652a7cb6233459f5a2e140cb4b4ad0f56592e`

The prior broad KSEI schedule acquisition used 77 index pages / 100 candidate
documents and yielded one exact schedule link. The residual-document audit
subsequently reused the same attested raw corpus and produced 22 exact
non-blocking events plus one exact transition among its residual event set.
Those results are evidence candidates for reuse only when the current event
identity matches exactly.

## Exact reuse contract

A current event can be reused only with exact `event_id + ticker` identity.
No source-date proximity, fuzzy ticker/family matching, price behavior, record
date, distribution date, or threshold contribution is used to choose a match.

Admissible existing claims are:

- `EXACT` -> exact transition, requiring nonempty transition date, transition
  semantic, KSEI reference, and source SHA;
- `EXACT_NON_BLOCKING` -> exact non-blocking classification from the accepted
  residual-document semantics lane.

Conflicting transition dates, conflicting claim kinds, incomplete evidence, or
multiple incompatible semantics fail closed.

## New runner

`python scripts/run_v4_3_ca_training_domain_schedule_80_reuse_census.py`

Inputs:

- local residual attribution root;
- immutable promoted evidence above;
- frozen config
  `config/v4_3_ca_training_domain_schedule_80_reuse_v1.json`.

Outputs only:

- `schedule_80_existing_evidence_reuse_census.csv`;
- `schedule_80_admitted_existing_claims.csv`;
- `schedule_80_residual_events_for_acquisition.csv`;
- `summary.json`;
- `MANIFEST.json`.

The runner derives and hashes the exact full 80-event inventory before reuse.
If residual events remain, their complete identity is frozen for the next
acquisition step. No event is selected because of its effect on the 90% gate.

## Hard boundaries

This prep/run has:

- zero network/provider calls;
- no source substitution;
- no fuzzy event matching;
- no record/distribution-date transition inference;
- no price inference;
- no pass-preserving subset selection;
- no R5/R10, target rank, model fit, prediction, performance, bootstrap, or
  protected/fresh-forward outcome access;
- no change to the V4-3 target/model/evaluation contract.

After the census, if residual events remain, the next step is a separately
frozen official-KSEI acquisition over **all residual events**, not a minimum
subset needed to pass. Only an actual full training-domain replay after real
evidence admission can authorize historical target/model execution.

## Coordination note

Canonical `origin/main:coordination/TEAM_STATUS.md` was inspected before this
lane was created and no overlapping ACTIVE V4-3 schedule-remediation lane was
found. The shared canonical row has not been edited by ChatGPT because the
connector exposes only full-file replacement for that large coordination
ledger; this checkpoint records the branch-local ownership boundary without
claiming a canonical TEAM_STATUS update.
