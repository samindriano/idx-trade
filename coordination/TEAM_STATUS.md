# IDX Trade — Repository-Wide Team Status

Last coordinated update: 2026-08-16 00:08 Asia/Jakarta
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
4. update the row whenever a material checkpoint, blocker, verdict, ownership change, or branch change;
5. update it again when the task becomes `REVIEW`, `DONE`, `PARKED`, `WAITING`, or `BLOCKED`.

No agent may duplicate another `ACTIVE` scope unless the user explicitly asks for independent/adversarial review.

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
| V4-X1 clean Phase-A execution-lock local capture | `REVIEW` | `Codex/V4-X1-Clean-Phase-A-Execution-Lock` | `research/idx-v4-x1-clean-phase-a-execution-lock-v1` / `3a7f50765341b5c20fef36be4df98a3e7dfa196f` | Hash-only capture PASS: status `V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK_CAPTURED_REPLAY_NOT_RUN`; manifest `D:\Documents\Project\idx-v4-x1-clean-phase-a-execution-lock-20260820-v1\v4_x1_clean_phase_a_execution_lock_manifest.json`, SHA `1846c94a74de8132672777c96f46580d298f942d87584e12b5e99e78e83a77f3`; exact runtime match and all five external input hashes PASS; all safety flags false. Focused `14 passed`, py_compile PASS, diff-check PASS. Phase-A replay not run. |
| V4-X1 clean Phase-A structural replay | `REVIEW` | `Codex/V4-X1-Clean-Phase-A-Structural-Replay` | `research/idx-v4-x1-clean-phase-a-structural-replay-v1` / `bca6c9cc8e78608cfa97e3c8a8fe96b115877e50` | One authorized outcome-blind replay completed: status `V4_X1_CLEAN_PHASE_A_CA80_SUPPORT_FAIL_REVIEW_REQUIRED`; manifest `D:\Documents\Project\idx-v4-x1-clean-phase-a-structural-replay-20260820-v1\MANIFEST.json`, SHA `1dedb76db7c1fc620e4feb286e409d0266bf367581cbf7dab28bc862f298787c`; old support oracle exact match PASS, clean CA80 FAIL, no refit/target/performance/forward-outcome access, no provider/network calls. |
| V4-X1 clean Phase-B final refit | `REVIEW` | `Codex/V4-X1-Clean-Phase-B-Final-Refit` | `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1` / `b3b9338d420c60dbc3853117d74d4ceb62bace19` | Exactly one frozen-boundary refit complete: status `V4_X1_CLEAN_PHASE_B_FINAL_REFIT_COMPLETE_INDEPENDENT_REVIEW_REQUIRED`; final manifest `D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1\MANIFEST.json`, SHA `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`; fit_count `4`, no historical/prospective scoring, provider/network, protected/fresh-forward, or counter mutation. |
| V4-X1 clean prospective deployment | `REVIEW` | `Codex/V4-X1-Clean-Prospective-Deployment` | `integration/v4-x1-clean-prospective-score-v1` / `3e20bc32ecb5ec26860a3a0f4974bd55b223e689` | Deployment preconditions passed and updater invoked exactly once at/after 2026-08-20 20:35 Asia/Jakarta, but it exited before mutation at its built-in Administrator check: `Administrator PowerShell is required`. Per fail-closed handoff, no retry, task verification/readiness rerun, manual start, pipeline/score, counter/registry, provider, model, or outcome access. `scheduled_task_mutated=false`. |
| Repository artifact governance V1 | `REVIEW` | `Codex/Artifact-Governance` | `codex/artifact-governance-v1` / final `30478f435c1d1f30aa1a3ced9b6db201c396d8cb` | Actual promotion complete: 13 accepted small 126-session canonical/summary/manifest artifacts, 123,650 Git bytes, source/promoted SHA verification PASS, and scrubbed certified-manifest pointer. Raw providers, full panels, attachments, binaries, runtime, credentials, and outcomes remain external. Focused registry tests 4 passed; full pytest retains 1 pre-existing unrelated storage expectation failure. |
| Repository Hygiene V1 branch inventory dry-run audit | `REVIEW` | `Codex/Repository-Hygiene-V1` | `codex/repository-hygiene-v1` / final `ecac6c6` | Forensic classifier remediation complete at snapshot `origin/main=86baf2a` with 138 remote branches and 29 PRs mapped: 66 KEEP, 67 ARCHIVE_TAG_THEN_DELETE, 1 TOMBSTONE_THEN_DELETE, 0 DELETE_SAFE, and 4 NEEDS_MANUAL_REVIEW. Manual hints no longer bypass evidence gates; reusable implementation preservation and branch/PR disposition consistency are explicit and validated. No branches, tags, PRs, history, runtime, O2, models, or scientific files were mutated. Reports: `docs/repository_hygiene/BRANCH_FORENSIC_INVENTORY_V1.csv`, `BRANCH_FORENSIC_PLAN_V1.md`, and `PR_FORENSIC_PLAN_V1.csv`. Destructive cleanup remains unauthorized pending independent review. |
| O2 vs V2 common-support comparator | `DONE` | ChatGPT review + Codex | `research/idx-ranking-o2-v2-common-support-comparator-v1` / acceptance `a2c5666637f2e879ce107cd44fc2dae8cc22a5c5` | Historical-development evidence accepted; **do not rerun or extend automatically**. |
| Market / Index / Breadth History V1 | `PARKED` | ChatGPT review + Codex | `data/market-index-breadth-history-v1` / review `d3827f1506736ec64c957e10f50f5447196d9983` | `CONDITIONAL_SOURCE_READY_PIT_BLOCKED`; no historical PIT bulk acquisition/model use. |
| Stockbit intraday forward capture | `AUTOMATED` | Existing runtime | `data/stockbit-intraday-forward-capture-v1` / read-only verification `b94b272` | 2026-08-12 intraday run is complete: 111,695 rows for 835 current-session tickers, SMBR returned 2026-08-11, and 126 no-activity names returned HTTP 404. `unfinished_tickers=0`, no synthetic fill, policy remains SHADOW. This is not canonical EOD; do not build another capture system. |
| Alternative alpha data/source feasibility V1 | `REVIEW` | `Codex/Alternative-Alpha-Data-Feasibility` | `research/idx-alternative-alpha-data-feasibility-v1` / result `e9d0b50ce81b51150a076529c37d6701eea1a387` | One-shot outcome-blind source census complete: `CONDITIONAL_SOURCE_READY_NO_HISTORICAL_ALPHA_YET`; final manifest SHA-256 `7761b8d0a12784c22f9f3938fe9001689c1937c72968dff88caed10ce0ca1ffd`. Stockbit Stream is prospective-only; per-ticker Stockbit broker flow is a bounded-pilot candidate; official IDX disclosure/events and BI macro are bounded-pilot candidates; IDX SBL is prospective-only. No model/feature fit, target/performance/protected-forward access, V4-X1/O2/counter mutation, bulk backfill, or duplicate intraday capture. Stop for independent review. |
| Investing historical intraday depth audit | `DONE` | `ChatGPT independent review + Codex/Investing-Intraday-Depth-Audit` | `data/investing-intraday-depth-audit-v1` / remediation `d083581c561c5777cc221b4a16bc48d4b98b4685` / acceptance `b80bd94daf26436092bd5e070c5b4bc70b2a2037` | `DEPTH_AUDIT_ACCEPTED_PREREGISTER_SECONDARY_INTRADAY_PILOT`: 3,685/3,685 sparse 1h probes completed with zero final provider errors; listing-aware conditional availability is 87.87%/80.04%/95.23%/94.89%/92.42% for 2018/2020/2022/2024/2026. Timezone remediation was documentation-only and fidelity metrics are unchanged. Next authorization is only a separately frozen acquisition/admission pilot; no bulk backfill, canonical panel integration, model work, protected outcomes, O2 changes, or automatic Path Risk restart. |
| Investing secondary intraday admission pilot | `DONE` | `ChatGPT independent review + Codex/Investing-Intraday-Admission-Pilot` | `data/investing-intraday-admission-pilot-v1` / reviewed HEAD `27e0b7a1b3f5bb4688efeb585215eb0b6e435ccd` / acceptance `6e3740e60e0196212ecbe4ea737703e2cf18ba01` | `PILOT_REJECTED_ACCEPTED_DECISION_VALID`: 58/138 final provider errors, all three coverage eras fail, and returned-data fidelity independently misses frozen gates. Two non-decision-changing evaluator gaps were found (frozen provenance hashes are recorded but not enforced; generated verdict does not enforce all admission gates). Lane remains rejected/closed; no rerun, bulk acquisition, canonical integration, Path Risk/O2 work, or outcome access. Fix both gaps before any separately preregistered future reuse. |
| TradingView historical intraday admission pilot | `REVIEW` | `Codex/TradingView-Historical-Intraday-Admission` | `data/tradingview-historical-intraday-admission-pilot-v1` / HEAD `c26c4e429e162fd6240f6b6918b3f27e86494229` | Frozen verdict `TRADINGVIEW_INTRADAY_ADMISSION_REJECTED`: certified-session coverage 86.62% fails despite HLC 96.18%, volume ±5% 95.01%, and 8/8 deep controls reaching 2020-01-02. No rerun/bulk/model/O2/Path Risk. |
 | TradingView activity-aware coverage forensic audit | `BLOCKED` | `ChatGPT/TradingView-Activity-Forensics` | `data/tradingview-intraday-activity-forensics-v1` / prepared HEAD `97b1f01c4ec4171e438cff6e4ad9118afde7e3b8` | Offline classifier/runner/checkpoint prepared and hash-pinned. Exact runtime is blocked only because the authoritative admission artifact root and canonical panel are local external bytes on the user's Windows machine, inaccessible to this ChatGPT runtime. Zero provider calls; frozen pilot rejection unchanged. |
 | TradingView Open / session semantics forensic V1 | `REVIEW` | `Codex/TradingView-Open-Session-Semantics` | `data/tradingview-open-session-semantics-v1` / final `80898c9098196db0275c1748cdfa28c859ff24b9` / runtime artifact root `tradingview_open_session_semantics_v1_retry_20260814` | `TV60_OPEN_BOUNDARY_PATTERN_FOUND_MEANING_UNPROVEN`: stored metadata supports regular `0900-1630` vs public extended `0845-1630`; bounded 2026 probe found regular 0 vs extended 10 pre-open rows across BBCA/BBRI/BMRI/TLKM/ASII (1m 08:58, 5m 08:55), while all 2021/2024 probes timed out after symbol load. Auction identity is unproven because no auction flag/trade classification exists. Frozen admission rejection, panel, model, Path Risk, O2, outcomes unchanged. |
