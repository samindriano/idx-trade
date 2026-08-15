# LBRE Monthly Free-Float History V1 — Preparation

Date: 2026-08-15
Branch: `data/idx-lbre-monthly-free-float-history-v1`
Scientific parent: `data/idx-lbre-lineage-parser-remediation-v1@a42715f027fceb0c7cd24f68e65c9e91b7bfa049`
Status: `PREPARED_CANONICAL_CLAIM_REQUIRED_BEFORE_RUNTIME`

## Objective

Build a provenance-complete, point-in-time-safe history of **official issuer LBRE reported statutory free-float observations** for position months from 2024-04-30 through 2026-06-30 inclusive.

This is a historical source/acquisition lane. It does not create a daily free-float series, effective supply, ownership-event overlay, Foreign Flow feature, or model input.

## Accepted parent evidence

Historical snapshot parent:

- branch `data/idx-historical-statutory-free-float-snapshot-v1`
- final HEAD `4762f4751cb4cc30d348704c7e19e65c47b7a329`
- external root `D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`
- manifest SHA-256 `7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`

LBRE remediation parent:

- branch `data/idx-lbre-lineage-parser-remediation-v1`
- final HEAD `a42715f027fceb0c7cd24f68e65c9e91b7bfa049`
- external root `D:\Documents\Project\idx-lbre-lineage-parser-remediation-20260815-v1-final6`
- manifest SHA-256 `cb2e929a8e7d5fc481c0eed6add4a6ba848c5a3374c65ea38e5fbe3fa5727244`

The June-2026 census/remediation established:

- 1,068 discovered LBRE announcements;
- 1,064 unique main attachments, 1,064/1,064 retrieved;
- parser exact `1,050 -> 1,051` after remediation;
- parser unresolved `18 -> 17`;
- lineage admitted `957 -> 963`;
- lineage excluded `93 -> 87`;
- current exact observations `871 -> 877`;
- zero previously admitted semantic changes;
- zero PIT violations;
- residual ambiguity remains explicit.

## Frozen historical window

Target **position dates** are month-end observations from:

- first: `2024-04-30`
- last: `2026-06-30`
- target months: 27

The acquisition/publication search window may extend beyond those dates because an LBRE for month M is normally published after the position date and corrections can arrive later. Publication-time cutoff is 2026-08-15 Asia/Jakarta.

Do not extend to 2021-2023 or position July 2026 in this V1 merely because isolated files are discoverable.

## Core semantics

An exact accepted observation must preserve:

- ticker;
- `as_of_date` / position date;
- timezone-aware official IDX `published_at`;
- explicit reported `free_float_shares`;
- explicit reported `free_float_pct`;
- `total_listed_shares` when explicitly available;
- source family `ISSUER_LBRE`;
- revision kind;
- correction supersession lineage where proven;
- official announcement identity;
- official source URL;
- attachment SHA-256;
- metadata SHA-256.

`published_at`, not report position date or retrieval date, governs historical knowledge availability.

## No synthetic completeness grid

Do **not** manufacture a ticker × month panel and label missing cells `NO_OBSERVATION` unless an independently certified historical issuer universe is admitted in a separate lane.

This V1 may report only evidence-backed counts such as:

- announcements discovered per position month;
- unique ticker-position keys observed;
- exact current observations per position month;
- parser unresolved rows;
- lineage unresolved rows;
- correction counts;
- transport failures;
- ambiguous identities.

Absence from the discovered corpus is not automatically evidence that an issuer did not file.

## Generalization requirement from remediation

The remediation runner contains bounded ticker-specific forensic handling. Those ticker names are **not production rules**.

Monthly V1 may generalize only evidence-backed semantics:

1. byte-identical duplicate transport references may be collapsed deterministically while preserving alias provenance;
2. same-announcement re-uploads with different bytes may collapse only when announcement identity, ticker/position identity, and parsed economic content are exactly equivalent; preserve both attachment hashes as aliases in the audit layer;
3. explicit `KOREKSI` / `CORRECTION` markers may override a bad default revision classification;
4. a correction may link only to a unique, already-published compatible prior state or to an explicitly referenced superseded record;
5. multiple genuine originals without deterministic supersession remain unresolved;
6. no synthetic original may be invented;
7. current FF shares and FF percentage must be explicit official values; no arithmetic derivation may rescue a missing field.

