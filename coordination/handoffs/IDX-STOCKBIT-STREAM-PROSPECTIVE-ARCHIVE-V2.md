# IDX Stockbit Stream Prospective Archive V2 — Handoff

owner: ChatGPT/Stockbit-Stream-Remediation  
status: `CLOUD_SMOKE_PASS_READY_FOR_ROUTINE_PROMOTION`

## Decision

The 963-ticker bootstrap is not the recurring contract. V2 recurring capture is top 200 by prior completed IDX-session regular-market traded value, three times per trading day, using GitHub Actions and private Cloudflare R2.

Any V1 full-universe objects already present remain immutable noncanonical bootstrap/census evidence. Do not delete them and do not schedule V1 again.

## Runtime

- workflow: `.github/workflows/stockbit-stream-prospective-capture.yml`
- runner: `scripts/run_stockbit_stream_capture_v2.py`
- capture implementation: `src/idx_trade/stockbit_stream_capture_v2.py`
- identity whitelist: `config/stockbit_stream_universe_v1.csv`
- storage prefix: `stockbit-stream-v2`

Schedule (Asia/Jakarta): `08:47`, `12:07`, `16:47` on Monday-Friday.

## Live verification

Temporary PR `#34` was used only because the available GitHub connector can observe PR-triggered Actions runs. It was closed without merge after the smoke.

Run `32450648278`, job `96678410979`:

- source session `2026-08-20`;
- top 5 bounded smoke;
- 5/5 Stream responses `OK`;
- 150 normalized post observations;
- manifest SHA-256 `0d9e4ccc3ea224aeae5e396f86d627f64fe6708e06d35c7907df1157c2118bbe`;
- universe SHA-256 `c12c95b65481cfa95f23d06dd5fb7bde89eb82eade3dbc0c54817dd4ee1d995a`;
- private R2 write path completed successfully;
- secrets remained redacted.

## Root-cause remediation

Current Zapi REST responses for IDX stock summary carry an outer `project/timestamp/data` envelope. The exact outer bytes are retained for provenance, while the nested finance payload is exposed to validation. This resolved the prior `invalid/empty stock-summary` smoke failure.

## Boundaries

No model fit, sentiment scoring, target/outcome access, IC, V4-X1/O2/counter mutation, or existing local scheduler changes occurred.

## Remaining action

Merge the V2 envelope/schedule cleanup to `main`, then allow the default-branch routine schedule to operate. The old 963-ticker V1 capture must not be used as routine coverage.
