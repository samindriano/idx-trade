# IDX-Trade Alpha — Ownership/KSEI Source Audit Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Disposition: `PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`

## Question

Can the already persisted KSEI ownership/free-float archive provide a
population-wide, point-in-time feature surface for the alpha program, or does
it only support a future research specification?

## Evidence and method

The audit was read-only and outcome-blind. It read the existing KSEI ZIPs,
existing IDX company-profile normalized CSVs, and the frozen research panel.
No provider/network request, target/outcome access, feature construction,
panel substitution, or canonical mutation occurred.

Reproducible code and verifier:

- `research/alpha_ownership_ksei_source_audit_v1.py`  
  SHA-256: `aa228457a18566cf28932529ab7a96a749ef6ab6f89c6c6a9399a0bc06175a4e`
- `research/verify_alpha_ownership_ksei_source_audit_v1.py`  
  SHA-256: `c6bc4781a96dabfa5627efe8a943a6195503ea381498c6137875bd8e74bead83`

Staged output:

`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_ownership_ksei_source_audit_v1_v2.json`

SHA-256: `a90883bf3614c59cd80d37ce87efc4594185fb78a03659addcdd68fe0878f8e6`  
Independent verification output SHA-256:
`41a8d525905f4611142e23430befae3f35c053bdfa4abebcac1038f3ecb090df`  
Target/privacy firewall output SHA-256:
`d6462fbe5d29efbc9f7b6ed2198b3f5ca34c68bc753fee90fd0917a52d93953a`

Verifier result: `PASS` on every registered check.

## KSEI aggregate snapshot profile

The official `BalanceposEfek` archive has eight persisted snapshots:

| Snapshot date | All rows | Equity rows | Panel tickers on date | Equity/panel overlap |
|---|---:|---:|---:|---:|
| 2021-12-30 | 2,198 | 803 | 696 | 696 (`100%`) |
| 2022-12-30 | 2,462 | 861 | 736 | 736 (`100%`) |
| 2023-12-29 | 2,862 | 939 | 806 | 806 (`100%`) |
| 2024-12-30 | 3,273 | 979 | 843 | 843 (`100%`) |
| 2025-12-30 | 3,624 | 1,002 | 850 | 850 (`100%`) |
| 2026-05-29 | 3,712 | 1,002 | 857 | 857 (`100%`) |
| 2026-06-30 | 3,851 | 1,002 | 841 | 841 (`100%`) |
| 2026-07-31 | 3,802 | 1,007 | 830 | 830 (`100%`) |

The frozen panel has 1,260 dates and 945 tickers. Thus the archive has exact
date support on only `8/1,260` panel dates (`0.6349%`). The 100% overlap above
means that every panel ticker on those eight exact dates is represented by the
source; it does not mean the source is population-complete between snapshots.

## Quality checks

The 25-column pipe-delimited schema is stable across all eight ZIPs. On the
`EQUITY` subset:

- no duplicate security codes within a snapshot;
- no malformed or missing numeric values;
- no negative numeric values;
- no row where local-plus-foreign holder totals exceed `Sec. Num`;
- one row per security/instrument snapshot, not one row per named holder.

Non-equity instruments are present in the same files and must not be silently
mixed into an equity feature. The KSEI fields represent aggregate local and
foreign investor-category composition. They are not named-holder history,
effective free-float ground truth, or an issuer/ISIN transition table.

## Free-float/profile surface

The bounded IDX company-profile archive contains five tickers and 50
normalized holder rows. It has current named-holder/controller snapshots but
no explicit free-float-like, public-ownership, or shares-outstanding field in
the normalized schema. It cannot be backdated to the historical panel.

The bounded official IDX `>=1%` attachment search did not acquire attachment
bytes because the recorded endpoint probes returned non-JSON 503 responses.
The retained public mirror is reference/schema evidence only and already has a
share-total reconciliation failure for one `MAYA` row; it is not canonical.

## PIT and admission assessment

| Gate | Result | Evidence |
|---|---|---|
| Exact panel-date overlap | `PASS NARROW` | 100% of panel tickers on each of the eight snapshot dates overlap. |
| Temporal completeness | `FAIL FOR DAILY USE` | Eight snapshots across 1,260 panel dates; no safe forward-fill contract. |
| Row-level publication/knowledge time | `UNKNOWN` | Archive retrieval timestamps are not the source's public-availability timestamps. |
| Revision/vintage semantics | `UNKNOWN` | No row-level revision identity or historical version selection. |
| Identity continuity | `INSUFFICIENT` | Ticker/code is present; global issuer/ISIN transition authority is absent. |
| Effective free-float authority | `ABSENT` | Aggregate composition and five current profiles do not establish it. |
| New candidate | `NONE` | No C5 or packet entry created. |

## Research disposition

This source is worth preserving as a future ownership/foreign-composition
specification, especially for event or monthly-state research. It is not
admitted for C1-C4 construction, daily forward fill, ownership-change alpha,
or H-FLOW-01 evaluation. The future contract would need publication timing,
revision/vintage lineage, population-wide historical coverage, stable issuer
identity, and explicit semantics for denominator/share-count transitions.

Current status remains:

`H-FLOW-01 = FUTURE_SPECIFICATION / SOURCE_PARTIAL / NOT_ADMITTED`

This result refines the capability map but does not change the candidate
budget, protected evaluation packet, or any incumbent/canonical artifact.
