# Foreign Flow Forward Context Bridge V1 — Local Runtime Result

Date: 2026-08-15 (Asia/Jakarta)

Branch: `data/foreign-flow-forward-context-bridge-v1`

HEAD at execution: `56b5b3c8041b87020f8cbfc25296eff3aeeacc4a`

Verdict: `CONTEXT_BRIDGE_READY_BUT_SMOKE_BLOCKED_FULL_CALENDAR_CONTRACT`

## Scope and preflight

The canonical `origin/main:coordination/TEAM_STATUS.md` lane was claimed as
`ACTIVE` before runtime work. HSC/free-float and O2 lanes were not modified.

Focused command:

```text
python -m pytest -q tests/test_forward_foreign_flow_context_bridge.py tests/test_forward_foreign_flow_context_bridge_policy.py tests/test_forward_foreign_flow_context_bridge_plan.py tests/test_forward_foreign_flow_representation_v2.py tests/test_forward_foreign_flow_setup.py
```

Result: `24 passed, 0 failed, 5 warnings`.

Full command: `python -m pytest -q`

Result: `118 collected, 117 passed, 1 failed, 5 warnings`.

The only failure was the known unrelated storage expectation:
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
expected one conflict while the current storage contract reports independent
`raw_close` and `vendor_adj_close` conflicts. No storage or joblib fix was made.
`git diff --check`: PASS.

## Accepted input pins

Runtime root:
`D:\Documents\Project\idx-trade-data-gate-20260808v`

| Input | Path | SHA-256 |
|---|---|---|
| Historical market panel | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet` | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| Historical Foreign Flow archive manifest | `D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1\archive_manifest.json` | `fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334` |
| PIT security master | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\security_master_1260.csv` | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| Accepted historical calendar | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |

## Bridge calendar

The handoff's legacy monthly HTML calendar command was attempted first. It
failed closed because both requested months returned zero parsed sessions:
`parsed_months=0`, `error_months=2`, `exchange_sessions=0`. No incomplete range
was promoted.

The current official IDX Daily Statistics publication-listing endpoint was
then used for the bounded range:

```text
https://www.idx.id/primary/Statistic/GetStatistic
```

Exact parameters were `type=daily`, `lang=en-us`, `StartDate=2026-07-01`,
`EndDate=2026-07-31`, `keyword=` and the equivalent August range. The
immutable bridge range is:

`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\context_bridge\calendar\ranges\2026-07-31_2026-08-13\exchange_sessions.csv`

- session count: `10`
- dates: `2026-07-31`, `2026-08-03` through `2026-08-07`, and
  `2026-08-10` through `2026-08-13`
- calendar SHA-256: `51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`
- summary SHA-256: `21fb08dee01318844fdacd5bdd54f06111dd404c13a9ec7740f08c169978ca06`
- raw July response SHA-256: `34301c51175b908c038a879b91404fd6ab627df0acb34deaa7c15ecf00003209`
- raw August response SHA-256: `1fa5e36cce324d0858c1af8985e41be0075feef2f8c73dabe1d17434d1c514d3`
- session-set SHA-256 over canonical newline dates:
  `3f91c661d2355b4457fb0977775adbb486aa56648936ee4257131dc0a1a5556f`

A diagnostic combined calendar was also materialized without changing the
operator calendar:

`D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\context_bridge\calendar\ranges\2021-04-29_2026-08-13\exchange_sessions.csv`

It contains `1,269` dates and combines the accepted historical calendar with
the verified extension. Its calendar SHA-256 is
`b3fbbed7f4dcea83fe7cd60c2b9ec98e4227ed309e50ea4cd8af105a0116594e`.
It was not used to rewrite or reinterpret the already captured bridge
sessions; those manifests are immutably pinned to the 10-date bridge range.

## Read-only planner

Planner input used historical cutoff `2026-07-31` and source session
`2026-08-12`.

Before capture:

- required extension sessions: `8`
- `NEED_BRIDGE_CAPTURE`: `2026-08-03`, `2026-08-04`, `2026-08-05`,
  `2026-08-06`, `2026-08-07`, `2026-08-10`
- `CANONICAL_READY`: `2026-08-11`, `2026-08-12`
- `NEED_CANONICAL_EOD`: none
- ambiguous: none
- provider calls/writes: `0 / 0`

After capture:

- status: `CONTEXT_BRIDGE_READY`
- `BRIDGE_READY`: all six bridge dates
- `CANONICAL_READY`: `2026-08-11`, `2026-08-12`
- `NEED_BRIDGE_CAPTURE`: none
- `NEED_CANONICAL_EOD`: none
- ambiguous: none
- provider calls/writes by planner: `0 / 0`

The planner correctly retained `2026-08-03` and `2026-08-10` as bridge-only
because their incomplete canonical directories were not treated as valid or
repaired.

## Bridge captures

Every capture used the official IDX Stock Summary endpoint with a complete
single response (`recordsTotal=recordsFiltered=963`) and the existing Yahoo
raw OHLCV path. `local_price_hits=0` for all six sessions; the listed count is
the number of validated downloaded price rows. All manifests record
`bridge_only=true`, `canonical_session_repair=false`,
`outcome_blind=true`, and `forward_outcomes_accessed=false`.

