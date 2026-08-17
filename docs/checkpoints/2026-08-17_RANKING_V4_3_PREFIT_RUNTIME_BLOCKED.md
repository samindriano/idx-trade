# Ranking V4-3 prefit runtime — blocked preflight

Date: 2026-08-17 (Asia/Jakarta)

Branch: `research/idx-ranking-v4-3-prefit-runtime-v1`

Attempted HEAD: `2c50e4a24e42593360f5ef6e87b28abe4768b5db`

## Result

`V4_3_PREFIT_RUNTIME_CAPTURE_BLOCKED_PINNED_PREREGISTRATION_HASH_MISMATCH`

The requested preflight was run without changing the frozen configuration.
The focused suite returned `8 passed, 1 failed` across the two requested test
files. The failing assertion is the protocol byte pin for
`config/ranking_v4_3_preregistration.json`:

- protocol expected SHA-256: `835da85549b1d6874cb2ab49a029b9f4358fdf28cb8379b3f9df105835b05849`;
- actual SHA-256 at HEAD: `3a54dcf0266f8a2808b8c1d73dda41a32baea368e6b48aac21e9fa073f6824ed`;
- actual bytes are identical to `HEAD:config/ranking_v4_3_preregistration.json`;
- `config/ranking_v4_3_preregistration.json` was not modified.

The requested compile and whitespace checks passed:

- `python -m py_compile scripts/capture_v4_3_prefit_environment.py`: PASS;
- `git diff --check`: PASS;
- worktree was clean before capture preflight;
- requested external output directory did not exist before the blocked run.

## Boundary confirmation

The environment capture was **not** started. No environment manifest was
created or promoted. No R5/R10 rows, target ranks, targets, model fit,
predictions, IC/Top30/raw-return performance, provider calls, or protected /
fresh-forward outcomes were accessed. No V4 contract, source code, or frozen
configuration was changed.

The next action requires ChatGPT review and an explicit correction of the
stale/mismatched frozen byte pin; this lane must not silently repair it.
