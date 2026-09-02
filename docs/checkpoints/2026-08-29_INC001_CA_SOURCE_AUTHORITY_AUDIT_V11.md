# INC-001 CA Source Authority Audit V1.1

Date: 2026-08-29 Asia/Jakarta
Branch: `data/ca-aware-feature-basis-remediation-v1`
Reviewed implementation baseline: `0626b653e273067612631fd3414b579ca93c3763`
The controlling V1.1 result was generated from that HEAD with the review
correction worktree changes recorded in the artifact's repository state.

## Decision and boundaries

`NO-GO` for source-authority admission. This is a retained/local-evidence
reconstruction only. No provider or network call, Phase-E run, outcome/target
access, model fit/refit/scoring, counter mutation, canonical historical rewrite,
production execution, or merge was performed. PR #108/#103 remain unmerged.

The controlling immutable artifact is the deterministic V8 root:

```text
D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v8
```

The prior V7 root remains an immutable comparison intermediate only:

```text
D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-final-rerun-v7
```

All 11 non-manifest output hashes match between V7 and V8; only the manifest
metadata differs. V8 `MANIFEST.json` SHA-256 is
`556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71`;
`summary.json` SHA-256 is
`e0475e06ec35c513dc383a3b58262954cf8d93245341a6e26ad30034df136fbc`.

## Facts from the current retained local audit

- Final fit: 240,344 rows / 629 tickers.
- Cross-sectional application: 276,153 rows / 716 tickers.
- Dependency closure: 365,968 rows / 716 tickers, `2021-04-29` through
  `2026-07-17`.
- Raw primary event census: 412 active source-bound physical events: 276 KSEI
  rows and 136 deduplicated IDX GetIssuedHistory rows, including five
  population-scoped source-native `gabungUsaha` rows retained as `MERGER`
  candidates. Forensic/taxonomy findings are not appended to this census.
- Raw ledger: 553 rows: 412 primary rows, 101 targeted schedule evidence rows,
  and 40 official announcement-byte rows. The schedule ledger preserves two
  retained rows whose local byte binding is not valid; they remain unresolved.
- Prior 136 event identities: 136/136 present in the raw census; old-only is 0;
  raw-additional is 276. The full physical census remains 412 rows; taxonomy
  findings remain in the separate forensic artifact.
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
- KSEI interval authority is page-observed only: 567/716 ticker pages parse for
  `RIGHTS_HMETD` and 567/716 for `STOCK_DIVIDEND`, with zero source-certified
  complete intervals. Retained row-count/page bytes do not prove pagination,
  provider completeness, observed-through/as-of semantics, or source-family
  no-event coverage. The other frozen families are `UNKNOWN_INTERVAL`; full
  716 temporal authority remains FAIL. Bounds are per ticker, not the global
  `2021-04-29` closure minimum.
- IDX negative coverage is `UNKNOWN` for all nine audited categories. A
  successful empty response is not promoted to no-event authority because the
  retained endpoint contract does not define exhaustive negative semantics.

The exact per-family counts, hashes, refs, raw fields, and input inventory are
in the artifact CSV/JSON files rather than inferred from this checkpoint.

## Named ADRO -> AADI 2024 forensic check

This is a source-authority and taxonomy check, not a new frozen family decision.
Both tickers are in the accepted populations: ADRO and AADI are final-fit,
cross-sectional, and closure. ADRO's retained per-ticker closure begins
`2021-11-18`; AADI's begins `2024-12-05`. The ADRO rights candidate and AADI
listing date intersect the accepted population geometry, so the check was
retained in scope; the forensic rows separately record per-ticker dependency
window intersection.

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
  `45577`), listing evidence only, not a structural ADRO transition. IDX ADRO
  `kurangModal` is a separate `2026-07-13` row and cannot prove the 2024 event
  is `CAPITAL_RESTRUCTURING`.
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
2024-05-08), plus seven exact IDX `gabungUsaha` rows in the 716 population
scope. The two TPIA documents link to the same underlying retained event and
document group; they are not double-counted as physical events. Five
`gabungUsaha` rows are population-scoped physical census rows; BDMN and GDST
remain forensic-only outside accepted global geometry. Literal `PUPS`,
`spin-off`, `demerger`, `distribution-in-specie`, and subsidiary labels were
not found in the retained structured/parsed source-label fields. Every finding
is preserved with exact raw label, source ref/hash, event identity where
available, and status in `v11_structural_separation_forensics.csv`; none is
force-mapped.

## Remaining gates and scientific verdict

The acquisition plan has 25 explicit units: capability verification is
separate from later bulk acquisition. The unresolved transition unit contains
all 291 exact unresolved physical event identities (193 tickers), reconciling
the prior 94 `SCHEDULE_REQUIRED` subset plus 197 additional unresolved rows;
291 is the minimum until source-backed document deduplication is proven. IDX
endpoint-wide capability units use `ticker_count=0` only where no ticker
request dimension is proven; later bulk units target the exact 716 ticker
set/hash. All units require explicit source refs/hashes and source-defined
completeness/empty/no-event semantics, and no provider acquisition is
authorized by this handoff.

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
- Implementation/content validation run `33199155485` on commit
  `a9b1ef45057efc7902e71bef4d1b567026552d1b`: SUCCESS, `360 passed, 5
  warnings` ([run](https://github.com/samindriano/idx-trade/actions/runs/33199155485)).
- Latest reviewed-head validation run `33199443043` on commit
  `0626b653e273067612631fd3414b579ca93c3763`: SUCCESS, `360 passed, 5
  warnings` ([run](https://github.com/samindriano/idx-trade/actions/runs/33199443043)).
  These are non-blocking Node.js action-runtime and NumPy timedelta
  deprecation warnings; they are not test failures. The final branch CI for
  this correction is run once after the handoff commit and reported with that
  final HEAD; no docs-only CI loop is required.

## Immutable artifact hashes

```text
v11_raw_source_event_ledger.csv          30f01b6b09bd11d7c2bbdd1d6e47b471a8d8b85a591c935832ba443520234ae1
v11_transition_reconstruction.csv        fc88858abea260994d4da31220580b0d40187eecf36a537b47851e5a1af66b3a
v11_dependency_closure_event_census.csv  8b4a1fd248eb609cd4b8f81863b0d88703b2efc92800ce1b6a0b752fd34623e6
v11_structural_separation_forensics.csv  af09d359991b3e7f0cb714119e7b2e10e394757033ee1ded6e4d511a00575206
v11_source_interval_authority.csv        8744732b524250d324353ebffe35ba8a280527d2b7f63fe815fcad9a5fe60d1e
v11_idx_negative_coverage_contract.csv   1d51700d2039f713739f224b58410b99a9e0a1d09516ccd4b7c2548b7c5cf8c7
v11_source_family_authority_matrix.csv   62c631d898d3ded23d8f20854131c7cbb5f99627f04a367aac919564567ada51
v11_population_authority.csv              18fc42077996ed6e2b303d11893a2a6f5bb4a1cc6e4ca963234d1030e98d1055
v11_remaining_gap_matrix.csv              47d105b7352fb2af547e96cbd9b52b25ecaccabe070c7202341755ecaf3839ae
acquisition_requirements_v11.json        aea73e6d242909bc9bef7cdc927e04fa52add349b8ccea7fb98e624858979ce9
```

This checkpoint is for ChatGPT review. No merge or further production
execution is authorized by it.
