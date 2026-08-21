# Decision V3 Graded Evidence V2 — Implementation Result

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTED_TESTED_NO_HISTORICAL_REPLAY_INDEPENDENT_AUDIT_REQUIRED`

Controlling preregistration: `research/idx-decision-v3-graded-evidence-prereg-v2` / `e9882e1b436f19e860d826a9c02a6bb3f1d46dcc`.

Adversarial prereg audit: PR #52 / verdict `PREREG_V2_REVIEW_ACCEPTED_IMPLEMENTATION_ONLY_REPLAY_NOT_AUTHORIZED`.

Validated implementation code HEAD: `8669179dca4314e7be93e834f19110dd92511bf0`.

## Implemented

- new generic engine: `src/idx_trade/decision_v3_graded_evidence.py`;
- V4-X1 adapter/profile binding: `src/idx_trade/v4_x1_decision_v3_graded_evidence.py`;
- Decision V2 implementation remains untouched;
- incumbent states exactly implement strong / acceptable / one-session mild 21..50 pending / confirmed mild exit / immediate severe >50 exit / universe exit;
- challenger evidence tiers exactly implement A Core, B Near, C Distant residual-vacancy-only, D No-history forbidden;
- vacancy fill priority is A -> B -> C;
- only remaining Tier-A candidates may soft-replace acceptable incumbents under unchanged inclusive gap-5;
- Tier B/C/D cannot create paired soft replacements;
- previous-absent Tier D cannot enter after bootstrap;
- shadow state is rule-bound and advances only from a Decision V3 plan;
- deterministic row/state-order handling;
- no same-session sell/rebuy path for names held at session start;
- explicit `FULL` / `UNFILLED_NO_QUALIFIED_CHALLENGER` capacity state.

## V4-X1 boundary

The adapter projects only `ticker` and `rank_consensus` from the verified V4-X1 score session. It does not consume H5/H10 values, raw alpha magnitude, returns/PnL, outcomes, sector/regime/liquidity, sizing, execution or fill state.

Runtime profile is tested against `docs/specs/decision_v3_graded_evidence_v4_x1_profile_v2.json`, while that frozen machine artifact intentionally retains status `PREREGISTERED_V2_NOT_IMPLEMENTED_NOT_REPLAYED`.

## Tests

Final GitHub Actions run #1116 on validated code HEAD:

- `491 passed`;
- `26 warnings`;
- `0 failed`.

Warnings are pre-existing pandas/NumPy and GitHub Actions Node deprecation warnings unrelated to Decision V3.

Adversarial coverage includes:

- exact bootstrap/no-preroll;
- mild boundary and one-session grace;
- severe rank 51+ immediate exit;
- A -> B -> C vacancy priority with constrained vacancy counts;
- B/C forbidden from soft replacement;
- Tier D forbidden for vacancy fill and soft replacement;
- inclusive gap-5 vs rejected gap-4;
- Tier-C entry followed by normal mild incumbent treatment;
- Tier-C entry followed by next-session severe exit without grace;
- universe disappearance;
- row/state permutation determinism;
- rule-id shadow binding;
- V4-X1 machine-profile parity and unchanged structural gates.

## Scientific boundary

No Decision V3 historical replay has been executed.

No alternative policy, threshold, confirmation length, gap, H5/H10 rescue, return/PnL inspection, protected/fresh-forward access, provider/network call, model refit or alpha retune occurred.

Historical replay remains unauthorized until a separate independent implementation audit accepts this exact implementation lineage. The audit must treat Tier-C delayed churn and severe-exit clustering as unresolved scientific risks to be measured by the eventual structural replay, not patched before it.
