# OHLCV O2 Forward Ledger Resume Fix

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-forward-v1`
Starting review HEAD: `29ce88aec6a1b2c9655b4cb134a4089339133876`
Status: `O2_FORWARD_RESUME_FIX_IMPLEMENTED_PENDING_INDEPENDENT_REVIEW`

## Review blocker fixed

The independent review identified that `persist_session_score_artifact(...)`
returned an in-memory `manifest_sha256` but did not write that field into the
persisted JSON. A process restart could therefore reload the artifact without
the hash required by `OfficialO2Counter.register(...)`.

The bounded fix now:

- computes `manifest_sha256` deterministically from canonical manifest content
  excluding the self-referential hash field;
- writes that hash into the JSON manifest before returning;
- reloads and self-verifies the newly written JSON;
- reloads an existing immutable artifact only when its data hash and persisted
  manifest hash both verify;
- refuses partial artifacts, changed data, missing manifest hash, or invalid
  manifest hash without overwriting anything.

## Counter resume hardening

Added `load_counter_state(...)`, which validates:

- exact counter schema, frozen 100-session requirement, and H10 horizon;
- outcome-clean state;
- non-negative first post-freeze boundary;
- count range and exact consecutive `last_session_index` relationship.

`persist_counter_state(...)` now refuses:

- rewinds in session count;
- changes to the first post-freeze boundary;
- changing the last session at the same count;
- malformed or outcome-tainted existing state.

## Explicit regression coverage

The focused tests now cover:

1. write a session artifact;
2. read the persisted JSON and verify its `manifest_sha256`;
3. call the existing-artifact path after creating a new counter object;
4. register the reloaded artifact successfully;
5. persist and reload counter state;
6. reject counter rewind and first-boundary changes.

## Validation and protected boundary

- focused forward-ledger pytest: `4 passed`;
- full pytest: `286 passed, 5 warnings`;
- official O2 score artifacts created: `0`;
- official O2 counter entries created: `0`;
- provider calls: `0`;
- protected outcomes accessed: `false`;
- model artifacts changed: `false`;
- feature/eligibility contract changed: `false`.

The five warnings are existing pandas FutureWarnings in unrelated modules.
Official O2 forward scoring remains unauthorized pending independent review of
this fix.
