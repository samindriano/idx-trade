# Full-Market 43-Session Certification — PASS

Date: 2026-08-08
Branch: `data/idx-data-002c`
Certified runtime code commit: `bef9bde1a7e539a0d1376da421dd0ba364215c63`
Window: `2026-06-02 -> 2026-07-31`
Official IDX exchange sessions: 43

## Result

The bounded full-market common-stock DATA GATE passed completely.

- pytest: **132 passed, 0 failed**
- securities discovered before security-type scope: **964**
- authoritative scope exclusion: `CNTX` — `NON_COMMON_SHARE / Saham Preference`
- required common-stock securities: **963**
- passed: **963**
- failed: **0**
- unresolved identities: **0**
- UNKNOWN required sessions: **0**
- missing ACTIVE-session Yahoo prices: **0**
- quarantined non-ACTIVE provider bars: **1,359**
- blocker histogram: `{}`

## CNTB / CNTX final bounded-window treatment

### CNTB

- common share;
- listing identity `listed_from = 2000-12-22`;
- official IDX legal evidence suspends CNTB in all markets from 2024-08-07;
- later 2025 opening was Negotiated-Market-only for crossing and did not open the Regular Market;
- therefore `2026-07-30` and `2026-07-31` resolve as `REGULAR = SUSPENDED`, not UNKNOWN and not inferred NO_TRADE.

### CNTX

- KSEI security type: `Saham Preference`;
- retained in source/evidence discovery;
- explicitly excluded from the common-stock research scope as `NON_COMMON_SHARE`;
- not removed by ticker hardcode.

## Certified model-safe panel

Runtime path at certification:

`D:/Documents/Project/idx-trade-data-gate-20260808p/certification/model_safe_price_panel.parquet`

SHA-256:

`ac923c22dfc3d85b1769419bc00d02136e4f9a96d7999ba466bc27a0579624b7`

This panel is restricted to in-scope common-stock rows whose official point-in-time Regular-Market state is ACTIVE.

## Certified snapshot manifest

Runtime path at certification:

`D:/Documents/Project/idx-trade-data-gate-20260808p/certification/certified_snapshot_manifest.json`

SHA-256:

`6c639bf009553db64e1b80b5d570bd83436af57a6c9b9d2ae26d71521b255ffa`

Manifest verification: **valid=true**, **9/9 artifacts verified**.

## Decision

The 43-session full-market data architecture is certified and becomes the immutable bounded baseline for subsequent historical expansion.

This does **not** mean 43 sessions are sufficient for model training. Historical expansion must now proceed incrementally while preserving the same ontology, source authority, security scope, and fail-closed gate.

Next checkpoint: **126 official sessions (~6 months)** ending on 2026-07-31.

Do not modify the 43-session certified artifacts in place. Historical expansion creates a new evidence/certification directory and, if it passes, a new versioned panel/manifest.

No modelling or `IDX-VAL-002` is authorized yet.
