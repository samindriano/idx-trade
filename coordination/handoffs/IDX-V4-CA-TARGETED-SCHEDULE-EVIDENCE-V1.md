# Handoff — IDX-V4-CA-TARGETED-SCHEDULE-EVIDENCE-V1

from: ChatGPT
to: local Windows operator / Codex
task_id: `IDX-V4-CA-TARGETED-SCHEDULE-EVIDENCE-V1`
branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`
scientific/code-test anchor: `5ea347b29d6ce81a1178e9dd2a6d6d37a656ab14`
parent: `data/idx-v4-ca-schedule-event-impact-attribution-v1@a7a3b998930cf0506d3ddc9cbbd21636ba6f3e93`

## Mission

Execute exactly one targeted official-KSEI evidence acquisition for the frozen seven-event priority subset, then exactly one outcome-blind continuity replay using whatever exact evidence was actually recovered. Stop after the replay regardless of pass/fail.

Do not redesign, patch, broaden scope, or retry after result exposure.

## Step 0 — canonical coordination gate

Before validation/provider access:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer ACTIVE lane owns this exact targeted seven-event CA evidence scope;
3. add/update exactly one row:
   - task: `V4 CA targeted schedule evidence V1`
   - status: `ACTIVE`
   - owner: `Codex/V4-CA-Targeted-Schedule-Evidence`
   - branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`
   - boundary: `exact NISP static cash + six selected KSEI schedules + one continuity replay; no target/model/outcome`;
4. push only that coordination edit to `main` using the shared-file safety rule.

If overlapping ACTIVE scope exists, STOP.

## Step 1 — checkout and validation

Pull the exact branch and confirm scientific/code-test anchor
`5ea347b29d6ce81a1178e9dd2a6d6d37a656ab14` remains in history unchanged.
Worktree must be clean.

Run from repository root:

```powershell
python -m pytest tests/test_v4_ca_targeted_schedule_evidence.py
python -m py_compile src/idx_trade/v4_ca_targeted_schedule_evidence.py scripts/run_v4_ca_targeted_schedule_evidence.py scripts/run_v4_ca_targeted_schedule_continuity_replay.py
python -c "import curl_cffi, lxml, pypdf, pandas, numpy; print('V4_CA_TARGETED_EVIDENCE_RUNTIME_PREFLIGHT_PASS')"
git diff --check
```

Expected focused pytest: **11 passed**.

The new direct scripts bootstrap the repository `src` directory themselves; do not patch `PYTHONPATH` logic.

If any validation/preflight fails: STOP. Do not patch locally and do not call KSEI.

## Step 2 — exact immutable inputs / fresh roots

Require repo-promoted selected subset:

`docs\artifacts\v4_ca_schedule_event_impact_attribution_20260818_v1\selected_schedule_event_subset.csv`

Pinned SHA-256:
`f6650daf7256196f976b0a9d161dbf0cf896d0d349306be4fe4c76b1d2168529`.

Require official calendar:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv`

Pinned SHA-256:
`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`.

Acquisition output root must NOT exist:

`D:\Documents\Project\idx-v4-ca-targeted-schedule-evidence-20260818-v1`

Continuity output root must NOT exist:

`D:\Documents\Project\idx-v4-ca-targeted-schedule-continuity-20260818-v1`

If either exists, STOP. Do not delete/reuse/rename it.

Also require for the later replay:

- frozen base continuity ledger:
  `D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv`
- repo-promoted prior event evidence:
  `docs\artifacts\ranking_v4_ca_continuity_gate_v1\event_family_evidence.csv`
- accepted KSEI remediation root:
  `D:\Documents\Project\idx-v4-ksei-coverage-gap-remediation-20260818-v1`
- accepted residual-document root:
  `D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1`

Do not substitute the obsolete/missing external filename `corporate_action_event_evidence.csv`; the promoted `event_family_evidence.csv` is the hash-pinned accepted evidence file.

If any required replay input is absent, STOP before acquisition. This avoids acquiring evidence that cannot be replayed under the frozen lineage.

## Step 3 — exactly one targeted provider acquisition

Run exactly once:

```powershell
python scripts/run_v4_ca_targeted_schedule_evidence.py `
  --selected-subset "docs\artifacts\v4_ca_schedule_event_impact_attribution_20260818_v1\selected_schedule_event_subset.csv" `
  --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" `
  --output-dir "D:\Documents\Project\idx-v4-ca-targeted-schedule-evidence-20260818-v1"
