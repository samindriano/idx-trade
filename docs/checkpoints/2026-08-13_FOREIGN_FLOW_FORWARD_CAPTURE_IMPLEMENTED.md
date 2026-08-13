# 2026-08-13 Foreign Flow Forward Capture

Status: `IMPLEMENTED_LOCAL_RUNTIME_REVIEW_REQUIRED`

The implementation reuses the official IDX Stock Summary raw artifact already stored by canonical EOD capture. It adds an immutable per-session foreign-flow sidecar in SHARES plus a hash-bound manifest and an offline catch-up runtime. It makes zero provider calls.

The implementation does not deploy or change the installed EOD scheduler. Local test/runtime verification is required before integration.
