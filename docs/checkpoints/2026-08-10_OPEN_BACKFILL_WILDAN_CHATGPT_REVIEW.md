# Open Backfill Tier-1 — Independent ChatGPT Review

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-v1`
Reviewed runtime commit: `ea8d9eb368c544317a82787ee29ec5981532d246`

## Decision

**`TIER1_WILDAN_REJECTED_AS_MISSING_OPEN_RECOVERY_SOURCE`**

The Tier-1 runtime is accepted as a valid fail-closed experiment. Its zero-fill result is not an implementation failure and must not be rescued by weakening the admission contract.

Frozen factual result:

- immutable panel SHA-256 remained `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- initial null Open rows: 446,843;
- candidate target rows with a Wildan secondary row: 424,556;
- accepted fills: 0;
- final null Open rows: 446,843;
- execution-grade promotion remains false;
- known-existing-Open overlap H/L/C exact rate: 100.0000000000%;
- known-existing-Open exact Open rate: 22.9210679347%;
- all target candidate rows failed as `SECONDARY_OHLC_INVALID`; 22,287 target rows had no secondary row.

## Interpretation

The 100% H/L/C agreement on 271,702 known-overlap rows shows that the Wildan archive is highly consistent with the certified panel for H/L/C and is therefore useful as lineage/cross-check evidence.

However, it does not provide usable independent Open evidence for the rows where Open is missing. Under the current validator, `SECONDARY_OHLC_INVALID` means at least one secondary OHLC value is missing or non-positive before cross-source H/L/C comparison. Because every one of the 424,556 missing-Open candidate rows failed at that gate, Wildan cannot close the historical Open gap under the execution-safe contract.

The most likely explanation is that the archive shares the same upstream opening-price absence/zero convention on these target rows, but the runtime artifacts have not yet separately decomposed `SECONDARY_OHLC_INVALID` by field. Therefore that causal/source-lineage explanation remains a hypothesis, not a measured fact. A later diagnostic may split invalidity into Open vs H/L/C components, but such a diagnostic is not required to reject Wildan as a recovery source.

The 22.9211% exact-Open agreement on rows where the certified panel already has Open is also insufficient to justify using non-matching Wildan Open values. Do not average, substitute, infer, or loosen exact admission criteria to improve coverage after seeing this result.

## Authorized next scope

Tier 1 is complete. The next allowed data-quality work is a **bounded Tier-2 source audit**, not immediate bulk ingestion.

Priority order:

1. test Zapi IDX historical `stock-summary` / equivalent documented endpoint on a small adversarial sample, including rows with known Open and rows currently missing Open;
2. test Yahoo/yfinance raw `.JK` daily OHLC as an independent fallback/witness using the same known-answer and H/L/C cross-validation framework;
3. only a source that demonstrates acceptable known-answer agreement and usable missing-Open coverage may be implemented for bulk Tier-2 backfill;
4. disagreements remain unresolved; existing certified Open remains immutable;
5. historical source work remains separate from Ranking V2 and from the forward-archive scheduler track.

No direct IDX scraping/crawling, execution-PnL claim, Stage-5 rerun, paper/live trading, or main merge is authorized.

## Research consequence

Signal-research HLCV remains valid for Ranking V2 because Open is not part of the current signal feature/label contract. Strict execution-grade 1260 OHLCV remains blocked by historical Open evidence until a later source closes the gap and passes a separate certification review.
