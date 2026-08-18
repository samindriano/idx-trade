# V4-3 CA training-domain — KSEI 129 coverage expansion prep

Date: 2026-08-19 Asia/Jakarta
Branch: `data/v4-3-ca-training-domain-ksei-129-v1`
Status: `READY_FOR_BOUNDED_OFFICIAL_KSEI_129_CENSUS`

## Finding

The outcome-blind V4-3 CA training-domain gate completed with a real domain
mismatch, not a target/model failure:

- decision-domain tickers through the frozen end: **739**;
- accepted final CA census tickers: **611**;
- historical decision tickers absent from that census: **129**;
- absent-window rows: **39,008**;
- combined frozen validation minimum support fell to **80.508475% H5** and
  **79.423868% H10/consensus**;
- zero dates therefore met the frozen >=90% combined target-support gate;
- no historical target, rank, model, prediction, performance, or protected
  forward outcome was accessed.

The missing set is not selected by impact or by the amount needed to make the
gate pass.  The entire exact 129-ticker identity set emitted by the blocked
gate is frozen for remediation, SHA-256:

`28d39c8b1a08585724e6b78d3b76520073043aa7c0f0a53bf6ae1f2fb5bbf58f`

The blocked training-domain manifest is pinned at:

`b7c87f709d27b8d2860f7cde073d048042810c4de21ce6fd4441e8556d96b46d`

## Remediation boundary

Only the exact 129 missing registered-security identities are acquired from the
same official public KSEI security-history endpoint already used by the accepted
V4 CA work.  The runner:

- uses `curl_cffi`, `chrome110`, a fresh session and KSEI home warmup per ticker;
- uses the unchanged strict `parse_ksei_security_history` parser;
- allows no alternate provider, alternate security identity, source substitution,
  or parser/semantic relaxation;
- writes raw HTML append-only plus normalized coverage/history/request delta;
- does **not** modify or recrawl the accepted parent 611 census;
- does **not** materialize returns, target ranks, model fits, predictions,
  performance, or protected-forward outcomes.

Config:
`config/v4_3_ca_training_domain_ksei_129_v1.json`

Runner:
`scripts/run_v4_3_ca_training_domain_ksei_129_census.py`

## Next after local census

The 129 delta must be reviewed and hash-pinned.  Then a separate **offline**
merge/replay will combine certified delta rows with the immutable final CA
census and rerun the full V4-3 training-domain support intersection.  Only that
replay can determine whether the >=90% gate is restored.  Any remaining
schedule-required events are handled after coverage expansion and are not
waived or inferred from price data.
