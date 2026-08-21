# V4-X1 Decision V1 — Temporal Persistence Diagnosis Result

Date: 2026-08-21 Asia/Jakarta
Status: `COMPLETE_OUTCOME_BLIND_TEMPORAL_PERSISTENCE_DIAGNOSIS`

## Source identity

Operator-supplied runtime completed against the exact frozen clean V4-X1 historical OOS replay:

- source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`
- source score SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`
- rows: `172,697`
- dates: `600`
- runtime manifest SHA-256: `23c877e366513c6d706995ae1a49cf0d81578ad812ed102cb1196bc745a548b7`
- focused test evidence supplied by operator: `2 passed`

No realized returns, target ledger, historical PnL, Decision V2 parameter test/simulation, model refit/retune, provider/network call, or protected/fresh-forward access occurred.

## Main result

### D1 — Temporal persistence is strongly informative

For all current Top-10 rows:

- next-session `rank >20`: `33.99%`
- next-session Top-10 survival: `47.98%`
- next-session Top-20 survival: `66.01%`
- any `rank >20` within 3 sessions: `61.06%`

For **fresh Top-10 names coming from prior rank >20 or absence**:

- next-session `rank >20`: `54.80%`
- next-session Top-10 survival: `30.20%`
- next-session Top-20 survival: `45.20%`
- any `rank >20` within 3 sessions: `83.01%`

For current Top-10 names that were **already Top-10 in the prior session** (`TOP10_RUN_GE2`):

- next-session `rank >20`: `20.67%`
- next-session Top-10 survival: `61.93%`
- next-session Top-20 survival: `79.33%`
- any `rank >20` within 3 sessions: `46.68%`

For current Top-10 names with a **3-session Top-10 run** (`TOP10_RUN_GE3`):

- next-session `rank >20`: `15.17%`
- next-session Top-10 survival: `68.47%`
- next-session Top-20 survival: `84.83%`
- any `rank >20` within 3 sessions: `37.65%`

Therefore the instability is not homogeneous. A one-day fresh Top-10 spike is dramatically less durable than a Top-10 name with prior persistence.

### D2 — Cross-head agreement adds further information but does not replace persistence

For current Top-10 with both H5 and H10 individually <=10:

- next-session `rank >20`: `24.70%`
- next-session Top-10 survival: `60.24%`
- next-session Top-20 survival: `75.30%`

For current Top-10 that was also prior-session Top-10 **and** currently has both heads <=10:

- next-session `rank >20`: `15.80%`
- next-session Top-10 survival: `69.43%`
- next-session Top-20 survival: `84.20%`
- any `rank >20` within 3 sessions: `38.65%`

This is consistent with the earlier head-entry diagnosis: head agreement is useful, but the strongest discrimination comes from temporal persistence plus agreement rather than agreement alone.

### D3 — A pure persistent-only 10-name portfolio would face capacity shortages

Candidate counts within current Top-20:

`CURRENT_TOP20_WITH_TOP20_RUN_GE2`:

- mean candidates/date: `11.095`
- median: `12`
- p10: `6`
- minimum: `0`
- dates with >=10 candidates: `67.67%`

`CURRENT_TOP20_WITH_TOP20_RUN_GE3`:

- mean: `7.675`
- median: `8`
- p10: `2`
- minimum: `0`
- dates with >=10 candidates: `38.83%`

`CURRENT_TOP20_PREV_TOP20_BOTH_HEADS_LE20`:

- mean: `7.462`
- median: `8`
- dates with >=10 candidates: `36.67%`

Therefore temporal confirmation cannot simply be imposed as a hard rule requiring all ten portfolio names to satisfy a strict persistence filter every day. A stateful portfolio policy must be able to retain incumbents, delay replacement, or otherwise avoid forcing immediate full-slot replenishment when confirmed candidates are scarce.

## Interpretation

The evidence now favors the hypothesis that frozen V4-X1 is **not uniformly unusable as a portfolio alpha**. The extreme-rank process contains a highly unstable fresh-spike component, but persistence materially identifies a more durable subset.

This supports keeping V4-X1 frozen and addressing the translation layer first. It does **not** prove that a stable Decision V2 preserves realized alpha; no return/PnL evidence was accessed here.

The immediate scientific problem is now narrower:

1. Decision V1 admits fresh Top-10 spikes too readily;
2. mandatory exits force immediate replenishment, amplifying the unstable fresh-spike population;
3. cross-head agreement is useful but insufficient by itself;
4. temporal persistence is a strong stability signal;
5. strict persistent-only eligibility lacks enough capacity for ten names on many dates.

## Decision / next action

Do **not** reopen or retune V4-X1 alpha yet.

The next action should be a separately named/preregistered **Decision V2 mechanical challenger** built around asymmetric, stateful confirmation rather than a parameter sweep. The preregistration should explicitly address:

- fresh-entry confirmation / spike avoidance;
- incumbent retention rather than forced immediate replenishment;
- optional use of H5/H10 agreement as supporting evidence;
- deterministic behavior when fewer than ten confirmed new candidates exist;
- an emergency deterioration rule distinct from ordinary rank noise.

Decision V2 must first be evaluated outcome-blind on structural metrics only. Realized-return/PnL comparison, if later authorized, must be a separate gate and must not be used to choose V2 mechanics retrospectively.

## What is not supported

Do not infer from this result that:

- V4-X1 needs immediate replacement by a new alpha model;
- a 2- or 3-session minimum holding period is automatically correct;
- every entry must satisfy strict 2- or 3-session persistence;
- H10-only veto is sufficient;
- a fixed rank-threshold widening solves the problem;
- the stability-conditioned subset necessarily preserves the historical IC/PnL.
