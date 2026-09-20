# IDX-Trade official authority crosswalk result — 2026-09-20

## Verdict

`RAW_STRUCTURAL_CROSSWALK_NO_ADMISSION`

The isolated lane reconciled the acquired official IDX report/XBRL, ratio,
trading-history, issued-history, and current-profile surfaces against the
current research corpus. It expanded raw coverage and made residuals explicit;
it did not close historical PIT, population, identity, revision, corporate-
action, capacity, or eligibility authority.

## What was established

- The annual report index contains 5,870 rows across 1,009 observed codes for
  2019–2025. Two rows (`2024:ASDF`, `2024:BINA`) have no instance attachment;
  5,864 instance archives were retained, leaving four expected 2025 keys
  (`CASH`, `OBMD`, `RIGS`, `SWAT`) not downloaded. These are explicit residuals,
  not silent substitutions.
- `File_Modified` is present on all 5,870 annual index rows, but its lag from
  the annual period end has a median of 91.468 days, reaches 2,287.839 days,
  and exceeds 180/365/730 days on 320/54/15 rows. This is descriptive source
  timing only; it does not establish publication, available-at, knowledge-time,
  or revision semantics.
- The quarterly index contains 9,971 rows across Q1/H1/9M periods for
  2022–2025. Quarterly XBRL was not downloaded or materialized.
- All 5,864 retained annual XBRL archives parsed structurally without error.
  Assets, liabilities, equity, net income, and operating cash flow were found
  in all archives; cash was found in 5,463 and revenue in 5,064. The projection
  preserves contexts and periods, but it does not certify taxonomy, units,
  consolidation, restatement, revision, issuer identity, or knowledge time.
- The raw projection contains both IDR and USD units for every selected field.
  Net income, operating cash flow, and equity each have multiple mapped
  concepts and duplicate code/year/period groups (11,728; 10,254; and 11,727
  groups respectively; revenue has two). This is direct semantic-collision
  evidence: structural parsing does not select the authoritative concept, unit,
  consolidation, restatement, or issuer identity.
- The 60 ratio snapshots contain 51,662 rows for 976 codes. Named sector,
  subsector, industry, and subindustry fields are present on every retained
  row and remain unchanged for each code across adjacent response snapshots.
  This is snapshot-stability evidence only: the query month is not a proven
  available-at date, `fsDate` is a financial period, and the coded
  `industryCode` field is empty in the retained surface.
- Official trading history contains 1,365,333 rows for 983 codes from
  2020-01-02 through 2026-09-18. Issued-history contains 1,563 event rows for
  1,043 code responses. Current profiles contain 1,016 populated and 27 empty
  responses; no stock ISIN field was observed in the bounded profile audit.

## Exact corpus crosswalk

The current panel has 981,940 keys for 945 tickers from 2021-04-29 through
2026-07-31. The current V2 financial bundle remains 277,244 rows for 729
tickers, with 70,520 core-3 rows and 34,412 all-five rows. Raw official XBRL
was not substituted into that bundle.

For the same calendar window, official trading history has 1,107,115 raw
keys: 981,833 intersect the panel, 107 panel keys are missing from the
official route, and 125,282 official keys are not in the panel. There are no
duplicate official keys. On the exact intersection, raw-field mismatches are
close 1,307, high 1,647, low 1,537, and volume 0, affecting 1,785 keys.
Official-only rows include dates outside the panel key set, so this is a raw
key/field comparison rather than session-calendar, adjustment, CA-basis, or
canonical-replacement evidence.

## Authority interpretation

The new evidence supports raw discovery, structural fact coverage, snapshot
classification stability, raw daily-field comparison, bounded event discovery,
and current identity cross-checks. It does not prove:

- population completeness or survivorship safety;
- issuer/security/ISIN continuity, ticker reuse, or relisting identity;
- publication/knowledge-time, available-at, or revision/vintage semantics;
- exchange-effective corporate-action transitions or price basis;
- financial taxonomy/unit/consolidation/restatement comparability;
- executable historical capacity; or
- policy-authorized eligibility/admission.

The ratio classification result is particularly important: stable repeated
labels are evidence about this response surface, not proof that the labels were
historically effective or point-in-time available. The remaining question is
therefore an authority-contract question, not a row-count question.

## Evidence and reproducibility

- Machine packet:
  `research_knowledge/official_idx_authority_crosswalk_v1.json`
- Audit:
  `research/alpha_idx_authority_crosswalk_v1.py`
- Focused tests:
  `tests/test_alpha_idx_authority_crosswalk_v1.py`
- External crosswalk SHA-256:
  `811f2cb68a3528ce25a5fbd0f6173e4d502584a9dc7760d2a760f951dfa8db6b`
- External XBRL projection SHA-256:
  `545ceb8d852a30ae505f4331683f8d1abf8cfc0a06a17b83e0f7482675d99a24`

No protected predictive outcomes were inspected. No canonical data,
production, cloud, provider, capture, telemetry, scheduler, or incumbent state
was mutated.

## Reopen conditions

Reopen only with a genuinely new authority contract: population-wide PIT
membership and lifecycle, issuer/security identity, publication/knowledge time
and revisions, exchange-effective CA basis, financial taxonomy/restatement
semantics, or an explicit eligibility/admission policy. More copies of the same
raw ticker/report/ratio snapshot family do not reopen this finding.
