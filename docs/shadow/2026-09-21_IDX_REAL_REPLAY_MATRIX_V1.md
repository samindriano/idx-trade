# IDX-Trade Real Historical Replay Matrix V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **INPUT CORPUS FOUND / REPLAY NOT RUN**

## Inventory-level matrix

| Input family | Real inventory | Candidate replay | Result |
|---|---|---|---|
| Retained session manifests | 29 session dates, 2026-08-03 through 2026-09-18 | copied to full discovery root | available for compatibility review; replay blocked by calendar lineage |
| Model-input snapshots | present in session corpus | not attempted | not paper state |
| Session OHLCV/evidence | present in session corpus | not attempted | not paper state |
| Prepared execution artifacts | not located | impossible | BLOCKED |
| Paper state/fill vectors | not located | impossible | BLOCKED |
| Real CA composition | not admitted | impossible | BLOCKED |
| Protected outcomes | excluded | prohibited | BLOCKED BY POLICY |
| Input-level EOD validator | copied OHLCV/model input/current calendar | all 29 sessions | 27 `PASS_INPUT_LEVEL`; 2026-08-03 not official in copied calendar; 2026-09-18 has no next official session |
| Schedule-bound validator | copied schedule attestation | not run against phase entrypoint | available but phase path remains blocked |
| Score manifest/artifact | copied for 2026-09-17 | PASS via explicit shadow adapter | full replay still BLOCKED by missing state/CA and source path provenance |
| All V4-X1 score manifests | 16 real manifests; 15 clean candidate-id, 1 legacy id | 15 PASS, 1 fail-closed rejection via shadow adapters | score-level validation only; full replay still BLOCKED |
| Legacy input shape/ambiguity hunt | copied 2026-09-16 and 2026-09-17 | PASS WITH LIMITATION | no duplicate required keys, required-field nulls, invalid dates, model/OHLCV ticker differences, or model/OHLCV close differences; wider evidence/stock universe remains an interface boundary |
| Extended CA event registry | 38 IDX event rows / 35 tickers; 18 certified-window rows | not attempted as state replay | source event evidence only; no holdings, entitlement, payment, receivable, or restart ledger |
| Extended execution-anchor corpus | 479,471 anchor rows across 504 session reports | not attempted as paper replay | source input evidence only; no transaction/fill vector or paper-state snapshot |
| Extended historical calendars | 516 available / 504 target sessions | not substituted | none of the admitted candidate calendar hashes matched the 23 embedded session hashes |
| Extended Official Open archive | one run metadata file plus eight logs | not attempted | operational capture evidence only; no execution-grade paper state |
| Real CA parser boundary | copied canonical `idx_actions.csv` | isolated candidate parser after NaN remediation | 38/38 rows parsed; 22 ratios present and 16 unknown; this is event-shape validation, not CA/state replay |

## Selected real manifests

Both selected manifests are `DATA_READY`, outcome-blind, and explicitly report
no forward-outcome access. The 2026-09-16 manifest has 963 listed tickers and
828 model rows. The 2026-09-17 manifest has 963 listed tickers and 831 model
rows. Their hashes and child-artifact hashes are recorded in the master
dossier and immutable-manifest candidate.

## Why replay was not claimed

The isolated copy verification found a calendar lineage mismatch in both
session manifests: the embedded calendar hash does not match the current
file at the manifest-referenced path, and no matching calendar CSV was found
under the approved root. These sessions are therefore NOT_REPLAYABLE until
the exact historical calendar artifact is separately admitted.

The available session corpus does not itself define the E2E paper state,
prepared parent, execution identity, CA authority, or recovery chain. Running
the candidate by projecting these inputs into invented state would violate the
fail-closed boundary. No replay entrypoint was invoked in this lane.

The read-only input validator passed for both selected sessions using the
copied model-input ticker set as the required-ticker set: 828 tickers for
2026-09-16 and 831 for 2026-09-17. This proves only OHLCV/model/calendar
structural compatibility. It does not prove score, sizing, CA, paper-state,
prepared, execution, or historical economic equivalence. It also used the
current copied calendar, whose embedded manifest hash is inconsistent, so it
cannot clear the calendar-lineage blocker.

The real score manifest and artifact were copied with equal hashes, but the
manifest points to the original absolute artifact path. The source manifest
was not rewritten. A derived shadow adapter rebound only that path to the
hash-identical copy; the candidate score validator then passed 296 rows after
the timezone-aware freeze-boundary fix. The adapter is not a production
manifest and does not establish paper-state or economic replay.

The separate copy-only legacy ambiguity hunt found the selected model-input and
OHLCV files aligned by ticker and close value, with no duplicate required keys,
required-field nulls, or invalid session dates. Evidence and stock summaries
retain 135 extra rows on 2026-09-16 and 132 on 2026-09-17 relative to the
model universe. That is a wider-universe scope boundary, not proof of paper
state or a duplicate version. Full details are in
`2026-09-21_IDX_REAL_LEGACY_AMBIGUITY_HUNT_V1.md`.

The final replay disposition is BLOCKED / INPUT-LEVEL PASS ONLY, not a full
historical E2E replay.

The expanded calendar search hashed 128 approved-root CSVs and recovered only
the current calendar hash; none of the 22 distinct historical embedded hashes
was found. The one matching 2026-09-18 session still has no next official
session in that current calendar. Calendar lineage therefore remains a hard
replay gate.

`HISTORICAL_REPLAY = BLOCKED / NOT RUN`.
