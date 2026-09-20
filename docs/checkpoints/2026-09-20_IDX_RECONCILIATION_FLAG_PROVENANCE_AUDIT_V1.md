# IDX Reconciliation Flag Provenance Audit V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`
Runtime under audit: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational`
Runtime branch: `runtime/idx-e2e-baseline-paper-v1`
Runtime HEAD: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`

## Verdict

`FAIL — RECONCILIATION_FLAG_IS_NOT_A_PRODUCED_MISMATCH_RESULT`

The pinned runtime treats `reconciliation_required` as a pre-existing input
gate and a serialized state bit. It does not derive the bit from a detected
portfolio, fill, cash, pending-order, corporate-action, or external-account
mismatch. `false` therefore means only that no explicit prior flag was carried
into the transition; it does not prove that the paper state is reconciled.

## Read-only evidence

The probe `research/idx_reconciliation_flag_provenance_probe_v1.py` inspected
the pinned source files with AST/source checks and performed no runtime or data
writes. Its exact result was:

- runtime HEAD matched the pin;
- zero constant `reconciliation_required=True` assignments were found in the
  audited runtime source;
- `PaperPortfolioState` defaults the field to `False`;
- `prepare_execution_v1` and the Decision V2 adapter reject only an input state
  that already has the flag set;
- `execute_open_v1` writes `False` into both `state_after` and
  `ExecutionResult`;
- the dividend-aware loader rehydrates the serialized bit, while serializers
  and `paper_state_hash` carry it forward;
- no mismatch detector assignment was found;
- `writes_performed=False`.

Pinned source hashes:

| File | SHA-256 |
|---|---|
| `src/idx_trade/e2e_paper_orchestration_v1.py` | `d10ace3f01e407ed8198460d5571f26e92107f681f3268ad60be1d42cc081eec` |
| `src/idx_trade/forward_dividend_runtime_v1_1.py` | `98ebc637340757f03e36c3c8b876f134022ca1282b9bad35cf573b4b784eca23` |
| `src/idx_trade/v4_x1_execution_v1.py` | `010567bfd6c9156d5c088a96ecb251ed2074c461cc5c326fcf9c98789ab76fc9` |
| `src/idx_trade/v4_x1_execution_v1_contract.py` | `0208800825e6f2f91af9d224d7540e829828379ca332f6630889789c936cf1fe` |
| `src/idx_trade/v4_x1_execution_v1_decision_v2_adapter.py` | `c151e2b1e43850d3f8c462eea58276a814efc9fa82ea233e73ee2cd46da35fd6` |

Relevant source locations at this runtime pin are the dataclass default and
state hash in `v4_x1_execution_v1_contract.py`, the prior-state gate and the
two explicit `False` writes in `v4_x1_execution_v1.py`, the equivalent prior
gate in the Decision V2 adapter, and serialized reload in
`forward_dividend_runtime_v1_1.py`.

## System interpretation

This is distinct from the already documented quantity-obligation findings. A
partial fill, a pending transition, a CA settlement, or a target reversal can
remain internally hash-consistent while the result still carries
`reconciliation_required=false`. The flag cannot currently distinguish:

1. an actually reconciled paper state;
2. a deterministic but economically underfilled state; and
3. a state for which no reconciliation check was implemented or run.

This makes the field unsuitable as a standalone operational certification or
as closure evidence for the CA/accounting frontier. No claim is made about a
broker or protected external account; those surfaces remain outside this
lane.

## Validation and boundaries

- Focused probe test: `1 passed`.
- `py_compile`: passed for the probe and test.
- `git diff --check`: passed.
- No runtime source, canonical data, provider, cloud/capture/telemetry,
  scheduler, or protected outcome was modified or accessed for mutation.
- No retry of a live/model smoke was performed; no push or merge was performed.

Reopen only with an explicitly authorized versioned reconciliation contract
that defines the evidence source, mismatch taxonomy, state owner, and
restart/replay behavior. Do not treat a future `false` bit as sufficient until
that contract exists.
