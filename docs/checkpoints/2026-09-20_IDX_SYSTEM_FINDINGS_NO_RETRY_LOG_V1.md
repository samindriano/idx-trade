# IDX System Findings and No-Retry Log V1

Date: 2026-09-20  
Lane: isolated `codex/alpha-available-data-20260919`

This is a durable system-research log. “No retry” means do not repeat the same probe expecting a different result without changing the contract, source, or evidence class. It does not prohibit an authorized isolated remediation test later.

| ID | Finding | Evidence | Why it matters | No-retry conclusion / reopen condition |
|---|---|---|---|---|
| SYS-EXEC-001 | Positive partial buy is not persisted as pending. | EOD close 1,000 → planned 5,000; Open 2,000 → filled 2,500; pending empty; next session no buy intent; reload preserves 2,500. | Silent underexposure and lost residual obligation across sessions. | Do not rerun the same gap case as if it were unresolved. Reopen only after quantity-aware obligation semantics change. |
| SYS-EXEC-002 | Positive partial-buy loss is trigger-general, including resolved paired replacement. | Four synthetic rows: capacity/Open change 5,000→1,200; fee boundary 1,000→900; stamp-threshold boundary 10,000→9,900; paired replacement 5,000→1,200. All had empty pending buys, equal target membership, equal cold-reload hashes, and no next-session retry. | The defect is a sizing→execution→pending→Decision contract split, not a single market-gap edge case; cost and replacement paths can silently underdeliver while seat count, NAV/cash arithmetic, and hashes remain internally valid. | Do not repeat the four trigger shapes as separate bugs. Reopen only with a different state owner, quantity-aware artifact, multi-session accounting evidence, or authorized remediation. |
| SYS-DEC-001 | Decision V2 ten-seat shadow treats a partially filled seat as fully satisfied. | Ten target names planned at 5,000 each; `T01` filled 2,400 due capacity, nine names filled 5,000; next plan reports `capacity_state=FULL`, `unfilled_slots=0`, zero effective buys and zero sizing entries. | Seat count and shadow ticker membership can suppress residual repair and make exposure/concentration appear complete. | Do not rerun another ten-seat variant without changing the quantity contract. Reopen with quantity-aware shadow state and residual-aware seat capacity. |
| SYS-CA-001 | Projected CA sizing state is incompatible with raw execution parent hash when payment settles on decision date. | Raw cash 1,000,000 vs projected 1,005,000; execution fails `EXECUTION_V1_STATE_HASH_MISMATCH`. | Valid dividend timing case is blocked before fills. | Do not retry live execution. Reopen with an explicit settle-before-prepare or projected-state hash policy. |
| SYS-ID-001 | `replacement_peer` alias can block a buy after canonical sell full-fills. | Sell `AAA` full-fills; buy peer `AAA.JK` remains pending. | Replacement liveness and portfolio transition are distorted. | Do not retry with provider aliases. Reopen only with shared identity normalization and permutation tests. |
| SYS-STATE-001 | Fractional shares are silently truncated by execution state normalization/reload. | `100.9` accepted as `100`; whole-lot check then passes. | State quantity can change without an explicit schema error. | Do not treat hash equality after reload as quantity correctness. Reopen with pre-cast integer validation. |
| SYS-CA-REP-001 | Malformed optional split/dividend values become apparent no-events. | `"2:1"`/`"bad"` → `NaN → fillna(0)`; CA flags false. | CA completeness can be overstated. | Do not retry fallback acquisition from this lane. Reopen with invalid/unknown CA schema policy. |
| SYS-STORAGE-001 | Duplicate dates have asymmetric behavior. | Existing duplicates raise ambiguous-Series `ValueError`; incoming duplicates silently keep last. | Revision lineage and data integrity are not uniform. | Do not rerun duplicate probes without source contract change. Reopen with typed duplicate rejection/provenance. |
| SYS-EVAL-001 | Pure evaluator and final gate use different ticker identity normalization. | Pure metrics accept `ALIS`/`ALIS.JK`; gate rejects normalized collision; 120 tests pass. | Research measurements can differ from admission behavior. | Do not interpret green pure metrics as gate-compatible. Reopen with one shared identity function. |
| SYS-UNIVERSE-001 | Universe warmup/era identity boundary is unproven. | Pre-listing rows count toward warmup; aliases and overlapping eras accepted in synthetic probes. | Eligibility and historical identity can distort downstream ranks. | Do not patch canonical universe from this lane. Reopen with explicit era/identity policy. |

## Negative results worth retaining

- Existing focused tests are valuable regression evidence but are not system closure evidence.
- Hash chains can preserve a semantically incomplete state; internal integrity is not equivalent to economic completeness.
- Fail-closed behavior can still be operationally wrong when the rejected state was the only valid path, as in payment-on-decision-date sizing.
- The current defects were reproducible without protected outcomes or new provider data.
