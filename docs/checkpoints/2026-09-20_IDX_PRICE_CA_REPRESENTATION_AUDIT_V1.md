# IDX Price and Corporate-Action Representation Audit V1

Date: 2026-09-20  
Lane: isolated `codex/alpha-available-data-20260919`  
Status: **FAIL — INVALID OPTIONAL CA VALUES ARE NOT PRESERVED AS UNKNOWN**  
Evidence class: synthetic-only, read-only audit

## Scope and boundary

This audit examines the local OHLCV canonicalization boundary where vendor-adjusted close, split, and dividend columns become execution-safe/raw and corporate-action flags. It does not access a provider, protected outcomes, capture/cloud state, canonical data, or production artifacts. No source or data was modified.

The result is about representation semantics. It does not establish that the current price history contains malformed optional fields or that any live corporate action was missed.

## Baseline validation

The lane-local focused suite completed successfully:

```text
python -m pytest -q tests/test_data.py tests/test_data_gate.py tests/test_adversarial_data_gate.py
7 passed
```

The passing tests confirm that raw execution prices remain separate from vendor adjustment and that sorted corporate-action flags work for clean numeric inputs. They do not cover malformed optional corporate-action values or duplicate provider dates.

## Reproduced behavior

Synthetic input included two rows for `2025-01-01` with different closes, then one row for `2025-01-02` whose optional values were:

```text
stock_splits = "2:1"
dividends = "bad"
adj_close = "bad"
```

Observed output:

```json
{
  "rows": 2,
  "dates": ["2025-01-01", "2025-01-02"],
  "split_flags": [false, false],
  "dividend_flags": [false, false],
  "adj_nan": 1
}
```

The duplicate `2025-01-01` row was reduced to one row using `keep="last"`; the earlier conflicting close was not reported. The invalid optional values were first coerced to `NaN`. The split/dividend series then uses `fillna(0.0)`, so both malformed values become non-events. The invalid adjusted close remains `NaN`, and the factor-change flag is false for that row rather than an explicit invalid-input state.

## Exact implementation evidence

- `src/idx_trade/data.py:25-29` — canonicalization normalizes columns and aliases.
- `src/idx_trade/data.py:45-47` — raw and optional vendor columns use `pd.to_numeric(..., errors="coerce")`.
- `src/idx_trade/data.py:51` — duplicate dates are silently reduced with `keep="last"`.
- `src/idx_trade/data.py:68-71` — invalid adjusted close becomes a missing factor and does not raise.
- `src/idx_trade/data.py:77-81` — missing or malformed split/dividend values are filled with zero before event flags are created.
- `src/idx_trade/security_master.py:22` — ticker normalization removes `.JK` anywhere in the string, rather than validating it as a suffix; this is an adjacent identity concern already covered by the universe/evaluation checkpoints.

Source hashes at audit time:

| File | SHA-256 |
|---|---|
| `src/idx_trade/data.py` | `F85EB18A0564E7E6FB3C8A479918B0A1F99C96F51A329806FF4DB5C3F5499A4D` |
| `src/idx_trade/security_master.py` | `C777600F459D69CB2B52C6C4C8EEB61FD22D7AFB1A85645FB63E1D4EBD180B69` |
| `tests/test_data.py` | `93F7D373839D475722F4407F0BE497EC7AF9FC1946731545C0B5FF74CEC5CE6B` |

## Risk interpretation

The canonicalizer is conservative for raw execution prices and does not infer a split merely from vendor adjustment-factor changes. However, malformed optional CA values are not preserved as an explicit unresolved/invalid state. They can be converted into an apparent no-event, which is unsafe for downstream CA completeness claims. Duplicate dates can also discard one observation without an audit conflict.

This is a representation-boundary failure and a reason to keep CA completeness fail-closed. It is not evidence of live contamination, and it does not authorize importing a fallback provider or rewriting the canonical panel.

## Hardening proposal — not applied

If implementation is later authorized:

1. Validate optional numeric fields before coercion or retain a per-column invalid-input flag.
2. Treat malformed split/dividend values as `UNKNOWN`/blocked, never as zero.
3. Reject duplicate dates or emit a typed conflict before deduplication.
4. Keep vendor adjustment anomalies separate from explicit CA event evidence.
5. Validate ticker suffix normalization through one shared identity contract.

Any fix must be tested in this isolated lane and must not rewrite existing price or corporate-action history.

## Verdict

**FAIL — INVALID OPTIONAL CA VALUES ARE NOT PRESERVED AS UNKNOWN**

No source, data, provider, cloud, capture, or production mutation was performed.
