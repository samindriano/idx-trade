# Corporate Action PIT Deterministic Linkage V1 — Claim

Date: 2026-08-14 (Asia/Jakarta)
Branch: `data/corporate-action-pit-deterministic-linkage-v1`
Status: `ACTIVE`

This lane continues from the accepted bounded source audit at `data/corporate-action-pit-source-audit-v1@2de089f0e48ae2ee74ffd16c4361155a04dccc30` and independent acceptance `review/idx-corporate-action-pit-source-audit-acceptance-v1@32e4ef8f33f8e58892ae7c395daf388d4ff47619`.

Scope is limited to event-specific deterministic linkage design and bounded offline validation against the existing immutable audit artifacts. It does not authorize bulk backfill, OHLC adjustment, shares-outstanding reconstruction, alpha features/models, protected outcomes, Financial PIT changes, Foreign Flow changes, or AKSes credentials.

The previous exact-date equality diagnostic is not a final identity rule. V1 must rely on source-internal event identifiers/fields, event-family semantics, official KSEI schedule-document evidence, and official IDX announcement/attachment evidence, with ambiguity failing closed.
