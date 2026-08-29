# IDX-Trade adversarial audit continuation

## Campaign result

```text
AUDIT_EPOCH = origin/main@adc071d6fd7e8009557bed27b1224217421514ae
PRODUCTION_E2E_PIN = 6b6a41114a910287b413a099a36d59c5e057a8f2
RESEARCH_INTEGRITY_PR103_HEAD = a1096aa1e0507f63b86a014201033d5c354840f9
CA_REMEDIATION_PR108_HEAD = d018ba4dc4d55daa48d9832b65df6d68e469d396
HUNTER_FINDINGS_BEFORE = 24
NEW_HUNTER_FINDINGS = 6
TOTAL_CANDIDATE_FINDINGS = 30
CHALLENGED_FINDINGS = 30
CONFIRMED = 13
LIKELY_REAL = 15
UNRESOLVED_DISPUTE = 1
LIKELY_FALSE_POSITIVE = 1
DISMISSED = 0
FINAL_STATE = AUDIT_NOT_SATURATED_CONTINUATION_RECOMMENDED
```

This is an integrated static challenge, not live production certification.
The four hunter passes were read-only. An additional independent challenger
was attempted with bounded waits twice and stopped without returning a verdict;
that absence is not treated as clearance.

## A1-A24 challenge disposition

| ID | Verdict | Core surviving or dismissal reason |
|---|---|---|
| A1 | CONFIRMED | Watchdog exact-slot predicate ignores run status/conclusion and durable stage commit. |
| A2 | CONFIRMED | E2E attempt is written before work and no attempt loader resumes post-crash work. |
| A3 | CONFIRMED | Stream resume depends on a manifest written after raw/normalized artifacts. |
| A4 | CONFIRMED | Intraday evidence persistence follows requester return, leaving a refetch window. |
| A5 | CONFIRMED | Nonterminal intraday results can be committed and later short-circuit retry. |
| A6 | CONFIRMED | Official Open variable accepts any valid SHA and is not approved-SHA allowlisted. |
| A7 | CONFIRMED | Manual historical session date can reach canonical Open archive before downstream checks. |
| A8 | CONFIRMED | Stream manual workflow can use triggering branch and arbitrary top_n. |
| A9 | LIKELY_REAL | Generic data gate coerces untyped values; canonical malformed-input reachability remains unproven. |
| A10 | LIKELY_REAL | Generic interval helper treats malformed listed_to as open-ended, while Path-A rejects it. |
| A11 | LIKELY_REAL | Generic normalizer keeps one conflicting OHLCV row without conflict evidence. |
| A12 | LIKELY_REAL | Generic coverage does not reject observed dates outside supplied calendar. |
| A13 | LIKELY_REAL | Generic warmup counts observed dates rather than verified post-listing sessions. |
| A14 | CONFIRMED | Generic provenance permits missing source representation and replacement semantics. |
| A15 | LIKELY_REAL | Evaluation gate is shape/metadata strong but lacks complete producer/input/state binding; real mode remains blocked. |
| A16 | LIKELY_REAL | Metric engine receives full alpha frame after ledger validation without enforcing EVALUABLE filter. |
| A17 | LIKELY_REAL | Top-k uses rank <= k and session minimums but no declared 10/20 eligible-name denominator. |
| A18 | LIKELY_REAL | Numeric feature builder does not itself carry CA/basis attestation; current admission is blocked. |
| A19 | LIKELY_REAL | Generic Security Master/provider schema lacks machine-enforced instrument scope. |
| A20 | LIKELY_REAL | Generic delisted adapter ignores pagination totals; Path-A has separate pagination hardening. |
| A21 | UNRESOLVED_DISPUTE | Current GitHub registry has 23 active entries vs 10 main files; 13 absent registrations are not classified as harmful canonical writers. |
| A22 | LIKELY_REAL | E2E manifest path is validated but no expected approved external manifest hash is bound. |
| A23 | LIKELY_REAL | Watchdog installer embeds caller-supplied checkout without ref/HEAD/cleanliness/hash attestation. |
| A24 | LIKELY_FALSE_POSITIVE | PR heads naturally move after a dated coordination snapshot; drift alone caused no proven wrong decision. |

