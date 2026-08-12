# PIT Sector History Revival — Independent Review

Date: 2026-08-13 (Asia/Jakarta)
Reviewer: ChatGPT / independent review
Branch reviewed: `data/idx-pit-sector-history-revival-v1`
Reviewed remote HEAD: `46709ed184d128a4c5601e00cd9970927257c247`
Decision: `REVIVAL_RECOVERY_ACCEPTED_FAIL_CLOSED_5_READY_3_BLOCKED`

## Review result

The bounded recovery attempt is accepted as decision-valid evidence work. No canonical source row should be promoted from this result.

The review verified that the branch moved only documentation after the revival implementation checkpoint; `config/pit_sector_sources_v1.json`, source code, and tests were not changed by the recovery result. The canonical inventory therefore remains `5 ready / 3 discovery-blocked`.

## Blocker-by-blocker judgment

### 2022

`IDX_IC_ANNUAL_CLASSIFICATION_2022` remains `DISCOVERY_REQUIRED`.

The bounded search of nearby June-2022 `Peng-00140..00155` references did not recover the dedicated annual listed-company classification announcement for the known seven-company event. Nearby successful official files are unrelated issuer, watchlist, PKIE/index, or other exchange documents. No guessed reference may be promoted.

### 2023

`IDX_IC_ANNUAL_CLASSIFICATION_2023` remains `DISCOVERY_REQUIRED`, but the blocker is materially narrower than before.

The exact annual reference is now strongly established as `Peng-00158/BEI.POP/06-2023`. The recovered mirror is visibly an IDX announcement titled `Perubahan Klasifikasi Industri Perusahaan Tercatat` and enumerates 14 companies. A separate BMTR exchange-announcement copy states that BMTR's change is effective 03 July 2023 and explicitly links `Klasifikasi Peng-00158.pdf`.

Independent web review reproduced those document semantics. However, the annual source bytes currently come only from a third-party mirror, while the direct official IDX static path returns a 22-byte empty ZIP. Under the existing frozen source hierarchy, a mirror may discover/corroborate an official reference but cannot silently substitute for the canonical official IDX attachment. The BMTR effective-date copy is also mirror-hosted. Therefore 2023 is near-resolved but not promotion-safe under the current provenance contract.

### 2026

`IDX_IC_ANNUAL_CLASSIFICATION_2026` remains `DISCOVERY_REQUIRED`.

`Peng-00100/BEI.POP/06-2026` remains the canonical classification event, but it still lacks an explicit event-specific effective date. `Peng-00099` dates sector-index applicability from 01 July 2026; that is not equivalent to the classification-event effective date and must not be used to infer one.

## Validation and provenance

Accepted local validation reported by the recovery checkpoint:

- focused PIT-sector tests: `23 passed`;
- full pytest: `494 collected, exit 0`;
- external recovery manifest SHA-256: `e9de303c5351b24d2d2f67f577a2785b6cf0578deb7c208973914b7667a725cb`.

GitHub review found no config/source/test mutation in the three commits from starting HEAD `620480cd768ea784b82b71b14c1232d406b39143` to reviewed HEAD `46709ed184d128a4c5601e00cd9970927257c247`; changes were limited to checkpoint/handoff/status documentation.

## Decision and next boundary

Accept the revival attempt and park the lane again at `5 ready / 3 blocked`.

Do not run V3-D or any sector-relative model, do not materialize a supposedly complete historical sector panel, and do not relax the source hierarchy ad hoc.

A future 2023-specific continuation is justified only if one of these occurs:

1. the exact official IDX bytes for `Peng-00158` or the linked BMTR exchange announcement are recovered from an official IDX host/archive; or
2. a separately frozen methodology review explicitly authorizes a `VERIFIED_OFFICIAL_DOCUMENT_MIRROR` evidence tier with objective anti-tamper/corroboration requirements. Such a policy change must be decided before looking at downstream model results.

2022 should reopen only on a new exact-reference/archive lead. 2026 should reopen only on event-specific official effective-date evidence.
