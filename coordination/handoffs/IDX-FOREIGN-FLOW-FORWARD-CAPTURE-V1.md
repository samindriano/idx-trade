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

Validation so far:
- GitHub Actions full pytest: `268 passed`, 23 existing warnings.
- CI was run via a temporary draft PR to the unchanged EOD integration base; the PR was closed without merge.

Required local runtime verification:
1. fetch this branch and run the focused foreign-flow tests plus full pytest;
2. run `python -m idx_trade.forward_foreign_flow_runtime --runtime-root <canonical runtime root>`;
3. verify the preserved 2026-08-12 Stock Summary produces a complete sidecar, expected source raw row count around the existing 963-row capture;
4. verify `ForeignBuy`/`ForeignSell` remain non-null, net equals buy-sell, unit is SHARES, provider_calls=0, hashes verify, and the parent canonical artifacts remain unchanged;
5. rerun the runtime once to prove idempotency/no refetch;
6. write a factual runtime checkpoint and stop for independent integration review.

Do not deploy or modify the installed scheduler in the local-runtime step. Do not touch Corporate Action, Financial PIT, PIT-sector, historical bulk acquisition, models, or protected outcomes.
