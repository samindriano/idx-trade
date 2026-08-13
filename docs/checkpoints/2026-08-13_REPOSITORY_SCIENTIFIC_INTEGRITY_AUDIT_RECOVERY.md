# Repository Scientific-Integrity Audit — Recovery Checkpoint

Date: 2026-08-13 (Asia/Jakarta)
Repository: `samindriano/idx-trade`
Audit branch: `codex/scientific-integrity-audit-v1`
Recovery HEAD: `612c11cdde5a942428fe74e3059811480fc0ceb2`
Controlling coordination ref at recovery: `origin/main@7436c213c625ea3856b8376e74c5927ff84a7eea`

## Recovery boundary

This checkpoint preserves the completed outcome-blind read-only audit state
after an interrupted root run. The worktree was clean before this file was
created: no staged or unstaged implementation diff, no reset/clean/checkout,
no rebase, no provider call, no experiment rerun, and no protected-outcome
access. The prior five auditors (Halley, Bohr, Pauli, Poincare, and Godel)
were not respawned.

The apparent `json-voucher-service` repository observation was a shell-wrapper
false alarm. Explicit `git -C` verification resolves this worktree to
`samindriano/idx-trade` and the canonical local checkout to
`integration/forward-eod-automation-monitoring@b94b272eddede0432e2fbe4acb2915e57a716bcb`.

## Recovered provisional findings

The following are audit findings, not new scientific results:

1. Multiple core data paths are fail-open for ambiguous booleans, malformed
   dates, duplicate/conflicting rows, incomplete provider frames, mutable
   manifests, source-authority metadata, and PIT observation domains. The
   highest-confidence example is textual `"False"` being converted to `True`
   by `astype(bool)`/`bool(...)`, allowing incomplete coverage or unverified
   flags to pass.
2. The canonical Windows EOD checkout contains the primary capture/model
   runtime, but not the accepted O2.1 sealed-shadow and Reliability V1 modules.
   Those modules exist on separate accepted branches and corresponding
   2026-08-12 external artifacts exist. Automatic production of those sidecars
   by the installed canonical task is therefore not established. This finding
   is `COORDINATE_WITH_ACTIVE_LANE` because forward runtime/test-gap ownership
   is active.
3. The canonical model fingerprints checked directly against external runtime
   files: V2 model/manifest, V3-B model/manifest, and O2 model/manifest hashes
   match the frozen runtime constants and accepted checkpoint values.
4. The current canonical EOD task is enabled/Ready with the intended 18:00
   Asia/Jakarta daily trigger, logon catch-up, StartWhenAvailable, and
   IgnoreNew settings; the legacy Open archive task is disabled and Stockbit
   remains a separate enabled task. This is operational evidence only and does
   not prove sidecar completeness.
5. Decision lineage is fragmented across divergent branch-local ledgers.
   `origin/main:coordination/TEAM_STATUS.md` is the controlling ownership
   ledger, while rich branch copies of `CURRENT_STATUS`/`PROJECT_LEDGER` are
   historical snapshots. The Stockbit row previously named the data branch
   while anchoring verification at an integration-branch commit; this is a
   stale/ambiguous reference to correct in the final coordination update.
6. Accepted artifact manifests generally preserve strong model and input
   hashes, but several runtime loaders do not enforce the complete accepted
   artifact bundle, counter ownership, environment/source lineage, or status
   manifest. These are `COORDINATE_WITH_ACTIVE_LANE` where they touch forward
   evaluator/runtime code.
7. Dependency reproducibility is incomplete in the repository contract:
   `pyproject.toml` uses ranges and no lock/hash file is tracked. External O2
   environment evidence records exact installed versions, but this is not a
   repository-enforced resolver lock.

## Ownership and stop rules

Do not patch the active Canonical EOD adversarial test-gap audit, Canonical
data-source/provenance registry, or Forward-100 evaluator execution review.
Those findings will be documented with explicit coordination labels. This audit
may apply only a small non-overlapping documentation/coordination correction;
it must not change model semantics, data contracts, forward counters,
protected-outcome guards, or research artifacts.

Next bounded actions: directly reverify only the high-severity examples,
classify findings as confirmed defect/documentation inconsistency/already-owned
remediation/false positive, write the comprehensive audit checkpoint and
handoff, then update only this lane in `origin/main:coordination/TEAM_STATUS.md`
after refetching it.
