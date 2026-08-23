# E2E PAPER Scheduler Config Loader V1

Date: 2026-08-23 Asia/Jakarta  
Branch: `integration/idx-e2e-baseline-paper-v1`  
Implementation parent: `c5a32225c61b20f676115a042a5d51e2e6ddb30b`

## Delivered

The E2E controller now has a deterministic external-runtime entrypoint:

- `src/idx_trade/e2e_paper_runtime_config_v1.py` loads only
  `%LOCALAPPDATA%\IDXTrade\e2e_baseline_paper_v1\operational\config.json`;
- `config.json.sha256` is required and must match the exact config bytes;
- all critical paths are absolute and all provider/CA/model-independent
  deployment identities remain explicit;
- secret-like config keys are rejected;
- `scripts/run_e2e_paper_scheduled_v1.py` passes only the loaded immutable
  config into the existing controller;
- `scripts/install_e2e_paper_task.ps1` prepares a user-level, limited,
  network-aware, `IgnoreNew`, `StartWhenAvailable` task with EOD and PREOPEN
  retry triggers without touching existing tasks.

The scheduler action contains only the Python runner, runtime root, and the
config SHA pin. It does not contain credentials or CA material. The runner also
requires the configured repository root to equal its own checkout root.

## Safety boundary

The installer refuses to register the task until the external config and its
SHA sidecar exist. The live CA attestation/provider configuration is still not
available on this machine, so the task was intentionally not installed and no
CA bootstrap or paper execution was attempted.

## Validation

- new focused config/scheduler tests: PASS, 6 tests;
- controller/operational focused regression tests: PASS;
- full pytest: PASS, with only the three existing pandas FutureWarnings;
- `py_compile`: PASS;
- `git diff --check`: PASS;
- no provider calls, protected outcome access, model refit/rescore, broker
  action, scheduler mutation, or TEAM_STATUS edit.
