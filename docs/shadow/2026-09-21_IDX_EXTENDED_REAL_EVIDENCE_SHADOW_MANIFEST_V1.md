# IDX-Trade Extended Real Evidence Shadow Manifest V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **IMMUTABLE COPY PASS / MIGRATION NOT AVAILABLE**

## Scope and boundary

This manifest extends the earlier 237-file forward-monitoring discovery copy
with bounded retained evidence found in the approved local parent root. The
source was read-only. The copy is isolated and is not an active runtime root.

Source base:

`D:\Documents\Project\idx-trade-data-gate-20260808v`

Shadow root:

`C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-extended-evidence\inputs`

Copied classes:

- `corporate_actions`: event registries and cross-check summaries;
- `execution`: execution-anchor input and session retrieval summaries;
- `sessions`: exchange-session calendars and target-window summaries;
- `forward_open_archive_windows_20260810`: retained Official Open archive
  metadata/logs.

No provider checkout/call, protected outcome/PnL access, counter access,
active-runtime write, scheduler mutation, cloud/R2 mutation, canonical-data
rewrite, alpha/model operation, or migration/replay entrypoint was performed.

## Copy attestation

| Class | Files | Bytes |
|---|---:|---:|
| corporate_actions | 6 | 25,332 |
| execution | 5 | 85,032,239 |
| sessions | 12 | 118,860 |
| forward_open_archive_windows_20260810 | 9 | 4,060 |
| **Total** | **32** | **85,180,491** |

For every row below, source pre-hash, source post-hash, and copy hash were
calculated. All 32 rows were equal; source changes during copy: `0`; copy
mismatches: `0`.

Aggregate digest over sorted `relative_path|bytes|copy_sha256` rows, joined by
LF and encoded as UTF-8:

`be2276257e47bd378d22f8e9b71afcaf19231eec6772dbd8e3917cdf685847af`