| TradingView intraday price-path semantic contract V1 | `REVIEW` | `Codex/TradingView-Price-Path-Contract` | `data/tradingview-intraday-price-path-contract-v1` / final `1906f8a9e3c582384d3b414ee3b763120398df95` | Semantic contract frozen: `official_open` and raw `tv_regular_open` remain separate; raw H/L/C/V path features are bounded and auction/repair semantics are prohibited. Admission V2 remains closed because the canonical Stage-1 checkpoint records 195 uncertain sessions. No model fit, bulk acquisition, panel write, Path Risk, O2, or outcome access. |
| TradingView Open + price-path remediation V1 | `REVIEW` | `Codex/TradingView-Open-Price-Path-Remediation` | `data/tradingview-open-price-path-remediation-v1` / final `97124d017de9533e1c84d7f84eab4b22edbfbda4` / artifact root `tradingview_open_price_path_remediation_v1_20260814` | `TRADINGVIEW_PRICE_PATH_CONTRACT_REMEDIATION_ACCEPTED_PREREGISTRATION_V2_READY`: classifier contradiction fix preserved `TV60_OPEN_BOUNDARY_PATTERN_FOUND_MEANING_UNPROVEN`; independent official regular-market evidence resolves 195/195 zero-activity rows with 0 unresolved; frozen 30-request 60m probe is 30/30 AVAILABLE, extended first 08:45 WIB vs regular 09:00 WIB, extended Open=official 14/15 and official inside extended H/L 15/15. Preregistration readiness true; admission/model/acquisition remain closed. No bulk, panel write, model, Path Risk, O2, outcomes, or Historical OPEN changes. |
| TradingView historical price-path V2 | `REVIEW` | `Codex/TradingView-Historical-Price-Path-V2` | `data/tradingview-historical-price-path-v2` / final `f6716bb861eee396a8b57c42b207af31b4565db7`; runtime manifest `a0bff854f6c76266c8b8487aa0d07af38ac263def3d7f719bea9af7715cb5e1e`; preregistration `70ca3a4c1088f7f6bde155b4f99fd65eb60cb0963e61a80ea5bd69416fd850f7`; lineage remediation `97124d017de9533e1c84d7f84eab4b22edbfbda4` / activity `c943a76fd56872d981a87519c2eb7072c413322c` | Final `TRADINGVIEW_PRICE_PATH_V2_REJECTED`: 962/978 AVAILABLE, 16 SYMBOL_ERROR, 87,372/994,265 ACTIVE coverage (8.7876%) because frozen max-10 pagination yielded only up to 550 bars/ticker; structural checks 0 violations; available-overlap HLC exact 94.3705%, volume ±5% 93.4885%. Canonical panel unchanged. No model, panel mutation, Path Risk, O2, protected outcomes, or extended-session corpus. Stop for independent review; any deeper pagination requires a new preregistration. |
| TradingView historical price-path V2.1 remediation | `REVIEW` | `Codex/TradingView-Historical-Price-Path-V2.1-Remediation` | `data/tradingview-historical-price-path-v2-1-remediation` / final `bfb3cbc`; base `f6716bb861eee396a8b57c42b207af31b4565db7` | `V2_1_REMEDIATION_READY_FOR_FULL_PREREGISTRATION`: offline contracts and preregistration verified; bounded anonymous prodata depth preflight passed 5/5, exactly 5 requests, 50,986 bars, all reached 2020-01-02, zero structural/session violations. Prereg SHA `5fd9b2eefc69fd0c5a29e9d82e790e9f8490583e82e63522f45c815788b5574e`; runtime manifest SHA `49d7db1ac33f2db6de9da1bf579b80b49dd7d26761f26020eafd69a94eb59a49`; panel unchanged. Stop for review; no full 978-ticker rerun, model, panel mutation, Path Risk, O2, outcomes, or provider search. |
| Path Risk | `WAITING` | none | prior V1/V2 lineage | V1/V2 failed. Do not restart/retune now; wait for richer intraday accumulation and a genuinely new preregistered hypothesis family. |
| Probability V1 legacy calibration | `DONE` | prior research lineage | `research/idx-stage4-v1` + `research/idx-stage4b-calibration-v1` + `research/idx-stage5-ranking-holdout-v1` | Final status `PROBABILITY_V1_NOT_READY_DEFERRED`: Stage-4 and Stage-4B calibration readiness failed, and the Stage-5 ranking holdout was consumed for Ranking V1. Do not restart Probability V1 or reuse that holdout. Any future Probability V2/current-alpha calibration must use a new preregistered contract and fresh-forward validation strictly after 2026-07-31. |
| Expected Payoff V0 feasibility | `DONE` | `ChatGPT independent review + Codex remediation` | `research/idx-expected-payoff-v0-feasibility` / `ecec6835eaee70f47a8a1c1b43fc2d14a4c34709` | `EXPECTED_PAYOFF_V0_FEASIBILITY_GO` accepted. Engineering/spec-compliance remediation reviewed complete; original one-shot verdict unchanged. Do not rerun/retune V0. |
| Expected Payoff V1 | `DONE` | `ChatGPT independent review + Codex remediation` | `research/idx-expected-payoff-v1` / correction `bc35d1c1d7d08ae3aa84c6e16200d20c1f279981` / acceptance `73b75af2322214138e55293a4bb2cb8ed4362c15` | Decision-valid `EXPECTED_PAYOFF_V1_NO_SURVIVOR` accepted after metric-only correction: median corrected MSE skill `-0.05217`, positive skill folds `0/6`; IC and D10-D1 ordering gates pass but cannot rescue conditional-mean failure. Exact V1 lane closed; no refit, tuning, alternate candidate, or forward shadow. |
| Reliability / Uncertainty V0 | `DONE` | `ChatGPT independent review + Codex` | `research/idx-reliability-uncertainty-v0` / result `1d01a1b` / acceptance `a99d53de91dfc44f9688ba7adead5206d7c7929d` | `RELIABILITY_V0_FEASIBILITY_GO_ACCEPTED`: only `score_margin_reliability` qualified, with positive Spearman/Q4-Q1/selective/conditional lift in 6/6 folds. `joint_marginal_support_reliability` failed and must not be rescued. V0 is closed; any V1 requires a separately frozen contract and fresh prospective validation. |
| Reliability / Uncertainty V1 forward shadow | `DONE` | `ChatGPT independent review + Codex remediation` | `research/idx-reliability-uncertainty-v1-forward-shadow` / remediation `4af006d` / acceptance `a21c2665f1afa73f4e377286b6ca9096bae48ab1` / frozen spec `3239a319fbd4ff492b16a74d899a20edc9affa7f` | `RELIABILITY_V1_FORWARD_SHADOW_ACCEPTED`: deterministic score-margin sidecar accepted after remediation. 2026-08-12 sidecar remains immutable: `836/836`, `806 AVAILABLE`, `30 NOT_APPLICABLE_O2_UNSCORED`; parquet SHA `76e5b798...be4422e`, manifest SHA `910cfc49...20dbb`. Continue outcome-blind prospective collection with O2; no independent counter, tiers/filtering, model fit, or outcome access before the O2 vault gate and separate preregistered forward-evaluation checkpoint. |
| Forward 100-session evaluation protocol | `DONE` | `ChatGPT independent review + Codex remediation` | `codex/idx-forward-100-evaluator-v1` / reviewed HEAD `12a5b99150cbb33c729343ceec3f4d4da2d66ecd` / acceptance `fe323e2977ef447aaa7fbd93b38ef3021563d072` / frozen protocol `6c05499d01ba644c80f0c6bd6d621aac92ab2813` | `FORWARD_100_SESSION_EVALUATOR_GUARDED_REMEDIATION_ACCEPTED`: four prior engineering blockers closed; focused `17 passed`, full `295 passed, 0 failed, 3 existing warnings`, `git diff --check` PASS. Canonical synthetic entrypoint is guarded and protected outcomes/providers/models/counter/real marker remain untouched. No protected adapter or vault opening is authorized until exact `100/100`, H10 maturity, and separate final `READY_TO_OPEN_VAULT` review. |
| O2 fresh-forward | `ACTIVE` | Existing forward runtime | `integration/forward-eod-automation-monitoring` / acceptance `c5b356ad1a21646c4d6b50352872c7e6718c6df9` | First official post-freeze session accepted: 2026-08-12 / index 1268, 806 scored, 30 true flat-range row exclusions, counter `1/100`; outcomes locked. Continue prospectively under identical frozen eligibility/counter/provenance rules. |
| O2.1 flat-range challenger experiment | `DONE` | ChatGPT review + Codex/O2.1-flat-range | `research/idx-ranking-ohlcv-o2-1-flat-range-v1` / acceptance `32ee9ee1e5696b2262b4defc936846dff5af557e` | Historical verdict remains `O2_1_NO_SURVIVOR` on 280,044 rows including 1,876 genuine flat bars. No rescue, tuning, robustness, promotion, or reinterpretation of this historical verdict. |
| O2.1 sealed shadow diagnostic | `DONE` | `ChatGPT independent review + Codex/O2.1-sealed-shadow` | `integration/o2-1-sealed-shadow-v1` / remediation `6d61b2b8083c3e524a0932e36943a56503c1bd17` / acceptance `d0dbf1992f019eaafb8790256dfcdf0c68c81858` | `O2_1_SEALED_SHADOW_REMEDIATION_ACCEPTED`: prior provenance/status/coverage findings are closed. Existing sidecars fail closed on certified OHLCV/snapshot and frozen O2.1 pins/protected flags; invalid manifests are excluded from status; exact O2 model-ID coverage resolution fails on ambiguity. 2026-08-12 artifact remains immutable at SHA `20925d72546f35ccce3a355fdc02d31789c90d20437cffd1db6068481ddd2c34`, O2 `806/836`, O2.1 `836/836`, 30 flat rows. Continue score-only outcome-blind accumulation; no promotion, counter, tuning, or first-vault O2.1 outcome verdict. |
| IDX forward calendar extension | `WAITING` | existing data lane | `data/idx-forward-calendar-extension-v1` | Evidence-only extension; rerun when a new official session is source-certified. Do not infer dates. |
| Historical OPEN recovery | `REVIEW` | `Codex/Official-Stock-Summary-Recovery` | `data/idx-open-official-stock-summary-recovery-v1` / result `e70ac11494c2d449d9bbc14aa246f5a34d2e01ea` | `OFFICIAL_STOCK_SUMMARY_OPEN_RECOVERY_NO_ROWS_ADMITTED`: 1,288 official IDX Stock Summary sessions were hash-verified offline. `OpenPrice` is the only admitted candidate semantics (98.9887% exact among positive canonical-known candidates); `FirstTrade` is rejected as fallback (56.5464%). Global missing Open `43,800/43,800` and clean V3-B missing Open `12,589/12,589` remain `OPENPRICE_NONPOSITIVE_OR_INVALID`; admitted rows `0`. Empty derivative overlays only; canonical panel and Foreign Flow artifacts unchanged. Await ChatGPT independent review. |
| Historical OPEN corporate-action scale reconstruction | `REVIEW` | `Codex/Open-CA-Scale-Independent-Verification` | `data/idx-open-ca-scale-reconstruction-v1` / result `5ca967c9a1c8b8229d686f66e87b7fa53363c70b` | Independently verified exactly 2,184 existing admissions (CLEO 874, MMIX 483, WGSH 827) with official factor + transformed-HLC rules and materialized an immutable external overlay. Remaining 47,292 rows stay fail-closed. Overlay is `VERIFIED_WITH_METADATA_WARNING` because the pinned residual summary's internal self-hash is stale; no provider/CA expansion, panel rewrite, model, or outcome access. |
| V4 target-support census | `REVIEW` | `Codex/V4-Target-Support-Census` | `research/idx-v4-target-support-census-v1` / final `5f3c2d7b66cf66b2676ba0a409cdc2f4c9ca8f5d` | Outcome-blind census complete: 264/1,260 dates pass both-target + CA ≥90% gates; longest official-calendar-consecutive run is 196, so 6×100 (600 sessions) is blocked. Exact identity SHA `cdad58189694d71d1ca4ebce1c12da7dea4a663d3930262325a637ca53fca7dc`. The manifest-pinned signal contract path is missing and strict 1260 execution grade remains FAIL. Full pytest was 39 passed / 1 unrelated pre-existing storage expectation failure. No labels, IC/performance, model fit, provider/CA acquisition, or evaluator-contract changes. Awaiting review. |
| V4 target-support census remediation | `REVIEW` | `Codex/V4-Target-Support-Census-Remediation` | `research/idx-v4-target-support-census-remediation-v1` / final `a2a3c30cd85d02de3e340536c376752cdf4456b0` | Exact outcome-blind rerun corrected the prior Open-lineage omission: derivative support 938,139 plus 2,184 incremental CA-overlay rows = 940,323 / 981,940. Eligible sessions: H5 910, H10 891, consensus 815; all satisfy the frozen 600-session requirement. Focused tests 3 passed; full pytest 41 passed / 1 unrelated pre-existing storage expectation failure. Exact signal-contract path remains a provenance warning. No provider calls, labels/outcomes, model fit, or V4 contract changes. Awaiting review. |
| V4-3 primary-liquid support census | `REVIEW` | `Codex/V4-3-Primary-Liquid-Support` | `research/idx-ranking-v4-3-preregistration-v1` / final `55440cac2b605c687963ce858ccd3610659ddba0` | Exact outcome-blind support run passed: primary-liquid universe 740 tickers / 348,765 rows; eligible H5/H10/consensus sessions 1,108 / 1,102 / 1,100. Exact last-600 consensus validation identity materialized as 6x100 with official 10-session purge. Small support/eligible/fold/summary/manifest artifacts promoted to Git. Focused tests 6 passed; no target materialization, labels/outcomes, model fit, predictions, performance, provider calls, or V4 contract changes. Awaiting review. |
| V4-3 prefit runtime capture | `REVIEW` | `Codex/V4-3-Prefit-Runtime` | `research/idx-ranking-v4-3-prefit-runtime-v1` / final `ffa79256c4c8f2e202047bab5a9c8a4f3ddd3218` | Outcome-blind environment capture PASS: manifest `cf6f1b0c...`; focused tests `10 passed`, compile and diff-check PASS. Captured estimator/imputer/package/thread environment only; no R5/R10, target ranks, model fit, predictions, performance, provider calls, or protected/fresh-forward outcomes. Stop for ChatGPT review before target/model execution. |
| V4-3 target/execution freeze | `REVIEW` | `Codex/V4-3-Target-Execution-Freeze` | `research/idx-ranking-v4-3-target-execution-freeze-v1` / final `b536c832730bd0c5e2dd6952b44cf9b11b4573f9` | Outcome-blind local validation PASS: focused tests `40 passed`; PIT verdict `V4_3_PIT_REMEDIATED_SUPPORT_PRESERVES_FROZEN_6X100`; execution-code manifest `631a3b6f...`. Frozen 6x100 identity preserved. `corporate_action_continuity_certified=false` remains the downstream blocker. No R5/R10, targets/ranks, model, predictions, performance, provider calls, CA acquisition, or protected/fresh-forward outcomes accessed. Stop for ChatGPT review. |
| V4 Corporate-Action Price-Basis Continuity Gate V1 | `REVIEW` | `Codex/V4-CA-Continuity` | `data/idx-v4-corporate-action-continuity-gate-v1` / final `7e03cdf7023590ea5b7881a61b4e0a958f147d25` | Outcome-blind gate result `BLOCKED`: 739 decision tickers / frozen 600 dates, 0/600 H5/H10/consensus dates meet continuity ≥90%. Existing official IDX/KSEI evidence is bounded candidate/provenance only; 344,740 rows are unresolved coverage and 50 unresolved effective-date cases. No target/rank materialization, model/performance/outcome access, provider calls, new CA acquisition, or V4 contract changes. External ledger SHA `52ce3f17...`. |
| V4 KSEI CA-history census V1 | `REVIEW` | `Codex/V4-KSEI-CA-History-Census` | `data/idx-v4-ksei-ca-history-census-v1` / result | Exact 610-ticker KSEI census complete: 567 coverage-certified, 43 unresolved, 14,723 history rows. Offline continuity V2 remains `V4_CA_CONTINUITY_STILL_BLOCKED`: 464/610 tickers resolved and 0/600 H5/H10/consensus dates meet the 90% gate; minimum rate 0.710027. Census manifest `7cc3ac4d...`; continuity V2 manifest `503afd04...`. No R5/R10, targets/ranks, model, prediction, performance, outcomes, provider substitution, or policy tuning. |
| V4 CA event-window semantics V1 | `REVIEW` | `Codex/V4-CA-Event-Window-Semantics` | `data/idx-v4-ca-event-window-semantics-v1` / result `96a652b311f868babab94ca24b32bf1df382627c` | Final Stage 3 verdict `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`: 610 tickers / 600 dates, 42 exact transitions, 94 schedule-required events / 74 tickers, 0/600 H5/H10/consensus dates, minimum rate `0.7596153846`, `corporate_action_continuity_certified=false`. Stage 2 used official KSEI only: 77 pages, 100 candidates, 1 parsed exact document, 1 exact link, 94 unresolved links. Small artifacts promoted; raw/full ledgers external. No V4 target/model/outcome work. |
| V4 CA Voluntary-Conversion Semantics Remediation V1 | `REVIEW` | `Codex/V4-CA-Voluntary-Conversion-Remediation` | `data/idx-v4-ca-voluntary-conversion-semantics-remediation-v1` / final `5b9afc24b758413f315351971b2cd07f634dc9c9` | One offline remediation run complete from scientific parent `data/idx-v4-ca-event-window-semantics-v1@96a652b311f868babab94ca24b32bf1df382627c`; source/config anchor `fc6ede265abeae97f6871f7b852e84aa669c159b`. Relevant events `102`: exact `41`, schedule-required `61/51`; strict voluntary-cash reclassification `0/29`. Frozen 610 tickers / 600 dates remain blocked: `0/600` H5/H10/consensus dates meet `>=90%`, minimum rate `0.7912087912`, `corporate_action_continuity_certified=false`. Provider calls `0`; no schedule evidence, target/model, or outcomes. Small result artifacts and hashes promoted; full ledger external. Stop for ChatGPT review. |
| V4 CA voluntary-conversion forensic replay V1 | `REVIEW` | `Codex/V4-CA-VC-Forensic-Replay` | `data/idx-v4-ca-voluntary-conversion-forensic-replay-v1` / final `c2246e5e82dc642950017e38e57cd97700e15199` | Forensic replay PASS: parent `136` relevant events / `63` Voluntary Conversion; remediation `102`; `34` removed and `0` added. Strict security-to-currency predicate and actual non-blocking reclassification both `34`; remaining schedule-required Voluntary Conversion `29`; removed IDs exactly equal strict reclassified IDs. All 600 date rows changed. Verdict `FORENSIC_REPLAY_CONFIRMS_VOLUNTARY_CASH_RECLASSIFICATION_REPORTING_UNDERCOUNT`. Provider calls `0`; no schedule, target, model, performance, or protected/fresh-forward outcome access. Small artifacts/hash manifest promoted. Stop for ChatGPT review. |
| V4 CA residual document semantics V1 | `REVIEW` | `Codex/V4-CA-Residual-Document-Semantics` | `data/idx-v4-ca-residual-document-semantics-v1` / final `67fc2c7f3bef7feee4c95890ea4c074ffb373712` | Stage-2 attestation PASS: 100 candidates, 98 successful, 97 verified raw paths, 2 provider-failed. Stage A PASS: 241 candidate rows, 22 exact non-blocking, 1 exact transition, 0 conflicts, 38 unresolved across 61 residual events. Stage B exact command attempted once but blocked before output because required `corporate_action_event_evidence.csv` is absent; available file is `event_family_evidence.csv`, no substitution/retry. Continuity verdict and certification not evaluated. Provider calls `0`; no target/model/performance/protected/fresh-forward outcome access. Small Stage-A artifacts promoted. Stop for ChatGPT review. |
| V4 CA residual document continuity replay V1 | `REVIEW` | `Codex/V4-CA-Residual-Continuity-Replay` | `data/idx-v4-ca-residual-document-continuity-replay-v1` / final `489891211b872e7f0c561f85af1cb8221f4d00ef` | Stage-B-only replay completed with hash-pinned promoted `event_family_evidence.csv`: verdict `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`, `corporate_action_continuity_certified=false`, relevant/exact/schedule-required events `80/42/38`, schedule-required tickers `34`, and `0/600` H5/H10/consensus dates meeting `>=90%`. Minimum rates H5/H10/consensus `0.8237179487/0.8216560510/0.8216560510`. Stage-A overlay copied: exact non-blocking `22`, exact transition `1`, conflicts `0`, unresolved `38`. Provider calls `0`; no Stage-A rerun, target/model/performance/protected/fresh-forward outcome access. Small Stage-B artifacts promoted. Stop for ChatGPT review. |
| V4 CA blocker attribution V1 | `REVIEW` | `Codex/V4-CA-Blocker-Attribution` | `data/idx-v4-ca-blocker-attribution-v1` / final `052351372215a5752199513a23cf3f7373ac1f59` | Validation PASS: `8 passed`, `py_compile` PASS, diff-check PASS; Stage-B ledger SHA exact `585a9c55...`. One offline attribution run completed with verdict `OPTIMISTIC_ATTRIBUTION_COVERAGE_DIMENSION_ALONE_CAN_CLEAR_GATE_SCHEDULE_ALONE_CANNOT`. Baseline fails `0/600`; schedule-only ceiling fails `586/600` consensus; KSEI-coverage and all-coverage optimistic ceilings pass `600/600`. Known mechanical crossings `227` never waived. Provider calls `0`; no semantic/provider/target/model/performance/protected/fresh-forward outcome work. Small artifacts promoted. Stop for ChatGPT review. |
| V4 CA blocker attribution V2 | `REVIEW` | `Codex/V4-CA-Blocker-Attribution-V2` | `data/idx-v4-ca-blocker-attribution-v2` / final `1ae3d8f36010a717491ad47396f73dd63bb5e864` | Validation PASS: `13 passed`, `py_compile` PASS, diff-check PASS; exact post-KSEI ledger SHA verified and one offline run completed with verdict `OPTIMISTIC_ATTRIBUTION_V2_MULTIPLE_MINIMAL_CLEARING_SCENARIOS`. Baseline remains `462/461/461` H5/H10/consensus dates with minimum rates `0.8814102564/0.8789808917/0.8789808917`; optimistic `SCHEDULE_ONLY_CEILING` and `ALL_COVERAGE_CEILING` pass as upper bounds only. Known mechanical rows `240` never waived. Provider calls `0`; no CA semantic, target/model/performance/protected/fresh-forward outcome work. Small artifacts and result checkpoint/handoff promoted. |
| V4 CA schedule event impact attribution V1 | `REVIEW` | `Codex/V4-CA-Schedule-Event-Impact` | `data/idx-v4-ca-schedule-event-impact-attribution-v1` / final `a7a3b998930cf0506d3ddc9cbbd21636ba6f3e93` | Validation PASS: `13 passed`, `py_compile` PASS, diff-check PASS; exact ledger/schedule-needs SHAs verified and one offline run completed. Critical events `34/39`; deterministic inclusion-minimal selected subset `7` (NISP, ISAT, ADRO, PANI, RAJA, PTRO, CUAN) counterfactually yields `600/600/600` with minimum H5/H10/consensus rates `0.9038461538/0.9012738854/0.9012738854`. Exact global minimum not proven (`NOT_RUN_CRITICAL_UNIVERSE_ABOVE_EXACT_BOUND`); result is optimistic acquisition-priority only. Provider calls `0`; no schedule acquisition, KSEI retry, semantic, target/model/performance/protected/fresh-forward outcome work. Small artifacts and result checkpoint/handoff promoted. |
| V4 KSEI coverage-gap remediation V1 | `REVIEW` | `Codex/V4-KSEI-Coverage-Gap` | `data/idx-v4-ksei-coverage-gap-remediation-v1` / final `8414ff04f4e89afafd07a55b7065e0f585bb7235` | Import-path retry validation PASS: focused pytest `7 passed`, `py_compile` PASS, diff-check PASS, zero-network preflight PASS with exact 43-ticker identity SHA. One targeted official KSEI run recovered `31/43` tickers (`636` history rows, `24` active mechanical/unknown rows), leaving `12` unresolved; provider requests/raw captures `76/76`, acquisition manifest SHA `7e86f5e5...85f50`. One outcome-blind continuity replay then returned `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`, `corporate_action_continuity_certified=false`, coverage `598/610`, and minimum H5/H10/consensus rates `0.8814102564/0.8789808917/0.8789808917` below the frozen `0.90` gate. No source/config patch, model/target/performance/protected/fresh-forward outcome work. Small result artifacts and dated checkpoint/handoff promoted on branch. |
| V4-X session-aligned counterfactual sensitivity audit V1 | `REVIEW` | `Codex/V4-X-Session-Sensitivity` | `audit/session-aligned-counterfactual-sensitivity-v1` / final `e18e85bb4c3328ba056bfced662abeeb0f709855` | Outcome-blind, provider-free audit complete after the exact PIT listing filter. On frozen V4-X union support (`241,724` rows / `629` tickers), strict official-session semantics changed `241,044` model-control rows (`99.718687%`), including `225,326` spillover-only rows; H5 `148,898/241,487`, H10 `146,188/239,836`. All gap attributions were within-listing no-panel-row; no pre/post-listing or unresolved identity cases. Focused `4 passed`; full suite `495 passed / 1 unrelated pre-existing storage failure`; no provider, repair, refit/score, target, protected/fresh-forward outcome, parent mutation, or frozen V4-X definition change. Result checkpoint/handoff and external manifest `049c4e40...3c0482` are pushed. Separate challenger preregistration is recommended for review; no automatic continuation. |
| V4-X session-aligned representation magnitude audit V1 | `REVIEW` | `Codex/V4-X-Session-Magnitude` | `audit/session-aligned-representation-magnitude-v1` / `9ca518fa44a205ba7d08b74c76e94d1811675b3e` | Outcome-blind magnitude run complete on exact parent V4-X support: union `241,724` rows / `629` tickers / `986` dates; any XS-rank delta >=1pp `133,778` (`55.343284%`), >=2.5pp `36,527` (`15.111036%`), >=5pp `9,564` (`3.956579%`), >=10pp `724` (`0.299515%`); row max-rank p50/p95 `0.0109992/0.0458768`; finite-to-missing `15,863`; date-correlation <0.999/<0.99/<0.95/<0.90 `443/143/2/0`; top-decile Jaccard p50/min `0.96/0.5`. Manifest `034daeade37b5e58d34f55c9f098a94ebc8fe63cba6e3e9827bef78dc5b8cf4d`; focused `4 passed`; full `495 passed / 1 unrelated pre-existing storage failure / 3 warnings`; no provider, repair, feature-definition, primary-liquidity, model, target/outcome, parent mutation, or V4-X2 preregistration. Stop for independent review. |
| V4-X clean-data consolidation V1 | `REVIEW` | `Codex/V4-X-Clean-Data-Consolidation` | `data/v4-x-clean-data-consolidation-v1-final-input-freeze-v1` / `30fcc9b353ec2f182649f8e18ced58d73f7c62c9` | Fresh final clean input bundle materialized and hash-verified under external manifest `ba246efe988c9caaba1af804d1b61b316dc7ad12579959f9dd1bac37f25e4351`: final security master `979/979`, accepted FINN + FREN overlay `2/2`, Stage-A panel bytes unchanged. Stage-C manifest `5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61` and decision `V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION` preserved. Focused `15 passed`, py_compile/diff-check PASS; full pytest has one unrelated pre-existing storage assertion failure. No refit, reset-counter, provider, score, target, label, protected/fresh-forward outcome, or model work. Independent review required before deterministic replay/refit. |
| PIT sector history | `PARKED` | `ChatGPT/PIT-sector-revival review` | `data/idx-pit-sector-history-revival-v1` / acceptance `5c9cb42a9b40774a5672f7487ce46ad94a806bed` | Targeted revival accepted fail-closed: canonical inventory remains `5 ready / 3 blocked`. 2023 is near-resolved (`Peng-00158`, BMTR effective 2023-07-03) but official IDX bytes are unavailable; reopen only on direct official archive recovery or a separately frozen verified-official-mirror methodology review. No dependent modeling. |
| Broker / Margin source audit V0 | `DONE` | `ChatGPT independent review + Codex` | `data/broker-margin-source-audit-v0` / live audit `567ec03` / acceptance `c7fcec2` | `BROKER_MARGIN_SOURCE_LIVE_AUDIT_ACCEPTED_MARGIN_FLOW_REJECTED`: Zapi parity to official IDX passes; literal All-Stock-filter H2 fails; H1 margin-financing flow is unsupported. Treat only as an official Margin category/reporting view with exact inclusion/aggregation semantics and PIT timing unresolved. No margin-usage/leverage/crowding features, automation, or bulk backfill. |
| Frontend monitoring / capture system | `REVIEW` | `Codex/Frontend Editorial Tech` | `codex/frontend-compare-v2` / `bc91a5f` | Read-only monitoring now presents the automated session archive and all three monitored lanes: O2, V3-B, and V2. UI was simplified to a compact archive, three score cards, and a slim shared-session summary; manual capture/date controls remain removed. Build and `/monitoring`, `/compare`, and `/api/monitor/status` HTTP 200 pass. Local runtime reports V2 + V3-B artifacts for 2026-08-10; O2 remains awaiting runtime score artifact. |
| Market/index prospective EOD archive extension | `AUTOMATED` | `Codex/Forward-EOD-Automation-UI` | `integration/forward-eod-automation-monitoring` / `666ec11` | Canonical `IDXTrade-ForwardEOD` is installed and `Ready`: daily 18:00 Asia/Jakarta plus logon catch-up, StartWhenAvailable, IgnoreNew, network guard, and existing repo/runtime paths. Legacy Open task is Disabled; first scheduled run remains pending. |
| Foreign Flow prospective canonical sidecar | `DONE` | `ChatGPT/Foreign-Flow-Forward-Capture` | `data/idx-foreign-flow-forward-capture-v1` / final `32bb1390303b9103ac53c6faa4d521c1352ee940` | Prospective SHARES sidecar hardening and offline runtime validation accepted: strict integer semantics, canonical parent/raw verification, exclusive no-overwrite artifacts, 18 focused tests, full pytest `280 passed`. No scheduler integration. |
| Foreign Flow historical acquisition and coverage census | `DONE` | `ChatGPT independent review + Codex/Foreign-Flow-Historical-Acquisition` | `data/idx-foreign-flow-historical-acquisition-v1` / accepted result `3297d060413849cd4934b9c475c1166ba7d76412`; metadata repair `6b00624` | `FOREIGN_FLOW_HISTORICAL_ACQUISITION_V1_ACCEPTED`: official IDX Stock Summary acquisition complete for the defensible frozen session union `2021-04-01..2026-08-13`: `1,288/1,288` sessions, `1,129,024` rows, `983` unique tickers, `0` errors, `42.5340%` zero-flow rows. 2018–2019 sampled dates were empty; 2020-01-02 was valid but a complete 2020 official session calendar was not established, so no older completeness claim. Unit SHARES; retrospective label `OFFICIAL_IDX_HISTORICAL_EOD / RETROSPECTIVELY_ACQUIRED`; causality starts session t+1. External archive only; no Financial PIT timestamp hard gate, models/outcomes/scheduler changes. Archive manifest SHA `fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334`. |
| Foreign Flow feature contract V1 | `ACTIVE` | `Codex/Foreign-Flow-Feature-Contract` | `research/idx-foreign-flow-feature-contract-v1` / base `c957fe7` | Feature contract plus offline materialization/coverage audit only over accepted external archive `D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1`. Freeze causal t→t+1 formulas, session-aware/listing-aware joins, missing/applicability semantics, and leakage tests before any outcome/performance test. No provider calls, Financial PIT, Corporate Actions, O2, scheduler, models, or protected outcomes. |
| AKSes adapter schema V1 | `REVIEW` | `ChatGPT/AKSes-Adapter-Prep` | `integration/schema-hardening-v2` / HEAD `66f6f13398134bb7fb7e85719d78c2c354e5acbf` | `ROUND2_REWORK_REMEDIATED_REVIEW3`: explicit timezone schema+semantic gate, one authoritative canonical semantic validator, endpoint arithmetic/failure/detail/summary reconciliation, direct duplicate-payload rejection, and factory-origin `SubaccountRef` hardening are prepared. No KSEI network/account/provider access, credential use, public API/UI, or public Ownership/KSEI changes. Exact branch pytest must be rerun independently; stop for review round 3. |
| Canonical IDXTrade-ForwardEOD automation audit | `DONE` | `Codex/Forward-EOD-Automation-Audit` | `integration/forward-eod-automation-monitoring` / `666ec11` | Installation and read-only verification complete; checkpoint `2026-08-13_FORWARD_EOD_AUTOMATION_INSTALLED` pushed. Stockbit remains separate/Ready, task/runtime credential scans are clean, and no provider capture was triggered. |
| Canonical EOD adversarial test-gap audit | `DONE` | `ChatGPT independent review + Codex/EOD-Test-Gap-Audit` | `codex/idx-eod-adversarial-tests-v1` / reviewed HEAD `7b21c50d278b13c8e94cdebddd4ca35765d7274e` / acceptance `f6a50cfcba3611c89bd71ee1b6b12d9da3dee51a` | `CANONICAL_EOD_ADVERSARIAL_HARDENING_ACCEPTED_NOT_YET_DEPLOYED`: exact-session, semantic artifact/manifest, stale-lease, provider validation, O2-counter idempotency, and owner-lock hardening accepted; focused 69 passed, full 286 passed, `git diff --check` PASS. Scheduled canonical checkout remains `integration/forward-eod-automation-monitoring@b94b272`, so a separate controlled integration/deployment verification is required before these protections are operationally active. Provenance/P1 remediation remains separate. |
| Repository-wide scientific integrity and reproducibility audit | `DONE` | `ChatGPT independent review + Codex/Scientific-Integrity-Audit` | `codex/scientific-integrity-audit-v1` @ `1a3d785b10e33af1f6f723fb4a23cf8a61980b0a` / acceptance `31b88496bcbf91bb7772351ab6c3e1df206b2375` | `REPOSITORY_SCIENTIFIC_INTEGRITY_AUDIT_ACCEPTED_NO_GO_FOR_REPRODUCIBLE_RESEARCH_RELEASE`: concrete current-main fail-open boolean/date/OHLCV/provenance paths independently verified. Historical model verdicts are not reversed. Remediation remains owned by active EOD/provenance lanes; reconsider release readiness only after P1 fixes and re-audit. |
| Frozen V2/V3-B/O2 training-lineage impact audit | `REVIEW` | `Codex/Frozen-Lineage-Impact-Audit` | `codex/frozen-lineage-impact-audit-v1` / HEAD `9395b5c26e0db1a280acee4cac9d5fa76d198e8c` | Forensic audit complete: V2, V3-B, and O2 are `TRAINING_LINEAGE_IMPACT_FOUND` because KOCI's pre-listing panel row entered causal feature construction and downstream context. Checkpoint and handoff pushed; no provider calls, protected outcomes, experiments, retraining, or active-owner remediation. Await ChatGPT independent review. |
| PIT Security Identity / Listing-Domain V1 adversarial audit | `REVIEW` | `Codex/PIT-Security-Identity-Audit` | `audit/pit-security-identity-stage-c-v1` / `a8c30b2076530c8777b4e7350f4452f51f1f0575` | Stage C complete: exact V4-X H5/H10 final-training support intersection is affected by identity-omission spillover. H5 `153,037/241,487` rows across `688/986` dates; H10 `151,788/239,836` across `684/982`; direct FREN intersection `0`, spillover-only union `153,136` rows / `555` tickers. Decision `V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION`; clean refit required after cross-lane consolidation. State-only projection only; numeric target ranks/returns/labels, predictions, models, providers, protected/fresh-forward outcomes, and counters remain locked. External manifest `5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61`. |
| PIT-safe V2/V3-B/O2 historical reproduction | `DONE` | `ChatGPT independent review + Codex/PIT-Safe-Lineage-Reproduction` | `codex/pit-safe-v2-v3b-o2-reproduction-research-v1` / HEAD `765bdba` / acceptance `review/idx-pit-safe-replay-acceptance-v1@2a70031` | `PIT_SAFE_HISTORICAL_REPLAY_ACCEPTED_CLEAN_DEVELOPMENT_DECISION`: clean historical parent is V2 `HGB_XS_MARKET`; V3-B fails its frozen late paired gate and is not rescued; O2 raw diagnostic stays `O2_SURVIVOR` but clean-lineage status is `O2_DIAGNOSTIC_ORPHANED_PARENT`. No canonical fitted model identity, forward counter, provider call, or fresh-forward outcome access. |
| Clean V2 Open-alpha research pass (V2.1/V2.2) | `DONE` | `ChatGPT independent review + Codex/Clean-V2-Open-Alpha-Prereg` | `research/idx-v2-open-alpha-prereg-v1` / HEAD `d9e0cd8` / acceptance `review/idx-v2-open-alpha-historical-acceptance-v1@4802185` | `CLEAN_V2_OPEN_ALPHA_HISTORICAL_ACCEPTED_RETAIN_CLEAN_V2`: exact 277,244 / 729 common-support run accepted. V2.1 and V2.2 both fail the frozen q25 paired PR-AUC gate; clean V2 `HGB_XS_MARKET` remains the surviving historical architecture. Lane closed: no V2.1/V2.2 rescue, V2.3, six-Open combination, alternate gate, or post-outcome tuning. Historical acceptance does not create a canonical refit/model identity or prospective counter. |
| Canonical data-source / provenance registry | `REVIEW` | `Codex/Provenance-Registry` | `codex/data-source-provenance-registry-v1` / `639fcb8` | Registry, JSON Schema, fail-closed validator, documentation, and tests complete; focused registry suite `9 passed`; full pytest has one pre-existing untouched storage assertion failure (2 revision conflicts vs expected 1). No providers, data, outcomes, experiments, or scientific remediation. Await ChatGPT review. |
| Direct IDX endpoint discovery audit | `DONE` | `ChatGPT independent review + Codex/IDX-Direct-Endpoint-Audit` | `data/idx-direct-endpoint-audit-v1` / reviewed HEAD `52c369ae` / acceptance `87e6947c0121aba52111d3dc633e05448f6da644` | `DIRECT_IDX_ENDPOINT_DISCOVERY_ACCEPTED_PARTIAL_SOURCE_USEFUL_NOT_PIT_READY`: direct transport validated for bounded discovery; `GetIssuedHistory` retained only as candidate event/share-count ledger, `GetFinancialReport` only as filing/provenance metadata, ratio sector fields rejected for PIT history. No bulk acquisition or canonical source promotion. |
| Financial PIT direct IDX publication-chain audit | `DONE` | `ChatGPT independent review + Codex/Financial-PIT-Direct-Audit` | `data/financial-pit-v1` / reviewed HEAD `64d52dbf` / acceptance `25eaa67a7f5446234db470756fe8b5c12cbb7696` | `FINANCIAL_PIT_DIRECT_IDX_SOURCE_AUDIT_ACCEPTED_PARTIAL_SOURCE_USEFUL_PIT_COVERAGE_INCOMPLETE`: direct report→announcement publication linkage and attachment-byte identity accepted for bounded samples; FY2022/Q1-2023 publication linkage remains retention-blocked, pagination must fail closed, and immutable restatement/version completeness is unproven. No bulk acquisition, feature derivation, or modeling. |

