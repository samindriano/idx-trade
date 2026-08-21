# Decision V3 A Same-Session Diagnosis Implementation

Status: `IMPLEMENTED_REVIEW_REQUIRED_EXECUTION_LOCKED`

Branch: `research/idx-decision-v3-a-same-session-diagnosis-v1`

This diagnosis is restricted to sessions in the already-produced A-soft-vs-A-vacancy artifact where both `A_SOFT` and `A_VACANCY` entries occurred. Session context is therefore shared by construction; the diagnosis compares candidate evidence and structural next/eventual severe incidence within that paired-session population.

Frozen contract canonical SHA-256: `6089bc20592a494820fdf9e63627536b4443577a22aeea13eaa2fd6fa7070953`.

Pinned parent manifest SHA-256: `d17f009df762678734d3f073419d44b707d55ba6dd3f25627e332438c9a7c224`.

Inputs are limited to `MANIFEST.json` and `a_entry_diagnosis.csv` from the consumed parent diagnosis. The runner verifies both the parent manifest hash and the CSV hash recorded inside that manifest.

Outputs are descriptive only: paired entries, equal-session summaries, fixed candidate-evidence strata, and summary/manifest. No Decision V4 implementation/replay, returns/PnL, protected outcomes, threshold sweep, causal claim, provider/network call, model refit, or paper/live activation is present.

Execution remains locked until exact-head CI and independent audit accept the runner.
