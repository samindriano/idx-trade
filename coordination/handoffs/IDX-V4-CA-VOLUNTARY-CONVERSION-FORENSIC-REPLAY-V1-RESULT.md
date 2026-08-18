# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-V4-CA-VOLUNTARY-CONVERSION-FORENSIC-REPLAY-V1
model_used: Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `ed6cd8aad1256df00ea5b09156f3d061e3cf3b50`
branch: `data/idx-v4-ca-voluntary-conversion-forensic-replay-v1`
head_commit: result documentation commit follows the frozen replay anchor
scope: one offline immutable-byte forensic replay of parent versus remediation audits

## Result

Validation passed: `15 passed in 0.63s`, `py_compile` PASS, and `git diff --check`
PASS from the exact worktree. Exactly one replay ran with zero provider calls.

- parent relevant events: `136`
- remediation relevant events: `102`
- removed/added: `34 / 0`
- parent Voluntary Conversion: `63`
- strict security-to-currency: `34`
- actual non-blocking reclassified: `34`
- remaining Voluntary Conversion schedule-required: `29`
- removed IDs exactly equal reclassified IDs: `YES`
- every removed ID satisfies strict predicate: `YES`
- changed 600-date rows: `600`; identical: `0`
- verdict: `FORENSIC_REPLAY_CONFIRMS_VOLUNTARY_CASH_RECLASSIFICATION_REPORTING_UNDERCOUNT`

Exact parsed ratio evidence is preserved in the ratio dump. Of 63 rows, 34
are `PARSED_SOURCE_TEXT_ONLY` with left security equal to the ticker and right
token `IDR`; 29 remain `UNRESOLVED_SOURCE_TEXT`.

## Promoted files

- `docs/artifacts/v4_ca_voluntary_conversion_forensic_replay_20260818_v1/summary.json`
- `docs/artifacts/v4_ca_voluntary_conversion_forensic_replay_20260818_v1/MANIFEST.json`
- `docs/artifacts/v4_ca_voluntary_conversion_forensic_replay_20260818_v1/event_set_diff.csv`
- `docs/artifacts/v4_ca_voluntary_conversion_forensic_replay_20260818_v1/voluntary_conversion_ratio_dump.csv`
- `docs/artifacts/v4_ca_voluntary_conversion_forensic_replay_20260818_v1/classifier_side_by_side.csv`
- `docs/artifacts/v4_ca_voluntary_conversion_forensic_replay_20260818_v1/continuity_per_date_diff.csv`

Manifest SHA: `495401d683b2faac953cb73086324561670c7c2b825055e18984729aba3b5287`.

## Boundaries and next action

No source/config patch was made after the replay output was exposed. No
provider, schedule, model, target, rank, performance, protected outcome, or
fresh-forward access occurred. Update only the matching TEAM_STATUS row to
`REVIEW`, push, and stop for ChatGPT review.