| Financial PIT direct-IDX adapter and coverage census | `DONE` | `ChatGPT acceptance review/idx-financial-pit-adapter-census-acceptance-v1` | `data/financial-pit-adapter-census-v1` / final `d1cb537e` (result `5f600f9c`) / acceptance `723200c32e06d99831b8ea43700fe695c397e4a0` | Adapter + bounded 2024–2026 census accepted as `PARTIAL_SOURCE_USEFUL_PIT_COVERAGE_INCOMPLETE`. 7,370 expected issuer-periods / 6,580 reports / 6,212 relevant announcement filename matches / 6,108 exact dual-byte hash joins / 0 PIT-ready because statement scope remains unresolved. Blockers and raw external evidence remain preserved; no facts/features/models/outcomes. Next authorized milestone is bounded statement-scope granularity feasibility. |

| Financial PIT statement-scope granularity feasibility | `DONE` | `ChatGPT independent review + Codex/Financial-PIT-Statement-Scope` | `data/financial-pit-statement-scope-v1` / final `e4537c1` / remediation `68fe984` / acceptance `review/idx-financial-pit-adapter-census-acceptance-v1@8675b0bc05327779a3f39d4b1a3f90b2bfcda551` | `FINANCIAL_PIT_STATEMENT_SCOPE_RESOLVER_ACCEPTED_OFFLINE_RECLASSIFICATION_NEXT`: XLSX visibility and exact IDX-DEI+`CurrentYearInstant` XBRL authority gates accepted; immutable 11/11 sample remains 7 consolidated / 4 separate. PDF empirical coverage remains unproven and fail-closed. Next authorized milestone is offline scope reclassification/PIT-ready coverage recomputation over the existing 6,108 exact joins only; no network/redownload/facts/features/models/outcomes. |
| Financial PIT offline scope reclassification and PIT-ready coverage | `DONE` | `ChatGPT independent review + Codex/Financial-PIT-Offline-Reclassification` | `data/financial-pit-offline-scope-reclassification-v1` / final `45d36ed` / acceptance `review/idx-financial-pit-offline-reclassification-acceptance-v1@7c94bc8a87374a75fc73687c04c4f8b5b7146595` | `FINANCIAL_PIT_OFFLINE_RECLASSIFICATION_ACCEPTED_FACT_TABLE_DESIGN_NEXT`: 5,965 PIT-ready rows accepted (4,410 consolidated / 1,555 separate), equal to 97.658808% of 6,108 exact joins and 80.936228% of 7,370 expected issuer-periods; 143 unresolved and all prior publication/linkage/hash/provider failures remain fail-closed. Canonical v2 artifact hashes pinned; no network/redownload/facts/features/models/outcomes. Next authorized milestone is bounded version-aware fact-table schema/extraction feasibility; no market-wide fact extraction or modeling yet. |

