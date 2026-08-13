# Corporate Action PIT Deterministic Linkage V1 — Frozen Design

Date: 2026-08-14 (Asia/Jakarta)
Branch: `data/corporate-action-pit-deterministic-linkage-v1`
Status: `FROZEN_DESIGN_PRE_BOUNDED_VALIDATION`
Parent source audit: `data/corporate-action-pit-source-audit-v1@2de089f0e48ae2ee74ffd16c4361155a04dccc30`
Independent source-audit acceptance: `review/idx-corporate-action-pit-source-audit-acceptance-v1@32e4ef8f33f8e58892ae7c395daf388d4ff47619`

## Purpose

Replace the old date-equality diagnostic with event-specific, fail-closed identity rules. This phase asks whether official KSEI schedule documents, KSEI registered-security history, and official IDX announcement/attachment evidence can be linked deterministically enough to create a future PIT event ledger.

This is still a data-admission/linkage experiment. It does not authorize market-wide acquisition, canonical event materialization, OHLC adjustment, shares-outstanding reconstruction, alpha features, model fitting, protected outcomes, or forward-counter changes.

## Source authority and roles

### 1. KSEI schedule document — primary economic-event identity/version evidence

Use the linked official KSEI document's internal fields as the strongest KSEI evidence:

- internal KSEI reference number;
- issuer/ticker;
- security/rights code and ISIN where present;
- event subject/family;
- economic ratio;
- record/distribution/listing/exercise dates where present;
- exercise price or other event-specific economics where present;
- explicit reference to a prior KSEI announcement/document for revisions or additional information.

The schedule-index row is a locator/provenance record, not identity authority when it conflicts with the linked document. A displayed reference mismatch must be preserved as `CONFLICT`; never silently rewrite the document from index metadata.

### 2. KSEI registered-security corporate-action history — operational supplement

Use as official evidence for observed C-BEST/security-level operation, ratio text, Cum Date, Record Date, Distribution Date and current visible Status.

The visible `Type of CA` is not always the economic event family. An explicit KSEI schedule-document subject overrides the security-page/C-BEST operation label when classifying the economic event.

Example principle: an economically defined bonus-share distribution can be implemented in C-BEST under a different operational action type. Do not classify economic family from the operation label alone when an authoritative schedule document exists.

Current visible status is not historical knowledge time. `Cancelled` today must not be back-propagated to dates before dated cancellation/revision evidence.

### 3. IDX issuer announcement/attachment — preferred precise publication-time evidence

If a deterministic event-specific linkage to an official IDX announcement/attachment can be established, preserve exact `TglPengumuman` with Asia/Jakarta semantics and derive UTC timestamp as in the accepted Financial PIT transport.

Ticker + broad date window + title token is discovery only. It may produce candidates but can never by itself produce `EXACT` PIT linkage.

### 4. IDX `GetIssuedHistory` — candidate activity/share-state corroboration

Retain source-native `TanggalPencatatan`, `JenisTindakan`, `JumlahSaham`, `JumlahSahamSetelahTindakan`.

Do not require universal equality between `TanggalPencatatan` and KSEI Cum/Record/Distribution dates. Do not call `TanggalPencatatan` a generic effective date. For some event families this source may remain optional corroboration rather than identity authority.

## Economic event-family classification

Schedule-document subject has precedence over source operation label.

Required normalized families for V1:

- `RIGHTS_ISSUE`
- `STOCK_SPLIT`
- `REVERSE_SPLIT`
- `BONUS_SHARES`
- `STOCK_DIVIDEND`
- `CASH_DIVIDEND`
- `MIXED_DIVIDEND`
- `NON_PREEMPTIVE_ISSUANCE`
- `PARTIAL_DELISTING`
- `CAPITAL_REDUCTION`
- `IPO`
- `MANDATORY_CONVERSION_UNCLASSIFIED`
- `OTHER`

`Mandatory Conversion` alone is not enough to infer split direction/type. A schedule document explicitly identifying Stock Split or Reverse Stock Split is required before promotion from `MANDATORY_CONVERSION_UNCLASSIFIED`.

## Deterministic linkage rules

### Rights / HMETD

Strong identity anchors:

1. exact ticker; and
2. exact rights security code and/or rights ISIN from official evidence.

When a rights code/ISIN is available and agrees, schedule-date differences in an explicit revision may represent version changes rather than a different event. Preserve the differences.

Fallback only if code/ISIN is unavailable:

- exact ticker;
- exact economic ratio including security identities;
- plus exact Record Date or exact listing/exercise-start anchor supported by both official sources.

Date/title proximity alone is insufficient.

### Stock split / reverse split

Require:

- exact ticker;
- schedule-document classification of split direction when source label is generic;
- exact economic ratio;
- at least one exact operational anchor among Record Date, Distribution Date or listing/effective listing date where both sources expose that same semantic field;
- no contradictory non-null anchor in fields declared comparable for the candidate pair.

### Bonus shares / stock dividend / mixed dividend

Require:

- exact ticker;
- document-classified economic family;
- exact economic ratio;
- exact Record Date;
- exact Distribution Date;
- no contradictory comparable field.

Do not reject a bonus-share event merely because the KSEI security/C-BEST operation label is `Mixed Dividend` or `Right Distribution` if the authoritative schedule document explicitly says bonus shares.

### Cash dividend

Require:

