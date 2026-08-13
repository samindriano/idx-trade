# Path Risk V1 Discovery — Import Preflight Block

Date: 2026-08-10 (Asia/Jakarta)
Status: **PRE-OUTCOME IMPORT BLOCK — PR-001 REMAINS UNVIEWED**

## What happened

The authorized local Path Risk V1 PR-001 F1-F4 discovery command stopped before the discovery runner loaded:

```text
No module named idx_trade.path_risk_v1_discovery_run
```

The working tree was clean and synced at `ae7f2bdf57c40b47e835e1f7e3da6d2c43f77bc6`. Full pytest passed (`381 passed, 0 failed, 3 warnings`). No output directory, target table, model table, metrics, predictions, model artifact, or summary was produced.

## Root cause

The repository uses a `src/` package layout:

```toml
[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

Therefore pytest resolves the current checkout's `src/idx_trade`, but a bare `python -m idx_trade...` can resolve another installed/inherited `idx_trade` package when the current `src` path is not explicitly present.

The failed local shell resolved `idx_trade` from an older Codex worktree:

```text
C:\Users\Sam\.codex\worktrees\idx-forward-open-archive-v1\idx-trade\src\idx_trade
```

That older package did not contain `path_risk_v1_discovery_run.py`. The intended runner remains present in the active research branch at:

```text
src/idx_trade/path_risk_v1_discovery_run.py
```

This is a runtime import-path isolation issue, not a runner rename or missing implementation.

## Outcome-access accounting

This stop occurred before the discovery runner loaded and before any Path Risk label/outcome materialization.

Confirmed untouched:

- PR-001 result remains unviewed;
- no F1-F4 Path Risk target rows or metrics were produced;
- no Path Risk F5/F6 outcome was accessed;
- no post-2026-07-31 fresh-forward outcome was accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
- final V3-B ranker remains unchanged;
- no risk-veto or alpha+risk integration rule exists.

The failed import therefore does **not** consume the authorized one-shot PR-001 historical outcome run.

## Corrective action

The run handoff now explicitly replaces inherited `PYTHONPATH` with the current checkout's resolved `src` directory and performs a fail-closed import-path assertion for both `idx_trade.__file__` and `idx_trade.path_risk_v1_discovery_run.__file__` before pytest or the real run.

Controlling handoff:

`coordination/handoffs/IDX-PATH-RISK-V1-DISCOVERY-F1-F4-RUN.md`

No Path Risk research semantics, model, feature set, folds, target, quantile, gates, or outcome boundaries changed.
