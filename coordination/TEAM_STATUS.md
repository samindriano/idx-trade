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
| Research Integrity / Data QA Gate V1 | `REVIEW` | `audit/research-integrity-data-qa-gate-v1` | Phase-1 framework validation/hardening passed (21 focused, 260 full). INC-001 historical CA/price-basis HEAVY QA is materially blocked: DATA_ADMISSION=FAIL, RESEARCH_ADMISSION=FAIL, MODEL_PROMOTION=NOT_EVALUATED. Incident is CONFIRMED/NOT_CLOSED. No V4-X1 refit, outcome access, counter mutation, capture/runtime change, historical CA remediation, or science rescue is authorized. Await independent review. |
| EOD Market Capture + prospective V4-X1 scoring | `REVIEW` | accepted E2E integration `integration/idx-e2e-baseline-paper-v1@043003ee`; clean scorer lineage retained in history | Canonical post-close Stock EOD/OHLCV, official IDX Index Summary context, and scoring are present in the accepted E2E POST_EOD lineage. The old `data/market-index-forward-eod-v1-monitoring` branch was independently compared and is now superseded by a stricter accepted implementation; preserve its exact head as forensic history, then remove its live branch ref. Windows remains fallback until first genuine cloud proof. |
| 100-session prospective alpha evaluation | `REVIEW` | `research/idx-forward-evaluation-protocol-v1`; `codex/idx-forward-100-evaluator-v1`; `research/idx-v4-x1-prospective-evaluation-protocol-v1`; merged PR #83 (`bd251c1c`); merged pre-access readiness/adapter PR #88 (`68894b97`); completion PR #89 `ops/v4-x1-preaccess-artifact-completion-v1` @ `1c4c6d17` | Frozen evaluator/access-gate science remains unchanged. Outcome-blind readiness core plus production adapters are merged. Real production score evidence remains `2/100`; runtime counter remains `2/100`; official schedule and independently anchored code pins are `READY`; canonical admitted 100-session inventory and sealed target attestation remain `NOT_AVAILABLE`; real protected preflight remains blocked. PR #89 remains a separate evaluation-completion lane; do not mix it with capture cleanup. |
| Decision policy | `DONE` | `research/idx-decision-v2-minimal-implementation-v1`; `research/idx-decision-economic-comparison-v1`; final closure `audit/idx-decision-v4-refill-decoupling-result-v1` | **Decision V2 is frozen incumbent. Decision research on this 600-session development set is CLOSED.** No V4.1/V5/rescue search. |
| Sizing + Execution + CA-aware paper foundations | `DONE` | `integration/forward-ca-attestation-v1`; `data/idx-v4-corporate-action-continuity-gate-v1`; `integration/idx-v4-ca-target-continuity-bridge-v1` | Frozen Sizing V1 and Execution V1 plus cash-dividend/persistent CA-aware state foundations are retained. Unsupported CA remains fail-closed. Corporate Action Capture is part of this integrated path, not a second standalone collector. |
| E2E Baseline Paper V1 integration | `ACTIVE` | `integration/idx-e2e-baseline-paper-v1@043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2` | Accepted Decision V2 → Sizing V1 → Execution V1, execution-grade Official IDX OpenPrice, EOD/CA-aware persistent state, and cloud-first adapter are now in the integration lineage. Windows paper/EOD paths remain fallback only until cloud live proof. No retroactive capture or protected-outcome access. |
| E2E Paper cloud-first orchestration | `REVIEW` | input provisioning `ops/e2e-paper-cloud-input-provisioning-v1@13cd07af`; implementation `integration/idx-e2e-baseline-paper-v1@043003ee`; launcher `ops/e2e-paper-cloud-launcher-v1@32a63ff4` | Offline manifest and all 10 required child hashes validated; schedule/model bundle validation passed. ConditionalS3 smoke and production `e2e-paper-v1/inputs` provisioning are currently blocked because local R2 credential values are unavailable to that worktree. No provider/R2 production bundle, scheduler activation, model, outcome, counter, or live E2E cycle was touched. |
| Stockbit Intraday cloud migration | `ACTIVE` | draft PR #95 `ops/stockbit-intraday-cloud-migration-v1` | Legacy Windows post-close capture remains operational fallback. Recovery correctness, immutable slot snapshots, conditional-write storage, final-manifest semantic admission, read-only accepted-E2E bridge, isolated R2-smoke tooling, and read-only preflight are being staged on PR #95. No GitHub schedule, production `stockbit-intraday-v1` write, live provider call, retroactive capture, synthetic fill, outcome access, or Windows retirement is authorized yet. Next gates: exact-head CI, isolated throwaway R2 smoke, read-only bridge preflight, then one controlled future-session proof. |
| Capture/runtime repository hygiene V3 | `WAITING` | merged PR #94 at `ab285091ba5e757a21501e389e5456d37ad43949`; apply contract `docs/repository_hygiene/CAPTURE_RUNTIME_HYGIENE_V3_APPLY.md` | Registry is merged after exact-head CI `223 passed, 4 warnings`. Ten merged/contained heads are branch-ref redundant; four graph-unique but superseded heads have temporary exact-head forensic refs. Market/Index EOD audit is closed in favor of the hardened accepted E2E implementation. Destructive ref cleanup now requires a local/tag-capable atomic Git apply; current connected GitHub surface cannot create/delete tag refs or delete branches. Open Stockbit red-team PR #36 remains protected. No runtime/scheduler deletion in this lane. |

