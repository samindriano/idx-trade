# 504-session repair checkpoint - STOP

Date: 2026-08-09

Source branch: `data/idx-data-002c`

Source commit: `5e6f6bd38a5af3ee11bca93a15f50fadf9515eb2`

## Scope and guardrails

This was a targeted repair of the three blockers from the failed 504-session
checkpoint. The certified 43- and 126-session artifacts were preserved. No
252-session diagnostic, 1260-session expansion, modelling, `IDX-VAL-002`, or
merge to `main` was started.

## Validation

- Full pytest: **PASS**, 141 tests, exit 0.
- Warnings: three non-blocking pandas `FutureWarning` messages.
- The 504 window remained `2024-06-21` through `2026-07-31`.

## FREN identity repair

The normal IDX/KSEI reconciliation was allowed to fail first. The KSEI
response for FREN was an undefined security/type/listing record. The curated
registry was then loaded with `load_curated_security_identities(...)` and
applied with `supplement_historical_security_identities(...)`.

The rebuilt PIT security master contains:

- security type: common share (`Saham Biasa`);
- `listed_from`: `2006-11-29`;
- `listed_to`: `2025-04-16`;
- 2025-04-16: `LISTED`;
- 2025-04-17: `DELISTED`.

The curated identity was not used to invent ACTIVE tradability. The
supplement and boundary evidence are preserved in:

`D:\Documents\Project\idx-trade-data-gate-20260808v\repair_504\listings\`

## Exact price repair attempt

The preserved failed gate was used to derive, rather than estimate, the exact
missing ACTIVE dates:

| ticker | missing ACTIVE sessions before repair |
|---|---:|
| MASA | 22 |
| MFIN | 249 |
| total | 271 |

The date-level evidence is:

`D:\Documents\Project\idx-trade-data-gate-20260808v\repair_504\prices\missing_active_sessions_504_pre_repair.csv`

The official IDX Stock Summary fallback was invoked only for MASA and only for
its exact 22 dates before the hard stop. It accepted only positive official
Regular-Market Volume/Frequency, required positive valid High/Low/Close, used
positive `OpenPrice` preferentially, and allowed positive `FirstTrade` only as
the documented fallback.

MASA result:

- requested: 22;
- `PRICE_PARSED`: 0;
- `FIRSTTRADE_FALLBACK`: 0;
- unresolved official price rows: 22;
- filled rows: 0;
- remaining missing ACTIVE rows: 22;
- diagnostic for every row: `UNRESOLVED_PRICE /
  OFFICIAL_OHLC_MISSING_OR_NONPOSITIVE`.

The official rows had positive Regular-Market Volume/Frequency and valid
High/Low/Close, but both `OpenPrice` and `FirstTrade` were non-positive. No
synthetic or forward-filled price was created. MFIN was not fetched after this
hard stop. The per-run diagnostics are preserved under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\repair_504\prices\`

After adding FREN's authoritative identity, FREN has 196 ACTIVE sessions in
the 504 window and no raw price artifact. Automatic raw-price semantics are
false for FREN, MASA, and MFIN. This newly exposed consequence is retained as
an unresolved diagnostic rather than hidden.

## Ladder decision

The hard stop in the price fallback contract was reached before the
126/504 `run_history_certification_ladder(...)` call. Consequently there is no
new post-repair PASS/FAIL ladder result, no new 504 model-safe panel, and no
new 504 certified manifest. The previous 504 failure artifacts remain
preserved under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\history_ladder_pre_repair\`

The 504 certification remains **NO-GO / STOP**. Do not weaken the price gate;
do not start 252 or 1260 until a separately reviewed official OHLC source path
resolves the exact missing opening executions.
