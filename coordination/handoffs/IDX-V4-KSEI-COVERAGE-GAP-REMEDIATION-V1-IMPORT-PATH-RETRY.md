# Handoff — IDX-V4-KSEI-COVERAGE-GAP-REMEDIATION-V1 Import-Path Retry

from: ChatGPT
to: local Windows operator / Codex
branch: `data/idx-v4-ksei-coverage-gap-remediation-v1`
scientific/provider code anchor: `5b311e0398afb9099887cf7558c92f15d99029b8`

## Boundary

This is a continuation of the existing frozen 43-ticker lane after a zero-network import-path preflight failure. Do not patch source/config, redesign, broaden scope, or change any scientific/provider semantics.

## Step 0 — coordination

Fetch latest canonical `origin/main:coordination/TEAM_STATUS.md`. Confirm no newer ACTIVE lane owns the exact same 43-ticker remediation. Change the existing matching row from REVIEW to ACTIVE. Do not create a duplicate lane.

## Step 1 — checkout and import-path remediation

Pull latest branch and require a clean worktree.

In the **same PowerShell process that will execute all following commands**, run exactly:

```powershell
$env:PYTHONPATH = (Resolve-Path "src").Path
python -c "import idx_trade.v4_ksei_coverage_gap as m; print(m.__file__)"
```

The printed module path must resolve under the current worktree's `src\idx_trade\v4_ksei_coverage_gap.py`.

If not, STOP. Do not install/edit anything.

## Step 2 — repeat unchanged validation/preflight

Run:

```powershell
python -m pytest tests/test_v4_ksei_coverage_gap.py
python -m py_compile `
  src/idx_trade/v4_ksei_coverage_gap.py `
  scripts/preflight_v4_ksei_coverage_gap_runtime.py `
  scripts/run_v4_ksei_coverage_gap_remediation.py `
  scripts/run_v4_ca_coverage_gap_continuity_replay.py
git diff --check
python scripts/preflight_v4_ksei_coverage_gap_runtime.py
```

Expected focused pytest: `7 passed`.

Preflight must report:

- `status=V4_KSEI_COVERAGE_GAP_RUNTIME_PREFLIGHT_PASS`;
- `network_calls=0`;
- `gap_tickers=43`;
- identity SHA `1cd050985841519d24f58a38d10014693ff4a843cbd438586237ad4419ffe812`.

If any step fails, STOP without patch/retry.

## Step 3 — immutable inputs / roots

Verify all exact inputs from the original handoff still exist:

- parent census root: `D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1`
- base continuity ledger: `D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv`
- residual document root: `D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1`
- official calendar: `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv`
- prior event evidence: `docs\artifacts\ranking_v4_ca_continuity_gate_v1\event_family_evidence.csv`

The fresh roots must still NOT exist:

- `D:\Documents\Project\idx-v4-ksei-coverage-gap-remediation-20260818-v1`
- `D:\Documents\Project\idx-v4-ca-ksei-coverage-gap-continuity-20260818-v1`

If either output root exists, STOP; do not delete or rename it.

## Step 4 — exactly one targeted provider run

Run once:

```powershell
python scripts/run_v4_ksei_coverage_gap_remediation.py `
  --parent-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" `
  --output-dir "D:\Documents\Project\idx-v4-ksei-coverage-gap-remediation-20260818-v1"
```

Do not rerun the command if it errors.

If successful, record:

- recovered ticker count/list;
- remaining unresolved ticker count/list;
- parent/recovery failure classes;
- merged certified/unresolved counts;
- recovered history rows and active mechanical/unknown rows;
- provider request/raw capture counts;
- acquisition manifest and output hashes.

## Step 5 — exactly one continuity replay

Only after successful Step 4, run once:

```powershell
python scripts/run_v4_ca_coverage_gap_continuity_replay.py `
  --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" `
  --prior-event-evidence "docs\artifacts\ranking_v4_ca_continuity_gate_v1\event_family_evidence.csv" `
  --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" `
  --ksei-remediation-root "D:\Documents\Project\idx-v4-ksei-coverage-gap-remediation-20260818-v1" `
  --document-root "D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1" `
  --output-dir "D:\Documents\Project\idx-v4-ca-ksei-coverage-gap-continuity-20260818-v1"
```

STOP after this command regardless of verdict.

Record the exact continuity verdict, certification flag, certified/unresolved ticker counts, relevant/exact/schedule-required events/tickers, H5/H10/consensus passing-date counts and minimum rates, reason counts, and all small artifact hashes.

## Step 6 — promotion and stop

Promote the same small artifacts authorized in the original handoff, create result checkpoint/handoff, set the existing TEAM_STATUS row to REVIEW, push branch/main, require clean/synced state, and STOP.

No alternate provider, alias/ticker remap, parser relaxation, schedule rescue, threshold change, target/rank/model/prediction/performance/bootstrap, or protected/fresh-forward outcome access is authorized.
