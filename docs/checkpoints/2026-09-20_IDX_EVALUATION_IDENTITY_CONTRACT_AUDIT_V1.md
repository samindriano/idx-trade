# IDX Prospective Evaluation Identity Contract Audit V1

Date: 2026-09-20  
Lane: isolated `codex/alpha-available-data-20260919`  
Status: **STRUCTURAL FAIL — METRIC/GATE IDENTITY CONTRACT SPLIT**  
Evidence class: outcome-blind, synthetic-only, read-only audit

## Scope and boundary

This checkpoint audits the identity boundary between the pure prospective-alpha metric engine and the final prospective-access gate. It does not access protected V4-X1 outcomes, provider credentials, cloud/capture state, canonical datasets, or production state. No source code, configuration, telemetry, or dataset was modified. No retry or live model smoke was run.

The historical/official data and corporate-action lanes remain separate. This finding is about ticker identity handling in prospective evaluation; it is not evidence that canonical data is contaminated.

## Validation performed

The focused synthetic-only suite completed successfully:

| Test file | Passed |
|---|---:|
| `tests/test_prospective_evaluation_v1.py` | 19 |
| `tests/test_prospective_preaccess_readiness_v1.py` | 17 |
| `tests/test_prospective_preaccess_adapters_v1.py` | 28 |
| `tests/test_prospective_evaluation_gate_v1.py` | 56 |
| **Total** | **120** |

These passing tests validate the existing intended paths; they do not prove that the pure evaluator and final gate share one identity contract.

## Observed contract split

Synthetic input contained the same issuer in two representations, `ALIS` and `ALIS.JK`, across 10 aligned sessions. No protected target or outcome was used.

| Boundary | Observed behavior | Result |
|---|---|---|
| `validate_alpha_session_alignment` | Checks exact session date/index inventory only; it does not normalize or validate ticker identity. | Accepts the synthetic frame. |
| `deterministic_rank` | Uppercases and trims ticker text, but does not remove `.JK`; therefore `ALIS` and `ALIS.JK` remain different keys. | Ranks both aliases as distinct tickers. |
| `_session_ic_table` / pure metric path | Uses the same uppercase/trim-only identity rule and checks duplicate keys only after that rule. | Accepts both aliases and counts both rows. |
| `evaluate_alpha_metrics` | Runs after session alignment and the pure identity checks. | Accepts 10 sessions with 12 rows per session, including the alias pair. |
| Final gate `_load_score_artifact` | Uppercases, strips `.JK`, trims, then rejects duplicate normalized tickers. | Would reject the same alias pair when loading a score artifact. |

Observed synthetic result:

```json
{
  "alignment_rows": 10,
  "gate_normalization_rule": "strip .JK then reject duplicated tickers",
  "input_normalized_collision": true,
  "metric_first_row_count": 12,
  "metric_session_count": 10,
  "pure_metric_accepts": true,
  "ranked_alias_tickers": ["ALIS", "ALIS.JK"]
}
```

## Exact implementation evidence

- `src/idx_trade/prospective_evaluation_v1.py:97-122` — session alignment validates date/index keys but has no ticker normalization.
- `src/idx_trade/prospective_evaluation_v1.py:145-166` — deterministic ranking uppercases/trims ticker text but does not strip `.JK`.
- `src/idx_trade/prospective_evaluation_v1.py:225-244` — session IC table uses the same identity rule and duplicate check.
- `src/idx_trade/prospective_evaluation_v1.py:735` — prospective evaluation enters the pure metric path after alignment.
- `src/idx_trade/prospective_evaluation_gate_v1.py:320-367` — score-artifact loader strips `.JK` and rejects duplicate normalized tickers.

Source hashes at audit time:

| File | SHA-256 |
|---|---|
| `src/idx_trade/prospective_evaluation_v1.py` | `98658814531367CF779AF71698C2DB77AE454900C1F86B84DDDF1DB0CA834108` |
| `src/idx_trade/prospective_evaluation_gate_v1.py` | `41A5CA7987B529675BC1EF1858B50B763467D3D5651F92178E4D74275F09052A` |
| `tests/test_prospective_evaluation_v1.py` | `AF9D945C01A909C5CCCD11BEC405CE971E1F8D6587B98AFD7C3078DC7B7A3446` |
| `tests/test_prospective_evaluation_gate_v1.py` | `017DA244F5DF06E6E431C63C3017E3319B86F61998C4949CED8EBFBB2B6FF0D6` |

## Risk interpretation

The pure development/metric path can measure and rank two representations of one issuer as if they were separate securities. The final score-artifact loader has a stricter rule and would reject the collision if the artifact reaches that boundary. Therefore the system is not proven to have one consistent identity contract across evaluation stages.

This is a structural fail, not a claim of live contamination or a claim about the quality of any alpha result. It also does not reopen the frozen V4-X1 model or authorize changing the canonical universe.

## Hardening proposal — not applied

If implementation is later authorized, the smallest coherent hardening would be:

1. Define one shared canonical ticker-normalization function for evaluator and gate.
2. Normalize before session alignment, ranking, IC calculation, and duplicate-key checks.
3. Reject normalized `(session_date, ticker)` collisions before any metric is computed.
4. Add a regression test covering `ALIS` plus `ALIS.JK` in both pure and gated paths.

Any change must be reviewed in an isolated lane against the frozen population and must not silently rewrite historical or canonical data.

## Verdict

**FAIL — EVALUATION_IDENTITY_CONTRACT_SPLIT**

No production mutation, canonical-data mutation, cloud/capture action, provider call, or retry was performed.
