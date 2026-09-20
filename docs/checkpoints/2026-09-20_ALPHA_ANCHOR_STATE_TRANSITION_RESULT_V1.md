# Anchor ACTIVE/NO_TRADE Transition Audit V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STATE_GEOMETRY / LIFECYCLE_UNKNOWN / NO ADMISSION`

## Result

Across 980 anchor tickers, 583 switch between `ACTIVE` and `NO_TRADE` at least
once. Among tickers with a state sequence spanning the full 1,260-session
surface:

| State-change measure | Result |
|---|---:|
| Median transitions among changed tickers | 10 |
| 95th percentile transitions | 212.9 |
| Maximum transitions for one ticker | 374 |
| Maximum ACTIVE blocks | 187 |
| Maximum NO_TRADE blocks | 188 |
| Tickers with more than 100 transitions | 91 |

First/last state profiles are `799 ACTIVE→ACTIVE`, `99 ACTIVE→NO_TRADE`,
`31 NO_TRADE→ACTIVE`, and `51 NO_TRADE→NO_TRADE`.

## Interpretation boundary

Repeated state changes are real observed state geometry, but they do not prove
that a transition is a suspension, delisting, relisting, ticker reuse, issuer
change, or any other lifecycle event. The sequence is too oscillatory to be
treated as a clean lifecycle interval without an explicit state definition,
publication/knowledge time, issuer/ISIN continuity, and overlap policy.

This strengthens the existing `UNKNOWN_NO_TRADE_NOT_EQ_SUSPENSION` and identity
boundaries. It does not authorize converting `NO_TRADE` into a suspension
feature, inferring delistings/relistings, or declaring survivorship safety.

## Reproducibility

- Script: `research/alpha_anchor_state_transition_audit_v1.py`
- Test: `tests/test_alpha_anchor_state_transition_audit_v1.py`
- Durable result: `research_knowledge/anchor_state_transition_audit_v1.json`
- Anchor input SHA-256: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`
- Code SHA-256: `1b7b0a6e2d0f1dcddd914665c1e3eedc7b7ff737c228c8510e75199b7d7cee5f`
- Isolated external result SHA-256: `fa22bc9f2b5c9d81d46e018b5685827c054da6bfec9d2fcb86c7e05fbf0bf612`

No provider, cloud/R2, canonical, capture, telemetry, scheduler, production,
incumbent, or protected outcome state was accessed or changed.
