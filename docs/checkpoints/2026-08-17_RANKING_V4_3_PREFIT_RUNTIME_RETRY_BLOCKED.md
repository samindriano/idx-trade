# Ranking V4-3 prefit runtime — remediation retry blocked

Date: 2026-08-17 (Asia/Jakarta)

Branch: `research/idx-ranking-v4-3-prefit-runtime-v1`

Attempted HEAD: `c540981255972cac10b11cfc48b9e8550418add1`

## Result

`V4_3_PREFIT_RUNTIME_CAPTURE_BLOCKED_STALE_CANONICAL_PREREGISTRATION_PIN`

The remediation retry was executed with the updated canonical-`git show`
verification path. The focused suite returned `9 passed, 1 failed`. The
remaining failure is not a Windows checkout conversion: the canonical bytes
at `HEAD:config/ranking_v4_3_preregistration.json` themselves hash to
`3a54dcf0266f8a2808b8c1d73dda41a32baea368e6b48aac21e9fa073f6824ed`, while
the frozen protocol still requires
`835da85549b1d6874cb2ab49a029b9f4358fdf28cb8379b3f9df105835b05849`.

The working-tree bytes equal the canonical Git bytes. The preregistration
config and frozen protocol were not edited during this retry.

Validation otherwise passed:

- `python -m py_compile scripts/capture_v4_3_prefit_environment.py`: PASS;
- `git diff --check`: PASS;
- worktree clean before capture;
- fresh output directory `D:\Documents\Project\idx-v4-3-prefit-runtime-20260817-v2` remained absent.

## Boundary confirmation

The environment capture did **not** start. No environment manifest was
created or promoted. No R5/R10 rows, target ranks, targets, model fit,
predictions, IC/Top30/raw-return performance, provider calls, or protected /
fresh-forward outcomes were accessed.

This lane requires ChatGPT review of the stale canonical preregistration SHA
pin. Do not silently replace the pin or run the capture until that identity is
explicitly corrected and reviewed.
