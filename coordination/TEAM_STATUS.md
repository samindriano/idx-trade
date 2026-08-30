# IDX Trade — Repository-Wide Team Status

Last coordinated update: 2026-08-27 Asia/Jakarta
Canonical location: `main:coordination/TEAM_STATUS.md`

## Authority

This is the **single live cross-chat coordination ledger** for `samindriano/idx-trade`.

- The canonical copy is always `origin/main:coordination/TEAM_STATUS.md`.
- Branch-local checkpoints/specs remain authoritative for scientific contracts and frozen gates.
- This file coordinates **current ownership and next work only**. Historical experiments do not belong here after closure; use checkpoints, tombstones, PR history, and archive tags.
- Before material work, read this file, inspect the controlling checkpoint for the target lane, and avoid duplicating another `ACTIVE` scope.
- A coordination-only commit directly to `main` is permitted for this file. Implementation/research changes stay on their own branches.

Status vocabulary: `PLANNED`, `ACTIVE`, `AUTOMATED`, `WAITING`, `BLOCKED`, `REVIEW`, `DONE`, `PARKED`.

---

## Repository baseline after Hygiene V2

Repository Hygiene V2 completed on 2026-08-22.

- pre-cleanup remote branches: **274**
- retained live branches: **50**
- removed remote branches: **224**
- exact historical branch heads preserved as archive tags: **45**
- tombstone/redundant branch removals: **179**
- destructive update mode: **one atomic remote ref transaction**
- authorized plan SHA-256: `40c3c21e565fa61344ba55675e67d564fc680a016a7729b0e28e768b4f0bbd8f`
- deletion-plan tag: `archive/hygiene-v2/deletion-plan-40c3c21e565fa613`
- cleanup implementation branch: `chore/repository-hygiene-v2-aggressive`
- cleanup implementation HEAD: `359ec2ca7477ba524be7db31f3f3e34da5b74661`

**Rule after V2:** do not recreate historical experiment branches merely for convenience. Recover exact old code from an archive tag when needed; otherwise use the durable tombstone/checkpoint conclusion.

Capture/runtime terminology is now governed by `docs/repository_hygiene/CAPTURE_RUNTIME_REGISTRY_V1.md`: only Official Open, EOD Market, Corporate Actions, Stockbit Stream, and Stockbit Intraday are canonical capture families. Derived sidecars are not separate collectors.

---

## Current critical path

