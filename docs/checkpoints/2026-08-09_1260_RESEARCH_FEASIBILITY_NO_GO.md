# 1260-session research-feasibility evaluation - NO-GO / STOP

Date: 2026-08-09 (Asia/Jakarta)

Branch: `data/idx-data-002c`

Scope: exact trailing 1260-session feasibility evaluation ending 2026-07-31.
The certified 43- and 126-session artifacts were preserved unchanged. No model,
`IDX-VAL-002`, main merge, or further 252 expansion was started.

## Decision

**NO-GO / STOP.** The strict 126 regression passes, but strict 504 remains
uncertified and the full 1260 gate fails. A generic research exclusion layer
would leave only 917/979 required common stocks (93.667%), below the 98%
ticker-coverage threshold. Official OHLC gaps also remain after the approved
public-source paths were exhausted. No model-safe 1260 panel or manifest was
created.

## Exact window and preserved evidence

- official window: `2021-04-29 -> 2026-07-31`, exactly 1260 sessions;
- official calendar sources: IDX Daily Statistics publication listing and IDX
  Digital Statistics daily trading table;
- session SHA-256:
  `5dae391a1b4068a71b0f0dd40edda207356a917f74dc860c50e4080fa7bd268f`;
- 504 suffix: `2024-06-21 -> 2026-07-31`, exactly the trailing 504 sessions;
- runtime root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809`.

The full pytest run passed: **157 passed, 0 failed**, with three existing
non-blocking pandas `FutureWarning` messages.

Official Stock Summary evidence was complete for all 1260 sessions:

- 982,398 ACTIVE regular-market anchors;
- 121,666 NO_TRADE anchors;
- 1,104,064 merged point-evidence rows;
- zero unresolved metrics.

The canonical PIT identity/scope result was 980 discovered tickers before
scope, CNTX excluded by the preserved authoritative KSEI `Saham Preference`
record, 979 required common stocks, and zero unresolved required identities.
FINN was reconciled from the official IDX delisting source. FREN's repaired
identity interval was preserved as common share, `2006-11-29 -> 2025-04-16`.

The complete official corporate-action query returned 55 `stockSplit` rows for
52 tickers and zero `reverseStock` rows. A complete authoritative no-event
query is verified; dividend evidence remains informational and is not used for
technical OHLC construction.

## Price evidence and fallback

The additional Yahoo backfill requested 897 tickers: 878 `UPDATED`, 19
`NO_PROVIDER_ROWS`, zero `DOWNLOAD_ERROR`, and zero `REVISION_CONFLICT`.

The targeted official IDX Stock Summary fallback requested 6,794 exact missing
ACTIVE ticker/date pairs over 989 distinct dates. Results:

- `PRICE_PARSED`: 78 rows, all WSKT;
- `FIRSTTRADE_FALLBACK`: 0 rows;
- unresolved official price rows: 6,716;
- rows filled: 78;
- no existing Yahoo/provider rows overwritten;
- no synthetic or forward-filled OHLC.

The fallback diagnostics are preserved at:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\strict_gate_1260\idx_price_fallback\`

## Strict layer results

| horizon | exact window | discovered before scope | scope exclusion | required common stocks | passed | failed | UNKNOWN sessions | missing ACTIVE prices | quarantined bars | blocker histogram |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| 126 | 2026-01-15 -> 2026-07-31 | 964 | CNTX | 963 | 963 | 0 | 0 | 0 | 2,672 | `{}` |
| 504 | 2024-06-21 -> 2026-07-31 | 977 | CNTX | 976 | 973 | 3 | 2 | 390 | 22,400 | `SESSION_COVERAGE_INCOMPLETE:3; PRICE_SEMANTICS_UNVERIFIED:2` |
| 1260 | 2021-04-29 -> 2026-07-31 | 980 | CNTX | 979 | 917 | 62 | 572 | 6,716 | 57,808 | `SESSION_COVERAGE_INCOMPLETE:62; PRICE_SEMANTICS_UNVERIFIED:15` |

Strict 504 failed tickers: `FREN`, `MASA`, `MFIN`.

Exact strict 1260 failed tickers:

`ADCP, AGAR, AGRS, AMIN, AYLS, BATA, BAYU, BBHI, BISI, BRMS, BRNA, BSIM,
BTON, BTPN, BUAH, BUKK, CBMF, CLAY, CPRI, DMND, DUCK, EDGE, FINN, FREN,
FUJI, GAMA, GEMA, GOLD, GRPH, HKMU, HOTL, IBST, INAF, INAI, INCI, INPC,
INPP, ISSP, JECC, JIHD, JSKY, JSPT, KETR, KRYA, LCKM, LFLO, LMAS, MAGP,
MASA, MFIN, PGJO, PTSP, PURE, RMBA, ROCK, SAFE, SRIL, TECH, TRST, TURI,
UNSP, WSKT`.

The canonical full gate output is:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\strict_gate_1260_post_fallback\full_universe_gate_summary.json`

## Research-feasibility layer

The registry uses `RESEARCH_UNSUPPORTED_SECURITY` only after normal IDX/KSEI
identity and tradability reconciliation plus Yahoo and official Stock Summary
price evidence were exhausted. It does not invent ACTIVE/NO_TRADE state and it
does not relax the strict gate.

- unsupported registry rows: 62;
- eligible common-stock tickers: 917;
- ticker coverage: 93.667% (threshold: >=98%);
- active-row coverage before exclusions: 99.316%;
- active-row coverage after exclusions: 100%;
- known excluded regular-market value share: 2.373%;
- excluded names in top 50 / 100 / 200 by known regular value: 1 / 2 / 4;
- excluded delisted count: 6;
- excluded suspension-interval count: 1;
- excluded corporate-action count: 3;
- sector bias: `NOT_COMPUTABLE_FROM_CURRENT_SECURITY_MASTER`.

The registry reason counts are:

- `PUBLIC_TRADABILITY_EVIDENCE_UNRESOLVED`: 3;
- `PUBLIC_PRICE_EVIDENCE_UNRESOLVED`: 42;
- price evidence plus `PRICE_SEMANTICS_UNVERIFIED`: 12;
- tradability evidence plus `PRICE_SEMANTICS_UNVERIFIED`: 1;
- both evidence classes plus `PRICE_SEMANTICS_UNVERIFIED`: 3;
- both evidence classes without the semantics blocker: 1.

The exact registry is external at:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\research_unsupported_registry_1260.csv`

The materiality and decision report is:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\research_feasibility_report.json`

The largest unresolved price gaps are historical; missing-row year counts are
2021: 2,316, 2022: 2,541, 2023: 1,172, 2024: 544, and 2025: 143. No approved
source supplied a defensible replacement for those missing OHLC rows.

## Stop condition

Stop at this checkpoint. Do not materialize a 1260 panel or manifest, start 252
or another expansion, model, run `IDX-VAL-002`, merge to `main`, or turn the
generic research exclusions into an unreported universe change. The next safe
step requires separately reviewed additional historical opening/OHLC evidence
or an explicit revision of the research contract.
