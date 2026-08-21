# Decision V2 Minimal — Independent Implementation Audit

Date: 2026-08-21 Asia/Jakarta

Status: `REMEDIATION_REQUIRED_BEFORE_600_OOS_REPLAY`

Audited implementation HEAD: `942095583e1921ae8d3daaf0fffe833317626465`

Parent preregistration branch: `research/idx-decision-v2-minimal-prereg-v1`

Implementation PR: `#41`

## Verdict

The implemented policy mechanics match the frozen Decision V2 Minimal preregistration in all material decision rules reviewed. No hidden H5/H10 rescue logic, score smoothing, parameter retuning, return/PnL dependence, or V4-X1-specific model-internal branching was found.

One explicit preregistration observability requirement is not yet implemented and must be remediated before the exact 600-OOS structural replay.

## Rule-by-rule audit

PASS:

- bootstrap exactly once from empty state using current Top-10 and no preroll;
- generic engine consumes rank/state only;
- V4-X1 adapter is separate from the generic engine;
- non-held entry requires current rank <=10 and previous-session rank <=20;
- prior absence or prior rank >20 makes a current Top-10 challenger unconfirmed;
- current rank <=10 is `STRONG_HOLD` and not soft-replaceable;
- current rank 11..20 is `ACCEPTABLE_HOLD` and may be soft-replaced only by a qualified challenger with rank advantage >=5;
- first current observation >20 after prior <=20 becomes `EXIT_PENDING_1` and is retained;
- current >20 with previous >20 becomes `CONFIRMED_EXIT`;
- recovery to <=20 clears effective exit-pending behavior;
- current-universe absence exits immediately;
- confirmed/universe exits are removed before vacancy filling;
- vacancies are filled only by qualified challengers;
- fresh/unconfirmed Top-10 names are not used as forced backfill;
- temporary underfill is mechanically allowed;
- soft replacement uses the frozen gap-5 threshold;
- no minimum holding period, cooldown, H5/H10 veto, raw-score rule, smoothing, turnover cap, regime rule, sizing, execution, returns, or PnL is present;
- target cannot exceed 10 names;
- row-order determinism is explicitly tested;
- shadow state must align to the supplied previous score-session date;
- V4-X1 adapter requires verified frozen model ID/fingerprint lineage;
- frozen profile constants are tested against the preregistered JSON.

## Required remediation R1 — explicit underfill capacity state

The preregistration requires that, when fewer qualified challengers exist than vacancies, the Decision output record explicit capacity state:

`UNFILLED_NO_QUALIFIED_CHALLENGER`

Current implementation exposes only numeric `unfilled_slots` in `DecisionV2Plan`. The mechanical behavior is correct, but the named state required by the frozen observability contract is absent.

Required fix:

- add an explicit deterministic capacity-state field to the Decision output;
- full target should report a neutral/full state;
- underfilled non-bootstrap target caused by insufficient qualified challengers must report exactly `UNFILLED_NO_QUALIFIED_CHALLENGER`;
- add focused tests covering both full and underfilled cases;
- do not change any Decision threshold or behavior while making this fix.

This is an engineering/observability remediation, not a scientific policy change.

## Replay invariant R2 — exact previous-session adjacency

The generic engine verifies that the supplied previous session is earlier than the current session and that shadow-state date equals that supplied previous session. It cannot independently prove that the pair is the immediately previous official score session.

The preregistration requires the immediately previous official score/rank table.

This does not require changing the generic engine. The future 600-OOS replay runner must enforce:

- exact pinned 600-date score-session ledger;
- iteration strictly by adjacent ledger index `(t-1, t)`;
- no skipped score session;
- no fold reset;
- no pre-roll;
- bootstrap only at ledger index 0;
- fail closed if session order/count/identity differs from the pinned source artifact.

## Non-blocking hardening note

`DecisionV2ShadowState` currently carries source identity but not profile/rule identity. This is acceptable for the one-profile, empty-bootstrap historical replay if the runner pins the profile and never imports external state. Before future prospective multi-profile/reusable deployment, state lineage should be bound to the Decision rule/profile identity to prevent accidental cross-profile state reuse.

This is not a blocker for the controlled historical replay after R1 is fixed and R2 is enforced by the runner.

## Validation evidence

GitHub Actions on implementation HEAD `942095583e1921ae8d3daaf0fffe833317626465` completed successfully. The preceding code HEAD validation reported `427 passed, 26 warnings, 0 failed`; the later docs-only HEAD also has successful workflow status.

No 600-OOS Decision V2 replay was run during this audit. No realized returns, PnL, protected/fresh-forward outcomes, provider/network calls, model refit, alpha retune, or Decision parameter sweep was performed.

## Authorization boundary

Do not run the exact 600-OOS structural replay yet.

Next authorized work is only:

1. remediate R1 without changing policy semantics;
2. rerun focused/full tests;
3. re-audit the small remediation diff;
4. then prepare the structural replay runner with R2 and all preregistered acceptance gates enforced before first replay.
