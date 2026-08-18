# V4 CA Voluntary-Conversion Forensic Replay V1 — Preregistration

Status: `PREREGISTERED_BEFORE_EXTERNAL_BYTE_REPLAY`

Branch: `data/idx-v4-ca-voluntary-conversion-forensic-replay-v1`
Scientific code/config anchor: `0727d13597315b5c00d7829ff12beac55701b224`
Parent result under review: `data/idx-v4-ca-voluntary-conversion-semantics-remediation-v1@5b9afc24b758413f315351971b2cd07f634dc9c9`

## Why this replay exists

The prior remediation result reported:

- parent relevant events: 136 before remediation;
- remediation relevant events: 102;
- source-native Voluntary Conversion rows remaining in the remediation audit: 29;
- reported Voluntary Conversion rows reclassified to `VOLUNTARY_CASH_SETTLEMENT`: 0;
- minimum continuity changed from 0.7588075881 to 0.7912087912.

Those facts are not internally interpretable as written. The remediation classifier returns strict source-native security-to-currency Voluntary Conversion rows as `NON_BLOCKING`, while the inherited `event_relevant_to_study_period()` filter excludes all `NON_BLOCKING` events from the relevant-event audit. Therefore a successful reclassification can disappear from the downstream audit before a post-filter count is computed.

The exact numerical delta `136 - 102 = 34` is consistent with, but does not prove, such a reporting/filtering undercount. This replay is frozen specifically to prove or reject that explanation from the immutable bytes.

## Pinned inputs

- immutable KSEI history JSONL SHA-256: `3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d`
- official calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- parent Stage-1 event audit SHA-256: `ba08fbdab5b72b377888320163ba8b893e7d1a19f69384ba7be0fdac5ca33908`
- remediation event audit SHA-256: `a2fe0206189916a796cda170e819053dd7147bf988ceed27f278081684ca4f1a`
- parent Stage-1 per-date SHA-256: `eefd6cbeed7381b01935a95b777cd88cfa4e073c0abc7d318005c2bc381fd85d`
- remediation per-date SHA-256: `55de6a8dc981bc2b16be96e3c02d767c6655b7025c402dbd50aa5d95aa65cbb9`

Expected promoted counts are 136 parent events, 102 remediation events, and 600 dates. Any mismatch stops the replay.

## Required outputs

The replay must emit:

1. `voluntary_conversion_ratio_dump.csv`: every parent-relevant source-native Voluntary Conversion row with immutable `ratio_raw`, parse status, left security, right security, and both classifier outputs;
2. `event_set_diff.csv`: exact removed/added event identities;
3. `classifier_side_by_side.csv`: parent vs remediation classification for every parent-relevant event;
4. `continuity_per_date_diff.csv`: parent vs remediation 600-date support output comparison;
5. `summary.json` and `MANIFEST.json` with exact hashes.

## Hard invariants

- No event ID may be added by the remediation audit.
- Every event ID removed from the parent relevant set must equal an event that the remediation classifier changes from blocking to `NON_BLOCKING`.
- Every removed event must independently satisfy the already-frozen strict predicate: source type `Voluntary Conversion`, active, ratio parsed from source text, left security exactly equals ticker, and right security is a recognized currency.
- If replay finds zero reclassifications, the parent and remediation event sets must be identical.
- If replay finds zero reclassifications, all comparable 600-date continuity fields must also be identical.
- Any unexplained removed event, added event, classifier/artifact mismatch, hash mismatch, or invariant failure produces only `FORENSIC_REPLAY_INCONSISTENT_BLOCKED`.

## Interpretation boundary

A verdict confirming reporting undercount means only that the existing frozen voluntary-cash semantic rule was applied but the prior result summary counted after the non-blocking filter. It does not introduce a new CA rule and does not itself certify the V4 CA gate.

No provider calls, schedule acquisition, R5/R10, targets, ranks, model fitting, prediction, performance metrics, or protected/fresh-forward outcomes are authorized.