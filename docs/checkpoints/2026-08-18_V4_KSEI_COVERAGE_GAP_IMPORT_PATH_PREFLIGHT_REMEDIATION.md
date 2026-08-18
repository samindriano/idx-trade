# V4 KSEI Coverage-Gap Remediation V1 — Import-Path Preflight Remediation

## Status

`PREFLIGHT_IMPORT_PATH_FAILURE_DIAGNOSED_OPERATIONAL_ONLY_RETRY_READY`

## Failed preflight

Branch `data/idx-v4-ksei-coverage-gap-remediation-v1` at HEAD `f3a2af51ec925b75498f798f3f1f1bbd72a5f35d` passed:

- focused pytest: `7 passed`;
- `py_compile`: PASS;
- `git diff --check`: PASS.

The zero-network runtime preflight then failed before any provider/input access with:

`ModuleNotFoundError: No module named 'idx_trade.v4_ksei_coverage_gap'`

No provider calls occurred and no output root was created.

## Root cause

The repository uses a `src/` package layout. `pyproject.toml` configures pytest with `pythonpath = ["src"]`, which explains why the focused tests imported the new module successfully. Direct execution with `python scripts/<runner>.py` does not inherit pytest's import-path injection, so `src/idx_trade` is not importable unless the package is installed or `src` is placed on `PYTHONPATH`.

The same condition affects the preflight, acquisition runner, and continuity replay because all three import `idx_trade` modules.

## Remediation

Do **not** patch scientific/provider source or install/change package versions.

In the same PowerShell process used for the retry, set exactly:

```powershell
$env:PYTHONPATH = (Resolve-Path "src").Path
```

Then rerun the unchanged validation/preflight and, only after PASS, the previously frozen one-shot acquisition/replay sequence.

This is operational import-path plumbing only. It does not alter:

- the frozen 43-ticker identity;
- provider URL/transport/retry policy;
- KSEI parser or CA semantics;
- parent hashes;
- continuity rules/gates;
- target/model/performance/outcome access boundaries.

## Scientific/provider anchor

Unchanged: `5b311e0398afb9099887cf7558c92f15d99029b8`.

No source/config change is authorized as part of this remediation.