| Session | Flow rows | Market rows | Downloaded price rows | Manifest SHA-256 | Raw SHA-256 | Market SHA-256 | Flow SHA-256 |
|---|---:|---:|---:|---|---|---|---|
| 2026-08-03 | 963 | 831 | 831 | `70eb58dc5daf1472ffae665131cfd472cc7aa3c44168ef8d8e26bcad185ab926` | `1dfc0f6fab1305b6e39a5e4e26b2e69729775f737c70a90ea3f2ce9befc01234` | `8512f2f5c06dfc64761c771a65f77eb4b0565bf6026035b04a7abfb0cb3694b0` | `6b775a2140926e6dfc833d58b2e26d4036500ab45b60d289dc9c78d53dae2532` |
| 2026-08-04 | 963 | 834 | 834 | `7616bf321268f18321d429e22f5e8d5448de8882f09480ac95c8362c9cee79c4` | `7a38bfae00fbe2f6a9b582c1091d0ea53ccc6a72a2fb85b0fbc3a39fc4d25156` | `950b0b8622efe0e496a45f0d77c5c39cf0c83b651f0fd76fa279a4c7b291f42f` | `be2958a575d3ca2b89ebb3a75c380fc7eab0ddd2e3b13525b57cc4bc85397ecc` |
| 2026-08-05 | 963 | 833 | 833 | `ce1a5c1bcfee158c30cac29250320265683cc9c2c9b0adfb5d5251d4ec1979e1` | `036395f38e1d18d074fb46a8a48dbfbd055c772186fd7d4daa21499ff97a75f0` | `1180b1644ef89423fb17b6f6e844fbf07811107a72a6689c60f08cecd200308f` | `e52cd6cd45f9590ab8288c09df2458326a05e762f4b47897034252495160f19d` |
| 2026-08-06 | 963 | 835 | 835 | `c5781f840437f58363388b1fef590b2c1bf42a7d58708be1a9194f7b9b903a75` | `c7407c24a999d65f69c4b019ea52fc42811e1248a8fb42b83d93696f57db43af` | `78f2b2abeb42a756a92df23dd652c81a4cece58c3874036a5979375180d3629c` | `d1cc9e7846f63b5ffef6aad512aada75de0fa4e37dbb72fb6b5550b183f09b41` |
| 2026-08-07 | 963 | 834 | 834 | `dba2a9ec87458001d7996da2292db361bc8948f3bb2f4f49e72840911ca126f7` | `84460f75d41dc8d97200ef24d883d9ed3c57453ff43584e1734e1573a9fe4c48` | `18c9e923c578f4771cf695f6194d910c29cdfce277d6d432056268399257cad6` | `80cd67430e229fc3df948ffaa0c6f98912fd740e1300c16e94d4a00699f9d9f8` |
| 2026-08-10 | 963 | 837 | 837 | `87ea8e115bcf186118629695c1caafb432d4d158a7978460b713fd3337ae9c13` | `649d59ccc6a01b48c26dd180454f3f867b272e08cca2c3954b80bb2eb09b06fd` | `a3c01da9d0e05d7f8ae5712847dbd7a49b4b74f2ef25d16e9d5f6826fdaf9a3c` | `5a1169f7a77f548b9b786c1c971e8d38fa4c12ff2126ad23889bca7aea94e669` |

## Smoke run and blocker

Exactly one bridge-aware producer smoke command was started with source
session `2026-08-12`, whose next official session is `2026-08-13`. It failed
before any output pair was written:

```text
ValueError: market panel contains dates outside official sessions
```

The supplied bridge calendar intentionally covers only the extension range,
but `materialize_representation_v2_for_session()` validates the full pinned
historical panel against the same `official_sessions` argument. The bridge
session manifests are themselves immutably pinned to the extension calendar
path/SHA, so silently substituting the combined calendar would invalidate
their provenance. No retry, manifest rewrite, recapture, or source-code
redesign was performed.

Consequences:

- Representation V2 for `2026-08-13`: not materialized;
- prospective Setup State for `2026-08-13`: not materialized;
- output directory did not exist after the failed run;
- no canonical 2026-08-10/11/12 file was overwritten;
- operator calendar and O2 counter were not modified.

Protected canonical manifest hashes observed after the run:

- 2026-08-10: `c2c15d47c437ca2a210197d73bb486e0bf74684967c9a7d9752e73ae403abb15`
- 2026-08-11: `8a76175199aebb7bf3a0c0f852134584f1e0bd78cd389123f80d9d3eaa5ad1bd`
- 2026-08-12: `39f5d02a37a59930ed02ecdbf98fbf5260ed2e6ce5754ff7f558d04357e8d51c`

No outcomes, labels, O2 scoring/counter, model fit, HSC/free-float, price
state, or scheduler path was accessed or changed.

## Review blocker

The runtime data acquisition is complete and the planner is ready, but the
accepted runner needs a reviewed calendar-identity bridge between:

1. the full historical session index required by the V2 materializer; and
2. the extension-only calendar SHA pinned into the six already captured bridge
   manifests.

This result intentionally leaves the lane at `REVIEW`; no prospective smoke
artifact is claimed until that identity contract is resolved by independent
review.
