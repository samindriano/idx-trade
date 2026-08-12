# Expected Payoff V0 Historical Feasibility Result

Date: 2026-08-12 (Asia/Jakarta)  
Branch: `research/idx-expected-payoff-v0-feasibility`  
Frozen specification: `docs/checkpoints/2026-08-12_EXPECTED_PAYOFF_V0_FEASIBILITY_SPEC.md`  
Decision: `EXPECTED_PAYOFF_V0_FEASIBILITY_GO`

## Scope and boundary

This was the single authorized historical-development diagnostic. It consumed
the accepted `O2_OPEN_GEOMETRY` out-of-fold scores exactly as stored; it did not
retrain or rescore O2 and did not fit a payoff model. The frozen contract was:

- signal close at `t`;
- next official IDX-session Open at `t+1`;
- raw Close at official session `t+10`;
- `ATR14_t = Close_t * atr14_over_close_t` from the verified V2 prepared
  feature table;
- primary gross payoff `(Close_t+10 - Open_t+1) / ATR14_t`;
- secondary gross percentage payoff;
- session-level Spearman IC and deterministic D10-D1 spread across six O2
  folds.

No provider call, data repair, synthesis, alternate horizon, alternate entry,
fresh-forward outcome, O2 runtime/counter access, or
`FORWARD_OUTCOME_ACCESS_STARTED` marker was used.

## Parent and source identity

The parent O2 artifact manifest was `O2_SURVIVOR`, SHA-256
`cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`.

| Input | SHA-256 |
|---|---|
| O2 `fold_predictions.parquet` | `fe02c0c743e7bfc5a57b1c8e731c5685a4bff5f9854f910f88703b15a6ca8f0c` |
| O2 stable parent key | `194432c8b5a6e40ee2f20996b373d7bffabfcac284dffe7069c29ec7aa9bef32` |
| immutable model-safe panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| PIT security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| accepted Open panel | `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab` |
| accepted Open provenance | `90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687` |
| canonical V2 prepared feature table | `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5` |
| V3-B final training table | `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe` |
| V3-B final manifest | `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9` |
| tradability anchors | `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e` |
| official split/reverse-action CSV | `a0ef73a548b3657260b46a0c497e6f87dd9b5138588e23006d4b538677125b35` |
| split/reverse-action summary | `cfdc92bc46f47c573dda097a01440768a6c8cd321c686938767462f72172b067` |

The canonical `atr14_over_close` was present in the verified V2 prepared table;
no cross-sectional rank or market median was substituted. The official
calendar had 1-based session indices and supplied the exact `t+1`/`t+10`
mapping.

## Coverage and exclusions

Parent population: **140,679 rows**, four historical years (2023–2026), six
folds. Resolved payoff rows: **140,595**. Global coverage was **99.9403%**;
the minimum fold coverage was **99.8664%**.

| Fold | Parent | Resolved | Coverage | Eligible signal sessions |
|---|---:|---:|---:|---:|
| V2F1 | 21,501 | 21,478 | 99.8930% | 100 |
| V2F2 | 20,057 | 20,046 | 99.9452% | 100 |
| V2F3 | 20,272 | 20,261 | 99.9457% | 100 |
| V2F4 | 20,205 | 20,178 | 99.8664% | 100 |
| V2F5 | 25,347 | 25,345 | 99.9921% | 100 |
| V2F6 | 33,297 | 33,287 | 99.9700% | 100 |

The 84 excluded parent rows were:

- `PRICE_SCALE_CA_CROSSED`: **56** rows. These were excluded fail-closed from
  windows crossing known official stock-split evidence; no price factor was
  invented.
- `OPEN_PROVENANCE_NOT_ACCEPTED`: **28** rows. No Open was filled or
  synthesized.

The row-level coverage ledger retains every parent row and its reason. The
canonical action source contains 55 records / 52 ticker-date events and was
marked query-complete by its source summary; duplicate source records were not
silently collapsed into a price adjustment.

## Fold metrics

The primary metrics are ATR-normalized gross payoff. Percentage payoff is
secondary and non-gating.

| Fold | Median IC ATR | Mean IC ATR | Median D10-D1 ATR | Mean D10-D1 ATR | Median IC % | Mean D10-D1 % |
|---|---:|---:|---:|---:|---:|---:|
| V2F1 | 0.057073 | 0.038194 | 0.207998 | 0.124467 | 0.091950 | 0.018352 |
| V2F2 | 0.052668 | 0.040812 | 0.313278 | 0.292431 | 0.076005 | 0.025475 |
| V2F3 | 0.035852 | 0.020900 | 0.318306 | 0.321963 | 0.038216 | 0.011237 |
| V2F4 | 0.004257 | 0.012900 | -0.088899 | -0.045952 | 0.030070 | -0.001547 |
| V2F5 | 0.032475 | 0.042558 | 0.337194 | -0.018153 | 0.043018 | -0.031351 |
| V2F6 | 0.049088 | 0.050639 | 0.149225 | 0.232901 | 0.114923 | 0.033244 |

Aggregate gate values:

- median of six fold-median ICs: **0.0424700 > 0**;
- q25 of six fold-median ICs: **0.0333188 > 0**;
- positive fold-median IC count: **6/6**;
- median of six fold-mean D10-D1 ATR spreads: **0.1786838 > 0**;
- positive fold-mean spread count: **4/6**.

Both readiness and feasibility gates passed, so the frozen verdict is
`EXPECTED_PAYOFF_V0_FEASIBILITY_GO`. This is evidence that accepted O2 scores
contain historical-development information about the size of a fixed-horizon
gross payoff; it is not a payoff model, net PnL, execution rule, or fresh-forward
validation result.

## Artifacts

External artifact root (kept outside Git):
`D:\Documents\Project\idx-trade-data-gate-20260808v\expected_payoff_v0_feasibility_20260812_001`

The required artifact manifest SHA-256 is
`c84170d5b438ad7481aa9a7985f377fbbd701ebfee80d720cd689d3bb7a49abd`.
It records all required artifact hashes, the parent/resolved stable key hashes,
and all protected false flags. The resolved payoff key SHA is
`f978ec6b81ddc72259e403e78698971f655721f94fbfdcc57f682c5cea3c4602`.

The diagnostic implementation is `src/idx_trade/expected_payoff_v0.py` and its
contract tests are `tests/test_expected_payoff_v0.py`.

## Validation and engineering note

- focused Expected Payoff tests: **6 passed**;
- full pytest after the minimal storage fix: **46 passed, 0 failed, 0 warnings**
  in **5.274 seconds**;
- one pre-run full pytest exposed an existing storage test mismatch: a raw-close
  revision and its derived `vendor_adj_close` were counted twice. The minimal
  fix reports the canonical raw-close conflict once and preserves fail-closed
  revision behavior.
- the one-shot diagnostic completed in approximately **112 seconds** wall time;
  no rerun was performed after outcome access began.

## Stop boundary

Do not fit Expected Payoff V1 automatically. Do not alter O2, O2.1, V3-B, the
forward counter/runtime, or the outcome vault. Independent ChatGPT review is
required before any next payoff-model specification.
