# V4 CA Voluntary-Conversion Semantics Remediation V1 — Result

Status: `REVIEW`

## Scope and frozen identity

This was the single authorized offline remediation run from:

- branch: `data/idx-v4-ca-voluntary-conversion-semantics-remediation-v1`
- execution HEAD: `18b8d78eec4236d749d830c7d679aab5ab514d1e`
- scientific parent result: `data/idx-v4-ca-event-window-semantics-v1@96a652b311f868babab94ca24b32bf1df382627c`
- source/config anchor: `fc6ede265abeae97f6871f7b852e84aa669c159b`

No source, configuration, target, execution, provider, model, or outcome
semantics were changed. The run reused the existing continuity/event evidence,
the official calendar, and the existing KSEI census artifacts.

## Validation

- focused tests: `20 passed in 2.84s`
- `py_compile`: PASS
- `git diff --check`: PASS
- provider calls: `0`
- additional schedule/provider acquisition: `0`

## Offline remediation result

The strict voluntary-conversion rule found no qualifying exact
security-to-currency source rows in the relevant event set:

- relevant event rows: `102`
- exact transitions: `41`
- schedule-required events: `61`
- schedule-required tickers: `51`
- source-native `Voluntary Conversion` rows: `29`
- reclassified as `VOLUNTARY_CASH_SETTLEMENT`: `0`
- remaining `Voluntary Conversion` rows: `29`, all still
  `VOLUNTARY_CONVERSION / SCHEDULE_REQUIRED`

The zero reclassification result is fail-closed: no row satisfied all frozen
requirements for active status, source-text-only parsed ratio, exact left
security identity, and a recognized currency on the right-hand side.

Frozen support census:

- rows: `344,790`
- tickers: `610`
- dates: `600`
- H5 gate dates at `>=90%`: `0/600`
- H10 gate dates at `>=90%`: `0/600`
- consensus gate dates at `>=90%`: `0/600`
- minimum H5/H10/consensus rate: `0.7912087912087912`
- corporate-action continuity certified: `false`
- verdict: `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`

Continuity status counts:

| Status | Rows |
|---|---:|
| `RESOLVED_NO_MECHANICAL_DISCONTINUITY` | 283,267 |
| `PRICE_CONTINUITY_UNRESOLVED_COVERAGE` | 29,084 |
| `PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE` | 32,439 |

Main reason counts:

| Reason | Rows |
|---|---:|
| `NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL` | 283,267 |
| `KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED` | 27,884 |
| `EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED` | 32,238 |
| `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION` | 201 |
| `CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY` | 1,200 |

## Provenance and artifacts

External output root:
`D:\Documents\Project\idx-v4-ca-voluntary-conversion-remediation-20260818-v1`

Input hashes:

- continuity ledger: `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`
- prior event evidence: `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`
- official calendar: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- KSEI history: `3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d`
- KSEI manifest: `7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25a`
- KSEI summary: `a046637fbcff69cbc42c09e4cac30d9181b2ce93a3cf7297a9a01cfc23a2f422`
- KSEI coverage: `bb5414125862411e5d3ee760f8e7415b8418803c71d1cc1ef26fb0c55397bc70`

Promoted small artifact hashes:

- `MANIFEST.json`: `1e3d276ef532c4a0ecaadda5a23d41372e4d26b31289a04e41e3a4133aefc802`
- `summary.json`: `2fdd1792040dd2b793adc53bbeeef38db5da41617e2ad0202aa4f3484ce54804`
- `event_semantics_audit.csv`: `a2fe0206189916a796cda170e819053dd7147bf988ceed27f278081684ca4f1a`
- `schedule_evidence_needs.csv`: `aec30360dad932001d04bbb2fb6a2f772f9cfb1930f5a4336a0f699eb924d4be`
- `v4_frozen_continuity_per_date_event_window.csv`: `55de6a8dc981bc2b16be96e3c02d767c6655b7025c402dbd50aa5d95aa65cbb9`

The full 65 MB continuity ledger remains external. Its output SHA is
`3298c86369de5d6649025ad2d664d9698725ab0b076054155e3f3abfd5bc81d5`.

## Boundary confirmation

This run did not execute Stage 2 or Stage 3 schedule acquisition, did not make
provider calls, and did not materialize R5/R10, targets, ranks, predictions,
performance metrics, or protected/fresh-forward outcomes. No source/config
patch was made after the remediation run.

Next action is independent ChatGPT review; no automatic continuation is
authorized.