| Lane | Status | Canonical branch / anchor | Current boundary / next action |
|---|---|---|---|
| V4-X1 Clean alpha | `DONE` | `research/idx-v4-x1-clean-historical-oos-replay-v1`; `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1` | Alpha science is frozen. Do not retune V4-X1 as part of downstream engineering. |
| Research Integrity / Data QA Gate V1 | `ACTIVE` | PR #103 `audit/research-integrity-data-qa-gate-v1@db97ad38`; stacked PR #108 `data/ca-aware-feature-basis-remediation-v1@b159870d` | INC-001/V1.1 retained-evidence decomposition is complete for all 47 `UNRESOLVED_OPERATIONAL_LABEL` events. Artifact `D:\Documents\Project\idx-ca-operational-label-decomposition-20260830-v1` manifest `4a540a73`; all 47 remain `SEMANTIC_INSUFFICIENT` because retained KSEI `Voluntary Conversion` rows have no ratio/receiving-security economics. V14 remains the controlling predecessor: 412/387/160/181/46 and 27 proven linkages. The retained-evidence triage for the remaining 50 events is complete at `51e3d7c6`: artifact `D:\Documents\Project\idx-ca-retained-evidence-triage-20260830-v1` manifest `0422948682e849022bc31ff0c93e0029e7a4db5f66566cf0e2a69d65ad6bdd86`; 43 `NO_RETAINED_EVENT_SPECIFIC_OFFICIAL_DOCUMENT`, 3 `RETAINED_OFFICIAL_DOCUMENT_SEMANTIC_INSUFFICIENT`, and 4 `TAXONOMY_ADJUDICATION_REQUIRED`. A single bounded official-source wave for exactly 18 standardized distribution events (BONUS_SHARES 11, STOCK_DIVIDEND 7) is complete: controlling acquisition artifact `D:\Documents\Project\idx-ca-official-distribution-acquisition-20260830-v4-final` manifest `33297117036972e91609f635175a3cce88aeada6a94b0c637edf1cf81a700c0d`; 3 `RESOLVED_EXACT`, 5 `OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE`, 5 `NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED`, and 5 `PROVIDER_DISCOVERY_FAILURE`. The fail-closed V15 successor at `D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v15-distribution-wave` manifest `d5a4a21beb2f065502fef3899b3a4f4f7204e0fbbed6f05ae7f4a0119fed6025` changes only transitions: 412/387/163/178/46 and 27 linkages; no new linkage. The 15 remaining distribution events stay unresolved. The exact-four-event `TRUE_SECURITY_CONVERSION` pass is complete at lane `b159870d`: controlling acquisition artifact `D:\Documents\Project\idx-ca-official-security-conversion-acquisition-20260830-v2` manifest `108e89f5145364ae1e348e8c8baec9ca5035b4f5e8f7821ff84531b387224f11`; 0 `RESOLVED_EXACT`, 1 `OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT` (MFIN), and 3 `OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE` (ASSA, PACK, KAEF). V15 remains unchanged at 412/387/163/178/46 and 27 linkages; all four conversion events remain unresolved. Historical negative/as-of/complete-interval authority remains unsupported or unknown; DATA/RESEARCH admission remains blocked. No Phase-E, outcomes, model work, refit/scoring, counter mutation, canonical rewrite, runtime change, production execution, backfill, or merge is authorized. Retained-evidence-only taxonomy adjudication is active for exactly four `UNKNOWN_TAXONOMY` KSEI `Mixed Dividend` rows (CNMA, KKGI, WINS x2); no provider acquisition is authorized. |
| EOD Market Capture + prospective V4-X1 scoring | `REVIEW` | accepted E2E integration `integration/idx-e2e-baseline-paper-v1@043003ee`; clean scorer lineage retained in history | Canonical post-close Stock EOD/OHLCV, official IDX Index Summary context, and scoring are present in the accepted E2E POST_EOD lineage. The old `data/market-index-forward-eod-v1-monitoring` branch was independently compared and is now superseded by a stricter accepted implementation; preserve its exact head as forensic history, then remove its live branch ref. Windows remains fallback until first genuine cloud proof. |
| 100-session prospective alpha evaluation | `REVIEW` | `research/idx-forward-evaluation-protocol-v1`; `codex/idx-forward-100-evaluator-v1`; `research/idx-v4-x1-prospective-evaluation-protocol-v1`; merged PR #83 (`bd251c1c`); merged pre-access readiness/adapter PR #88 (`68894b97`); completion PR #89 `ops/v4-x1-preaccess-artifact-completion-v1` @ `1c4c6d17` | Frozen evaluator/access-gate science remains unchanged. Outcome-blind readiness core plus production adapters are merged. Real production score evidence remains `2/100`; runtime counter remains `2/100`; official schedule and independently anchored code pins are `READY`; canonical admitted 100-session inventory and sealed target attestation remain `NOT_AVAILABLE`; real protected preflight remains blocked. PR #89 remains a separate evaluation-completion lane; do not mix it with capture cleanup. |
| Decision policy | `DONE` | `research/idx-decision-v2-minimal-implementation-v1`; `research/idx-decision-economic-comparison-v1`; final closure `audit/idx-decision-v4-refill-decoupling-result-v1` | **Decision V2 is frozen incumbent. Decision research on this 600-session development set is CLOSED.** No V4.1/V5/rescue search. |
| Sizing + Execution + CA-aware paper foundations | `DONE` | `integration/forward-ca-attestation-v1`; `data/idx-v4-corporate-action-continuity-gate-v1`; `integration/idx-v4-ca-target-continuity-bridge-v1` | Frozen Sizing V1 and Execution V1 plus cash-dividend/persistent CA-aware state foundations are retained. Unsupported CA remains fail-closed. Corporate Action Capture is part of this integrated path, not a second standalone collector. |
| E2E Baseline Paper V1 integration | `ACTIVE` | `integration/idx-e2e-baseline-paper-v1@043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2` | Accepted Decision V2 → Sizing V1 → Execution V1, execution-grade Official IDX OpenPrice, EOD/CA-aware persistent state, and cloud-first adapter are now in the integration lineage. Windows paper/EOD paths remain fallback only until cloud live proof. No retroactive capture or protected-outcome access. |
| E2E Paper cloud-first orchestration | `ACTIVE` | main workflow `.github/workflows/e2e-paper-cloud-orchestration.yml` activation main `1eaf79c3f949a65346b064521ecb93a14d39b688`; implementation pin `6b6a41114a910287b413a099a36d59c5e057a8f2`; input bridge `ops/e2e-paper-cloud-input-provisioning-v1@13cd07af` | Production workflow now invokes V3. Path-A population compatibility gate, Security Master continuity, and runtime tradability bootstrap are active under `PRESERVE_FROZEN_SCIENCE_DECOUPLE_RUNTIME`. PREOPEN_CA retries run at 08:30/08:45/08:55 WIB, PREOPEN retries remain 09:03/09:13/09:22, and POST_EOD retries remain 18:35/19:05/19:35. PREOPEN_CA, PREOPEN, and POST_EOD use isolated concurrency groups; the V3 09:02 cutoff remains fail-closed. 2026-08-27 prospective POST_EOD: **FAILED / NOT SALVAGED**. Watchdog fallback: **PRODUCTION_PROVEN**. Next acceptance gate: **future genuine scheduled POST_EOD**. No manual rerun or backfill is authorized. No live production proof or Cloudflare production fallback activation is claimed yet. |
| Stockbit Intraday cloud migration | `ACTIVE` | main workflow `.github/workflows/stockbit-intraday-cloud-production.yml` activation baseline `53767b2b`; merged PR #95 implementation plus PR #105 production schedule | PR #95, PR #104, and PR #105 are merged. Isolated R2 smoke `32992195295` and read-only E2E bridge preflight `32992458786` passed. Production schedule is enabled at 18:30/19:30/20:30 Asia/Jakarta. The Windows fallback task definition remains available, while the exact automatic task `IDX-Trade Stockbit Intraday Daily` is reversibly disabled during cloud proof to prevent dual writes; rollback: `Enable-ScheduledTask -TaskName 'IDX-Trade Stockbit Intraday Daily' -TaskPath '\'`. First genuine post-EOD production proof is still pending. |
| Capture/runtime repository hygiene V3 | `WAITING` | merged PR #94 at `ab285091ba5e757a21501e389e5456d37ad43949`; apply contract `docs/repository_hygiene/CAPTURE_RUNTIME_HYGIENE_V3_APPLY.md` | Registry is merged after exact-head CI `223 passed, 4 warnings`. Ten merged/contained heads are branch-ref redundant; four graph-unique but superseded heads have temporary exact-head forensic refs. Market/Index EOD audit is closed in favor of the hardened accepted E2E implementation. Destructive ref cleanup now requires a local/tag-capable atomic Git apply; current connected GitHub surface cannot create/delete tag refs or delete branches. Open Stockbit red-team PR #36 remains protected. No runtime/scheduler deletion in this lane. |

