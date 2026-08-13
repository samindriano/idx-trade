# Repository-Wide Scientific Integrity Audit — Independent Acceptance

Date: 2026-08-13 (Asia/Jakarta)
Reviewed branch: `codex/scientific-integrity-audit-v1`
Reviewed HEAD: `1a3d785b10e33af1f6f723fb4a23cf8a61980b0a`
Decision: `REPOSITORY_SCIENTIFIC_INTEGRITY_AUDIT_ACCEPTED_NO_GO_FOR_REPRODUCIBLE_RESEARCH_RELEASE`

## Verdict

The audit verdict `NO-GO_FOR_REPRODUCIBLE_RESEARCH_RELEASE` is accepted.

This verdict is scoped to repository-wide reproducibility/PIT/data-integrity readiness. It does **not** reverse accepted historical model/research verdicts and does not assert that frozen V2, V3-B, O2, Expected Payoff, Reliability, or O2.1 results are invalid. The audit found concrete fail-open infrastructure paths that prevent the repository from being represented as generally reproducible/PIT-safe until remediated.

## Independently verified current-main defects

Independent review confirmed directly in current main:

1. `canonicalize_coverage_windows()` coerces `is_complete` with `astype(bool)`, so textual values such as `"False"` are truthy and can incorrectly authorize ACTIVE state downstream.
2. `build_security_master()` parses finite `listed_to` values with `errors="coerce"`; malformed non-null end dates become `NaT`, which is subsequently interpreted as open-ended.
3. `canonicalize_ohlcv()` silently resolves duplicate dates with `drop_duplicates(..., keep="last")`, including conflicting bars, without conflict diagnosis.
4. `source_fingerprints()` records missing source files as `None`, and `write_manifest_atomic()` atomically replaces an existing manifest path rather than enforcing immutable/write-once publication.

These defects are sufficient to uphold the repository-wide NO-GO without relying solely on orchestration/subagent summaries.

## Accepted additional findings

The audit's additional findings are accepted as documented risks/coordination items, including incomplete provider/source authority enforcement, PIT/session-domain enforcement gaps, mutable artifact-bundle publication, and the absence of accepted O2.1/Reliability V1 modules in the currently scheduled canonical EOD checkout. Future-session automatic sidecar production is therefore not established merely by the existence of 2026-08-12 sidecars.

Model/hash checks for V2, V3-B, and O2 were consistent with frozen runtime/manifests, and the historical decision lineage reviewed by the audit showed no substantive verdict reversal.

## Validation caveat

The audit recorded `39 passed, 1 failed` for its targeted test run. The remaining failure is an existing storage-test expectation mismatch owned by an active engineering boundary. It does not invalidate the factual audit findings, but it is additional evidence that the repository is not currently clean enough for a reproducible-research release claim.

## Remediation ownership

This audit lane is complete. It should not independently patch defects already owned by active lanes.

- Canonical EOD adversarial test-gap lane owns EOD/runtime/session/artifact recovery hardening.
- Canonical data-source/provenance registry owns source authority/status representation and contradiction/staleness validation.
- Forward evaluator is separately accepted for pre-vault engineering and remains gated from protected outcome access.

The repository-wide NO-GO may be reconsidered only after the confirmed P1 fail-open paths and relevant integration/provenance blockers are remediated and independently re-audited.