Exact files/blobs, canonical reachability, contracts, reproduction attempts,
counterevidence, impact and confidence for every row are in
`challenge_ledger.csv`.

## New findings A25-A30

- A25 is a confirmed lineage blocker, not a claim that 56,602 is the current
  contamination size. Current Phase-B union is 240,344 versus old 241,724;
  the current handoff explicitly marks the old 56,602 overlay
  `NOT_APPLICABLE_UNPROVEN_ON_CURRENT_SUPPORT` and did not recompute it.
- A26 confirms the ontology boundary: 412 source evidence rows; 389 economic
  physical events; 155 resolved transitions; 188 unresolved economic
  events/transitions; 46 non-basis excluded. These quantities must remain
  separate.
- A27 confirms that Stream adds `manifest_sha256` after storing the serialized
  manifest, so the stored bytes do not self-contain the reported self-hash.
- A28 is a likely post-hoc provenance gap because E2E stage identity omits
  launcher workflow, GitHub run, provider commit and Official Open variable.
- A29 is a likely retention/durability gap: the exact E2E pin is reachable and
  verified but is off-main and not associated with a permanent reviewed ref.
- A30 confirms current CA/KSEI authority remains an admission failure: identity
  reconciliation passes but date-level as-of coverage and transition semantics
  remain unknown/fail.

## Root-cause clusters

1. Scheduler false-green: A1 and A23.
2. Recovery and commit semantics: A2-A5.
3. Mutable capture control plane: A6-A8 and A22.
4. Data gate and identity semantics: A9-A14 and A19-A20.
5. Evaluation provenance and metric denominator: A15-A17.
6. Workflow registry and coordination drift: A21 and A24.
7. CA basis lineage and authority: A18 and A25-A26 and A30.
8. Evidence self-description and retention: A27-A29.

## Impact buckets

Potential historical training-input identity impact: A9-A14, A18-A20, A25,
A26 and A30. These remain outcome-blind and do not prove model-performance
impact.

Potential prospective-credit invalidation: A1-A5, A9, A12-A18 and A22.
No prospective credit is accepted: current score/counter is 2/100 and target
attestation is unavailable.

Potential Decision/Sizing/Execution/PaperState impact: A15-A17 and A28. The
protected evaluation gate currently blocks real mode; no protected outcomes or
PaperState were accessed.

False-positive operational success risk: A1, A5, A6-A8, A21-A23. Recent
GitHub run conclusions are metadata only and do not prove provider capture,
R2 commit, or PaperState success.

## Human adjudication required before remediation

- Decide whether the 13 absent registered workflows are historical, renamed,
  or still authorized runnable surfaces.
- Decide the approved immutable allowlist mechanism for Official Open and E2E
  input manifests.
- Decide whether generic helper findings A9-A13 and A19-A20 are in scope for
  canonical Path-A or should remain legacy-surface risks.
- Decide whether the evaluation contract must cryptographically bind the
  scorer, ordered features, PIT/as-of inputs, target rows and state transition
  artifacts before any outcome access.
- Decide how to independently recompute current Phase-B CA applicability; do
  not reuse the legacy 56,602 geometry as current evidence.

## Remaining unsaturated surfaces

- Per-registration workflow trigger/ref/status classification for the 13
  absent files.
- Synthetic crash harnesses for every E2E/Stream/Intraday write boundary.
- Full canonical caller graph for generic data-gate and Security Master helpers.
- Independent current Phase-B CA support-set and transition reconciliation.
- Synthetic mutated target/NAV/PaperState gate challenge under the protected
  contract without loading real outcomes.

No remediation was performed. The next safe work is further read-only
adjudication or an explicit human decision on these questions.
