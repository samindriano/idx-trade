# IDX Trade — Repository-Wide Team Status

Last coordinated update: 2026-08-12 23:44 Asia/Jakarta
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
5. update the row again when work becomes `REVIEW`, `DONE`, `PARKED`, or `BLOCKED`.

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
| Expected Payoff V1 | `REVIEW` | `ChatGPT independent review + Codex remediation` | `research/idx-expected-payoff-v1` / runtime `bf6916927ea1a3ecd73708834aa38d0ad91c3c88` / review `fb584c988cd4ac07ef077103f5a53f6ba3ef097e` | Original `EXPECTED_PAYOFF_V1_NO_SURVIVOR` is **not accepted**: frozen `TRAIN_MEAN_PAYOFF` baseline was scored with training-set target variance instead of validation-set MSE of the training-mean constant prediction. Scientific outcome is undetermined. Metric-only correction is authorized using the existing frozen V1 predictions; no model refit, tuning, alternate candidate, provider call, or fresh-forward access. |
| O2 fresh-forward | `ACTIVE` | Existing forward runtime | `integration/forward-eod-automation-monitoring` / acceptance `c5b356ad1a21646c4d6b50352872c7e6718c6df9` | First official post-freeze session accepted: 2026-08-12 / index 1268, 806 scored, 30 true flat-range row exclusions, counter `1/100`; outcomes locked. Continue prospectively under identical frozen eligibility/counter/provenance rules. |
| O2.1 flat-range challenger experiment | `DONE` | ChatGPT review + Codex/O2.1-flat-range | `research/idx-ranking-ohlcv-o2-1-flat-range-v1` / acceptance `32ee9ee1e5696b2262b4defc936846dff5af557e` | Historical verdict remains `O2_1_NO_SURVIVOR` on 280,044 rows including 1,876 genuine flat bars. No rescue, tuning, robustness, promotion, or reinterpretation of this historical verdict. |
| O2.1 sealed shadow diagnostic | `REVIEW` | `Codex/O2.1-sealed-shadow + ChatGPT review` | `integration/o2-1-sealed-shadow-v1` / `b60a238` / authorization `051c6da2e0170c84de4c53e515a41887f4be9e35` | Implemented and pushed the explicitly authorized sealed score-only shadow lane. Frozen model SHA `318d8b988f3689109a1f808781c4aa8e8b478f7ee9324e8405c4641586da1ea7`, feature SHA `f0259e82240f3db76bab8929669082a422e124c8cb37a08cd94c6cff9220b3b3`, support SHA `8c6429253d84d1e355c536c0c4b715f00d20ae0344c304aa2d7a218b323c596d`. Existing 2026-08-12 artifact aligned 1 session: O2 `806/836`, O2.1 `836/836`, 30 flat rows included. Historical `O2_1_NO_SURVIVOR` preserved; outcome-blind, no provider/recapture/outcome access, no independent counter/promotion, subordinate O2-detail UI only. Awaiting independent ChatGPT review. |
| IDX forward calendar extension | `WAITING` | existing data lane | `data/idx-forward-calendar-extension-v1` | Evidence-only extension; rerun when a new official session is source-certified. Do not infer dates. |
| Historical OPEN recovery | `PARKED` | none | OPEN/Yahoo/TV accepted lineage | Research coverage gate passed conditionally; substantial residual remains. Do not restart broad provider search/backfill without a new explicit reason. |
| PIT sector history | `PARKED` | none | `data/idx-pit-sector-history-v1` | Research direction recorded; blocked/not authorized for dependent modeling until PIT evidence improves. |
| Frontend monitoring / capture system | `REVIEW` | `Codex/Frontend Editorial Tech` | `codex/frontend-compare-v2` / `bc91a5f` | Read-only monitoring now presents the automated session archive and all three monitored lanes: O2, V3-B, and V2. UI was simplified to a compact archive, three score cards, and a slim shared-session summary; manual capture/date controls remain removed. Build and `/monitoring`, `/compare`, and `/api/monitor/status` HTTP 200 pass. Local runtime reports V2 + V3-B artifacts for 2026-08-10; O2 remains awaiting runtime score artifact. |
| Market/index prospective EOD archive extension | `WAITING` | `Codex/Forward-EOD-Automation-UI` | `integration/forward-eod-automation-monitoring` / `cd2a834` | Single 18:00 EOD runner, logon catch-up, official-calendar/exact-date validation, and legacy Open-task disable path are implemented and tested. Awaiting one post-18:00 controlled capture before local scheduler enablement. |

## Cross-chat no-duplicate rules currently in force

- Do not create a second generic EOD capture system until the existing frontend/backend capture path and forward archive infrastructure are inspected.
- Do not recreate Stockbit intraday automation.
- Do not reopen Path Risk V1/V2 or silently create a V3 rescue before the new-data prerequisite and preregistration are satisfied.
- Do not restart legacy Probability V1 or reuse its consumed Stage-5 ranking holdout; any future Probability V2/current-alpha calibration must use a new preregistered contract and fresh-forward validation.
- Expected Payoff V0 is closed with accepted `FEASIBILITY_GO`. Expected Payoff V1 runtime verdict at `bf691692...` is not decision-valid because the primary `TRAIN_MEAN_PAYOFF` baseline MSE was evaluated on training targets instead of validation outcomes. Only the bounded metric correction authorized in review `fb584c98...` may proceed; no payoff candidate search, post-result model rescue, refit, or fresh-forward outcome access.
- Do not rerun the completed O2-vs-V2 comparator unless a specific audit/reproduction request requires it.
- O2.1 historical `NO_SURVIVOR` remains final. The only authorized continuation is the separately frozen **sealed shadow diagnostic** in its dedicated lane: no tuning/rescue, no performance peeking, no promotion, and no change to active O2.
- Do not treat Market/Index/Breadth historical session-date data as PIT-complete or bulk-model-ready.
- Before suggesting a “next task,” check this file first; a suggestion counts as coordination and can itself cause duplicate work.

## Agent update template

When claiming/updating a row, keep it compact:

`<task> | ACTIVE/REVIEW/etc | <owner> | <branch + HEAD if useful> | <what is being done, blocker, or exact next boundary>`

If a material lane is missing, add it before starting the work.
