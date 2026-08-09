# Handoff

from: ChatGPT MAIN
to: local Codex Luna xhigh
task_id: IDX-FORWARD-OPEN-ARCHIVE-WINDOWS-INSTALL
model_used: GPT-5.6 Thinking
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: VERIFY_REMOTE_HEAD_AT_RUNTIME
branch: ops/idx-forward-open-archive-v1
head_commit: VERIFY_REMOTE_HEAD_AT_RUNTIME
scope: install and verify the source-blocked Windows forward Open archival scheduler only
files_changed: local Task Scheduler state and external runtime/status files only unless a factual install bug requires a bounded fix
findings: forward archive scaffold exists; no price provider is frozen; scheduler must fail closed until provider audit is complete
decisions_made: daily 22:00 + logon catch-up + StartWhenAvailable; 45-day lookback; immutable per-session archive; no silent source selection
decisions_needed: local repo path, Python executable/environment, external DataRoot; later separate provider-source decision
blocking_risks: Windows Task Scheduler registration semantics, wrong Python environment, wrong repo path, source accidentally configured without audit
validation_run: run full pytest; install task; inspect task triggers/settings; invoke task once and confirm BLOCKED_SOURCE_NOT_FROZEN plus latest_run.json; do not treat source block as an implementation failure
recommended_next_action: perform local installation, document factual result, then stop for ChatGPT review

## Runtime instructions

Use a Codex-managed **Worktree** based on existing branch:

`ops/idx-forward-open-archive-v1`

Read:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/FORWARD_OPEN_ARCHIVE_V1.md`
4. `docs/checkpoints/2026-08-10_FORWARD_OPEN_ARCHIVE_SCAFFOLD_READY.md`
5. this handoff

Verify repository, detached/worktree HEAD, remote branch HEAD, and clean state before local actions.

### Required local choices

Resolve factual local values rather than committing them:

- repository/worktree absolute path;
- Python executable that can import `idx_trade` and project dependencies;
- external data root, preferably under the existing IDX runtime-artifact root but outside Git.

Do not commit user-specific absolute paths.

### Validation before install

Run the full pytest suite.

Then test the source-blocked runner manually:

```powershell
python -m idx_trade.forward_open_archive --data-root "<DATA_ROOT>" --lookback-days 45
```

Expected current result:

`BLOCKED_SOURCE_NOT_FROZEN`

Expected durable file:

`<DATA_ROOT>\forward_open_archive\latest_run.json`

A process exit code indicating the source block is expected at this stage. Do not add a provider to make the command green.

### Install scheduled task

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_forward_open_archive_task.ps1 `
  -RepoPath "<WORKTREE_PATH>" `
  -DataRoot "<DATA_ROOT>" `
  -PythonExe "<PYTHON_EXE>" `
  -DailyTime "22:00" `
  -LookbackDays 45
```

Do **not** pass `-ProviderModule` yet.

Verify Task Scheduler entry `IDXTrade-ForwardOpenArchive` has:

- daily 22:00 trigger;
- AtLogOn trigger;
- StartWhenAvailable enabled;
- RunOnlyIfNetworkAvailable enabled;
- MultipleInstances = IgnoreNew;
- 45-minute execution limit;
- current-user interactive principal.

Manually start the task once. Confirm it fails closed because provider is unset and leaves logs/status artifacts. The expected source block must not be "fixed" by adding Yahoo/Zapi/IDX scraping or any other unreviewed provider.

### Prohibited

- no direct `idx.co.id` scraping/crawling;
- no provider-source implementation or selection;
- no historical Open backfill changes;
- no Ranking V1/V2 changes;
- no Stage-5 rerun;
- no execution-PnL/paper/live trading;
- no broker integration;
- no main merge;
- no credentials in Git;
- no force push/rebase/reset-hard.

### Completion

If installation is successful, update only factual installation documentation/checkpoint/handoff state if useful, commit those documentation-only changes on the worktree, and report:

- exact branch/HEAD;
- pytest result;
- resolved local Python path class (do not expose secrets);
- Task Scheduler trigger/settings verification;
- manual task result;
- status/log paths;
- confirmation provider remains unset and no price data was fetched.

Then STOP for ChatGPT review.