---

## Canonical capture surface

The project recognizes exactly these acquisition families:

1. **Official Open Capture** — IDX `OpenPrice`, GitHub Actions -> private R2, strict downstream admission.
2. **EOD Market Capture** — one post-close transaction containing Stock EOD/OHLCV plus Market/Index EOD context.
3. **Corporate Action Capture** — official prospective CA evidence integrated with CA-aware E2E accounting/execution.
4. **Stockbit Stream Capture** — default-branch GitHub Actions -> private R2.
5. **Stockbit Intraday Capture** — post-close intraday capture/reconstruction; Windows runtime remains the live fallback while draft PR #95 stages bounded GitHub/R2 migration. Cloud scheduling is not active yet.

Foreign flow, price/trend, reliability/uncertainty, model scoring, Decision, Sizing, Execution, and PaperState are derived/consumer layers, not additional canonical capture systems.

---

## Always-on / operational lanes

| Lane | Status | Canonical anchor | Boundary |
|---|---|---|---|
| Official Open Capture | `AUTOMATED` | default-branch `.github/workflows/official-open-prospective-cloud-capture.yml`; accepted implementation SHA pinned by deployment contract | GitHub Actions -> private R2 `official-open-v1`. Legacy generic Forward Open is not execution authority. |
| Stockbit Stream Capture | `ACTIVE` | `main` workflow/runtime; independent audit `audit/stockbit-stream-v2-red-team-v1` PR #36 remains open/draft | Production workflow is on `main`, not old base/remediation branches. Long-term R2 retention is active and verified. Do not delete PR #36 branch until audit closure/integration. |
| Stockbit Intraday Capture | `ACTIVE` | live fallback `fix/stockbit-intraday-postclose-fix-v1`; migration draft PR #95 `ops/stockbit-intraday-cloud-migration-v1` | Windows 18:30/19:30/20:30 post-close runtime is retained as the current live path. PR #95 stages restart-safe conditional R2 durability and a pinned read-only E2E bridge. Do not activate cloud scheduling or run both automated paths concurrently until isolated smoke/preflight pass and the controlled future-session proof plan explicitly handles the Windows fallback. |
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

For E2E cloud-first: finish private R2 input provisioning and isolated ConditionalS3 smoke, then independently audit readback/preflight before activating PR #93 for one genuine future-session cloud proof. Keep Windows fallbacks until that proof passes. Do not backfill missed sessions.

For Stockbit Intraday: continue only on draft PR #95. Require exact-head CI, then run the dedicated isolated throwaway-prefix ConditionalS3 smoke and the read-only pinned-E2E bridge preflight. Do not activate a GitHub schedule or production `stockbit-intraday-v1` writes yet. Before the first genuine future-session cloud proof, define a single-writer operating plan so the existing Windows 18:30/19:30/20:30 tasks and cloud workflow cannot both issue provider calls for the same session. Keep the Windows implementation available for rollback until the cloud proof is accepted; do not backfill missed sessions.

For capture hygiene: use the merged `CAPTURE_RUNTIME_HYGIENE_V3_APPLY.md` contract from `main@ab285091...` in a clean local/tag-capable Git environment. Convert the four temporary exact-head forensic refs (Forward Open scaffold, Stockbit V1 base, Stockbit observable smoke, Market/Index EOD) to permanent archive tags; atomically remove only the 10 certified merged/contained branches, the four certified superseded source branches, and the four temporary archive branch refs; then verify protected refs and workflow bytes are unchanged. If atomic push is unsupported or any expected SHA moved, stop fail-closed. Keep PR #36 and current intraday/E2E branches untouched.

In parallel, keep PR #89 as a separate forward-evaluation completion lane; do not materialize protected targets, mutate counters/runtime/schedulers, or mix evaluation-science changes into capture/runtime cleanup.
