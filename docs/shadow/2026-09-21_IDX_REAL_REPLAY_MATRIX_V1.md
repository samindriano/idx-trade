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

## Selected real manifests

Both selected manifests are `DATA_READY`, outcome-blind, and explicitly report
no forward-outcome access. The 2026-09-16 manifest has 963 listed tickers and
828 model rows. The 2026-09-17 manifest has 963 listed tickers and 831 model
rows. Their hashes and child-artifact hashes are recorded in the master
dossier and immutable-manifest candidate.

## Why replay was not claimed

The available session corpus does not itself define the E2E paper state,
prepared parent, execution identity, CA authority, or recovery chain. Running
the candidate by projecting these inputs into invented state would violate the
fail-closed boundary. No replay entrypoint was invoked in this lane.

`HISTORICAL_REPLAY = BLOCKED / NOT RUN`.