| Relative path | Bytes | Source SHA-256 | Copy SHA-256 | Equal |
|---|---:|---|---|---|
| corporate_actions/idx_actions_summary.json | 820 | 9e0f77db9a7a1319183716de007848c67211ccad9f33127d38f1320cd7e9f7dd | 9e0f77db9a7a1319183716de007848c67211ccad9f33127d38f1320cd7e9f7dd | True |
| corporate_actions/idx_actions.csv | 10305 | 40c0ade2a3d2f4a73483d7016c61eef751eda961ead3f9c6a6cfaa7217a20aa6 | 40c0ade2a3d2f4a73483d7016c61eef751eda961ead3f9c6a6cfaa7217a20aa6 | True |
| corporate_actions/official_idx_split_reverse_actions_504_summary.json | 432 | bc09f05f6919640a2a1d4103b02e728f639e6f63dba17ae2d92fdc09c2217ea4 | bc09f05f6919640a2a1d4103b02e728f639e6f63dba17ae2d92fdc09c2217ea4 | True |
| corporate_actions/official_idx_split_reverse_actions_504.csv | 4948 | 22b56b2441da228f0996a9d8d0558e6aaef48ffe45be925af9e63a479779e7eb | 22b56b2441da228f0996a9d8d0558e6aaef48ffe45be925af9e63a479779e7eb | True |
| corporate_actions/yahoo_split_cross_check_summary.json | 246 | d13e208b05efc643418c19c5432d2bec5582aab1f17328fd2f19711879a40192 | d13e208b05efc643418c19c5432d2bec5582aab1f17328fd2f19711879a40192 | True |
| corporate_actions/yahoo_split_cross_check.csv | 8581 | 442bf262730c71bf78e2762720951eec6774eb54947e09419e1a5efe36e197c3 | 442bf262730c71bf78e2762720951eec6774eb54947e09419e1a5efe36e197c3 | True |
| execution/idx_execution_anchors.csv | 84974693 | 06fc978b939d1de51a435b2c85bbd14a66274a7664ecdbf720f22309cd0d9aba | 06fc978b939d1de51a435b2c85bbd14a66274a7664ecdbf720f22309cd0d9aba | True |
| execution/idx_execution_backfill_summary.json | 397 | b84f46ac09380365f0e16df0a8c54add220ff10ffec8d9025aacaa891e3984e0 | b84f46ac09380365f0e16df0a8c54add220ff10ffec8d9025aacaa891e3984e0 | True |
| execution/idx_execution_diagnostics.csv | 2 | 7eb70257593da06f682a3ddda54a9d260d4fc514f645237f5ca74b08f8da61a6 | 7eb70257593da06f682a3ddda54a9d260d4fc514f645237f5ca74b08f8da61a6 | True |
| execution/idx_execution_session_report.csv | 56446 | 371c4bb117a903dd70021d6da789244cd52ba9ac0d67902b63e99ae2c994a38b | 371c4bb117a903dd70021d6da789244cd52ba9ac0d67902b63e99ae2c994a38b | True |
| execution/target_execution_summary.json | 701 | 18d923e7df63594cee931d8b3c136b1d6dbca2ab196238e4567fb301a2e1519d | 18d923e7df63594cee931d8b3c136b1d6dbca2ab196238e4567fb301a2e1519d | True |
| forward_open_archive_windows_20260810/forward_open_archive/latest_run.json | 236 | c9bc5aa4fbb129ea274e13037a9f7f39ce9c0cd8a7718d0a37c3db040347d786 | c9bc5aa4fbb129ea274e13037a9f7f39ce9c0cd8a7718d0a37c3db040347d786 | True |
| forward_open_archive_windows_20260810/forward_open_archive/logs/forward-open-20260810-012432.log | 478 | 5090411fbcab53d49ceea4d6ed4cbaf31d8e775255dc7d45e34952d5da4e1380 | 5090411fbcab53d49ceea4d6ed4cbaf31d8e775255dc7d45e34952d5da4e1380 | True |
| forward_open_archive_windows_20260810/forward_open_archive/logs/forward-open-20260810-220001.log | 478 | af8fe8f0f5522a03b4d32e9a81998da394f88c7830302872a09bdc511ef28698 | af8fe8f0f5522a03b4d32e9a81998da394f88c7830302872a09bdc511ef28698 | True |
| forward_open_archive_windows_20260810/forward_open_archive/logs/forward-open-20260811-103940.log | 478 | 9a54653c7715af451f9d26f8f92f358f7a308ea69b98a7ee9184c84eafe8892e | 9a54653c7715af451f9d26f8f92f358f7a308ea69b98a7ee9184c84eafe8892e | True |
| forward_open_archive_windows_20260810/forward_open_archive/logs/forward-open-20260811-220002.log | 478 | 35bfb4fdacc6f4e786970c1890496516434df97711329172966b85e5136f8352 | 35bfb4fdacc6f4e786970c1890496516434df97711329172966b85e5136f8352 | True |
| forward_open_archive_windows_20260810/forward_open_archive/logs/forward-open-20260812-074016.log | 478 | 90102c21fb38876fea2887f2c1eb4a70195315ca09285b3112b24bb841dab8ce | 90102c21fb38876fea2887f2c1eb4a70195315ca09285b3112b24bb841dab8ce | True |
| forward_open_archive_windows_20260810/forward_open_archive/logs/forward-open-20260812-081430.log | 478 | b20b83ce29e4675bd69fffffadc58b404556075d1ced09ba499897c4049b5d32 | b20b83ce29e4675bd69fffffadc58b404556075d1ced09ba499897c4049b5d32 | True |
| forward_open_archive_windows_20260810/forward_open_archive/logs/forward-open-20260812-082923.log | 478 | 3736a99642e849b42b3b1694df18afc69ef75a3640bd641ea02eeecdd9bedf82 | 3736a99642e849b42b3b1694df18afc69ef75a3640bd641ea02eeecdd9bedf82 | True |
| forward_open_archive_windows_20260810/forward_open_archive/logs/forward-open-20260812-220003.log | 478 | 08805638a021110904dda52d25fc6404e7009a6d4f646ec48368b1885ea9f01e | 08805638a021110904dda52d25fc6404e7009a6d4f646ec48368b1885ea9f01e | True |
| sessions/additional_sessions_504.csv | 4542 | 9e8eed1112405f81a901f410845da57bae9bf3f82ac698aa916c7bca45c57af2 | 9e8eed1112405f81a901f410845da57bae9bf3f82ac698aa916c7bca45c57af2 | True |
| sessions/calendar_2024_2025/exchange_session_sources.csv | 15720 | 6bd703545cbcb3984cdccdcb4ba574cca7ecc9d5d5484b9a91a29469f9de06a6 | 6bd703545cbcb3984cdccdcb4ba574cca7ecc9d5d5484b9a91a29469f9de06a6 | True |
| sessions/calendar_2024_2025/exchange_session_summary.json | 4933 | 189447b3415288ea36bf665ee150cfd0ec9062ed19c4b0cfb38bc091c9bdb0e7 | 189447b3415288ea36bf665ee150cfd0ec9062ed19c4b0cfb38bc091c9bdb0e7 | True |
| sessions/calendar_2024_2025/exchange_sessions.csv | 4578 | 76c4b6d8aa1c615c6759b46fcbc246ccdcbbd892b732a247c92468cb96d57e06 | 76c4b6d8aa1c615c6759b46fcbc246ccdcbbd892b732a247c92468cb96d57e06 | True |
| sessions/calendar_default/exchange_session_sources.csv | 25312 | 8792484e3718189b40b901662179662c4f56f56d0dd9a5ff468fc90630573cbb | 8792484e3718189b40b901662179662c4f56f56d0dd9a5ff468fc90630573cbb | True |
| sessions/calendar_default/exchange_session_summary.json | 9410 | fba9e0d168f8c49588aa4e5263fbba7649fbc5e7e0ee3c0ff057d60141e25996 | fba9e0d168f8c49588aa4e5263fbba7649fbc5e7e0ee3c0ff057d60141e25996 | True |
| sessions/calendar_default/exchange_sessions.csv | 522 | a4fc897f7e840d16c28db5d6af82003035c05b07bc38b121a48f9c9289712476 | a4fc897f7e840d16c28db5d6af82003035c05b07bc38b121a48f9c9289712476 | True |
| sessions/exchange_session_sources.csv | 20252 | 56b559a1eecfe2da695f38e1182afdf1b5a9d83bdd08f2afa8ae81db21d4d47c | 56b559a1eecfe2da695f38e1182afdf1b5a9d83bdd08f2afa8ae81db21d4d47c | True |
| sessions/exchange_session_summary.json | 20981 | e46b825335d8f0c19b5a97d09611dab8b34d1c40b705f30c7ebd07cf6b7c76aa | e46b825335d8f0c19b5a97d09611dab8b34d1c40b705f30c7ebd07cf6b7c76aa | True |
| sessions/exchange_sessions.csv | 6198 | 3a3bdb6db642e26eaee9b5d9f85b0e1ac16e9d6a70ea3ddd60c0d032e99c6279 | 3a3bdb6db642e26eaee9b5d9f85b0e1ac16e9d6a70ea3ddd60c0d032e99c6279 | True |
| sessions/target_504_summary.json | 358 | 49923767fef76915aa70f33006e2694ecff1f109cbbf0d064b9727a7752c1e5d | 49923767fef76915aa70f33006e2694ecff1f109cbbf0d064b9727a7752c1e5d | True |
| sessions/target_sessions_504.csv | 6054 | d22ecbc172d7325d4ff06d1be12e45794ad0c698f0a96ba761e6bdaa49b55542 | d22ecbc172d7325d4ff06d1be12e45794ad0c698f0a96ba761e6bdaa49b55542 | True |

