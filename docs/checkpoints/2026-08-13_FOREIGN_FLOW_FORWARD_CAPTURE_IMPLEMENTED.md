# 2026-08-13 Foreign Flow Forward Capture

Status: `LOCAL_RUNTIME_VALIDATED_REVIEW`

The implementation reuses the official IDX Stock Summary raw artifact already stored by canonical EOD capture. It adds an immutable per-session foreign-flow sidecar in SHARES plus a hash-bound manifest and an offline catch-up runtime. It makes zero provider calls.

Implementation:
- `src/idx_trade/forward_foreign_flow.py`
- `src/idx_trade/forward_foreign_flow_runtime.py`
- `tests/test_forward_foreign_flow.py`
- `tests/test_forward_foreign_flow_sidecar.py`

Semantics:
- `ForeignBuy` and `ForeignSell` are archived in `SHARES`; net is buy minus sell.
- zero is retained as a real observed value;
- missing/invalid/partial/duplicate/date-mismatched rows fail closed;
- all official 4/5-character security codes are archived without inferring common-share eligibility;
- capture time is stored only as an upper bound on knowledge time, not publication time;
- sidecar provenance pins the official raw Stock Summary SHA and parent session-manifest SHA.

Hardening completed on `data/idx-foreign-flow-forward-capture-v1`:
- SHARES are strict non-negative integers; fractional, infinite, negative, and
  missing values fail closed.
- Parent validation requires `DATA_READY`, outcome-blind flags, canonical raw
  SHA, exact source session/date parameter, complete-records status, HTTPS
  source reference, and timezone-aware observed availability.
- Verification deterministically rebuilds the expected frame from the
  session-local canonical `manifest.json` and `idx_stock_summary.raw.json`.
- Sidecar and sidecar-manifest publication is create-once/exclusive; a valid
  sidecar can complete an interrupted manifest without rewriting the sidecar.
- Coherent sidecar plus sidecar-manifest tampering fails semantic verification.

Validation:
- Focused tests: `18 passed`.
- Full pytest: `280 passed, 0 failed, 3 existing warnings`.
- No provider/network calls; no scheduler deployment or modification.

## Local runtime validation

The runtime root was discovered from the installed automation checkpoint and
verified on disk:
`D:\Documents\Project\idx-trade-data-gate-20260808v`.

The catch-up runtime was executed twice. Both runs reported
`provider_calls=0`, `outcome_blind=true`, `forward_outcomes_accessed=false`,
and no failures. The first run created two sidecars; the second created none
and reported both as already valid.

| Session | Rows | 4-char | 5-char | Zero-flow | Source raw SHA-256 | Sidecar SHA-256 | Sidecar manifest SHA-256 | Observed available UTC |
|---|---:|---:|---:|---:|---|---|---|---|
| 2026-08-11 | 963 | 962 | 1 | 299 | `3fceb51a437cab058df00d3949649abcc758de8638315e070e12a6e5371a2ea2` | `b73822ed2506f8e9710ad8b2045bc816a9a4868f00921fcc0faa0ca9db7aac7e` | `22ab6052b1b509da46722743f49e250f0546b2bc34a021937d9e78f7335792a7` | `2026-08-12T11:07:54.613572+00:00` |
| 2026-08-12 | 963 | 962 | 1 | 286 | `816d6e96c736ed11518720bd5a27a6896c3385760c32332319e2ec8dc65bbcb6` | `87fb9e5cc955d161b3753d50ba95de26284d99dd98700850dad9df83c5f70a0c` | `27862bef424e140fa1d8e8e06bc9cb05066b7d14a27b110a508d4d7f8fcd8f7d` | `2026-08-12T11:32:19.803104+00:00` |

Both sessions verified with unit `SHARES`, exact `foreign_net =
foreign_buy - foreign_sell`, and `publication_time_known=false`.
Parent canonical manifest hashes were unchanged:

- 2026-08-11: `8a76175199aebb7bf3a0c0f852134584f1e0bd78cd389123f80d9d3eaa5ad1bd`
- 2026-08-12: `39f5d02a37a59930ed02ecdbf98fbf5260ed2e6ce5754ff7f558d04357e8d51c`

Legacy sessions 2026-08-03 and 2026-08-10 were skipped because their
canonical Stock Summary raw artifacts are absent. No 2026-08-13 canonical
session exists locally; no session was manufactured or backfilled.

Verdict: `FOREIGN_FLOW_PROSPECTIVE_SIDECAR_SAFE_LOCAL_RUNTIME_ONLY`.
The sidecar can safely keep accumulating from already captured canonical EOD
sessions. Scheduler integration remains a separate review/authorization step.
