# Claim — IDX-V4-CA-VOLUNTARY-CONVERSION-FORENSIC-REPLAY-V1

Status: `ACTIVE`
Owner: `ChatGPT/V4-CA-Voluntary-Conversion-Forensic-Replay`
Branch: `data/idx-v4-ca-voluntary-conversion-forensic-replay-v1`
Scientific parent result: `data/idx-v4-ca-voluntary-conversion-semantics-remediation-v1@5b9afc24b758413f315351971b2cd07f634dc9c9`

## Scope

Offline forensic replay only. Determine whether the prior remediation result's reported `0` voluntary-cash reclassifications is a reporting/filtering artifact and explain the exact `136 -> 102` relevant-event delta.

Authorized work:

- inspect the immutable KSEI census history already captured externally;
- dump exact source-native `Voluntary Conversion` rows and ratio parse fields;
- replay parent and remediation classifiers side-by-side on identical rows;
- compare exact event-id sets from parent Stage-1 and remediation result;
- enforce invariants linking reclassification counts, dropped event IDs, and continuity outputs;
- emit only outcome-blind forensic diagnostics.

Not authorized:

- provider/network calls or re-downloads;
- new CA semantics beyond the already frozen voluntary security-to-currency rule;
- schedule acquisition or Stage 2/3 continuation;
- target/R5/R10/rank materialization;
- model fitting, prediction, performance, or protected/fresh-forward outcome access;
- modification of the immutable parent results.

Canonical TEAM_STATUS must be updated for this lane before the local external-byte replay is executed.