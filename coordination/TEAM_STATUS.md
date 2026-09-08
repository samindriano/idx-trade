# IDX Trade — Repository-Wide Team Status

Last coordinated update: 2026-08-31 Asia/Jakarta
Canonical location: `main:coordination/TEAM_STATUS.md`

## Authority

This is the single live cross-chat coordination ledger for `samindriano/idx-trade`.

- The canonical copy is always `origin/main:coordination/TEAM_STATUS.md`.
- Branch-local checkpoints/specs remain authoritative for scientific contracts and frozen gates.
- This file tracks current ownership, state, progress, and next actions. Historical experiments belong in checkpoints, tombstones, PR history, and archive tags.
- Before material work, read this file, inspect the controlling checkpoint, and avoid duplicating another `ACTIVE` scope.
- Coordination-only commits directly to `main` are permitted only for this file. Implementation and research changes stay on their own branches.

Current project statuses: `ACTIVE`, `WAITING`, `BLOCKED`, `DONE`, `PARKED`, `ARCHIVED`.
Scientific and integrity verdicts: `PASS`, `FAIL`, `UNKNOWN`.

## Repository baseline after Hygiene V2

Repository Hygiene V2 completed on 2026-08-22.

- Before cleanup: **274** remote branches.
- Retained live branches: **50**.
- Removed remote branches: **224**.
- Exact historical heads preserved as archive tags: **45**.
- Tombstone/redundant branch removals: **179**.
- Cleanup used one atomic remote ref transaction.
- Authorized plan SHA-256: `40c3c21e565fa61344ba55675e67d564fc680a016a7729b0e28e768b4f0bbd8f`.
- Deletion-plan tag: `archive/hygiene-v2/deletion-plan-40c3c21e565fa613`.

Do not recreate historical experiment branches merely for convenience. Recover exact old code from an archive tag when needed; otherwise use the durable tombstone/checkpoint conclusion.

Capture/runtime terminology is governed by `docs/repository_hygiene/CAPTURE_RUNTIME_REGISTRY_V1.md`. The canonical capture families are Official Open, EOD Market, Corporate Actions, Stockbit Stream, and Stockbit Intraday. Derived sidecars are not separate collectors.

## Canonical capture surface

| Family | Role | Runtime |
|---|---|---|
| Official Open Capture | Execution-grade next-session `OpenPrice`. | GitHub Actions → private R2. |
| EOD Market Capture | One post-close Stock EOD/OHLCV and market/index context transaction. | E2E POST_EOD cloud path. |
| Corporate Action Capture | Prospective CA evidence for accounting and execution continuity. | Integrated with the E2E path. |
| Stockbit Stream Capture | Prospective market-context archive. | GitHub Actions → private R2. |
| Stockbit Intraday Capture | Post-close intraday reconstruction/capture. | Cloud migration with local fallback retained. |

Foreign flow, reliability/uncertainty, price/trend state, scoring, Decision,
Sizing, Execution, and PaperState are derived or consumer layers, not additional
capture systems.

## Current critical path

| Lane | Status | Progress / blocker | Next |
|---|---|---|---|
| V4-X1 Clean alpha | `DONE` | Alpha science is frozen. | Keep it unchanged during downstream engineering. |
| Research Integrity / Data QA Gate V1 | `BLOCKED` | Population completeness and historical as-of authority remain unknown; admission and closure cannot proceed. | Obtain one authoritative population-wide source contract. |
| EOD Market Capture + prospective V4-X1 scoring | `WAITING` | Accepted E2E path exists; genuine scheduled cloud proof is pending. | Observe the next eligible scheduled run. |
| 100-session prospective alpha evaluation | `BLOCKED` | Frozen access science is in place, but real production evidence is 2/100 and the admitted inventory/target attestation is unavailable. | Complete the separate pre-access closure; do not open protected outcomes. |
| Decision policy | `DONE` | Decision V2 is the incumbent; decision research is closed. | Do not reopen tuning without explicit reprioritization. |
| Sizing, Execution, and CA-aware paper foundations | `DONE` | Frozen foundations are retained; unsupported structural CA remains fail-closed. | Use the retained foundations in the E2E path. |
| E2E Baseline Paper V1 integration | `ACTIVE` | Decision, sizing, execution, EOD/CA state, and the cloud adapter are in one integration lineage. | Verify the next eligible genuine paper cycle. |
| E2E Paper cloud-first orchestration | `ACTIVE` | Scheduled phases are active; the 2026-08-27 POST_EOD run failed and was not rerun. | Wait for the next genuine scheduled POST_EOD. |
| Cloudflare production readiness | `WAITING` | Version-byte preparation and dry-runs pass; production remains inert. | Obtain separately authorized production proof. |
| GitHub Actions cost optimization | `WAITING` | Normal-CI optimization is integrated; representative scheduled production measurements are pending. | Measure the next representative scheduled runs. |
| Stockbit Intraday cloud migration | `ACTIVE` | Cloud schedule, smoke, and bridge-preflight work are in place; genuine production proof is pending. | Run one controlled future-session single-writer proof. |
| Capture/runtime repository hygiene V3 | `WAITING` | Registry and CI are complete; the local tag-capable atomic cleanup has not been applied. | Apply and verify the documented ref cleanup. |