| Financial PIT fact-table schema and extraction feasibility | `DONE` | `ChatGPT acceptance review` | `data/financial-pit-fact-schema-v1` / final `fce0468` / acceptance `4013f90a56edc6d8409e6a7514a9170d5f301aff` | `BOUNDED_SCHEMA_FEASIBILITY_ACCEPTED_MARKET_WIDE_EXTRACTION_STILL_BLOCKED`: version-aware append-only schema and bounded 36-filing evidence audit accepted; market-wide fact extraction remains separately blocked pending correction/restatement lineage, unsupported/PDF policy, unit/scale and taxonomy/version gates. |
| Financial PIT correction/restatement lineage audit | `DONE` | `ChatGPT acceptance review/idx-financial-pit-revision-lineage-acceptance-v1` | `data/financial-pit-revision-lineage-v1` / final `58e5e26de4646794a38e844decf54890696375c5` / acceptance `903e843f3f53c14e7bdc7fb1e3d959f2cfe62a66` | Bounded lineage result accepted: RONY FY2024, BAPA FY2025 and MUTU H1-2025 each expose two independently retrievable versions with distinct publication timestamps and distinct XLSX/inlineXBRL/instance bytes; current report pointers resolve to latest; fail-closed observed-version policy accepted. No market-wide extraction, unit/scale repair, features, models, or protected outcomes. |
| Financial PIT fact-extraction semantic hardening | `DONE` | `ChatGPT acceptance` | `data/financial-pit-fact-extraction-hardening-v1` / HEAD `baf0334a1dd6a31e9d88ae978630ec864bfb3410` / acceptance `FINANCIAL_PIT_FACT_EXTRACTION_HARDENING_ACCEPTED_MARKET_WIDE_OFFLINE_EXTRACTION_CENSUS_NEXT` | Bounded hardening accepted: 197/212 candidates extracted; all 42 former unit cases and 14 former repeated-label conflicts resolved safely; 15 prior-period XBRL rows remain fail-closed. No network/redownload, ratios/features, models, or protected outcomes. |
| Financial PIT market-wide offline fact extraction census | `DONE` | `ChatGPT independent review + Codex/Financial-PIT-Marketwide-Fact-Extraction-Census` | `data/financial-pit-marketwide-fact-extraction-census-v1` / HEAD `419f0be54a7b08ee958c52b8a727be9423286d96` / acceptance `review/idx-financial-pit-marketwide-census-acceptance-v1@4c68b5a3259e89782f6263857630089b93ed04e8` | `FINANCIAL_PIT_MARKETWIDE_FACT_CENSUS_ACCEPTED_TEMPLATE_DRIFT_AUDIT_REQUIRED_BEFORE_FEATURE_CONTRACT_FREEZE`: census/reproducibility accepted, but candidate density drops from ~6.1–6.2 facts/filing through 2024 and 2025 Q1 to ~1.4–1.8 from 2025 H1 onward. Because absent canonical labels are recorded as missing rather than candidate failures, the 99.6416% candidate extraction rate does not establish true semantic coverage. Next allowed milestone is a separately claimed bounded missing-fact/template-drift + co-occurrence audit over immutable corpus; no feature materialization or model work yet. |
| Financial PIT missing-fact / template-drift audit | `DONE` | `ChatGPT acceptance review/idx-financial-pit-template-drift-acceptance-v1@22774855350d5a75b1b568d59b38f0d7205908aa` | `data/financial-pit-template-drift-audit-v1` / HEAD `f2238f35546db0934e7ce1203cefc57fa05eec86` | `FINANCIAL_PIT_TEMPLATE_DRIFT_AUDIT_ACCEPTED_STRICT_SCIENTIFIC_NOTATION_REMEDIATION_NEXT`: exact labels retained; scientific-notation rejection explains the coverage collapse. Next bounded step is parser-only remediation plus the same offline census; no feature design yet. |
| Financial PIT strict scientific-notation parser remediation + census | `DONE` | `ChatGPT acceptance` | `data/financial-pit-scientific-notation-remediation-v1` / HEAD `98f409cda9943cc06747e875153c231d950a3221` / acceptance `review/idx-financial-pit-template-drift-acceptance-v1@22774855350d5a75b1b568d59b38f0d7205908aa` | `FINANCIAL_PIT_STRICT_SCIENTIFIC_NOTATION_REMEDIATION_ACCEPTED_FEATURE_CONTRACT_DESIGN_NEXT`: strict exponent parsing plus visible inline/shared-string routing recovered the predicted coverage; 37,167 extracted facts and 4,287 complete eight-fact filings match the accepted audit prediction. No feature design, model, or protected-outcome work was performed in that lane. |
| Financial PIT feature-contract design V1 | `DONE` | `Codex/Financial-PIT-Feature-Contract` | `data/financial-pit-feature-contract-v1` / HEAD `6b510d8d254dd47973e749ffeae7cf1569069395` | `FINANCIAL_PIT_FEATURE_CONTRACT_V1_ACCEPTED_PERIOD_BOUNDARY_REMEDIATION_NEXT`: contract and fail-closed offline dry-run accepted for review; next lane is bounded offline period-boundary recovery. |
| Financial PIT period-boundary remediation V1 | `DONE` | `Codex/Financial-PIT-Period-Boundary` | `data/financial-pit-period-boundary-remediation-v1` / final `09e8e8eba738e4dcea3c871f0eda83b53cc07c42` | `FINANCIAL_PIT_PERIOD_BOUNDARY_REMEDIATION_V1_ACCEPTED_FEATURE_MATERIALIZATION_NEXT`: exact offline sidecar accepted; `5,965/5,965` instant boundaries, `5,962/5,965` duration boundaries, `37,239/37,246` fact rows explicitly verified. Three filings remain fail-closed (LEAD/UNVR chronology conflicts; VTNY missing XBRL start). Manifest-pinned availability dry-run uses GENERAL + CONSOLIDATED only; no annualization/TTM, feature values, network/redownload, models, or protected outcomes. |
| Financial PIT feature materialization V1 | `DONE` | `ChatGPT review + Codex/Financial-PIT-Feature-Materialization` | `data/financial-pit-feature-materialization-v1` / final `7b5ed76c934b32cc7d995cc93870ac16d797e9e4` | `FINANCIAL_PIT_FEATURE_PANEL_V1_ACCEPTED_MODEL_EXPERIMENT_PREREGISTRATION_NEXT`: exact 13-feature offline panel accepted from immutable facts + manifest-pinned boundaries, GENERAL + CONSOLIDATED only. `258,401` rows / `531` issuers / `4,226` issuer×as-of keys / `150,407` AVAILABLE values; 7 unresolved boundary facts excluded, knowledge-time violations `0`, period/provenance and deterministic-hash checks PASS. No outcomes, model fitting, O2 changes, provider calls, or redownloads. |
| Financial PIT Alpha V1 preregistration + support census | `REVIEW` | `Codex/Financial-PIT-Alpha` | `research/idx-financial-pit-alpha-v1` / final `1a9bf7267728d9beec2a975ac4b4e931d0be16d0` / executable code `507aaf8bca3286996eb30f3f8e7ea161d8892cc1` / frozen contract external `D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-financial-era-contract` / base clean V2 `research/idx-v2-open-alpha-prereg-v1` | `FINANCIAL_PIT_ALPHA_V1_NO_SURVIVOR`: exact completion run finished all 9 fits under the unchanged contract. Primary `V2_PLUS_FINANCIAL` vs `CONTROL_FINANCIAL_ERA` had median PR delta `+0.001278`, q25 PR delta `-0.014714`, positive folds `2/3`; median ROC and Q5-Q1 both regressed, triggering the frozen guardrail. No rescue, refit, promotion, O2, fresh-forward, or protected-outcome access. Full result checkpoint/handoff pushed; external manifest SHA `07241cc863315a354e241f4f60e9bb7554a5ad8c927fc0bf3472a1024f5ef70a`. |
| Financial Representation V2 structural audit | `REVIEW` | `Codex/Financial-Representation-V2` | `research/idx-financial-representation-v2` / final `f2f401e3e68893426858a60e1093832cf122bd41` | Outcome-blind structural audit complete: 277,244 support rows / 729 tickers; 70,520 CORE3 rows. Both YoY variants have 34,412 rows but are structurally inadmissible because both are completely absent from V2F4 training. Recommended block is `CORE3`; same-bundle, provenance, and 18:00 knowledge-time gates pass. Focused tests `3 passed`; full pytest `64 passed / 1 unrelated pre-existing storage failure`. No labels, predictions, performance artifacts, model fit/score, O2, fresh-forward, or protected-outcome access. Await ChatGPT review before Financial Alpha V2. |

