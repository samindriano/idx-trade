# Historical E2E KSEI + Structured IDX Closure V2

Date: 2026-08-24  
Branch: `research/idx-historical-e2e-replay-v1`  
Source commit before this documentation: `44f5d2e018c706bccda5d2dbc453b15a4de4d799`

## Scope and boundary

This was an outcome-blind data-closure pass. It reused the existing KSEI
captures and bounded Zapi/IDX structured-source probes; it did not restart the
market-wide acquisition. No labels, scores, returns, NAV, P&L, performance,
Monte Carlo, forward runtime, scheduler, counter, or protected outcome was
accessed.

`coordination/TEAM_STATUS.md` was not edited because MAIN owns that file.

## KSEI positive-control result

The existing official KSEI registered-security history evidence was reused:

| Artifact | SHA-256 |
|---|---|
| `merged_ksei_611/MANIFEST.json` | `8a72eb195904af842f8250d17a8d2982609e2a4650da4eaed7c480e6c1cf5e0a` |
| `merged_ksei_611/ksei_ca_history.jsonl` | `4dcdd9e44cc40e348079c1447aa3e1e20427b000247be5be91b6622fb03e997d` |
| `merged_ksei_611/ticker_coverage.csv` | `44f7b9e9f7e02e5f2dacaf27f5ded3aa1d41d4ce61664725db096f7a28a93081` |
| `merged_schedule_evidence.csv` | `05bfe12a2c81510cda8836c5c1e7efcd47c35ab6a9d120bebf519735c631a992` |
| KSEI positive-control `EVIDENCE_MANIFEST.json` | `7fa05f2f268b3f05bc18598143d84f8d82ff4254b343234312e4132da1682946` |
| KSEI positive-control `CONTROL_RESULTS.json` | `3ef2eb4cfe1a8c46dcd15ca270fcb20e266d008635c8dddfdf63735718be6b36` |

The 15 bounded controls cover cash dividend, stock dividend, rights,
mandatory conversion, and cancelled events:

- 11 controls reproduced event type, dates, ratio, and status exactly;
- 1 additional cancelled stock-dividend control reproduced event, dates, and
  status but had no ratio in the source and therefore remains ratio-unresolved;
- 3 BBCA controls were unavailable on the repeat request (HTTP 500) and were
  not treated as absence or as a pass.

The KSEI pages exposed the six expected CA columns. For the nine successful
sample pages, returned row counts matched the prior pinned census and no
server pagination marker was observed. This is sufficient for positive-row
reproduction, not for market-wide negative/no-event certification. KSEI also
does not expose a sufficient revision/correction lineage field in this
surface, and no split/reverse-split control was invented when none was
available in the certified sample.

The existing 601-ticker corpus covers all 347 exposure tickers, but only 343
are certified. Exposure-unresolved KSEI tickers are `AYAM`, `FREN`, `SLIS`,
and `SOCI`. The normalized corpus does not contain security identity/ISIN or
retrieval-time fields; those remain unavailable rather than fabricated.

The bounded attestation and exposure coverage extract are external to Git:

- `D:\Documents\Project\idx-historical-e2e-ksei-structured-closure-v2-20260824\KSEI_STRUCTURED_CLOSURE_MANIFEST.json`
  SHA-256 `7aae55fe3ff22e1b05375909cca2b556003821aeab00cc86c58b40f3ca7d96a9`;
- `KSEI_EXPOSURE_TICKER_COVERAGE.csv` SHA-256
  `be062b09414cc23102887df6ab72b1a6b789dbc1885ec413d3395b98ba581cd3`.

## Structured IDX/Zapi result

The catalog schema probes were HTTP 200 but generic. The catalog artifact SHA
is `bdb7538832345f2272feb962f13d60173af7b3544c7d0da5e7956a8c4d4c0faa` and
the bounded positive-control result SHA is
`52cd017192ec45bbb76c65230f22ad39290b4ff79778a113d0d42111eb16ffb6`.

| Dataset | Bounded result | Consequence |
|---|---|---|
| `stock-splits` | RAJA `1:5`, `2026-07-16`, `count=1,total=1` | Event identity/ratio positive, but full market-effective date semantics remain unclear versus KSEI record/distribution dates; no negative use. Raw SHA `a4473db06e46004cec2b5f72460b15d294a7cd20da4b0116bcb9184548bd0add`. |
| `additional-listings` | YOII right issue reproduced, `lastDate=2026-07-23`, `count=1,total=1` | Bounded identity positive, but a nonmatching RANS query returned YOII; search is unsafe for negative enumeration. Raw SHA `7eef4de9a09aec32d7121a08c346babfd088cb66ca1d1d1460fa9d1a979bb29f`. |
| `rights-offerings` | Known YOII/PANI positive returned zero | `POSITIVE_CONTROL_FAIL`; no absence inference. |
| `delistings` | Known FREN/MEGA positive returned zero | `POSITIVE_CONTROL_FAIL`; no absence inference. |
| `issued-history` | Known RAJA transition returned zero | `POSITIVE_CONTROL_FAIL`; no absence inference. |
| `dividends` | Prior BBCA known-positive failed | `POSITIVE_CONTROL_FAIL`; no broad query repeated. |

Therefore no structured endpoint was admitted as a complete historical
negative-evidence or continuity source. The two bounded identity-positive
routes remain discovery/cross-check evidence only.

## Target-window and scope recompute

Because the outcome-blind closure inputs still could not certify every
exposure row, no target closure window was frozen and no new target-specific
KSEI acquisition was started.

The exact pinned scope validator was run once with a fresh output root:

`D:\Documents\Project\idx-historical-e2e-scope-closure-v3-20260824\REPLAY_SCOPE.json`

| Result | Value |
|---|---:|
| Candidate sessions | 600 |
| Strict sessions | 0 |
| CA-ready rows / sessions | 4,471 / 40 |
| Dividend-ready rows / sessions | 11 / 0 |
| Scope artifact SHA-256 | `cb765a5f1675ea35c2a4d075302c64fd6ac09d413ba8edb4a8198079ed203ae0` |
| Scope payload SHA-256 | `f75cf7302f4bd27927e36e296634c7ae9adfcd32849ed8fc78555a9e27dc6fd7` |
| Status | `STRICT_SCOPE_EMPTY_BLOCKED` |

Exact blockers remain:

- `NO_CONTIGUOUS_EXPOSURE_COMPLETE_RANGE`;
- `DIVIDEND_EXPOSURE_WINDOW_PROOF_INCOMPLETE`.

The 4,384 dividend exposure rows requiring attachment semantics and 1,298
rows with no-event proof not authorized remain fail-closed. The 1,222 CA
exposure rows unresolved in the pinned CA ledger also remain unresolved.

## Decision

KSEI positive evidence: **PASS for bounded positive-row reproduction**.  
KSEI negative/no-event certification: **NO-GO**.  
Structured IDX replacement for complete closure: **NO-GO**.  
Non-empty strict historical replay scope: **NOT ESTABLISHED**.

Final disposition remains:

`TRUE_HISTORICAL_E2E_ENGINE_READY_PERFORMANCE_BLOCKED_BY_DATA`

The next source needed is an official structured historical CA/dividend
archive with deterministic identity, date semantics, revision chronology, and
complete pagination/coverage—most likely an IDX Data Reference or paid
official KSEI/IDX product. Thousands of arbitrary announcement PDFs are not an
acceptable fallback.

No replay, performance, NAV, or Monte Carlo was run.
