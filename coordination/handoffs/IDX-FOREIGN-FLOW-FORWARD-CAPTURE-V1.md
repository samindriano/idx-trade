# IDX Foreign Flow Forward Capture V1

Branch: `data/idx-foreign-flow-forward-capture-v1`

Implemented an offline, resumable foreign-flow sidecar runtime over existing canonical Stock Summary raw artifacts.

Artifacts per session:
- `idx_foreign_flow.parquet`
- `idx_foreign_flow.manifest.json`

Semantics:
- `ForeignBuy` / `ForeignSell` unit = `SHARES`.
- `foreign_net = foreign_buy - foreign_sell`.
- capture timestamp is only a knowledge-time upper bound; publication time remains unknown.
- all official 4/5-character security codes are archived without common-share inference.
- raw Stock Summary SHA and parent session manifest SHA are pinned.
- zero provider calls; no historical bulk acquisition.

Next local verification: run focused/full pytest, then run `python -m idx_trade.forward_foreign_flow_runtime --runtime-root <runtime>` against preserved forward sessions. Review artifacts before integrating with the installed canonical EOD scheduler.
