# Financial PIT Revision Lineage — ChatGPT Acceptance

Date: 2026-08-13 (Asia/Jakarta)
Reviewed branch: `data/financial-pit-revision-lineage-v1`
Reviewed HEAD: `58e5e26de4646794a38e844decf54890696375c5`

## Verdict

`FINANCIAL_PIT_REVISION_POLICY_ACCEPTED_FAIL_CLOSED_MARKET_WIDE_USE_ALLOWED`

The bounded evidence is sufficient to accept the versioning policy, not to claim complete market-wide revision-history coverage.

## Accepted evidence

- RONY FY2024, BAPA FY2025 and MUTU H1-2025 each expose two independently retrievable official versions.
- Original and correction/revision versions have distinct `TglPengumuman` timestamps and distinct XLSX/inlineXBRL/instance bytes.
- The current `GetFinancialReport` pointer selects the latest version in all three cases.
- The older target XLSX URLs still return their original bytes; no retrospective byte replacement was observed in the bounded sample.
- `File_Modified` matches the latest announcement timestamp to the second for the current pointer but is not accepted as historical publication authority.
- The literal BAPA `tes` reference remains preserved as-is and must not be normalized or guessed.

## Accepted PIT policy

Use a filing version only from its own proven publication timestamp onward. If an earlier version is unavailable, the fact is missing before the first observed version; never backfill a later version into an earlier knowledge state.

This policy makes incomplete revision lineage a coverage loss rather than a look-ahead correctness failure, provided every consumed version retains its own publication timestamp, attachment hash, and source evidence.

## Boundary

A larger market-wide reconstruction of every historical correction chain is not required before further fact-extraction engineering. Any filing with contradictory or insufficient version evidence must still fail closed as latest-version-only, retrospective-byte-replacement-risk, or unresolved.

Next priority is bounded hardening of unit/scale and repeated-label/taxonomy semantics. No market-wide fact extraction, ratios/features, model work, or protected-outcome access is authorized by this acceptance alone.