---

## Canonical capture surface

The project recognizes exactly these acquisition families:

1. **Official Open Capture** — IDX `OpenPrice`, GitHub Actions -> private R2, strict downstream admission.
2. **EOD Market Capture** — one post-close transaction containing Stock EOD/OHLCV plus Market/Index EOD context.
3. **Corporate Action Capture** — official prospective CA evidence integrated with CA-aware E2E accounting/execution.
4. **Stockbit Stream Capture** — default-branch GitHub Actions -> private R2.
5. **Stockbit Intraday Capture** — post-close intraday capture/reconstruction; the main GitHub/R2 workflow is scheduled for 18:30/19:30/20:30 Asia/Jakarta, while the retained Windows task definition is disabled during the first cloud proof to enforce single-writer operation.

Foreign flow, price/trend, reliability/uncertainty, model scoring, Decision, Sizing, Execution, and PaperState are derived/consumer layers, not additional canonical capture systems.

---

## Always-on / operational lanes

| Lane | Status | Canonical anchor | Boundary |
|---|---|---|---|
| Official Open Capture | `AUTOMATED` | default-branch `.github/workflows/official-open-prospective-cloud-capture.yml`; accepted implementation SHA pinned by deployment contract | GitHub Actions -> private R2 `official-open-v1`. Legacy generic Forward Open is not execution authority. |
| Stockbit Stream Capture | `ACTIVE` | `main` workflow/runtime; independent audit `audit/stockbit-stream-v2-red-team-v1` PR #36 remains open/draft | Production workflow is on `main`, not old base/remediation branch chain. Long-term R2 retention is active and verified. Do not delete PR #36 branch until audit closure/integration. |
| Stockbit Intraday Capture | `ACTIVE` | main workflow `.github/workflows/stockbit-intraday-cloud-production.yml` at activation baseline `53767b2b`; Windows fallback `fix/stockbit-intraday-postclose-fix-v1` | Cloud schedule is enabled for 18:30/19:30/20:30 Asia/Jakarta after merged implementation, isolated R2 smoke, and read-only bridge preflight. The Windows fallback remains retained but its exact automatic task is reversibly disabled during cloud proof; the failed 2026-08-27 E2E POST_EOD was not salvaged and no genuine cloud capture proof exists. |
| EOD Market Capture | `REVIEW` | accepted E2E POST_EOD path `043003ee` | Stock EOD/OHLCV and official Market/Index context are one canonical transaction. Old Market/Index branch head `8c94f56b...` is superseded and forensic-only; do not build a second provider/canonical hierarchy. |
| Corporate Action Capture | `ACTIVE` | accepted E2E/forward-CA lineage | Integrated CA acquisition/attestation; verify first genuine cloud cycle before retiring local fallback. |
| Legacy Forward Open scaffold | `PARKED` | historical head `dc5e84b589eebe040119f48f9f69538d398a9d36` | PR #12 closed unmerged, source never frozen/execution-grade, superseded by Official Open. Archive exact head then delete live branch ref. |
| Frontend monitoring | `PARKED` | `frontend/v4x-v2-monitoring-refresh-v1` | Viewer/ops surface only; preserve historical model/score/hover visibility. |

