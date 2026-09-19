# Independent Structural Review Correction — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Stage: `Q_INDEPENDENT_REVIEW_CORRECTION_REPLAY`

## Trigger

An independent read-only red-team identified two implementation risks in prior
target-free structural artifacts:

1. `research/alpha_structural_robustness_v1.py` selects lookback variants by
   positional index after a key merge has reset the index. This can associate a
   variant score with the wrong `(ticker,date)` row.
2. `research/alpha_combination_economics_v1.py` computes value/volume
   percentiles over the full panel, while the combination selection itself is
   restricted to `eligible_decision_universe`.

The earlier V1 code and outputs are historical evidence and will not be
overwritten. This preregistration defines independent V2 replays that change
only the identified implementation defects.

## Scope and invariants

- Use the same frozen features, panel, official sessions, and anchors as the
  V1 studies.
- Preserve candidate formulas, lookbacks, equal-weight combinations, top-K
  values, friction scenarios, and frozen-session window.
- V2 robustness variant scores must be joined by explicit `(ticker,date)` keys,
  never by post-merge positional index.
- V2 combination percentiles must be ranked within each date using only rows
  where `eligible_decision_universe=true`; non-eligible rows receive no
  percentile.
- Do not access targets, forward returns, labels, incumbent score artifacts,
  providers, cloud, capture, scheduler, canonical production state, or
  protected outcomes.
- Do not create candidate IDs, fit weights, refit, rescue, or promote a
  candidate.
- Preserve all V1 artifacts and report V1 versus V2 as a correction audit.

## Predeclared gates

1. V2 base-formula equivalence remains exact within `1e-10`.
2. V2 has no duplicate keys and no target-like output columns.
3. V2 robustness lookback metrics are key-aligned and reproducible.
4. V2 combination liquidity percentiles have an explicit eligible-only
   contract and the output carries the eligible denominator metadata.
5. All access flags remain false and the lane remains isolated.

## Decision rule

If either correction changes a previously recorded structural conclusion, the
V1 conclusion is superseded for scientific interpretation but remains in the
ledger as a preserved historical artifact. No predictive or economic claim is
created by this replay.

## Planned outputs

- `research/alpha_structural_robustness_v2.py`
- `research/alpha_combination_economics_v2.py`
- staged V2 JSON outputs under the isolated external research staging root
- one result checkpoint with code/output hashes and the V1/V2 disposition

