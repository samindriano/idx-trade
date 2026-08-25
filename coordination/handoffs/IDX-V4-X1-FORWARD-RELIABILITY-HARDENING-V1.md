# Handoff

from: Codex
to: MAIN / independent reviewer
task_id: IDX-V4-X1-FORWARD-RELIABILITY-HARDENING-V1
model_used: GPT-5 Codex
reasoning_level: high
source_repository: `samindriano/idx-trade`
source_commit: `2be7160f20184e489f7a9f82a0d6aac890622c7e`
branch: `research/idx-v4-x1-prospective-evaluation-protocol-v1`
head_commit: `2eba462c78888b1034f5e979306f1aaaf66b43f8`

scope: sequential PR #83 target provenance resolution plus separate Stockbit,
Official Open, and outcome-blind evidence-health reliability lanes

files_changed: Package A provenance graph/checkpoint/handoff on PR #83; see
PR #84, PR #85, and PR #86 for separated reliability changes and exact file
lists.

findings:
- canonical target identity is proven from retained semantic lineage, not IC
  numeric proximity;
- `0.0980538834688018` remains historical-reference provenance unresolved only;
- Stockbit mixed HTTP-response -> RequestException bookkeeping is fixed and
  tested;
- Official Open retries/fallback are bounded and fail closed on invalid direct
  200 responses; the runner now targets the hardened v2 runtime;
- outcome-blind health report for 2026-08-24 is correctly pending because the
  Official Open and downstream paper artifacts are absent;
- no genuine 2026-08-25 scheduled run had occurred at 08:14 WIB.

decisions_made:
- frozen IDX/OpenPrice/model/Decision/Sizing/Execution/counter contracts were
  not changed;
- no provider capture, protected outcome loader, marker, or counter access was
  performed;
- no scheduler task was reinstalled or mutated;
- `TEAM_STATUS.md` was not edited from a non-MAIN branch.

decisions_needed:
- review/merge ordering for PR #84, PR #85 (base integration branch), and PR
  #86;
- update the separate deployed runtime checkout to the PR #85 runner before
  the next natural Official Open proof;
- MAIN-owned TEAM_STATUS status update.

blocking_risks:
- live proof is still pending and the last Official Open run failed closed;
- the deployed runtime checkout is separate from PR #85 until integration;
- the current five-trigger execution-grade morning window remains bounded;
  post-window evidence resolution needs a separate frozen contract;
- PR #84 CI was still running at handoff time and PR #86 has no GitHub check.

validation_run:
- PR #83: target identity 18, preflight 7, gate 56, evaluator 19, full 176;
- PR #84: focused 27, full 78;
- PR #85: focused 61, full 760, PowerShell parse, py_compile, diff-check;
- PR #86: focused 10, full 760, py_compile, diff-check;
- external health report: one metadata/hash-only run, SHA
  `922163578e424c509981d39ce99e963b992e29be2a52ba4660884ee54f1a2560`.

recommended_next_action: MAIN/reviewer should review the three reliability PRs,
integrate only after CI and lineage checks, update the separate runtime checkout,
then wait for the next genuine scheduled session. Do not open protected outcomes
or declare a first controlled E2E pass before all frozen artifacts exist.