---

## Parallel retained research/data lanes

These branches are retained because they contain reusable work, but **none may silently become a prerequisite or modify frozen V4-X1/Decision V2**.

| Domain | Status | Retained anchors | Boundary |
|---|---|---|---|
| Financial PIT / representation | `PARKED` | `research/idx-financial-pit-alpha-v1`; `research/idx-financial-representation-v2` | Resume only as separately scoped challenger work. |
| Foreign flow | `PARKED` | `research/idx-foreign-flow-alpha-v2-core`; `research/idx-foreign-flow-representation-v2`; `integration/foreign-flow-representation-v2-forward-v1`; capture/acquisition history | Treat forward representation as a derived sidecar over canonical Stock Summary raw unless a future acquisition contract explicitly changes that. No silent admission into incumbent alpha. |
| Price/trend state | `PARKED` | `research/idx-price-trend-confirmation-state-v1`; `integration/price-trend-state-forward-sidecar-v1`; `integration/price-trend-runtime-bridge-adapter-v1` | Derived sidecar/challenger only. |
| Reliability / uncertainty | `WAITING` | `research/idx-reliability-uncertainty-v1-forward-shadow` | Derived forward sidecar evidence only; not alpha or Decision input by default. |
| Historical/open/price-basis remediation | `PARKED` | `data/idx-open-official-stock-summary-recovery-v1`; `data/tradingview-historical-price-path-v2-1-remediation`; `data/price-basis-remediation-v1`; `research/price-basis-clean-refit-v1` | Historical evidence only. Do not revive rejected approximate executable-Open/intraday sources as production collectors. |
| Personal KSEI | `PARKED` | `integration/personal-ksei-bounded-auth-design-v1` | Private authenticated observation/reconciliation only; no credentials in repo/browser and no implied broker order routing. |

