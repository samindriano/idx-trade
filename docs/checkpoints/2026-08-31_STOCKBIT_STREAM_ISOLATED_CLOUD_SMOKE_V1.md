# Stockbit Stream Isolated Cloud Smoke V1

Date: 2026-08-31 Asia/Jakarta

## Scope

Bounded off-hours functional proof for the Stockbit Stream cloud path. This checkpoint does not claim scheduler proof for the production 08:47 WIB slot and does not modify model, outcome, counter, PaperState, canonical production capture, or production R2 namespace.

Branch: `ops/stockbit-stream-cloud-smoke-v1`

Initial smoke implementation commit: `f9f955a10c56a363f23340ed9d700a9b3719edc0`

Manual-only workflow cleanup commit: `4eb483b0442c408343a3e2f9e4434f8d4aa62562`

## Isolation contract

The smoke workflow uses:

- real GitHub hosted runner;
- real repository secrets;
- real IDX stock-summary universe lookup through the existing ZAPI path;
- real Stockbit Stream provider calls;
- existing parser/normalizer/HMAC logic;
- real private R2 writes;
- `slot=smoke`;
- `top_n=5`;
- throwaway R2 prefix `stockbit-stream-smoke-v1/<github.run_id>`.

The workflow explicitly rejects the production prefix `stockbit-stream-v2` and limits smoke size to 1-10 tickers.

## First cloud smoke

GitHub Actions run: `33350648499`
Job: `99363210215`
Conclusion: `SUCCESS`

Observed summary:

- status: `DATA_READY`
- planned calls: `5`
- completed calls: `5`
- successful responses: `5`
- response classifications: `OK=5`
- normalized post rows: `150`
- source session: `2026-08-28`
- slot: `smoke`
- top_n: `5`
- universe SHA-256: `99bb3c934ed85bfd1e2120a5bbea45ab538be7104cd0d3b2117f334cb1ada6ea`
- run id: `2026-08-31_smoke_99bb3c934ed85bfd_43ecc72d7e38076f`
- manifest SHA-256: `a2b95868556ade33954e21a0fa9881ed04bf99c4568cade9a12993d1e8826535`
- model accessed: false
- outcome accessed: false
- counter mutated: false

R2 success is evidenced by the returned immutable manifest SHA and `DATA_READY` result from the existing archive implementation.

## Workflow rerun observation

The same GitHub run was rerun once to inspect replay behavior.

Second job: `99363394903`
Conclusion: `SUCCESS`

Observed summary:

- status: `DATA_READY`
- planned/completed/successful: `5/5/5`
- normalized post rows: `150`
- source session: `2026-08-28`
- universe SHA-256 unchanged: `99bb3c934ed85bfd1e2120a5bbea45ab538be7104cd0d3b2117f334cb1ada6ea`
- run id changed to `2026-08-31_smoke_99bb3c934ed85bfd_fc5135f82cf1628f`
- manifest SHA-256: `e394eab51d9754ff3e435b81ef1115a5b6e1801482262f4419b86ef5f5a5c8a6`

This rerun is a fresh observation, not an idempotent replay, because the existing run namespace intentionally includes the exact raw universe-source response SHA. The selected universe stayed identical while the exact raw source-response digest changed. No production correctness claim depends on treating this cross-process rerun as idempotent.

No further provider rerun is required for this bounded smoke task.

## Verdict

`STOCKBIT_STREAM_CLOUD_FUNCTIONAL_PATH = PASS`

Proven in an isolated namespace:

`GitHub Actions -> secrets -> universe lookup -> Stockbit provider -> parser -> normalization -> HMAC -> immutable R2 manifest/data`

This materially narrows the morning 08:47 miss: the cloud capture implementation itself is functional. The remaining live acceptance question is scheduler/invocation behavior for the genuine production slot and production-size `top_n=200`, not basic cloud connectivity.

## Remaining live gate

`STOCKBIT_STREAM_0847_SCHEDULER_PROOF = PENDING`

Next genuine live proof should observe the normal 08:47 WIB production schedule without using the smoke namespace as a substitute for scheduled production evidence.

The separate morning finding that no native GitHub `schedule` runs appeared on 2026-08-31 should be handled as scheduler/watchdog reliability work, not by reopening Stockbit Stream provider/parser/R2 debugging.
