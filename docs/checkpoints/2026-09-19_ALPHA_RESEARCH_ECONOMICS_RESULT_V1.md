# Alpha Research Program — Stage A Structural Economics Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `A_OUTCOME_BLIND_ECONOMICS`  
Result: `PASS_STRUCTURAL_ONLY / NOT ALPHA EVIDENCE`

## Scope and boundary

This audit uses the corrected Stage A rank artifact, frozen official sessions,
and the frozen-only panel `regular_market_value` field. It uses the fixed last
600 official sessions (`2024-01-12` through `2026-07-31`) and fixed Top-30
selection. It does not read a target, forward label, incumbent score,
provider, or protected artifact.

The source classification is
`PARTIAL_FROZEN_ONLY_CAPABILITY_DIAGNOSTIC`. Results below are structural
turnover/liquidity/concentration diagnostics, not IC, OOS, net-return, or
promotion evidence.

## Frozen friction interpretation

The protocol assumptions are buy fee 15 bps, sell fee 25 bps, and 10 bps
slippage per side. For the one-way turnover definition
`1 - Top30 overlap / 30`, the matched-turnover cost burden is 60 bps at base
assumptions and 110 bps under the +25 bps-per-side sensitivity. The reported
mean friction is this burden multiplied by observed one-way turnover; it is not
realized net alpha or a broker-fill estimate.

## Structural economics

| Candidate | Finite dates | Top-30 dates | Mean turnover | Median | Q95 | Base burden (bps/NAV) | Q10 1% capacity (IDR) | Top-10 ticker share | Largest ticker share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C1 residual reversal | 600 | 600 | 42.15% | 40.00% | 56.67% | 25.29 | 7,630,887 | 5.88% | 0.70% |
| C2 participation confirmation | 600 | 600 | 32.91% | 33.33% | 50.00% | 19.75 | 6,403,241 | 7.12% | 0.77% |
| C3 financial quality/growth | 291 | 278 | 10.93% | 10.00% | 27.67% | 6.56 | 13,026,468 | 25.77% | 2.93% |
| C4 path efficiency reversal | 600 | 600 | 23.70% | 23.33% | 36.67% | 14.22 | 5,022,700 | 7.39% | 1.12% |

`Q10 1% capacity` is the tenth percentile of per-selected-name
`1% * regular_market_value`, a coarse structural proxy only. It is not a
capacity guarantee and does not account for spread, queue position, or order
size.

## Interpretation and status

- C2 has lower structural turnover and lower modeled cost burden than C1, but
  this does not establish predictive superiority.
- C4 has the lowest turnover among the three broad-coverage candidates and
  lower cost burden than C1/C2, but it still has no target comparison.
- C1 has the highest turnover/cost burden among the broad-coverage candidates;
  this is an economic caution, not an alpha rejection.
- C3 has low turnover and the highest capacity proxy, but only 278 usable
  Top-30 dates in the frozen window and a 25.77% Top-10 ticker slot share.
  This reinforces its existing `BLOCKED` / partial-PIT status; no fallback or
  sparse-period claim is allowed.
- No candidate is upgraded to `RESEARCH_SURVIVOR`. Historical target access,
  incumbent overlap, IC/ICIR, friction-adjusted return, and prospective
  evidence remain unavailable under the admission gate.

## Reproducibility

- Builder: `research/alpha_stage_a_economics_v1.py`
- Builder SHA-256:
  `df32189c2a78073db632fccad1e2744aada360802f6025d56568671d552a6d85`
- Independent verifier: `research/verify_alpha_stage_a_economics_v1.py`
- Independent verifier SHA-256:
  `bb0ce9ea2d1ddff62d8e5cb8d57f6372895e25529aa159d2fdf7129ea5e22bac`
- Staging directory:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`
- Economics JSON SHA-256:
  `b99f2e8c03610e0505445b4118e5716dc5c177618ba3c100661cc553cb1430b5`
- Independent audit JSON SHA-256:
  `cc6f613bd06618c6386a896b04ae7e8e086a773b5b2e58eaaaa54063293c58a6`
- Independent audit result: `PASS`
- Outcome/provider/target/incumbent access flags: all `false`

