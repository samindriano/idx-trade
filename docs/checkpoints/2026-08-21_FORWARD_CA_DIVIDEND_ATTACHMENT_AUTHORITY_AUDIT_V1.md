# Forward CA — Dividend Attachment Authority Audit V1

Date: 2026-08-21
Branch: `integration/forward-ca-attestation-v1`

## Evidence already established

The direct official IDX `/ListedCompany/GetAnnouncement` V2 capture returned HTTP 200 and exactly one BBCA announcement in the bounded 2026-08-18 through 2026-08-21 window:

- announcement ID: `20260819183103-005/CSG-IVR/2026_id-id`;
- announcement number: `005/CSG-IVR/2026`;
- announcement timestamp: `2026-08-19T18:31:03`;
- title: `Jadwal Dividen Tunai Interim`;
- form ID: `11000`;
- source raw SHA-256: `6e8ced1891addecdb9a1029d064c75d072ebcbeb4319ad633d30e43fac004473`.

Offline inspection identified three official IDX PDF attachment URLs on that exact announcement. This resolves the earlier announcement false negative: the V2 reviewer date regex failed on ISO datetimes containing `T`; the source itself was valid.

The current `LINK_DIVIDEND` August query returned zero BBCA rows. It is therefore not admitted as a real-time/forward authority for this event. It remains useful as lagging structured corroboration/history.

## Authority hypothesis

Forward/current cash-dividend authority should be:

`official IDX announcement metadata + immutable hashed official IDX attachment bytes`.

`LINK_DIVIDEND` is secondary corroboration only. Zapi company-profile remains optional parity only.

## Bounded live capture

Using only the attachment URLs already present in the frozen announcement raw artifact, capture each PDF exactly once with direct `curl_cffi` browser impersonation. No retry helper is used. No new announcement, LINK_DIVIDEND, Zapi, model, outcome, or paper-state request is authorized by this audit.

Expected attachment URLs are not hard-coded into the reviewer; lineage is anchored to the exact announcement raw SHA above, and each downloaded PDF is persisted externally and SHA-256 hashed.

## Semantic PASS gate

The combined extracted official PDF text must establish all of:

- issuer/ticker BBCA / Bank Central Asia;
- `Jadwal Dividen Tunai Interim` or equivalent dividend-interim subject;
- dividend per share IDR 25;
- cum dividend Regular/Negotiated: 28 August 2026;
- ex dividend Regular/Negotiated: 31 August 2026;
- recording date: 1 September 2026;
- payment date: 16 September 2026.

PASS status:

`PASS_DIRECT_IDX_ANNOUNCEMENT_ATTACHMENT_TERMS_ELIGIBLE_FOR_V1_1`

A PASS admits the source contract for Forward CA V1.1 dividend certification. It does not by itself mutate paper state or alter V4-X1 alpha.

## Next implementation after PASS

1. freeze announcement + attachment evidence contract;
2. implement normalized certified cash-dividend event identity;
3. entitlement snapshot at EOD cum-date after same-session execution;
4. create gross dividend receivable on ex-date;
5. include receivable in NAV but not spendable cash;
6. settle receivable to cash on payment date without second PnL recognition;
7. preserve revision/correction lineage and fail closed on conflicting official documents;
8. prospectively archive publication timestamp and terms for future successor alpha research only.

## Boundaries

- V4-X1 model, features, ranks, and frozen scientific identity remain unchanged;
- no historical performance rerun;
- no dividend alpha overlay authorization;
- no historical bulk backfill;
- no paper mutation until the Dividend Engine implementation and tests are separately admitted.
