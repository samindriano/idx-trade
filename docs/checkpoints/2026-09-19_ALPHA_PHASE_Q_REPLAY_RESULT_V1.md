# Phase Q Replay and Research-Tooling Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Research HEAD before this documentation commit: `5ca03b65a81282d4ee03f52dc70b5b452492f0c5`

## Scope and boundary

This checkpoint records the follow-up to the three read-only Phase-Q red-team
reports. It is outcome-blind and research-only. No target, forward return,
protected label, incumbent predictive score, provider, network, cloud/R2,
capture, scheduler, counter, canonical dataset, or production artifact was
opened or modified.

The result is not predictive evidence and does not change any candidate status.

## 1. Former verifier independence claim: corrected

The former `verify_alpha_c1234_adversarial_audit_v1.py` was found to be an
artifact-envelope verifier, not an independent structural replay. It trusted
`result["checks"]` and never recomputed raw-data checks, candidate counts,
listing-age metrics, static implementation checks, or source hashes. A
counterexample JSON with empty check maps could pass because `all({}.values())`
is true.

New tool:

`research/verify_alpha_c1234_adversarial_audit_v2.py`

It independently reopens the same frozen outcome-blind inputs and checks:

- implementation AST/static checks;
- feature/panel keys, duplicates, official dates, chronological order;
- stored candidate schema, finite support, score/rank masks, and rank bounds;
- security-master interval mapping;
- listing-age metrics and identity summary;
- all source hashes and audit-code hash;
- exact artifact schema and interpretation boundary.

Result: `PASS_INDEPENDENT_STRUCTURAL_REPLAY` for the registered artifact/
structural checks. It does not independently rebuild the feature constructor
or eligibility masks from raw inputs; see
`2026-09-19_ALPHA_C1234_REDTEAM_SCOPE_ADJUDICATION_RESULT_V1.md`.

Important limitation: access flags inside the old artifact remain
self-attested. The new verifier reports this explicitly and does not claim
process-level proof that protected data was never accessed.

| Artifact/tool | SHA-256 |
|---|---|
| `verify_alpha_c1234_adversarial_audit_v2.py` | `807ad882a45aea24ce7e72dc68c642a29512fe79b5d29e0f88be88ccb4be3f46` |
| replay output `alpha_c1234_independent_replay_v2.json` | `0f147bf0babbeb854f16a328b748eab13d85dbb56e5f48e6590cda5b6a04a2e8` |

## 2. Deterministic selection contract: fixed

`research/alpha_structural_robustness_v1.py` previously used `nlargest()`
without a ticker tie-break. It now uses stable score-descending,
ticker-ascending sorting with `mergesort`, matching the structural lab and
combination selection contract.

The current canonical-order replay produced no metric or set changes for
C1/C2/C3/C4/H-LIQ and an exact 100% set match. That does not make the old
implementation safe: C3 had 52 cutoff-tie dates, and row permutations changed
selection on 17, 12, and 17 dates in the tested permutations. A synthetic
equal-score `ZZ`/`AA` example also changes under `nlargest()` but is fixed by
the explicit ticker tie-break.

Patched code SHA-256:

`research/alpha_structural_robustness_v1.py` —
`b37daa850e685007c3d64c349806807b169146dc1ce274cf3a230c73bf14363b`

Regenerated artifact:

`alpha_structural_robustness_v2.json` —
`0d0f234698bcc533a65b671a2bcf0bfbbbca3cdb60ea05fd6878418147769bd1`

Status: `PASS_STRUCTURAL_ONLY`.

## 3. Missing-value handling: fixed and regenerated

`research/alpha_structural_lab_v1.py` previously used default
`pct_change()`, while the candidate builder explicitly used
`pct_change(fill_method=None)`. The structural lab now uses the explicit
no-fill policy.

The bounded comparison showed that default-fill replay changed C1 on 52/600
Top-30 dates, with mean overlap `99.6889%` and turnover changing from
`42.1536%` to `42.1369%`; C2 did not change and C4 had only floating-point
noise. The raw-panel market-state path had no explicit missing-close rows, so
its reported state metrics did not change, but the reindexed candidate-path
risk was sufficient to require the fix.

Patched code SHA-256:

`research/alpha_structural_lab_v1.py` —
`715e1d96c83d8facf6f9a893f7dfbedcfbe5e192d69e50e3f6943c8fd66c7cf0`

Regenerated artifact:

`alpha_structural_lab_v2.json` —
`30899d21d4cdc4940e0a926e5e7d73a66603f78bc4d8731df9c2be9cc08ed323`

The existing structural-lab verifier returned `PASS` against the regenerated
artifact.

## 4. Newly classified local data surfaces

The inventory worker found no newly admissible historical research source.

| Surface | Classification | Finding |
|---|---|---|
| `config/tradability_snapshot.sample.csv` | `PARTIAL / CHECKPOINT-SAMPLE / NON-ADMISSIBLE` | Five rows, all dated 2025-07-30; not an event history. |
| `config/idx_tradability_manifest.sample.csv` | `PARTIAL / CHECKPOINT-SAMPLE / NON-ADMISSIBLE` | Four announcement references, including one `MANUAL_REVIEW` case. |
| `config/tradability_coverage_windows.csv` | `EMPTY / UNKNOWN` | Header-only; zero declared coverage windows. |
| External Stage-A generations | `DERIVED / STRUCTURAL-ONLY / HISTORICAL-STAGING` | Multiple 981,940-row derived generations exist; some are byte-identical but carry different manifest heads/audit metadata. Duplicate/superseded lineage must be explicit before treating one as canonical research staging. |

The implementation and runbook already state that snapshots are not
substitutes for event logs and that coverage completeness requires a discovery
audit. Therefore these surfaces do not widen the admissible-data boundary.

## 5. Scientific disposition

- C1/C2/C4 remain `FUTURE_RESEARCH`.
- C3 remains `BLOCKED`.
- H-LIQ-01 remains `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`.
- No C5 or other candidate ID was created.
- No candidate became `READY_FOR_REENTRY`.
- Historical PIT/as-of, issuer/ISIN continuity, survivorship, global price
  basis, and real liquidity/capacity remain unresolved.

## 6. Next high-information actions

1. Keep the new deterministic-selection and no-fill contracts in all future
   research-only structural artifacts.
2. Use the v2 replay verifier for future C1/C2/C4 audit artifacts; describe
   the old v1 verifier as envelope-only.
3. Add explicit Stage-A generation lineage/duplicate status to the data
   inventory; require an immutable event-log and coverage manifest before
   tradability admission.
4. Continue only with bounded CA/issuer-basis, capacity, provenance, and
   genuinely distinct mechanism work. Do not open protected targets.

No predictive superiority claim is made.
