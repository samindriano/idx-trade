# Handoff: Financial PIT Alpha V1 completion result

from: Codex
to: ChatGPT reviewer
task_id: IDX-FINANCIAL-PIT-ALPHA-V1-FINANCIAL-ERA-COMPLETION1
model_used: GPT-5 Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `507aaf8bca3286996eb30f3f8e7ea161d8892cc1`
branch: `research/idx-financial-pit-alpha-v1`
head_commit: recorded after this handoff commit

## Scope

One authorized exact-contract completion run after the prior execution-wrapper
timeout. The run used a clean external output root and did not reuse partial
models.

## Frozen identity

- Contract SHA-256: `cabeb0db3db44996bda91472576855cb549965d19791f640717502cdd321993c`
- Support: 70,520 rows / 321 tickers
- Support SHA-256: `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6`
- Matrix SHA-256: `464c2a18bd7b238f98c786365026466bfd52c514022b3ced09798b2654665471`
- Folds: exactly `V2F4`, `V2F5`, `V2F6`

## Result

All nine fits completed in `16.12591` seconds. The primary paired result was:

- PR-AUC deltas: `+0.001278`, `+0.003010`, `-0.030705`;
- median PR-AUC delta: `+0.0012781203`;
- q25 PR-AUC delta: `-0.0147136528`;
- positive folds: `2/3`;
- median ROC change: candidate `0.4903306189` vs control `0.5087252608`;
- median Q5-Q1: candidate `0.0386820315` vs control `0.0465104028`.

The frozen guardrail is active and q25 paired PR is negative. Final verdict:

`FINANCIAL_PIT_ALPHA_V1_NO_SURVIVOR`

## Artifacts

External output root:

`D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-financial-era-completion1`

- artifact count: `16`;
- summary SHA-256: `3594934c846bacfd67eb7a775512be9a1a75b33af2c290f06d678a8100fc4b3f`;
- manifest SHA-256: `07241cc863315a354e241f4f60e9bb7554a5ad8c927fc0bf3472a1024f5ef70a`;
- predictions SHA-256: `20a77ba50c3319f9cf8fdb676fe15b557b7903e7fe91bc0452469a104bc70e20`;
- primary paired CSV SHA-256: `0fe94ec0c9448368bd87fdc53e7fd37a61cd3592a214cfd1489640694f29d19e`.

The manifest records all nine model hashes and all result artifact hashes.

## Boundary confirmation

No code or scientific contract changed. Previous partial output roots remain
read-only. No canonical refit/promotion, O2 access, fresh-forward access,
protected-forward outcome access, provider call, or third run occurred.

## Decision needed

Independent ChatGPT review of the frozen `NO_SURVIVOR` result. No follow-up
candidate or rescue is proposed by this handoff.

