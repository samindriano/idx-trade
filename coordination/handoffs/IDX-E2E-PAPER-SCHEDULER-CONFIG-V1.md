# Handoff

from: Codex root coordinator  
to: ChatGPT independent review / MAIN integration  
task_id: IDX-E2E-PAPER-SCHEDULER-CONFIG-V1  
model_used: Codex root  
reasoning_level: xhigh  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: `c5a32225c61b20f676115a042a5d51e2e6ddb30b`  
branch: `integration/idx-e2e-baseline-paper-v1`  
head_commit: e95c5c70b7cd8c2f7ec64b92c544411b16775b29

## Scope

Add a hash-pinned external runtime config loader and a single-argument
headless scheduler entrypoint for the existing E2E controller. No new data,
provider, model, state, or scheduler hierarchy was introduced.

## Files changed

- `src/idx_trade/e2e_paper_runtime_config_v1.py`
- `scripts/run_e2e_paper_scheduled_v1.py`
- `scripts/install_e2e_paper_task.ps1`
- focused tests for config hashing, same-snapshot hash/parse binding,
  secret-key rejection, exit semantics, and task isolation/retry settings.

## Findings / decisions

- The task action can carry only the runtime root; operational paths and
  hashes are loaded from an external immutable config; the config SHA is also
  pinned in the task action.
- Missing config, missing SHA sidecar, changed config bytes, relative paths,
  invalid commits, and secret-like keys fail closed.
- Config is hashed and parsed from one in-memory byte snapshot; the task action
  pins the same digest.
- The scheduled runner verifies its own config-pinned SHA and exact clean
  branch/HEAD before importing controller modules.
- `preopen_capture_start` is fixed to 08:30 Asia/Jakarta; invalid earlier or
  late values fail closed.
- Post-EOD task retries are 18:35/19:35/20:35, following the existing upstream
  EOD attempts at 18:30/19:30/20:30.
- Installer refuses an existing task and does not reference or modify
  `IDXTrade-ForwardEOD`, `IDXTrade-ForwardOpenArchive`, Official Open, or
  Stockbit tasks.
- The E2E task was not installed because the separately hash-pinned live CA
  attestation/provider configuration is still unavailable. This preserves the
  existing no-retroactive-paper-trading boundary.
- `coordination/TEAM_STATUS.md` was not edited; MAIN owns it.

## Validation

- focused new tests after SHA/repository pin hardening: PASS (11);
- existing operational/controller tests: PASS;
- full pytest: PASS with three pre-existing pandas FutureWarnings;
- `py_compile`: PASS;
- `git diff --check`: PASS.

## Next action

After ChatGPT review and explicit CA configuration, create the external config
and SHA sidecar, rerun scheduler preflight, and only then install the limited
user-level task. A first weekday cycle must still be proven separately.
