# IDX-Trade Real Legacy Ambiguity Hunt V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **COPY-ONLY STRUCTURAL CHECK COMPLETE / REPLAY STILL BLOCKED**

## Scope and boundary

This check used only the immutable copies under
`C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921`.
It did not read the provider checkout, protected outcomes, counters, cloud/R2,
or any live writable runtime. It did not rewrite a source artifact and did not
run a replay or production entrypoint.

The purpose was to distinguish ordinary legacy-universe shape from an actual
duplicate/state ambiguity before deciding whether the selected real sessions
could be used in a bounded shadow validation.

## Selected copied sessions

| Session | Model-input rows | OHLCV rows | Evidence rows | Stock-summary rows | Index-summary rows |
|---|---:|---:|---:|---:|---:|
| 2026-09-16 | 828 | 828 | 963 | 963 | 45 |
| 2026-09-17 | 831 | 831 | 963 | 963 | 45 |

The copied calendar has 28 data rows. Its current hash is already recorded in
the V2 immutable-input manifest; both selected session manifests embed a
different historical `calendar_sha256`. That lineage mismatch remains a
separate blocker and is not resolved by this structural check.

## Checks and results

| Check | 2026-09-16 | 2026-09-17 | Interpretation |
|---|---|---|---|
| Duplicate required keys | none | none | no duplicate-key ambiguity found |
| Nulls in required fields | none | none | no null-driven ambiguity found |
| Invalid/non-session dates in required date fields | none | none | dates are structurally admissible |
| Model-input vs OHLCV ticker set | exact | exact | model input has a matching OHLCV row for every model ticker |
| Model-input vs OHLCV close values | exact | exact | no copied close-value mismatch was found |
| Model-input vs evidence ticker set | difference | difference | evidence contains the wider listed universe |
| Model-input vs stock-summary ticker set | difference | difference | stock summary contains the wider listed universe |

The wider evidence/stock-summary sets contain 135 extra tickers on
2026-09-16 and 132 extra tickers on 2026-09-17 relative to the model-input
set. The difference is consistent with inactive/non-model universe rows in the
retained session package; it is not, by itself, evidence of duplicate rows,
multiple state versions, or a hidden paper portfolio. The candidate must still
keep the model-input/score universe boundary explicit if a future replay is
authorized.

## What this does and does not establish

Established in the isolated copy:

- the selected model-input and OHLCV files are structurally aligned at the
  ticker and close-value level;
- no duplicate required keys, required-field nulls, or invalid session dates
  were found in the checked files;
- the extra evidence/stock rows are a universe-scope distinction requiring
  interface discipline, not a discovered paper-state artifact.

Not established:

- the exact historical calendar bytes referenced by either session manifest;
- a paper portfolio, fill vector, prepared execution, pending ledger, or CA
  ledger;
- old-vs-candidate equivalence, recovery continuity, or economic replay;
- permission to read provider/outcome data or mutate the active runtime.

## Disposition

`LEGACY_INPUT_SHAPE = PASS WITH LIMITATION`.

This hunt removes a possible copied-input duplicate/universe ambiguity, but it
does not close the calendar-lineage, paper-state, CA, recovery, identity, or
operational gates. The overall historical replay verdict remains
`BLOCKED / INPUT-LEVEL VALIDATION ONLY` and the pre-canary verdict remains
`NO-GO`.
