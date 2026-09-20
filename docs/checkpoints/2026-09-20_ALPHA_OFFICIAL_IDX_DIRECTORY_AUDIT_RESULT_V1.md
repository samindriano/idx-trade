# Official IDX Current Directory Audit — Result V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `CAPABILITY FOUND / HISTORICAL ADMISSION BLOCKED`

## Question

Does a directly acquired official IDX current-company directory add independent
evidence around the public EOD snapshot gap and the relationship between the
current directory and the historical anchor surface?

This is an outcome-blind, read-only audit. It did not access targets or
protected outcomes, mutate canonical data, call a provider during verification,
or change production, cloud, capture, telemetry, or scheduler state.

## Acquired artifact

The ordinary public GET endpoint
`https://www.idx.id/primary/ListedCompany/GetCompanyProfiles?start=0&length=9999&code=`
returned HTTP 200. The retained raw response has SHA-256
`bdca057527fa061fd2318f7c9aa6c4f2c508d50a98f013c38ea1a7c4c9ad2312`; the
retained response headers have SHA-256
`9ce728a337c52d05f2b497ea84be50a1f5a735fc13338f49bbf2ebebae114121`.
The response date header is retrieval metadata only: `Sun, 20 Sep 2026
06:11:24 GMT`.

Structural checks passed:

- `recordsTotal = recordsFiltered = 962` and 962 data rows were returned;
- all 962 issuer codes are unique and all `Status` values are `0`;
- listing dates parse from `1977-08-10` through `2026-07-10`;
- code and listing-date sets exactly match the prior official current snapshot;
- official current codes are a subset of the 980-code anchor surface.

The response supplies current code, issuer name, listing date, board, sector,
and subsector fields, but no issuer/ISIN transition field, historical
publication/available-at time, revision/vintage identifier, or
corporate-action basis linkage.

## Cross-source findings

The six codes present in the official current directory but absent from the
newer public Pholenk EOD snapshot are:

| Code | Official listing date |
|---|---|
| `JECX` | 2026-07-07 |
| `JELI` | 2026-07-07 |
| `BACH` | 2026-07-08 |
| `EMMI` | 2026-07-08 |
| `PRDL` | 2026-07-09 |
| `RANS` | 2026-07-10 |

This independently strengthens the bounded snapshot-timing/new-issue
explanation already supported by the IPO dataset. It does not prove that the
public EOD source was intended to contain those rows or establish a row-level
availability timestamp.

The 18 anchor-only codes are `CNTB`, `CNTX`, `FINN`, `FORZ`, `FREN`, `HDTX`,
`JKSW`, `KPAL`, `KPAS`, `KRAH`, `MAMI`, `MASA`, `MFIN`, `MYRX`, `NIPS`,
`PRAS`, `RMBA`, and `TURI`. CNTX is therefore historical-anchor-only relative
to this current snapshot, while it remains discoverable in both public EOD
snapshots. That combination is not a contradiction: current-directory
membership, historical-anchor membership, and public EOD row presence are
different surfaces.

## Relationship to the lifecycle archive

The existing official lifecycle archive remains the stronger bounded artifact
for event-level listing/delisting capability: 440 monthly requests, 962 current
rows, and 163 delisting records. Its existing audit remains
`PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED` because it lacks daily PIT
membership, issuer/ISIN transition continuity, publication/knowledge time,
revision/vintage semantics, and corporate-action linkage, with retained
lifecycle conflicts. The current-directory response does not repair those
limits and was not used to reinterpret any lifecycle row.

## Verdict

| Authority | Result |
|---|---|
| Current-directory identity snapshot | `SUPPORTED_CURRENT_SNAPSHOT` |
| Historical population completeness | `UNKNOWN` |
| Survivorship safety | `UNKNOWN` |
| Daily PIT membership | `MISSING` |
| Issuer/ISIN continuity and ticker reuse | `MISSING` |
| Publication/available-at and revision authority | `MISSING` |
| Corporate-action effective basis | `MISSING` |
| Historical predictive-research admission | `BLOCKED` |

The durable summary is `research_knowledge/official_idx_directory_audit_v1.json`.
The read-only verifier is `research/alpha_official_idx_directory_audit_v1.py`.
The isolated raw and result artifacts remain under the external staging root.

## Reopen condition

Reopen only for an authoritative population-wide daily PIT/lifecycle contract
with issuer/ISIN continuity, publication/knowledge time, revision/vintage
semantics, and corporate-action basis linkage. More current-directory or
ticker-file snapshots would be redundant for the present question.
