# 2026-08-13 Foreign Flow Forward Capture

Status: `IMPLEMENTED_CI_PASS_LOCAL_RUNTIME_REQUIRED`

The implementation reuses the official IDX Stock Summary raw artifact already stored by canonical EOD capture. It adds an immutable per-session foreign-flow sidecar in SHARES plus a hash-bound manifest and an offline catch-up runtime. It makes zero provider calls.

Implementation:
- `src/idx_trade/forward_foreign_flow.py`
- `src/idx_trade/forward_foreign_flow_runtime.py`
- `tests/test_forward_foreign_flow.py`
- `tests/test_forward_foreign_flow_sidecar.py`

Semantics:
- `ForeignBuy` and `ForeignSell` are archived in `SHARES`; net is buy minus sell.
- zero is retained as a real observed value;
- missing/invalid/partial/duplicate/date-mismatched rows fail closed;
- all official 4/5-character security codes are archived without inferring common-share eligibility;
- capture time is stored only as an upper bound on knowledge time, not publication time;
- sidecar provenance pins the official raw Stock Summary SHA and parent session-manifest SHA.

Validation:
- GitHub Actions full pytest on the implementation head: `268 passed`, 23 existing warnings.
- No scheduler deployment was performed.

Next boundary: local runtime verification against preserved canonical forward sessions, especially 2026-08-12, then independent integration review before adding this runtime to the installed EOD scheduler.
