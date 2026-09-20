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
