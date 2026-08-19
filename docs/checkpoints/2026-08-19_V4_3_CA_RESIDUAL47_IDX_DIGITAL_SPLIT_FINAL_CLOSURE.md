# V4-3 CA Residual-47 IDX Digital Split — Final Closure

Date: 2026-08-19

Status: `CLOSED_NO_INCREMENTAL_ADMISSIBLE_EVIDENCE`

## Scope

Final bounded, outcome-blind corporate-action remediation attempt for the residual 47 `SCHEDULE_REQUIRED` events after combined KSEI + IDX announcement evidence replay.

This lane used only the official IDX Digital Statistic `LINK_STOCK_SPLIT` surface. It did not access targets, ranks, predictions, model performance, or protected forward outcomes.

## Frozen acquisition result

Artifact root:

`D:\Documents\Project\idx-v4-3-ca-residual47-idx-digital-split-20260819-v1`

Manifest SHA-256:

`84271e7b72d36c77d958472b7bcf9214ec7f433b9bff96d27d92d97b07077538`

Result:

- residual events: 47
- query months: 69
- pages requested: 69
- failed queries: 0
- inventory rows: 63
- candidate links: 39
- events with candidate rows: 35
- events without candidate rows: 12
- semantic admission during acquisition: false
- historical target loaded: false
- model fit: false
- performance computed: false

## Calendar path hotfix

The first offline adjudication invocation failed before evidence evaluation because the config referenced `official_idx_session_calendar.csv`, while the previously frozen calendar artifact is named `official_exchange_sessions_1260.csv`.

The filename-only hotfix preserved the exact frozen calendar SHA-256:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

No threshold, parser, linkage rule, evidence, or semantic admission rule changed.

## Frozen offline adjudication result

Artifact root:

`D:\Documents\Project\idx-v4-3-ca-residual47-idx-digital-split-adjudication-20260819-v1`

Manifest SHA-256:

`fd8a9f23b0d965d357e71cefab7c5ac8bbcadf04f1e1b8814b51f318791aa3ea`

Result:

- residual events: 47
- exact transition events: 0
- resolved events: 0
- unresolved events: 47
- conflict events: 0
- historical target loaded: false
- model fit: false
- performance computed: false

## Decision

The explicit stop rule is triggered.

Because this final structured official-source attempt produced zero newly admissible events, no further corporate-action provider search, issuer-site crawl, transport retry, parser relaxation, threshold relaxation, or pass-impact-directed acquisition is authorized for this V4-3 generation.

A replay is intentionally not run because zero event semantics changed; it would be a deterministic no-op relative to the frozen combined KSEI + IDX replay.

The controlling combined replay therefore remains:

- manifest SHA-256: `12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43`
- combined resolved from original 80: 33
- remaining schedule events: 47
- frozen H5 minimum support rate: `0.8432203389830508`
- frozen H10 minimum support rate: `0.8395061728395061`
- frozen consensus minimum support rate: `0.8395061728395061`
- all frozen 600 full-target eligible: false
- tail-600 identity unchanged: false
- all fold/head training sets nonempty: false
- only folds 5 and 6 have any admitted training dates

Verdict:

`V4_3_BLOCKED_BY_PREREGISTERED_CA_GATE_STOP_RULE_TRIGGERED`

## Next scientific action

Do not run the frozen V4-3 historical model under the original generation because the preregistered CA gate is not satisfied.

If model research is to resume, create a separately preregistered next generation before historical target/performance access, with an explicitly redesigned CA uncertainty/admission policy. The original V4-3 generation remains frozen as a blocked data-gate result.