| Corporate Action PIT source audit | `REVIEW` | `Codex/Corporate-Action-PIT-Source-Audit` | `data/corporate-action-pit-source-audit-v1` / result `2de089f0e48ae2ee74ffd16c4361155a04dccc30` | Bounded live official IDX + public KSEI source/semantics audit completed. Verdict `CONDITIONAL_SOURCE_USEFUL_PIT_LINKAGE_INCOMPLETE`: discovery useful, but strict PIT event linkage remains incomplete. No bulk backfill, OHLC adjustment, Financial PIT/Foreign Flow changes, features/models, outcomes, or O2/forward work. |
| Corporate Action PIT deterministic linkage V1 | `REVIEW` | `Codex/Corporate-Action-PIT-Deterministic-Linkage` | `data/corporate-action-pit-deterministic-linkage-v1` / final `5222af3b68bf86765c43017912e990edf02148ad` | Bounded result: 5/5 official KSEI schedule documents parsed, 5/5 schedule-locator/document identities exact, MEGA append-only revision exact via prior KSEI reference, SINI rights identity exact, MLPT/RAJA split-family precedence verified. KSEI evidence remains DATE_ONLY; MLPT IDX correction timestamp is retained separately with explicit KSEI-linkage caveat. Full pytest 64 passed / 1 pre-existing unrelated storage expectation failed. No market-wide backfill, canonical table, OHLC adjustment, models, outcomes, Foreign Flow, Financial PIT, or AKSes. |
| Corporate Action PIT availability provenance V1 | `REVIEW` | `Codex/Corporate-Action-PIT-Availability-Provenance` | `data/corporate-action-pit-availability-provenance-v1` / HEAD `314b99a3a91e2297fa0061a52849ee3c64d60222` | Semantic remediation and bounded audit complete over 34 official KSEI PDF records. Verdict `KSEI_ASSET_TIMESTAMP_CANDIDATE_ONLY`: 16 strict filename candidates, 18 generic names, YOII +5-day counterexample, 0 exact KSEI↔IDX timing linkages. External manifest `D:\Documents\Project\idx-corporate-action-pit-availability-20260814-v1-final\MANIFEST.json` SHA `c8f8639b2d076fd91cb684925c6a0c6c13d2e3ed87a2e7a2fc0da8cad69a39f7`. No market-wide backfill, canonical table, session mapping, OHLC adjustment, models, outcomes, Foreign Flow, Financial PIT, AKSes, or O2/forward changes. |

## Current status overrides (2026-08-14)

| Lane | Status | Owner / acceptance | Branch / HEAD | Scope note |
|---|---|---|---|---|
| Corporate Action PIT availability provenance V1 | `DONE` | ChatGPT acceptance `review/idx-corporate-action-pit-availability-acceptance-v1@4f776a8f34eda012d4368287fe37699d4c8dc0dc` | `data/corporate-action-pit-availability-provenance-v1` / `50718c3f23352444630160dc54934eaa2201289d` | Accepted bounded result; availability timestamps remain unverified. |
| Corporate Action KSEI→IDX publication linkage V1 | `ACTIVE` | `Codex/Corporate-Action-PIT-IDX-Publication-Linkage` | `data/corporate-action-pit-idx-publication-linkage-v1` | Bounded 8–15 event linkage audit only; no market-wide acquisition or modeling. |

## Current result overrides (2026-08-14)

| Lane | Status | Owner / acceptance | Branch / HEAD | Scope note |
|---|---|---|---|---|
| Corporate Action KSEI→IDX publication linkage V1 | `REVIEW` | ChatGPT independent review pending | `data/corporate-action-pit-idx-publication-linkage-v1` / `13c54861821998d2148d0a8df6252d6dc1a8cd64` | Bounded 11-row audit: 6 exact, 4 unresolved, 1 conflict. Exact attachment-level economic anchors yield `IDX_TIMESTAMP_CONFIRMED`; ambiguity/conflict remains null. External manifest `D:\Documents\Project\idx-corporate-action-pit-idx-publication-linkage-20260814-v1\MANIFEST.json` SHA `25714d922a1bbd3410babd60e041dca64eb9e4fdbb517ec5e02928d3910eb306`. Focused 37 passed; full suite retains 1 unrelated storage failure. No market-wide acquisition, canonical table, OHLC adjustment, models, outcomes, or other lane changes. |

## Current remediation overrides (2026-08-15)

| Lane | Status | Owner / review | Branch / base | Scope note |
|---|---|---|---|---|
| Corporate Action IDX publication linkage V1 remediation | `ACTIVE` | `Codex/Corporate-Action-PIT-IDX-Publication-Linkage-Remediation`; independent review `36774d172efd7c742e760053c1ab4c366b49d3cd` | `data/corporate-action-pit-idx-publication-linkage-remediation-v1` / scientific base `13c54861821998d2148d0a8df6252d6dc1a8cd64` | Offline-only evaluator remediation over the same immutable 11 rows and parent manifest; no provider calls, market-wide acquisition, canonical table, OHLC adjustment, models, or outcomes. |

## Current remediation result overrides (2026-08-15)

| Lane | Status | Owner / acceptance | Branch / HEAD | Scope note |
|---|---|---|---|---|
| Corporate Action IDX publication linkage V1 remediation | `REVIEW` | ChatGPT independent review pending; review source `36774d172efd7c742e760053c1ab4c366b49d3cd` | `data/corporate-action-pit-idx-publication-linkage-remediation-v1` / `dc34287de2e46531eb837d3d9f18623d64d158e0` | Offline same-11 rerate: `6 EXACT`, `0 AMBIGUOUS`, `1 CONFLICT`, `4 UNRESOLVED`; verdict `IDX_PUBLICATION_LINKAGE_BOUNDED_GO`. Remediation manifest `D:\Documents\Project\idx-corporate-action-pit-idx-publication-linkage-remediation-20260815-v1\MANIFEST.json` SHA `74e3703f1a043150d9bd9784336c32c1e3f6aca64ec8393d30df7458bf3b3f9e`. Focused 42 passed; full suite retains one unrelated storage assertion failure. No provider calls, market-wide acquisition, canonical table, OHLC adjustment, models, or outcomes. |

## Current remediation R2 overrides (2026-08-15)

| Lane | Status | Owner / review | Branch / base | Scope note |
|---|---|---|---|---|
| Corporate Action IDX publication linkage remediation R2 | `REVIEW` | ChatGPT independent review pending; review source `981e1586038d91392ac0397b12391a1cd37f010f` | `data/corporate-action-pit-idx-publication-linkage-remediation-r2-v1` / `3b74c78` | Offline same-11 rerate: `4 EXACT`, `0 AMBIGUOUS`, `3 CONFLICT`, `4 UNRESOLVED`; SINI/YOII rights-ISIN presence conflicts preserved fail-closed; verdict `IDX_PUBLICATION_LINKAGE_BOUNDED_GO`. Final manifest `D:\Documents\Project\idx-corporate-action-pit-idx-publication-linkage-remediation-r2-20260815-v1\MANIFEST.json` SHA `ce82b342af066fcea8cdf6b1679be57be29f1788305412ef018e6c21c0d465c7`. Focused 44 passed; full suite 83 passed/1 unrelated storage assertion failure. No provider calls, new cases, market-wide acquisition, canonical table, OHLC adjustment, models, or outcomes. |

## Cross-chat no-duplicate rules currently in force

- Do not create a second generic EOD capture system until the existing frontend/backend capture path and forward archive infrastructure are inspected.
  - Do not recreate Stockbit intraday automation.

## Current status correction — 2026-08-14

The `Foreign Flow feature contract V1` row above is superseded by this
checkpoint: status `REVIEW`, branch
`research/idx-foreign-flow-feature-contract-v1` at HEAD
`ff15f335f43db645db18769c082ea5ee8773a72e`. Causal remediation is complete:
`foreign_gross_to_volume_1` uses the prior official session; 1,102,650 rows
were rematerialized with 964,078 fully available, 137,592 partial, and 980
missing. Remediated feature SHA is
`059471948ad9efb5b2343d9aed729d04c5e3f2c01881153679db579b3a1d1733`; audit
manifest SHA is
`2341df7d7ff646dc8a13da2a45e9220e0c4c569017b373ca72daed18dcb377e4`.
Focused tests pass `9`; full suite is `49 collected, 48 passed, 1 failed`
on the unrelated storage expectation documented in the checkpoint. No
provider calls, outcomes, performance testing, models, O2, or other lanes
were touched.
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

## Current status correction — 2026-08-14 — Foreign Flow alpha lane

The Foreign Flow feature contract V1 is closed as `DONE` based on the accepted
branch `research/idx-foreign-flow-feature-contract-v1` at HEAD
`ff15f335f43db645db18769c082ea5ee8773a72e`, with verdict
`FOREIGN_FLOW_FEATURE_CONTRACT_V1_ACCEPTED`.

