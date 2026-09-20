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
