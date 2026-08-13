# Corporate Action PIT Deterministic Linkage V1 — Bounded Result

Date: 2026-08-14 (Asia/Jakarta)  
Branch: `data/corporate-action-pit-deterministic-linkage-v1`  
Base: `ec7261b3ddae9c2fb2cfd98fb9ea59b01ce57586`  
Status: `REVIEW`

## Scope and safety boundary

This result covers semantic remediation and one bounded deterministic
validation set only. It does not create a market-wide corporate-action table,
adjust OHLC, reconstruct shares outstanding, derive features, access protected
outcomes, or touch Foreign Flow, Financial PIT, AKSes, O2, or forward runtime.

The accepted parent source-audit manifest was reverified without mutation:

`D:\Documents\Project\idx-corporate-action-pit-source-audit-20260814-v1-final2\MANIFEST.json`

- expected SHA-256: `d44b9362909f5c05d8412ff07ca4c5616a74b43930bd1caf92242ed25b5e10cf`
- observed SHA-256: `d44b9362909f5c05d8412ff07ca4c5616a74b43930bd1caf92242ed25b5e10cf`
- parent verification: `PASS`

New immutable bounded artifacts are external to Git:

`D:\Documents\Project\idx-corporate-action-pit-linkage-20260814-v1-final`

- final manifest SHA-256: `1db444f6ceb815bdc29f1f80c8158c7a2050ebf7a5fe0ec0c4230e65940bb195`
- 32 manifest-listed raw/derived files
- raw KSEI PDFs, extracted text, rendered visual checks, parser rows,
  decisions, revision lineage, unresolved cases, and source hashes retained

## Implementation remediation

The linkage core now enforces:

1. A schedule-document subject overrides the operational/C-BEST label through
   every event-family path, including `link_event` and revision checks.
2. `Tanpa HMETD` / non-preemptive language is checked before generic HMETD
   language.
3. Explicit revision language is token-boundary checked, combines subject and
   title, and cannot be triggered by a substring such as `Exchange`.
4. An exact `prior_ksei_reference` establishes append-only lineage even when
   schedule dates change; a mismatched reference is a conflict.
5. Rights code/ISIN presence mismatches cannot fall back to ratio/date
   matching; exercise-start date is an allowed exact fallback anchor only when
   rights identifiers are unavailable.
6. Conflicting explicit candidates block promotion of another exact candidate.
7. Schedule-index/document conflicts retain both raw identities in the
   decision evidence and are conflict-dominant over incomplete secondary
   fields.
8. IDX timestamps require `EXACT` linkage and are labeled
   `IDX_TIMESTAMP_CONFIRMED`; KSEI document dates remain `DATE_ONLY` with no
   fabricated intraday time.

`src/idx_trade/corporate_action_pit_documents.py` adds a conservative parser
for text extracted from immutable official KSEI schedule PDFs. It only emits
explicit identity, family, ratio, date, rights, revision-reference, source
hash, and evidence-location fields; missing evidence remains `UNRESOLVED`.

## Bounded validation

Five official KSEI PDFs were fetched once in the bounded run and parsed:

| Case | Reference | Ticker | Document date | Family | Key evidence |
|---|---|---|---|---|---|
| SINI | KSEI-17438/JKU/0726 | SINI | 2026-07-03 | RIGHTS_ISSUE | rights code/ISIN, 2:3, record/listing/exercise dates, price |
| MEGA base | KSEI-7347/JKU/0426 | MEGA | 2026-04-07 | BONUS_SHARES | 1:1 bonus ratio, record/distribution schedule |
| MEGA follow-up | KSEI-7806/JKU/0426 | MEGA | 2026-04-14 | BONUS_SHARES | explicit subject ticker and prior KSEI reference |
| MLPT | KSEI-18691/JKU/0726 | MLPT | 2026-07-15 | STOCK_SPLIT | subject, ISIN, 1:25, recording date |
| RAJA | KSEI-18423/JKU/0726 | RAJA | 2026-07-13 | STOCK_SPLIT | subject, ISIN, 1:5, recording date |

Counts:

- parsed document rows: `5/5`
- exact schedule-locator → document identity decisions: `5/5`
- family counts: `RIGHTS_ISSUE=1`, `BONUS_SHARES=2`, `STOCK_SPLIT=2`
- MEGA operational labels (`Right Distribution` / `Mixed Dividend`) were
  overridden by the authoritative bonus-share subjects
- MLPT and RAJA generic `Mandatory Conversion` labels were classified as
  `STOCK_SPLIT` from the official schedule subjects
- KSEI PIT precision: `DATE_ONLY=5`, `IDX_TIMESTAMP_CONFIRMED=0` for KSEI
  document publication; no KSEI intraday timestamp was fabricated

The MEGA revision decision is:

`EXACT(EXPLICIT_REVISION, PRIOR_KSEI_REFERENCE_EXACT)`

The later document cites `KSEI-7347/JKU/0426` exactly. Both document versions
remain independently retrievable in the external artifact root and retain
independent byte hashes and document dates. The later document is not used to
overwrite the base row.

## IDX timestamp and fail-closed cases

The parent official IDX capture includes MLPT:

- revision announcement: `049/MLPT/PDC/VII/2026`
- prior announcement: `048/MLPT/PDC/VII/2026`
- published timestamp: `2026-07-15T08:15:43Z`
- correction attachment SHA-256:
  `007e00ac72ea0400dfb35b2bd407b743e37c27f854b74c9328145ca2f9d2fea1`

This is retained as `IDX_TIMESTAMP_CONFIRMED` event-specific revision
evidence: exact ticker, `STOCK_SPLIT`, ratio `1:25`, and explicit `KOREKSI`
with prior IDX announcement `048`. The attachment does not cite the KSEI
reference, so its timestamp is **not** relabeled as the KSEI document's
publication time. This keeps the cross-source linkage fail-closed.

The required cancellation/revision audit case remains conservative:

- TRST's current KSEI `Cancelled` status is not historical knowledge time;
- no dated cancellation/change document was captured in this bounded run;
- historical cancellation state remains `UNRESOLVED`.

The metadata-conflict case is a deliberate adversarial fixture using the
captured MLPT document identity with a changed locator reference. It returns
`CONFLICT`, preserves locator and document references, and is explicitly not
reported as a live source defect. A separate deliberate proximity-only case
returns `UNRESOLVED`.

## Tests and decision

Focused linkage/parser tests: `20 passed`.  
Full pytest: `64 passed, 1 failed, 0 warnings` out of 65 collected. The sole
failure is the pre-existing unrelated `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` expectation: the current
storage contract reports both `raw_close` and `vendor_adj_close` revision
conflicts while that test still expects one. This linkage lane did not modify
`storage.py` and did not weaken or hide that audit.

Decision: `CONDITIONAL_SOURCE_USEFUL_PIT_LINKAGE_DATE_ONLY`

The semantic core and bounded KSEI document identity are usable for further
bounded discovery. Canonical PIT materialization is not authorized: most
available KSEI evidence is date-only, and deterministic KSEI↔IDX publication
timestamp linkage remains incomplete except for the separate MLPT IDX revision
evidence row described above.
