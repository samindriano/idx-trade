# E2E Cloud Producer Provenance Pin Remediation V1

Status: REVIEW pending independent review; no merge, scheduler mutation, live
provider, R2, model, or outcome execution was performed.

Implementation branch checkpoint: `integration/e2e-cloud-first-orchestration-v1`
at implementation commit `f38ef328e90857d94daa27d01655e095b7a0acca` before
this documentation update. PR #93 is repinned to that exact current PR #92
head for the pending, unmerged integration lineage.

## P1 root cause

The downstream Official Open cloud admission gate already required
`runner_provenance.runner=GITHUB_ACTIONS` and
`runner_provenance.github_event_name=schedule`, but the active producer
workflow was still checking out `8a96a3d9caebfbd2c0235234e9394afc04693efa`,
which predates the event-name field. A scheduled capture from that workflow
would therefore be rejected by the consumer. Event provenance alone was also
too broad because it did not bind evidence to one reviewed producer
implementation.

## Remediation

- The producer continues to record `GITHUB_EVENT_NAME` and remains
  `CAPTURE_ONLY_NOT_EXECUTION_ADMITTED`.
- The downstream materializer now requires an explicit
  `expected_capture_code_ref` and accepts only a lowercase/uppercase-normalized
  40-hex commit SHA. It rejects missing, malformed, or mismatched
  `runner_provenance.capture_code_ref` values before local materialization.
- The cloud consumer passes
  `E2E_CLOUD_EXPECTED_OFFICIAL_OPEN_CAPTURE_CODE_REF` from the repository
  variable `IDX_TRADE_OFFICIAL_OPEN_CAPTURE_CODE_REF`.
- The producer workflow uses that same repository variable and has a
  pre-check requiring a non-empty 40-hex SHA before checkout. An unset variable
  fails closed; it cannot silently fall back to the old producer checkout.
- Workflow-dispatch/manual evidence, late/future evidence, capture timing,
  outer/inner contract, child hashes, capture-only marker, and no-retroactive
  guards remain unchanged.

## Required deployment sequence

1. Merge the accepted PR #92 implementation.
2. Obtain the exact accepted integration merge SHA.
3. Repin the PR #93 E2E launcher implementation checkout to that merge SHA.
4. Repin the default-branch Official Open producer to a commit containing the
   scheduled provenance field.
5. Set `IDX_TRADE_OFFICIAL_OPEN_CAPTURE_CODE_REF` to that exact same accepted
   producer pin; both producer and consumer then use the same value.
6. Only after those pins and the live private-input evidence are verified may
   provisioning, live testing, or activation be considered.

The repository variable is intentionally not changed by this remediation, so
no temporary PR-head SHA is treated as the permanent accepted producer
identity.

## Tests and boundary

The focused cloud tests cover old 8a96-style missing event provenance,
workflow-dispatch, absent/malformed/wrong producer code refs, correct event +
correct pin admission, and the existing late/future timing rejection tests.
No real cloud capture, provider call, scheduler call, model access, outcome
access, or merge was performed.

Final local validation after the implementation change: focused cloud tests
`36 passed`; E2E/Official Open regression `149 passed`; full pytest `879
passed`, `0 failed`, `0 skipped`, with the same 3 pre-existing FutureWarnings;
all changed Python entrypoints compiled/imported, both workflow YAML files
parsed, and `git diff --check` passed.
