# INC-001 CA Source Authority Audit V1.1

Date: 2026-08-29 Asia/Jakarta  
Branch: `data/ca-aware-feature-basis-remediation-v1`  
Implementation commit: `13ba27598f971591f6f8b144cd95d9b4fc6ee3c3`  
Reviewed base pin: `879a6f95bfe28379a7c918461f2ce955f2deea84`

## Decision and boundaries

`NO-GO` for source-authority admission. This is a retained/local-evidence
reconstruction only. No provider or network call, Phase-E run, outcome/target
access, model fit/refit/scoring, counter mutation, canonical historical rewrite,
production execution, or merge was performed. PR #108/#103 remain unmerged.

The controlling immutable artifact is:

```text
D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-final-rerun-v4
```

The deterministic rerun is:

```text
D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v5
```

All non-manifest output hashes match between those two roots. Final
`MANIFEST.json` SHA-256 is
`ec8ad724d66db7180686096353fd75b229ea465854053eb9721e9e627e5c210c`;
`summary.json` SHA-256 is
`1b4320b98519c8f26e4328c92ef3df85941cba3baa4a9f284742ac0c1c228cc3`.

## Facts from the current retained local audit

- Final fit: 240,344 rows / 629 tickers.
- Cross-sectional application: 276,153 rows / 716 tickers.
- Dependency closure: 365,968 rows / 716 tickers, `2021-04-29` through
  `2026-07-17`.
- Raw primary event census: 412 active source-bound events: 276 KSEI rows and
  136 deduplicated IDX GetIssuedHistory rows, including five source-native
  `gabungUsaha` rows retained as `MERGER` candidates.
- Raw ledger: 553 rows: 412 primary rows, 101 targeted schedule evidence rows,
  and 40 official announcement-byte rows. The schedule ledger preserves two
  retained rows whose local byte binding is not valid; they remain unresolved.
- Prior 136 event identities: 136/136 present in the raw census; old-only is 0;
  raw-additional is 276. The primary census has two appended taxonomy-unknown
  candidates from the named forensic check.
- Prior `EXACT_TRANSITION`: 42/42 re-proven from raw evidence; 0 not re-proven;
  79 raw transitions are newly resolved; 291 remain unresolved.
- The current strict-26 scope counts are:

  ```text
  before: OUTSIDE_DEPENDENCY_TICKER=10,
          OUTSIDE_DEPENDENCY_AFTER_CLOSURE=5,
          UNRESOLVED_CANDIDATE_BEFORE_CLOSURE=3,
          UNRESOLVED_CANDIDATE_IN_CLOSURE=8
  after:  OUTSIDE_DEPENDENCY_TICKER=10,
          UNKNOWN_UNRESOLVED_AFTER_CLOSURE=5,
          UNRESOLVED_CANDIDATE_BEFORE_CLOSURE=3,
          UNRESOLVED_CANDIDATE_IN_CLOSURE=8
  ```

  Thus the current census has 0 `OUTSIDE_DEPENDENCY_AFTER_CLOSURE`; no new
  outside classification was introduced.
- KSEI interval authority is partial: 567/716 ticker intervals are certified
  for `RIGHTS_HMETD` and 567/716 for `STOCK_DIVIDEND`, using the retained
  registered-security page behavior and source ref/hash. The other frozen
  families are `UNKNOWN_INTERVAL`; full 716 temporal authority remains FAIL.
- IDX negative coverage is `UNKNOWN` for all nine audited categories. A
  successful empty response is not promoted to no-event authority because the
  retained endpoint contract does not define exhaustive negative semantics.

The exact per-family counts, hashes, refs, raw fields, and input inventory are
in the artifact CSV/JSON files rather than inferred from this checkpoint.

## Named ADRO -> AADI 2024 forensic check

This is a source-authority and taxonomy check, not a new frozen family decision.
Both tickers are in the accepted populations: ADRO is final-fit,
cross-sectional, and closure; AADI is final-fit, cross-sectional, and closure.
ADRO's retained closure begins `2021-11-18`; AADI's retained closure begins
`2024-12-05`. The ADRO rights candidate and the AADI listing date therefore
intersect an accepted backward-dependency window, so the check was retained in
scope.

Current retained source evidence shows:

- KSEI ADRO source-native `Right Distribution`, record `2024-11-29`,
  distribution `2024-12-02`, ratio `(4389 ADRO : 1000 ADRO-H )`, no cum date,
  page SHA `94cf7d898146b7366a1efd776cd3bb3b76dd3c3ae6937c318dd7604ceec39113`.
  This is evidence of a right to acquire ADRO-H, not source proof of an
  AADI-share distribution-in-specie. Under the controlling CA contract it is
  a rights candidate, but its transition remains unresolved because no exact
  transition schedule is linked.
