# V4 CA Voluntary-Conversion Forensic Replay V1 — Result

Status: `REVIEW`

## Scope and validation

- branch: `data/idx-v4-ca-voluntary-conversion-forensic-replay-v1`
- execution HEAD: `ed6cd8aad1256df00ea5b09156f3d061e3cf3b50`
- scientific/config anchor: `0727d13597315b5c00d7829ff12beac55701b224`
- focused pytest: `15 passed in 0.63s`
- `py_compile`: PASS
- `git diff --check`: PASS
- replay count: exactly one
- provider calls: `0`
- schedule acquisition: `false`

The first pytest invocation was accidentally issued from the unrelated
`US-Stock-Model` workspace and found no IDX tests. No replay or data access
occurred in that invocation. The exact validation was then rerun from this
worktree and passed as reported above.

## Forensic replay findings

The parent audit contains 136 relevant events, including 63 `Voluntary
Conversion` rows. The remediation audit contains 102 relevant events. The
forensic difference is deterministic:

| Measure | Count |
|---|---:|
| Parent relevant events | 136 |
| Remediation relevant events | 102 |
| Removed events | 34 |
| Added events | 0 |
| Parent Voluntary Conversion | 63 |
| Strict security-to-currency predicate | 34 |
| Reclassified to non-blocking | 34 |
| Remaining Voluntary Conversion schedule-required | 29 |
| Removed IDs equal reclassified IDs | YES |
| Every removed ID satisfies strict predicate | YES |

The replay verdict is:

`FORENSIC_REPLAY_CONFIRMS_VOLUNTARY_CASH_RECLASSIFICATION_REPORTING_UNDERCOUNT`

The preceding remediation result reported zero reclassifications because its
relevant-event audit was narrower. The forensic replay against the parent
audit shows that 34 strict source-native security-to-currency conversions were
removed by the remediation classifier and correctly became non-blocking.

## Ratio evidence

The ratio dump has 63 rows:

- `PARSED_SOURCE_TEXT_ONLY`: `34`
- `UNRESOLVED_SOURCE_TEXT`: `29`
- parsed rows with `ratio_left_security == ticker`: `34`
- parsed rows with right token `IDR`: `34`
- strict security-to-currency predicate: `34`
- unresolved rows satisfy neither parsed left/right evidence path: `29`

Representative exact parsed ratios include:

| Ticker | Source ratio |
|---|---|
| ADMF | `(1 ADMF : 9082 IDR)` |
| ANJT | `(1 ANJT : 1813 IDR)` |
| AYLS | `(1 AYLS : 134 IDR)` |
| BEEF | `(1 BEEF : 123 IDR)` |
| CNKO | `(1 CNKO : 8 IDR)` |
| DATA | `(1 DATA : 974 IDR)` |
| EDGE | `(1 EDGE : 11500 IDR)` |
| EXCL | `(1 EXCL : 2350 IDR)` |

## Continuity comparison

- frozen date rows compared: `600`
- changed parent-vs-remediation date rows: `600`
- identical date rows: `0`
- no target/rank/metric materialization was performed

This replay is a reporting/identity audit only. It does not promote the
overall corporate-action continuity gate or authorize V4 target/model work.

## Provenance and hashes

External output root:
`D:\Documents\Project\idx-v4-ca-voluntary-conversion-forensic-replay-20260818-v1`

Input hashes:

- KSEI history: `3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d`
- official calendar: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- parent event audit: `ba08fbdab5b72b377888320163ba8b893e7d1a19f69384ba7be0fdac5ca33908`
- parent per-date: `eefd6cbeed7381b01935a95b777cd88cfa4e073c0abc7d318005c2bc381fd85d`
- remediation event audit: `a2fe0206189916a796cda170e819053dd7147bf988ceed27f278081684ca4f1a`
- remediation per-date: `55de6a8dc981bc2b16be96e3c02d767c6655b7025c402dbd50aa5d95aa65cbb9`

Promoted output hashes:

- `MANIFEST.json`: `495401d683b2faac953cb73086324561670c7c2b825055e18984729aba3b5287`
- `summary.json`: `7d2fde23d99a375557b635276060a27ffbff893a2fc69a050051396a6f974c45`
- `event_set_diff.csv`: `e5bfe4311704b3bfa26a20448102084ab7397d7bd6ed6c85d39f6194467554df`
- `voluntary_conversion_ratio_dump.csv`: `904a257e2070fe6237a8746c69d68cc1ea2d6505800c2339d8820b17ce39312f`
- `classifier_side_by_side.csv`: `e621b19f4af6aee7ad5f5bdf433e0a26aad2bc3125ce932205d0fb25fedeb05d`
- `continuity_per_date_diff.csv`: `dbfa35831cf80f54ff64fbeac1008e8f9e87764c384d6aba611e744c6a886976`
- manifest SHA: `495401d683b2faac953cb73086324561670c7c2b825055e18984729aba3b5287`

## Boundaries

No KSEI/provider calls, schedule Stage 2/3, CA acquisition, R5/R10, targets,
ranks, model fitting, predictions, performance metrics, protected outcomes, or
fresh-forward outcomes were accessed. Stop for independent ChatGPT review.
