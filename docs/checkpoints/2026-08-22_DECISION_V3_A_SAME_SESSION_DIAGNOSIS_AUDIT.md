# Decision V3 A Same-Session Diagnosis Audit

Verdict: `A_SAME_SESSION_DIAGNOSIS_RUNNER_AUDIT_ACCEPTED_SINGLE_LOCAL_EXECUTION_AUTHORIZED`

Reviewed implementation HEAD: `cd4c8e1421e26243183dda840269d75288c0787a`.

Frozen contract canonical SHA-256: `6089bc20592a494820fdf9e63627536b4443577a22aeea13eaa2fd6fa7070953`.

Pinned parent diagnosis manifest SHA-256: `d17f009df762678734d3f073419d44b707d55ba6dd3f25627e332438c9a7c224`.

CI run #1152: **546 passed, 38 warnings, 0 failed**.

Audit checks:
- execution token is checked before contract or local scientific artifacts are touched;
- parent manifest SHA is exact and the parent `a_entry_diagnosis.csv` is re-hashed against the parent manifest artifact pin;
- no historical rank source, structural replay source, provider/network, Decision planner, Decision V4 implementation/replay, model refit, return/PnL, or protected/fresh-forward outcome path is used;
- paired sessions require both `A_SOFT` and `A_VACANCY` entries;
- session context is asserted constant within each paired session;
- next-session and eventual severe denominators exclude unobservable/right-censored observations appropriately;
- both entry-weighted and equal-session-weighted comparisons are reported;
- fixed candidate-evidence strata are descriptive reporting bins only;
- same-session restriction removes session-level context differences but does not remove selection-mechanism confounding, so no causal claim is authorized;
- output directory and staging directory are fail-closed and artifacts are hashed into a manifest.

Exactly one local descriptive execution is authorized on the reviewed implementation HEAD with a fresh output directory. No Decision V4 policy or replay is authorized by this audit.
