# Financial PIT fact-schema independent review

Reviewed: data/financial-pit-fact-schema-v1 @ fce046890884c22f214eef480a7156753e865048

Verdict: FINANCIAL_PIT_FACT_SCHEMA_PROTOTYPE_ACCEPTED_MARKET_WIDE_EXTRACTION_STILL_BLOCKED

Accepted bounded evidence: 36 filings; 212 candidate observations; 141 extracted; 42 unresolved unit/scale; 14 conflicting facts; 15 prior-period XBRL candidates correctly rejected. The append-only version-aware schema and fail-closed extraction contract are accepted for further bounded work.

Market-wide extraction remains blocked. The next scientific priority is a bounded correction/restatement lineage audit on the known RONY FY2024, BAPA FY2025, and MUTU H1-2025 correction markers. It should test whether original and corrected announcements/files have distinct defensible publication timestamps and immutable bytes, whether prior versions remain retrievable, and whether current endpoints can retrospectively replace bytes under an older publication record. Unit/scale and repeated-label hardening can follow because those issues reduce coverage rather than PIT correctness.
