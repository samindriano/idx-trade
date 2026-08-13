# IDX Foreign Flow Forward Capture V1

Branch: `data/idx-foreign-flow-forward-capture-v1`
Implementation checkpoint: `docs/checkpoints/2026-08-13_FOREIGN_FLOW_FORWARD_CAPTURE_IMPLEMENTED.md`

Implemented an offline, resumable foreign-flow sidecar runtime over existing canonical Stock Summary raw artifacts.

Artifacts per session:
- `idx_foreign_flow.parquet`
- `idx_foreign_flow.manifest.json`

Semantics:
- `ForeignBuy` / `ForeignSell` unit = `SHARES`.
- `foreign_net = foreign_buy - foreign_sell`.
- zero is a valid observed flow value.
- capture timestamp is only a knowledge-time upper bound; publication time remains unknown.
- all official 4/5-character security codes are archived without common-share inference.
- raw Stock Summary SHA and parent session manifest SHA are pinned.
- zero provider calls; no historical bulk acquisition.

Hardening and local validation completed:
- strict integer SHARES, exact net identity, zero preservation, and fail-closed
  missing/partial/fractional inputs;
- strict `DATA_READY`/outcome/source/completeness/date/HTTPS parent contract;
- canonical rebuild verification from deterministic session-local parent files;
- exclusive create-once sidecar/manifest publication with interrupted-manifest
  recovery and no-overwrite conflict handling;
- coherent sidecar + sidecar-manifest tampering rejected;
- focused tests `18 passed`; full pytest `280 passed, 0 failed, 3 warnings`.

Runtime root:
`D:\Documents\Project\idx-trade-data-gate-20260808v`.

The offline catch-up ran twice with `provider_calls=0`. First run created and
verified sessions 2026-08-11 and 2026-08-12; second run created none and
verified both as already valid. Each has 963 rows, 962 four-character codes,
one five-character code, and respectively 299/286 zero-flow rows. Full raw,
sidecar, manifest, knowledge-time, and parent-hash details are pinned in the
checkpoint. Parent canonical manifest hashes were unchanged. Legacy 2026-08-03
and 2026-08-10 lacked raw Stock Summary and were skipped; no 2026-08-13 session
was locally available.

Verdict: `FOREIGN_FLOW_PROSPECTIVE_SIDECAR_SAFE_LOCAL_RUNTIME_ONLY`.
Scheduler integration is not included or authorized by this handoff.

Do not deploy or modify the installed scheduler. Do not touch Corporate Action,
Financial PIT, PIT-sector, historical bulk acquisition, models, or protected
outcomes.
