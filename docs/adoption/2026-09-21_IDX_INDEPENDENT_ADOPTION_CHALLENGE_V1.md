# Independent Adoption Challenge V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **PASS LOCAL / SYNTHETIC ONLY**

This is a MAIN-run independent challenge of the assembled candidate. It is
not a production, provider, scheduler, cloud, capture, telemetry, canonical
data, protected-outcome, or live-migration test. A delegated observer did not
return a result; the checks below were executed directly against the candidate
after that observer was stopped.

## Identity under challenge

- branch: `codex/idx-authoritative-runtime-adoption-20260921`;
- candidate code HEAD: `66140b05`;
- documentation HEAD after this report is committed separately;
- candidate base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`;
- immutable hardening source: `8ceec523d49500949b5ecf46e3b862cd4eb1c4fd`;
- active operational checkout remains `32eaaa8e50d0521de7faef98faa8081219bc667b`.

## Challenge results

| Surface | Independent check | Result |
|---|---|---|
| source extraction | `git diff 8ceec523..66140b05 -- src tests scripts` contains only the six intentional candidate remediation files | PASS |
| lineage | merge-base is `402fca4`; `402..8ce` is 109 commits and `32..402` is 12 commits; no active checkout mutation | PASS |
| phase entrypoints | AST audit found `attest_deployment`, `load_phase_runtime_binding`, `require_phase_attestation`, and `exclusive_run_lock` in all four phase scripts | PASS |
| phase CLI surface | all four `--help` commands parsed successfully | PASS |
| migration complete/partial/pending | seven independently constructed envelopes produced the expected typed classifications/dispositions | PASS |
| migration adversarial input | unknown field rejected with `MIGRATION_COMPATIBILITY_PAYLOAD_NOT_CANONICAL` | PASS |
| duplicate event safety | conflicting duplicate event bytes produced `REQUIRES_RECONCILIATION/BLOCKED` | PASS |
| quantity safety | over-plan fill vector produced `REQUIRES_RECONCILIATION/BLOCKED` | PASS |
| orphan safety | positive position without plan/fill vector produced `UNKNOWN_ORPHANED_PARTIAL/BLOCKED` | PASS |
| identity boundary | source envelope hash is retained; deterministic `.JK` canonicalization matches the existing contract; external authority remains unadmitted | PASS / EXTERNAL GATE OPEN |
| integrated replay corroboration | selected rehearsal nodes: 29 passed; focused runtime/config/controller/migration tests: 111 passed; full suite: 905 passed | PASS SYNTHETIC |
| Official Open/scheduler corroboration | synthetic verification and scheduler contract tests: 16 passed | PASS SYNTHETIC |
| rollback assumptions | rollback matrix remains forward-only and does not claim unsafe V2-to-V1 downgrade | PASS DESIGN / LIVE GATE OPEN |

## Semantic-chain review

The challenge inspected the required chain:

`obligation -> Decision -> sizing -> execution -> snapshot -> CA -> reconciliation -> restart`

The candidate-local tests preserve quantity obligations, parent/payload
hashes, pending ownership, CA timing boundaries, recovery quarantine, and
replay fences. No semantic false-green was found that is locally fixable
within the current scope. This conclusion is limited to synthetic fixtures and
the candidate checkout; it is not evidence of live economic correctness.

## Remaining gates are external, not hidden failures

- authoritative PIT identity artifact is not admitted;
- Decision-seat close/pairing/expiry/FULL/concentration/tax policy remains
  explicitly fail-closed;
- real artifact migration requires a separately authorized immutable input root;
- active task checkout/config/runner repin is not authorized;
- no controlled canary or production promotion is authorized.

## Verdict

`INDEPENDENT_ADOPTION_CHALLENGE: PASS_LOCAL_SYNTHETIC`

No material locally fixable defect was found by this challenge. The result
does not change the separate `BLOCKED`/`NO-GO` external gates in the adoption
packet.
