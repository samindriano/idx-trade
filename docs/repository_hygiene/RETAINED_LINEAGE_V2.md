# Repository Hygiene V2 — Retained Lineage Map

Date: 2026-08-22 Asia/Jakarta
Original status: `POST_CLEANUP_CANONICAL_MAP`
Current interpretation after 2026-08-26 capture-hygiene review: `HISTORICAL_V2_SNAPSHOT_WITH_CURRENT_CAPTURE_SUPERSESSION`

Purpose: preserve the exact post-Hygiene-V2 survivor state without forcing future agents to reconstruct 200+ historical branches.

> **2026-08-26 update:** sections describing the exact 50-branch survivor set remain historical evidence of the 2026-08-22 cleanup. They are not a current authorization list. For current acquisition/runtime ownership, use `docs/repository_hygiene/CAPTURE_RUNTIME_REGISTRY_V1.md` and `coordination/TEAM_STATUS.md`. Several branches retained on 2026-08-22 have since been merged, superseded, or certified for archive/delete.

Repository state immediately after destructive Hygiene V2 apply:

- remote branches before: **274**
- remote branches after: **50**
- removed: **224**
- archive-tagged historical heads: **45**
- tombstone/redundant removals: **179**

The temporary post-cleanup docs branch is not part of the 50-branch frozen cleanup result.

## 1. Canonical coordination / governance

Primary anchors at the V2 snapshot:
- `main` — canonical shared coordination authority.
- `chore/repository-hygiene-v2-aggressive` — exact cleanup implementation/pre-destructive evidence.
- `codex/artifact-governance-v1`
- `codex/data-source-provenance-registry-v1`
- `codex/frozen-lineage-impact-audit-v1`
- `integration/schema-hardening-v2`

Documentation/UI anchors:
- `docs/idx-trade-human-notebooks-v1`
- `docs/readme-main-refresh-v1`
- `frontend/v4x-v2-monitoring-refresh-v1`

## 2. Alpha / clean model lineage

Durable anchors:
- `research/idx-ranking-v2-spec-v1` — durable V2 HGB_XS_MARKET parent/runtime lineage.
- `codex/pit-safe-v2-v3b-o2-reproduction-research-v1` — clean PIT-safe historical adjudication; V3-B/O2 contamination conclusions.
- `research/idx-v4-x1-clean-historical-oos-replay-v1` — clean V4-X1 historical evidence anchor.
- `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1` — final clean refit lineage.
- `data/v4-x-clean-data-consolidation-v1-final-input-freeze-v1` — final consolidated clean input freeze.
- `integration/v4-x1-clean-prospective-score-v1` — prospective clean scorer deployment lineage.

`integration/v4-x1-eod-auto-score-v1` was a live integration anchor at the V2 snapshot but is now contained in the accepted E2E integration lineage and is certified branch-ref redundant by Capture Runtime Registry V1.

Forward evaluation:
- `research/idx-forward-evaluation-protocol-v1`
- `codex/idx-forward-100-evaluator-v1`
- `research/idx-reliability-uncertainty-v1-forward-shadow` — reliability is sidecar evidence, not a second Decision policy.

## 3. Decision lineage — final

Durable anchors only:
- `research/idx-decision-v2-minimal-implementation-v1` — incumbent Decision V2 implementation.
- `research/idx-decision-economic-comparison-v1` — frozen development-set economic evidence supporting V2.
- `audit/idx-decision-v4-refill-decoupling-result-v1` — final Decision closure / V4 structural reject anchor.

Binding state:
- Decision V2 = incumbent.
- Decision V3 = rejected.
- Decision V4 Refill Decoupling = structural reject.
- Decision research = **CLOSED** on the consumed development set.
- No V4.1/V4.2/V5/rescue search.

The separate accepted Decision V2 implementation audit is preserved as an `archive/hygiene-v2/*` tag rather than a live branch.

## 4. E2E downstream stack — current capture interpretation

Accepted E2E implementation anchor as of 2026-08-26:

- `integration/idx-e2e-baseline-paper-v1@043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2`

The accepted lineage contains the cloud-first adapter plus existing downstream science/runtime foundations. Current capture terminology is deliberately smaller:

