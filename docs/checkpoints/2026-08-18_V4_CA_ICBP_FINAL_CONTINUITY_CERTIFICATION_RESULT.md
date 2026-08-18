# V4 CA — ICBP Single-Ticker Final Continuity Certification Result

Date: 2026-08-18
Branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`
Runtime root: `D:\Documents\Project\idx-v4-ca-icbp-single-ticker-continuity-20260818-v1`

## Decision

`V4_CA_EVENT_WINDOW_CONTINUITY_CERTIFIED`

`corporate_action_continuity_certified=true`

This is a **panel-level continuity certification under the frozen 90% per-date gate**. It is not a claim that every ticker or every corporate-action event has exact transition evidence.

## ICBP bounded remediation

The exact official KSEI registered-security page for ICBP was retried using the previously frozen transport and strict parser.

Result:

- target ticker: `ICBP` only;
- source substitution: `false`;
- parser relaxation: `false`;
- alternate provider: `false`;
- full 610-ticker recrawl: `false`;
- security attempts: `1`;
- total request records in delta: `2` (home warmup + one security request);
- KSEI source SHA-256: `d2f9f58ba7b5536fd9b5e409cc35ee8a30f2a8fed552b6deb528d52ef0ed2f4c`;
- coverage certified tickers: `599 / 610`;
- remaining unresolved tickers: `11` — AMAN, AVIA, AYAM, BCIP, PRIM, SKRN, SLIS, SMAR, SNLK, SOCI, SOFA.

ICBP parsed history contains 34 CA rows, including one active mechanical `Mandatory Conversion`. That event is dated 2016-07-26 / 2016-07-29 / 2016-08-01 with ratio `(1 ICBP : 2 ICBP)`. It is outside the frozen V4 study period plus 60-calendar-day selection halo, so `icbp_event_semantics=[]` in the replay. No semantic relaxation was required.

ICBP remediation manifest SHA-256:
`8f69b8ffb7819865eb91411e4e13717ef94a9585b4cffd288677af9038d5757e`

## Final continuity replay

Frozen dimensions remained unchanged:

- frozen tickers: `610`;
- frozen signal dates: `600`;
- frozen rows: `344,790`;
- gate rate: `0.90`;
- horizons: H5 and H10;
- selection halo: 60 calendar days;
- missing exact schedule: fail closed;
- price inference: forbidden;
- entry on transition date: post-event basis;
- provider calls during replay: `false`;
- model fit / performance / prediction / target-rank / protected-forward access: all `false`.

Final gate result:

- H5: `600 / 600`, minimum continuity rate `0.9038461538461539`;
- H10: `600 / 600`, minimum continuity rate `0.9006410256410257`;
- consensus: `600 / 600`, minimum continuity rate `0.9006410256410257`.

Continuity status counts:

- `RESOLVED_NO_MECHANICAL_DISCONTINUITY`: `320,601`;
- `PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE`: `17,345`;
- `PRICE_CONTINUITY_UNRESOLVED_COVERAGE`: `6,844`.

Event semantics remain intentionally incomplete at ticker/event level:

- relevant event rows: `82`;
- `EXACT_TRANSITION`: `49`;
- `SCHEDULE_REQUIRED`: `33` across `29` tickers;
- targeted selected-event evidence: `5` exact schedule transitions, `1` exact static non-blocking, `1` unresolved selected event.

## ADRO / AAI-AADI boundary

The unresolved targeted selected event remains ADRO's 2024 AAI/AADI PUPS/spin-off-related event. **ADRO is not excluded from the frozen 610-ticker universe, and its unresolved transition is not reclassified or waived.** Any ADRO target interval affected by an unresolved exact transition continues to fail closed at the row/window level.

The panel nevertheless passes because the frozen scientific contract requires at least 90% certified continuity on every validation date, not 100% issuer/event completion. The final minimum H10/consensus rate is `0.9006410256410257`, above the frozen `0.90` threshold.

Therefore downstream code may consume `corporate_action_continuity_certified=true` only as the **aggregate V4 gate result**. It must not be interpreted as `ADRO_SPINOFF_RESOLVED`, `ALL_CA_EVENTS_RESOLVED`, or `ALL_610_TICKERS_CA_CERTIFIED`.

## Provenance

Key final input hashes:

- base continuity ledger: `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`;
- KSEI coverage: `09d5271f1e3267e2b44177cdb73d638cc94a0c8c99f005f9415fe05c967331d9`;
- KSEI history: `6c8ad906848eafffa9f73e46bd604ca168e6d0bbc96bc58fd183e26b4ca5d204`;
- KSEI remediation manifest: `8f69b8ffb7819865eb91411e4e13717ef94a9585b4cffd288677af9038d5757e`;
- official calendar: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- prior event evidence: `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`;
- merged schedule evidence: `05bfe12a2c81510cda8836c5c1e7efcd47c35ab6a9d120bebf519735c631a992`.

Final output hashes:

- continuity ledger: `b42a1b39341bf402aeb4294f27009bd4ee1d2c0e12ac664247b0b2bc9d23b342`;
- event semantics audit: `09ab5fb39394a9376c814d937423bc4ef62e551086bc73045b9ec026a651502b`;
- per-date result: `0fe224a748df8cc19850e04950f4e590161ce04f4f6beaf49d96b6b686c0fd7d`;
- schedule evidence needs: `da0d18e418ad124e0a439b8f7dfae9e279271632657598e8487d88a65f698ec0`;
- continuity summary: `59be17307b90c2404abd9f7ee033ee9f4a7ba4b1849793bab67de657f9f4273d`;
- ICBP continuity overlay: `ee4a2e59affc7bee46652516acb1dff5cc510408b10dba52552c38de118946a5`.

## Downstream authorization boundary

The CA continuity prerequisite that blocked V4-3 target execution is now satisfied under its frozen aggregate gate. A downstream V4-3 execution lane must independently verify and pin this certified artifact before any target/model execution.

This result does **not** authorize:

- changing the 90% gate;
- treating unresolved ADRO spin-off semantics as resolved;
- silently using unresolved ticker-windows as clean observations;
- modifying CA semantics or adjustment rules;
- accessing protected/fresh-forward outcomes outside the separately authorized V4 execution contract.
