# Reproducibility Record

## Lane identity

- Branch: `codex/alpha-available-data-20260919`
- Current recorded HEAD at knowledge-base creation: `a718756c359ea214755b9b7f93480f73323eb9f9`
- Baseline: `58f094b8`
- Worktree: `C:/Users/Sam/.codex/worktrees/idx-alpha-available-data-20260919`
- Scope: research/docs-only isolated lane

## Current control evidence

- Lane integrity: `PASS`, 10/10; current process-scope staging count 160.
- Packet verifier: `PASS`, 65/65.
- Recorded firewall: `PASS`, 31/31.
- Packet SHA-256: `7756bc138cd4b7da9ac2a5ad09c7fe5a10addeb76e54f9132b292bb73d212894`.
- Packet contract SHA-256: `a76cd5acdfe457668b6241c4d28d677e4c2b92a98f2a54b82401338a6d794d4d`.
- Eligibility guard SHA-256: `743ad3b809a11536506487e26dbb4d57809089960f91dd30ee777be8ccff5dd6`.
- Firewall result SHA-256: `a55df4853c14f2b27f2b0d1f591ba35af1eadfe0d8cbaae697859f1ff926e397`.
- Staging filename digest: `0c3bd7a88d5ce352b2ff397084e955b19cfa2a6602943486706183d1d8beddf3`.

## Reproduction boundaries

The constructor replay reproduces 981940 structural keys, masks, scores, and
ranks with zero mismatches. This is an implementation-reproduction statement.
It is not proof of PIT, population completeness, survivorship, CA basis,
capacity, target correctness, or predictive value.

The packet/firewall checks bind code, manifests, hashes, candidate budget, and
fail-closed policy state. They do not authorize execution. The lane verifier
binds branch/worktree/delta/staging scope and explicitly does not prove runtime
access absence.

## Verifier independence audit

- The packet verifier does not import the producer module; this is positive
  module-level independence.
- It duplicates `sha256_file` and `key_digest`, so helper-assumption coupling is
  possible even without an import.
- It verifies contract clauses, hashes, manifests, key sets, and provenance,
  but does not independently recompute the producer's rolling and score formulas.
- The target firewall is a hybrid: required-path/hash bindings plus forbidden
  path/import/output-token scans. It is not a proof against every encoded or
  semantically disguised protected payload.
- Current packet output embeds the verifier code hash, and that hash matches the
  current verifier. The contract does not itself pin an expected verifier
  version, so stale historical PASS artifacts must be rejected by rechecking
  embedded packet/contract/code hashes.

## Regeneration protocol after a policy change

1. Record authoritative eligibility rule, count/median semantics, finite-value
   treatment, calendar, row count, and authorization.
2. Regenerate only in this isolated lane.
3. Re-run constructor/key/score/rank, packet, firewall, and lane controls.
4. Append new registry/finding entries; never overwrite prior evidence.
5. Reassess candidate support and common-support methodology; do not open
   protected outcomes automatically.

## Common-support census

