# E2E cloud trigger and Security Master live-identity audit V1

Date: 2026-08-27 Asia/Jakarta  
Lane: `audit/e2e-security-master-live-identity-v1`  
Source implementation anchor: `fix/e2e-cloud-runtime-security-master-bootstrap-v1@6ec8ade98b47ea8099dff0fc32e9b3a644d260a2`

## Scope and boundary

This checkpoint separates the already-proven trigger fallback from the
downstream E2E runtime blocker. It does not change the production workflow,
the deployed implementation pin, the watchdog branch, scheduler tasks,
provider capture policy, model/Decision/Execution science, or outcomes.

## Production ground truth

The following evidence was read from GitHub Actions and the local watchdog
event ledger; timestamps are UTC unless noted otherwise.

| Evidence | Observed result |
|---|---|
| Watchdog at `2026-08-27T12:40:06Z` (`19:40 WIB`) | Requested exact Stockbit `1930` dispatch. |
| Stockbit run `33072962647` | `workflow_dispatch`, slot `1930`, success; `cycle_status=WAITING_CANONICAL_EOD_GATE`, `provider_calls_attempted=0`, `retroactive_capture_used=false`, `outcome_accessed=false`. |
| Watchdog at `2026-08-27T12:40:10Z` | Treated delayed E2E schedule run `33072549882` as ambiguous for `POST_EOD` and requested an exact `POST_EOD` dispatch. |
| E2E run `33072967537` | `workflow_dispatch`, phase `POST_EOD`; entered the runtime and failed closed with `CLOUDSECURITYMASTERERROR` / `RUNTIME_SECURITY_MASTER_BASELINE_LIVE_IDENTITY_MISSING:CNTB`. No fill/order/model refit/paper-state mutation/outcome access. |
| Native E2E run `33072549882` | Created around `19:34:56 WIB` but resolved to morning `PREOPEN`, not a `POST_EOD` recovery; failed separately with `E2E_DEPLOYMENT_WORKTREE_DIRTY`. |
| Watchdog result ledger | `provider_calls=0` and `protected_outcomes_accessed=false` for the watchdog process. |

Therefore the trigger portion is classified:

```text
TRIGGER REDUNDANCY: PROVEN
NATIVE GITHUB SCHEDULE: DEGRADED / BACKLOGGED
POST_EOD RUNTIME: BLOCKED
CURRENT BLOCKER: RUNTIME_SECURITY_MASTER_BASELINE_LIVE_IDENTITY_MISSING:CNTB
```

The delayed native run did not suppress the later exact slot: the watchdog
kept the ambiguous run separate and dispatched the required `1930` and
`POST_EOD` inputs. This proves conservative trigger fallback for the observed
incident, not full E2E production acceptance.

## Separate external provider-infrastructure incident

An external operator report places a Pluang/Stockbit Cloudflare-bypasser
billing incident at approximately `17:44–18:44 WIB` (`10:44–11:44 UTC`) on
2026-08-27, with service reportedly restored around `18:44–18:47 WIB`. This is
recorded as a separate provider-infrastructure incident, not as an explanation
for the scheduler or Security Master failures.

The IDX-Trade evidence in that exact window does not corroborate an in-window
provider failure:

- Stockbit watchdog dispatch at `18:40 WIB` completed before provider capture
  and recorded `provider_calls_attempted=0`.
- The E2E `18:35 WIB` path failed before provider access with the separate
  deployment-worktree-dirty guard.
- The Stockbit Stream run observed at `19:00:56 WIB`, after the window, failed
  on the `CENT` item schema and showed no Cloudflare/403/timeout marker.
- Official Open evidence at approximately `18:45 WIB` was an
  `AFTER_WINDOW_NO_EXECUTION_GRADE` local result, not an in-window provider
  failure.

Therefore the causal classifications remain explicitly separate:

```text
1. GITHUB_SCHEDULER:
   DEGRADED / BACKLOGGED native schedule delivery; exact-slot watchdog
   fallback was used.
2. EXTERNAL_PLUANG_STOCKBIT_BYPASSER:
   EXTERNALLY_REPORTED_PROVIDER_INFRASTRUCTURE_INCIDENT;
   IDX_TRADE_CORROBORATION=NONE_IN_17:44_18:44_WIB_WINDOW.
3. SECURITY_MASTER:
   CNTB_INTEGRITY_LIFECYCLE_MISMATCH; current-active snapshot omission of a
   baseline-listed suspended identity, corrected generically in this lane.
```

