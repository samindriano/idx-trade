# Foreign Flow V2 Core Alpha — One-Shot Result

Status: `FOREIGN_FLOW_V2_CORE_NO_SURVIVOR`

The preregistered experiment was run once after the frozen preregistration
commit. No subset, alternate-window, rescue, provider, forward/O2, or
protected/fresh-forward outcome work followed it.

## Run identity and support

- Branch: `research/idx-foreign-flow-alpha-v2-core`
- Run implementation commit: `8140825643a24b39f7f4a2eb7d5cb88d3dfe754a`
- Preregistration commit: `4adc9484bc33febf240752c3e904a93aca9bae82`
- External result root:
  `D:\Documents\Project\idx-trade-foreign-flow-alpha-v2-core-20260815-001`
- Result manifest SHA-256:
  `23275d2a673ac99dc0928a5a6c0956a0059c82c80a13eea83b4e5db4c4252852`
- Common support: 292,631 rows / 737 tickers / 1,231 sessions
- Support key SHA-256:
  `79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826`
- Session/date boundary: Clean V2 accepted development table through
  2026-07-31
- Flow rows joined: 292,631; missing flow keys: 0
- Complete eight-feature rows: 266,498
- Partial eight-feature rows: 25,873
- All-eight-feature-missing rows: 260
- `feature_session` is the decision session and
  `flow_through_session` is exactly the preceding official session; no same or
  future flow session was detected.

Pinned inputs were verified at run time:

- Clean V2 table:
  `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`
- Foreign Flow V2 feature parquet:
  `0c2212a166115b2f5b974b93096ea06b222b7451d70fa7d58257a9bed0f7a1f0`
- Foreign Flow V2 manifest:
  `4e8e7278b6505a356c2f95c4ac69a47cb4dc91803cc819cf6b0aaafbe34c98dc`
- Official calendar:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

The exact eight-feature challenger block was:

`foreign_participation_1`, `foreign_flow_shock_percentile_120`,
`xs_rank_foreign_flow_shock_mean_5`, `xs_rank_foreign_flow_shock_mean_20`,
`foreign_weighted_persistence_5`, `foreign_flow_acceleration_5_20`,
`foreign_flow_price_divergence_5`, `foreign_flow_price_divergence_20`.

## Fold metrics

| Fold | BASE PR-AUC | Challenger PR-AUC | Paired delta | BASE ROC | Challenger ROC | ROC delta | BASE Q5−Q1 | Challenger Q5−Q1 | Q5−Q1 delta | Top-lift delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V2F1 | 0.401837 | 0.397709 | -0.004128 | 0.525715 | 0.519962 | -0.005753 | 0.083507 | 0.057807 | -0.025700 | -0.013907 |
| V2F2 | 0.419996 | 0.417739 | -0.002257 | 0.526389 | 0.522682 | -0.003707 | 0.060808 | 0.062166 | +0.001359 | -0.021667 |
| V2F3 | 0.423559 | 0.419099 | -0.004460 | 0.524626 | 0.524069 | -0.000557 | 0.045753 | 0.057262 | +0.011509 | +0.004202 |
| V2F4 | 0.411295 | 0.414888 | +0.003594 | 0.502925 | 0.513295 | +0.010370 | 0.043246 | 0.055111 | +0.011865 | +0.009113 |
| V2F5 | 0.501156 | 0.495582 | -0.005574 | 0.539627 | 0.537093 | -0.002535 | 0.060414 | 0.058356 | -0.002058 | +0.013032 |
| V2F6 | 0.340690 | 0.336141 | -0.004549 | 0.487025 | 0.487571 | +0.000546 | 0.045169 | 0.040586 | -0.004583 | -0.011963 |

Aggregate paired diagnostics:

- Median paired PR-AUC delta: `-0.0042937528`
- Q25 paired PR-AUC delta: `-0.0045263462`
- Worst paired PR-AUC delta: `-0.0055742487`
- Positive PR-AUC folds: `1/6`
- Median ROC-AUC delta: `-0.0015457125`
- Median Q5−Q1 delta: `-0.0003497424`
- Median BASE PR-AUC / challenger PR-AUC: `0.4156453 / 0.4163136`
- Median BASE ROC-AUC / challenger ROC-AUC: `0.5251706 / 0.5213221`
- Median BASE Q5−Q1 / challenger Q5−Q1: `0.0530835 / 0.0575347`

## Gate and interpretation

| Frozen check | Result |
|---|---|
| Median paired PR-AUC delta > 0 | FAIL |
| Q25 paired PR-AUC delta > 0 | FAIL |
| At least 2/6 positive PR-AUC folds | FAIL (`1/6`) |
| No ranking guardrail reversal | PASS |

Final allowed verdict: `FOREIGN_FLOW_V2_CORE_NO_SURVIVOR`.

The eight-feature V2 representation did not demonstrate incremental PR-AUC
alpha against the exact Clean V2 control on the preregistered common support.
The challenger improved PR-AUC only on V2F4. The higher aggregate challenger
median Q5−Q1 is not sufficient to pass because the primary PR-AUC checks fail;
no post-result rescue or feature selection is authorized.

Runtime was 35.687 seconds. Output artifact hashes are in the external
manifest, including the six challenger models, paired predictions, fold
metrics, paired metrics, aggregate metrics, gate, and support keys. No raw
provider data was requested, and no O2/forward/protected outcome artifact was
accessed.
