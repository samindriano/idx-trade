# IDX Trade — Repository-Wide Team Status

Last coordinated update: 2026-08-13 02:25 Asia/Jakarta
Canonical location: `main:coordination/TEAM_STATUS.md`

## Authority

This is the **single live cross-chat coordination ledger** for the entire `samindriano/idx-trade` repository.

- The canonical copy is always the one on `origin/main`.
- A copy on a feature branch is non-authoritative and may be stale.
- Scientific authorization still comes from the newest controlling branch-local spec/checkpoint. This file coordinates ownership/status and prevents duplicate work; it does not bypass research gates.

## Mandatory agent protocol

Before **starting, continuing, or proposing any material IDX-Trade work**, every ChatGPT/Codex agent must:

1. fetch/read the latest `origin/main:coordination/TEAM_STATUS.md`;
2. check whether another active task already owns the same scope;
3. if starting new material work, claim/update a task row before implementation;
4. update the row whenever a material checkpoint, blocker, verdict, branch, or ownership state changes;
5. update the row again when work becomes `REVIEW`, `DONE`, `PARKED`, `WAITING`, or `BLOCKED`.

No agent may duplicate an `ACTIVE` scope unless the user explicitly asks for independent/adversarial review.

### Safe shared-file update rule

This file is intentionally shared across branches/chats. On every write:

- refetch the latest `main` version first;
- preserve every other agent's row/change;
- change only the relevant task row(s) plus necessary global notes;
- never force-push or overwrite a newer version;
- on conflict, refetch and reapply the small status edit.

A coordination-only commit directly to `main` is permitted **only for this file** unless separately authorized. Feature/research implementation must remain on its own branch.

Suggested owner labels: `ChatGPT/<purpose>` or `Codex/<purpose>`.

Status vocabulary: `PLANNED`, `ACTIVE`, `AUTOMATED`, `WAITING`, `BLOCKED`, `REVIEW`, `DONE`, `PARKED`.

## Current live work / ownership

