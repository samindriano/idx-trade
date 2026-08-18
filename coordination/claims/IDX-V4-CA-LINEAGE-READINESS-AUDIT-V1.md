# Claim — IDX-V4-CA-LINEAGE-READINESS-AUDIT-V1

status: ACTIVE
owner: ChatGPT/V4-CA-Lineage-Readiness-Audit
branch: review/idx-v4-ca-lineage-readiness-audit-v1
parent: data/idx-v4-ca-targeted-schedule-evidence-v1@a980d33e9e4ea63306c6af3cf174c329e58f49e6

## Scope

Independent read-only scientific/engineering audit of the V4 corporate-action continuity lineage and the post-CA V4 execution path. The audit may add only review/checkpoint artifacts and test/audit helpers if needed; it must not change corporate-action semantics, frozen gates, V4 target/evaluation contracts, provider acquisition logic, model hyperparameters, or protected/fresh-forward outcome access.

Primary questions:

1. Can any prior CA result be invalidated by a lineage, identity, parser, date-binding, coverage, conflict, or replay error?
2. Can the prepared targeted seven-event lane produce a false positive/false negative continuity verdict because of stale pins, path drift, event-identity transcription, evidence union, or classifier overlay behavior?
3. If continuity later certifies, is the V4 target/materialization/evaluation implementation actually ready to execute the frozen V4-1/V4-2/V4-3 contracts without hidden engineering or provenance blockers?

No provider calls, no local D: access, no target materialization, no model fit, no performance computation, no protected/fresh-forward outcome access.
