# Checkpoint — PIT sector source discovery update

Date: 2026-08-11 (Asia/Jakarta)
Status: `SOURCE_DISCOVERY_PROGRESS_RECORDED_NOT_CANONICAL_YET`
Branch: `data/idx-pit-sector-history-v1`

## New finding

A public company press release that cites the IDX sectoral classification evaluation surfaced the 2023 announcement reference:

- `Peng-00156/BEI.POP/06-2023`;
- cited announcement date: `2023-06-22`;
- described sector-index period: July 2023 through June 2024;
- described IDX-IC rule: regular classification evaluation occurs annually in April-May, results are announced at the end of June, and become effective on the first exchange day of July.

This is useful for discovery, but it is **not yet canonical** for the PIT dataset because the corresponding official IDX announcement/attachment URL has not been recovered and SHA-pinned.

The source inventory therefore records the announcement reference/date but keeps `IDX_IC_ANNUAL_2023` in `DISCOVERY_REQUIRED` with `effective_from=null` and no download URL.

## Why this matters

The project must distinguish:

```text
secondary source discovers official reference
        !=
official source acquired and canonicalized
```

A secondary page may help locate the document, but it must not silently become historical truth.

## Remaining blockers

- official 2023 attachment URL + exact effective date;
- annual 2021 and 2022 official references/attachments;
- annual 2024 and 2025 official attachment URLs;
- annual 2026 official reference/attachment;
- IPO classification events and any exceptional reclassifications.

No source-specific parser or model experiment is authorized by this discovery update.