## Always-on operational lanes

| Lane | Status | Progress / blocker | Next |
|---|---|---|---|
| Official Open Capture | `ACTIVE` | GitHub Actions capture writes to private R2 under the accepted implementation. | Continue scheduled observation. |
| Stockbit Stream Capture | `ACTIVE` | Isolated cloud smoke passed; genuine scheduled top-200 proof is pending. | Observe the next eligible scheduled run. |
| Stockbit Intraday Capture | `ACTIVE` | Cloud schedule is enabled and the Windows fallback remains available but disabled during cloud proof. | Verify the first eligible cloud post-close cycle. |
| EOD Market Capture | `WAITING` | Stock EOD/OHLCV and official market/index context use one canonical transaction; first genuine cloud proof is pending. | Verify the next accepted POST_EOD result. |
| Corporate Action Capture | `ACTIVE` | CA acquisition and attestation are integrated with the E2E path. | Verify the first genuine cloud cycle before retiring fallback. |
| Legacy Forward Open scaffold | `PARKED` | Superseded and retained only for exact historical recovery. | Archive the exact head, then remove only the live branch ref when authorized. |
| Frontend monitoring | `PARKED` | Viewer/operations surface only. | Preserve historical model, score, and hover visibility. |

## Parallel retained research and data lanes

These lanes may continue independently but must not silently change frozen V4-X1 or Decision V2.

| Lane | Status | Progress / blocker | Next |
|---|---|---|---|
| Financial PIT / representation | `PARKED` | Retained challenger work is not part of the baseline. | Resume only as a separately scoped challenger. |
| Foreign flow | `ACTIVE` | Outcome-blind behavioral-forensics challenger is active. | Continue within its separate artifact and no-outcome boundary. |
| Price/trend state | `PARKED` | Derived sidecar/challenger only. | Resume only after explicit reprioritization. |
| Reliability / uncertainty | `WAITING` | Forward sidecar evidence is retained; it is not an alpha or Decision input by default. | Wait for a separately scoped review. |
| Historical/open/price-basis remediation | `PARKED` | Historical evidence only. | Do not revive rejected approximate executable sources. |
| Personal KSEI | `PARKED` | Private observation/reconciliation design only. | Resume only with a separately approved authenticated task. |

## Technical anchors

The tables above are the primary view. Exact references remain here for review and forensic routing.

- **V4-X1 Clean alpha:** `research/idx-v4-x1-clean-historical-oos-replay-v1`; `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1`.
- **Research Integrity / Data QA:** PR #103 `audit/research-integrity-data-qa-gate-v1@a1096aa1`; PR #108 `data/ca-aware-feature-basis-remediation-v1@c14e00e6b432705babe5e140b802b82031d7b880`; controlling V16 external manifest `3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030`; V17 external manifest `8d2139c9388c6b94c4131ca692f0de3add433c294e4a7b20f2db6d7f22b106e8`.
- **EOD/scoring:** accepted `integration/idx-e2e-baseline-paper-v1@043003ee`; superseded `data/market-index-forward-eod-v1-monitoring` remains forensic only.
- **100-session evaluation:** `research/idx-forward-evaluation-protocol-v1`; `codex/idx-forward-100-evaluator-v1`; `research/idx-v4-x1-prospective-evaluation-protocol-v1`; PR #89 `ops/v4-x1-preaccess-artifact-completion-v1@1c4c6d17`.
- **Decision:** `research/idx-decision-v2-minimal-implementation-v1`; `research/idx-decision-economic-comparison-v1`; final closure `audit/idx-decision-v4-refill-decoupling-result-v1`.
- **Sizing/Execution/CA:** `integration/forward-ca-attestation-v1`; `data/idx-v4-corporate-action-continuity-gate-v1`; `integration/idx-v4-ca-target-continuity-bridge-v1`.
- **E2E cloud:** `.github/workflows/e2e-paper-cloud-orchestration.yml`; Path-A activation `1eaf79c3f949a65346b064521ecb93a14d39b688`; implementation repin `b8ff82373de922455fce7139fb8d144e97cf5bfb`; input bridge `ops/e2e-paper-cloud-input-provisioning-v1@13cd07af`.
- **Cloudflare:** PR #122 `codex/cloud-runtime-recovery-integration-v1@e03893f344c188ae82856bd833c7aa1614f246eb`; final checkpoint `docs/checkpoints/2026-09-08_CLOUDFLARE_VERSION_BYTE_ATTESTATION_V2_FINAL_REWORK.md`.
- **Cost optimization:** `main@898864b4a8934877dc81086403a2a1068f7a6566`; `docs/checkpoints/ACTIONS_COST_OPTIMIZATION_V1_POST_RESET_MEASUREMENT.md`.
- **Stockbit Intraday:** `.github/workflows/stockbit-intraday-cloud-production.yml`; activation baseline `53767b2b`; PR #95 implementation and PR #105 schedule.
- **Repository hygiene:** PR #94 `ab285091ba5e757a21501e389e5456d37ad43949`; apply contract `docs/repository_hygiene/CAPTURE_RUNTIME_HYGIENE_V3_APPLY.md`.

