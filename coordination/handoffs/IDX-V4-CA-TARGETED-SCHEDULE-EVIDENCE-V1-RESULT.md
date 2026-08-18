# Result Handoff — IDX-V4-CA-TARGETED-SCHEDULE-EVIDENCE-V1

Status: `REVIEW`
Outcome access: `NONE`
Target/model authorization: `NO`

## Result

The frozen seven-event official-KSEI acquisition and one continuity replay completed without post-result patch or retry.

Acquisition:

- selected events `7`;
- exact static non-blocking `1` (NISP);
- exact schedule transitions `0`;
- unresolved selected mechanical events `6` (ISAT, ADRO, PANI, RAJA, PTRO, CUAN);
- provider request-attempt records `52`;
- index pages `29`;
- candidate documents `7`;
- acquisition manifest SHA-256 `df1455b80c4b5d76d8bde0c23ac992db81fc93373a9a40af18ca29583b94b79b`.

Continuity replay:

- verdict `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`;
- `corporate_action_continuity_certified=false`;
- H5 `515/600`, min `0.8846153846153846`;
- H10 `504/600`, min `0.8821656050955414`;
- consensus `504/600`, min `0.8821656050955414`;
- relevant/exact/schedule-required events `82/44/38`;
- schedule-required tickers `34`;
- unresolved coverage rows `8,044`;
- unresolved effective-date rows `23,252`;
- known mechanical-crossing rows `240` preserved;
- cross-source conflicts remain `MEGA`, `SCMA`;
- continuity summary SHA-256 `46eecaa534854f74e759482a1416dc70c16d6803f2f833210087a39728a65c9d`;
- targeted overlay SHA-256 `0fd567c1f96a41741b9eac22ffc978b9d6549430ce1ac4924a2b29a1e472aedc`.

NISP alone improved gate-date counts from the accepted post-KSEI baseline `462/461/461` to `515/504/504` and reduced schedule-required unresolved rows by exactly `1,200`; this is genuine monotone continuity-support improvement but does not clear the frozen every-date `>=0.90` gate.

## Next allowed action

Offline-only forensic inspection of the already captured candidate-document/linkage/parse evidence for the six unresolved selected mechanical events. Determine whether failure is parser/linkage admission or source-document semantic insufficiency before authorizing any new acquisition lane.

No provider retry, source substitution, parser relaxation after result exposure, target/rank/model/prediction/performance/bootstrap, protected-forward, or fresh-forward access.