```

Authorized provider scope is exactly:

- NISP: one strict current KSEI registered-security page path for static security-to-currency evidence;
- ISAT, ADRO, PANI, RAJA, PTRO, CUAN: only KSEI schedule-index months implied by each frozen source-date ±2 months and candidate schedule documents whose index subject contains the exact ticker.

No other ticker/event/source is authorized.

If the command exits non-zero: STOP. Do not patch, delete output, retry, use browser/manual evidence, use a mirror, or run continuity.

If it exits zero, record exactly:

- provider request-attempt records;
- index pages requested;
- candidate documents;
- NISP static linkage status and ratio fields if exact;
- exact schedule transitions by ticker with date, semantic, KSEI reference, source SHA;
- unresolved selected events and diagnostics;
- acquisition manifest/summary/evidence/linkage/parse hashes.

Do not edit source/config/code after seeing these results.

## Step 4 — exactly one continuity replay

If Step 3 exited zero, run this exactly once without any intervening patch:

```powershell
python scripts/run_v4_ca_targeted_schedule_continuity_replay.py `
  --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" `
  --prior-event-evidence "docs\artifacts\ranking_v4_ca_continuity_gate_v1\event_family_evidence.csv" `
  --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" `
  --ksei-remediation-root "D:\Documents\Project\idx-v4-ksei-coverage-gap-remediation-20260818-v1" `
  --residual-document-root "D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1" `
  --targeted-evidence-root "D:\Documents\Project\idx-v4-ca-targeted-schedule-evidence-20260818-v1" `
  --output-dir "D:\Documents\Project\idx-v4-ca-targeted-schedule-continuity-20260818-v1"
```

Then STOP regardless of verdict.

Report exactly:

- continuity verdict and `corporate_action_continuity_certified`;
- final relevant / NON_BLOCKING / EXACT_TRANSITION / SCHEDULE_REQUIRED event counts;
- remaining schedule-required event/ticker count;
- H5/H10/consensus passing-date counts and minimum rates;
- continuity reason/status counts;
- known mechanical-crossing rows after exact transitions are admitted;
- 12 unresolved KSEI tickers / coverage rows and MEGA/SCMA cross-source blockers remain fail-closed unless the frozen rebuild itself says otherwise;
- targeted overlay SHA, continuity summary SHA, manifest SHA;
- provider calls occurred only in Step 3 and continuity replay provider calls are zero.

Do **not** run R5/R10, target/rank materialization, model, prediction, IC/performance, or bootstrap even if continuity certifies. ChatGPT review is mandatory first.

## Step 5 — promote small evidence only

Keep raw HTML/PDF/request bytes and full continuity ledger external.

Promote a compact acquisition bundle under a new `docs/artifacts/` directory:

- `MANIFEST.json`
- `summary.json`
- `targeted_evidence.csv`
- `targeted_event_linkage_audit.csv`
- `targeted_schedule_document_parse_audit.csv` if reasonably small

Promote a compact continuity bundle:

- `MANIFEST.json`
- `summary.json`
- `event_semantics_audit.csv`
- `schedule_evidence_needs.csv`
- `v4_frozen_continuity_per_date_event_window.csv`
- `targeted_schedule_continuity_overlay.json`

Do not commit the full rebuilt continuity ledger or raw provider corpus.

Add one factual dated checkpoint and one result handoff. Update the canonical TEAM_STATUS lane to `REVIEW` with final branch HEAD, exact recovered/unresolved seven-event counts, continuity verdict/rates, and explicit no-target/model/outcome statement. Push branch + coordination update, verify branch/main clean and synced, then STOP.

## Hard restrictions

- exact seven selected event identities only;
- official KSEI only;
- no 39-event recrawl;
- no 610-ticker recrawl or 12-ticker coverage retry;
- no source substitution or manual evidence admission;
- no Record/Distribution -> transition fallback;
- no inferred next session or price-jump inference;
- no parser/semantic change after acquisition result exposure;
- no threshold/universe change;
- no target/model/performance/protected/fresh-forward outcome access.