# Canonical EOD Calendar-Parent Runtime Attestation + Price State Smoke

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/canonical-eod-calendar-parent-attestation-v1`

Authorization: `review/idx-price-trend-runtime-smoke-blocker-v1@fa280cf9d9d618973b0b5292daf5cf64874b60a7`

## Sequence

The read-only preflight was rerun first for canonical EOD sessions 2026-08-11
and 2026-08-12. Both retained their previous manifest/snapshot/evidence hashes
and session semantics. Only 2026-08-11 had the unrecovered capture-time
calendar-parent edge; 2026-08-12 retained its direct parent. No canonical
session was rewritten or recaptured.

Exactly one runtime attestation was then created for 2026-08-11 at:

`forward_monitoring/provenance_attestations/canonical_eod_calendar_parent_v1/2026-08-11/attestation.json`

Attestation SHA-256:
`03e41ddc1fb1f0d83ecceb540eca36bee43d8b25f35107c3fb0887fcaf4ea3bc`

Strict verification passed on the first write. A second create/verify replay
returned the same path and identical SHA, proving idempotency. No attestation
was created for 2026-08-12.

## Controlled smoke result

The single zero-provider command used the existing Price State runtime path
for source session 2026-08-12 and feature session 2026-08-13.

Status: `PRICE_TREND_CONTROLLED_SMOKE_VERIFIED`

- rows/tickers: `836 / 836`
- Price State artifact SHA-256:
  `8dab4a1d532c42cb46f9a9b86c5f853f99f00e13677222c7ae1e1ab0ca1901af`
- manifest SHA-256:
  `aad51b933ba8a8868c050e17fec52330a3b6c66002ba29d0ddd4ba84949cbd6f`
- Price State context-anchor attestation SHA-256:
  `ec8783b231eabecb0c61d89413b5f0a9216355949815744fa9bec40bf03cd312`
- canonical 2026-08-11 calendar-parent attestation SHA-256:
  `03e41ddc1fb1f0d83ecceb540eca36bee43d8b25f35107c3fb0887fcaf4ea3bc`
- strict bridge verification: `true`
- idempotent replay: `true`
- provider calls: `0`
- outcome-blind: `true`
- outcomes/labels accessed: `false`
- model fit/scoring: `false`
- trade recommendation: `false`

## Runtime context

- historical calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- bridge calendar SHA-256:
  `51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`
- combined session-set SHA-256:
  `dd51d3dbcb29915ff80612d84a912da237331e979ee3847bd8fd4984ead413dd`
- combined session count: `1269`
- source kinds/order:
  `BRIDGE_ONLY × 6 → CANONICAL_EOD × 2`
- extension sessions: 2026-08-03 through 2026-08-12, official-session order
- optional separate Foreign Flow context attestation: not used; existing
  bridge flow files were only provenance-validated context dependencies and no
  Foreign Flow + Price State feature/model combination was performed.

State distributions for the 836 rows:

| Axis | Distribution |
|---|---|
| confirmation | BREAKOUT_CONFIRMED 22; BREAKOUT_WEAK_VOLUME 12; FAILED_BREAKOUT_RECENT 52; INDETERMINATE 17; NEAR_BREAKOUT 114; NO_BREAKOUT 619 |
| long-term | ABOVE_RISING_MA200 164; BELOW_FALLING_MA200 475; INDETERMINATE 17; MIXED 175; UNAVAILABLE 5 |
| MA structure | BEARISH_STACK 65; BULLISH_STACK 251; INDETERMINATE 17; MIXED 192; RECOVERING 233; WEAKENING 78 |
| swing | HIGHER_LOW_HIGHER_HIGH 323; HIGHER_LOW_ONLY 243; INDETERMINATE 17; LOWER_LOW_LOWER_HIGH 100; LOWER_LOW_ONLY 62; MIXED 91 |
| trend | BASING 147; DOWNTREND 65; EARLY_REVERSAL 200; INDETERMINATE 17; TRANSITION 156; UPTREND 251 |
| volatility | CONTRACTING 268; EXPANDING 158; INDETERMINATE 17; NORMAL 393 |
| volume | CONTRACTING 273; EXPANDING 242; INDETERMINATE 17; NORMAL 304 |

## Validation

- focused tests: `15 passed`;
- full pytest: `86 passed, 1 failed` out of `87` collected; the only failure
  is the known unrelated storage conflict-count expectation;
- `git diff --check`: passed;
- no scheduler/counter/O2/HSC/free-float changes;
- no WATCH/READY/ENTRY_ELIGIBLE or trading decision was produced.

This lane stops here for independent review. No second smoke, recapture,
provider call, or downstream integration is authorized.
