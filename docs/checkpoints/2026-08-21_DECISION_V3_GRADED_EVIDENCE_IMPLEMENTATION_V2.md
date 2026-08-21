# Decision V3 Graded Evidence V2 — Implementation Result

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTED_TESTED_AUDIT_HARDENED_NO_HISTORICAL_REPLAY`

Controlling preregistration: `research/idx-decision-v3-graded-evidence-prereg-v2` / `e9882e1b436f19e860d826a9c02a6bb3f1d46dcc`.

Adversarial prereg audit: PR #52 / verdict `PREREG_V2_REVIEW_ACCEPTED_IMPLEMENTATION_ONLY_REPLAY_NOT_AUTHORIZED`.

Validated implementation code HEAD: `c89ecb4f88e98cc23c140f15dee13ca423a92f5c`.

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
- deterministic row/state-order handling;
- no same-session sell/rebuy path for names held at session start;
- explicit `FULL` / `UNFILLED_NO_QUALIFIED_CHALLENGER` capacity state.

## V4-X1 scientific boundary

The V4-X1 adapter projects only `ticker` and `rank_consensus` from the verified score session. It does not consume H5/H10 values, raw alpha magnitude, returns/PnL, outcomes, sector/regime/liquidity, sizing, execution or fill state.

Non-bootstrap V4-X1 state is fail-closed and must carry the exact `V4_X1_DECISION_V3_GRADED_EVIDENCE_V2` rule ID. An adversarial implementation review identified that the generic low-level shadow-state validator tolerated an unbound (`rule_id=None`) non-bootstrap state. Rather than change scientific semantics, the authorized V4-X1 adapter was hardened to reject any such unbound runtime state. Bootstrap remains the only allowed unbound empty state. This remediation happened before any historical replay.

The generic low-level engine still rejects an explicitly mismatched non-null rule ID. The eventual historical runner must route through the V4-X1 adapter and may not bypass this runtime binding.

Runtime profile is tested against `docs/specs/decision_v3_graded_evidence_v4_x1_profile_v2.json`, while that frozen machine artifact intentionally retains status `PREREGISTERED_V2_NOT_IMPLEMENTED_NOT_REPLAYED` and `source.replay_authorized=false`.

## Tests

Final GitHub Actions run #1120 on validated code HEAD:

- `504 passed`;
- `26 warnings`;
- `0 failed`.

Warnings are pre-existing pandas/NumPy and GitHub Actions Node deprecation warnings unrelated to Decision V3.

Adversarial coverage includes:

- exact bootstrap/no-preroll;
- exact incumbent boundaries 10/11/20/21/50/51;
- exact challenger previous-rank boundaries 20/21/50/51;
- mild one-session grace;
- severe rank 51+ immediate exit;
- A -> B -> C vacancy priority with constrained vacancy counts;
- B/C forbidden from soft replacement;
- Tier D forbidden for vacancy fill and soft replacement;
- inclusive gap-5 vs rejected gap-4;
- Tier-C entry followed by normal mild incumbent treatment;
- Tier-C entry followed by next-session severe exit without grace;
- universe disappearance;
- row/state permutation determinism;
- rule-id mismatch rejection;
- V4-X1 rejection of unbound non-bootstrap state;
- V4-X1 machine-profile parity and unchanged structural gates.

## Runner responsibility not implemented here

The state machine validates chronological session order and requires the shadow state to be as-of the provided previous session. It does **not** itself know the pinned 600-session official ledger. The future structural replay runner must independently enforce:

- exact 600 frozen dates / 172,697 rows and source hashes;
- exact official `(t-1,t)` adjacency;
- bootstrap only index 0;
- no pre-roll;
- continuous state with no fold resets;
- V4-X1 adapter routing with bound state;
- consensus-only historical source projection;
- all frozen V2 hard acceptance gates plus V3 correctness gates;
- Tier-C-specific diagnostics, including entry count, holding duration, one-session share, next-state, next severe exit and downstream replacement contribution.

## Scientific boundary

No Decision V3 historical replay has been executed.

No alternative policy, threshold, confirmation length, gap, H5/H10 rescue, return/PnL inspection, protected/fresh-forward access, provider/network call, model refit or alpha retune occurred.

Tier-C delayed churn and severe-exit clustering remain unresolved scientific risks for the eventual one-shot structural replay; they were not patched away during implementation.
