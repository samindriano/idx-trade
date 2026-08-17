# Handoff — IDX-V4-CA-EVENT-WINDOW-SEMANTICS-V1 Result

from: local Windows execution operator  
to: ChatGPT reviewer  
task_id: IDX-V4-CA-EVENT-WINDOW-SEMANTICS-V1  
source_repository: `samindriano/idx-trade`  
branch: `data/idx-v4-ca-event-window-semantics-v1`  
head: `8affe6d6024109b438f4d9d4b55e43759c4f8b71`

## Scope completed

Reused the immutable Stage 1 result without rerunning it. Executed the exact
pin-remediated Stage 2 official KSEI schedule acquisition with fresh output
root `D:\Documents\Project\idx-v4-ca-schedule-evidence-20260818-v3`, then
executed the exact pin-remediated Stage 3 final gate with fresh output root
`D:\Documents\Project\idx-v4-ca-event-window-final-20260818-v3`.

## Results

- Validation: `21 passed`; py_compile PASS; diff-check PASS.
- Stage 1: `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`; 136 relevant events,
  41 exact transitions, 95 schedule-required events / 75 tickers, and 0/600
  H5/H10/consensus gate dates; minimum rate `0.7588075881`.
- Stage 2: 77 index pages requested, 100 candidate documents, 1 parsed exact
  transition document, 1 exact event link, 94 unresolved links. Official KSEI
  only; no source substitution.
- Stage 3: `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`; 42 exact
  transitions, 94 schedule-required events / 74 tickers, and 0/600
  H5/H10/consensus gate dates; minimum rate `0.7596153846`.
- `corporate_action_continuity_certified=false`.

## Important hashes

- Stage 2 manifest: `5073adb3178a90e71ea9105ddb6ff737896e86a709d1998eefbdb14ca12b6f8c`.
- Stage 2 schedule evidence: `c9f396951ae82f2526c6e7943bff2ed359aa488697d3086f1afdb64127e8d3b4`.
- Stage 2 linkage audit: `e0aa6880035e78396c992b443f73389123dc130df61570fdad1de331f37c7006`.
- Stage 3 manifest: `c635ee354c923eebdb586bc4d82a6693d230e1a347df50879dda4c1f5f56bff4`.
- Stage 3 event semantics: `6d750de249396667775a4b9da55a7d7458b65a845427cd2bbfa9dd5fe66765ff`.
- Stage 3 per-date: `96a77f22691c1cd736c5e21ce40ac3d67501a4494cb140e1f8c46aa606672558`.

## Safety confirmation

No source/configuration or frozen semantics were changed. No V4 target/rank
materialization, model fit, prediction, performance metric, protected outcome,
fresh-forward access, or provider substitution occurred. Large ledgers and raw
HTML/PDF/request records remain external; only small result artifacts were
promoted under `docs/artifacts/`.

## Decision / next action

Final gate is blocked and the lane is `REVIEW`. Stop for independent ChatGPT
review; do not start V4 model execution from this handoff.
