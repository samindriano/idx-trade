# Handoff

from: Codex  
to: MAIN / ChatGPT review  
task_id: IDX-HISTORICAL-E2E-CA-TARGET-ATTACHMENT-AUDIT-V1  
model_used: GPT-5 Codex  
reasoning_level: high  
source_repository: samindriano/idx-trade  
branch: `research/idx-historical-e2e-replay-v1`  

## Scope

Outcome-blind official IDX attachment recovery for the 94 frozen CA schedule
needs. No frozen CA ledger, operational runtime, scheduler, counter, model,
outcome, or TEAM_STATUS file was modified.

## Inputs and external artifacts

- source batch manifest:
  `D:\Documents\Project\idx-historical-e2e-dividend-corpus-batch-20260824-v1`
  SHA `9c89e0e089827a46c51a18ee3d2ddba36861fc02660f677942315d9d367e25bf`;
- target discovery CSV SHA:
  `c140dd08739c2a7ab2a9d9a30e1dc395c064fd85237b8ca7ad88a694e441ffb0`;
- PDF audit root:
  `D:\Documents\Project\idx-historical-e2e-ca-target-attachment-audit-20260824-v2`
  manifest SHA `e8ae75db0bf6f8314c5c7e582a6bc98e5bb903fbfa3ce73f96d3f9685f82db3f`;
- ZIP remediation root:
  `D:\Documents\Project\idx-historical-e2e-ca-target-attachment-zip-remediation-20260824-v2`
  manifest SHA `03d842b17cf9f2dd28cd98e9d4fe88e87737395ab6b1ec82b339b326425e8d83`;
- provider commit:
  `75d6c0f74fa360d225794c70c383348977de6798`.

## Findings

- 94 unique schedule-needs event IDs / 74 tickers;
- 62 event IDs had any nearby issuer announcement;
- 35 event IDs had an action-specific announcement candidate;
- 60 unique candidate announcements / 138 PDF-or-ZIP attachment requests;
- 133 PDFs were HTTP 200 with PDF magic;
- 7 official BEI ZIP notices were separately captured and inspected;
- exact schedule candidates were found for INDS, PTRO, MFIN, INET, BUVA,
  COCO, and bonus-share notices for MEJA/MMIX/RISE.

The evidence is candidate-only. It has not been joined to every frozen event
identity with an accepted effective-date policy, so it cannot be used to
change `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`.

## Boundary and blockers

The current strict scope remains empty because:

1. official Open support is incomplete for BUY intents;
2. 59/94 CA needs lack an action-specific candidate in the bounded corpus and
   all candidates still need ledger reconciliation;
3. market-wide dividend no-event and entitlement evidence is not proven.

No absence was promoted to a no-event fact. No performance or Monte Carlo work
is authorized while the strict 6x100 scope remains empty.

## Validation and recommendation

The source acquisition was outcome-blind and used only official IDX files via
the pinned provider transport. No Zapi, Stockbit, model, label, or protected
outcome access occurred in this remediation.

Recommended next step: MAIN may authorize a separate ledger-reconciliation
lane for the explicit candidate events, with a clear rule for which official
attachment establishes each event transition. Do not alter the frozen ledger
or run replay metrics from this handoff alone.

