# IDX-Trade Real CA Interface Remediation V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **LOCAL INTERFACE DEFECT FIXED / CA COMPOSITION STILL BLOCKED**

## Observed real-artifact failure

The copied real canonical CA registry
`corporate_actions/idx_actions.csv` contains 38 `stockSplit` rows. Sixteen
rows materialize optional `old_shares`, `new_shares`, and `ratio` fields as
CSV `NaN` values because the source counts are unknown.

Before remediation, passing those copied rows through the candidate's
`parse_idx_corporate_actions` boundary failed closed at the first such row
(`ALDO`) with `ValueError: Invalid old_shares`. The failure was not a provider
call and did not read live state.

## Isolated remediation

Changed only the candidate shadow branch:

`src/idx_trade/providers/idx_corporate_actions.py`

`_parse_share_count` now treats scalar pandas/NumPy `NaN` as missing (`None`),
while non-scalar malformed values still fail closed through the existing
`Decimal` validation path. No ratio, share count, price, or action was
fabricated.

Added regression coverage:

`tests/test_idx_corporate_actions_provider.py::test_nan_optional_share_counts_remain_unknown_not_invalid`

## Evidence after remediation

| Check | Result |
|---|---|
| Focused CA/provider tests | 8/8 passed |
| CA/attestation/dividend/V4-X1 regression set | 38/38 passed |
| Candidate parser against copied real `idx_actions.csv` | 38 input rows → 38 parsed rows |
| Parsed action family | all `stockSplit` |
| Valid effective dates | 38/38 |
| Derived ratios | 22 present; 16 remain unknown |
| Provider/network/live invocation | none |
| Full repository suite | collection blocked by an existing unrelated import/dependency issue involving `idx_trade.stockbit_stream_archive`; not treated as a CA regression |

The full suite attempt was not retried. The focused regression set is the
authoritative validation for this isolated change; the earlier full-suite
result remains documented separately, with the current collection limitation
preserved explicitly.

## Qualification boundary

This remediation proves canonical CA event-shape compatibility in the shadow
candidate. It does not create a CA entitlement/settlement ledger, holdings,
obligation, receivable, payment, or restart chain. Therefore:

- `REAL_CA_EVENT_REGISTRY`: PASS WITH LIMITATION;
- `CA COMPOSITION`: BLOCKED REAL;
- `REAL_MIGRATION`: BLOCKED because no paper-state artifact exists;
- no live runtime, provider, scheduler, cloud, counter, outcome, or alpha
  surface was changed.
