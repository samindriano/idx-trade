# Handoff

from: Codex  
to: ChatGPT independent review  
task_id: IDX-ALTERNATIVE-ALPHA-DATA-FEASIBILITY-V1  
model_used: Orchestra with Luna xhigh read-only explorers  
reasoning_level: xhigh  
source_repository: samindriano/idx-trade  
source_commit: f8686af8e0d1f89c2288d77fc9ec47f0c2db360a  
branch: research/idx-alternative-alpha-data-feasibility-v1  
head_commit: filled after final commit

## Scope

One-shot comprehensive feasibility census for genuinely new IDX information
sets. No outcomes, labels, scores, models, counters, bulk backfill, provider
migration, existing-lane mutation, or duplicate Stockbit capture system.

## Files changed

- `docs/research/2026-08-21_IDX_ALTERNATIVE_ALPHA_DATA_FEASIBILITY_V1.md`
- `docs/artifacts/idx_alternative_alpha_data_feasibility_v1/source_inventory.csv`
- `docs/artifacts/idx_alternative_alpha_data_feasibility_v1/github_repo_inventory.csv`
- `docs/artifacts/idx_alternative_alpha_data_feasibility_v1/bounded_probe_results.csv`
- `docs/checkpoints/2026-08-21_IDX_ALTERNATIVE_ALPHA_DATA_FEASIBILITY_V1.md`
- this handoff

## Findings

- Overall: `CONDITIONAL_SOURCE_READY_NO_HISTORICAL_ALPHA_YET`.
- Stockbit Stream is actually accessible now but only latest-page;
  AADI/CUAN/SMBR = 30/30/29 rows for count=50; no historical cursor.
- Stockbit per-ticker broker flow is the most promising unproven
  orthogonal candidate, private and absent from the Zapi catalog.
- Official IDX disclosure/event data is the strongest provenance path for a
  bounded/prospective event corpus.
- IDX SBL/lendable is accessible as a current snapshot; history and
  completeness remain unknown.
- BI JISDOR/policy/inflation is a credible public fourth pilot.
- Yahoo `.JK` analyst/earnings/holders/summary are sparse/current-state-heavy
  or redundant; no immediate challenger.

## GitHub references pinned

Exact reviewed commits are in `github_repo_inventory.csv`, including
NeaByteLab/IDX-API `910b8db...`, nichsedge/idx-bei `75d6c0f...`,
INo-xious/stockbit-mcp `4d531349...`, Invezgo `964afc3...`, and the named
legacy Stockbit/IDX repositories with explicit reject reasons.

## Decisions

- `GO_PROSPECTIVE_CAPTURE_ONLY`: Stockbit Stream; IDX SBL/lendable.
- `GO_BOUNDED_PILOT`: Stockbit broker flow; official IDX disclosures/events;
  BI macro.
- `WAIT_FOR_MORE_EVIDENCE`: derivatives/open interest; Yahoo earnings and
  analysts.
- `DROP_REDUNDANT` / `DROP_LOW_VALUE`: generic OHLCV/intraday and current
  Yahoo snapshots.

## Blocking risks

Private Stockbit auth/ToS/schema drift; no social historical pagination;
official IDX retention boundary; SBL/derivative zero-field semantics;
Yahoo publication/revision timestamps and issuer coverage.

## Validation

This lane changed documentation and sanitized CSV artifacts only. Before push:
run `git diff --check`; no pytest is required because no executable source or
runtime contract changed. Raw provider responses remain external.

## Recommended next action

Stop for ChatGPT review. If approved, authorize one small account-bound,
read-only Stockbit broker-flow pilot or one prospective Stream archive
contract. Do not bulk backfill or open model/outcome work.
