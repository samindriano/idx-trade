# Handoff — Ownership / KSEI V1 Ready

from: ChatGPT reviewer
to: Codex local runtime
task_id: IDX-OWNERSHIP-KSEI-V1-SOURCE-AUDIT
branch: `data/ownership-ksei-v1`

## Scope

Initial point-in-time ownership snapshot/fact contract is implemented. The next task is local source discovery and a bounded official IDX/KSEI/Zapi audit only.

## Read first

- `docs/OWNERSHIP_KSEI_V1_SPEC.md`
- `src/idx_trade/ownership_pit.py`
- `tests/test_ownership_pit.py`

## Boundaries

Do not bulk-acquire years of files before source dates, publication timing, revision behavior, categories, and missing-file semantics are established.

Do not touch models/features, outcomes, OPEN, PIT sector, Historical Universe, Corporate Actions, Financial PIT, Foreign Flow, Path Risk, execution/PnL, or main.
