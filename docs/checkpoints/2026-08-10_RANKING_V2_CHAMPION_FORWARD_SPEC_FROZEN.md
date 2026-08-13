# Ranking V2 Champion Forward Spec Frozen

Date: 2026-08-10 (Asia/Jakarta)

## Decision

`HGB_XS_MARKET` is frozen as the sole historical-development champion for the
next separately authorized final-refit and fresh-forward phase. The complete
contract is in:

`docs/RANKING_V2_CHAMPION_FORWARD_SPEC_V1.md`

This checkpoint records a specification freeze only. No final model was fit,
no fresh-forward label or outcome after 2026-07-31 was read, and no fresh-
forward result was inspected.

## Frozen lineage

- branch at freeze: `research/idx-ranking-v2-spec-v1`;
- source HEAD at freeze: `a41f13f29f5186e126b78845311b9b2d0a839256`;
- substantive V2 code commit: `5f2ed2f53aececfd7c338d3f9f65db1efae372b6`;
- prepared-cache SHA-256: `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- prepared-cache manifest SHA-256: `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- historical integration summary SHA-256: `3facb4468caafab8cf19f368cf5ef04f36dac052089d2ecb810b683c851ec705`;
- final-refit eligible rows: `292633`;
- final-refit eligible tickers: `737`;
- final-refit signal-session boundary: `20..1250`.

## Frozen forward controls

- one final fit over the exact resolved primary H10 cache rows;
- the exact 25-feature order and existing HGB parameters;
- causal primary-liquid universe and same-date market context;
- only signals with complete official H10 maturity are observed;
- first verdict only after 100 consecutive mature official forward signal
  sessions;
- one-shot evaluation with fixed PASS/MIXED/FAIL rules;
- global `FORWARD_OUTCOME_ACCESS_STARTED` marker before outcome reads;
- immutable, hashed input snapshots and manifests;
- no calibration, threshold search, candidate reopening, adaptive rescue, or
  probability claim.

The runtime optimization note was read. The future implementation must first
profile post-cache stages, use bounded deterministic scheduling, and prove
semantic equivalence before any fresh outcome access.

## Result and next action

The phase is complete and ready for independent ChatGPT review. The exact
next action is to obtain explicit authorization before implementing or running
the final-refit/fresh-forward runtime. Stage 6, `IDX-VAL-002`, trading, and
merge to `main` remain unauthorized.
