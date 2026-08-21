# Decision V3 Graded Evidence V2 — Independent Implementation Audit

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTATION_AUDIT_ACCEPTED_REPLAY_RUNNER_PREP_ONLY`

Reviewed controlling preregistration:

- branch `research/idx-decision-v3-graded-evidence-prereg-v2`;
- prereg HEAD `e9882e1b436f19e860d826a9c02a6bb3f1d46dcc`;
- rule ID `V4_X1_DECISION_V3_GRADED_EVIDENCE_V2`.

Reviewed implementation lineage:

- branch `research/idx-decision-v3-graded-evidence-implementation-v2`;
- validated code HEAD `c89ecb4f88e98cc23c140f15dee13ca423a92f5c`;
- documentation/claim HEAD after validation `acb01ea58ae3ae78969b00c8e473160fa2cd9d5d`;
- implementation PR #53.

This audit authorizes **replay-runner preparation only**. It does not authorize the historical 600-OOS Decision V3 replay.

## 1. Audit method

The implementation was reviewed adversarially against:

- human preregistration V2;
- machine profile `docs/specs/decision_v3_graded_evidence_v4_x1_profile_v2.json`;
- V2 frozen implementation boundary;
- V3 kill-diagnosis evidence boundary;
- exact PR #53 changed-file set;
- final GitHub Actions validation.

No Decision V3 historical replay, alternative Decision simulation, threshold sweep, returns/PnL, protected/fresh-forward outcomes, provider/network calls, H5/H10 rescue, model refit or alpha retune was used.

## 2. Lineage / immutability — PASS

Comparison from prereg HEAD to validated code HEAD shows only newly added V3 implementation/test/claim files. No Decision V2 engine, Decision V2 runner, frozen V2 result, alpha model, scoring code or existing scientific data artifact was modified.

Decision V2 remains an immutable rejected predecessor rather than being silently patched into V3.

## 3. Human prereg ↔ machine profile ↔ runtime profile — PASS

Runtime V4-X1 profile matches the frozen machine profile on:

- rule ID;
- target ceiling `10`;
- strong rank `<=10`;
- retention rank `<=20`;
- mild deterioration through rank `50`;
- severe deterioration starting rank `51`;
- soft-replacement gap `5`;
- vacancy priority `A_CORE -> B_NEAR -> C_DISTANT`;
- previous-absent Tier D prohibition;
- temporary underfill;
- bootstrap/no-preroll/no-fold-reset contract boundary.

All frozen V2 hard structural thresholds remain unchanged in the machine profile. No acceptance gate was relaxed to accommodate the new mechanism.

## 4. Incumbent state machine — PASS

Code and adversarial boundary tests confirm:

- current rank `<=10` -> `STRONG_HOLD`;
- `11..20` -> `ACCEPTABLE_HOLD`;
- `21..50` with previous rank `<=20` -> exactly one `MILD_DETERIORATION_PENDING_1` observation;
- `21..50` with previous rank `>20` -> `CONFIRMED_MILD_DETERIORATION_EXIT`;
- current rank `>50` -> immediate `SEVERE_DETERIORATION_EXIT`, irrespective of previous rank;
- absence from current universe -> immediate `UNIVERSE_EXIT`.

Exact boundaries `10/11/20/21/50/51` are tested. Severe rank 51 is not accidentally given grace. A Tier-C entrant that is rank 51 next session is immediately exited, as preregistered.

No strong or mild-pending incumbent is soft-replaceable. Only `ACCEPTABLE_HOLD` is eligible for the gap-5 path.

## 5. Challenger evidence tiers — PASS

Only non-held current-Top10 names become challengers.

Exact previous-rank boundary tests confirm:

- previous rank `<=20` -> Tier A `CORE`;
- `21..50` -> Tier B `NEAR`;
- `>50`, provided previous presence exists -> Tier C `DISTANT`;
- previous absence -> Tier D `NO_HISTORY`.

Tier D has no buy permission after bootstrap.

The implementation records explicit challenger observations and distinct buy reasons, which gives the future replay runner enough provenance to measure Tier-C usage without changing Decision behavior.

## 6. Vacancy priority and turnover permissions — PASS

Vacancy processing is deterministic:

1. mandatory incumbent exits;
2. retain non-exiting incumbents;
3. fill existing seats with Tier A;
4. then Tier B;
5. then Tier C;
6. only after vacancy filling, remaining Tier A may soft-replace an acceptable incumbent.

Tests with constrained one-, two-, and three-vacancy scenarios verify that B/C cannot leapfrog available stronger tiers.

Tier B and Tier C cannot manufacture a vacancy and cannot soft-replace. Tier D cannot fill or soft-replace. Therefore the implementation preserves the prereg distinction between weak evidence used to avoid an already-existing empty seat and evidence strong enough to create turnover.

## 7. Soft replacement — PASS

Only a remaining Tier-A challenger can soft-replace an incumbent currently ranked 11..20.

The gap condition is exactly inclusive:

`incumbent_rank - challenger_rank >= 5`.

An exact gap of 5 replaces; gap 4 does not. Matching remains deterministic: best remaining Tier-A challenger versus weakest eligible acceptable incumbent.

No gap parameter was changed or swept.

## 8. Same-session re-entry / collision — PASS

Challenger construction excludes every ticker held at the start of the session, even if that incumbent receives a mandatory sell later in the same Decision pass.

Thus a severe/confirmed/universe-exit incumbent cannot be sold and then immediately re-admitted as a challenger on the same session.

A separate buy/sell collision guard fails closed if an invalid path is ever introduced later.

## 9. Shadow-state provenance — REMEDIATED / PASS

Adversarial review found one non-scientific fail-closed weakness before sign-off:

- the generic low-level shadow-state validator rejected explicit wrong rule IDs but tolerated `rule_id=None` on a non-bootstrap state.

This did not alter Decision ranks, thresholds or actions, and no historical replay had occurred. The authorized V4-X1 adapter was hardened before audit acceptance:

- bootstrap may use the empty unbound state;
- every non-bootstrap V4-X1 call must carry exact rule ID `V4_X1_DECISION_V3_GRADED_EVIDENCE_V2`;
- unbound or mismatched V4-X1 runtime state fails closed.

A focused test now locks this behavior.

The generic low-level engine remains reusable, but the future scientific replay runner must route through the hardened V4-X1 adapter rather than call the low-level planner directly.

## 10. Determinism — PASS

The implementation normalizes state ordering, sorts candidates and targets deterministically by rank/ticker, and has row-order/state-order permutation tests.

No randomness or model fitting exists in the Decision engine.

## 11. Data-access boundary — PASS

The V4-X1 adapter validates the existing verified V4-X1 model ID/fingerprint and projects only:

- `ticker`;
- `rank_consensus`.

It does not reference H5/H10 values, raw alpha scores/margins, returns, PnL, outcome labels, sector/regime/volatility/liquidity, sizing, capital, execution or fill state.

The eventual historical runner must preserve an even stricter source boundary: parquet projection must read only the consensus-ranking columns needed to reconstruct the verified rank stream. This is a runner responsibility and remains closed until implemented/audited.

## 12. Session continuity boundary — EXPECTED RUNNER RESPONSIBILITY

The engine requires:

- non-bootstrap previous session;
- shadow state as-of date equal to that provided previous session;
- previous date strictly before current date.

It intentionally does not contain the authoritative 600-session calendar. Therefore it does not by itself prove that a supplied pair is the exact adjacent official frozen session.

This is not an implementation blocker. The future replay runner must independently enforce exact `(t-1,t)` adjacency against the pinned 600-date source, bootstrap only at index 0, no pre-roll and no fold reset.

## 13. Scientific risks deliberately left unresolved

The audit does not claim the policy will pass structural gates.

Two primary risks remain intentionally untouched:

### Tier-C delayed churn

A distant observed fresh Top10 can fill an already-empty seat and later become a normal incumbent. If these entries frequently collapse to rank >50 soon after entry, they can create delayed vacancy/exit cycles. This is the main Tier-C falsification risk.

### Severe-exit clustering

Immediate severe exits may concentrate sell/fill activity on sessions already experiencing rank instability. The kill diagnosis showed this is plausible.

Adding Tier-C-specific min-hold, cooldown, special grace, turnover caps or severity sub-bands now would create unpreregistered knobs. The audit therefore requires these risks to be **measured**, not patched, in the eventual one-shot replay.

## 14. Required future replay-runner diagnostics

Before any replay authorization, the runner/reporting contract must freeze and independently audit at least:

- all unchanged V2 churn/holding/rank/capacity hard gates;
- V3 correctness gates: zero target rank >50 after processing, zero second-consecutive 21..50 retention, zero post-bootstrap previous-absent entrants;
- entry counts by Tier A/B/C;
- vacancy fills by Tier A/B/C;
- Tier-C entry holding-spell distribution;
- Tier-C one-session holding share;
- Tier-C next-session state/rank distribution;
- Tier-C entries followed by next-session or later severe exits;
- replacements attributable to Tier-C entry -> later exit loops;
- severe-exit counts and clustering, including high-churn sessions;
- underfill and vacancy-days;
- six 100-session blocks and fold-boundary transitions without state resets;
- deterministic identical rerun on the same in-memory source;
- output fail-closed / immutable manifest behavior.

These diagnostics are descriptive. They may not create new post-hoc gates or rescue variants after seeing the replay.

## 15. Validation

Final implementation validation on code HEAD `c89ecb4f88e98cc23c140f15dee13ca423a92f5c`:

- GitHub Actions run #1120;
- `504 passed`;
- `26 warnings`;
- `0 failed`.

Warnings are unrelated existing pandas/NumPy and GitHub Actions Node deprecations.

## 16. Verdict

`IMPLEMENTATION_AUDIT_ACCEPTED_REPLAY_RUNNER_PREP_ONLY`

The exact Decision V3 Graded Evidence V2 implementation is accepted as faithful enough to the frozen preregistration to proceed to **structural replay-runner + reporting implementation**.

This verdict does **not** authorize historical Decision V3 execution.

Next allowed work:

1. freeze a V3 structural replay/reporting contract using the same exact 600-OOS source and unchanged hard gates;
2. implement the runner with strict consensus-only source projection and exact session continuity;
3. independently audit the runner and gate mapping;
4. only after that audit may exactly one local 600-OOS Decision V3 replay be authorized.
