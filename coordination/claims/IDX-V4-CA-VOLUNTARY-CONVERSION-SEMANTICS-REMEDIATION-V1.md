# Claim — V4 CA Voluntary-Conversion Semantics Remediation V1

Branch: `data/idx-v4-ca-voluntary-conversion-semantics-remediation-v1`
Scientific parent/result: `data/idx-v4-ca-event-window-semantics-v1@96a652b311f868babab94ca24b32bf1df382627c`
Owner: `ChatGPT/V4-CA-Voluntary-Conversion-Remediation`
Status: `ACTIVE_PREPARATION`

## Scope

Outcome-blind, offline-only semantic remediation of KSEI source-native `Voluntary Conversion` rows for the V4 corporate-action price-basis continuity gate.

The parent Stage-3 result remains immutable. This lane does not reinterpret or overwrite it.

### Allowed

- classify an active KSEI `Voluntary Conversion` row as non-blocking only when the source-native ratio is structurally parsed as exact requested security -> recognized currency;
- keep all other voluntary-conversion rows fail-closed through the prior schedule-required path;
- rerun the same frozen 610-ticker / 600-date continuity support gate offline using the immutable KSEI census and prior continuity ledger;
- produce a fresh remediation result root and small provenance/audit artifacts.

### Forbidden

- R5/R10, target ranks, predictions, model fit, IC, Top30/spread, bootstrap, performance, protected/fresh-forward outcomes;
- provider calls or schedule redownloads in the first remediation run;
- changing the V4 90% continuity gate, frozen universe/dates, target/execution contract, or event-window crossing rule;
- treating Record Date or Distribution Date as a generic price-basis transition;
- classifying an unparsed, security->security, unknown-currency, or identity-mismatched voluntary conversion as harmless.

## Evidence basis frozen before remediation run

Official KSEI states that Mandatory Corporate Action does not require Account Holder instruction and includes Mandatory Conversion for merger/acquisition and stock split/reverse split, while Voluntary Corporate Action requires investor instruction/response.

Observed official KSEI registered-security rows further distinguish:

- `PADA`: Voluntary Conversion `(1 PADA : 63 IDR)`;
- `KETR`: Voluntary Conversion `(1 KETR : 523 IDR)` and `(1 KETR : 240 IDR)`;
- `EDGE`: Voluntary Conversion `(1 EDGE : 11500 IDR)` versus Mandatory Conversion `(1 EDGE : 5 EDGE)`;
- `MFIN`: Voluntary Conversion `(1 MFIN : 3426 IDR)` versus Mandatory Conversion `(1 MFIN : .052401 ADMF)`.

Official source references:

- `https://web.ksei.co.id/services/types/corporate-action`
- `https://web.ksei.co.id/services/registered-securities/shares/lc/PADA?setLocale=id-ID`
- `https://web.ksei.co.id/services/registered-securities/shares/lc/KETR?setLocale=id-ID`
- `https://web.ksei.co.id/services/registered-securities/shares/lc/EDGE`
- `https://web.ksei.co.id/services/registered-securities/shares/lc/MFIN`

## Coordination note

Canonical `main:coordination/TEAM_STATUS.md` must be updated to this lane before any local remediation run. This branch-local claim does not replace that canonical ownership step.
