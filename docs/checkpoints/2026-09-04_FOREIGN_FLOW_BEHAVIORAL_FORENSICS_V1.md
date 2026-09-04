# Foreign Flow Behavioral Forensics V1 — 2026-09-04

Status: `FOREIGN_FLOW_BEHAVIORAL_FORENSICS_V1_OFFLINE_COMPLETE`

Decision: `INTERESTING_BUT_TOO_QUALIFIED`

This checkpoint records a new outcome-blind behavioral investigation. It does
not rewrite the accepted Exploration V1 notebook or claim predictive alpha,
production admission, or historical real-time availability.

## Orchestration and lineage

- Level: `HEAVY`.
- Execution surface: one MAIN with three read-only `LOCAL_CHILD_AGENT` lanes:
  independent V2 replay; structural/anomaly/CA/listing/liquidity analysis; and
  PIT/economic/redundancy/adversarial analysis.
- Branch: `research/idx-foreign-flow-behavioral-forensics-v1`.
- Research base: accepted Exploration V1 head
  `64d0dc541f6e31adbb657b1bb3c3f8b95d6fb0a2`.
- Main coordination claim: `d7ec68775dc10e04d36c3ff5a9cce317414e08ca`
  (coordination-only Foreign Flow row update).
- Accepted Exploration V1 notebook remained byte-untouched. The active branch
  carries only the current main worker-execution policy addition in `AGENTS.md`.

Detailed report and all tabular outputs are in:
`D:\Documents\Project\idx-foreign-flow-behavioral-forensics-20260904-v1`

Artifact manifest SHA-256:
`349a6757a306210a001f734729927641abd4e51e72ca1d2844871aa4d016054b`

## Hash-bound sources

- Representation V2 manifest:
  `4e8e7278b6505a356c2f95c4ac69a47cb4dc91803cc819cf6b0aaafbe34c98dc`.
- Representation V2 parquet:
  `0c2212a166115b2f5b974b93096ea06b222b7451d70fa7d58257a9bed0f7a1f0`.
- Causal market context:
  `085d7628024c3792bd3a021320ac5377b3e869bcb4ad2e8e2e1209234fe4939d`.
- V2 input manifest:
  `93e39bb9829413b71965978b39d949ea4bb59c1f4e98bf86bf4486b60b585028`.
- Foreign-flow archive manifest:
  `fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334`.
- Official calendar:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`.
- Security master:
  `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.
- Bounded CA V16 manifest:
  `3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030`.

## Coverage and contract findings

- Raw archive: 1,129,024 rows, 1,288 sessions, 983 tickers,
  2021-04-01–2026-08-13.
- Official-calendar intersection: 1,106,490 rows, 1,260 sessions,
  2021-04-29–2026-07-31. 22,534 rows across 28 outside-calendar sessions were
  excluded from V2 materialization.
- V2: 1,102,400 rows, 979 tickers, 1,259 feature sessions,
  2021-04-30–2026-07-31; source flow-through ends 2026-07-30.
- Causal context: 981,939 rows / 945 tickers. HLCV panel: 981,940 rows /
  945 tickers.
- Raw contract: all normalized archive hashes/bytes matched; all units are
  `SHARES`; zero buy/sell negatives; zero `foreign_net` identity mismatches;
  zero duplicate ticker/session rows; no active zero-volume rows.
- Listing contract: zero invalid intervals; one pre-listing row excluded
  (`KOCI`, 2023-10-06).
- Blocking identity coverage: `CNTX`, `GOTOM`, `MAMIP`, and `MYRXP` are flow
  tickers absent from the security master (3,750 rows); 34 security-master
  tickers have no market-context ticker coverage. 2,473 raw rows use
  non-four-character tickers.

## Independent V2 replay

The independent replay did not import or call the V2 feature helper. All 15
accepted fields passed with 1,102,400 matching keys, zero finite mismatches,
zero NaN-pattern mismatches, and maximum absolute difference `0.0`.

