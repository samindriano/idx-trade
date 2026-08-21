# Forward CA — Dividend Attachment Amount Parser Remediation

Date: 2026-08-21
Branch: `integration/forward-ca-attestation-v1`

## Trigger

The bounded direct-IDX attachment audit successfully downloaded and hash-pinned all three PDFs from the BBCA announcement `005/CSG-IVR/2026` (`Jadwal Dividen Tunai Interim`). Offline PDF extraction found:

- BBCA / PT Bank Central Asia Tbk;
- interim cash dividend subject;
- `Rp25,00 per lembar saham` / `Rp25.00 per share`;
- regular/negotiated cum date 2026-08-28;
- regular/negotiated ex date 2026-08-31;
- record date 2026-09-01;
- payment date 2026-09-16.

All semantic gates passed except the amount parser.

## Root cause

`review_forward_ca_idx_dividend_attachments_v1.py` only recognized layouts where `dividen per saham` preceded an `IDR/Rp 25` token. The official PDF instead uses the common issuer form:

`dividen interim sebesar Rp25,00 per lembar saham`

and the English attachment uses:

`interim dividend ... Rp25.00 per share`.

This was a reviewer false negative, not a source-data failure.

## Remediation

The amount parser now:

- accepts `Rp` or `IDR`;
- accepts integer / comma-decimal / dot-decimal forms for an exact expected amount;
- accepts `per saham`, `per lembar saham`, `/ saham`, and `per share` layouts;
- preserves exact-amount semantics (e.g. an expected 25 does not match 30).

Regression tests cover Indonesian and English official-style sentences plus a wrong-amount rejection case.

## Runtime boundary

No new IDX request or attachment download is required. Re-review must use the already captured directory:

`D:\Documents\Project\idx-forward-ca-dividend-attachments-20260821-v1`

The existing attachment SHA-256 identities remain authoritative:

- `c3076472a8_e5ca870b61.pdf` → `4ee38c989b3ff09c5d721e6d56340d873e8183822eadd3c87cd8dbfa576e092c`
- `11548b9ab7_c9c532d0c5.pdf` → `1d8b37031c4a0c23baeb6d511e8270c3f2be160c9c40c3102c7faaffdf54b94b`
- `b127fba58f_9aa6c0c497.pdf` → `93ff2e663af91ac6d87ed29c6a192725f2b4b86b0fc0432610ff7bdaad0c1949`

No V4-X1 alpha/model identity, historical outcome, paper state, or execution state is changed by this remediation.

## Admission rule

If the offline re-review now returns:

`PASS_DIRECT_IDX_ANNOUNCEMENT_ATTACHMENT_TERMS_ELIGIBLE_FOR_V1_1`

then the source contract is considered sufficient to proceed with Forward Dividend Engine V1.1 using direct IDX announcement + hash-pinned official attachment as current/forward authority. `LINK_DIVIDEND` remains lagging corroboration/history and Zapi remains optional parity only.