| Task / lane | Status | Owner | Branch / anchor | Current boundary / next action |
|---|---|---|---|---|
| O2 vs V2 common-support comparator | `DONE` | ChatGPT review + Codex | `research/idx-ranking-o2-v2-common-support-comparator-v1` / acceptance `a2c5666637f2e879ce107cd44fc2dae8cc22a5c5` | Historical-development evidence accepted; **do not rerun or extend automatically**. |
| Market / Index / Breadth History V1 | `PARKED` | ChatGPT review + Codex | `data/market-index-breadth-history-v1` / review `d3827f1506736ec64c957e10f50f5447196d9983` | `CONDITIONAL_SOURCE_READY_PIT_BLOCKED`; no historical PIT bulk acquisition/model use. |
| Stockbit intraday forward capture | `AUTOMATED` | Existing runtime | `data/stockbit-intraday-forward-capture-v1` | Daily capture infrastructure already exists. **Do not build it again.** Accumulate evidence for possible future Path Risk research. |
| Path Risk | `WAITING` | none | prior V1/V2 lineage | V1/V2 failed. Do not restart/retune now; wait for richer intraday accumulation and a genuinely new preregistered hypothesis family. |
| Probability V1 legacy calibration | `DONE` | prior research lineage | `research/idx-stage4-v1` + `research/idx-stage4b-calibration-v1` + `research/idx-stage5-ranking-holdout-v1` | Final status `PROBABILITY_V1_NOT_READY_DEFERRED`: Stage-4 and Stage-4B calibration readiness failed, and the Stage-5 ranking holdout was consumed for Ranking V1. Do not restart Probability V1 or reuse that holdout. Any future current-alpha/Probability V2 validation requires a new preregistered lane and fresh-forward data strictly after 2026-07-31. |
| Expected Payoff V0 feasibility | `DONE` | `ChatGPT independent review + Codex remediation` | `research/idx-expected-payoff-v0-feasibility` / `ecec6835eaee70f47a8a1c1b43fc2d14a4c34709` | `EXPECTED_PAYOFF_V0_FEASIBILITY_GO` accepted. Engineering/spec-compliance remediation reviewed complete; original one-shot verdict unchanged. Do not rerun/retune V0. |
| Expected Payoff V1 | `DONE` | `ChatGPT independent review + Codex remediation` | `research/idx-expected-payoff-v1` / correction `bc35d1c1d7d08ae3aa84c6e16200d20c1f279981` / acceptance `73b75af2322214138e55293a4bb2cb8ed4362c15` | Decision-valid `EXPECTED_PAYOFF_V1_NO_SURVIVOR` accepted after metric-only correction: median corrected MSE skill `-0.05217`, positive skill folds `0/6`; IC and D10-D1 ordering gates pass but cannot rescue conditional-mean failure. Exact V1 lane closed; no refit, tuning, alternate candidate, or forward shadow. |
| Reliability / Uncertainty V0 | `DONE` | `ChatGPT independent review + Codex` | `research/idx-reliability-uncertainty-v0` / result `1d01a1b` / acceptance `a99d53de91dfc44f9688ba7adead5206d7c7929d` | `RELIABILITY_V0_FEASIBILITY_GO_ACCEPTED`: only `score_margin_reliability` qualified, with positive Spearman/Q4-Q1/selective/conditional lift in 6/6 folds. `joint_marginal_support_reliability` failed and must not be rescued. V0 is closed; any V1 requires a separately frozen contract and fresh prospective validation. |
| Reliability / Uncertainty V1 forward shadow | `DONE` | `ChatGPT independent review + Codex remediation` | `research/idx-reliability-uncertainty-v1-forward-shadow` / remediation `4af006d` / acceptance `a21c2665f1afa73f4e377286b6ca9096bae48ab1` / frozen spec `3239a319fbd4ff492b16a74d899a20edc9affa7f` | `RELIABILITY_V1_FORWARD_SHADOW_ACCEPTED`: deterministic score-margin sidecar accepted after remediation. 2026-08-12 sidecar remains immutable: `836/836`, `806 AVAILABLE`, `30 NOT_APPLICABLE_O2_UNSCORED`; parquet SHA `76e5b798...be4422e`, manifest SHA `910cfc49...20dbb`. Continue outcome-blind prospective collection with O2; no independent counter, tiers/filtering, model fit, or outcome access before the O2 vault gate and separate preregistered forward-evaluation checkpoint. |
| O2 fresh-forward | `ACTIVE` | Existing forward runtime | `integration/forward-eod-automation-monitoring` / acceptance `c5b356ad1a21646c4d6b50352872c7e6718c6df9` | First official post-freeze session accepted: 2026-08-12 / index 1268, 806 scored, 30 true flat-range row exclusions, counter `1/100`; outcomes locked. Continue prospectively under identical frozen eligibility/counter/provenance rules. |
| O2.1 flat-range challenger experiment | `DONE` | ChatGPT review + Codex/O2.1-flat-range | `research/idx-ranking-ohlcv-o2-1-flat-range-v1` / acceptance `32ee9ee1e5696b2262b4defc936846dff5af557e` | Historical verdict remains `O2_1_NO_SURVIVOR` on 280,044 rows including 1,876 genuine flat bars. No rescue, tuning, robustness, promotion, or reinterpretation of this historical verdict. |
| O2.1 sealed shadow diagnostic | `REVIEW` | `Codex/O2.1-sealed-shadow + ChatGPT review` | `integration/o2-1-sealed-shadow-v1` / `b60a238` / authorization `051c6da2e0170c84de4c53e515a41887f4be9e35` | Implemented and pushed the explicitly authorized sealed score-only shadow lane. Frozen model SHA `318d8b988f3689109a1f808781c4aa8e8b478f7ee9324e8405c4641586da1ea7`, feature SHA `f0259e82240f3db76bab8929669082a422e124c8cb37a08cd94c6cff9220b3b3`, support SHA `8c6429253d84d1e355c536c0c4b715f00d20ae0344c304aa2d7a218b323c596d`. Existing 2026-08-12 artifact aligned 1 session: O2 `806/836`, O2.1 `836/836`, 30 flat rows included. Historical `O2_1_NO_SURVIVOR` preserved; outcome-blind, no provider/recapture/outcome access, no independent counter/promotion, subordinate O2-detail UI only. Awaiting independent ChatGPT review. |
| IDX forward calendar extension | `WAITING` | existing data lane | `data/idx-forward-calendar-extension-v1` | Evidence-only extension; rerun when a new official session is source-certified. Do not infer dates. |
| Historical OPEN recovery | `PARKED` | none | OPEN/Yahoo/TV accepted lineage | Research coverage gate passed conditionally; substantial residual remains. Do not restart broad provider search/backfill without a new explicit reason. |
| PIT sector history | `ACTIVE` | `ChatGPT/PIT-sector-revival` | `data/idx-pit-sector-history-revival-v1` (planned from `data/idx-pit-sector-history-v1`) | User explicitly authorized a targeted revival: recover dedicated annual 2022/2023 classification evidence and 2026 effective-date provenance, then implement only evidence/parsers that satisfy the existing fail-closed PIT contract. No dependent modeling or outcome access. |
| Broker / Margin source audit V0 | `REVIEW` | `ChatGPT/Broker-Margin-Source-Audit` | `data/broker-margin-source-audit-v0` / checkpoint `b298715` | Preliminary repo + official/Zapi source audit complete without billed provider calls. Broker is aggregate per broker/day with no ticker or side fields; margin is per-stock and potentially informative but transaction-subset semantics, raw/direct parity, historical depth, publication cadence, revision behavior, and PIT timing require a bounded local live audit before automation/model use. |
| Frontend monitoring / capture system | `REVIEW` | `Codex/Frontend Editorial Tech` | `codex/frontend-compare-v2` / `bc91a5f` | Read-only monitoring now presents the automated session archive and all three monitored lanes: O2, V3-B, and V2. UI was simplified to a compact archive, three score cards, and a slim shared-session summary; manual capture/date controls remain removed. Build and `/monitoring`, `/compare`, and `/api/monitor/status` HTTP 200 pass. Local runtime reports V2 + V3-B artifacts for 2026-08-10; O2 remains awaiting runtime score artifact. |
| Market/index prospective EOD archive extension | `BLOCKED` | `Codex/Forward-EOD-Automation-UI` | `integration/forward-eod-automation-monitoring` / `5ee8d2d` | Controlled canonical captures passed for 2026-08-11 and 2026-08-12, but local `IDXTrade-ForwardEOD` is still NOT_FOUND after the prior Access-denied registration. Legacy Open task remains Ready; one authorized elevated installer run plus post-install verification is required. |
| Canonical IDXTrade-ForwardEOD automation audit | `REVIEW` | `Codex/Forward-EOD-Automation-Audit` | `integration/forward-eod-automation-monitoring` / `5ee8d2d` | Read-only audit complete and pushed in checkpoint `2026-08-13_FORWARD_EOD_AUTOMATION_ACTUAL_AUDIT`; canonical task NOT_FOUND, legacy task Ready with last result 1, Stockbit separate/Ready, latest canonical artifacts verified. No scheduler/data-contract changes made. |

