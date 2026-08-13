# Stage 5 Post-Mortem — Independent Interpretation

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage5-postmortem-v1`

## Decision

The completed Stage-5 post-mortem supports a **regime/covariate-shift failure hypothesis** for Ranking V1, not a claim that all frozen technical features are devoid of information.

Ranking V1 remains a **FAILED benchmark**. The consumed Stage-5 holdout is diagnostic/development knowledge only and cannot regain independent validation status.

Probability V1 remains `PROBABILITY_V1_NOT_READY_DEFERRED`.

## What the evidence supports

### 1. The A -> B environment shift was large

The strongest post-mortem shifts were market-state variables, especially:

- median ATR/Close SMD `+2.2328`;
- median 20-session return SMD `-1.0206`;
- breadth return-20 positive SMD `-1.0093`;
- primary-liquid universe size SMD `+0.8715`;
- median relative regular-market value SMD `-0.6434`;
- median close-position-20 SMD `-0.5494`.

HOLDOUT_B was therefore a materially different volatility/breadth/return/liquidity environment from HOLDOUT_A.

This is descriptive evidence of distribution shift. It does not by itself prove a causal regime mechanism.

### 2. Performance degradation was localized and progressive, not explained by prevalence alone

Fixed-block HGB ranking:

- A1: PR-AUC delta `+0.0322`, ROC `0.5206`;
- A2: near-null, delta `+0.0016`, ROC `0.5002`;
- A3: delta `+0.0305`, ROC `0.5314`;
- B1: near-null, delta `+0.0014`, ROC `0.5067`;
- B2: negative, delta `-0.0129`, ROC `0.4725`;
- B3: negative, delta `-0.0077`, ROC `0.4848`.

B1 had a very low prevalence (`0.2766`) while ROC remained slightly above 0.50. The clear ranking reversal appears later in B2/B3. Therefore lower base rate alone is not a sufficient explanation for the Stage-5 failure.

### 3. Several core structure relationships remained directionally stable

The following frozen feature/outcome relationships retained their sign from A to B:

- `close_position_20`: negative in both halves;
- `distance_high_20_atr`: positive in both halves;
- `distance_low_20_atr`: negative in both halves;
- `distance_high_60_atr`: positive in both halves;
- `distance_low_60_atr`: negative in both halves.

This weakens the hypothesis that all technical structure signal disappeared in B.

It instead motivates testing whether V1's absolute feature scales and nonlinear interactions failed to transport across market states.

### 4. Momentum behavior changed materially

`close_return_20` shifted from positive absolute levels in A to negative levels in B, while its within-date target relationship became more negative in B.

This is consistent with a materially different return environment and motivates market-relative / cross-sectional treatment rather than relying only on raw absolute returns.

### 5. Volatility was the strongest individual distribution shift and lost its A relationship

`atr14_over_close` had feature SMD `+0.5584` and the daily market median ATR/Close had SMD `+2.2328`.

Its feature Q5-Q1 relationship changed from positive in A to approximately neutral/slightly negative in B.

This supports a V2 hypothesis that absolute volatility level needs explicit market-state context or cross-sectional normalization.

### 6. Weak sign reversals are not automatically useful features

`relative_volume_20`, `log_regular_value_relative_20`, `observed_session_count`, and `security_age_sessions_exact` showed factual sign changes, but several effects were small and close to zero.

They must not be treated as independently validated regime switches.

`observed_session_count` and `security_age_sessions_exact` also drift mechanically with calendar time. V2 should explicitly test whether such time/age proxies add robust incremental ranking information rather than allowing them to serve as implicit time identifiers.

### 7. Top-tail behavior does not rescue V1

HGB decile 10 had strong lift in A (`+0.0558`) but essentially no lift in B (`-0.0013`).

Therefore the failure is not adequately described as "broad ranking failed but top-tail remained valid". Any future top-tail objective must be treated as a new V2 research question.

## Ranking V2 hypotheses authorized for design

The post-mortem supports a bounded V2 design around the following predeclared ideas:

1. **Cross-sectional/date-relative normalization**
   - within-date percentile ranks or robust z-scores for return, volatility, structure, volume and value features;
   - purpose: reduce sensitivity to absolute level shifts across market regimes.

2. **Causal continuous market-state context**
   - breadth-5 / breadth-20;
   - median market return-5 / return-20;
   - median ATR/Close;
   - median close-position-20;
   - relative-volume/value state;
   - no post-hoc regime threshold optimization.

3. **Market-relative / sector-relative strength features**
   - stock return/structure relative to contemporaneous market and, where causal sector mapping is available, sector peers.

4. **Time-proxy control**
   - `observed_session_count` and `security_age_sessions_exact` should be tested only as explicit optional/sensitivity families, not silently relied upon as core ranking drivers.

5. **Ranking-native objective as a bounded challenger**
   - one predeclared date-grouped ranking objective may be compared with the frozen V1-style binary classifiers;
   - this is a new V2 architecture, not a reinterpretation of Stage-5 success.

6. **No top-decile cutoff optimization on the consumed holdout**
   - top-tail enrichment can be a V2 evaluation dimension, but cutoff selection must be predeclared in future validation.

## V2 research-validation policy

Because V2 design is now informed by the consumed Stage-5 holdout, the full historical window through `2026-07-31` is development/research knowledge for V2.

V2 may use chronological walk-forward research across that historical window, but none of those results are independent final validation.

Any independent Ranking V2 or Probability V2 claim requires **fresh forward data strictly after `2026-07-31`**, accumulated after the V2 design/model is frozen.

No Stage-5 rerun or result-driven rescue is permitted.

## Runtime-performance prerequisite

Before broad V2 experimentation, complete the separate performance track:

- exact full-panel equivalence of the candidate vectorized label engine versus legacy;
- wall-clock and peak-memory benchmark;
- immutable cached feature/label research tables so model comparisons do not rebuild deterministic labels/features repeatedly.

This is a computational optimization only and must not alter label/feature semantics.

## Authorization after this review

Authorized next work:

1. finish the performance/equivalence track;
2. freeze a bounded Ranking V2 research specification based on the hypotheses above;
3. implement V2 development experiments only after that specification is frozen.

Not authorized:

- Stage 5 rerun;
- claiming the consumed holdout as independent V2 validation;
- Stage 6 promotion of Ranking V1;
- Probability V1 rescue;
- execution-PnL claims;
- paper/live trading;
- `IDX-VAL-002`;
- merge to `main`.
