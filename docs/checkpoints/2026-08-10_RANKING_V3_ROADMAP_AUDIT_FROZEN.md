# Checkpoint — Ranking V3 Roadmap Audit Frozen

Date: 2026-08-10 (Asia/Jakarta)
Status: **RANKING_V3_ROADMAP_AUDIT_FROZEN**

## Scope

This checkpoint records the post-legacy-audit V3 research roadmap. It is documentation/research-governance only and does not authorize V3 model scoring or any V2 forward-outcome access.

Primary roadmap:

`docs/RANKING_V3_ROADMAP_AUDIT_V1.md`

Supporting lessons:

`docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`

Backlog aligned to audit:

`docs/RANKING_V3_RESEARCH_BACKLOG.md`

## Audited priority

1. `V3-A RECENCY`
2. `V3-B STRUCTURE-LITE`
3. `V3-C REGIME-SPECIALIZATION`
4. `V3-D SECTOR-RELATIVE`
5. `V3-E TRUE-RANKING`

The important change from the earlier draft is that `STRUCTURE-LITE` is promoted ahead of explicit regime gating. V2 already contains explicit market context and nonlinear HGB interactions; regime specialists would add fragmentation/complexity immediately, while compact causal price geometry is a more orthogonal information test.

## Research-governance changes

- every experiment asks one falsifiable question;
- exact frozen V2 champion is the control;
- normal candidate budget is control plus at most two bounded variants;
- maintain a permanent hypothesis/candidate ledger;
- failed/viewed variants stay in the research denominator;
- evaluate robustness distribution, not only median/mean;
- no post-result rescue inside the same hypothesis;
- use earlier development folds for repeated hypothesis discovery and reserve later development folds for one frozen late-development confirmation of the final V3 architecture;
- that late confirmation is still development evidence, not independent validation;
- surviving components are not automatically stacked: allow at most one preregistered integration experiment and prefer the simpler practically tied model;
- distributional, path-risk, broker-flow, event, fundamental, and macro-expansion lanes remain separate until their own hypotheses/data gates justify them.

## V2 boundary unchanged

`HGB_XS_MARKET` remains frozen. Fresh-forward V2 outcomes remain blocked. `FORWARD_OUTCOME_ACCESS_STARTED` must not be written. The V2 100-mature-session one-shot contract is unchanged.

## Next task

Next V3 task is **specification only**:

`RANKING_V3_RECENCY_SPEC_V1`

The spec must freeze the discovery-fold contract, exact V2 control, no more than two recency variants, weight formula/normalization, metrics, robustness gates, kill/promotion rule, hypothesis-ledger identity, runtime/provenance, and explicit prohibition on reserved V2 forward outcomes.

Do not fit/score V3 until that spec is independently reviewed and a separate run authorization is given.

## Commits

- roadmap audit creation: `5a79025b7985e76d789913d1c9faac6c5544a5f6`;
- backlog aligned to audited roadmap: `d026d44c4f5365003f0a527807ea168f506ec062`.