- exact ticker;
- exact cash ratio/amount+currency representation;
- exact Record Date;
- exact Distribution Date;
- no contradictory comparable field.

### Non-preemptive issuance / partial delisting / capital reduction

V1 may accept only when the pair has:

- exact ticker;
- exact event family;
- exact listing/share-state date with the same source semantics; and
- exact authoritative `total_shares_after_action` or equivalent official post-action share count.

If the meaning of a share-count field remains unproven, keep the event unresolved rather than applying legacy arithmetic.

### IPO

IPO is not admitted into deterministic cross-source materialization in this V1 unless an explicit, separately documented identity rule exists. Keep unresolved rather than weakening gates simply to increase coverage.

## Revision / correction / cancellation lineage

All versions are append-only. Never overwrite an older observed event.

Revision relation requires:

1. exact ticker;
2. same normalized economic event family; and
3. explicit revision/change language such as `KOREKSI`, `Perubahan`, `Informasi Tambahan`, `Penjadwalan Ulang`, `Revision`, `Additional Information`, or `Rescheduling`.

Strongest revision rule:

- later official KSEI document explicitly cites the prior KSEI reference; and
- cited prior reference exactly equals the earlier document's internal KSEI reference.

This explicit prior-reference rule can establish version lineage even when schedule dates/economic details changed. A mismatched explicit prior reference is a conflict.

Without a prior-reference citation, the later document must still satisfy the normal event-specific deterministic identity anchors.

A current KSEI security-page `Cancelled` status is not itself sufficient to know when cancellation became public. A dated cancellation/change document or exact timestamped official announcement is required before creating historical cancellation knowledge state.

## Schedule-index metadata conflict rule

If schedule-index reference/ticker conflicts with the linked official document's internal reference/ticker:

- preserve both raw values;
- status = `CONFLICT` for locator validation;
- document internal identity remains evidence authority;
- do not silently repair the index row;
- do not discard the raw locator because it remains provenance for how the document was discovered.

## Availability / PIT precision

Evidence precision must remain explicit:

### `IDX_TIMESTAMP_CONFIRMED`

Only for deterministic exact linkage to an official IDX announcement with valid timestamp. Preserve exact UTC timestamp.

### `KSEI_DOCUMENT_DATE_ONLY`

If only official KSEI schedule document date is known, preserve date-only evidence:

- `knowledge_at_utc = null`
- `knowledge_date = YYYY-MM-DD`
- precision = `DATE_ONLY`

Never fabricate 00:00/09:00/close timestamp from a KSEI document date.

Mapping date-only evidence to an actionable market session is explicitly deferred to a later feature/PIT contract. No model use is authorized by this spec. A future conservative policy may choose next official IDX session, but that rule is NOT frozen here.

### Unknown

No publication timestamp/date evidence => fail closed.

## Linkage statuses

- `EXACT`: exactly one candidate satisfies the event-family-specific rule.
- `AMBIGUOUS`: more than one candidate satisfies the exact rule.
- `UNRESOLVED`: no candidate has sufficient deterministic anchors.
- `CONFLICT`: a candidate has contradictory explicit identity evidence.

No confidence score or fuzzy threshold is permitted in V1.

## Bounded validation set

The first validation must remain deliberately small and include:

1. **SINI HMETD 2026** — prove rights code/ISIN + ratio + official schedule fields.
2. **MEGA bonus shares 2026** — prove schedule document overrides C-BEST operation label; prove base + `Informasi Tambahan` lineage via explicit prior KSEI reference.
3. **MLPT stock split 2026** — prove generic `Mandatory Conversion` security label is classified by official schedule document.
4. **RAJA stock split 2026** — second independent split case.
5. **one cancellation/revision case** — historical cancellation must require dated evidence, not current status alone.
6. **one deliberate unresolved case** — prove fail-closed behavior.
7. **one schedule-index/document metadata-conflict case** — preserve mismatch and use document internal identity.

Do not select or drop cases based on eventual model performance; no model/outcome access exists in this lane.

## Pre-runtime implementation remediation

The branch currently contains an initial linkage core added before the full official-document semantic review. Before any validation result is accepted, implementation/tests must enforce:

1. schedule-document economic-family precedence over security/C-BEST operation label;
2. explicit `prior_ksei_reference` revision lineage;
3. locator/document reference mismatch as a surfaced conflict;
4. no title/date-proximity exact linkage;
5. no fabricated KSEI intraday timestamp.

Focused tests must include MEGA bonus classification and explicit prior-reference lineage.

## Validation outputs

Persist outside Git in a new immutable runtime root:

- exact source-audit parent artifact hashes used;
- newly downloaded bounded KSEI schedule PDFs/HTML if required;
- parser output for document-internal references/ticker/ISIN/ratio/dates;
- event candidate rows;
- deterministic linkage decisions and reason codes;
- version/revision lineage rows;
- unresolved/conflict rows;
- request manifest + SHA-256;
- bounded coverage by event family.

Repo outputs:

- implementation + focused tests;
- result checkpoint;
- handoff;
- TEAM_STATUS → REVIEW after safe latest-main refetch.

## Stop boundary

Stop after bounded deterministic validation for independent ChatGPT review.

No market-wide backfill, canonical event table, shares-outstanding reconstruction, OHLC adjustment, features, models, protected outcomes, Financial PIT edits, Foreign Flow edits, AKSes login, O2 changes, or forward-counter changes.
