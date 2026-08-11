# Open Research-Grade Coverage Gate Runtime

Date: 2026-08-12 (Asia/Jakarta)
Branch: `data/idx-open-research-coverage-gate-v1`
Starting HEAD: `97b4075410cf80b01e9eb33b2883aece3475c0c5`
Implementation commit: pending
Decision: `CONDITIONAL_PASS_FOR_OHLCV_ALPHA_RESEARCH`

## Scope and controls

This run executed only the frozen Open research-grade coverage gate. It used
the exact V3-B Structure-Lite final-refit population from the preserved
`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` artifacts. It did not approximate the
universe from all panel rows.

No provider or network calls were made. No OHLCV model was trained or tuned,
no fresh-forward outcomes were accessed, no corporate-action repair was run,
and no Ranking/PIT-sector or execution work was started.

The immutable certified panel was read-only and unchanged:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

## Accepted SMBR overlay

The accepted external Yahoo+TradingView derivative was copied to a new
read-only overlay. Exactly one previously-null row was filled:

| ticker | date | Open | High | Low | Close | evidence |
|---|---|---:|---:|---:|---:|---|
| SMBR | 2023-03-14 | 388 | 388 | 372 | 372 | exact certified H/L/C + positive/in-range Open |

No existing non-null Open was overwritten. The SMBR row is outside the exact
V3-B final-refit population, so it changes global accounting but does not
change V3-B population coverage.

Global accounting after the overlay:

| Metric | Count |
|---|---:|
| Total rows | 981,940 |
| Known Open | 938,140 |
| Null Open | 43,800 |
| Open coverage | 95.5394423% |

## Exact V3-B population

The final-refit manifest was verified as architecture
`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`, status
`RANKING_V3_B_FINAL_REFIT_FROZEN`, with no fresh-forward access marker. The
frozen training table contains 292,633 resolved model rows, 737 tickers, and
signal session indices 20 through 1250; every row has
`universe_primary_liquid=True`.

| Metric | Result |
|---|---:|
| Exact V3-B final-refit rows | 292,633 |
| Tickers | 737 |
| Open known | 280,044 |
| Open missing | 12,589 |
| Open coverage | 95.6980245% |
| Rows lost if Open is required | 12,589 (4.3019755%) |
| All Open-feature-ready rows after lag/range checks | 278,168 |
| Rows lost if all Open features are required | 14,465 (4.9430505%) |
| All Open-feature-ready rate | 95.0569485% |

The exact frozen development partitions were also reconciled from preserved
V3-B prediction-row identities without using scores or outcomes:

| Fold | Rows | Open known | Open missing | Coverage |
|---|---:|---:|---:|---:|
| V2F1 | 22,564 | 21,581 | 983 | 95.6435% |
| V2F2 | 20,756 | 20,154 | 602 | 97.0996% |
| V2F3 | 21,016 | 20,361 | 655 | 96.8833% |
| V2F4 | 20,396 | 20,286 | 110 | 99.4607% |
| V2F5 | 25,647 | 25,644 | 3 | 99.9883% |
| V2F6 | 33,844 | 33,844 | 0 | 100.0000% |

## Time, ticker, and session concentration

| Year | Rows | Open known | Open missing | Coverage |
|---:|---:|---:|---:|---:|
| 2021 | 33,313 | 29,332 | 3,981 | 88.0497% |
| 2022 | 61,064 | 56,374 | 4,690 | 92.3195% |
| 2023 | 53,068 | 50,680 | 2,388 | 95.5001% |
| 2024 | 49,700 | 48,272 | 1,428 | 97.1268% |
| 2025 | 55,783 | 55,681 | 102 | 99.8171% |
| 2026 | 39,705 | 39,705 | 0 | 100.0000% |

Ticker concentration:

- 652/737 tickers have no missing Open in the V3-B population;
- 78 are partially missing;
- 7 have no known Open rows;
- top 10 missing tickers contain 5,061 rows (40.2018% of missing);
- top 20 contain 7,471 (59.3455%);
- top 50 contain 11,660 (92.6205%).

Top missing tickers include `FREN 773`, `CLEO 689`, `ISAT 619`, `WINS 614`,
`IMPC 472`, `MSIN 446`, `SGER 444`, `UFOE 368`, `ADHI 321`, and `KKGI 315`.

