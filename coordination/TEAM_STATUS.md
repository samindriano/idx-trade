# IDX Trade — Repository-Wide Team Status

Last coordinated update: 2026-08-13 10:24 Asia/Jakarta
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
| Stockbit intraday forward capture | `AUTOMATED` | Existing runtime | `data/stockbit-intraday-forward-capture-v1` / read-only verification `b94b272` | 2026-08-12 intraday run is complete: 111,695 rows for 835 current-session tickers, SMBR returned 2026-08-11, and 126 no-activity names returned HTTP 404. `unfinished_tickers=0`, no synthetic fill, policy remains SHADOW. This is not canonical EOD; do not build another capture system. |
| Path Risk | `WAITING` | none | prior V1/V2 lineage | V1/V2 failed. Do not restart/retune now; wait for richer intraday accumulation and a genuinely new preregistered hypothesis family. |
| Probability V1 legacy calibration | `DONE` | prior research lineage | `research/idx-stage4-v1` + `research/idx-stage4b-calibration-v1` + `research/idx-stage5-ranking-holdout-v1` | Final status `PROBABILITY_V1_NOT_READY_DEFERRED`: Stage-4 and Stage-4B calibration readiness failed, and the Stage-5 ranking holdout was consumed for Ranking V1. Do not restart Probability V1 or reuse that holdout. Any future Probability V2/current-alpha calibration must use a new preregistered contract and fresh-forward validation. |
| Expected Payoff V0 feasibility | `DONE` | `ChatGPT independent review + Codex remediation` | `research/idx-expected-payoff-v0-feasibility` / `ecec6835eaee70f47a8a1c1b43fc2d14a4c34709` | `EXPECTED_PAYOFF_V0_FEASIBILITY_GO` accepted. Engineering/spec-compliance remediation reviewed complete; original one-shot verdict unchanged. Do not rerun/retune V0. |
| Expected Payoff V1 | `DONE` | `ChatGPT independent review + Codex remediation` | `research/idx-expected-payoff-v1` / correction `bc35d1c1d7d08ae3aa84c6e16200d20c1f279981` / acceptance `73b75af2322214138e55293a4bb2cb8ed4362c15` | Decision-valid `EXPECTED_PAYOFF_V1_NO_SURVIVOR` accepted after metric-only correction: median corrected MSE skill `-0.05217`, positive skill folds `0/6`; IC and D10-D1 ordering gates pass but cannot rescue conditional-mean failure. Exact V1 lane closed; no refit, tuning, alternate candidate, or forward shadow. |
| Reliability / Uncertainty V0 | `DONE` | `ChatGPT independent review + Codex` | `research/idx-reliability-uncertainty-v0` / result `1d01a1b` / acceptance `a99d53de91dfc44f9688ba7adead5206d7c7929d` | `RELIABILITY_V0_FEASIBILITY_GO_ACCEPTED`: only `score_margin_reliability` qualified, with positive Spearman/Q4-Q1/selective/conditional lift in 6/6 folds. `joint_marginal_support_reliability` failed and must not be rescued. V0 is closed; any V1 requires a separately frozen contract and fresh prospective validation. |
| Reliability / Uncertainty V1 forward shadow | `DONE` | `ChatGPT independent review + Codex remediation` | `research/idx-reliability-uncertainty-v1-forward-shadow` / remediation `4af006d` / acceptance `a21c2665f1afa73f4e377286b6ca9096bae48ab1` / frozen spec `3239a319fbd4ff492b16a74d899a20edc9affa7f` | `RELIABILITY_V1_FORWARD_SHADOW_ACCEPTED`: deterministic score-margin sidecar accepted after remediation. 2026-08-12 sidecar remains immutable: `836/836`, `806 AVAILABLE`, `30 NOT_APPLICABLE_O2_UNSCORED`; parquet SHA `76e5b798...be4422e`, manifest SHA `910cfc49...20dbb`. Continue outcome-blind prospective collection with O2; no independent counter, tiers/filtering, model fit, or outcome access before the O2 vault gate and separate preregistered forward-evaluation checkpoint. |
| Forward 100-session evaluation protocol | `REVIEW` | `ChatGPT/Forward-Evaluator-Remediation` | `codex/idx-forward-100-evaluator-v1` @ `ca0b3c1` / review `beec0bf` / frozen protocol `6c05499d01ba644c80f0c6bd6d621aac92ab2813` | `FORWARD_100_SESSION_EVALUATOR_GUARDED_REMEDIATION_IMPLEMENTED_PENDING_EXECUTION_REVIEW`: four blockers remediated via canonical guarded synthetic entrypoint: evaluated frames now load directly from exact hash-pinned O2/Reliability artifacts; accepted Reliability V1 schema/PROTECTED_FLAGS are authoritative; missing sidecars are predeclared `RELIABILITY_FORWARD_INCONCLUSIVE_DATA` before marker/loader; protocol SHA is fixed and caller-non-overridable. Added adversarial tests and checkpoint. Original metric/decision core unchanged; unguarded `1410feb` orchestration is superseded for future protected-adapter use. GitHub connector cannot run pytest, so execution-capable focused/full test run remains required. No protected outcomes accessed. |
| O2 fresh-forward | `ACTIVE` | Existing forward runtime | `integration/forward-eod-automation-monitoring` / acceptance `c5b356ad1a21646c4d6b50352872c7e6718c6df9` | First official post-freeze session accepted: 2026-08-12 / index 1268, 806 scored, 30 true flat-range row exclusions, counter `1/100`; outcomes locked. Continue prospectively under identical frozen eligibility/counter/provenance rules. |
| O2.1 flat-range challenger experiment | `DONE` | ChatGPT review + Codex/O2.1-flat-range | `research/idx-ranking-ohlcv-o2-1-flat-range-v1` / acceptance `32ee9ee1e5696b2262b4defc936846dff5af557e` | Historical verdict remains `O2_1_NO_SURVIVOR` on 280,044 rows including 1,876 genuine flat bars. No rescue, tuning, robustness, promotion, or reinterpretation of this historical verdict. |
| O2.1 sealed shadow diagnostic | `DONE` | `ChatGPT independent review + Codex/O2.1-sealed-shadow` | `integration/o2-1-sealed-shadow-v1` / remediation `6d61b2b8083c3e524a0932e36943a56503c1bd17` / acceptance `d0dbf1992f019eaafb8790256dfcdf0c68c81858` | `O2_1_SEALED_SHADOW_REMEDIATION_ACCEPTED`: prior provenance/status/coverage findings are closed. Existing sidecars fail closed on certified OHLCV/snapshot and frozen O2.1 pins/protected flags; invalid manifests are excluded from status; exact O2 model-ID coverage resolution fails on ambiguity. 2026-08-12 artifact remains immutable at SHA `20925d72546f35ccce3a355fdc02d31789c90d20437cffd1db6068481ddd2c34`, O2 `806/836`, O2.1 `836/836`, 30 flat rows. Continue score-only outcome-blind accumulation; no promotion, counter, tuning, or first-vault O2.1 outcome verdict. |
| IDX forward calendar extension | `WAITING` | existing data lane | `data/idx-forward-calendar-extension-v1` | Evidence-only extension; rerun when a new official session is source-certified. Do not infer dates. |
| Historical OPEN recovery | `PARKED` | none | OPEN/Yahoo/TV accepted lineage | Research coverage gate passed conditionally; substantial residual remains. Do not restart broad provider search/backfill without a new explicit reason. |
| PIT sector history | `PARKED` | `ChatGPT/PIT-sector-revival review` | `data/idx-pit-sector-history-revival-v1` / acceptance `5c9cb42a9b40774a5672f7487ce46ad94a806bed` | Targeted revival accepted fail-closed: canonical inventory remains `5 ready / 3 blocked`. 2023 is near-resolved (`Peng-00158`, BMTR effective 2023-07-03) but official IDX bytes are unavailable; reopen only on direct official archive recovery or a separately frozen verified-official-mirror methodology review. No dependent modeling. |
| Broker / Margin source audit V0 | `DONE` | `ChatGPT independent review + Codex` | `data/broker-margin-source-audit-v0` / live audit `567ec03` / acceptance `c7fcec2` | `BROKER_MARGIN_SOURCE_LIVE_AUDIT_ACCEPTED_MARGIN_FLOW_REJECTED`: Zapi parity to official IDX passes; literal All-Stock-filter H2 fails; H1 margin-financing flow is unsupported. Treat only as an official Margin category/reporting view with exact inclusion/aggregation semantics and PIT timing unresolved. No margin-usage/leverage/crowding features, automation, or bulk backfill. |
| Frontend monitoring / capture system | `REVIEW` | `Codex/Frontend Editorial Tech` | `codex/frontend-compare-v2` / `bc91a5f` | Read-only monitoring now presents the automated session archive and all three monitored lanes: O2, V3-B, and V2. UI was simplified to a compact archive, three score cards, and a slim shared-session summary; manual capture/date controls remain removed. Build and `/monitoring`, `/compare`, and `/api/monitor/status` HTTP 200 pass. Local runtime reports V2 + V3-B artifacts for 2026-08-10; O2 remains awaiting runtime score artifact. |
| Market/index prospective EOD archive extension | `AUTOMATED` | `Codex/Forward-EOD-Automation-UI` | `integration/forward-eod-automation-monitoring` / `666ec11` | Canonical `IDXTrade-ForwardEOD` is installed and `Ready`: daily 18:00 Asia/Jakarta plus logon catch-up, StartWhenAvailable, IgnoreNew, network guard, and existing repo/runtime paths. Legacy Open task is Disabled; first scheduled run remains pending. |
| Canonical IDXTrade-ForwardEOD automation audit | `DONE` | `Codex/Forward-EOD-Automation-Audit` | `integration/forward-eod-automation-monitoring` / `666ec11` | Installation and read-only verification complete; checkpoint `2026-08-13_FORWARD_EOD_AUTOMATION_INSTALLED` pushed. Stockbit remains separate/Ready, task/runtime credential scans are clean, and no provider capture was triggered. |
| Canonical EOD adversarial test-gap audit | `ACTIVE` | `Codex/EOD-Test-Gap-Audit` | `codex/idx-eod-adversarial-tests-v0` / base `79eb694` | Repo-wide engineering-only adversarial audit of canonical EOD runtime, source validation, artifact/hash/session integrity, catch-up/idempotency, partial/corrupt/provider/stale-date failures, outcome locks, fingerprints, duplicates, and ambiguous session resolution. No scientific/model behavior changes and no outcome access. |
| Repository-wide scientific integrity and reproducibility audit | `ACTIVE` | `Codex/Scientific-Integrity-Audit` | `codex/scientific-integrity-audit-v1` / planned from `origin/main` `79eb694` | Comprehensive outcome-blind audit of code, manifests/hashes, provenance/PIT, model and feature identities, branch/checkpoint/handoff verdict lineage, mutable-artifact risk, and fail-open behavior. No experiment reruns or protected-outcome access; only bounded safe engineering remediation is authorized. |
| Canonical data-source / provenance registry | `ACTIVE` | `Codex/Provenance-Registry` | `codex/data-source-provenance-registry-v1` / planned from current `origin/main` | Build a machine-readable registry and contradiction/staleness validator from accepted repository evidence/checkpoints only. Documentation/schema/tests scope; no provider calls, data acquisition, outcome access, experiment reruns, scientific remediation, or reinterpretation of unresolved conclusions. Coordinate boundaries with the active scientific-integrity audit. |

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
