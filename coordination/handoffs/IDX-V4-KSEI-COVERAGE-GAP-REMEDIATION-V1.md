# Handoff — IDX-V4-KSEI-COVERAGE-GAP-REMEDIATION-V1

from: ChatGPT
to: local Windows operator / Codex
task_id: `IDX-V4-KSEI-COVERAGE-GAP-REMEDIATION-V1`
branch: `data/idx-v4-ksei-coverage-gap-remediation-v1`
scientific/provider code anchor: `5b311e0398afb9099887cf7558c92f15d99029b8`
parent decision: `data/idx-v4-ca-blocker-attribution-v1@052351372215a5752199513a23cf3f7373ac1f59`

## Mission

Execute exactly one bounded official-KSEI recovery over the frozen 43 unresolved
tickers, then—only if that run completes successfully—execute exactly one
outcome-blind V4 CA continuity replay using the resulting coverage/history
overlay. STOP after the replay regardless of verdict.

Do not design, patch, broaden the ticker set, recrawl the other 567 tickers,
substitute a source, relax the parser, or access target/model/performance/
protected outcomes.

## Step 0 — canonical coordination hard gate

Before local validation/provider execution:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer ACTIVE lane owns this exact 43-ticker KSEI coverage-gap
   remediation scope;
3. add/update exactly one row:
   - task: `V4 KSEI coverage-gap remediation V1`
   - status: `ACTIVE`
   - owner: `Codex/V4-KSEI-Coverage-Gap`
   - branch: `data/idx-v4-ksei-coverage-gap-remediation-v1`
   - boundary: `exact 43 unresolved KSEI registered-security histories only; strict parser; one targeted provider run + one continuity replay; no 610 recrawl/alternate source/target/model/outcome`
4. push only that coordination edit to `main` under the shared-file safety rule.

If an overlapping ACTIVE lane exists, STOP.

## Step 1 — exact branch and validation

Checkout/pull this branch. Confirm code anchor
`5b311e0398afb9099887cf7558c92f15d99029b8` exists unchanged in history.
Worktree must be clean.

Run exactly:

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

Expected focused test count: `7 passed`.
Runtime preflight must report:
`V4_KSEI_COVERAGE_GAP_RUNTIME_PREFLIGHT_PASS`, `network_calls=0`, 43 tickers,
and identity SHA
`1cd050985841519d24f58a38d10014693ff4a843cbd438586237ad4419ffe812`.

If any validation/preflight fails, STOP and report. Do not patch locally.

## Step 2 — immutable external input preflight

Require exact parent census root:

`D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1`

The acquisition runner will independently enforce exact parent hashes for
MANIFEST, summary, ticker coverage, history, and request records.

Require the later continuity inputs to exist before consuming provider budget:

- base continuity ledger:
  `D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv`
- residual document root:
  `D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1`
- official calendar:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv`
- repo prior event evidence:
  `docs\artifacts\ranking_v4_ca_continuity_gate_v1\event_family_evidence.csv`

Fresh acquisition output root must NOT exist:

`D:\Documents\Project\idx-v4-ksei-coverage-gap-remediation-20260818-v1`

Fresh continuity output root must NOT exist:

`D:\Documents\Project\idx-v4-ca-ksei-coverage-gap-continuity-20260818-v1`

If either exists, STOP. Do not delete, overwrite, or choose another root without
ChatGPT review.

## Step 3 — one targeted 43-ticker provider run

Run exactly once:

```powershell
python scripts/run_v4_ksei_coverage_gap_remediation.py `
  --parent-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" `
  --output-dir "D:\Documents\Project\idx-v4-ksei-coverage-gap-remediation-20260818-v1"
```

The runner must contact only the frozen 43 KSEI security URLs. Do not retry the
whole command if it errors. Do not manually fetch missing tickers.

After a successful command, record before Stage 4:

- parent failure-class counts;
- recovered ticker count and exact ticker list;
- remaining unresolved ticker count and exact ticker list;
- recovery failure-class counts;
- merged certified/unresolved ticker counts;
- recovered history row count;
- recovered active mechanical-or-unknown row count;
- provider request/raw capture counts;
- acquisition MANIFEST SHA and summary/output hashes.

Do not interpret a high recovered count as continuity certification.

## Step 4 — exactly one continuity replay

Only if Step 3 returned exit code 0 and emitted a valid MANIFEST/summary, run:

```powershell
python scripts/run_v4_ca_coverage_gap_continuity_replay.py `
  --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" `
  --prior-event-evidence "docs\artifacts\ranking_v4_ca_continuity_gate_v1\event_family_evidence.csv" `
  --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" `
  --ksei-remediation-root "D:\Documents\Project\idx-v4-ksei-coverage-gap-remediation-20260818-v1" `
  --document-root "D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1" `
  --output-dir "D:\Documents\Project\idx-v4-ca-ksei-coverage-gap-continuity-20260818-v1"
```

Run once only. The exact recovered histories—including any newly discovered
mechanical/unknown events—must flow into the replay. Do not suppress new
schedule requirements.

Record:

- continuity verdict;
- `corporate_action_continuity_certified`;
- coverage certified/unresolved ticker counts;
- relevant/exact/schedule-required event counts and schedule-required tickers;
- cross-source conflict tickers;
- H5/H10/consensus gate-date counts;
- minimum H5/H10/consensus rates and worst dates if available;
- continuity status/reason counts;
- continuity MANIFEST, summary, event-semantics, per-date, schedule-needs, and
  coverage-gap overlay hashes.

STOP after this whether certified, blocked, or error. Certification does not
automatically authorize R5/R10/model execution; ChatGPT review is required.

## Step 5 — promotion / TEAM_STATUS

Promote only small artifacts to the branch:

Acquisition:
- `summary.json`
- `MANIFEST.json`
- `coverage_gap_results.csv`
- `parent_failure_diagnostic.csv`

Continuity, if completed:
- `summary.json`
- `MANIFEST.json`
- `event_semantics_audit.csv`
- `schedule_evidence_needs.csv`
- `v4_frozen_continuity_per_date_event_window.csv`
- `ksei_coverage_gap_continuity_overlay.json`

Keep raw HTML, request-record delta, full merged history, full merged coverage
bundle if considered large, and full continuity ledger external. Do not commit
provider raw bytes.

Create a concise result checkpoint + handoff. Update the matching canonical
TEAM_STATUS row to `REVIEW` with exact result/blocker and push. Branch/main must
be clean and synced.

## Hard stop

No Stage-2 schedule acquisition, no alternate source, no alias/ticker mapping
repair, no parser relaxation, no 567-ticker recrawl, no cross-source conflict
repair, no threshold/universe change, no R5/R10, target/rank, model, prediction,
IC/performance/bootstrap, protected/fresh-forward outcomes, or V4 contract
rescue is authorized in this lane.
