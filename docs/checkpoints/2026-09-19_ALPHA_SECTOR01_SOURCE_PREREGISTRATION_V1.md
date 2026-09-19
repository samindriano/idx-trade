# SECTOR-01 Official IDX-IC Archive — Source Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Hypothesis: `SECTOR-01`

## Scope

Audit only the locally staged official IDX-IC archive under
`D:\Documents\Project\idx-pit-sector-official-raw-20260811`.

The audit will inventory archive files and hashes, inspect structured sector
workbooks when present, and record announcement/effective-period text,
constituent-row counts, ticker uniqueness, duplicate rows, and field shape.
PDF-only sources will be recorded as present but not converted into row-level
membership. The audit will not scrape providers, contact the network, inspect
targets/outcomes, modify canonical data, or create a feature/candidate.

## Frozen source scope

- `IDX_IC_2021_Peng-00171.zip`
- `IDX_IC_2022_Peng-00150.zip`
- `IDX_IC_2023_Peng-00156.zip`
- `IDX_IC_2024_Peng-00128-ID.zip`
- `IDX_IC_2025_Peng-00110-ID.zip`
- `IDX_IC_2026_Peng-00100-ID.zip`
- `IDX_IC_BASELINE_2021_idx-industrial-classification.zip`

The palm/issuer-specific incidental archive is outside this sector-archive
scope. The 2022 and 2023 sector workbooks are the only expected row-level
structured membership surfaces in this audit. Other files remain inventory
evidence unless they expose structured row-level membership without a new
interpretive step.

## Registered checks

1. Exact source-file SHA-256 and archive-member inventory.
2. Structured workbook count and sector-sheet count.
3. Announcement date/effective-period text presence and consistency within a
   workbook.
4. Current constituent row count, ticker non-null/format validity, duplicate
   ticker count, and per-sheet uniqueness.
5. Whether a row-level available-at/publication timestamp, daily membership
   interval, issuer/security identity, revision/vintage, or transition chain
   is present.
6. Fail closed if workbook structure is ambiguous, duplicate tickers appear,
   or effective/publication semantics cannot be distinguished.

## Predeclared interpretation

This is a source-capability audit. Even a clean workbook does not establish a
PIT-safe daily sector feature. `SOURCE_PARTIAL_STRUCTURAL_SIGNAL` is the
maximum possible disposition from this audit; `SOURCE_BLOCKED` is expected if
membership intervals, publication timing, or identity authority are absent.
No predictive metric, target, IC/ICIR/OOS, candidate, or incumbent comparison
will be computed.

## Guardrails

- No target/outcome/protected vault access.
- No provider/Zapi/network access.
- No incumbent/model/canonical/capture/cloud/R2/scheduler/telemetry mutation.
- All outputs go to the isolated external staging root and this worktree only.
- Missingness, PDF-only coverage, ambiguous classification, and identity gaps
  remain explicit; no imputation, forward-fill, or daily expansion is allowed.