The new lane is claimed as `ACTIVE` by `Codex/Foreign-Flow-Alpha` on branch
`research/idx-foreign-flow-alpha-v1`. Scope is exactly one preregistered,
paired historical-development experiment: clean V2 `HGB_XS_MARKET` control
versus clean V2 plus all frozen Foreign Flow V1 features, on exact common
support. No subset rescue, provider calls, Financial PIT/Corporate Actions,
O2/forward-counter changes, protected/fresh-forward outcome access, or
post-result tuning is authorized.

## Current status correction — 2026-08-14 — Foreign Flow alpha result

The Foreign Flow feature contract V1 is now closed as `DONE` at
`research/idx-foreign-flow-feature-contract-v1` HEAD
`ff15f335f43db645db18769c082ea5ee8773a72e`, verdict
`FOREIGN_FLOW_FEATURE_CONTRACT_V1_ACCEPTED`.

The one-shot Foreign Flow alpha lane is complete and remains `REVIEW` for
ChatGPT independent review:
`research/idx-foreign-flow-alpha-v1` at HEAD
`d9fd985de9b0b1c8909574714c8c6f460517da62`.
Verdict: `FOREIGN_FLOW_V1_NO_SURVIVOR`. Exact common support was 292,631 rows,
737 tickers, and 1,231 sessions. The frozen paired PR-AUC gate failed with
median delta `-0.0026589351774433945`, Q25 delta
`-0.0030184760134138455`, and 2/6 positive paired PR folds.

External result root:
`D:\Documents\Project\idx-trade-foreign-flow-alpha-v1-20260814-001`.
Result manifest SHA-256:
`b13424ef614b60bcd5745974663cbc9b93ff7b80f1f15757e4fe052e2953c777`.
Focused tests passed `4`; full pytest was `52 passed, 1 failed` due to the
known unrelated storage revision-conflict expectation mismatch. No provider,
protected/fresh-forward outcome, O2/forward-counter, rescue, or model-line
integration work occurred. Do not launch a rescue experiment from this lane
without a new frozen specification and authorization.

## Current status correction — 2026-08-15 — Foreign Flow Representation V2

Foreign Flow Representation V2 is claimed as `ACTIVE` by
`Codex/Foreign-Flow-Representation-V2` on branch
`research/idx-foreign-flow-representation-v2` at reviewed starting HEAD
`ad19babb7794ddf2fcbfa82bf2ae695c246cbda0`. Scope is limited to offline
historical materialization and availability/behavior census using the accepted
Foreign Flow archive and clean-V2 causal full-cross-section market context.
No provider calls, outcome/label access, model fitting/scoring, Foreign Flow V1
alpha reuse, effective-supply/free-float work, Financial PIT, Corporate Action,
O2, or TradingView work is authorized in this lane.

## Current status correction — 2026-08-15 — Foreign Flow Representation V2 result

Foreign Flow Representation V2 offline materialization is complete and is now
`REVIEW` for ChatGPT independent review. Branch
`research/idx-foreign-flow-representation-v2` is synchronized at HEAD
`5c0bba250d9aac3b4789416080e4c242e9a2bb44`. The external output root is
`D:\Documents\Project\idx-trade-foreign-flow-representation-v2-20260815-001`;
manifest SHA-256 is
`4e8e7278b6505a356c2f95c4ac69a47cb4dc91803cc819cf6b0aaafbe34c98dc`.

The outcome-blind census contains 1,102,400 rows, 979 tickers, 1,259 feature
sessions, 318,592 fully available rows, 783,240 partial rows, and 568
all-missing rows. Exact next-official-session causality, own-history exclusion,
full-panel primary-liquid cross-sectional scope, zero duplicates, and zero
infinities passed. Focused tests passed 15/15. Full pytest is 63 passed / 1
unrelated pre-existing storage expectation failure. No provider, outcome,
model, V1-alpha, free-float, Financial PIT, Corporate Action, O2, or
TradingView work occurred. Do not start the Foreign Flow alpha experiment
until ChatGPT reviews the census.

## Current status correction — 2026-08-15 — Foreign Flow Representation V2 distribution review

The final outcome-blind distribution/behavior audit is documented and the lane
remains `REVIEW`. Branch
`research/idx-foreign-flow-representation-v2` is synchronized at HEAD
`10a72f25b840d3689e39352c779d95ca33c40f77`.

The audit finds healthy non-collapsed percentile/rank/persistence behavior and
retains the complete feature distributions, shock outlier counts/top-20
diagnostics, and full missingness table in
`docs/checkpoints/2026-08-15_FOREIGN_FLOW_REPRESENTATION_V2_FINAL_DISTRIBUTION_REVIEW.md`.
Repeated extreme-shock clusters remain an explicit data-quality review item.
No authoritative full-universe primary-liquid flag artifact was found; the
292,631-row clean-V2 prepared table is model-support-only, so full-universe
parity remains unprovable rather than marked PASS. No formula, artifact,
provider, model, label, or outcome was changed/accessed.

## Current status correction — 2026-08-15 — Free Float / Effective Supply source lane

Free-float / ownership-concentration source work is claimed as `ACTIVE` by
`ChatGPT/Free-Float-Effective-Supply` on branch
`data/idx-free-float-effective-supply-v1`. Scope is source discovery, provider
scaffolding, raw-provenance capture, and normalized ownership/free-float fields
only. Reuse accepted direct-IDX transport patterns and the documented
`nichsedge/idx-bei` Company Profile endpoints where valid. The external >1%
ownership snapshot is evidence for concentration, not a true free-float ground
truth. No inferred effective-float percentage, supply-tightness score, Foreign
Flow V2 feature integration/materialization, outcome access, model fitting,
Financial PIT, Corporate Action, O2, or TradingView work is authorized.

## Current status correction — 2026-08-15 — Free Float / Effective Supply continuation

The existing Free Float / Effective Supply source lane remains `ACTIVE` and is
being continued by `Codex/Free-Float-Effective-Supply` on
`data/idx-free-float-effective-supply-v1` at prepared HEAD
`36a874da865b9d7f4e03b14f284b047e77bd8cc2`. This is the same bounded source
audit, not a duplicate ownership lane. The current scope is live IDX Company
Profile, official monthly >=1% shareholder publication, and KSEI
BalanceposEfek schema/retention inspection only. No effective free-float
calculation, supply-tightness feature, Foreign Flow integration, outcomes,
models, or unrelated data lane work is authorized.

## Current status correction — 2026-08-15 — Free Float source audit result

The bounded Free Float / Effective Supply source audit is complete and remains
`REVIEW` for ChatGPT independent review. Branch
`data/idx-free-float-effective-supply-v1` is synchronized at HEAD
`69cdd30`. Official IDX Company Profile Detail succeeded for the bounded
DCII/BBCA/BAIK/WBSA/RLCO sample and exposed current named-holder/controller
rows, but no explicit reported-free-float field. Official KSEI
`BalanceposEfek` ZIPs for 2026-02-27, 2026-05-29, and 2026-07-31 were
hash-verified as aggregate local/foreign holding-composition files. The
official monthly >=1% IDX attachment could not be recovered in this bounded
probe because `ListedCompany/GetAnnouncement` returned non-JSON HTTP 503;
the public mirror also contains one exact MAYA holding-reconciliation
mismatch. Verdict: `SOURCE_REMEDIATION_REQUIRED`. External evidence root:
`D:\Documents\Project\idx-trade-free-float-effective-supply-20260815-v1`;
consolidated manifest SHA-256:
`344b59cd84da8adc8866cb3e47f942a6ea92c1b32a6fb763d74b2a54647fed94`.
Focused provider tests passed 10/10; full suite was 49 passed and one
pre-existing unrelated storage expectation failed. No effective-float
calculation, supply score, Foreign Flow integration, model/outcome access, or
other lane changes occurred.

## Current status correction — 2026-08-15 — Foreign Flow V2 core alpha

Foreign Flow V2 Core Alpha Experiment is complete and remains `REVIEW` by
`Codex/Foreign-Flow-Core-Alpha-V2` on branch
`research/idx-foreign-flow-alpha-v2-core`, based on accepted representation
commit `ceb0c2c6f57aac0433cac9a5532daa0db4c99c0b`. Scope is one preregistered
paired historical-development experiment: exact Clean V2 `HGB_XS_MARKET`
control versus the exact frozen eight-feature Foreign Flow V2 core block.
Free-float/effective-supply remains a separate active lane and is not included.
No provider calls, forward/O2 counter changes, protected/fresh-forward outcomes,
Financial PIT, Corporate Action, or TradingView work are authorized here.
Result: `FOREIGN_FLOW_V2_CORE_NO_SURVIVOR`; branch HEAD
`5867fd8377eb717659abef4caa01ae01a15df3e5` and external result manifest
SHA-256 `23275d2a673ac99dc0928a5a6c0956a0059c82c80a13eea83b4e5db4c4252852`.
Common support was 292,631 rows / 737 tickers / 1,231 sessions; median paired
PR-AUC delta was -0.004294 with 1/6 positive folds. Focused tests passed 4/4;
full pytest remains 67 passed / 1 pre-existing storage expectation failure.

## Current status correction — 2026-08-15 — Foreign Flow Setup State V1

Foreign Flow Setup State V1 is `REVIEW` by `ChatGPT/Foreign-Flow-Setup-State`
on branch `research/idx-foreign-flow-setup-state-v1` at HEAD
`d204a8fd3edaacef91aacbe90ac39f0e1969e420`. This is an outcome-blind,
prospective-only descriptive state layer built on the accepted Foreign Flow V2
representation. The existing accepted Foreign Flow catch-up runtime now
conditionally consumes a hash-pinned per-session Representation V2 artifact
and writes an immutable Setup State sidecar; sessions without that V2 input are
explicitly skipped rather than synthesized. It keeps current participation
separate from own-history abnormality magnitude/percentile and preserves raw
participation, shock 1/5/20, all three XS shock ranks, persistence,
cross-sectional pressure, acceleration, and flow-price divergence. It emits
deterministic setup labels such as `HIGH_PARTICIPATION_ROUTINE_FLOW` and
`STEALTH_ACCUMULATION_CANDIDATE`, with the latter remaining descriptive only.
The sidecar emits no probability, expected return, trade recommendation, or
fitted score. Exact V2 schema/provenance, prior-official-session causality,
identity/duplicate/missingness/revision gates, and outcome protection fail
closed. Focused tests pass 38; full repo pytest is 105 passed / 1 unrelated
pre-existing storage expectation failure out of 106 collected. No provider
calls, historical alpha/performance evaluation, protected outcomes, model
fitting, free-float/effective-supply inference, O2 changes, or new forward
counter occurred. Post-V2 price-state/confirmation research remains separate
and prospective-only; independent review is required before activating a V2
representation producer for live EOD sessions.

## Current status correction — 2026-08-15 — Foreign Flow Representation V2 forward producer

Foreign Flow Representation V2 forward producer is `REVIEW` by
`Codex/Foreign-Flow-Representation-V2-Forward` on branch
`integration/foreign-flow-representation-v2-forward-v1` at
`db630a80ae5cac3e25acbe149a3c1335a38c99d8`. Scope is outcome-blind
prospective rolling-context materialization for new canonical EOD sessions,
using the accepted V2 formulas, official calendar, listing-aware history,
canonical market/price artifacts, and existing Foreign Flow catch-up runtime.
The producer triggers from completed source session `t`, writes an immutable
prospective `t+1` Representation V2 pair, and immediately materializes and
verifies the Setup State V1 pair beside it without requiring any `t+1` session
directory, market data, Foreign Flow data, or EOD completion. The Setup State
manifest is pinned to source/calendar/Representation V2 hashes and unchanged
frozen thresholds; strict access flags, counts, path identity, calendar
revision, and immutable sidecar revision checks fail closed. Existing catchup
remains the later canonical-session consumption path. Focused
producer/V2/setup tests pass 33; full pytest is 117 passed / 1 unrelated
pre-existing storage expectation failure / 5 warnings out of 118 collected;
`git diff --check` passes. No scheduler, capture hierarchy, counter, provider
expansion, historical performance test, model/outcome access, free-float/HSC
integration, price-state layer, or O2 change is authorized. HSC/free-float
remains separate and was not modified. No real runtime run occurred; the
official calendar/rolling context after 2026-07-31 remains incomplete and the
local state is `NO_GO_CURRENT_CONTEXT`.

## Current status correction — 2026-08-15 — HSC source remediation lane

The new bounded High Shareholding Concentration (HSC) source-remediation lane
is claimed as `ACTIVE` by `Codex/Ownership-HSC-Source-Remediation`
on branch `data/idx-ownership-hsc-source-remediation-v1`, anchored at
`69cdd303ad937e6bc90d930955f751f1a2686ab0`. Scope is official IDX/KSEI
HSC/RSC publication transport, raw attachment/hash/provenance recovery, PIT
event semantics, and bounded secondary recovery of monthly >=1% attachments.
Keep `BalanceposEfek` separate and unchanged. No effective-float
calculation, HHI/features, Foreign Flow integration, models, outcomes, or
unrelated lane changes are authorized.

## Current status correction — 2026-08-15 — HSC source remediation result

HSC source remediation is now `REVIEW` by `Codex/Ownership-HSC-Source-Remediation`
on branch `data/idx-ownership-hsc-source-remediation-v1` at HEAD
`ba03d0d0ebe89f9219a2ac885af758b5e51c68ef`. Verdict:
`HSC_SOURCE_READY_FOR_CONTRACT`.

Using preserved official IDX GetAnnouncement metadata locators and direct
official StaticData retrieval through `www.idx.id`, the lane recovered and
hash-pinned 9 initial April HSC publications, MGRO May HSC, DGWG July HSC,
LUCY July HSC removal, and the MGRO correction lineage. A separate official
monthly `Pemegang Saham di atas 1% (KSEI)` attachment was also recovered.
External root:
`D:\Documents\Project\idx-ownership-hsc-source-remediation-20260815-v1`;
manifest SHA-256
`8cae847d2aa2aad2c16f7510d2c94d4578af522cf37e9f634caaf60bd2b6925c`.

