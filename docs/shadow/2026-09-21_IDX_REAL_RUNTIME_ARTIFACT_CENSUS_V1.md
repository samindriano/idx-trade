# IDX-Trade Real Runtime Artifact Census V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **READ-ONLY CENSUS COMPLETE; NO SOURCE MUTATION**

The complete 29-session discovery copy and expanded inventory are recorded in
`2026-09-21_IDX_FULL_SESSION_SHADOW_CENSUS_V1.md`.

## Approved roots inspected

| Root | Files | Bytes | Role |
|---|---:|---:|---|
| `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1` | 135 | 79,770 | active E2E runtime metadata/logs |
| `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring` | 819 | 63,136,721 | retained forward session/model/EOD evidence |
| `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational` | 605 | 5,223,913 | source and tests, not state |
| `C:\Users\Sam\.codex\worktrees\idx-e2e-baseline-paper-pinned-20260824` | 569 | 4,838,475 | pinned source checkout |

## Active E2E runtime contents

Retained relevant classes were `operational/config.json`, its SHA sidecar,
`operational/latest.json`, `operational/controller.lock`,
`official_open/latest_capture.json`, the OfficialOpen logs, and the pinned
wrapper. No prepared artifact, execution artifact, pending ledger, paper
portfolio state, CA ledger, reconciliation artifact, or state snapshot was
found by the bounded filename census.

The `controller.lock` value was all zeroes and was not treated as a live lock.
The latest operational record terminated with
`WAITING_PREPARED_EXECUTION/NO_PREPARED_EXECUTION_FOR_TODAY`.

## Forward-monitoring contents

Top-level classes observed:

`attempts`, `calendar`, `context_bridge`, `eod_automation`,
`model_calendar`, `model_runs`, `prospective`,
`provenance_attestations`, `reliability_v1_shadow`, `sessions`,
`shadow_runs`, and `v4_x1_clean_inputs`.

The `sessions` class contains 29 session-date directories. It contains real
session manifests and data products such as model input, session OHLCV,
session evidence, and stock/index summaries. These are retained data/evidence
artifacts, not proof of an E2E paper portfolio state or execution lifecycle.

The EOD pipeline class contains run metadata. The selected 2026-09-17 run
recorded `PIPELINE_OK_X1_EXISTING_SCORE_VERIFIED` with provider and protected
outcome access disabled in its metadata. This record was not used as a paper
state or migration input.

The expanded read-only scan found 132 model-run files, 262 EOD automation
metadata files, 135 attempt files, and 29 session packages. JSON key-signature
and filename classification did not identify an admitted paper portfolio,
prepared execution, fill vector, pending ledger, or CA ledger. Prospective
`*_state_v1` artifacts were retained as feature/context state contracts, not
reclassified as trading state.

All 29 session packages were copied to a new isolated discovery root. The copy
contains 237 files / 27,907,223 bytes; source pre/post/copy hashes were equal
for every copied file. The copy-attestation digest is
`5246c4ca7e25974db313ebc8f754014c2365d92eb88bac41d114fef0f2c12012`.

## Bounded local extension

A second metadata-only pass covered the local IDXTrade container and the
operational source root to check whether a retained paper-state root existed
outside the approved four roots:

| Local surface | Files | Bytes | Finding |
|---|---:|---:|---|
| `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1` | 135 | 79,770 | 129 logs, 3 JSON metadata files, lock/config/wrapper; no paper-state artifact class |
| `C:\Users\Sam\AppData\Local\IDXTrade\rollback-packages` | 7 | 30,452 | deployment/task backup only; not runtime state |
| `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational` | 605 | 5,223,913 | source/tests/docs, not retained state |

Local cloud/handoff, watchdog, and synthetic-test surfaces were not admitted as
runtime evidence. The provider checkout and protected outcome/counter surfaces
remain excluded. This extension found no additional paper portfolio,
prepared-execution, fill, pending, CA, or recovery artifact beyond the bounded
inventory already recorded.

## Explicit exclusions

- `D:\Documents\Project\idx-bei-forward-ca-provider`: provider checkout; no
  provider data was read and no call was made.
- `C:\Users\Sam\AppData\Local\IDXTrade\pytest-manual-*`: synthetic/manual
  test artifacts; not real retained runtime evidence.
- `C:\Users\Sam\AppData\Local\IDXTrade\cloudflare-*`: Cloudflare handoff
  state; not E2E paper state.
- Protected outcome/counter artifacts: not used as shadow inputs.

## Census conclusion

`REAL_ARTIFACT_DISCOVERY = PASS_WITH_LIMITATION`.

The retained inventory is sufficient to document a real session-input corpus,
but insufficient to qualify real state migration or real recovery. No absence
claim is made beyond the bounded roots and filename classes listed above.
