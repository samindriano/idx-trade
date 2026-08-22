# Repository Hygiene V2 — Retained Lineage Map

Date: 2026-08-22 Asia/Jakarta
Status: `POST_CLEANUP_CANONICAL_MAP`

Purpose: after aggressive branch pruning, identify the small set of live branches that matter without reconstructing 200+ historical branches.

Repository state immediately after destructive Hygiene V2 apply:

- remote branches before: **274**
- remote branches after: **50**
- removed: **224**
- archive-tagged historical heads: **45**
- tombstone/redundant removals: **179**

The temporary post-cleanup docs branch is not part of the 50-branch frozen cleanup result.

## 1. Canonical coordination / governance

Primary anchors:
- `main` — canonical shared coordination authority.
- `chore/repository-hygiene-v2-aggressive` — exact cleanup implementation/pre-destructive evidence; keep until a future hygiene pass deliberately archives it.
- `codex/artifact-governance-v1`
- `codex/data-source-provenance-registry-v1`
- `codex/frozen-lineage-impact-audit-v1`
- `integration/schema-hardening-v2`

Documentation/UI anchors:
- `docs/idx-trade-human-notebooks-v1`
- `docs/readme-main-refresh-v1`
- `frontend/v4x-v2-monitoring-refresh-v1`

## 2. Alpha / clean model lineage

Live anchors:
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
- `research/idx-reliability-uncertainty-v1-forward-shadow` — reliability is sidecar evidence, not a second Decision policy.

## 3. Decision lineage — final

Live anchors only:
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

## 4. E2E downstream stack

Primary downstream implementation anchor:
- `integration/forward-ca-attestation-v1`

This lineage already contains source required for E2E, including:
- Sizing V1;
- Execution V1 engine/allocator/contract/verifier;
- dividend execution/runtime;
- persistent CA-aware forward/paper-state foundations;
- canonical EOD/CA attestation support.

Additional live E2E anchors:
- `integration/forward-eod-automation-monitoring`
- `data/idx-forward-calendar-extension-v1`
- `data/idx-v4-corporate-action-continuity-gate-v1`
- `data/idx-v4-ca-voluntary-conversion-semantics-remediation-v1`
- `integration/idx-v4-ca-target-continuity-bridge-v1`
- `data/idx-open-official-stock-summary-recovery-v1`
- `ops/idx-forward-open-archive-v1`
- `data/market-index-forward-eod-v1-monitoring`

Next engineering objective:

`clean prospective score -> Decision V2 -> fixed ~10% seats -> Execution V1 -> CA-aware persistent paper state -> restart-safe E2E orchestrator`

## 5. Active Stockbit operational lineages

Protected live heads:
- `fix/stockbit-intraday-postclose-fix-v1`
- `data/stockbit-stream-prospective-archive-v1`
- `fix/stockbit-stream-zapi-envelope-v1` — PR #35 head.
- `audit/stockbit-stream-v2-red-team-v1` — PR #36 head.
- `ops/stockbit-stream-observable-smoke-v1`

Superseded Stockbit ancestors were removed when their relevant code was contained in retained descendants.

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

Price / Trend:
- `research/idx-price-trend-confirmation-state-v1`
- `integration/price-trend-state-forward-sidecar-v1`
- `integration/price-trend-runtime-bridge-adapter-v1`

Personal KSEI:
- `integration/personal-ksei-bounded-auth-design-v1`

Price-basis cleanup:
- `data/price-basis-remediation-v1`
- `research/price-basis-clean-refit-v1`

Final live TradingView remediation anchor:
- `data/tradingview-historical-price-path-v2-1-remediation`

These are **retained**, not automatically active priorities. `TEAM_STATUS.md` controls current ownership/status.

## 7. Exact 50-branch cleanup survivor set

The atomic Hygiene V2 cleanup retained exactly these 50 remote branches:

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

The exact branch-to-SHA cleanup map is preserved in annotated tag:

`archive/hygiene-v2/deletion-plan-40c3c21e565fa613`

## 9. Tombstoned/deleted means closed, not forgotten

A removed branch must not be recreated simply because it no longer appears in the branch list. Before reopening an old idea, read:
- `docs/repository_hygiene/EXPERIMENT_TOMBSTONES_V2.md`;
- surviving canonical checkpoints;
- the closed PR history;
- relevant `archive/hygiene-v2/*` tag when exact code is needed.

The branch list should represent **what can still be acted on**. Docs/tags preserve **what was learned**.
