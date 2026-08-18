# V4-3 CA Training-Domain Schedule-80 — Offline Adjudication Prep

Date: 2026-08-19
Branch: `data/v4-3-ca-training-domain-schedule-80-adjudication-v1`
Status: `READY_FOR_HASH_PINNED_OFFLINE_ADJUDICATION`

## Frozen acquisition parent

The one-shot official-KSEI acquisition is accepted only as raw evidence input:

- manifest SHA-256:
  `a7b10ded6246102d6d7858546fdb955ad426bf9a18f762239245a7253f801765`;
- 80 exact frozen schedule-required events;
- event identity SHA-256:
  `f89cd1e86b1de5f88792551a993311700e4ab15db19f8447e6e8dd61dec3594d`;
- 111 index queries, zero HTTP failures;
- 30 index-page parse failures retained as observed failures;
- 74/80 events with at least one candidate document;
- 89 unique candidate documents;
- zero provider-failed candidate documents;
- successful raw-response identity SHA-256:
  `2f83dfa2753fd9ea2eec2d20f5720f036ac71c628a2d495b88b2f4a0f7dd57a3`.

No provider rerun, source substitution, or new document discovery is authorized
for this adjudication.

## Adjudication semantics

Candidate event-document mapping is inherited exactly from the acquisition
artifact. No fuzzy event matching is permitted.

The hardened parser path is mandatory:

`parse_residual_document_hardened`

All dates that can admit evidence are rebound to explicit PDF-layout semantic
rows. This includes:

- payment/settlement/cash-purchase dates used to identify exact voluntary cash
  documents;
- Record/Distribution dates used only for event-document linkage;
- Regular-Market Ex / first-new-basis transition dates.

Record/Distribution dates remain prohibited as transition fallbacks.

Mechanical event admission requires all of:

1. exact frozen candidate event identity;
2. exact ticker evidence in the official document;
3. compatible event family;
4. exact frozen source-date linkage to a layout-bound Record/Distribution date;
5. an explicit layout-bound accepted Regular-Market transition semantic;
6. transition date is an official exchange session;
7. no conflicting transition evidence.

Voluntary cash/tender evidence may resolve NON_BLOCKING only with exact ticker,
recognized cash-document semantics, and source-date linkage to a layout-bound
payment/settlement/purchase date.

Conflicts and missing evidence fail closed.

## Runner

Use only:

`scripts/run_v4_3_ca_training_domain_schedule_80_offline_adjudication_v2.py`

V2 delegates the frozen V1 input/output contract but rebinds the parser to the
hardened layout-only admissive date implementation. Do not run the V1 entrypoint.

Required local inputs:

- KSEI schedule-80 acquisition root;
- the canonical research artifact root containing
  `official_exchange_sessions_1260.csv`, SHA-256
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- a fresh output directory.

Outputs:

- `schedule_80_event_document_evidence.csv`;
- `schedule_80_document_adjudication_audit.csv`;
- `summary.json`;
- `MANIFEST.json`.

The run reports exact-transition, exact-nonblocking, conflict, and unresolved
counts over all 80 events. It does not decide the 90% training-domain gate.

## Scientific firewall

This lane performs no network/provider call, price inference, target/rank
materialization, model fitting, prediction, performance evaluation, bootstrap,
or protected-forward access.

After adjudication, the exact adjudication manifest must be frozen before a
separate full training-domain continuity replay. Only that actual replay—not
this adjudication and not the earlier counterfactual ceiling—can determine
whether historical target/model execution becomes authorized.

## Coordination

Canonical `origin/main:coordination/TEAM_STATUS.md` was read immediately before
this material continuation. No overlapping active schedule-80 remediation lane
was found in the visible live-lane section. The canonical coordination file was
not rewritten because the available contents write operation requires replacing
the full large ledger; this checkpoint records branch-local ownership without
claiming a canonical TEAM_STATUS update.