Worst official sessions were concentrated at the historical boundary. The
lowest was 2021-06-03 with 175/209 known (83.7321%), followed by 2021-07-21
with 175/208 (84.1346%). The full 1,231-session table is preserved externally.

## Causal Open-feature readiness

The diagnostic definitions are explicit and model-free:

- overnight gap: `Open_t / prior_close - 1`, where `prior_close` is the
  previous observed ACTIVE panel bar for the same ticker;
- intraday return: `Close_t / Open_t - 1`;
- Open position: `(Open_t - Low_t) / (High_t - Low_t)`, left undefined when
  `High_t == Low_t`;
- Open-to-High: `High_t / Open_t - 1`;
- Open-to-Low: `Low_t / Open_t - 1`.

The decision time is after session close, so current-day Open is available by
the decision time; the prior-close lag is explicit. No forward fill,
synthetic value, or adjusted-price substitution was used.

| Feature | Usable rows | Rate |
|---|---:|---:|
| Overnight gap | 280,044 | 95.6980% |
| Intraday return | 280,044 | 95.6980% |
| Open position | 278,168 | 95.0569% |
| Open-to-High | 280,044 | 95.6980% |
| Open-to-Low | 280,044 | 95.6980% |
| All five features | 278,168 | 95.0569% |

There were 1,876 Open-known rows with a flat High-Low range; their Open
position was left unavailable rather than fabricated.

## Remaining-missing provenance overlap

The 12,589 missing rows were reconciled against the preserved Yahoo residual
detail and TradingView census where available:

| Remaining-missing bucket | Rows | Share |
|---|---:|---:|
| TV H/L/C disagreement | 4,887 | 38.8196% |
| TV history-window unavailable | 4,632 | 36.7940% |
| Corporate-action/outside TradingView target | 2,101 | 16.6892% |
| TV identity/provider error | 969 | 7.6972% |

The original Yahoo residual classes for these rows were also preserved in the
external detail, including provider H/L/C mismatch, provider error, no provider
row, and two corporate-action residual classes. The whole V3-B population is
already liquidity/universe-eligible by construction; rows are not removed to
improve coverage.

## Recommendation

`CONDITIONAL_PASS_FOR_OHLCV_ALPHA_RESEARCH`.

Open coverage is broad enough for a controlled OHLCV challenger only on an
explicit common-support intersection. It is not a clean unrestricted
population: 2021/2022 coverage is materially lower, seven tickers are fully
missing, and the top 20 tickers contain 59.3455% of missing rows. Any future
HLCV-vs-OHLCV comparison must use the exact same 278,168-row Open-feature
intersection for both sides, with partition/year/ticker diagnostics retained.

This is a research-data adequacy recommendation only. It is not execution-
grade promotion, model approval, or a license to access fresh-forward outcomes.

## Validation and artifacts

- Focused pytest: **3 passed**.
- Full pytest: **274 passed**, 6 existing `FutureWarning` locations, 0 failures.
- Network calls: **0**.
- Training/tuning: **not performed**.
- External runtime root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\open_research_coverage_gate_v1_20260812`
- Artifact manifest SHA-256:
  `7e15220bedc3f12c9576f43e8e0efcb8f906301828788a56fca36c1a5caf9e87`
- Coverage summary SHA-256:
  `bacaa2cf4a098dca3b6d7ec93a2782c22ba2c60a0ee77a1d782cfddc20df9ab1`

Source hashes:

| Source | SHA-256 |
|---|---|
| Immutable panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| Accepted derivative panel | `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab` |
| Accepted derivative provenance | `90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687` |
| SMBR candidate audit | `33b06259e663ab3ecae5be01514d495a071ef57f7628b061986cf88af9e0e7f5` |
| V3-B final-refit table | `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe` |
| V3-B final-refit manifest | `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9` |
| Yahoo residual detail | `26cd2319991aa5dc2fcce78d7f256f31fb1762b4510c0623fcd16fb87b66fd02` |
| TradingView census | `1c05a53155ed52783f112f58babc363e4ee081180542be71a9dfa1bd3ba4c5cd` |

The overlay and all diagnostic files remain external to Git. Stop for
independent ChatGPT review.
