# Foreign Flow Transition Challenger V1 — Prospective Shadow Diagnostic

Date: 2026-09-19 Asia/Jakarta  
Lane: `codex/alpha-challenger-pit-safe-20260919`  
Status: `SHADOW_MATERIALIZED — NOT ADMITTED`

## What was materialized

Using the accepted Foreign Flow V2 builder from
`integration/foreign-flow-prospective-pit-shadow-v1@10d6060fad89de7bc030bae45326024aaf98fcf3`,
the isolated diagnostic replayed the already-produced canonical source session
`2026-09-16` into feature session `2026-09-17`. It used the historical archive
through `2026-08-13` and only forward raw sessions after that boundary. The
overlap was rejected explicitly; no duplicate source identity was silently
deduplicated.

The challenger overlay was then computed as the frozen
`foreign_weighted_persistence_5 - foreign_weighted_persistence_20` rank. No
outcomes, labels, fitting, incumbent rescore, provider call, counter, or
canonical artifact write occurred.

## Diagnostic result

- official-session union: `1,288` sessions;
- causal market rows used: `1,002,726`;
- foreign-flow rows used: `1,132,491`;
- target rows/tickers: `963 / 963`;
- transition available: `790 / 963` (`82.035306%`);
- transition rank bounds: `0.0012658228` to `1.0`;
- `flow_through_session == 2026-09-16` for every target row: `true`;
- duplicate `(ticker, feature_session)` keys: `0`;
- outcome-like columns in output: none.

This demonstrates that the fixed transition overlay can be computed on a
post-freeze prospective source snapshot without reading outcomes. It is not a
performance result and cannot establish OOS improvement by itself.

Against the already-committed incumbent score artifact for the same feature
session, the structural cross-check found:

- incumbent score rows: `296`;
- common rows: `296`;
- transition available on common rows: `284/296` (`95.945946%`);
- prospective transition-rank Spearman versus incumbent rank: `0.11970779`;
- fixed `90/10` blend top-30 overlap: `100%`;
- fixed `90/10` blend top-30 churn: `0%`.

These are one-session orthogonality and turnover diagnostics only. They are not
IC, return, or OOS evidence; the exact top-30 overlap must not be interpreted as
an alpha win.

## Input identity

The source session manifest declares `DATA_READY`, `outcome_blind=true`, and
`forward_outcomes_accessed=false`:

- session manifest SHA-256: `27912cb5b6a8e04608e0a44bf2e9f8eb8e207cf0492585d1eb9421a2340d7119`;
- raw Stock Summary SHA-256: `ded996904611e603c0bcb1c8b2815b1e8c93c926b42e06a894894ef8a6f83ab6`;
- current calendar SHA-256: `fb853b375c47bcd3afb97a775b0f15a9afbbfef66a000915f89b52c302068762`;
- security-master file SHA-256: `39c34074204bc09af3521a73bd66d2dbc45faf6b81dd0ed0c8c25f4e3880df93`.

## Why it is not admitted

The current evidence does provide a partial run binding:

- EOD run `20260917T113016Z-3ced2a5b` reports `NO_MISSING_SESSION`,
  `outcome_access=LOCKED`, and captures sessions `2026-09-16` and `2026-09-17`;
- V4 pipeline run `20260917T113016Z-04128c51` embeds that EOD `run_id` and the
  exact snapshot/OHLCV hashes, with `protected_outcome_accessed=false`;
- EOD run SHA-256:
  `e453c39efa42076a8a34bd05a72051d2fa04b4e7832a858967f5d4d40332ec7f`;
- V4 pipeline run SHA-256:
  `31a4b8bd37e1d27519a003eccc51bc1ee3fc12170f049f4e3429f7f9e4b295cc`.

The binding is still incomplete for Foreign Flow admission: the EOD run record
does not carry the raw Stock Summary SHA or an explicit capture-attempt number,
and the attempt directory is not linked from the run record. The
security-master file has a hash but no independently attested as-of validity
bound to this source observation. Those gaps are sufficient to keep this result
shadow-only under the PIT contract. `DATA_READY`, file existence, and a partial
run chain are not promoted into admission.

The next legitimate step is to obtain a future canonical session with the
completion/attempt/hash attestation and security-master as-of contract fixed;
then replay this same frozen overlay. Do not use this snapshot for historical
performance selection, sign flips, weight tuning, or incumbent replacement.
