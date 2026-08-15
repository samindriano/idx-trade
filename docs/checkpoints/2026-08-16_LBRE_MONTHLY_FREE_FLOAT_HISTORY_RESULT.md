# LBRE Monthly Free-Float History V1 — Result

Date: 2026-08-16 (Asia/Jakarta)
Branch: `data/idx-lbre-monthly-free-float-history-v1`
Scientific parent: `data/idx-lbre-lineage-parser-remediation-v1@a42715f027fceb0c7cd24f68e65c9e91b7bfa049`

## Verdict

`LBRE_MONTHLY_FF_HISTORY_PARTIAL_SOURCE_USEFUL`

The official IDX issuer LBRE source and generalized acquisition/replay path
are usable for bounded research with explicit gaps. This is not a complete
ticker-by-month panel: no synthetic completeness grid, forward-fill,
interpolation, holder/HSC arithmetic, or ambiguous-original selection was
used. The remaining coverage and lineage gaps stay fail-closed.

## Parent verification

- Snapshot root: `D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`
- Snapshot manifest SHA-256:
  `7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`
- Remediation root: `D:\Documents\Project\idx-lbre-lineage-parser-remediation-20260815-v1-final6`
- Remediation manifest SHA-256:
  `cb2e929a8e7d5fc481c0eed6add4a6ba848c5a3374c65ea38e5fbe3fa5727244`
- Both manifests matched before acquisition/replay.

## Discovery and acquisition

The direct official IDX endpoint was `ListedCompany/GetAnnouncement` with
keyword `Laporan Bulanan Registrasi Pemegang Efek`, `pageSize=1000`, the
bounded publication query `20240501..20260815`, and zero-based `indexFrom`
page parameters. The endpoint reported `27,724` records over `28` pages;
all pages were fetched, page cardinality and stable total were checked, and
`30,405` main LBRE attachments from `954` tickers were inventoried.

Acquisition was append-only and resume-safe:

- `1,068` official parent attachments reused by exact verified path/hash;
- `29,335` new official attachment downloads;
- `2` bounded HTTP 404 download errors (`CMRY`, `ATLA`);
- no valid artifact was overwritten.

All raw metadata, attachment bytes, retrieval metadata, parser outputs, and
lineage outputs are outside Git under:

`D:\Documents\Project\idx-lbre-monthly-free-float-history-20260815-v1`

## Parsing and lineage

- Candidates: `30,405`
- Exact explicit shares + percentage + listed-shares parses: `28,254`
- Audit rows: `2,151`
  - `UNRESOLVED_FIELDS`: `1,007`
  - `NON_TARGET_POSITION`: `1,092`
  - `PARSER_ERROR`: `42`
  - `UNRESOLVED_POSITION`: `8`
  - `DOWNLOAD_ERROR`: `2`
- Canonical rows after transport/economic alias collapse: `25,262`
- Transport/economic aliases: `2,992`
- Admitted append-only observations: `24,394`
  - `ORIGINAL`: `23,373`
  - `CORRECTION`: `1,021`
- Current exact observations: `23,373`
- Lineage unresolved: `868`
  - multiple genuine originals: `532`
  - no recoverable original for a correction/current row: `332`
  - invalid correction chronology: `4`

Corrections were linked only to a unique prior admitted state in publication
order. Same-announcement economic reuploads and byte-identical transport
duplicates remain visible as aliases. Explicit correction markers were used;
no ticker-specific forensic rule was copied into production logic.

## Per-position-month census

`acq` is discovered/download-success-or-reused, `exact` is parser exact,
`canon` is post-alias canonical input, `alias` is collapsed duplicate count,
`admit` is append-only replay admission, `unres` is replay lineage unresolved,
and `current` is the current exact observation count after replay.