- **Official Open Capture** — execution-grade IDX `OpenPrice`, cloud archived.
- **EOD Market Capture** — one post-close Stock EOD/OHLCV + Market/Index context transaction.
- **Corporate Action Capture** — integrated forward CA evidence/attestation.
- **Stockbit Stream Capture**.
- **Stockbit Intraday Capture**.

Important V2-era branch disposition updates:

- `integration/forward-eod-automation-monitoring` — now fully contained by accepted E2E ancestry; certified branch-ref redundant.
- `integration/v4-x1-eod-auto-score-v1` — now fully contained by accepted E2E ancestry; certified branch-ref redundant.
- `ops/idx-forward-open-archive-v1` — historical source-blocked generic Open scaffold; superseded by Official Open, exact head must be archived before branch deletion.
- `data/market-index-forward-eod-v1-monitoring` — **retain for now**; unique commits remain and must be audited/absorbed into canonical EOD Market Capture first.
- CA clean/continuity anchors remain durable because they provide current accounting/execution semantics rather than competing acquisition hierarchies.

## 5. Stockbit operational lineage — current interpretation

Current production authority is the Stockbit Stream workflow/runtime on `main`, not the old branch chain.

Certified branch-ref redundant after successful merges:
- `fix/stockbit-stream-zapi-envelope-v1` — PR #35 merged.
- `fix/stockbit-stream-daily-capture-v1` — PR #72 merged.
- `fix/stockbit-stream-transient-reliability-main-v1` — PR #79 merged.
- `fix/stockbit-stream-schema-diagnostics-v1` — PR #81 merged.
- `fix/stockbit-r2-retention-v1` — retention remediation and activation closure merged.

Unique but superseded heads requiring forensic archive before deletion:
- `data/stockbit-stream-prospective-archive-v1@009be16e5db8a7a9899cff73f10f53dfc8a3fe6c` — early generation base.
- `ops/stockbit-stream-observable-smoke-v1@17803978c1e145dbe084c828e45bed5247c13aa6` — validation-only smoke; PR #34 intentionally closed unmerged.

Protected / do not delete yet:
- `audit/stockbit-stream-v2-red-team-v1` — PR #36 remains open/draft with unique adversarial work.
- `fix/stockbit-intraday-postclose-fix-v1` — current Stockbit Intraday operational implementation and future cloud-migration target.

See `CAPTURE_RUNTIME_REGISTRY_V1.md` for the exact audited delete/archive table and runtime-safety checks.

## 6. Retained parallel research/data lanes

Financial PIT:
- `research/idx-financial-pit-alpha-v1`
- `research/idx-financial-representation-v2`

Foreign Flow:
- `research/idx-foreign-flow-alpha-v2-core`
- `research/idx-foreign-flow-representation-v2`
- `integration/foreign-flow-representation-v2-forward-v1`
- `data/idx-foreign-flow-forward-capture-v1`
- `data/idx-foreign-flow-historical-acquisition-v1`

The Foreign Flow forward lane is not automatically a separate canonical collector: current capture registry treats representation derived from canonical Stock Summary raw as a downstream sidecar unless a future explicit acquisition contract changes that.

Price / Trend:
- `research/idx-price-trend-confirmation-state-v1`
- `integration/price-trend-state-forward-sidecar-v1`
- `integration/price-trend-runtime-bridge-adapter-v1`

Personal KSEI:
- `integration/personal-ksei-bounded-auth-design-v1`

Price-basis cleanup:
- `data/price-basis-remediation-v1`
- `research/price-basis-clean-refit-v1`

Final historical TradingView remediation anchor:
- `data/tradingview-historical-price-path-v2-1-remediation`

These are **retained evidence/research lanes**, not automatically active priorities or canonical capture systems. `TEAM_STATUS.md` controls current ownership/status.

## 7. Exact 50-branch cleanup survivor set — historical snapshot

The atomic Hygiene V2 cleanup retained exactly these 50 remote branches on 2026-08-22. This list is intentionally preserved unchanged as historical evidence; it must not be read as the current live-branch authorization set.

