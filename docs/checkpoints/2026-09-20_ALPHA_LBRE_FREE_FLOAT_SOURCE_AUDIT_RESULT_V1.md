# LBRE Monthly Free-Float Source Audit Result V1

Status: `PASS_STRUCTURAL_ONLY / SOURCE_REMEDIATION_REQUIRED`

This is a read-only, outcome-blind audit of the locally persisted IDX LBRE
monthly free-float corpus. It does not call the provider, open targets or
outcomes, mutate source/canonical data, create a universe mask, or construct a
feature or candidate.

## Structural evidence

- The artifact manifest declares 58,671 files and all 58,671 are present.
- Every declared file matches its manifest byte count and SHA-256. The
  manifest sidecar also matches the manifest file.
- The manifest schema is `IDX_LBRE_MONTHLY_FREE_FLOAT_HISTORY_V1` with 27
  monthly targets from 2024-04-30 through 2026-06-30.
- Normalized counts are exact against the persisted replay summary: 25,262
  canonical rows, 24,394 admitted rows, 23,373 current rows, and 28,254 exact
  input rows.
- Required fields, as-of dates, publication timestamps, free-float ranges,
  and provenance hash fields pass structural validation. Admitted source keys
  are a subset of canonical source keys, and current source keys are a subset
  of admitted source keys.
- The independent verifier, generic artifact hash contract, and outcome-blind
  target/privacy firewall all return `PASS`.

## Lineage and admission limits

- Canonical rows contain 1,326 duplicate ticker/date rows; admitted rows retain
  1,021 correction-related duplicate ticker/date rows; exact input contains
  4,318 duplicate ticker/date rows. These are lineage/revision surfaces, not
  rows to silently deduplicate.
- The current normalized set contains 950 rows marked `CORRECTION`; the
  current-set selection therefore does not mean “original-only”.
- The lineage audit reports 868 unresolved rows:
  - 532 `GENUINE_SOURCE_AMBIGUITY_MULTIPLE_ORIGINALS`;
  - 332 `SOURCE_EVIDENCE_MISSING_NO_ORIGINAL`;
  - 4 `INVALID_CORRECTION_CHRONOLOGY`.
- The source covers monthly issuer reports, not a continuous daily
  population-wide panel. Coverage before 2024 is absent from this corpus.
- No issuer/ISIN transition chain, corporate-action linkage, revision/vintage
  completeness certificate, or independent public-availability contract is
  established. `published_at` being present is not by itself a full PIT
  admission certificate.

## Decision

The corpus is valuable as a future free-float capability and lineage source,
but remains `PARTIAL / SOURCE_REMEDIATION_REQUIRED`. It must not be used for
candidate features, daily universe masks, corporate-action repair, or
protected evaluation. Remediation would require resolving the 868 lineage
rows, establishing issuer/ISIN and CA continuity, extending/qualifying the
historical coverage contract, and proving public-availability semantics.

## Artifact provenance

- Artifact manifest SHA-256: `e134809a1f1b745daf2f21c33ab7db78c38d1d5d520f5320564359d5b865bd86`
- Canonical observations SHA-256: `90cbb4970aa2764da3192174ff909e5171aa158ae30cc7398e15a8d51a5825d4`
- Admitted observations SHA-256: `ad127af72e6ea0e17bd8b2676c4f3072f95855027dc70ff5484294a27b66d9f5`
- Current observations SHA-256: `9f6f172fbcb4531f8cf75f76487c8890370aa07fd314a7e9ded3f60fc3706af9`
- Exact observations SHA-256: `190430c45e069c016d6f1e8ecd300857007129437541cdb45cfa1de73a582331`
- Replay summary SHA-256: `29836de791d08a1aee937259752e97f9068177fd9b11c92549eed7c0829f66ff`
- Lineage audit SHA-256: `04328335f5ebd01a52829393f0b81d8cc168d7804dc11ef6f330a424816834f9`
- Parse audit SHA-256: `69b27060230899eb997582f1307f6b35f2920b4829b42883b08cd0ec246cfb1e`
- Monthly census SHA-256: `350733aa423306f72ac6a815426f94a081f474573f0f9c7d8c7256bc46e29d0b`
- Audit JSON SHA-256: `610b8df86ee474de200c71e06566e035dc68738428188a6edbae5bbceb6d44b3`
- Independent verification JSON SHA-256: `00e84a51dd393d4872d5b23e257028d7185f1dd1f7d0cde022833b92e0f33bfa`
- Hash-contract JSON SHA-256: `ccefdcdab28e5b5efcc17bedfe3d11f4280a21e94c6b28bd507d5d4c07bf6915`
- Privacy/target firewall JSON SHA-256: `e56b03d58e4a5e3946ddeab38564e35f414514dc7bdc36bad1ad6a535b561ec3`
- Builder SHA-256: `26dc5dabc38ef6e32c4f9dd04ca6375c76cdfe73514f5d913c79bb19e10c71db`
- Independent verifier SHA-256: `099992f896c0e8e1141daa455a8d5dae187a54387b6994fa36004f2489f91915`

No target, outcome, incumbent, provider, network, cloud, canonical, capture,
or production state was accessed or modified.
