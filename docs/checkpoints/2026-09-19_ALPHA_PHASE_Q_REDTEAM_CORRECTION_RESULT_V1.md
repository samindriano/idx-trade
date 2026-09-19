# Phase Q Independent Red-Team and Correction Replay — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Stage: `Q_INDEPENDENT_REVIEW_CORRECTION_REPLAY`
Result: `NO-GO FOR COMBINATION READINESS / STRUCTURAL-ONLY`

## Executive disposition

An independent read-only red-team found no basis for a candidate promotion or
protected evaluation. It did find two implementation defects in prior
target-free studies. The historical V1 artifacts are preserved, but the
affected interpretations are superseded by the corrected V2 replays below.

The protected packet remains exactly C1–C4 and remains blocked by independent
Data QA. H-LIQ-01 remains
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 was created.

## Independent red-team findings

| Challenge | Verdict | Evidence and consequence |
|---|---|---|
| C1/C2/C4 static formula/key closure | `PASS` limited | Independent review reproduced the frozen feature/panel relationship; this is not PIT or predictive proof. |
| Historical PIT/as-of/vintage | `UNKNOWN` | The panel has date but no row-level available-at, knowledge timestamp, revision, or vintage contract. |
| Corporate-action basis | `FAIL` for readiness | 188 unresolved scale rows across 19 tickers/70 dates, with factors up to 25x; the forensic substitution changes 82,357 C1 score rows and lowers minimum Top-30 overlap to 36.6667%. Values are not admitted corrections. |
| Issuer/ISIN continuity | `UNKNOWN` | The security master interval join is one-to-one for eligible rows but does not contain an issuer/ISIN transition chain. |
| Listing interval | `PASS` narrow | 310,761/310,761 eligible rows map to exactly one active identity; the full panel still has one uncovered key outside eligibility. |
| Survivorship/population completeness | `UNKNOWN` | The available master/panel snapshot has no population-completeness contract; this remains a Data QA gate. |
| Combination readiness | `FAIL` | C1/C4 daily rank dependence is high (full-sample Spearman about 0.4113 for the component scores; combination-level dependence is higher), and real capacity is not admitted. No optimized weights or promotion are authorized. |
| Economic capacity | `UNKNOWN` | `regular_market_value` is only a proxy; ADV, spread, queue, order-book, and executable-fill evidence are absent. |

## Correction A — robustness lookback alignment

The V1 robustness code used a positional `.loc[surface.index]` after a merge
that reset the index. This could attach a variant score to the wrong key. V2
joins every variant explicitly on `(ticker,date)` and leaves formulas,
lookbacks, frozen inputs, and diagnostic scope unchanged.

| Candidate/horizon | V1 mean Top-30 overlap | V2 key-aligned mean Top-30 overlap | V2 finite rows |
|---|---:|---:|---:|
| C1 h3 | 12.1056% | 57.2333% | 154,939 |
| C1 h10 | 12.0389% | 52.0389% | 154,939 |
| C2 h3 | 11.6722% | 65.3167% | 155,679 |
| C2 h10 | 11.4556% | 60.1389% | 155,679 |
| C4 h10 | 11.2944% | 44.7611% | 155,309 |
| C4 h40 | 12.0778% | 45.4111% | 155,635 |

All V2 rows cover 600 frozen dates. Base-formula equivalence remained exact
within `1e-10`; the V1 low-overlap values must not be used as evidence of
extreme horizon instability. The corrected values still show meaningful
horizon dependence and do not establish predictive robustness.

## Correction B — combination liquidity denominator

The V1 combination code ranked `regular_market_value` and `volume` over all
panel rows, while selection was restricted to eligible rows. V2 ranks within
each date over `eligible_decision_universe=true` only. Combination formulas,
weights, selection, turnover, and friction scenarios are unchanged.

| Combination | V1 bottom-value Q25 | V2 bottom-value Q25 | V2 bottom-volume Q25 | V2 mean Top-30 turnover |
|---|---:|---:|---:|---:|
| C1+C2 EW | 0.6278% | 40.6722% | 33.6167% | 42.1369% |
| C1+C4 EW | 0.4333% | 30.7722% | 29.1389% | 34.8470% |
| C2+C4 EW | 0.7056% | 39.0667% | 31.9611% | 36.7001% |
| C1+C2+C4 EW | 0.6500% | 40.3556% | 33.5278% | 37.9521% |

The prior combination liquidity-exposure claims are therefore invalid and
must be replaced by the V2 values. This materially strengthens implementation
caution; it does not prove a loss, profitability, capacity failure, or
predictive redundancy.

## H-LIQ-01 independent novelty result

The independent replay finds H-LIQ-01 structurally distinct from C1/C2/C4,
but novelty at the economic-mechanism level remains `UNKNOWN`:

- mean daily Spearman versus C2 is `0.0996`, versus the C2 turnover-level
  component `0.1648`, and Top-30 overlap versus C2 is `31.34%`;
- dependence rises in the top-value quartile to about `0.1958`;
- h10/h20/h40 turnover is `16.83% / 10.31% / 6.90%`, with h20 overlaps only
  `61.13%` and `62.02%` against the neighboring horizons;
- baseline bottom-value Q25 exposure is `39.672%`; a size-neutral diagnostic
  reduces it to `14.983%` but raises turnover to `20.785%` and retains
  `72.01%` overlap.

No C5 or size-neutral variant is admitted.

## Reproducibility and hashes

Frozen source hashes:

- panel: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- guarded features: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- official sessions: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- tradability anchors: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`

Corrected V2 artifacts in the isolated external staging root:

- robustness builder: `research/alpha_structural_robustness_v2.py`, SHA-256
  `d5b07ff38cb61723bc4a3470e2716857cf5a5dbb5227baaf5f3f98e4f7bb63ee`
- robustness output: `alpha_structural_robustness_v2_key_aligned_final.json`,
  SHA-256 `64d03527b7bb504dee34e854ed9123f03fb55c557a455462eef46a928c823444`
- robustness verifier: `research/verify_alpha_structural_robustness_v2.py`
- combination builder: `research/alpha_combination_economics_v2.py`, SHA-256
  `5c1db06448f656f7a11a1217a7e05887c398beeb7900592eed2f8432f1d971ff`
- combination output: `alpha_combination_economics_v2_eligible_percentiles.json`,
  SHA-256 `87b195ea6cbd281d861932bd9bdf2935c9538bfb6b5031bee2dbf60675ee6c2f`
- combination verifier: `research/verify_alpha_combination_economics_v2.py`

Both V2 verifiers returned `PASS`. Compile and diff checks pass. All access
flags are false; no target, outcome, provider, cloud, capture, scheduler,
canonical, or production state was opened or modified.

## Decision and next action

`C1/C2/C4` remain `FUTURE_RESEARCH` (C4 also economic caution), C3 remains
`BLOCKED`, H-LIQ-01 remains future/no-C5, and the protected evaluation packet
remains `SPECIFICATION_ONLY / BLOCKED_BY_DATA_ADMISSION`.

Do not use the superseded V1 robustness lookback overlaps or V1 combination
liquidity-exposure percentages. Continue only with bounded CA/issuer/PIT and
capacity audits from already admitted local evidence; do not reopen providers
or protected outcomes.