## Classification of the copied classes

| Class | Observed evidence | Runtime qualification classification | Migration disposition |
|---|---|---|---|
| Corporate actions | 38 IDX event rows / 35 tickers; 18 rows in the certified window; all `stockSplit`; Yahoo cross-check `22 MATCH`, `16 IDX_RATIO_UNAVAILABLE`, `5 YAHOO_ONLY` | `REAL_CA_EVENT_REGISTRY`, not a CA entitlement/settlement ledger | no migration; CA composition remains blocked without holdings, obligations, receivables, payment, and restart state |
| Execution | 504 session report rows, all `OK`; 479,471 `REGULAR` anchor rows; 425,340 `ACTIVE` and 54,131 `NO_TRADE`; one regular-execution-observation evidence type; zero duplicate `(ticker, market, as_of_date)` keys; 0 unresolved metric rows | `REAL_EXECUTION_ANCHOR_INPUT`, not a transaction/fill vector or paper execution artifact | no migration; use only as source evidence after separate interface/lineage authorization |
| Sessions | 516 available calendar sessions / 504 target sessions, 2024-06-03 through 2026-07-31 | `REAL_CALENDAR_INPUT`, not a runtime schedule binding | no substitution for the 23 embedded hashes; no historical manifest was rewritten |
| Official Open archive | one retained run metadata file plus eight small logs | `REAL_OPEN_CAPTURE_ARCHIVE`, not an execution-grade paper state | no replay or activation |

The execution summary contains a cache path ending in `20260808u` while the
approved parent root is `20260808v`. This is retained metadata and is recorded
as partial lineage; it was not corrected or treated as an identity match.

These artifacts expand the real evidence census but do not produce a real
paper-state snapshot, prepared parent, fill vector, pending ledger, CA ledger,
or recovery chain. Therefore `REAL_MIGRATION`, full `HISTORICAL_REPLAY`, real
`CA COMPOSITION`, and real `RECOVERY` remain blocked.
