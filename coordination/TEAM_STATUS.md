# IDX Trade — Repository-Wide Team Status

Last coordinated update: 2026-08-26 00:18 Asia/Jakarta
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

---

## Current critical path

| Lane | Status | Canonical branch / anchor | Current boundary / next action |
|---|---|---|---|
| V4-X1 Clean alpha | `DONE` | `research/idx-v4-x1-clean-historical-oos-replay-v1`; `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1` | Alpha science is frozen. Do not retune V4-X1 as part of downstream engineering. |
| Fresh EOD + prospective V4-X1 scoring | `BLOCKED` | `integration/v4-x1-clean-prospective-score-v1`; `integration/v4-x1-eod-auto-score-v1`; `integration/forward-eod-automation-monitoring` | Science/runtime preparation exists. Last deployment attempt failed closed at Windows Administrator requirement before scheduler mutation. Resolve as operational deployment work only; no retroactive prospective scoring. |
| 100-session prospective alpha evaluation | `REVIEW` | `research/idx-forward-evaluation-protocol-v1`; `codex/idx-forward-100-evaluator-v1`; `research/idx-v4-x1-prospective-evaluation-protocol-v1`; merged PR #83 (`bd251c1c`); review lane `ops/v4-x1-prospective-preaccess-readiness-v1` @ `0d125e66` | Frozen evaluator/access-gate science remains unchanged. Outcome-blind readiness core plus production adapters are review-ready: real production score evidence is `2/100`; runtime counter reconciles `2/100`; official schedule and independently anchored code pins are `READY`; raw production score shape is intentionally **not** gate-admitted; `canonical_admitted_gate_inventory_sha256` remains `NOT_AVAILABLE`; target/PaperState/benchmark/prior-access attestations remain missing. Overall is `ACCUMULATING_OUTCOME_BLIND`. Next action: rebase/reconcile against latest `main`, open a clean PR, obtain CI on the exact head, and independently review before merge. No real score projection, target materialization, counter mutation, protected outcome access, or protected-loader authorization is permitted by this review state. |
| Decision policy | `DONE` | `research/idx-decision-v2-minimal-implementation-v1`; `research/idx-decision-economic-comparison-v1`; final closure `audit/idx-decision-v4-refill-decoupling-result-v1` | **Decision V2 is frozen incumbent. Decision research on this 600-session development set is CLOSED.** V4 refill-decoupling structurally rejected; no V4.1/V5/rescue or V4 economic comparison. |
| Sizing + Execution + CA-aware paper foundations | `DONE` | `integration/forward-ca-attestation-v1`; `data/idx-v4-corporate-action-continuity-gate-v1`; `integration/idx-v4-ca-target-continuity-bridge-v1` | Frozen Sizing V1 and Execution V1 plus cash-dividend/persistent CA-aware state foundations are retained. Unsupported CA remains fail-closed. |
| E2E Baseline Paper V1 integration | `ACTIVE` | `integration/idx-e2e-baseline-paper-v1`; integrated HEAD `b5265295` (PR #87) | Decision V2 → Sizing V1 and Decision V2 → Execution V1 adapters are accepted. Execution-grade official IDX `OpenPrice` evidence is accepted with `DIRECT_IDX_THEN_ZAPI_RAW_V1`. PR #85 (Open runtime hardening), PR #86 (outcome-blind evidence-health audit), and PR #87 (read-only session audit / missed-execution continuity hardening) are merged into the integration lineage. Windows task `IDXTrade-E2E-OfficialOpen` remains the active scheduled path. First genuine weekday same-session capture remains pending; no retroactive capture or protected-outcome access is authorized. |

---

## Always-on / operational lanes

| Lane | Status | Canonical branch | Boundary |
|---|---|---|---|
| Stockbit Stream prospective archive | `ACTIVE` | `data/stockbit-stream-prospective-archive-v1`; remediation head `fix/stockbit-stream-zapi-envelope-v1`; audit `audit/stockbit-stream-v2-red-team-v1`; retention remediation `fix/stockbit-r2-retention-v1` | Prospective archive only. No historical backfill/model/outcome use without a separate contract. PR #35/#36 heads intentionally retained. Long-term R2 retention is active and GET-verified: raw, normalized, manifests, and universe_inputs are retained indefinitely; no Stockbit-prefix delete rule remains; unrelated multipart-abort rule is preserved. |
| Stockbit intraday post-close capture | `AUTOMATED` | `fix/stockbit-intraday-postclose-fix-v1` | Scheduler moved to EOD-aligned post-close windows; do not invent retroactive captures for missed sessions. |
| Market/index forward EOD | `AUTOMATED` | `data/market-index-forward-eod-v1-monitoring` | Keep operational monitoring separate from alpha promotion. |
| Forward Open archive | `AUTOMATED` | `ops/idx-forward-open-archive-v1` | Legacy/generic archive retained as historical operational evidence; do not treat it as the E2E execution-grade Open source. The separate E2E official `OpenPrice` sidecar is now deployed and uses explicit direct-IDX → Zapi-raw transport redundancy. |
| Frontend monitoring | `PARKED` | `frontend/v4x-v2-monitoring-refresh-v1` | Viewer/ops surface only; backend E2E completion takes priority. Preserve historical model/score/hover visibility. |

---

## Parallel retained research/data lanes

These branches are retained because they contain current reusable work, but **none may silently become a prerequisite or modify frozen V4-X1/Decision V2**.

| Domain | Status | Retained anchors | Boundary |
|---|---|---|---|
| Financial PIT / representation | `PARKED` | `research/idx-financial-pit-alpha-v1`; `research/idx-financial-representation-v2` | Resume only as a separately scoped alpha/data challenger after baseline E2E or explicit user reprioritization. |
| Foreign flow | `PARKED` | `research/idx-foreign-flow-alpha-v2-core`; `research/idx-foreign-flow-representation-v2`; `integration/foreign-flow-representation-v2-forward-v1`; capture/acquisition branches | Existing representation/capture work preserved. No silent admission into incumbent alpha. |
| Price/trend state | `PARKED` | `research/idx-price-trend-confirmation-state-v1`; `integration/price-trend-state-forward-sidecar-v1`; `integration/price-trend-runtime-bridge-adapter-v1` | Sidecar/challenger only unless separately promoted. |
| Reliability / uncertainty | `WAITING` | `research/idx-reliability-uncertainty-v1-forward-shadow` | Forward sidecar evidence only; not alpha or Decision input by default. |
| Historical/open/price-basis remediation | `PARKED` | `data/idx-open-official-stock-summary-recovery-v1`; `data/tradingview-historical-price-path-v2-1-remediation`; `data/price-basis-remediation-v1`; `research/price-basis-clean-refit-v1` | Keep accepted source/lineage improvements; do not reopen rejected historical-source experiments without new preregistration. |
| Personal KSEI | `PARKED` | `integration/personal-ksei-bounded-auth-design-v1` | Private authenticated observation/reconciliation only; no credentials in repo/browser and no implied broker order routing. |

Historical PIT sector, ownership/free-float, market-breadth, old CA, O2, Stage3/4/5, Decision V1/V3/V4 intermediates, and rejected intraday/source experiments were deliberately archived or tombstoned by Hygiene V2. Recover via `archive/hygiene-v2/*` tags only when forensic reconstruction is genuinely required.

---

## Current project decision

The project is now in **system-completion mode**, not model-search mode.

Canonical ordering:

```text
repository/documentation consolidation
    ↓
fresh V4-X1 scoring deployment
    ↓
prospective Decision V2 shadow
    ↓
Sizing V1 (fixed ~10% per seat; residual cash allowed)
    ↓
Execution V1
    ↓
official IDX OpenPrice evidence / execution admission
    ↓
CA/accounting safety
    ↓
restart/idempotency-tested paper orchestrator
    ↓
prospective paper portfolio
    ↓
whole-stack evaluation
```

Baseline sizing remains **10% per seat/name, maximum 10 seats**. If fewer names qualify, keep residual cash; do not renormalize remaining names upward merely to reach 100% exposure.

Do not reopen Decision research, Path Risk rescue work, probability/payoff rescue work, or new alpha experiments merely because E2E integration exposes operational inconvenience.

---

## Hygiene / branch-creation discipline going forward

1. Prefer **one material branch per current lane**, not a new branch for every minor audit/checkpoint.
2. Use commits/checkpoints on the same lane while scope and scientific contract remain unchanged.
3. Create a separate audit branch only when independence actually matters for a scientific/destructive gate.
4. Close stale PRs when their verdict is final; do not use open PRs as an archive.
5. When a lane is closed, preserve the durable conclusion in docs and archive-tag only genuinely valuable exact code heads.
6. Before opening a new lane, check whether a retained branch already contains the required code.
7. Target repository steady state: **well below 100 live remote branches**; if branch count starts trending materially upward, perform hygiene before adding more experiments.

---

## Next authorized coordination action

Continue `integration/idx-e2e-baseline-paper-v1` as the single primary E2E runtime lane and observe the first genuine weekday same-session capture without forcing or retroactively filling evidence. In parallel, complete review/integration of `ops/v4-x1-prospective-preaccess-readiness-v1` @ `0d125e66`: rebase/reconcile against current `main`, open a clean PR, obtain CI on the exact final head, and do not merge until independent review. While that review is pending, any follow-on pre-access artifact-completion work must remain on a separate dependent branch and stay outcome-blind: no protected target reads, no target materialization, no counter/runtime/scheduler mutation, no protected loader, and no silent modification of the frozen evaluator/gate science.