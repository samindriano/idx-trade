# Decision V3 A Admission Mechanism Diagnosis V1 — Implementation

Status: IMPLEMENTED_AWAITING_EXACT_HEAD_CI_AND_AUDIT

This is the final outcome-blind descriptive mechanism diagnosis before returning to Decision V4 design.

Parent: consumed same-session diagnosis manifest `bb2b38696d83629ace4a50609eb042e42951086fda27c7d9f39ad50f25f87902`.

Frozen contract canonical SHA-256: `5add7fb9b18ace3347aff24025f49425ab8ee8fc08c7b34610491b477bc0c4ed`.

The runner reads only the parent `MANIFEST.json` and `paired_entries.csv`. It restricts primary analysis to the 204 observed A_SOFT entries in the paired-session population and reports threshold-free soft-rank-gap associations with next-session severe state, eventual severe state among completed spells, completed holding duration, fixed pre-existing candidate-evidence strata, and same-session discordant-pair concordance.

No threshold search/sweep or numeric successor cutoff is produced. The diagnosis cannot identify the causal effect of the existing >=5 hurdle because all A_SOFT entries already passed it.

Forbidden: Decision V4 implementation/replay, alternative-policy simulation, portfolio/PnL, returns, protected/fresh-forward access, refit/retune, provider/network calls, causal claims, paper/live activation.

Stop rule: once the one-shot result is consumed, stop mechanism diagnosis and return to Decision V4 design/brainstorming.