The BEI/KSEI decree confirms scrip+scripless HSC review/publication and
reannouncement/removal semantics, but the detailed written review mechanism
and numeric threshold were not recovered; no threshold or free-float inference
is authorized. Focused provider tests: 10 passed. Full pytest: 49 passed / 1
unrelated pre-existing storage expectation failure. No BalanceposEfek rewrite,
features, Foreign Flow, model, outcome, or unrelated lane changes occurred.
Stop for ChatGPT review before contract integration.

## Current status correction — 2026-08-15 — HSC full-history ledger

HSC full-history ledger V1 is now `ACTIVE` by `Codex/HSC-Full-History-Ledger`
on branch `data/idx-hsc-full-history-ledger-v1`, prepared at
`52a62c4913402ad5d6908c6c06f2a0f738a7ba80`. Scope is recovery of official
HSC/RSC/correction events through 2026-08-15, strict event-ledger replay, and
exact reconciliation to the official current active set. This lane may reuse
the accepted HSC source-remediation transport and external artifacts.
No free-float/effective-supply inference, HHI/features, Foreign Flow
integration, models, outcomes, or unrelated lane changes are authorized.

## Current status correction — 2026-08-15 — Foreign Flow Forward Context Bridge V1

Foreign Flow Forward Context Bridge V1 is now `REVIEW` on branch
`data/foreign-flow-forward-context-bridge-v1` at final HEAD
`490f1a9b09b3b5d67bfcfc7aa7e7930467ad3f1e`. The accepted bridge captures and
planner remain immutable. Calendar-contract remediation now separates the
pinned historical calendar from the existing 10-session bridge calendar,
verifies bridge manifests against their original SHA, and passes only the
validated in-memory union to the accepted V2 materializer. The controlled
source `2026-08-12` smoke produced Representation V2 and Setup State for
`2026-08-13` with 963 rows/tickers, combined session-set SHA
`dd51d3dbcb29915ff80612d84a912da237331e979ee3847bd8fd4984ead413dd`, and
zero provider calls/outcome access. Focused tests: 9 passed. Full pytest:
126 passed, 1 pre-existing unrelated storage expectation failed, 5 warnings.
No recapture, artifact rewrite, O2, HSC/free-float, price-state, model,
outcome, counter, scheduler, or storage changes are in scope.

## Current status correction — 2026-08-15 — HSC full-history ledger result

HSC full-history ledger V1 is now `REVIEW` by `Codex/HSC-Full-History-Ledger`
on branch `data/idx-hsc-full-history-ledger-v1` at final HEAD
`b86e3f4906edcc57f8d5f579906321e44d12be06`. Verdict:
`HSC_FULL_HISTORY_LEDGER_READY_FOR_OWNERSHIP_CONCENTRATION_CONTRACT` for the
bounded 2026-08-15 cutoff.

The ledger contains 59 official events: 56 originals, 2 corrections, and 1
explicit LUCY removal. Strict replay passed all checkpoints: 9, 10, 11, 12,
13, 15, 14, 51, and final bounded current state 55 active tickers. The final
state is the July 51 plus AGAR, ALKA, BKDP, and BAJA. External artifact root:
`D:\Documents\Project\idx-hsc-full-history-ledger-20260815-v1`; manifest
SHA-256 `230fec0544fb7464e63008ee080fda0c8082049626529f0a565376601416b55d`.

Focused HSC tests: 16 passed. Full pytest: 105 passed / 1 unrelated existing
storage expectation failure. `git diff --check` passed. No free-float,
effective-supply, HHI, feature, Foreign Flow, model, or outcome work occurred.
Stop for ChatGPT review before ownership-concentration contract work.

## Current status correction — 2026-08-15 — Statutory Free Float Reconstruction V1

Statutory Free Float Reconstruction V1 is now `ACTIVE` by
`Codex/Statutory-Free-Float-Reconstruction` on branch
`data/idx-statutory-free-float-reconstruction-v1` at prepared HEAD
`414f4c232326f4da6e3fb1430d824eb1329877e7`. Scope is the bounded recovery of
official statutory free-float rules, BEI market-wide reports, issuer LBRE
attachments, and fail-closed diagnostic reconstruction. Official reported
free float remains preferred; no 100%-minus-holder arithmetic, HSC or >=1%
inference, effective-supply/HHI/features, Foreign Flow integration, models,
outcomes, or unrelated lane changes are authorized.

## Current status correction — 2026-08-15 — Statutory Free Float Reconstruction V1 result

The bounded Statutory Free Float Reconstruction V1 run is complete and remains
`REVIEW` for ChatGPT independent review. Branch
`data/idx-statutory-free-float-reconstruction-v1` is synchronized at HEAD
`9eb73df879d44456adfc8d5f717e6c75be5d07a0`. Official IDX static attachment
transport recovered 34/34 bounded files, including official market reports
`Peng-S-00006/BEI.PLP/02-2026` and `Peng-S-00011/BEI.PLP/04-2026`, each with
956 parsed company rows. The issuer sample contains 15 exact LBRE records
across DCII, WBSA, RLCO, BREN, BBCA, TLKM, and MAYA; all 15 expose explicit
reported free-float fields and 5 are correction records, but all remain
`BOUNDED_ONLY` because an independently complete share classification was not
proven. Exact official rule bytes/locators for `Kep-00045`, `SE-00004`, and
`Kep-00101` remain unresolved, and 2021–2023 historical report depth is not
demonstrated. Final verdict: `STATUTORY_FREE_FLOAT_SOURCE_REMEDIATION_REQUIRED`.
External evidence root:
`D:\Documents\Project\idx-statutory-free-float-reconstruction-20260815-v1`;
manifest SHA-256:
`ff25cefed69af8cd221530a23f6fc31e85e0c510a21ef5bfb78526d618a45454`.
Focused statutory tests: 8 passed. Full pytest: 50 passed / 1 known unrelated
storage expectation failure. `git diff --check` passes. No free-float point
estimate, HHI/effective-supply feature, Foreign Flow integration, model,
outcome, or canonical artifact change occurred.

## Current status correction — 2026-08-15 — Historical Statutory Free Float Snapshot V1

Historical statutory free-float snapshot work is now `ACTIVE` by
`Codex/Historical-Statutory-Free-Float` on branch
`data/idx-historical-statutory-free-float-snapshot-v1` at prepared HEAD
`6d5b7f28b4f2e0adf10fc47e63412b67896f5e27`. Scope is official reported FF
snapshot history only: quarterly market-wide anchors first, one bounded
monthly LBRE census, PIT correction lineage, and explicit AGREE/CONFLICT/
SINGLE_SOURCE reconciliation. Reuse the parent official bytes by exact hash;
do not start full monthly acquisition. No holder reconstruction, 100%-minus-
holders arithmetic, HSC subtraction, daily fill, effective supply, Foreign
Flow, features, models, outcomes, or unrelated lane work is authorized.

## Current status correction — 2026-08-15 — Historical Statutory Free Float Snapshot V1 result

Historical statutory free-float snapshot V1 is complete and remains `REVIEW`
for ChatGPT independent review. Branch
`data/idx-historical-statutory-free-float-snapshot-v1` is synchronized at final
HEAD `4762f4751cb4cc30d348704c7e19e65c47b7a329` and contains the factual
checkpoint and handoff for the bounded run. Verdict:
  `HISTORICAL_STATUTORY_FF_SNAPSHOT_READY_WITH_GAPS`.

## Current status correction — 2026-08-16 — Statutory Free-Float Knowledge-State Contract V1

Statutory Free-Float Knowledge-State Contract V1 is now `ACTIVE` by
`Codex/Statutory-Free-Float-State-Contract` on branch
`data/idx-statutory-free-float-state-contract-v1`, based on scientific parent
`data/idx-lbre-market-anchor-reconciliation-v1@ed17ec840cf7cdcffd586f3f12bdd37b0044b004`.
The existing ACTIVE free-float source/reconstruction lanes remain separate:
this lane performs only the PIT/session knowledge-state contract and adversarial
offline tests, without source discovery, acquisition, daily panel
materialization, effective-supply inference, Foreign Flow integration,
features, models, or outcomes. The contract will preserve LBRE and market
evidence independently, apply strict post-publication official-session
eligibility, and keep genuine share-count conflicts fail-closed.

## Current status correction — 2026-08-16 — Statutory Free-Float Knowledge-State Contract V1 result

Statutory Free-Float Knowledge-State Contract V1 is now `REVIEW` by
`Codex/Statutory-Free-Float-State-Contract` on branch
`data/idx-statutory-free-float-state-contract-v1` at final HEAD
`8e0892f6261b4553965949150df95d689ead1376`.

The query-level contract is implemented without historical session-panel
materialization. It enforces strict post-publication official-session
eligibility, append-only correction replay, maximum economic `as_of_date`
selection, separate LBRE/market provenance, percentage-only disagreement as
denominator-eligible, and genuine share-count conflicts as fail-closed.
Focused state/statutory tests passed 33. Full pytest was 87 collected, 86
passed, and 1 unrelated pre-existing storage expectation failed. `git diff
--check` passed. No provider calls, acquisition, panel materialization,
effective-supply, Foreign Flow, features, models, O2/counter, or outcomes were
accessed. Awaiting ChatGPT review before any historical state materialization.

The external artifact root is
`D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1`
with manifest SHA-256
`7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`.
The two parent market-wide reports were reused only after verifying parent
manifest SHA-256
`ff25cefed69af8cd221530a23f6fc31e85e0c510a21ef5bfb78526d618a45454`.

The bounded census produced 923 exact market-wide observations at position
2025-12-31 and 871 current issuer LBRE observations at position 2026-06-30,
with AGREE=1, CONFLICT=1, and SINGLE_SOURCE=1,798 on overlapping positions.
Complete quarterly market-wide coverage for 2024–2026 was not proven; no
forward-fill, interpolation, holder/HSC reconstruction, effective supply,
Foreign Flow, feature, model, or outcome work occurred. Focused tests passed
14; full pytest was 61 passed / 1 unrelated storage expectation failure / 0
warnings reported. `git diff --check` passed.

## Current status correction — 2026-08-15 — LBRE Lineage / Parser Remediation V1

LBRE lineage/parser remediation is now `ACTIVE` by
`Codex/LBRE-Lineage-Parser-Remediation` on branch
`data/idx-lbre-lineage-parser-remediation-v1` at prepared HEAD
`936181b15214edbe7eb721e672bce057b2690c32`. Scope is forensic inventory and
evidence-backed remediation of the immutable 2026-06-30 LBRE corpus from the
accepted Historical Statutory Free Float Snapshot V1 parent. No new month
acquisition, synthetic originals, ambiguous-original selection, holder/HSC/
>=1% arithmetic, forward-fill, effective supply, Foreign Flow, features,
models, outcomes, or unrelated lane work is authorized.

## Current status correction — 2026-08-15 — Price / Trend Runtime Bridge Adapter V1

Price / Trend Runtime Bridge Adapter V1 is now `REVIEW` on branch
`integration/price-trend-runtime-bridge-adapter-v1` at final HEAD
`6d0470e81599b4772cd62a676ae2201f94001efe`, with validated implementation
lineage including `2df8134aac531ec1214f560a8393cda607b9da7a`. Focused tests
passed `39`; full pytest was `78 passed, 1 unrelated storage expectation
failure, 4 warnings`; `git diff --check` passed. The exactly-one local smoke
failed closed before Price State materialization because canonical
2026-08-11 declares parent calendar SHA `e61a3b7e...` while the current bytes
at that path are `bd33e977...`; no Price State artifacts were created or
overwritten. Provider calls and outcome access were both zero/false. Do not
retry, recapture, rewrite canonical EOD, or alter Price State semantics
without independent review. No scheduler/counter, Foreign Flow + Price State
combination, O2, HSC/free-float, or trade-state logic is in scope.

## Current status correction — 2026-08-15 — Canonical EOD Calendar-Parent Attestation V1

Canonical EOD calendar-parent provenance/runtime smoke lane is now `REVIEW` on
branch
`integration/canonical-eod-calendar-parent-attestation-v1`, based on the
independent Price/Trend runtime-smoke review
`review/idx-price-trend-runtime-smoke-blocker-v1@fa280cf9d9d618973b0b5292daf5cf64874b60a7`.
Scope is limited to read-only audit of canonical EOD sessions 2026-08-11 and
2026-08-12 plus an immutable sibling attestation and strict verifier when the
only failure is unrecoverable capture-time calendar bytes. Canonical manifests,
snapshots, evidence, formulas, thresholds, scheduler, counters, providers,
outcomes, models, O2, Foreign Flow + Price State integration, HSC/free-float,
and trade-state logic remain out of scope. No Price State smoke rerun was
authorized in this lane.

Independent review `fa280cf9d9d618973b0b5292daf5cf64874b60a7` accepted the
temporal remediation and authorized exactly one runtime attestation + one
Price State smoke. The authorized sequence completed exactly once. Accepted
implementation remains at
`e90f902c040d1458786dc68369be8c58d1e58fa1`; final result is on branch HEAD
`32c30d17c7a2d1d5f434f9f6df0c7fb88e2b13ae`. The read-only runtime audit found
2026-08-11's declared calendar SHA unrecoverable while all non-calendar
canonical artifacts remain valid; 2026-08-12's declared calendar remains
recoverable at its original path. Exactly one immutable 2026-08-11 sibling
attestation was written and strictly verified twice; no 2026-08-12 attestation
was created. The single zero-provider smoke 2026-08-12 -> 2026-08-13 returned
`PRICE_TREND_CONTROLLED_SMOKE_VERIFIED` with 836 rows/tickers, idempotent
replay, and provider/outcome/model/trade flags false. Full pytest is
`86 passed, 1 failed` out of 87 collected; the sole failure is the unrelated
pre-existing storage conflict-count expectation. No second smoke, provider,
outcome, model, trade-state, scheduler, counter, O2, Foreign Flow + Price
State integration, or canonical EOD rewrite occurred. Lane is ready for
ChatGPT review.

## Current status correction — 2026-08-15 — LBRE Lineage / Parser Remediation V1 result

LBRE lineage/parser remediation V1 is now `REVIEW` on branch
`data/idx-lbre-lineage-parser-remediation-v1` at final HEAD
`a42715f027fceb0c7cd24f68e65c9e91b7bfa049`. The exact immutable 2026-06-30
corpus was reused after verifying parent manifest SHA-256
`7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`.

