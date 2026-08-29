# IDX-Trade adversarial challenge audit

This is an evidence-only review branch published on 2026-08-29. It is based on
the exact audited `origin/main` commit:

`adc071d6fd7e8009557bed27b1224217421514ae`

The production E2E implementation pin observed during the audit was:

`6b6a41114a910287b413a099a36d59c5e057a8f2`

The audit artifacts were copied from the external audit workspace without
including source datasets, provider captures, credentials, or runtime state.
The branch contains findings and reproducibility evidence only; it does not
apply remediation and must not be treated as a production implementation
branch.

## Contents

- `final_report.md`: consolidated challenge results and dispositions.
- `candidate_findings.csv`: initial finding inventory.
- `challenge_ledger.csv`: challenge-by-challenge verdicts and evidence.
- `surviving_findings.csv`: findings surviving the challenge process.
- `root_cause_clusters.csv`: separated root-cause clusters.
- `audit_surface_coverage.csv`: inspected and unsaturated surfaces.
- `unresolved_questions.csv`: items requiring further evidence or policy.
- `reproducers.md`: read-only reproduction notes.
- `checkpoint.md`: audit checkpoint and continuation state.
- `artifact_hashes.sha256`: SHA-256 manifest for the nine substantive artifacts.

## Review boundary

The audit is outcome-blind and static-evidence based. It does not claim live
provider, outcome, R2, or PaperState proof. The checkpoint status is
`AUDIT_NOT_SATURATED_CONTINUATION_RECOMMENDED`; newer production or branch
evidence should supersede any historical note in these artifacts.
