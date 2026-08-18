# V4 primary-liquid 740 minus CA-support 610 universe audit — prep

Date: 2026-08-18
Branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`

## Question

After the V4 CA aggregate continuity gate reached 600/600 at the frozen 90% threshold, audit the apparent `740 - 610 = 130` ticker difference before model execution. The goal is to determine exactly which tickers are outside the CA support population and distinguish benign historical-universe churn from a real support omission.

## Important interpretation

The two counts are not contemporaneous universe sizes:

- `740` is the union of tickers that qualified for the frozen causal primary-liquid universe at least once over the full 1,241-session V4 support history.
- `610` is the union of tickers represented in the frozen 600-date CA continuity ledger.

Therefore a 130-name difference is not automatically an exclusion or data problem. The audit must prove why each name is absent.

## Frozen inputs

- official calendar SHA-256 `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- signal panel SHA-256 `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- security master SHA-256 `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`
- tradability anchors SHA-256 `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`
- frozen CA continuity ledger SHA-256 `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`
- expected frozen validation identity: 600 dates, `2023-12-28..2026-07-17`
- expected union sizes: primary-liquid 740; CA-support 610; exact difference 130.

## Classification contract

For each of the exact 130 tickers, emit:

1. first/last date it was primary-liquid;
2. number of primary-liquid rows inside the frozen 600 validation dates;
3. primary-liquid and raw signal-panel presence during 2026;
4. latest known exact REGULAR-market tradability anchor and date;
5. security-master listing/delisting/status fields when those semantics can be detected without renaming or inference;
6. latest and peak frozen 60-session median regular-market value, with descriptive liquidity bands;
7. an absence class.

Critical rule:

- if a ticker has one or more frozen primary-liquid rows on the exact 600 validation dates but is completely absent from the 610-ticker CA continuity ledger, classify it `POTENTIAL_CA_SUPPORT_DATA_GAP`.
- if it has no primary-liquid row on those dates, its absence is not automatically a CA support bug. Separate 2026-present/non-primary names from historical-only names.

The audit uses liquidity as an internal materiality diagnostic only. It does **not** call a current market-cap provider. Current market-cap verification is a second step only for the bounded active/material candidate set after the exact 130 identities are known.

## Hard boundaries

- outcome-blind only;
- no provider calls in the exact diff stage;
- no targets, returns, ranks, predictions, performance, model fit, or protected-forward access;
- no change to the 90% CA gate or its certified verdict;
- no reinterpretation of ADRO AAI/AADI spin-off semantics;
- no universe removal or model execution from this audit alone.

## Outputs

- `v4_primary740_minus_ca610.csv` — full exact 130 rows;
- `v4_primary740_minus_ca610_priority.csv` — bounded priority subset;
- `v4_primary740_minus_ca610_tickers.txt` — exact sorted identities;
- `summary.json` and `MANIFEST.json` with pinned input/output hashes.