## Cross-chat no-duplicate rules currently in force

- Do not create a second generic EOD capture system until the existing frontend/backend capture path and forward archive infrastructure are inspected.
- Do not recreate Stockbit intraday automation.
- Do not reopen Path Risk V1/V2 or silently create a V3 rescue before the new-data prerequisite and preregistration are satisfied.
- Do not restart legacy Probability V1 or reuse its consumed Stage-5 ranking holdout; any future Probability V2/current-alpha calibration must use a new preregistered contract and fresh-forward validation.
- Expected Payoff V0 is closed with accepted `FEASIBILITY_GO`. Expected Payoff V1 is closed with independently accepted `EXPECTED_PAYOFF_V1_NO_SURVIVOR` at review `73b75af2...`; do not rescue it with another estimator/loss/target transform/quantile variant/horizon/feature subset, and do not create a forward shadow from this V1.
- Reliability / Uncertainty V0 is closed with accepted `RELIABILITY_V0_FEASIBILITY_GO`; only `score_margin_reliability` survived. Do not rerun V0, revive the failed marginal-support proxy, or fit/deploy a reliability model without a new frozen V1 contract.
- Reliability / Uncertainty V1 is a deterministic outcome-blind forward shadow only. Do not fit a reliability model, optimize thresholds/tiering, filter trades, create an independent counter, or access forward outcomes before the O2 vault gate.
- Do not rerun the completed O2-vs-V2 comparator unless a specific audit/reproduction request requires it.
- O2.1 historical `NO_SURVIVOR` remains final. The only authorized continuation is the separately frozen **sealed shadow diagnostic** in its dedicated lane: no tuning/rescue, no performance peeking, no promotion, and no change to active O2.
- Do not treat Market/Index/Breadth historical session-date data as PIT-complete or bulk-model-ready.
- Before suggesting a “next task,” check this file first; a suggestion counts as coordination and can itself cause duplicate work.

## Agent update template

When claiming/updating a row, keep it compact:

`<task> | ACTIVE/REVIEW/etc | <owner> | <branch + HEAD if useful> | <what is being done, blocker, or exact next boundary>`

If a material lane is missing, add it before starting the work.
