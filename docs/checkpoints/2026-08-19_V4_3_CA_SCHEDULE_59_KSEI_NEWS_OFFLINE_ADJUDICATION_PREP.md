# V4-3 CA Schedule-59 — KSEI News Offline Adjudication Prep

Date: 2026-08-19
Status: `READY_FOR_HASH_PINNED_OFFLINE_ADJUDICATION`

## Frozen secondary acquisition parent

The one-shot KSEI public-site secondary acquisition is accepted only as an
immutable raw-evidence input:

- acquisition manifest SHA-256:
  `96c11caa6ed728cbd19af8f13cc30bedde45c04e7a256e6d0c9a591dd62fc7d1`;
- residual event count: 59;
- residual event identity SHA-256:
  `f1c587eca59a9e7ec68cb8b1b2fc0980489a8f8a1b608f10403f2cc9f6d85707`;
- 227 frozen internal-KSEI search queries;
- 159 failed search queries retained as observed failures;
- 6 pagination-truncated queries retained as observed truncations;
- zero search parse failures;
- 1,114 unique KSEI News results/articles requested;
- 56/59 events with KSEI News candidates and exact ticker evidence;
- 3/59 events without KSEI News candidates;
- 4 provider-failed news articles;
- one discovered attachment and one provider-failed attachment;
- successful raw-response identity SHA-256:
  `45132e0b5ae17b74ee005c55d26ddb464bdd5bb692b4a3a62d6649189f7ff7a8`.

No provider retry, search-query change, pagination expansion, source substitution,
or external search engine is authorized inside this adjudication lane.

## Adjudication policy

This stage does not weaken the accepted residual-document semantics.

For a mechanical event, an exact transition requires all of:

1. exact frozen `event_id + ticker` candidate linkage inherited from the
   acquisition artifact;
2. exact ticker evidence in the captured official KSEI News page;
3. compatible event family;
4. frozen source-date linkage to a layout-bound Record/Distribution date;
5. explicit Regular-Market Ex or first-new-basis transition semantics;
6. transition date is an official exchange session;
7. no conflicting exact transition evidence.

Record/Distribution dates are linkage fields only and never transition
fallbacks.

For Voluntary Conversion, exact NON_BLOCKING evidence remains restricted to
recognized cash/tender/buyback semantics with frozen source-date linkage to a
layout-bound payment, settlement, or purchase date.

Conflicts fail closed.

## HTML layout hardening

The acquisition parser stored flattened body text only as diagnostics.  The
adjudication reopens the already-frozen raw HTML locally and constructs a
conservative layout from explicit headings, paragraphs, list items, and table
rows.  Dates are admissible only from those physical semantic blocks.  A
free-floating date in another generic `div` is not permitted to satisfy a
date-less transition row.

The existing pre-frozen hardened parser remains the semantic authority:

`parse_residual_document_hardened`

and exact event resolution remains delegated to:

`resolve_event_document_evidence`.

## Inputs

Required local roots:

- the immutable KSEI News acquisition root;
- the canonical research artifact root containing
  `official_exchange_sessions_1260.csv`, SHA-256
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- a fresh output directory.

## Runner and outputs

Runner:

`scripts/run_v4_3_ca_training_domain_schedule_59_ksei_news_offline_adjudication.py`

Outputs:

- `schedule_59_ksei_news_event_evidence.csv`;
- `schedule_59_ksei_news_adjudication_audit.csv`;
- `summary.json`;
- `MANIFEST.json`.

The run reports exact-transition, exact-nonblocking, conflict, and unresolved
counts across all 59 events.  It does not itself decide the V4-3 90% continuity
gate.

## Scientific firewall

This stage performs no provider/network call, source substitution, new document
discovery, external search, fuzzy event matching, price inference, target/rank
materialization, model fit, prediction, performance evaluation, bootstrap, or
protected-forward access.

After this adjudication the exact output manifest must be pinned before a
separate combined evidence replay.  The previous 21 schedule-80 resolutions
remain immutable evidence and will be combined with any newly admitted
schedule-59 evidence only in that later replay.

## Coordination

Canonical `origin/main:coordination/TEAM_STATUS.md` was read before this material
continuation.  No overlapping active schedule-59 KSEI News adjudication lane was
found in the visible live-lane section.  Canonical TEAM_STATUS was not rewritten
because the available contents write action requires replacing the full large
ledger; this checkpoint records branch-local ownership without claiming a
canonical coordination update.
