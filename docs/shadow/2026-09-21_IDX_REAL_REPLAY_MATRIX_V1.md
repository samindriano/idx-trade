# IDX-Trade Real Historical Replay Matrix V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **INPUT CORPUS FOUND / REPLAY NOT RUN**

## Inventory-level matrix

| Input family | Real inventory | Candidate replay | Result |
|---|---|---|---|
| Retained session manifests | 29 session dates, 2026-08-03 through 2026-09-18 | not attempted | available for compatibility review |
| Model-input snapshots | present in session corpus | not attempted | not paper state |
| Session OHLCV/evidence | present in session corpus | not attempted | not paper state |
| Prepared execution artifacts | not located | impossible | BLOCKED |
| Paper state/fill vectors | not located | impossible | BLOCKED |
| Real CA composition | not admitted | impossible | BLOCKED |
| Protected outcomes | excluded | prohibited | BLOCKED BY POLICY |
| Input-level EOD validator | copied OHLCV/model input/current calendar | 2026-09-16 and 2026-09-17 | PASS_INPUT_LEVEL |
| Schedule-bound validator | copied schedule attestation | not run against phase entrypoint | available but phase path remains blocked |
| Score manifest/artifact | copied for 2026-09-17 | PASS via explicit shadow adapter | full replay still BLOCKED by missing state/CA and source path provenance |

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

The final replay disposition is BLOCKED / INPUT-LEVEL PASS ONLY, not a full
historical E2E replay.

`HISTORICAL_REPLAY = BLOCKED / NOT RUN`.
