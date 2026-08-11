# Yahoo Full-Universe Open Census — Independent Review

Date: 2026-08-11 (Asia/Jakarta)
Reviewed branch: `data/idx-open-backfill-yahoo-census-v1`
Reviewed runtime documentation commit: `12a84e50597557ded2f5c3a6c0d5645d7a308e2b`
Runtime code HEAD used by census: `c338fe8fafd711eb40dee211897d0ee79842d990`

## Decision

**`YAHOO_FULL_UNIVERSE_CENSUS_ACCEPTED_RESIDUAL_DIAGNOSTIC_AUTHORIZED`**

The full-universe Yahoo historical Open census is accepted as valid recovery evidence under the frozen raw-price and official-factor contract.

The derivative remains a candidate execution-data artifact only. This review does **not** promote execution grade, does not authorize execution-PnL claims, and does not authorize downstream model changes, Stage-5 reruns, paper/live trading, broker integration, or merge to `main`.

The next authorized Open-track work is a **bounded residual diagnostic using the already-produced census artifacts**. Do not add a new provider yet and do not relax the admission contract.

## Evidence accepted

Input immutability and runtime discipline were preserved:

- panel: `981,940` rows / `945` tickers;
- immutable panel SHA before/after unchanged: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- existing non-null Open changed: `0`;
- original panel columns/order preserved in the derivative;
- unresolved rows remain null;
- Yahoo raw OHLC used with `auto_adjust=False`;
- no additional provider was introduced;
- no factor was inferred from Yahoo/panel ratios;
- no Adj Close, dividend adjustment, previous Close, interpolation, forward fill, averaging, or synthetic Open was used;
- runtime documentation reports `236 passed, 3 warnings` before execution and no source/test change or runtime bug fix;
- runtime commit added documentation only.

Provider and known-answer evidence is strong enough to accept Yahoo as the primary recovery source:

- Yahoo success: `940 / 945` tickers;
- exact ticker/date coverage: `975,069 / 981,940 = 99.3003%`;
- known-Open rows with provider evidence: `534,942`;
- exact H/L/C known-answer agreement: `526,756 / 534,942 = 98.4697%`;
- exact raw Open after the H/L/C gate: `526,656 / 526,756 = 99.9810%`;
- direct accepted missing-Open fills: `386,157`;
- verified official split-scale fills: `11,210`;
- total fills: `397,367`;
- initial unresolved Open: `446,843`;
- final unresolved Open: `49,476`;
- gap closure: `88.9277%`;
- `execution_grade_promoted=false`.

Accepted artifact hashes:

- derivative: `d8d3463362a8c43bdb9e8d3aaba5e66ceffe86803b76979d18e3e2e71a276ea4`;
- provenance: `1c11b832c9a8b049202547e8b76c1a4972e9177afefd9a02deb3ca49795bb17d`;
- raw-cache manifest: `08f37a4100e911049a3535357959e43df94c748cdd7bc8cb525a84d870b3b0f6`;
- artifact manifest: `b6e47c98ac256cb07ac0441be41f599ba21481a5340c6b306b5f3301e207da2f`.

## Interpretation of the residual

The remaining problem is materially smaller and is no longer primarily a generic provider-availability problem.

Residual diagnostics sum exactly to the final `49,476` unresolved rows:

- `HLC_MISMATCH_HIGH`: `42,200` (`85.2939%` of residual);
- `NO_PROVIDER_ROW`: `6,716` (`13.5743%`);
- `HLC_MISMATCH_LOW`: `346` (`0.6993%`);
- `HLC_MISMATCH_CLOSE`: `214` (`0.4325%`).

Only five tickers ended in provider error (`FREN`, `MASA`, `MFIN`, `RMBA`, `TURI`), while Yahoo succeeded for `940/945` tickers. Therefore the next decision should not be framed as "find another source for 49,476 rows". The dominant question is why the remaining Yahoo rows fail certified H/L/C equality, especially the `HIGH` mismatch class.

The residual also has strong temporal concentration:

| year | initial missing Open | accepted | unresolved | unresolved rate within that year's missing set |
|---|---:|---:|---:|---:|
| 2021 | 17,931 | 3,238 | 14,693 | 81.94% |
| 2022 | 42,649 | 26,359 | 16,290 | 38.20% |
| 2023 | 173,743 | 162,708 | 11,035 | 6.35% |
| 2024 | 177,829 | 170,999 | 6,830 | 3.84% |
| 2025 | 34,691 | 34,063 | 628 | 1.81% |

This is strong evidence of historical-era degradation rather than a uniform full-window failure. It does not by itself authorize shortening the execution window, but it makes window/universe feasibility analysis a valid downstream diagnostic after the residual causes are understood.

The final residual is `49,476 / 981,940 = 5.04%` of all ACTIVE panel rows and `11.07%` of the original missing-Open set.

## Authorized next bounded work

Perform a **residual diagnostic only**, preferably from existing census cache/provenance/row-audit artifacts without new network retrieval unless required solely to read already-cached evidence.

Required outputs:

1. exact residual counts by ticker, year, diagnostic, listing/delisting state, and available tradability/eligibility state;
2. concentration statistics: top tickers responsible for residual rows and cumulative shares;
3. isolate all `6,716 NO_PROVIDER_ROW` rows and distinguish:
   - the five provider-error tickers;
   - ticker/date rows outside returned Yahoo history;
   - identity/rename/delisting/history-edge cases;
4. diagnose the `42,200 HLC_MISMATCH_HIGH` rows without fitting or inferring a correction factor from Yahoo/panel ratios;
5. cross-reference residual mismatch rows against already-authoritative split/reverse-split evidence and identify which mismatches have no authorized corporate-action explanation;
6. report whether residuals fall inside or outside the actual point-in-time model/tradable universe and liquidity eligibility, but do not drop rows merely to improve coverage;
7. compute descriptive candidate coverage by possible research start year/window (for example 2022, 2023, 2024 starts) and by eligible universe, explicitly labelled **feasibility diagnostics only**, not certification;
8. produce a decision table separating:
   - `SOURCE_2_WORTH_TESTING`;
   - `IDENTITY_OR_HISTORY_RESEARCH_REQUIRED`;
   - `CORPORATE_ACTION_EVIDENCE_REQUIRED`;
   - `UNRESOLVED_FAIL_CLOSED`;
   - rows that are outside a future execution-eligible universe but remain preserved in the historical store.

## Not authorized yet

- do not query Zapi, TradingView, Investing.com, another Yahoo endpoint, or another provider;
- do not scrape/crawl IDX;
- do not average or vote sources;
- do not infer split factors from observed price ratios;
- do not overwrite the immutable panel;
- do not promote the Yahoo derivative to execution grade;
- do not claim a shortened execution window is certified solely because newer years have better coverage;
- do not run execution-PnL, Stage 5, Ranking V1/V2, Probability, paper/live trading, or broker integration;
- do not merge to `main`.

## Stop boundary

After the residual diagnostic is complete, STOP for another independent review. Only then decide whether a targeted second-source audit is justified and for which exact residual class/subset, or whether a narrower execution-grade universe/window should be formally gated.
