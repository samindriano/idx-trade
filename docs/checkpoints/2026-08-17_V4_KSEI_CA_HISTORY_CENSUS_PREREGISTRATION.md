# V4 KSEI Corporate-Action History Census V1 — Preregistration

Date: 2026-08-17 (Asia/Jakarta)
Branch: `data/idx-v4-ksei-ca-history-census-v1`
Scientific code anchor: `57a15599cf96205bc75f3f5e8b593eac0a77c4cd`
Parent blocked gate: `data/idx-v4-corporate-action-continuity-gate-v1@7e03cdf7023590ea5b7881a61b4e0a958f147d25`
Status: `PREREGISTERED_BEFORE_PROVIDER_RUN`

## Why this lane exists

The first V4 CA continuity gate correctly failed closed because existing IDX/KSEI artifacts were bounded candidate evidence, not a market-wide no-event ledger. Of 344,790 frozen horizon rows, 344,740 were unresolved for coverage and only 50 were unresolved because a known candidate event lacked a proven effective date. This lane addresses only the coverage problem; it does not change V4 targets, folds, learner, evaluator, or promotion gates.

## Frozen population

The provider population is not selected from results. It is the exact unique ticker set in the blocked continuity ledger:

- continuity ledger SHA-256: `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`;
- expected unique tickers: `610`;
- frozen validation dates remain `600` / `6 × 100`.

The prior bounded official event evidence is also immutable:

- `event_family_evidence.csv` SHA-256: `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`.

## KSEI coverage contract

For each of the exact 610 tickers, acquire only the official public KSEI registered-security page:

`https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}?setLocale=en-US`

Frozen transport:

- `curl_cffi`;
- Chrome 110 impersonation;
- maximum three attempts per ticker;
- retry backoff 1s then 3s;
- no alternate provider or URL substitution;
- every response body retained append-only outside Git.

Ticker history coverage is certified only when:

1. HTTP response is successful and non-empty;
2. page `Short Code` equals the requested four-character ticker;
3. exactly one static Corporate Action table exists;
4. headers exactly equal `Type of CA / Ratio / Cum Date / Record Date / Distribution Date / Status`;
5. every visible table row parses structurally.

A successfully parsed official table is treated as the issuer-level KSEI CA history ledger. Unknown active CA types are preserved, never silently classified as harmless.

## Frozen continuity remediation policy

No effective date is inferred from Cum/Record/Distribution dates.

Instead, the V4-period rule is deliberately conservative:

- determine the broad period from minimum frozen `entry_date` through maximum frozen `terminal_date`;
- add a fixed `60` calendar-day halo on both sides;
- if a coverage-certified ticker has any **active mechanical or unknown** KSEI CA row in that broad period, quarantine that ticker for **all** frozen H5/H10 rows;
- cancelled CA rows are not treated as executed basis changes;
- cash dividend and proxy voting are not price-basis blockers;
- if prior official candidate evidence exists in-period but the complete KSEI history has no active mechanical/unknown representation, classify a cross-source coverage conflict;
- only a coverage-certified ticker with no active mechanical/unknown event and no cross-source conflict receives `RESOLVED_NO_MECHANICAL_DISCONTINUITY`.

This avoids event-specific effective-date guessing entirely. The policy is frozen before any of the 610 KSEI pages are acquired.

## Gate

Rerun only continuity support on the exact blocked ledger.

For every frozen date:

- H5 resolved coverage must be `>= 90%`;
- H10 resolved coverage must be `>= 90%`;
- consensus exact H5∩H10 resolved coverage must be `>= 90%`.

Possible final verdicts:

- `V4_CA_CONTINUITY_CERTIFIED`;
- `V4_CA_CONTINUITY_STILL_BLOCKED`.

If blocked, stop. Do not relax the 90% gate, halo, event mapping, ticker quarantine, or coverage contract based on the result.

If certified, stop for independent ChatGPT review. Certification alone does **not** authorize R5/R10 materialization or model execution.

## Forbidden during this lane

- R5/R10 or target-rank materialization;
- model fit or predictions;
- IC, Top30, spread, raw-return or bootstrap performance;
- protected/fresh-forward outcomes;
- V4 target/evaluator/preregistration changes;
- alternate provider fallback;
- post-response parser/policy tuning in the same run.

## Prepared implementation

- `config/v4_ksei_ca_history_census_v1.json`
- `src/idx_trade/v4_ksei_ca_history.py`
- `src/idx_trade/v4_ca_continuity_remediation.py`
- `scripts/run_v4_ksei_ca_history_census.py`
- `scripts/run_v4_ca_continuity_gate_v2.py`
- `tests/test_v4_ksei_ca_history.py`

Provider/runtime execution remains intentionally pending.
