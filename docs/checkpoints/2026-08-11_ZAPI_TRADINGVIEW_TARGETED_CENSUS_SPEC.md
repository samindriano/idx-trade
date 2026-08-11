# Zapi TradingView Targeted Residual Census — Frozen Spec

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-tradingview-targeted-census-v1`
Base: `dda3cb1ca7ed455e1cb932c093639723e4d3ea82`

## Decision

`TRADINGVIEW_NON_CA_RESIDUAL_CENSUS_AUTHORIZED_NO_PANEL_WRITE`

The completed Pro-resume audit is accepted as sufficient evidence to census the remaining non-corporate-action Open residuals using the unchanged Zapi TradingView chart contract. This experiment is evidence collection only. It does not authorize panel backfill or execution-grade promotion.

## Accepted evidence from frozen 240-row audit

Combined original + Pro resume:

- 206 frozen sample tickers
- 201 TradingView SUCCESS, 5 REQUEST_ERROR
- 156/240 exact ticker/date coverage
- 117/240 exact certified H/L/C
- 32/40 known controls exact certified H/L/C
- 33/40 known-control Open exact (diagnostic only; H/L/C gate still mandatory)
- 85/200 missing-Open recovery candidates
  - 35/120 `RESIDUAL_HLC_MISMATCH`
  - 50/80 `RESIDUAL_PROVIDER_GAP`
- 67 `HISTORY_WINDOW_UNAVAILABLE`
- 39 `TV_HLC_DISAGREEMENT`
- 5 final provider/symbol error tickers: `FREN`, `MASA`, `MFIN`, `RMBA`, `TURI`
- immutable panel SHA remained `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Within the sampled missing-Open rows, every row that reached exact certified H/L/C under TradingView became an admissible positive in-range Open candidate (85 recovery candidates = all exact-HLC missing rows in the combined sample). This justifies a wider census while preserving the fail-closed gate.

## Census target

Start from the existing official Yahoo residual census of 49,476 rows, but keep corporate-action residuals separate.

Authorized row classes:

- `PROVIDER_HLC_MISMATCH_NO_VERIFIED_SPLIT_FACTOR`: 32,103 rows
- `NO_PROVIDER_ROW`: 3,840 rows
- `PROVIDER_ERROR_OR_SYMBOL_RESOLUTION_FAILURE`: 2,876 rows

Total authorized non-CA census target: **38,819 residual rows**.

Excluded from this experiment:

- `CORPORATE_ACTION_ADJACENT_INCOMPLETE_OFFICIAL_EVIDENCE`: 8,804 rows
- `CORPORATE_ACTION_SCALE_MISMATCH_VERIFIED_FACTOR_FAILED`: 1,853 rows

Total excluded corporate-action rows: **10,657**.

Do not silently reclassify or include excluded CA rows.

## Reuse-first network policy

Before any new TradingView request:

1. Load the exact existing 49,476-row residual detail and verify its expected provenance/hash if already frozen in prior checkpoints/artifacts.
2. Filter to the exact 38,819 authorized non-CA rows.
3. Load and verify the preserved combined TradingView artifacts from the completed sample/resume audit, including manifest SHA `68adea6bd6cf2b251b43e010133d8a3899c7d3ff8af8566f4bd9b88f0f9f3134` and prior source artifacts.
4. Score every authorized residual row that can be resolved from already-preserved TradingView ticker/date rows **offline first**.
5. Do not refetch any ticker whose required TradingView chart history is already preserved and usable.
6. Build the network fetch set only from unique residual tickers still lacking any preserved usable TradingView chart response.

The 5 known TradingView 404 tickers (`FREN`, `MASA`, `MFIN`, `RMBA`, `TURI`) must not be retried under the unchanged symbol contract. Preserve them as provider/symbol unresolved unless a separately authorized symbol-resolution experiment is created later.

## TradingView request contract

For each newly required unique ticker, use exactly:

- endpoint: existing Zapi TradingView chart endpoint
- `symbol=IDX:<ticker>`
- `market=indonesia`
- `resolution=1D`
- `count=1000`

At most one initial request per new ticker, with only bounded transient retry behavior already implemented/tested. Do not add pagination, historical anchors, alternate symbol mappings, request-shape experimentation, or another upstream provider in this experiment.

Because `count=1000` imposes a bounded historical window, if an authorized residual date is older than the returned chart history, classify it as `HISTORY_WINDOW_UNAVAILABLE`. Do not synthesize or infer a row.

## Admission contract

For an exact authorized residual ticker/date, a TradingView Open may be classified as a recovery candidate only when:

1. exact requested IDX ticker identity is preserved;
2. exact session date exists in provider history;
3. raw TradingView High == certified panel High;
4. raw TradingView Low == certified panel Low;
5. raw TradingView Close == certified panel Close;
6. raw TradingView Open is finite and > 0;
7. certified Low <= raw TradingView Open <= certified High;
8. existing non-null panel Open is never overwritten;
9. no split/scale inference is used;
10. no adjusted price, previous Close, averaging/voting, interpolation, forward fill, or synthetic Open is used.

The exact H/L/C gate must remain unchanged. A TradingView row that supports Yahoo rather than the certified panel is not admissible.

## Artifact policy

Preserve all new raw TradingView responses outside Git in a new immutable artifact root. Preserve provenance at minimum for:

- original TradingView audit rows
- Pro-resume TradingView rows
- new targeted-census rows

Create a combined deduplicated TradingView cache keyed by ticker/date/provider contract, but do not overwrite the prior immutable artifact roots.

No API key may be printed, committed, or persisted in artifacts.

## Required report

Report both reuse/offline and new-network portions, then the final 38,819-row census:

- exact residual-detail input hash/provenance
- exact authorized row count and excluded CA count
- number of unique authorized residual tickers
- number of tickers fully/partially covered from preserved TradingView cache before network
- number of prior successful tickers refetched (must be 0)
- new unique tickers requested
- requests, retries, 429s, provider errors
- quota before/after
- provider rows newly returned and combined deduplicated rows
- exact ticker/date coverage over 38,819
- exact H/L/C count/rate
- admissible Open recovery candidates count/rate
- recovery by original residual class
- recovery by calendar year
- recovery by ticker concentration (top 20 and cumulative top 10/50/100)
- `HISTORY_WINDOW_UNAVAILABLE` count/rate
- H/L/C disagreement count/rate
- provider/symbol error count and tickers
- Yahoo arbitration counts where applicable
- residual rows still unresolved after TradingView evidence, broken down by reason/class/year
- immutable panel SHA before/after
- artifact hashes and manifest SHA
- focused and full pytest results

Also calculate the hypothetical remaining non-CA Open residual count **if** all admissible candidates were later approved, but label it counterfactual only. Do not write those values into the derivative panel in this experiment.

## Stop gate

After the census, STOP for independent ChatGPT review.

Explicitly not authorized:

- writing/backfilling the derivative or immutable panel
- execution-grade promotion
- corporate-action repair
- alternate TradingView symbol resolution
- Investing calls
- `finance:idx/stock-history` Open recovery
- another provider census
- PIT-sector work
- model/alpha changes
- execution PnL or downstream decision work
