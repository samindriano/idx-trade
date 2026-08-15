# Handoff — HSC Full-History Ledger V1 Result

from: Codex/HSC-Full-History-Ledger  
to: ChatGPT/HSC-Full-History-Ledger  
task_id: IDX-HSC-FULL-HISTORY-LEDGER-V1  
model_used: Luna xhigh  
reasoning_level: xhigh  
source_repository: samindriano/idx-trade  
source_commit: 52a62c4913402ad5d6908c6c06f2a0f738a7ba80  
branch: data/idx-hsc-full-history-ledger-v1  
head_commit: pending-final-commit  

## Scope

Recovered and hash-pinned official IDX HSC/RSC/correction bytes through the
bounded 2026-08-15 cutoff, materialized the strict HSC event CSV, replayed it
with the existing ledger implementation, and reconciled the 9/10/11/12/13/15/
14/51/final-current checkpoints. No free-float inference, features, models,
Foreign Flow integration, or outcome access.

## Findings

- 59 official event records: 56 originals, 2 corrections, 1 removal.
- Official PDF captures: 118; 24 reused from the accepted parent and 94 newly
  retrieved; zero download failures.
- July expansion reconciles exactly to 51 active tickers.
- Final bounded state through 2026-08-15 is 55 active tickers after AGAR,
  ALKA, BKDP, and BAJA additions.
- MGRO and MEGA correction lineage is preserved independently.
- LUCY removal is explicit and replays to 14 pre-expansion active names.
- CMNP and BAJA formatting/typo anomalies are retained in the parse audit and
  not silently discarded.
- No later RSC/correction was admitted from the preserved official metadata
  capture through the cutoff.

## Decisions

Verdict:
`HSC_FULL_HISTORY_LEDGER_READY_FOR_OWNERSHIP_CONCENTRATION_CONTRACT`

This is only a bounded event-ledger readiness result. The ledger does not
claim statutory free float, effective supply, locked shares, HHI, or a daily
feature panel.

## Artifacts

External root:
`D:\Documents\Project\idx-hsc-full-history-ledger-20260815-v1`

Manifest SHA-256:
`230fec0544fb7464e63008ee080fda0c8082049626529f0a565376601416b55d`

Normalized CSV SHA-256:
`afbbb642807e04d6050de3574fec49559eb8fcf2963039a53439e507f067cbd2`

Normalized JSON SHA-256:
`9033c801c042d6a10bf2a308513c8120ca8dd9585e85a95ae419a78ec874daa0`

## Validation

Focused tests: `16 passed`. Full pytest: `105 passed, 1 failed`, the known
unrelated storage expectation failure. `git diff --check`: pass.

## Recommended next action

Independent ChatGPT review of the bounded current-state target and methodology
classification before any ownership-concentration contract or feature work.
