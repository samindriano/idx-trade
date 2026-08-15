# LBRE Lineage / Parser Remediation V1 — Preparation

Date: 2026-08-15
Branch: `data/idx-lbre-lineage-parser-remediation-v1`
Scientific parent: `data/idx-historical-statutory-free-float-snapshot-v1@4762f4751cb4cc30d348704c7e19e65c47b7a329`
Status: `PREPARED_NOT_YET_CLAIMED_FOR_RUNTIME`

## Purpose

Resolve only the bounded problem cases already observed in the accepted 2026-06-30 LBRE census before any multi-month acquisition is authorized.

Parent census facts:

- 1,068 LBRE announcements discovered;
- 1,064 unique main attachments;
- 1,064/1,064 official PDF retrieval success;
- 1,050 exact parsed rows;
- 18 parser-unresolved rows;
- 1,015 exact 2026-06-30 input rows;
- 915 originals / 100 corrections;
- 907 unique ticker-period keys before lineage;
- 871 current observations after conservative lineage replay;
- 93 exact rows excluded from lineage replay:
  - 35 `UNRESOLVED_NO_ORIGINAL`;
  - 29 `UNRESOLVED_MULTIPLE_ORIGINAL`;
  - 29 `UNRESOLVED_INVALID_CONTRACT_CHAIN`.

The remediation target is therefore the existing bounded problem inventory only. Do not discover or acquire another reporting month in this lane.

## Scientific objective

Separate each unresolved case into one of three outcomes:

1. `REMEDIATED_EXACT`
   - official bytes and metadata unambiguously support parsing and/or correction lineage;
   - observation satisfies the existing exact historical statutory-FF contract;
2. `GENUINE_SOURCE_AMBIGUITY`
   - source itself does not establish one defensible exact state/lineage;
   - remains excluded;
3. `UNSUPPORTED`
   - required evidence is absent, malformed, or cannot be tied to exact official bytes/metadata;
   - remains excluded.

Do not target a predetermined recovery rate. A zero-recovery result is valid if the evidence is genuinely ambiguous.

## Parent artifacts are immutable

Reuse only after exact manifest verification:

`D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`

Parent manifest SHA-256:

`7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`

Do not overwrite or mutate the parent artifact tree.

## Parser-remediation rules

For the 18 parser-unresolved PDFs:

- inventory the exact failure reason per file before changing code;
- group by visible template/layout family;
- inspect text extraction/table structure and exact reported FF section;
- parser changes must be template-specific and evidence-backed, not fuzzy value guessing;
- explicit FF shares and FF percentage must both be recoverable from the same official report context;
- ticker and position date must be explicit or tied through exact official metadata;
- zero/blank/missing values remain distinct;
- no arithmetic reconstruction from percentages, holder buckets, HSC, or `100% - holders`;
- existing successfully parsed rows must remain byte-for-byte semantically stable under regression tests.

## Lineage-remediation rules

For the 93 exact rows excluded from current-state replay:

### `UNRESOLVED_NO_ORIGINAL`

Investigate whether an earlier original for the same ticker + position date is already present in the bounded official announcement capture or exact attachment set but was misclassified/missed by metadata normalization.

A correction may be linked only if the original identity is explicit and unique. Do not create a synthetic original from the correction itself.

### `UNRESOLVED_MULTIPLE_ORIGINAL`

Determine whether apparent multiple originals are actually:

- exact duplicate announcements/attachments;
- replacement uploads with identical economic content;
- different attachment roles in one announcement;
- genuinely conflicting originals.

Collapse only provable transport duplicates with exact identity evidence. Distinct official publications remain distinct and ambiguous unless correction/supersession semantics explicitly resolve them.

### `UNRESOLVED_INVALID_CONTRACT_CHAIN`

Audit publication chronology and explicit correction labels/references. Repair only deterministic chains such as:

`ORIGINAL -> CORRECTION_1 -> CORRECTION_2`

when every edge is supported by exact official metadata/report evidence and publication time is strictly causal.

Never infer chain order solely from file naming, retrieval order, or numeric similarity.

## PIT requirements

- `as_of_date` is the reported ownership position date;
- `published_at` is official IDX publication knowledge time;
- retrieval time is not historical knowledge time;
- corrections become usable only from their own publication timestamp;
- never rewrite a prior historical state as if a later correction were known earlier.

## Outputs

The remediation runtime should produce an immutable new external root, for example:

`D:\Documents\Project\idx-lbre-lineage-parser-remediation-20260815-v1`

Required outputs:

- exact parent-manifest verification report;
- `problem_case_inventory.csv` covering every parent unresolved case;
- parser failure taxonomy;
- lineage failure taxonomy;
- per-case evidence + disposition;
- recovered exact observations, if any;
- post-remediation current-state table for 2026-06-30;
- before/after counts;
- deterministic manifest + SHA-256.

The original parent normalized files remain immutable.

## Admission gates

PASS requires all of the following:

- every parent problem case is accounted for exactly once;
- zero silent drops;
- zero invented originals/corrections;
- zero non-official evidence promoted to exact;
- zero publication-time regressions;
- zero changes to previously accepted exact observations except a separately documented genuine parser defect;
- recovered rows satisfy existing `HistoricalFreeFloatObservation` validation;
- correction replay remains fail-closed on unresolved ambiguity;
- focused tests and regression tests pass.

## Hard boundaries

Do not:

- acquire another LBRE month;
- expand to full 2024–2026 monthly history;
- reconstruct free float holder-by-holder;
- use HSC or >=1% ownership to repair LBRE;
- create daily carry-forward/interpolation;
- create Ownership Change Events;
- compute effective supply, turnover, free-float market cap, or Foreign Flow-normalized features;
- access outcomes/models or modify O2/Foreign Flow/Financial PIT/Corporate Action/TradingView lanes.

## Decision after remediation

Only after independent review may the next lane decide whether a full monthly LBRE history acquisition is justified.

Suggested verdicts:

- `LBRE_REMEDIATION_ACCEPTED_MONTHLY_HISTORY_READY`
- `LBRE_REMEDIATION_ACCEPTED_WITH_RESIDUAL_AMBIGUITY`
- `LBRE_REMEDIATION_BLOCKED_SOURCE_AMBIGUITY`