1. `audit/idx-decision-v4-refill-decoupling-result-v1`
2. `audit/stockbit-stream-v2-red-team-v1`
3. `chore/repository-hygiene-v2-aggressive`
4. `codex/artifact-governance-v1`
5. `codex/data-source-provenance-registry-v1`
6. `codex/frozen-lineage-impact-audit-v1`
7. `codex/idx-forward-100-evaluator-v1`
8. `codex/pit-safe-v2-v3b-o2-reproduction-research-v1`
9. `data/idx-foreign-flow-forward-capture-v1`
10. `data/idx-foreign-flow-historical-acquisition-v1`
11. `data/idx-forward-calendar-extension-v1`
12. `data/idx-open-official-stock-summary-recovery-v1`
13. `data/idx-v4-ca-voluntary-conversion-semantics-remediation-v1`
14. `data/idx-v4-corporate-action-continuity-gate-v1`
15. `data/market-index-forward-eod-v1-monitoring`
16. `data/price-basis-remediation-v1`
17. `data/stockbit-stream-prospective-archive-v1`
18. `data/tradingview-historical-price-path-v2-1-remediation`
19. `data/v4-x-clean-data-consolidation-v1-final-input-freeze-v1`
20. `docs/idx-trade-human-notebooks-v1`
21. `docs/readme-main-refresh-v1`
22. `fix/stockbit-intraday-postclose-fix-v1`
23. `fix/stockbit-stream-zapi-envelope-v1`
24. `frontend/v4x-v2-monitoring-refresh-v1`
25. `integration/foreign-flow-representation-v2-forward-v1`
26. `integration/forward-ca-attestation-v1`
27. `integration/forward-eod-automation-monitoring`
28. `integration/idx-v4-ca-target-continuity-bridge-v1`
29. `integration/personal-ksei-bounded-auth-design-v1`
30. `integration/price-trend-runtime-bridge-adapter-v1`
31. `integration/price-trend-state-forward-sidecar-v1`
32. `integration/schema-hardening-v2`
33. `integration/v4-x1-clean-prospective-score-v1`
34. `integration/v4-x1-eod-auto-score-v1`
35. `main`
36. `ops/idx-forward-open-archive-v1`
37. `ops/stockbit-stream-observable-smoke-v1`
38. `research/idx-decision-economic-comparison-v1`
39. `research/idx-decision-v2-minimal-implementation-v1`
40. `research/idx-financial-pit-alpha-v1`
41. `research/idx-financial-representation-v2`
42. `research/idx-foreign-flow-alpha-v2-core`
43. `research/idx-foreign-flow-representation-v2`
44. `research/idx-forward-evaluation-protocol-v1`
45. `research/idx-price-trend-confirmation-state-v1`
46. `research/idx-ranking-v2-spec-v1`
47. `research/idx-reliability-uncertainty-v1-forward-shadow`
48. `research/idx-v4-x1-clean-historical-oos-replay-v1`
49. `research/idx-v4-x1-clean-phase-b-final-refit-prep-v1`
50. `research/price-basis-clean-refit-v1`

## 8. Archive-only evidence

Hygiene V2 created 45 lightweight archive tags for selected exact historical heads, including:
- Historical Universe / early CA / PIT-sector / early Foreign Flow results;
- clean/CA historical replay anchors;
- V3/O2 lessons/common-support evidence;
- TradingView semantic/fidelity anchors;
- identity/window/basis integrity audits;
- accepted Decision V2 implementation audit;
- Financial PIT / Foreign Flow / Price-State acceptance heads;
- statutory free-float/HSC evidence;
- canonical EOD parent attestation.

Archive tags are forensic recovery references, not active work authorization.

The exact branch-to-SHA V2 cleanup map is preserved in annotated tag:

`archive/hygiene-v2/deletion-plan-40c3c21e565fa613`

Capture Hygiene V3 uses the same principle: unique superseded capture heads must receive exact forensic refs before their live branch refs are removed.

## 9. Tombstoned/deleted means closed, not forgotten

A removed branch must not be recreated simply because it no longer appears in the branch list. Before reopening an old idea, read:
- `docs/repository_hygiene/EXPERIMENT_TOMBSTONES_V2.md`;
- `docs/repository_hygiene/CAPTURE_RUNTIME_REGISTRY_V1.md` for acquisition/runtime work;
- surviving canonical checkpoints;
- the closed PR history;
- relevant `archive/hygiene-v2/*` evidence when exact old code is needed.

The branch list should represent **what can still be acted on**. Docs/archive refs preserve **what was learned**.
