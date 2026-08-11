# Handoff — Ownership / KSEI V1 source audit result

from: Codex local runtime
to: ChatGPT reviewer
task_id: IDX-OWNERSHIP-KSEI-V1-SOURCE-AUDIT
model_used: Codex local runtime
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `df26e33e41872b19794ca43e8e02109c0aead0c5`
branch: `data/ownership-ksei-v1`
head_commit: final commit reported in the completion message and GitHub PR #23

## Scope

Bounded Ownership/KSEI source audit only. No bulk historical acquisition and
no model, feature, outcome, OPEN, PIT-sector, Historical Universe, Corporate
Actions, Financial PIT, Foreign Flow, Path Risk, execution/PnL, or main work.

## Files changed

- `docs/OWNERSHIP_KSEI_V1_SPEC.md` — factual audit-status update.
- `docs/checkpoints/2026-08-12_OWNERSHIP_KSEI_SOURCE_AUDIT.md` — complete
  evidence report.
- this handoff.

Raw captures remain outside Git:
`D:\Documents\Project\idx-trade-ownership-ksei-20260812`.

## Findings

- Focused pytest: 7 passed.
- Full pytest: 478 passed, 0 failed, 3 warnings, 29.57s.
- Zapi IDX ownership-files exposes official IDX file metadata for >1%, >5%,
  investor classification, and investor type files.
- Zapi KSEI ownership is per-security and returns local/foreign totals, nine
  investor categories per side, outstanding, recorded total, and two foreign
  percentages.
- Zapi demographics/distribution are market-wide aggregates, not per-security.
- Direct KSEI public monthly ZIPs matched Zapi exactly for 198/198 compared
  fields across BBCA/AADI/BBRI and May/June/July 2026.
- Direct KSEI archive samples passed non-negative, unique-code, and total
  arithmetic checks from 2021-12 through 2026-07.
- Zapi's response timestamp is retrieval time; no source publication timestamp
  or timezone was found.
- The >1% official workbook explicitly allows prior-period updates, so
  immutable revision lineage is not established.

## Decisions

- Source discovery: PASS.
- Bounded per-security semantics: PASS.
- PIT timing: BLOCKED / fail closed.
- Complete historical coverage: not demonstrated.
- Bulk acquisition: NO-GO until publication-time/version handling and a full
  monthly/file census are solved.
- No real snapshot was mapped into `ownership_pit.py` because doing so would
  require inventing a timezone-aware `published_at`.

## Decisions needed

1. Whether to obtain a source that preserves official publication timestamps
   and immutable corrections, or explicitly approve a conservative publication
   upper-bound policy for a future bounded use case.
2. Whether to authorize a month-by-month direct KSEI/IDX file census after that
   timing decision.

## Validation

Focused and full pytest were run before documentation-only changes and passed.
No implementation fix was needed. After the documentation commit, verify the
tree is clean and the branch is synchronized with origin.

## Recommended next action

ChatGPT review should decide the publication-time/version policy first. Until
then, keep Ownership/KSEI source work at audit status and do not bulk-fill or
materialize PIT ownership snapshots.
