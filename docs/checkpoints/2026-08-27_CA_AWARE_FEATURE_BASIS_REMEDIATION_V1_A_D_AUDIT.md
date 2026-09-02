# INC-001 CA-Aware Feature-Basis Remediation V1 — A-D Audit

Date: 2026-08-27 Asia/Jakarta  
Branch: `data/ca-aware-feature-basis-remediation-v1`  
Controlling incident: `INC-001 — Historical CA / backward feature price-basis integrity`

## Verdict

The exact final-fit identity reconciliation passed, but the historical
application gate remains fail-closed:

```text
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
MODEL_PROMOTION = NOT_EVALUATED
MODEL_REFIT = NOT_AUTHORIZED
PHASE_E_HISTORICAL_APPLICATION = NOT_RUN
```

The blockers are not repaired by this lane: the final-fit population is not
the frozen KSEI population, KSEI is a post-hoc issuer snapshot without the
required per-session as-of/no-event attestation, and the required structural
event family/transition evidence is partial and contradictory.

## Immutable inputs

The runner `scripts/run_ca_aware_feature_basis_reconciliation_v1.py` consumes
only the following local artifacts and refuses hash drift:

| Input | Path | SHA-256 |
|---|---|---|
| Accepted Phase-A manifest | `D:\Documents\Project\idx-v4-x1-clean-phase-a-open-lineage-remediation-20260820-v1\MANIFEST.json` | `f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda` |
| H5 final-fit identities | `...\clean_h5_support_identities.csv` | `c4768bf09956ec0599df2bcefe4aa26fba3608178110dc2a6d64f9f68e8b0049` |
| H10 final-fit identities | `...\clean_h10_support_identities.csv` | `b537d2ebea9610431522199e6221abe6b13cd96a6b1d487ad761ae4ba46a191b` |
| Accepted Phase-B manifest | `D:\Documents\Project\idx-v4-x1-clean-phase-b-final-refit-20260820-v1\MANIFEST.json` | `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf` |
| KSEI 610 census manifest | `D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1\MANIFEST.json` | `7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25a` |
| KSEI ticker coverage | `...\ticker_coverage.csv` | `bb5414125862411e5d3ee760f8e7415b8418803c71d1cc1ef26fb0c55397bc70` |
| KSEI history | `...\ksei_ca_history.jsonl` | `3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d` |
| KSEI request records | `...\request_records.jsonl` | `e68d60103cc3efc04299c1b330c4ef39e55ba1e44bbcf79f178b2f1ccff812e5` |
| Prior strict CA census | `D:\Documents\Project\idx-ca-feature-basis-integrity-audit-20260826-v4\ca_event_census.csv` | `10540f8f73e6a0cec3975ac189dc2ab2034a81c6610f81381009966848f95ed3` |

The Phase-B manifest binds its H5/H10 identity hashes to the Phase-A files.
The Phase-A acceptance document referenced by the Phase-B manifest is retained
by its historical Git ref/blob but is not present in this branch; the exact
identity files and Phase-B hash binding remain independently verifiable.

## A — Exact final-fit population

| Identity | Rows | Unique tickers | Date interval |
|---|---:|---:|---|
| H5 | 239,648 | 629 | 2022-02-11 — 2026-07-17 |
| H10 | 237,976 | 629 | 2022-02-11 — 2026-07-17 |
| H5 ∪ H10, deduplicated | 240,344 | 629 | 2022-02-11 — 2026-07-17 |

H5/H10 share 237,280 exact `(ticker,date)` identities. Both identity files
were unique-key validated; no model binaries or numeric targets were loaded.

The KSEI census has 610 tickers, of which 567 are mechanically coverage
certified and 43 are unresolved. The exact-fit union overlaps 562 KSEI
tickers, leaves 67 fit tickers outside the KSEI population, and has 99 fit
tickers that are either KSEI-unresolved or absent. There are 48 KSEI tickers
not in the final-fit union. Only 530 of the 629 fit tickers are KSEI
`COVERAGE_CERTIFIED`.

This is a population mismatch, not permission to substitute the 610-ticker
census for the 629-ticker fit population.

## B — Temporal/as-of coverage

The support identity interval is exact, but it is not CA-source coverage.
KSEI request records show a snapshot retrieval interval of
`2026-08-17T16:28:38.283516Z` through `2026-08-17T17:57:30.274512Z`.

The pinned KSEI `ticker_coverage.csv` does not contain
`coverage_start_session`, `coverage_end_session`, or
`coverage_observed_at`. It therefore cannot prove per-ticker historical
no-event coverage or an as-of boundary for the full feature observation
interval. Its event-date extrema (`2001-04-10` through `2026-09-15`) are
source-specific fields, include future scheduled dates, and are not promoted
to market transition sessions.

The frozen feature dependency geometry was recorded without recomputation:

| Dependency | Exact observed-row geometry | Direct exposure after warmup |
|---|---|---:|
| `close_return_5` | `t-5..t` | 5 |
| `ATR14` / `atr14_over_close` | `t-14..t` | 14 |
| `close_return_20` | `t-20..t` | 20 |
| rolling-20 price features | `t-19..t` | 20 |
| rolling-60 price features | `t-59..t` | 59 |

