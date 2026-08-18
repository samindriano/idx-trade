# V4 CA Targeted Schedule Linkage Remediation V4 — Prepared

Date: 2026-08-18
Branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`
Status: `OFFLINE_V4_REMEDIATION_PREPARED_LOCAL_RUNTIME_REQUIRED`

## Accepted V3 result

V3 geometry remediation completed outcome-blind and offline with manifest:

`1aee0285c74b47f12da76e1a4d7fccb6b8409a9c87e6d959ee9c9ea73d3c8dfe`

Result:

- NISP remains exact static non-blocking;
- PANI is now exact schedule transition at `2025-12-09` with `REGULAR_MARKET_EX_DATE`;
- CUAN, ISAT, PTRO, RAJA remain unresolved despite diagnostics showing the exact new-basis date on the semantic line while `Pasar Reguler ...` wraps to the next line;
- ADRO remains unresolved;
- provider calls in V3 remediation: zero.

V3 also demonstrated why reparsed Record/Distribution fields must not be used blindly for stock-split linkage: their layout association can shift. Those reparsed fields are not admitted by V4.

## V4 hypothesis

The four stock-split PDFs preserve the transition semantic as two adjacent extracted line fragments:

1. the line containing `Mulai perdagangan saham dengan Nilai Nominal Baru` and one explicit date;
2. the immediately following line completing `Pasar Reguler dan Pasar Negosiasi`.

V4 therefore performs a narrow two-line row repair. It does not reorder detached dates and does not infer a transition from Record/Distribution or price behavior.

## Event-document linkage gate

The two-line transition is admitted only if:

1. V3 recorded exactly one candidate document for that event;
2. exact ticker identity is preserved;
3. parsed family is `STOCK_SPLIT`;
4. the same official PDF explicitly contains **every frozen source date** for the selected event;
5. the two-line transition row contains exactly one date;
6. that transition date is an official exchange session;
7. KSEI reference and exact source SHA-256 remain present.

This permits transition dates that are not themselves in `source_dates` while still requiring deterministic event-document identity from the complete frozen source-date fingerprint.

## Implementation

Added:

- `src/idx_trade/v4_ca_targeted_schedule_linkage_remediation.py`
- `scripts/run_v4_ca_targeted_schedule_linkage_remediation.py`
- `tests/test_v4_ca_targeted_schedule_linkage_remediation.py`

Pinned roots:

- original acquisition manifest: `df1455b80c4b5d76d8bde0c23ac992db81fc93373a9a40af18ca29583b94b79b`;
- V3 remediation manifest: `1aee0285c74b47f12da76e1a4d7fccb6b8409a9c87e6d959ee9c9ea73d3c8dfe`.

Scientific firewall remains unchanged: no provider calls, no price inference, no source substitution, no target/rank/model/prediction/performance/protected-forward access.

## Next local step

Run focused tests and the V4 runner against the exact V3 output plus the original acquisition root. Audit the resulting four stock-split transitions and full frozen source-date containment before any continuity replay.
