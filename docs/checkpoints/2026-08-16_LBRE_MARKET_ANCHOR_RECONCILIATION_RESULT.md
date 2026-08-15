# LBRE / Market-Wide Free-Float Anchor Reconciliation V1 — Result

Date: 2026-08-16 Asia/Jakarta
Branch: `data/idx-lbre-market-anchor-reconciliation-v1`
Scientific parent: `data/idx-lbre-monthly-free-float-history-v1@bf0648c9dd37ad4a25e2de42d6f4a18fd19f857d`

## Scope and boundaries

This was an offline-only decomposition of the accepted 2025-12-31
LBRE/market-wide comparison. The two parent manifests were verified before
analysis. No network calls, acquisition, redownload, parser/lineage change,
source replacement, daily state, forward-fill, effective-supply or
Foreign-Flow feature work, model work, or outcome access was performed.

The existing percentage comparison tolerance was retained exactly at 0.01
percentage points. Official reported shares and percentages remain separate
values; the LBRE implied percentage is diagnostic only and never replaces
either source value.

## Parent verification

- Monthly-history root:
  `D:\Documents\Project\idx-lbre-monthly-free-float-history-20260815-v1`
  - manifest SHA-256:
    `e134809a1f1b745daf2f21c33ab7db78c38d1d5d520f5320564359d5b865bd86`
- Historical market-anchor root:
  `D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`
  - manifest SHA-256:
    `7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`

Both hashes matched the pinned inputs.

## Full decomposition

The 2025-12-31 union contains 923 tickers: 885 overlaps and 38 market-only.
The prior `260 AGREE / 625 CONFLICT / 38 SINGLE_SOURCE` result decomposes as:

| Class | Count | Meaning |
|---|---:|---|
| `EXACT_AGREE` | 260 | Shares identical and percentages within 0.01 pp |
| `SHARES_AGREE_PCT_DIFF` | 616 | Shares identical; reported percentages differ beyond tolerance |
| `SHARES_DIFF_PCT_AGREE` | 0 | Shares differ; percentages within tolerance |
| `SHARES_AND_PCT_DIFF` | 9 | Both reported shares and percentages differ |
| `LBRE_ONLY` | 0 | Present only in LBRE at this anchor |
| `MARKET_ONLY` | 38 | Present only in the market-wide anchor |

Therefore, among the prior 625 conflicts:

- 616 (98.56%) have identical official free-float share counts and differ
  only on the reported percentage axis;
- 9 (1.44%) have genuine reported share-count disagreement.

No row was silently selected, overwritten, or converted from one source to the
other.

## Genuine share-count conflicts

The nine `SHARES_AND_PCT_DIFF` rows are:

| Ticker | Absolute share delta | Relative to LBRE shares | Percentage-point delta |
|---|---:|---:|---:|
| CSIS | 1,381,000 | 0.522% | -0.68 pp |
| HOKI | 2,986,991,880 | 50.061% | +30.85 pp |
| OLIV | 87,633,400 | 16.779% | -4.61 pp |
| PANR | 28,000,000 | 11.195% | -1.97 pp |
| SGRO | 400,000 | 0.064% | -0.03 pp |
| TFAS | 763,500 | 0.220% | +0.08 pp |
| TRIN | 227,562,900 | 28.959% | -5.04 pp |
| UNTR | 110,025,800 | 9.163% | -2.90 pp |
| WOOD | 210,505,500 | 14.987% | -3.28 pp |

Across all 885 overlaps, the absolute share-delta distribution has median
0, q75 0, mean 4,127,981.90, and maximum 2,986,991,880 shares. This reflects
the 876 exact-share overlaps plus the nine unresolved conflicts; it is not a
justification to average or select a source.

For the 885 LBRE rows with listed shares available, the diagnostic difference
between LBRE reported percentage and LBRE shares-implied percentage has median
approximately -0.000005 pp, q25 -0.002435 pp, q75 +0.002087 pp, minimum
-0.004988 pp, and maximum +0.005000 pp. This confirms that the LBRE internal
shares/percentage relationship is tightly rounded in this sample, but does
not resolve cross-source disagreements.

## Publication-time comparison

The market-wide anchor has one publication timestamp,
`2026-02-19T10:45:51+07:00`. LBRE publication timestamps are issuer-level.
Across 885 overlaps:

- LBRE was published before the market anchor for 882 rows;
- same timestamp: 0 rows;
- LBRE was after the market anchor for 3 rows: BHIT, EKAD, and NISP.

The LBRE-minus-market publication delta has median -3,682,606 seconds
(approximately 42.6 days), q25 -3,761,541 seconds, q75 -3,529,602 seconds,
minimum -4,145,833 seconds, and maximum +1,682,225 seconds. These are
publication-time diagnostics only; they do not establish that either source
is the correct value for a conflicting row.

## Denominator decision

`free_float_shares` from LBRE is usable as a historical denominator only with
explicit row-level exclusions/gaps:

- 876/885 overlap rows have identical shares across LBRE and market-wide
  evidence;
- 9/885 overlap rows have unresolved share-count conflicts and must remain
  fail-closed until separately reconciled;
- 38 market-only rows have no LBRE observation at this anchor;
- 0 LBRE-only rows were found.

The allowed final verdict is:

`LBRE_FF_SHARES_DENOMINATOR_PARTIAL_CONFLICT_REVIEW_REQUIRED`

This is not a blanket source preference. The result supports conditional use
for explicitly non-conflicting rows, with market-wide evidence retained as an
independent anchor and all unresolved rows excluded or surfaced. A later
contract would need to define the treatment of the nine conflicts and the 38
market-only gaps before claiming complete market-wide denominator coverage.

## External artifacts

- Root:
  `D:\Documents\Project\idx-lbre-market-anchor-reconciliation-20260816-v1`
- Manifest:
  `D:\Documents\Project\idx-lbre-market-anchor-reconciliation-20260816-v1\artifact_manifest.json`
- Manifest SHA-256:
  `34fe46f9077fe8c6630fbec5f3682718f01cea1456d7bcb904fa7be6a9479840`
- Manifest file count: 6
- Full classified table:
  `normalized/classified_reconciliation_2025_12_31.json`
- Bounded evidence sample:
  `reports/evidence_review_sample.json`

## Validation

- Focused reconciliation tests: `3 passed`.
- Full pytest: `72 collected; 71 passed, 1 failed`.
- Remaining failure is the pre-existing unrelated storage expectation:
  `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expects one conflict but current independent `raw_close` and
  `vendor_adj_close` auditing returns two. No storage change was made.
- `git diff --check`: PASS.

No downstream daily free-float state, effective-supply, Foreign Flow,
features, models, or outcomes were started.