The replay also passed the raw net/participation/shock checks, exact
`acceleration = mean_5 - mean_20` identity, cross-sectional rank scope,
listing masks, warm-up rules, zero duplicate keys/infinities, and
`feature_session = next_official(flow_through_session)`. Arithmetic and
mechanical causality are `PASS`; complete universe certification is `UNKNOWN`
because the context/identity scope is not fully reconciled.

## Behavioral and anomaly findings

- `foreign_flow_shock_1` is close-valued net shares divided by prior
  20-session median regular-market value. `regular_market_value / (close *
  volume)` has Q01 `0.9401`, median `1.0000`, Q99 `1.0750`; it is a traded-value
  proxy, not an independent historical float series.
- Absolute shock median rises from `0.0317` to `0.1251` across price
  quintiles, `0.0282` to `0.1320` across current-liquidity quintiles, and
  `0.0267` to `0.2156` across abnormal-volume quintiles.
- Largest requested cases are FUJI (`62,062.3`, 2022-12-20 flow), CASA
  (`-41,719.1`, 2021-10-12), JGLE (`-31,310.1`, 2024-05-02), and PSKT
  (`-19,722.1`, 2022-01-18). The broader `|shock|>5` tail is 4,809 rows /
  632 tickers and `|shock|>20` is 1,301 rows / 334 tickers.
- Bounded primary-liquid rank scope is 347,837 rows, 740 tickers, 1,240
  source sessions; source cross-sections have median size 268 and range
  222–433. Typical daily absolute-shock concentration is top 1 `5.98%`, top 5
  `19.14%`, top 10 `28.85%`.
- Persistence exists descriptively but is highly redundant: shock vs signed
  streak `+0.9408`; 5-session shock mean vs weighted persistence `+0.9168`;
  20-session `+0.9018`. Acceleration is an exact transform, not a new source.
- Shock vs same-session close return is `+0.1305` Spearman; nonzero flow/price
  signs agree `58.17%` and oppose `41.83%`. High-effort/low-result is `4.13%`
  under the declared descriptive quantiles. These are behavioral descriptions,
  not causal or future-return claims.

## CA, PIT, and adversarial boundary

- CA comparison used only the bounded resolved transition-attestation ledger:
  55 rows / 52 tickers, all `stockSplit`. None of the 12 ranked anomaly names
  appears in it. Exhaustive CA absence and anomaly cleanliness are `UNKNOWN`.
- All raw sessions are `RETROSPECTIVELY_ACQUIRED`; manifest
  `publication_time_known=false`. Retrieval `knowledge_at_utc` is not a
  historical first-known timestamp. PIT publication/revision validity is
  `UNKNOWN / BLOCKING`.
- Price provenance is mixed: 751,958 `IDX_PUBLIC_STOCK_SUMMARY` and 229,982
  `YAHOO_RAW` panel rows; 446,843 opens are null. Close/volume/range remain
  descriptive, but homogeneous price-basis interpretation is not certified.
- Adversarial audit finds plausible explanations in price denomination,
  liquidity/volume, listing age, ticker identity, mixed price provenance, and
  unresolved CA. No residual economic mechanism is certified.

## Hypotheses and next experiment

Park only a small future shortlist:

1. flow-price disagreement / effort-versus-result;
2. aggregate breadth/concentration as a market-regime descriptor;
3. persistence only as a conditioned descriptive state, not as an independent
   shock-derived feature.

Reject raw share magnitude, unconditioned shock tails, persistence/acceleration
as independent features, exhaustive CA-clean claims, and any predictive claim
in this phase. Do not freeze or execute `FOREIGN_FLOW_ALPHA_CHALLENGER_V1` yet.

If later authorized, first freeze one bounded hypothesis, exact features,
target/horizon, universe, PIT cutoff, folds, baseline, metrics, acceptance
criteria, multiplicity policy, and artifact contract before protected outcome
access. No future outcome/label, model fit, feature selection, provider call,
production capture, counter/PaperState/R2 mutation, or deployment occurred in
this lane.