The KSEI snapshot cannot certify these dependency windows as present and
known at the relevant historical sessions. The temporal verdict is
`UNKNOWN_NO_KSEI_PER_SESSION_AS_OF_ATTESTATION`.

## C — Structural CA family matrix

The strict frozen census contains 26 positive rows: STOCK_SPLIT 7,
STOCK_DIVIDEND 3, BONUS_SHARES 1, RIGHTS_HMETD 10,
MANDATORY_CONVERSION 4, and CAPITAL_RESTRUCTURING 1. All 26 remain
`PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE`.

| Family | Positive evidence | No-event coverage | Transition semantics | Verdict |
|---|---:|---|---|---|
| `STOCK_SPLIT` | 7 IDX rows | UNKNOWN | `TanggalPencatatan` is not generic effective date | UNKNOWN |
| `REVERSE_SPLIT` | 0 observed rows | UNKNOWN | absence is not proof | UNKNOWN |
| `RIGHTS_HMETD` | 10 IDX/KSEI rows | UNKNOWN | rights terms/date not promoted | UNKNOWN |
| `STOCK_DIVIDEND` | 3 KSEI rows | UNKNOWN | source event date not market transition | UNKNOWN |
| `BONUS_SHARES` | 1 IDX row | UNKNOWN | source date not market transition | UNKNOWN |
| `MANDATORY_CONVERSION` | 4 KSEI-labelled rows | UNKNOWN | voluntary/mandatory taxonomy conflict | FAIL / UNKNOWN |
| `VOLUNTARY_CONVERSION` | 0 strict rows; KSEI source-labelled rows exist | UNKNOWN | historical voluntary rows mapped to mandatory | FAIL / UNKNOWN |
| `CAPITAL_RESTRUCTURING` | 1 strict row | UNKNOWN | `CAPITAL_RESTRUCTURING` vs `CAPITAL_REDUCTION` conflict | FAIL / UNKNOWN |
| `MERGER` | 0 strict rows; prior IDX `gabungUsaha` pool exists | UNKNOWN | no distinct certified merger contract | UNKNOWN |

The current implementation requires all eight structural families and rejects
partial global coverage. KSEI evidence is source/family scoped; it cannot be
promoted directly to global coverage. Cash dividend remains a separate
non-blocking price-return policy and is not evidence for structural no-event
coverage.

## D — In-scope event classification

Five strict-census rows fall simultaneously inside the exact 629-ticker fit
population and the `2022-02-11` — `2026-07-17` support interval (ISAT split
rows, RAJA split, and SINI conversion/rights evidence). All five are retained
as `UNRESOLVED`; no source date is shifted to the nearest official session and
no generic split/conversion/rights formula is applied. The remaining strict
census rows are retained with explicit outside-scope flags in the event ledger.

All 629 exact-fit tickers remain `UNRESOLVED` for model-row CA admission,
because global no-event coverage and family-specific transition semantics are
not certified. This is conservative even for the 562 tickers present in KSEI.

BBCA remains absent from exact H5/H10 fit identities (`0` exact-fit rows in
the accepted audit); its prior H/L/C trace is not reinterpreted as Open-basis
certification.

## Phase E decision

Phase E was **not run**. No historical price panel, direct feature, rank,
market-context, target, outcome, model, or counter artifact was recomputed or
overwritten. The audit does not claim a new exact-fit feature impact number;
the prior accepted impact artifacts remain historical evidence only.

## Audit artifacts

External immutable output root:
`D:\Documents\Project\idx-ca-aware-feature-basis-remediation-20260827-v1`

| Artifact | SHA-256 |
|---|---|
| `MANIFEST.json` | `a4f8e97cd6d8548a83810e2dfc7fe66a335948eed2a8f2731f6e5aa4832744a4` |
| `summary.json` | `34d54c4c62218fed87e5f815743032dfc32953591af219e3f9ee794b5b0172c8` |
| `population_reconciliation.csv` | `3fad40646a04cbf3173d46bfe82537f027b594a20c3c29f4d41e7c0162f124db` |
| `structural_ca_event_ledger.csv` | `426f82fdbe4d8cbcc2a6c00bef2676a758c7c48fb22463f80c9b986bcc42e0f5` |
| `ca_family_coverage.csv` | `b0f2e0f18ab146526f78c25baff61eb9e6a79d56af01143812ba03ff655574d8` |
| `temporal_coverage.csv` | `d376b7e8fef3ff942e6018eb20775d990038faa79bfadc040bb32e7e6f40fb58` |
| `model_population_classification.csv` | `6203ad936c2630cc7c84bd8a824a2ca31d7f4f31de45995f9bfb6ecbe82ce1d6` |

The same runner was executed into a separate fresh root for determinism; all
six output hashes matched (`0` mismatches). Existing source artifacts were not
modified.

## Guardrails and validation

```text
outcome_blind = true
target_values_accessed = false
outcomes_accessed = false
provider_calls = false
model_fit = false
model_scoring = false
historical_feature_recompute = false
phase_e_run = false
counter_mutated = false
canonical_artifacts_mutated = false
```

Focused CA/integrity suite: **84 passed, 0 failed**.  
`py_compile` for the runner and CA primitives: **PASS**.  
`git diff --check`: **PASS**.

The result is ready for independent ChatGPT review; no merge or scientific
promotion is authorized by this checkpoint.
