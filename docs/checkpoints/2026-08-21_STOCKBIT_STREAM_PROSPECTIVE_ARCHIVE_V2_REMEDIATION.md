# Stockbit Stream Prospective Archive V2 — Routine Capture Remediation

Date: 2026-08-21  
Scope: acquisition infrastructure only  
Status: `CLOUD_SMOKE_PASS_READY_FOR_ROUTINE_PROMOTION`

## Why V2 was needed

The first cloud bootstrap used the entire 963-ticker prospective identity list for an `after_close` run. That is useful only as a one-time sparsity/census attempt, not as a recurring social-data universe. The V1 storage hot path also performed raw writes, immediate read-backs, normalized writes/read-backs, and per-post canonical object writes/read-backs. With roughly 30 posts per ticker this turns one Stream request into many sequential object-store operations.

V2 therefore rejects 963-ticker routine capture. Any V1 full-universe objects already written to R2 remain immutable, noncanonical bootstrap/census evidence and are not deleted or promoted into the V2 routine lineage.

## Frozen routine universe

Routine scheduled capture uses the top **200** active current identities ranked by the immediately prior completed IDX session's **regular-market traded value**:

`regular_value = Value - NonRegularValue`

Selection is deterministic with ticker as the tie-break. Same-run Stockbit activity, sentiment, returns, model scores, targets, O2, and protected outcomes are not used.

The source session is discovered by bounded backward search and every returned stock-summary row must attest the exact requested `Date`; this fails closed if Zapi ignores the historical date parameter.

Expected normal 22-session Stream-call budget:

`200 tickers × 3 slots × 22 sessions = 13,200 Stream calls/month`

This intentionally leaves material headroom under the user's 25,000-call Zapi Pro monthly quota.

## Schedule

GitHub Actions remains the canonical scheduler because the user's laptop is not assumed to be awake.

- `08:47 WIB` — pre-open
- `12:07 WIB` — midday
- `16:47 WIB` — after close

GitHub schedule time is nominal; actual provider observation timestamp remains authoritative.

## Storage remediation

R2 remains private durable storage. V2 hot path writes:

1. one immutable raw Stream response per ticker;
2. one normalized JSONL observation object per successful ticker response;
3. one run manifest;
4. the exact IDX stock-summary source response used to construct the runtime universe.

The normal R2 path uses conditional immutable PUT semantics and does **not** immediately GET every object back. Existing-object collisions are checked against stored SHA-256 metadata. Per-post canonical objects are removed from the hot path; post `first_seen` is derived offline as the minimum observed timestamp across immutable observations.

## Zapi envelope remediation

Live GitHub Actions evidence showed that the current Zapi REST response for `finance:idx/stock-summary` adds an outer project envelope:

- top-level keys: `data`, `project`, `timestamp`;
- the actual documented IDX stock-summary payload is nested inside the outer `data` object.

The V2 cloud runner now preserves the **exact outer response bytes** for provenance while exposing the nested finance payload to the stock-summary validator.

This is an execution/schema adaptation only. It does not alter universe ranking logic or use outcomes.

## End-to-end cloud smoke evidence

Temporary validation PR: `#34` (closed without merge after evidence)  
Workflow run: `32450648278`  
Smoke job: `96678410979`

Result:

- source session: `2026-08-20`;
- selected universe: top `5` for bounded validation only;
- planned Stream calls: `5`;
- completed Stream calls: `5`;
- successful responses: `5/5`;
- response classifications: `OK=5`;
- normalized post observations: `150`;
- run ID: `2026-08-21_observable_validation_c12c95b65481cfa9`;
- universe SHA-256: `c12c95b65481cfa95f23d06dd5fb7bde89eb82eade3dbc0c54817dd4ee1d995a`;
- manifest SHA-256: `0d9e4ccc3ea224aeae5e396f86d627f64fe6708e06d35c7907df1157c2118bbe`;
- GitHub Actions secrets were redacted in logs;
- no model, sentiment, target, outcome, O2, or forward-counter access/mutation.

The smoke proves the intended cloud path can execute end-to-end:

`GitHub Actions -> Zapi IDX universe -> Zapi Stockbit Stream -> private R2 -> normalized observations + manifest`.

## Test state

The remediation PR CI reached `47 passed, 1 failed`; the only failure remains the pre-existing unrelated storage assertion `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` (fixture emits two conflicts while the assertion expects one). New Stockbit Stream V2 tests passed.

## Scientific boundary

- model fits = 0
- sentiment scoring = 0
- target/outcome access = 0
- IC calculations = 0
- V4-X1 mutation = 0
- O2 mutation = 0
- forward-counter mutation = 0
- existing local EOD/intraday scheduler mutation = 0

## Next operational state

Promote the envelope fix and permanent top-200 schedule to `main`. Remove temporary push-smoke permissions/triggers. The next routine scheduled slot may run normally from the default branch. Do not schedule the old 963-ticker V1 universe again.
