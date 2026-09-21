# IDX-Trade Historical Calendar Lineage Reconciliation V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **HISTORICAL CALENDAR NOT RECOVERED / REPLAY BLOCKED**

## Read-only search scope

The search used the immutable 29-session copy to collect all embedded
`calendar_sha256` values, then hashed every CSV under the approved retained
root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring`

No provider checkout, fetch, cloud/R2, counter, outcome, scheduler, or live
runtime was accessed. No calendar file was rewritten or substituted.

## Results

| Check | Result |
|---|---:|
| Session manifests examined | 29 |
| Distinct embedded calendar hashes | 23 |
| CSV files hashed under approved root | 128 |
| Historical embedded hashes found in approved CSVs | 0 |
| Current calendar hash found | 1 |
| Matching file | `calendar\exchange_sessions.csv` |

The sole match is the current calendar copy
`8a5fd51630c331b651fcd41bd024a70c6f8fad6dcc9fe9d5393429e16766a6fe`, embedded
only by the 2026-09-18 session manifest. The other 22 distinct embedded hashes
were not found among the 128 approved CSVs. At the manifest-reference level,
28 of 29 sessions still mismatch the current calendar.

The two retained calendar provenance attestations for 2026-08-10 and
2026-08-11 already record that declared capture-time calendar bytes were not
recovered. This search found no later local CSV that changes that conclusion.

## Disposition

`CALENDAR_LINEAGE = BLOCKED / REQUIRES_RECONCILIATION`.

The current calendar is not an admissible historical replacement. The one
session whose embedded hash matches it is still at the current-calendar end
boundary and fails the next-official-session requirement. No historical replay
may proceed until the exact calendar bytes are separately recovered/admitted or
the affected sessions are explicitly marked `NOT_REPLAYABLE`.