- Script: `research/alpha_common_support_census_v1.py`.
- Script SHA-256: `4a1117170e93894534a137f480cbe12e747011344f13368a922d7662c158cd43`.
- Input feature SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`.
- Current native rows: C1 `295243`, C2 `310761`, C3 `30994`, C4 `310323`.
- Exact all-four finite intersection: `30861` rows, `9.9308%` of current
  eligible rows; daily max `175`, 277 dates with at least 30 names, median 0.
- The first daily aggregation attempt was wrong and was corrected before the
  accepted output; the corrected method groups the all-four boolean by date.

## Eligibility counterfactual scenario

- Script: `research/alpha_eligibility_policy_scenario_v1.py`.
- Unit test: `tests/test_alpha_eligibility_policy_scenario_v1.py`, 2/2 passing.
- Result summary: `research_knowledge/eligibility_policy_scenario_v1.json`.
- External result SHA-256:
  `3fb1331937d14c5fa17a066aaa0eaab1170064c4652a14e7d5e78190c3666c98`.
- Code SHA-256:
  `58d3280c9e191903bd195bfa11a92201ee693ead1b752f1010f5b93b15cd0e11`.
- The replay reads only the allowlisted structural panel, financial bundle,
  official sessions, and tradability anchors. It writes only to the isolated
  staging root and contains no protected outcome values.
- It evaluates both policy branches without selecting one. The 600-session
  Top-30 scope uses previous-official-session logic to align with the existing
  structural lab; all-session summaries are retained only as diagnostics.
- The result is `PASS_STRUCTURAL_SCENARIO_ONLY` with
  `BLOCKED_POLICY_CONFLICT`, not policy resolution or predictive evidence.

## Tooling mutation audit

- Script: `research/alpha_data_authority_tooling_audit_v1.py`.
- Durable result: `research_knowledge/tooling_mutation_audit_v1.json`.
- The audit uses temporary fixtures only and reports
  `PASS_EXPECTED_MUTATIONS_AND_RECORDED_GAPS`.
- The corrected authority-packet verifier now checks both evidence-reference
  path shape and file existence, including the counterfactual scenario ref.
- Known gaps remain: the firewall is not a semantic allowlist, disguised fields
  and unexpected non-matching schema columns can pass, and producer formulas
  are not independently recomputed by the envelope verifiers.

## Lane allowlist correction

- The lane verifier initially classified `tests/` as out of scope even though
  the new files were isolated research unit tests.
- `tests/` is now an explicit allowed research prefix; canonical, production,
  cloud, capture, telemetry, and protected paths remain outside the allowlist.
- This is a process-scope correction, not proof that runtime access was absent.

## Historical archaeology audit

- Script: `research/alpha_historical_archaeology_audit_v1.py`.
- Script SHA-256:
  `bb6214e69b4553be52ed07b40344e5a57af6ed1af4d2798d408f819c6b51fff9`.
- Durable result: `research_knowledge/historical_archaeology_audit_v1.json`.
- External result SHA-256:
  `dd1201a169e4f0f9b2194c637e3f91204f20cf5146ac22a58dd65abeb97e904c`.
- Method: current evidence-document existence/hash checks plus Git ref,
  commit, and safe tree-name inspection; protected-looking historical paths
  were counted but not read.
- Result: family-level archaeology supported; exact old implementation
  replayability partial; no candidate or protected comparison authorized.

## Semantic tooling challenger

- Script: `research/alpha_tooling_semantic_challenger_v1.py`.
- Script SHA-256:
  `eb171a9209ef1143e939d606e7ea2da5833914083d4b08980f0ceee3920aafa7`.
- Durable result: `research_knowledge/tooling_semantic_challenger_v1.json`.
- External result SHA-256:
  `0f389e4fd46795f56e0fed457e101174b8c07fa388c95de27ab90bea6488581d`.
- Result: three false-green surfaces confirmed; top-level packet allowlist
  still rejects unknown fields; verifier-version pin remains absent.

## Formula mutation challenger

- Script: `research/alpha_formula_mutation_challenger_v1.py`.
- Durable result: `research_knowledge/formula_mutation_challenger_v1.json`.
- Checkpoint: `docs/checkpoints/2026-09-20_ALPHA_FORMULA_MUTATION_CHALLENGER_RESULT_V1.md`.
- Script SHA-256:
  `86c6fd1d9ad18cdb2b29f110a5a6f7b522cd4a3c2eebcbdd3251f67f2409d434`.
- External result SHA-256:
  `044d92db4c49e0c9744127fcfca6d30820dd80f358f7a43254acd8f33c5d6ce5`.
- One independent baseline plus five semantic mutations were run on a
  150-session synthetic fixture. Baseline passed; every declared mutation was
  detected by score, rank, or eligibility checks.
- This is mutation-sensitivity evidence only. It does not certify the admitted
  panel, PIT, corporate-action basis, capacity, or predictive validity.

## Nested packet schema challenger

- Script: `research/alpha_packet_nested_schema_challenger_v1.py`.
- Durable result: `research_knowledge/packet_nested_schema_challenger_v1.json`.
- Checkpoint: `docs/checkpoints/2026-09-20_ALPHA_PACKET_NESTED_SCHEMA_CHALLENGER_RESULT_V1.md`.
- Script SHA-256:
  `b3a621052952dda41619a55e4939f90f7c964882367eae3a2b5ce3eb2caf27a1`.
- External result SHA-256:
  `2e1a8ef14427bd8226a16c160bc70f7e72aefb943fb59ec621310069d2163429`.
- The draft strict allowlist passed the baseline and rejected five declared
  nested/missing schema mutations; the current verifier rejected only the
  unknown top-level mutation and accepted the four nested/missing cases.
- The draft is not integrated. Value semantics, type/range rules, and expected
  verifier-version freshness remain open.

## Verifier freshness challenger

- Script: `research/alpha_verifier_freshness_challenger_v1.py`.
- Durable result: `research_knowledge/verifier_freshness_challenger_v1.json`.
- Checkpoint: `docs/checkpoints/2026-09-20_ALPHA_VERIFIER_FRESHNESS_CHALLENGER_RESULT_V1.md`.
- Script SHA-256:
  `f4937eddfe80796abfd9f56ef5226bac76f90b0012de6a200fc1f83d2c2332a0`.
- External result SHA-256:
  `8975f7e897001a4673df9f6b1c046fede825400d90dd617045940aea0597287d`.
- The draft freshness contract passed baseline and rejected four missing/stale
  result mutations; unchanged packet validation remained PASS in every case.
- The contract is not integrated and requires independent review/adoption.

## Eligibility provenance history

- Script: `research/alpha_eligibility_provenance_history_v1.py`.
- Durable result: `research_knowledge/eligibility_provenance_history_v1.json`.
- Checkpoint: `docs/checkpoints/2026-09-20_ALPHA_ELIGIBILITY_PROVENANCE_HISTORY_AUDIT_RESULT_V1.md`.
- Script SHA-256:
  `82af867fd58cff6e3999b42fa0063c7f8da8c0436063329607b7cc8d42853166`.
- External result SHA-256:
  `c6e4ba13928e36718394bba90d4566686c64cc2d2ecdd2c39c84eb44a5c33a9a`.
- The audit verifies that the legacy pre-protocol primary liquidity rule uses
  a 60 official-session window and at least 20 finite ACTIVE observations.
  Stage-A complete-window rolling and the separate security-master warm-up are
  recorded as distinct implementation/concept surfaces.
- This narrows provenance but does not bind current project policy. No
  population was selected or regenerated, and no protected outcome was read.

## Eligibility policy delta by calendar year

- Script: `research/alpha_eligibility_era_delta_v1.py`.
- Durable result: `research_knowledge/eligibility_era_delta_v1.json`.
- Checkpoint: `docs/checkpoints/2026-09-20_ALPHA_ELIGIBILITY_ERA_DELTA_RESULT_V1.md`.
- Code SHA-256:
  `dd20ca55a6ac8d967e3e76853724d2e81f49d074a40a9e78aed6f2d70f198f7c`.
- Durable result SHA-256:
  `2a5764e2bccb5b50f8834eac89b1f389ce41880cffb86b2fe357e433970416cb`.
- The min20-minus-min60 delta is present in every calendar year and totals
  38004 rows across 619 tickers and 1241 dates. No policy or era was selected.

## Candidate calendar-year mechanics

- Script: `research/alpha_candidate_era_mechanics_v1.py`.
- Durable result: `research_knowledge/candidate_era_mechanics_v1.json`.
- Checkpoint: `docs/checkpoints/2026-09-20_ALPHA_CANDIDATE_ERA_MECHANICS_RESULT_V1.md`.
- Code SHA-256:
  `b58269a65eaafa627bf912cce7e860196d151939703baec3335e50297fd94039`.
- External result SHA-256:
  `797c41486fd08ee86c04988331dc6179994570fe7c2374cc72b14657d04ec34e`.
- Focused tests: `tests/test_alpha_candidate_era_mechanics_v1.py`, 2/2 passing.
- The result uses fixed Top-30 descending rank and no outcome fields. It
  records year-specific turnover, persistence, HHI/effective names, rank
  displacement, and between-year selected-ticker Jaccard; non-comparable
  sparse-era pairs are explicit nulls, not zeros.

## Candidate score-separation mechanics

- Script: `research/alpha_candidate_score_separation_v1.py`.
- Durable result: `research_knowledge/candidate_score_separation_v1.json`.
- Checkpoint: `docs/checkpoints/2026-09-20_ALPHA_CANDIDATE_SCORE_SEPARATION_RESULT_V1.md`.
- Code SHA-256:
  `38777f7c530552ad88eb2e6779b64e2c64a1e4500c538692970eff935cfc80e9`.
- External result SHA-256:
  `43866dc33d2ab6041f346666d6c6df674a68d72a20b805276c0ec115959ff9db`.
- Focused tests: `tests/test_alpha_candidate_score_separation_v1.py`, 2/2
  passing.
- The audit measures fixed Top-30 score at positions 30 and 31, same-day IQR
  normalization, exact ties, unique-score fraction, and same-year next-session
  turnover association. C2 has the widest median normalized gap (0.05912),
  C1/C4 are thinner (0.01089/0.00936), and C3 has a 10.18% exact tie fraction.
- The first execution was discarded after correcting the year-boundary pairing
  rule. The recorded result is the corrected rerun. This remains structural,
  representation-dependent evidence only.

## Candidate component anatomy

- Script: `research/alpha_candidate_component_anatomy_v1.py`.
- Durable result: `research_knowledge/candidate_component_anatomy_v1.json`.
- Checkpoint: `docs/checkpoints/2026-09-20_ALPHA_CANDIDATE_COMPONENT_ANATOMY_RESULT_V1.md`.
- Code SHA-256:
  `de8466ce25cce5fad2e91ada8877e8c8f8806492655355072ad45c88eb14255e`.
- External result SHA-256:
  `c024d20e01008e2ba13d234843f195dbf859dfd9dbe66cc3404344bb57230295`.
- Focused tests: `tests/test_alpha_candidate_component_anatomy_v1.py`, 1/1
  passing.
- The official-session rolling components exactly reconstruct finite C1/C2/C4
  scores: 295243, 310761, and 310323 checked values, all with maximum absolute
  difference 0.0. C1/C4 are numerator-dominated reversals; C2 is an
  interaction between ret_5 and abnormal-turnover log. The result is
  implementation/structural evidence only.