Historical PIT sector, ownership/free-float, market-breadth, old CA, O2, Stage3/4/5, Decision V1/V3/V4 intermediates, and rejected intraday/source experiments were deliberately archived or tombstoned by Hygiene V2. Recover via `archive/hygiene-v2/*` evidence only when forensic reconstruction is genuinely required.

---

## Current project decision

The project is in **system-completion mode**, not model-search mode.

Canonical operational ordering:

```text
canonical data capture
    ↓
EOD clean scoring
    ↓
Decision V2
    ↓
Sizing V1 (fixed ~10% per seat; residual cash allowed)
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

Baseline sizing remains **10% per seat/name, maximum 10 seats**. If fewer names qualify, keep residual cash; do not renormalize remaining names upward merely to reach 100% exposure.

Do not reopen Decision research, Path Risk rescue work, probability/payoff rescue work, rejected historical source work, or new alpha experiments merely because E2E integration exposes operational inconvenience.

---

## Hygiene / branch-creation discipline going forward

1. Prefer **one material branch per current lane**, not a new branch for every minor audit/checkpoint.
2. Use commits/checkpoints on the same lane while scope and scientific contract remain unchanged.
3. Create a separate audit branch only when independence actually matters for a scientific/destructive gate.
4. Close stale PRs when their verdict is final; do not use open PRs as an archive.
5. When a lane is closed, preserve the durable conclusion in docs and archive-tag only genuinely valuable exact code heads.
6. Before opening a new lane, check whether a retained branch already contains the required code.
7. A branch deletion is not runtime retirement; verify workflow checkout refs and local scheduled tasks separately.
8. Target repository steady state: well below 100 live remote branches; run hygiene before clutter becomes architectural documentation.

---

## Next authorized coordination actions

For E2E cloud-first: after the failed and unsalvaged 2026-08-27 prospective POST_EOD, the next acceptance gate is a future genuine scheduled POST_EOD on the repinned main workflow, followed by verification of the resulting cloud evidence. Keep Windows fallbacks unchanged unless a separately approved single-writer cutover requires reversible suppression. Do not manually rerun or backfill 2026-08-27.

For Stockbit Intraday: observe the first eligible production post-EOD cloud cycle after the merged schedule. The Windows 18:30/19:30/20:30 task definition is retained and currently disabled reversibly so it cannot issue duplicate provider calls during cloud proof; re-enable with the recorded rollback command only if cloud proof fails and fallback is explicitly restored. Do not backfill missed sessions.

For capture hygiene: use the merged `CAPTURE_RUNTIME_HYGIENE_V3_APPLY.md` contract from `main@ab285091...` in a clean local/tag-capable Git environment. Convert the four temporary exact-head forensic refs (Forward Open scaffold, Stockbit V1 base, Stockbit observable smoke, Market/Index EOD) to permanent archive tags; atomically remove only the 10 certified merged/contained branches, the four certified superseded source branches, and the four temporary archive branch refs; then verify protected refs and workflow bytes are unchanged. If atomic push is unsupported or any expected SHA moved, stop fail-closed. Keep PR #36 and current intraday/E2E branches untouched.

In parallel, keep PR #89 as a separate forward-evaluation completion lane; do not materialize protected targets, mutate counters/runtime/schedulers, or mix evaluation-science changes into capture/runtime cleanup.
