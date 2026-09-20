# Official IDX raw acquisition surfaces — result V1

Date: 2026-09-20
Branch: `codex/alpha-available-data-20260919`
Boundary: outcome-blind, external staging only, no admission

## Result

The available-data lane expanded the evidence surface through ordinary public
requests to `www.idx.id` and pinned public source-contract repositories. The
new material is `RAW_EVIDENCE_ONLY_NO_ADMISSION`.

| Surface | Retained coverage | What it adds | Admission limit |
|---|---:|---|---|
| Official report index | 5,870 annual rows, 1,009-code union, 2019–2025 | report periods, attachment paths, File_Modified, file IDs | File_Modified is mutable/revision evidence, not available-at time |
| Official annual XBRL | 5,864 retained instance.zip payloads across 2019–2025; 4,961 downloaded annual payloads structurally parsed (903/903 in 2023) | raw filing attachments and XML structure | six 2024/2025 attachments missing or ambiguous; no taxonomy/PIT/issuer/revision contract |
| Official monthly ratios | 60 snapshots, 51,662 rows | issuer-level ratio and fsDate coverage census | query month/fsDate are not proven publication cutoffs |
| Official trading history | 983 codes, 1,365,333 rows, 2020-01-02–2026-09-18 | daily fields, foreign buy/sell, share transitions, zero-trade rows | no population, vintage, adjustment/CA, or capacity authority |
| Official issued history | 1,043-code union, 1,563 event rows | IPO/listing/HMETD/split/bonus/delisting event discovery | event labels/dates are not complete PIT lifecycle or effective price basis |
| Official profile detail | 1,043-code union; 1,016 populated and 27 empty profiles | current code/name/listing/status field presence | no stock-ISIN field, historical vintage, or issuer-continuity contract |

The event route exposes a concrete code-universe effect: the 1,009-code
financial-report union had no explicit `Delisting` label in the bounded result;
adding the 34 price-only codes surfaced 23 explicit delistings, including
CNTX. This is visibility evidence, not population-completeness or
survivorship evidence.

## Durable interpretation

Official-source status does not establish a combined historical authority.
Report `File_Modified`, ratio `fsDate`, trading row dates, issued-history event
dates, and current-directory listing dates remain distinct until a contract
binds publication/knowledge time, revisions, issuer/ISIN continuity,
population membership, exchange-effective corporate-action transitions, and
capacity. No candidate was admitted and no policy was selected.

Raw result summaries and hashes are recorded in
`research_knowledge/official_idx_acquisition_surfaces_v1.json`. Raw payloads
remain outside the repository at the isolated staging root documented there.

## Safety

No protected predictive outcomes, provider credentials/calls, canonical data,
production/cloud/capture/telemetry state, scheduler, incumbent, GitHub
dispatch, or runtime state was accessed or mutated. The only repository
changes are research adapters, tests, durable authority documentation, and
registry updates on this branch.