Any generalized rule requires focused positive and adversarial tests.

## Source discovery and acquisition

Use only the accepted official IDX announcement metadata + official StaticData attachment transport.

Discovery must be pagination-complete for each bounded query used. Preserve raw metadata bytes and hashes.

Do not infer position date from publication month alone. Determine the report position date from authoritative report content/metadata and admit only target dates.

Reuse June-2026 parent official bytes by exact hash/path identity. Do not redownload them simply to make a new copy. Reuse any other already-pinned official bytes where exact identity can be verified.

For new official attachments:

- store outside Git;
- hash before parsing;
- preserve official URL, announcement identity and retrieval metadata;
- never overwrite an existing hash-pinned artifact;
- retry transport failures only under a bounded deterministic retry policy and report final failure counts.

## Parsing

Parser priority:

1. existing exact parent parser paths that already passed;
2. generalized evidence-backed remediation parser rules;
3. new template-specific exact rules only when an official document visibly exposes every required field.

Do not use fuzzy/narrative extraction to fabricate a current value.

The official reported percentage remains authoritative. Any shares/total arithmetic is diagnostic only.

## Revision / correction replay

Preserve every admitted original and correction as an append-only observation.

For each ticker + position date:

- replay only in official publication order;
- corrections must be later than the state they supersede;
- stale/ambiguous correction lineage fails closed;
- duplicate transport aliases do not create economic revisions;
- multiple independent originals remain ambiguous unless official evidence resolves them.

The output should distinguish:

- all admitted revision observations;
- current exact observation after PIT-safe replay;
- unresolved parser/lineage cases.

## Cross-source audit

Where position `2025-12-31` overlaps the already-pinned official market-wide exact report, reconcile issuer LBRE against the market-wide observation using the existing `AGREE / CONFLICT / SINGLE_SOURCE` semantics.

Do not choose a preferred value inside a conflict.

This cross-source check is diagnostic and does not replace LBRE lineage.

## External artifact root

Suggested:

`D:\Documents\Project\idx-lbre-monthly-free-float-history-20260815-v1`

Required durable outputs:

- raw official metadata query captures;
- acquisition inventory;
- attachment/hash inventory;
- parser audit;
- revision/lineage audit;
- unresolved-case inventory;
- all admitted observations CSV/JSON;
- current exact observations CSV/JSON;
- per-position-month coverage/census summary;
- 2025-12-31 cross-source reconciliation;
- final deterministic manifest and SHA-256.

No raw bulk attachments in Git.

## Scientific gates

This lane has no incentive to maximize row count at the expense of evidence quality.

Required integrity gates:

- zero synthetic values;
- zero holder/HSC/>=1% arithmetic;
- zero retrieval-time-as-publication-time substitutions;
- zero duplicate economic observations created by transport duplicates;
- zero ambiguous corrections silently selected;
- zero silently dropped failures;
- zero forward-fill/interpolation;
- all output rows traceable to exact official metadata + attachment hashes;
- all residual ambiguity explicitly counted by reason and month.

Coverage gaps are allowed and must remain visible.

## Hard boundaries

Do not:

- build a daily statutory FF state;
- forward-fill a monthly FF value across trading days;
- reconstruct FF from holders, HSC, >=1% ownership, Company Profile, or investor type;
- create Ownership Change Event logic;
- calculate effective/mobile supply;
- calculate float turnover, FF market cap, or Foreign Flow-normalized features;
- access labels/protected outcomes;
- fit or score models;
- touch O2, Foreign Flow, Financial PIT, Corporate Action, TradingView, AKSes, or unrelated lanes.

## Validation

At completion run focused historical/LBRE tests, full pytest, and `git diff --check`.

Known unrelated storage expectation failure may remain, but storage must not be modified by this lane.

## Candidate final verdicts

- `LBRE_MONTHLY_FF_HISTORY_READY_WITH_GAPS`
- `LBRE_MONTHLY_FF_HISTORY_PARTIAL_SOURCE_USEFUL`
- `LBRE_MONTHLY_FF_HISTORY_SOURCE_REMEDIATION_REQUIRED`

No feature/model work is automatically authorized by any of these verdicts.
