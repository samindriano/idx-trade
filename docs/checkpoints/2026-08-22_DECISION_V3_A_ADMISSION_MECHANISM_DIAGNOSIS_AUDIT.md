# Decision V3 A Admission Mechanism Diagnosis V1 — Independent Adversarial Audit

Verdict: `A_ADMISSION_MECHANISM_DIAGNOSIS_RUNNER_AUDIT_ACCEPTED_SINGLE_LOCAL_EXECUTION_AUTHORIZED`

Reviewed implementation HEAD: `3a51d002c23b7ae1756b1ea766727cbaa7362631`.

Frozen contract canonical SHA-256: `5add7fb9b18ace3347aff24025f49425ab8ee8fc08c7b34610491b477bc0c4ed`.
Pinned parent same-session manifest SHA-256: `bb2b38696d83629ace4a50609eb042e42951086fda27c7d9f39ad50f25f87902`.

CI run #1155: **551 passed, 38 warnings, 0 failed**.

## Audit findings

- Runner checks the authorization token before contract or local scientific artifact access.
- Scientific inputs are parent-only: the already-consumed same-session `MANIFEST.json` and its hash-pinned `paired_entries.csv`.
- No historical source, Decision planner, alternative portfolio, return/PnL, provider/network, model refit, protected/fresh-forward, or paper/live path exists in this runner.
- Parent status, scientific boundary, artifact hash, entry counts (204 A_SOFT / 223 A_VACANCY), and 151 paired sessions fail closed.
- Primary analysis is restricted to observed A_SOFT entries. A_VACANCY is reference-counted only; no synthetic vacancy gap or counterfactual admission rule is derived.
- Primary gap statistics are threshold-free. No new gap bins, sweep, rescue cutoff, or numeric successor threshold are emitted.
- Next-session and eventual-severe denominators respect observability/completion. Right-censored spells are excluded from completed-duration/eventual analysis.
- The same-session discordant-pair diagnostic compares observed A_SOFT entries only and reports ties explicitly.
- Direction convention is explicit: a negative `severe_minus_nonsevere_mean_gap` is consistent with larger gap being associated with durability.
- Interpretation remains descriptive. All A_SOFT entries already passed the existing >=5 hurdle, so this analysis cannot estimate the causal effect of that hurdle itself.

## Authorization

Exactly one local descriptive execution is authorized on reviewed HEAD `3a51d002c23b7ae1756b1ea766727cbaa7362631` with token:

`DECISION_V3_A_ADMISSION_MECHANISM_DIAGNOSIS_AUDIT_ACCEPTED_V1`

No Decision V4 implementation or replay is authorized. After the result is consumed, the frozen stop rule requires returning to Decision V4 design/brainstorming rather than launching another mechanism diagnosis automatically.
