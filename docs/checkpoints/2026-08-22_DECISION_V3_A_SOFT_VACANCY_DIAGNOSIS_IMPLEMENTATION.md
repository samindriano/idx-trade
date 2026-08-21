# Decision V3 A-Soft vs A-Vacancy Diagnosis V1 — Implementation

Date: 2026-08-22 Asia/Jakarta

Status: `IMPLEMENTED_NOT_EXECUTED_INDEPENDENT_AUDIT_REQUIRED`

Branch: `research/idx-decision-v3-a-soft-vacancy-diagnosis-v1`

Frozen contract canonical SHA-256: `f3d549cafb04fb66735f7a668f6094b800c5354b148361c5d9ba4d9773a57663`.

The diagnosis is descriptive and outcome-blind. It compares the two observed Tier-A entry mechanisms from the already-rejected Decision V3 trajectory:

- `A_SOFT` = `SOFT_RANK_GAP_REPLACEMENT`;
- `A_VACANCY` = `TIER_A_VACANCY_FILL`.

Measured candidate evidence:

- current and previous consensus rank;
- current-minus-previous rank delta;
- t-2/t-3 rank where observable;
- consecutive Top10 and Top20 run lengths including entry;
- Top10/Top20 counts over the last three observed sessions.

Measured session context:

- severe/confirmed-mild/universe mandatory-exit counts before refill;
- whether entry occurs on a severe-exit session;
- consecutive-session cross-sectional Top10 and Top20 overlap;
- count of previous Top10 names collapsing beyond 50 or disappearing.

Outcome-blind structural durability labels are inherited from emitted V3 states/intents only:

- next-session `SEVERE_DETERIORATION_EXIT`;
- eventual severe exit among completed holding spells;
- one-session holding and duration summaries.

Fixed reporting strata are preregistered in the contract. No stratum is a proposed policy threshold. No matching/causal estimator, Decision V4 rule, wait/cash simulation, hypothetical portfolio/PnL, threshold sweep, returns/outcomes, protected-forward access, model refit, provider/network call, or paper/live activation is implemented.

The CLI checks the exact audit authorization token before contract or scientific artifact access. The quality-supply diagnosis manifest is hash-verified only as lineage evidence. Local execution remains unauthorized until exact-head CI and independent adversarial audit acceptance.