# Repository Hygiene V2 — Retained Lineage Map

Date: 2026-08-22 Asia/Jakarta
Status: `PRE_DESTRUCTIVE_CANONICAL_MAP`

Purpose: after aggressive branch pruning, a future agent should be able to identify the few live branches that matter without reconstructing 200+ historical branches.

## 1. Canonical coordination / governance

Live anchors:
- `main` — canonical shared coordination authority.
- `chore/repository-hygiene-v2-aggressive` — temporary cleanup control branch; retain through post-cleanup audit.
- `codex/artifact-governance-v1`
- `codex/data-source-provenance-registry-v1`
- `codex/frozen-lineage-impact-audit-v1`
- `integration/schema-hardening-v2`

Documentation/UI anchors:
- `docs/idx-trade-human-notebooks-v1`
- `docs/readme-main-refresh-v1`
- `frontend/v4x-v2-monitoring-refresh-v1`

## 2. Alpha / clean model lineage

Current clean research/production direction:
- `research/idx-ranking-v2-spec-v1` — durable V2 HGB_XS_MARKET parent/runtime lineage.
- `codex/pit-safe-v2-v3b-o2-reproduction-research-v1` — clean PIT-safe historical adjudication; V3-B/O2 contamination conclusions.
- `research/idx-v4-x1-clean-historical-oos-replay-v1` — clean V4-X1 historical evidence anchor.
- `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1` — final clean refit lineage.
- `data/v4-x-clean-data-consolidation-v1-final-input-freeze-v1` — final consolidated clean input freeze.
- `integration/v4-x1-clean-prospective-score-v1` — prospective clean scorer deployment lineage.
- `integration/v4-x1-eod-auto-score-v1` — EOD scoring integration.

Forward evaluation:
- `research/idx-forward-evaluation-protocol-v1`
- `codex/idx-forward-100-evaluator-v1`
- `research/idx-reliability-uncertainty-v1-forward-shadow` — reliability remains sidecar evidence, not a second Decision policy.

## 3. Decision lineage — final

Live anchors only:
- `research/idx-decision-v2-minimal-implementation-v1` — incumbent Decision V2 implementation. It contains the accepted remediated code lineage; the separate acceptance audit is archive-tagged, not live.
- `research/idx-decision-economic-comparison-v1` — frozen development-set economic evidence supporting V2 as incumbent.
- `audit/idx-decision-v4-refill-decoupling-result-v1` — final Decision closure / V4 structural reject anchor.

Binding state:
- Decision V2 = incumbent.
- Decision V3 = rejected.
- Decision V4 Refill Decoupling = structural reject.
- Decision research = CLOSED on the consumed development set.
- No V4.1/V4.2/rescue search.

All other Decision prereg, runner, audit, and mechanism-diagnosis branches are non-live after Hygiene V2.

## 4. E2E downstream stack

Primary downstream integration anchor:
- `integration/forward-ca-attestation-v1`

This retained lineage contains the actual downstream source required for E2E, including:
- `v4_x1_sizing_v1.py`;
- `v4_x1_execution_v1.py`;
- Execution V1 allocator/contract/verifier;
- dividend execution/runtime;
- persistent CA-aware forward/paper-state foundations;
- canonical EOD/CA attestation support.

Therefore historical sizing/execution branches are not required to remain live merely to preserve code.

Additional E2E anchors:
- `integration/forward-eod-automation-monitoring`
- `data/idx-forward-calendar-extension-v1`
- `data/idx-v4-corporate-action-continuity-gate-v1`
- `data/idx-v4-ca-voluntary-conversion-semantics-remediation-v1`
- `integration/idx-v4-ca-target-continuity-bridge-v1`
- `data/idx-open-official-stock-summary-recovery-v1`
- `ops/idx-forward-open-archive-v1`
- `data/market-index-forward-eod-v1-monitoring`

Next engineering objective after cleanup:

`clean prospective score -> Decision V2 -> fixed 10% seats -> Execution V1 -> CA-aware persistent paper state -> restart-safe E2E orchestrator`

## 5. Active Stockbit operational lineages

These are explicitly protected from cleanup:
- `fix/stockbit-intraday-postclose-fix-v1`
- `data/stockbit-stream-prospective-archive-v1`
- `fix/stockbit-stream-zapi-envelope-v1` — open PR #35 head.
- `audit/stockbit-stream-v2-red-team-v1` — open PR #36 head.
- `ops/stockbit-stream-observable-smoke-v1`

Superseded Stockbit ancestor branches may be deleted when their code is fully contained in the retained descendant.

## 6. Still-live alpha/data research lanes

Financial PIT:
- `research/idx-financial-pit-alpha-v1`
- `research/idx-financial-representation-v2`

Foreign Flow:
- `research/idx-foreign-flow-alpha-v2-core`
- `research/idx-foreign-flow-representation-v2`
- `integration/foreign-flow-representation-v2-forward-v1`
- `data/idx-foreign-flow-forward-capture-v1`
- `data/idx-foreign-flow-historical-acquisition-v1`

Price / Trend state:
- `research/idx-price-trend-confirmation-state-v1`
- `integration/price-trend-state-forward-sidecar-v1`
- `integration/price-trend-runtime-bridge-adapter-v1`

Personal KSEI:
- `integration/personal-ksei-bounded-auth-design-v1`

Price-basis cleanup:
- `data/price-basis-remediation-v1`
- `research/price-basis-clean-refit-v1`

TradingView historical semantics is reduced to one final live remediation anchor:
- `data/tradingview-historical-price-path-v2-1-remediation`

Other historical TradingView/Investing/PIT-sector/KSEI/breadth source lines become archive-only or tombstoned until a future separately justified reopening.

## 7. Archive-only high-value evidence

Hygiene V2 creates lightweight archive tags for a bounded set of exact historical heads. Categories include:
- final source-audit results (Historical Universe, early CA, PIT sector, Foreign Flow);
- selected clean/CA historical replay anchors;
- V3/O2 lessons and common-support evidence;
- selected TradingView semantic/fidelity anchors;
- selected identity/window/basis integrity audits;
- Decision V2 accepted implementation audit;
- Financial PIT, Foreign Flow, Price/Trend and joint-setup final acceptance heads;
- statutory free-float/HSC evidence anchors;
- canonical EOD parent attestation.

Archive tags are forensic recovery references, not active work authorization.

## 8. Tombstoned/deleted means scientifically closed, not forgotten

A deleted branch must not be recreated simply because it no longer appears in the branch list. Before reopening an old idea, read:
- `docs/repository_hygiene/EXPERIMENT_TOMBSTONES_V2.md`;
- surviving canonical checkpoints;
- the closed PR history;
- relevant archive tag if one exists.

The cleanup goal is to make the branch list represent **what can still be acted on**, while docs/tags preserve **what was learned**.
