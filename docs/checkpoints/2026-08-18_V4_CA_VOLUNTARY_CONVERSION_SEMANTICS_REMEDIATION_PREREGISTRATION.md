# V4 CA Voluntary-Conversion Semantics Remediation V1 — Preregistration

Status: `PREREGISTERED_BEFORE_OFFLINE_REMEDIATION_RUN`

Branch: `data/idx-v4-ca-voluntary-conversion-semantics-remediation-v1`
Scientific parent/result: `data/idx-v4-ca-event-window-semantics-v1@96a652b311f868babab94ca24b32bf1df382627c`
Scientific code/config anchor: `fc6ede265abeae97f6871f7b852e84aa669c159b`

## Why this is a separate remediation

The parent Stage-3 result remains immutable:

- verdict `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`;
- 42 exact transitions;
- 94 schedule-required events / 74 tickers;
- H5/H10/consensus passing dates `0/600` each;
- minimum continuity rate `0.7596153846`;
- no V4 target/model/performance/outcome access.

Post-result forensic review found a source-semantics defect in the pre-outcome CA gate: source-native KSEI `Voluntary Conversion` was treated generically as a mechanical price-basis event requiring an exact market transition. The older KSEI normalizer also maps `voluntary conversion` to `MANDATORY_CONVERSION`, which is not an admissible semantic basis for this remediation. The immutable history bytes are not rewritten; this lane uses source-native `event_family_source` plus source-parsed ratio fields.

## Official KSEI evidence frozen before the remediation run

KSEI's Corporate Action Services page distinguishes:

- Mandatory Corporate Action: no Account Holder instruction is required. Mandatory Conversion includes merger/acquisition and stock split/reverse split and automatically changes security composition based on an issuer-provided ratio/effective date.
- Voluntary Corporate Action: Account Holder/investor instruction or response is required.

Official registered-security examples show a separate economic pattern:

- PADA: `Voluntary Conversion (1 PADA : 63 IDR)`;
- KETR: `Voluntary Conversion (1 KETR : 523 IDR)` and `(1 KETR : 240 IDR)`;
- EDGE: `Voluntary Conversion (1 EDGE : 11500 IDR)` while its stock split is recorded separately as `Mandatory Conversion (1 EDGE : 5 EDGE)`;
- MFIN: `Voluntary Conversion (1 MFIN : 3426 IDR)` while merger conversion is `Mandatory Conversion (1 MFIN : .052401 ADMF)`.

Source URLs:

- `https://web.ksei.co.id/services/types/corporate-action`
- `https://web.ksei.co.id/services/registered-securities/shares/lc/PADA?setLocale=id-ID`
- `https://web.ksei.co.id/services/registered-securities/shares/lc/KETR?setLocale=id-ID`
- `https://web.ksei.co.id/services/registered-securities/shares/lc/EDGE`
- `https://web.ksei.co.id/services/registered-securities/shares/lc/MFIN`

## Frozen remediation rule

An active source-native `Voluntary Conversion` may be classified `NON_BLOCKING / VOLUNTARY_CASH_SETTLEMENT` only if all conditions hold on the immutable KSEI row:

1. `ratio_parse_status == PARSED_SOURCE_TEXT_ONLY`;
2. ratio left security exactly equals the requested ticker;
3. ratio right security is exactly one of the frozen currency tokens `IDR, USD, SGD, EUR, JPY, AUD, GBP, CNY, HKD`.

Interpretation: the row is a security-to-currency voluntary settlement requiring investor response, not an automatic market-wide price-basis rebase of the listed share.

Everything else delegates unchanged to the parent classifier and remains fail-closed. In particular:

- security -> security voluntary conversions remain schedule-required;
- unparsed ratios remain schedule-required;
- identity mismatches remain schedule-required;
- unknown right-hand tokens remain schedule-required;
- Mandatory Conversion, stock split/reverse split, merger/restructuring, Rights, stock dividend, bonus, and mixed-dividend semantics are unchanged.

## Frozen V4 rules unchanged

- 610 frozen tickers / 600 frozen signal dates;
- continuity gate `>= 0.90` on every H5, H10, and consensus date;
- target interval crossing rule remains `entry_date < transition_date <= terminal_date`;
- Record Date and Distribution Date are not generic price-basis transition fallbacks;
- no synthetic dates or price-jump inference;
- no provider calls in the first remediation run;
- no R5/R10, target ranks, model fitting, prediction, IC, Top30/spread, bootstrap, performance, or protected/fresh-forward outcomes.

## Execution design

The first run is offline only against the exact immutable inputs already used by the parent event-window support census. The new launcher reuses the frozen support runner, applies the already-documented 63->64 character KSEI MANIFEST input-pin correction, swaps only the preregistered voluntary-conversion classifier, and relabels the output policy ID.

Fresh external output root:

`D:\Documents\Project\idx-v4-ca-voluntary-conversion-remediation-20260818-v1`

Regardless of verdict, stop after this offline run for independent review. No schedule/provider continuation is automatically authorized.