No causal collapse is justified. In particular, the external report must not
be used to explain missing GitHub schedule events, the Official Open morning
failure, or the CNTB Security Master failure.

## CNTB root-cause tree

```text
official current-active IDX response
  -> fetch_complete_active_listings / normalized active rows
  -> CNTB absent because current-active is not a legal-identity history
post-freeze official delisting response
  -> no CNTB delisting row through observation
build_security_master(active, delisted)
  -> CNTB absent from current union
frozen baseline config
  -> CNTB present, listed_from=2000-12-22, live at freeze/observation
baseline-live set difference
  -> old implementation raises BASELINE_LIVE_IDENTITY_MISSING:CNTB
```

Evidence supports the following conclusions:

- `CNTB` is first introduced to this runtime path by the accepted frozen
  baseline `config/stockbit_stream_universe_v1.csv`, not by a newly admitted
  provider row. Its row is `CNTB,Century Textile Industry Tbk Seri B,2000-12-22`.
- The project context records official KSEI/IDX identity evidence: CNTB is
  `Saham Biasa`, IDX, KSEI Active, listed `2000-12-22`.
- The same context records official IDX suspension evidence from
  `Peng-SPT-00006/BEI.PP1/08-2024`, effective `2024-08-07`, with later
  negotiated-market activity not reopening the Regular Market.
- This is not a new IPO, ticker rename, relisting, delisting, or corporate
  action identity change. It is a category error: current-active absence was
  treated as legal identity disappearance instead of a possible suspension.
- The baseline is not stale in the relevant sense; the identity and its legal
  suspension state are already retained in the accepted project artifacts.

Relevant local artifact hashes:

- `config/stockbit_stream_universe_v1.csv`:
  `25d2cc80a883c3026538db747da73ab715e8c179e45d8e02ae2d01c4abe15380`
- `config/curated_tradability_intervals.csv`:
  `b827c746e44a4e5ed9aca34a3d85044ed8078912fdcda1c2f8b4b9f13b5e20ba`

## Generic remediation

`src/idx_trade/e2e_cloud_security_master_v1.py` now:

1. validates active, delisted, baseline, and merged identity frames before the
   existing canonical builder can silently drop malformed rows;
2. requires four-character normalized IDX identity, valid listing intervals,
   and unique identity rows;
3. rejects current listing or delisting dates after the observed date;
4. compares shared baseline/current listing dates and fails closed on a
   rename/relisting-style identity conflict;
5. requires baseline identities that were live at observation to be present in
   current active data, post-freeze delisting evidence, or unchanged baseline
   continuity;
6. preserves a baseline identity absent from current-active only when no
   explicit delisting row contradicts it, with source marker
   `IDX_FROZEN_BASELINE_IDENTITY_CONTINUITY`;
7. continues to admit an identity absent from baseline only when the official
   listing date is strictly after the frozen date; and
8. records preserved-baseline identities and counts in the refresh manifest.

No ticker-specific exception was added. A genuine new listing still requires
complete authoritative source data and a post-freeze effective listing date;
an unknown/malformed/bogus source identity remains fail-closed.

## Validation

- focused Security Master + source completeness suite: `23 passed`;
- `py_compile src/idx_trade/e2e_cloud_security_master_v1.py`: PASS;
- `git diff --check`: PASS;
- provider calls in this lane: none;
- protected outcome access in this lane: none.

Adversarial coverage includes suspended-like baseline continuity, valid
post-freeze listing, malformed source identity, future listing date, baseline
listing-date conflict, stale baseline end-date, duplicate identity, invalid
interval, and same-input restart determinism.

## Decision and next proof

The watchdog fallback is `PRODUCTION_PROVEN_FALLBACK` for the observed
19:40 incident. The E2E runtime remains blocked until this generic remediation
is reviewed and integrated into the exact production implementation pin.

No manual production rerun or backfill was performed. A future genuine
scheduled POST_EOD session must prove that the refreshed identity artifact is
created, the CNTB-style suspended identity is preserved without admitting
unverified identities, and the rest of the existing fail-closed E2E gates
remain unchanged.
