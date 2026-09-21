# IDX-Trade Immutable Shadow Input Manifest V2

Date: 2026-09-21 (Asia/Jakarta)

Status: **PASS FOR SELECTED INPUT CLASS / PAPER-STATE CLASS ABSENT**

## Shadow root

- Root: C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921
- Input root: C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs
- Files copied: 20
- Total copied bytes: 750,681
- Source stability: PASS; source hash before and after copy matched
- Copy integrity: PASS; every copy hash matched the post-copy source hash
- Destination was new and separate from the active E2E runtime root.

The raw copied files remain outside Git and outside the live runtime. This
branch commits only this hash/path manifest and the associated documentation.

## Hash-bound copied inputs

For every row below:

source SHA-256 before copy = source SHA-256 after copy = copy SHA-256.

| Class | Type | Session | Source path | Shadow copy path | Bytes | SHA-256 |
|---|---|---|---|---|---:|---|
| active_config | runtime config | n/a | C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1\operational\config.json | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\active\operational\config.json | 1,729 | fff7af72d7c761218385faadba11bb09408110c76b9fbaa43e121d5ec9bfb3e0 |
| active_config_sidecar | config SHA sidecar | n/a | C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1\operational\config.json.sha256 | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\active\operational\config.json.sha256 | 65 | 1e9dd3cba267b3a1f9b5e4122375a2ff3d0be2bdd60bdc601e930df8934b2c0d |
| active_latest_metadata | operational metadata | 2026-09-21 | C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1\operational\latest.json | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\active\operational\latest.json | 1,556 | 52fcba8be3f9eb3dc7f8830f64ccbfa783f3aa60000f1635e4d722e2b82c517c |
| active_official_open_metadata | OfficialOpen metadata | 2026-09-21 | C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1\official_open\latest_capture.json | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\active\official_open\latest_capture.json | 301 | c955e693aeaa51908ac19c1da2376e04d5b82d3752569e722b3e27b455a09f17 |
| session_manifest | session manifest | 2026-09-16 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-16\manifest.json | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-16\manifest.json | 5,021 | 27912cb5b6a8e04608e0a44bf2e9f8eb8e207cf0492585d1eb9421a2340d7119 |
| session_ohlcv | session OHLCV | 2026-09-16 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-16\session_ohlcv.parquet | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-16\session_ohlcv.parquet | 94,172 | 6d5b5b2977928835aa50a0fcf7a36a5910e58e46db9223ad4ae505f747aa4860 |
| model_input | model input | 2026-09-16 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-16\model_input.parquet | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-16\model_input.parquet | 31,522 | f5d39e7ee642f376ee9b50949a4fe77adfceda607eb436e304592e538fb3efde |
| session_evidence | session evidence | 2026-09-16 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-16\session_evidence.parquet | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-16\session_evidence.parquet | 17,810 | aa86b96e88311891acfe6f48bf3190344ff4ead0caf231a32119b4eb08549639 |
| stock_summary | stock summary | 2026-09-16 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-16\idx_stock_summary.csv | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-16\idx_stock_summary.csv | 175,114 | 7b3c4a0f9b05487b25170e1fa4cadc7296d00e53e346e1263bfcec7b85370818 |
| index_summary | index summary | 2026-09-16 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-16\idx_index_summary.csv | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-16\idx_index_summary.csv | 16,396 | 1a99d391cd1775d8b4b413bf210e8a777cfde9dd31fe8e414a350970a524d696 |
| session_manifest | session manifest | 2026-09-17 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-17\manifest.json | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-17\manifest.json | 5,021 | e4174f611ab75e51a9f31d2f5924ad62e123c6bdc68b0c163e468fa45602252 |
| session_ohlcv | session OHLCV | 2026-09-17 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-17\session_ohlcv.parquet | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-17\session_ohlcv.parquet | 94,425 | 4481137b79086db1d8249806d5f575fe7a461849b693edcce8f87a9eafabf433 |
| model_input | model input | 2026-09-17 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-17\model_input.parquet | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-17\model_input.parquet | 31,634 | f7bdebb038d110425225311b0fa99122370d4b6ac2076ee6d3a3d129025be4e8 |
| session_evidence | session evidence | 2026-09-17 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-17\session_evidence.parquet | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-17\session_evidence.parquet | 17,837 | 09a9318ccb585f7ad8f7fcc327bf578ee8bebe0d4aad88120555a09466e8a026 |
| stock_summary | stock summary | 2026-09-17 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-17\idx_stock_summary.csv | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-17\idx_stock_summary.csv | 175,140 | 7534a1890aa11eafbaea55d2d9d4f3bf152e24089f3827aac56815f228ba1ef1 |
| index_summary | index summary | 2026-09-17 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-17\idx_index_summary.csv | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\sessions\2026-09-17\idx_index_summary.csv | 16,353 | a54f8dba45518cb97e735f57c1ef99c39d98753125e4a129f50e59dcb2f958e7 |
| exchange_calendar | exchange calendar | 2026-09-16/17 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\calendar\exchange_sessions.csv | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\calendar\exchange_sessions.csv | 342 | 8a5fd51630c331b651fcd41bd024a70c6f8fad6dcc9fe9d5393429e16766a6fe |
| schedule_attestation | execution schedule attestation | 2026-01-01/2026-12-31 | D:\Documents\Project\idx-e2e-schedule-attestation-20260824-v1\attestation\execution_schedule_attestation.json | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\schedule\execution_schedule_attestation.json | 5,509 | 6c81eb8457cbb5558339e08bd7a159fe700adbe441e287f56a99fb237e081a65 |
| score_manifest | V4-X1 score manifest | 2026-09-17 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\model_runs\2026-09-17\v4_x1_clean_geometry3_prospective_v1\manifest.json | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\model_runs\2026-09-17\v4_x1_clean_geometry3_prospective_v1\manifest.json | 22,496 | d3e627a4440ca9225617599328bbd12af30b9ba06a3f921fb1ee7710eb834be0 |
| score_artifact | V4-X1 score parquet | 2026-09-17 | D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\model_runs\2026-09-17\v4_x1_clean_geometry3_prospective_v1\score_artifact.parquet | C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921\inputs\forward\model_runs\2026-09-17\v4_x1_clean_geometry3_prospective_v1\score_artifact.parquet | 38,238 | 909e6e98f576434d8151bc96b30b4208fc76cb30e3fa50cfc472ecc02c47b72c |

## Admission boundary

The copied active runtime files are diagnostic metadata only. The copied
session files are real retained session/model evidence. None is a paper
portfolio state, prepared execution, fill vector, pending ledger, or CA
ledger. Therefore this manifest proves immutable input handling but does not
open the real migration or canary gates.

The score manifest is retained as a real input, but its embedded artifact path
is an absolute source path outside the shadow root. It is therefore not passed
to the candidate score loader from the copied root without an explicitly
labelled shadow adapter. The source manifest is not rewritten.