The remediation inventory accounts for 111 row-level problem cases / 107
unique evidence keys. Parser exact rows changed `1050 -> 1051` and unresolved
rows `18 -> 17`; lineage changed `957 admitted / 93 excluded / 871 current`
to `963 admitted / 87 excluded / 877 current`. Six lineage rows were repaired
deterministically (byte-identical duplicates, one same-announcement re-upload,
and one explicit BAPA correction marker). Residual source ambiguity remains:
17 parser rows and 87 lineage rows remain excluded or ambiguous. Verdict:
`LBRE_REMEDIATION_ACCEPTED_WITH_RESIDUAL_AMBIGUITY`.

External artifact root is
`D:\Documents\Project\idx-lbre-lineage-parser-remediation-20260815-v1-final6`
with manifest SHA-256
`cb2e929a8e7d5fc481c0eed6add4a6ba848c5a3374c65ea38e5fbe3fa5727244`.
Focused tests passed 19; full pytest was `67 passed / 1 unrelated storage
expectation failure`; `git diff --check` passed. No provider calls, new month
acquisition, free-float arithmetic, forward-fill, features, models, outcomes,
or unrelated lane work occurred. Monthly history remains blocked pending
independent review.

## Current status correction — 2026-08-15 — LBRE Monthly Free-Float History V1

LBRE monthly free-float history V1 is now `ACTIVE` by
`Codex/LBRE-Monthly-History` on branch
`data/idx-lbre-monthly-free-float-history-v1` at prepared HEAD
`f6537c09b5121cc8b185df4fd9d672e305a879d1`. Scope is generalized official
IDX LBRE acquisition and append-only parser/lineage replay for positions
2024-04-30 through 2026-06-30 inclusive, reusing the accepted June-2026
corpus and the reviewed bounded LBRE lineage/parser parent. Discovery and
pagination completeness must be proven before bulk acquisition. No holder,
HSC, >=1%, forward-fill, effective-supply, Foreign Flow, feature, model,
outcome, or unrelated lane work is authorized.

## Current status correction — 2026-08-15 — Joint Setup Readiness State V1

Joint Setup Readiness State V1 remediation is now `REVIEW` by
Codex/Joint-Setup-Readiness on branch
`research/idx-joint-setup-readiness-state-v1` at final HEAD
`3ad481cc4b371f5022742101a12f6b9d603481a4`. This is an outcome-blind
contract-only lane using the accepted Foreign Flow Setup State / Representation
V2 and Price / Trend Confirmation State parents. The strict contract joins
same ticker + feature session, requires Foreign Flow `flow_through_session` =
Price State `source_session` and next-official-session causality, and carries
parent artifact/manifest hashes and protected access flags. Explicit mapping is
frozen as `IGNORE -> WATCH -> READY -> ENTRY_ELIGIBLE` with deterministic reason
codes; `ENTRY_ELIGIBLE` remains descriptive context, never a trade
recommendation. This remediation is limited to BASING semantics, frozen
rule-definition/fingerprint completeness, fail-closed parent handling, strict
ticker identity, and explicit provenance/protected-flag validation. No
prospective runtime wiring, scheduler/provider work, model/scoring,
performance/outcome access, O2/counter change, HSC/free-float work, or
modification of either parent formula occurred. The remediation restores
`BASING` as a READY trend state, makes the ordered rule matrix/output schema
fingerprint-complete, changes invalid parent compatibility to
`FAIL_CLOSED_NO_OUTPUT`, rejects noncanonical ticker identities without
normalization, and requires explicit provenance/protected fields. Focused
tests: 11 passed. Full pytest: 50 passed / 1 known unrelated storage
expectation failure / 51 collected. `git diff --check` PASS. Runtime wiring
remains blocked pending ChatGPT review.

## Current status correction — 2026-08-16 — Joint Setup Readiness State V1.1

Joint Setup Readiness State V1.1 real-parent domain remediation is now
`REVIEW` by Codex/Joint-Setup-Readiness on branch
`research/idx-joint-setup-readiness-state-v1-1-domain-remediation`, based on
the accepted V1 contract at
`research/idx-joint-setup-readiness-state-v1@3ad481cc4b371f5022742101a12f6b9d603481a4`
and acceptance review
`review/idx-joint-setup-readiness-state-v1-acceptance@d906caa03dc6c41c62d346c7f185a5bd8cb6e0c3`.
The bounded scope is only the V1.1 real-parent applicability domain: Price
State is authoritative, every Price key must exist exactly once in Foreign
Flow, Foreign-Flow-only keys are allowed but excluded with exact provenance,
and no runtime joint artifact is created in this lane. Real-parent audit is
`JOINT_REAL_PARENT_DOMAIN_COMPATIBLE`: Price `836`, Foreign Flow `963`,
overlap `836`, Price-only `0`, Foreign-Flow-only excluded `127`. Final branch
HEAD is `471287c`. Focused tests: `22 passed`. Full pytest: `61 passed, 1
unrelated storage expectation failure, 62 collected`; `git diff --check`
PASS. Repository Hygiene, parent formulas/thresholds, providers, schedulers,
O2/counters, models, outcomes, and trade semantics remain out of scope.

## Current status correction — 2026-08-16 — Joint Setup Readiness V1.1 prospective runtime

Joint Setup Readiness V1.1 prospective runtime adapter is now `REVIEW` by
Codex/Joint-Setup-Readiness on branch
`integration/joint-setup-readiness-v1-1-forward-v1` at final HEAD
`8ede786622713b03127fbf856abe2d7d2bd5c03d`. The controlled smoke completed
with status `JOINT_SETUP_READINESS_V1_1_CONTROLLED_SMOKE_VERIFIED` for source
session 2026-08-12 and feature session 2026-08-13. The output contains 836
rows/tickers from the authoritative Price State domain; the reconciled domain
was FF 963 / Price 836 / overlap 836 / Price-only 0 / FF-only 127, with state
distribution IGNORE 697 / WATCH 84 / READY 54 / ENTRY_ELIGIBLE 1. The output
artifact SHA-256 is
`d83593b61a25f9f32a82c153001e0c548f29ffb255485b29a84760ae6ae03418` and the
manifest SHA-256 is
`c3007af5af3061ee91be176fb0d29dc000cfc162fcc0c3642c5f26723646d646`.
Strict verification passed and the idempotent replay created no second
artifact. Focused tests passed 33; full pytest was 72 passed, 1 unrelated
pre-existing `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
failure out of 73 collected; `git diff --check` passed. Repository Hygiene,
providers/network, scheduler, O2/counter, models, outcomes, and trade
semantics remain out of scope.

## Current status correction — 2026-08-16 — Joint Setup Readiness V1.1 generic prospective runner

Joint Setup Readiness V1.1 generic prospective runner is `REVIEW` after bounded
parent-semantic remediation under independent review
`review/idx-joint-setup-readiness-v1-1-forward-acceptance@2bdc8608d1900076b6e94f5f5c8b4c76c71b547f`.
The frozen joint classifier, thresholds, domain semantics, output schema, and
accepted 2026-08-13 artifact remain unchanged. The remediation is limited to
strict upstream Price State and Foreign Flow parent verification before hash
pinning.

The prior generic runner result was `REVIEW` by
`Codex/Joint-Setup-Readiness-Generic-Runner` on branch
`integration/joint-setup-readiness-v1-1-generic-runner-v1` at final HEAD
`0a0943e3f86bc5b1200ca55cf4bc18a3a9a528ff`, based on accepted runtime parent
`integration/joint-setup-readiness-v1-1-forward-v1@8ede786622713b03127fbf856abe2d7d2bd5c03d`.
The remediation adds strict upstream Price State context verification plus
source-context replay and strict Foreign Flow Representation/Setup replay
before parent hashes are recorded. The generic runner passed compatibility
replay for 2026-08-12 -> 2026-08-13 with `created=false`, preserving artifact SHA
`d83593b61a25f9f32a82c153001e0c548f29ffb255485b29a84760ae6ae03418` and
manifest SHA `c3007af5af3061ee91be176fb0d29dc000cfc162fcc0c3642c5f26723646d646`.
Focused joint tests: 47 passed. Full pytest: 81 passed, 1 unrelated
pre-existing `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
failure, 82 collected. `git diff --check` PASS. No new prospective session,
provider/network, scheduler, O2/counter, model, outcome, trade, or Repository
Hygiene work was performed. See checkpoint
`docs/checkpoints/2026-08-16_JOINT_SETUP_READINESS_V1_1_GENERIC_RUNNER_PARENT_SEMANTIC_REMEDIATION.md`.

## Current status correction — 2026-08-16 — LBRE Monthly Free-Float History V1 result

LBRE Monthly Free-Float History V1 is now `REVIEW` by
`Codex/LBRE-Monthly-History` on branch
`data/idx-lbre-monthly-free-float-history-v1` at final HEAD
`bf0648c9dd37ad4a25e2de42d6f4a18fd19f857d`. The generalized official IDX
LBRE acquisition covered position dates 2024-04-30 through 2026-06-30: 27,724
reported announcement records over 28 complete pages, 30,405 main
attachments, 1,068 exact parent reuses, 29,335 new downloads, and 2 bounded
HTTP 404 failures. Offline parsing produced 28,254 exact rows; append-only
replay produced 24,394 admitted observations and 23,373 current exact rows,
with 868 lineage cases kept unresolved (532 multiple originals, 332 missing
original evidence, 4 invalid correction chronologies). The June-2026 current
count is 870 versus the accepted 877 parent; all eight old-only tickers are
explicitly fail-closed due to malformed/ambiguous evidence or missing
correction lineage, while INAF is an additional exact row from the wider
official discovery. No ambiguous value was selected. The 2025-12 cross-source
diagnostic is 260 AGREE / 625 CONFLICT / 38 SINGLE_SOURCE. External artifact
manifest SHA-256 is
`e134809a1f1b745daf2f21c33ab7db78c38d1d5d520f5320564359d5b865bd86` under
`D:\Documents\Project\idx-lbre-monthly-free-float-history-20260815-v1`.
Verdict: `LBRE_MONTHLY_FF_HISTORY_PARTIAL_SOURCE_USEFUL`. Focused tests:
21 passed. Full pytest: 69 collected, 68 passed, 1 unrelated storage
expectation failure. No daily FF state, effective supply, Foreign Flow
features, models, outcomes, or unrelated lanes were touched; daily-state and
feature integration remain unclaimed pending review.

## Current status correction — 2026-08-16 — LBRE Market-Wide Anchor Reconciliation V1

LBRE / market-wide free-float reconciliation V1 is now `ACTIVE` by
`Codex/LBRE-Market-Anchor-Reconciliation` on branch
`data/idx-lbre-market-anchor-reconciliation-v1` at prepared HEAD
`b2855061f470bc23e9aed6f91ebf8ec91e1b8e99`. This is an offline-only
decomposition of the accepted 2025-12-31 reconciliation (260 AGREE / 625
CONFLICT / 38 SINGLE_SOURCE) using the exact monthly-history and snapshot
parent manifests. It will classify share-count and percentage disagreements,
compute diagnostics without replacing official values, and determine whether
issuer LBRE shares are a safe historical denominator. No network, acquisition,
parser/lineage change, daily FF state, effective supply, Foreign Flow,
features, models, outcomes, or unrelated lane work is authorized.

## Current status correction — 2026-08-16 — LBRE Market-Wide Anchor Reconciliation V1 result

LBRE / market-wide free-float reconciliation V1 is now `REVIEW` by
`Codex/LBRE-Market-Anchor-Reconciliation` on branch
`data/idx-lbre-market-anchor-reconciliation-v1` at final HEAD
`ed17ec840cf7cdcffd586f3f12bdd37b0044b004`.

The exact final branch HEAD is recorded in the handoff; the branch was pushed
successfully after the offline run. The 923-ticker 2025-12-31 union decomposed
to 260 `EXACT_AGREE`, 616 `SHARES_AGREE_PCT_DIFF`, 0
`SHARES_DIFF_PCT_AGREE`, 9 `SHARES_AND_PCT_DIFF`, 0 `LBRE_ONLY`, and 38
`MARKET_ONLY`. Thus 616/625 prior conflicts had identical shares, while 9/625
had genuine share-count disagreements ranging from 400,000 to 2,986,991,880
shares and 0.064% to 50.061% relative to LBRE shares. Publication comparison
was LBRE-before-market for 882 overlaps, after for BHIT/EKAD/NISP, and equal
for none. Final verdict:
`LBRE_FF_SHARES_DENOMINATOR_PARTIAL_CONFLICT_REVIEW_REQUIRED`.

External manifest SHA-256 is
`34fe46f9077fe8c6630fbec5f3682718f01cea1456d7bcb904fa7be6a9479840` under
`D:\Documents\Project\idx-lbre-market-anchor-reconciliation-20260816-v1`.
Focused tests passed 3. Full pytest was 72 collected, 71 passed, and 1
unrelated pre-existing storage expectation failed. No network, acquisition,
parser/lineage, daily FF state, effective supply, Foreign Flow, features,
models, outcomes, or unrelated lanes were touched. The lane is awaiting
independent review.

## Current status correction — 2026-08-16 — Statutory Free-Float Knowledge-State V1 remediation

Statutory Free-Float Knowledge-State V1 remediation is now `REVIEW` by
`Codex/Statutory-Free-Float-State-Contract-Remediation` on branch
`data/idx-statutory-free-float-state-contract-v1-remediation`, based on
`data/idx-statutory-free-float-state-contract-v1@8e0892f6261b4553965949150df95d689ead1376`.
This is a contract-correctness-only remediation: remove chronology asymmetry
between LBRE and market evidence, stop exposing a silently LBRE-preferred
percentage, and add adversarial tests. Final branch HEAD is `506f734`.
Focused tests pass (`18 passed`); full suite is `86 passed, 1 failed` out of 87
collected because of the unrelated storage revision-conflict expectation. No
source/network work, historical
panel materialization, parser/monthly-history/reconciliation changes,
effective supply, Foreign Flow, HSC, models, outcomes, or O2 changes are
authorized. Ready for independent review; historical panel materialization
remains unauthorized.