| Position month | acq | exact | canon | alias | admit | unres | current |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024-04-30 | 1146 | 1110 | 902 | 208 | 875 | 27 | 850 |
| 2024-05-31 | 1183 | 1131 | 898 | 233 | 864 | 34 | 844 |
| 2024-06-30 | 1279 | 1251 | 903 | 348 | 873 | 30 | 855 |
| 2024-07-31 | 1181 | 1134 | 903 | 231 | 868 | 35 | 849 |
| 2024-08-31 | 1126 | 1099 | 896 | 203 | 865 | 31 | 849 |
| 2024-09-30 | 2316 | 2274 | 909 | 1365 | 866 | 43 | 846 |
| 2024-10-31 | 1221 | 1187 | 912 | 275 | 875 | 37 | 856 |
| 2024-11-30 | 941 | 907 | 907 | 0 | 871 | 36 | 848 |
| 2024-12-31 | 964 | 923 | 923 | 0 | 866 | 57 | 841 |
| 2025-01-31 | 965 | 914 | 909 | 5 | 866 | 43 | 854 |
| 2025-02-28 | 949 | 919 | 914 | 5 | 892 | 22 | 871 |
| 2025-03-31 | 958 | 926 | 921 | 5 | 878 | 43 | 855 |
| 2025-04-30 | 950 | 922 | 916 | 6 | 899 | 17 | 880 |
| 2025-05-31 | 950 | 923 | 919 | 4 | 906 | 13 | 882 |
| 2025-06-30 | 948 | 920 | 916 | 4 | 893 | 23 | 879 |
| 2025-07-31 | 962 | 918 | 917 | 1 | 895 | 22 | 877 |
| 2025-08-31 | 966 | 926 | 922 | 4 | 896 | 26 | 881 |
| 2025-09-30 | 971 | 933 | 922 | 11 | 905 | 17 | 884 |
| 2025-10-31 | 958 | 924 | 920 | 4 | 900 | 20 | 882 |
| 2025-11-30 | 970 | 944 | 926 | 18 | 911 | 15 | 889 |
| 2025-12-31 | 1053 | 1020 | 1013 | 7 | 986 | 27 | 885 |
| 2026-01-31 | 994 | 965 | 961 | 4 | 934 | 27 | 890 |
| 2026-02-28 | 1034 | 981 | 967 | 14 | 939 | 28 | 872 |
| 2026-03-31 | 1178 | 1126 | 1121 | 5 | 1020 | 101 | 843 |
| 2026-04-30 | 1064 | 1021 | 1005 | 16 | 962 | 43 | 857 |
| 2026-05-31 | 989 | 952 | 941 | 11 | 930 | 11 | 884 |
| 2026-06-30 | 1045 | 1004 | 999 | 5 | 959 | 40 | 870 |

## June-2026 parent reconciliation

The accepted remediation parent has `877` current exact rows for 2026-06-30;
the generalized monthly replay has `870`. The difference is fully explicit:

- `AYAM`: two independent ORIGINAL announcements with identical economics
  but no deterministic supersession. The generalized contract correctly
  leaves it unresolved; choosing the parent’s one row would violate the
  multiple-original fail-closed rule.
- `DGNS`, `KSIX`, `LAPD`, `LUCK`, `OASA`, `SICO`: the official reports expose
  the current values but their previous/current two-column presentation is
  malformed or semantically non-comparable (for example a prior percentage
  column contains a non-percentage numeric string). The generalized parser
  refuses to promote these without a new evidence-backed template contract.
- `SPRE`: the exact `KOREKSI` attachment is available, but its original is
  not exact/recoverable, so the correction cannot be linked to a unique prior
  state.
- `INAF`: an additional official exact observation appears in the wider
  publication discovery and is not in the parent’s bounded June current set.

Thus `877 - 8 + 1 = 870`; no row was silently selected or synthesized.

## 2025-12 cross-source reconciliation

Against the accepted official market-wide anchor:

- `AGREE`: `260`
- `CONFLICT`: `625`
- `SINGLE_SOURCE`: `38`

No conflict was resolved by preference; these are diagnostic statuses only.

## Artifacts

- External root:
  `D:\Documents\Project\idx-lbre-monthly-free-float-history-20260815-v1`
- Artifact manifest: `artifact_manifest.json`
- Manifest file count: `58,671`
- Manifest SHA-256:
  `e134809a1f1b745daf2f21c33ab7db78c38d1d5d520f5320564359d5b865bd86`
- Durable output includes discovery page captures, acquisition inventory,
  exact observations, canonical/admitted/current observations, aliases,
  parser audit, lineage audit, monthly census, and 2025-12 reconciliation.

## Validation and boundaries

- Focused LBRE/statutory suites: `21 passed`.
- Full repository collection: `69 tests`; `68 passed, 1 failed`.
- The one failure is the pre-existing unrelated
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`:
  current storage semantics surface independent `raw_close` and
  `vendor_adj_close` conflicts while the old test expects one. No storage
  file was changed in this lane.
- `git diff --check`: PASS before commit.

No models, features, outcomes, Foreign Flow integration, daily FF state,
effective supply, holder/HSC reconstruction, or unrelated lanes were touched.
