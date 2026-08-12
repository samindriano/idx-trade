# Full-market 126-session certification — PASS

Date: 2026-08-08

Branch at runtime: `data/idx-data-002c`
Runtime commit: `f8427efa7e6181e0c0522d6dd4f9445ff48de3b8`

## Window

- official IDX sessions: **126**
- first session: **2026-01-15**
- last session: **2026-07-31**

This is a certified historical-expansion checkpoint. It extends, but does not replace, the previously certified 43-session baseline.

## Runtime validation

- pytest: **133 passed**, exit 0
- non-blocking warnings: 2

## PIT universe and scope

- officially discovered before scope: **964 securities**
- required in-scope common stocks: **963**
- `CNTX`: retained as authoritative `NON_COMMON_SHARE / Saham Preference` scope exclusion
- `CNTB`: retained as an in-scope common share with resolved identity/tradability evidence

## Official Stock Summary execution evidence

- sessions complete: **126/126**
- ACTIVE anchors: **107,424**
- NO_TRADE anchors: **13,335**
- unresolved metric rows: **0**

## Yahoo/provider extension

- additional UPDATED tickers: **874**
- NO_PROVIDER_ROWS: **0**
- DOWNLOAD_ERROR: **0**
- REVISION_CONFLICT: **0**

## DATA GATE results

Regression horizon:

- 43 sessions: **963/963 PASS**

Expanded horizon:

- 126 sessions: **963/963 PASS**
- UNKNOWN sessions: **0**
- missing expected ACTIVE prices: **0**
- quarantined non-ACTIVE provider bars: **2,672**
- blocker histogram: `{}`

The 43-session baseline reproducing PASS is important evidence that the historical extension did not regress the already-certified recent window.

## Model-safe dataset

ACTIVE-only model-safe panel:

- rows: **107,424**
- tickers represented: **880**
- SHA-256: `401d2bdb65beaf9442f1a54212372e2adc5d1b2c006fc1e759738f6deea8a19a`

Certified snapshot manifest:

- verification: **valid=true**
- artifacts verified: **14/14**
- SHA-256: `650ab19e5a77085b7987ffaaa0ed7cbee0eb8c478a72c0c1166767e9eec68f5b`

## Phase decision

126 sessions PASS cleanly across the complete in-scope PIT common-stock universe. The project therefore no longer needs to certify every intermediate horizon sequentially.

Primary historical checkpoints are now adaptive:

`43 -> 126 -> 504 -> 1260 sessions`

where:

- 504 sessions ~= 2 trading years (`2 x 252`);
- 1260 sessions ~= 5 trading years (`5 x 252`).

Intermediate 252- and 756-session horizons are diagnostic fallbacks only. If a large jump fails, use an intermediate horizon to localise the first historical evidence boundary before changing semantics or sources.

## Next action

Attempt **504 official IDX sessions** ending on 2026-07-31.

Preserve the certified 43- and 126-session artifacts unchanged. Extend calendar, official Stock Summary evidence, PIT identity/scope reconciliation, Yahoo raw price evidence, legal tradability evidence, and authoritative split/reverse-split verification into a new 504-session workspace.

Run at least the 126- and 504-session DATA GATE horizons. If 504 PASS, freeze a new 504-session model-safe panel and certified manifest, then jump directly to 1260 sessions. If 504 FAIL, stop and use 252 sessions only if necessary to localise the failure boundary.

Do not begin modelling, `IDX-VAL-002`, or merge to `main` from this checkpoint.