- KSEI also has a separate ADRO `Cash Dividend` row, ratio `(1 ADRO : 1 IDR)`,
  cum `2024-11-26`, record `2024-11-29`, distribution `2024-12-06`, on the same
  retained page. It is not merged with the structural entitlement.
- Retained targeted schedule records are `KSEI-27597/JKU/1124` and
  `KSEI-28171/JKU/1224`, with source SHA-256 values
  `4c51477093cdb6b93f568781ac3d21f834a26154e18f2ac09576f1eed3867aca` and
  `177618678e05cb18f68022a2e89f33c76e05e5ad0a501ace2c4cff2fb8527b8e`.
  Their retained parse has no accepted regular-market transition semantic.
- IDX source-native evidence is `ipo` for AADI on `2024-12-05` (row id
  `45577`), not a structural ADRO transition. IDX ADRO `kurangModal` is a
  separate `2026-07-13` row and cannot prove the 2024 event is
  `CAPITAL_RESTRUCTURING`.
- No retained IDX announcement-linkage row names ADRO or AADI for this case.
  That absence is not negative-event authority. Retained AADI KSEI history has
  no structural-family row tying AADI to the ADRO entitlement.

The retained source contract does not justify mapping the separation aspect to
`CAPITAL_RESTRUCTURING`, nor does it justify selecting `SPIN_OFF`, `DEMERGER`,
`PUPS_ENTITLEMENT`, or `DISTRIBUTION_IN_SPECIE`. The finding is therefore
`REQUIRES_POLICY_DECISION` / taxonomy `UNKNOWN` while the existing rights row
retains its source-contract `RIGHTS_HMETD` representation.

The source-label red-team search found two retained KSEI schedule titles
containing the exact raw label `Pemisahan Unit Usaha` (TPIA, 2024-05-07 and
2024-05-08), plus seven IDX `gabungUsaha` rows in the 716 scope. Literal
`PUPS`, `spin-off`, `demerger`, `distribution-in-specie`, and subsidiary labels
were not found in the retained structured/parsed source-label fields. Every
candidate is preserved with its exact raw label, ref, and SHA in
`v11_structural_separation_forensics.csv`; none is force-mapped.

## Remaining gates and scientific verdict

The one authoritative future PASS path remains evidence-rich family coverage
plus source/ref/hash-bound date/as-of attestation for the full expanded scope.
The synthetic 629/716/716 gate passes only with that complete provenance; naked
booleans, partial fit-only evidence, missing families/hashes, conflicts, or
missing date provenance fail closed.

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

## Validation

- Focused V1.1/source-audit tests: 11 passed.
- All CA/integrity tests: 121 passed, exit 0, with a unique Windows basetemp.
- Full pytest: 360 passed, exit 0, with a unique Windows basetemp.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Deterministic artifact rerun: PASS, zero non-manifest hash mismatches.
- Exact-head GitHub Actions: pending at checkpoint creation; must be recorded
  in the final handoff after the pushed final documentation commit.

## Immutable artifact hashes

```text
v11_raw_source_event_ledger.csv          30f01b6b09bd11d7c2bbdd1d6e47b471a8d8b85a591c935832ba443520234ae1
v11_transition_reconstruction.csv        fc88858abea260994d4da31220580b0d40187eecf36a537b47851e5a1af66b3a
v11_dependency_closure_event_census.csv  f92a31534525f0cf840d890e0908b04d248c0e6339b7fb42488e87f3caae172e
v11_structural_separation_forensics.csv  058132b7f983b6e33b98ef01ec822ff3b88715759d74cd49b960c2d5f144b6ff
v11_source_interval_authority.csv        2bd459a2d7da6c84574a1ca8fd98905c0a2765ff18b482c14b362c42e53b6ef2
v11_idx_negative_coverage_contract.csv   1d51700d2039f713739f224b58410b99a9e0a1d09516ccd4b7c2548b7c5cf8c7
v11_source_family_authority_matrix.csv   c5e72025acea4b1cf3b96f31ae3d15e6cd591a125266aae423b6e875ff4aeece
v11_population_authority.csv              18fc42077996ed6e2b303d11893a2a6f5bb4a1cc6e4ca963234d1030e98d1055
v11_remaining_gap_matrix.csv              6585647d741a92984ff37ae17ab7c4669fc98705d842643ccede134ef5c152a4
acquisition_requirements_v11.json        a0ad0cfd3d6d2f848c5345a60707cf1e5fdf9e70ddb3e9f7166244bf5f47a462
```

This checkpoint is for ChatGPT review. No merge or further production
execution is authorized by it.