## Binding evidence and boundaries

- **Research Integrity:** public IDX/KSEI/OJK/issuer/ZAPI evidence remains discovery/event-level; `SOURCE_CONTRACT_REQUIRES_VENDOR_ACCESS` is the technical boundary, and ZAPI is `DISCOVERY_ROUTER_ONLY_NOT_TRANSITION_AUTHORITY`. The controlling V16 population is 412 source rows / 387 economic events / 163 exact-resolved / 178 unresolved / 46 proven non-basis / 27 proven linkages. V17 changes the resolved/unresolved split to 167/174 while preserving V16. Population completeness and historical as-of authority remain `UNKNOWN`; the technical feasibility result is `NO_CERTIFIABLE_SCOPE_CURRENTLY`, and no same-science certifiable subset is established.
- **Prospective evaluation:** real production score evidence and the runtime counter remain `2/100`; the canonical admitted inventory and sealed target attestation are `NOT_AVAILABLE`, while official schedule/code pins are `READY`. Protected preflight remains blocked.
- **E2E scheduling:** PREOPEN_CA is 08:30/08:45/08:55 WIB, PREOPEN is 09:03/09:13/09:22, and POST_EOD is 18:35/19:05/19:35. The historical 2026-08-27 POST_EOD result was `FAILED / NOT SALVAGED`; no manual rerun or backfill is authorized. The runtime contract is `PRESERVE_FROZEN_SCIENCE_DECOUPLE_RUNTIME`; watchdog trigger proof (`PRODUCTION_PROVEN`) is separate from capture proof.
- **Cloudflare:** local version-byte preparation and dry-runs pass; `CLOUDFLARE_PRODUCTION_PREPARED_NONAUTOMATIC` is preparation evidence only, and active readiness requires the same attested Version at 100%. Production remains inert and Windows V1 remains the automatic controller.
- **Stockbit Stream:** isolated smoke produced 5/5 `OK`, 150 normalized posts, and `DATA_READY` under a throwaway R2 prefix; genuine scheduled top-200 proof remains pending.
- **Safety boundary:** do not infer dates or negative authority, access protected outcomes, refit or score V4-X1, mutate counters, rewrite canonical data, backfill, deploy, or add an unreviewed adapter.

## Branch and history discipline

- Prefer one material branch per current lane and use commits within that lane for minor cycles.
- Create an independent audit branch only when independence is meaningful for a scientific or destructive gate.
- Close stale PRs when their conclusion is final; use archive tags and tombstones for historical recovery.
- A branch deletion is not runtime retirement; verify workflows and scheduled tasks separately.
- Keep the live remote branch set well below 100 and run hygiene before it becomes architectural documentation.

## Current project decision

The project is in system-completion mode, not model-search mode.

```text
canonical data capture
    ↓
EOD clean scoring
    ↓
Decision V2
    ↓
Sizing V1
    ↓
Execution V1
    ↓
Official IDX OpenPrice admission
    ↓
CA/accounting safety
    ↓
restart/idempotency-tested cloud paper orchestrator
    ↓
prospective paper portfolio
    ↓
whole-stack evaluation
```

Sizing remains **10% per seat/name, maximum 10 seats**. If fewer names qualify, keep residual cash; do not renormalize the remaining names upward.

Do not reopen Decision research, Path Risk rescue work, probability/payoff rescue work, rejected historical source work, or new alpha experiments merely because E2E integration exposes operational inconvenience.

## Next authorized coordination actions

- **E2E cloud-first:** wait for the next genuine scheduled POST_EOD and verify the resulting cloud evidence. Do not manually rerun or backfill 2026-08-27.
- **Stockbit Intraday:** observe the first eligible cloud post-EOD cycle. Keep the Windows fallback available and restore it only through the documented reversible path if cloud proof fails.
- **Capture hygiene:** apply the merged `CAPTURE_RUNTIME_HYGIENE_V3_APPLY.md` contract in a local tag-capable environment, then verify protected refs and workflow bytes. Keep PR #36 and current intraday/E2E branches untouched.
- **Forward evaluation:** keep PR #89 separate; do not materialize protected targets or mutate counters, runtime, schedulers, or outcomes.

Historical PIT, ownership/free-float, market-breadth, old CA, O2, Stage3/4/5, Decision intermediate, and rejected source experiments remain archived or tombstoned. Recover them only through `archive/hygiene-v2/*` evidence when forensic reconstruction is required.
