# Decision V3 Graded Evidence — Kill-Diagnosis Preregistration

Date: 2026-08-21 Asia/Jakarta

Status: `PREREGISTERED_DIAGNOSIS_NOT_IMPLEMENTED_NOT_RUN`

## Purpose

The adversarial review of Decision V3 Graded Evidence returned `PREREG_REVIEW_NOT_ACCEPTED_ADDITIONAL_MECHANISM_DIAGNOSIS_REQUIRED`.

This diagnostic pass exists only to test whether the exact V3 mechanism rationale survives broader outcome-blind rank evidence. It must not simulate Decision V3 or any alternative Decision policy.

Pinned upstream identities:

- V2 structural manifest SHA-256: `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`
- V2 structural plan digest: `51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4`
- V2 failure-diagnosis manifest SHA-256: `bada04d8403457d4456653fad66d9119b80349f65e13be9cff911a886c31af06`
- historical score manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`
- historical score SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`
- exact source: `600` sessions / `172,697` score rows

## Allowed inputs

Only:

1. the frozen V2 structural ledgers;
2. the exact pinned historical `rank_consensus` stream;
3. deterministic reporting strata already used by the prior diagnosis.

Forbidden:

- Decision V3 execution or replay;
- alternative threshold/rule simulation;
- returns/PnL;
- H5/H10 internals;
- protected/fresh-forward outcomes;
- provider/network calls;
- model refit/retune;
- parameter sweeps.

## Diagnostic A — Global fresh-current-Top10 persistence

Population: every non-bootstrap session `t` and every current Top-10 ticker that was not in the V2 shadow target at the start of session `t`.

For each observation record:

- current index/date/block;
- ticker;
- current rank;
- immediately previous-session rank or previous absence;
- previous-rank reporting stratum: `LE20`, `21_30`, `31_50`, `51_100`, `101_200`, `GT200`, `ABSENT`;
- next-session rank/presence when index <599;
- next Top-10 / Top-20 persistence.

Report overall and by previous-rank stratum, plus six fixed 100-session blocks.

Purpose: test whether near-history fresh Top-10 persistence generalizes beyond the V2-underfilled subset.

## Diagnostic B — Severe-collapse same-session replacement context

Population: every frozen V2 incumbent observation with state `EXIT_PENDING_1` and current rank `>50`.

For each event record:

- session index/date/block/ticker;
- previous and current rank;
- next-session recovery to `<=20` when evaluable;
- V2 transition replacement count and whether high-churn `>=3`;
- number of current unheld Top-10 candidates with previous rank `<=20` (`core_supply`);
- number with previous rank `21..50` (`near_supply`);
- number with previous rank `>50` (`distant_supply`);
- number previously absent;
- whether `core_supply >= 1`;
- whether `core_supply + near_supply >= 1`.

This is descriptive only. The event is not exited and no candidate is inserted.

Purpose: quantify whether severe-collapse observations typically occur when replacement evidence exists, and whether they cluster with already-high churn.

## Diagnostic C — Session-level V2-underfill supply decomposition

Population: the exact `135` frozen V2 sessions with `UNFILLED_NO_QUALIFIED_CHALLENGER`.

For each session record:

- unfilled slots;
- current unheld Top-10 supply with previous rank `<=20`;
- current unheld Top-10 supply with previous rank `21..30`;
- previous rank `31..50`;
- previous rank `51..100`;
- previous rank `101..200`;
- previous rank `>200`;
- previous absence;
- `core + 21..50` supply;
- whether `core + 21..50 >= vacancies`.

Purpose: directly test the proposed provisional Tier-B supply claim at session level without simulating admission.

## Reporting boundary

The existing bins are descriptive strata, not candidate thresholds. Results may support or weaken the preregistered V3 mechanism rationale, but they do not authorize changing rank 50 or selecting a different threshold in this run.

Terminal index 599 has no frozen next session and is excluded only from next-session rate denominators. Actual ticker absence on an existing next frozen session counts as non-persistence.

## Required outputs

- `summary.json`
- `global_fresh_top10_persistence.csv`
- `severe_collapse_replacement_context.csv`
- `underfill_supply_decomposition.csv`
- `block_summary.csv`
- `MANIFEST.json`

Output directory and staging directory must fail closed if already present.

## Completion status

Successful execution reports only:

`COMPLETE_OUTCOME_BLIND_DECISION_V3_KILL_DIAGNOSIS`

There is no ACCEPT/REJECT gate in the diagnostic runner. Interpretation and any revised V3 preregistration happen only after the frozen result is reviewed.

## Authorization boundary

This preregistration authorizes implementation and audit of the diagnostic runner only. Local execution remains locked until the implementation has passed full tests and an independent audit.