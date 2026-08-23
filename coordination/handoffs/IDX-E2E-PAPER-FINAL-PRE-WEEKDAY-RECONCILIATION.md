# Handoff

from: Codex
to: MAIN / ChatGPT reviewer
task_id: IDX-E2E-PAPER-FINAL-PRE-WEEKDAY-RECONCILIATION
model_used: GPT-5.6 + native read-only side audit
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: c943960af93785a2eba3989d6fd34e5392f4cd26
branch: integration/idx-e2e-baseline-paper-v1
head_commit: documentation descendant of source_commit

## scope

Final Sunday pre-weekday reconciliation of the existing E2E PAPER and
execution-grade Official Open deployment. No science, target, model, outcome,
broker, or protected-forward changes.

## files_changed

- `tests/test_v4_x1_execution_v1_official_open_verify.py` — one stale expected
  error updated to the hardened Zapi project-marker rejection.
- `docs/checkpoints/2026-08-23_E2E_FINAL_PRE_WEEKDAY_RECONCILIATION.md`
- this handoff

## findings

- Remote hardening baseline `af7c65f787b231a25dfff3126dabeb59c93a33f8` was
  fast-forwarded and validated.
- Before pin reconciliation, the live E2E config still expected
  `759e1c0e...`; its CA capture-script hash was also stale
  (`a391b776...` versus the actual `76a5af4c...`).
- The official production CA capture smoke (`POST_EOD`, BBCA,
  2026-08-21) failed closed at the first `ListingActivity/GetIssuedHistory`
  request with HTTP 403. No final manifest or attestation was promoted.

## validation_run

- Official Open / execution focused: 47 passed.
- Operational / CA / orchestration / phase / Official Open focused: 97 passed.
- Full pytest: 702 passed, 3 pre-existing pandas warnings, 0 failures.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- No protected outcomes, model scoring, broker calls, or Stockbit calls.

## deployment_action

After the documentation commit, repin the external config under
`%LOCALAPPDATA%\IDXTrade\e2e_baseline_paper_v1\operational` to the final
clean branch HEAD and actual script hashes. Update only the existing
`IDXTrade-E2E-Paper` action's config SHA; preserve its 11 daily triggers,
`StartWhenAvailable`, `IgnoreNew`, Limited user-level principal, and network
requirement. Do not reinstall or duplicate tasks. Leave
`IDXTrade-E2E-OfficialOpen` and legacy tasks otherwise unchanged.

## remaining evidence

The official IDX CA endpoint remains blocked by HTTP 403 in this environment,
so real V1.2 provider capture and verifier acceptance remain pending. A
weekday same-session POST_EOD → PREOPEN → Official Open → paper chain is also
pending. Sunday no-op is not weekday proof and no retroactive paper execution
is authorized.

## recommended_next_action

Review the final pin/task reconciliation and the 403 blocker. On the first
legitimate weekday, inspect the genuinely prospective chain only; do not
backfill a missed session or claim a live pass from a weekend run.
