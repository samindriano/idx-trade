# V4-X1 Forward CA Feature-Basis Firewall Review Remediation V3

Status: `FORWARD_CA_FEATURE_BASIS_FIREWALL_REVIEW_READY_V3`

This checkpoint records the narrow V3 remediation on the existing review
branch. It remains outcome-blind and is not a production activation or a
certificate for any retained session.

## Review blockers closed

1. The clean panel maximum is retained as `HISTORICAL_PANEL_END`. Official
   scoring sessions come from the exact frozen scorer calendar construction:
   its historical official-session artifact combined with the prospective
   official calendar. Transition windows use that official-session index, not
   calendar days or clean-panel row presence. A forward target may therefore
   follow the clean panel without being incorrectly classified as unofficial.
2. The detached evidence producer is now checked against an external,
   separately supplied `trusted_producer_contract`. Bundle claims cannot choose
   their own authority. Missing or invalid production configuration fails
   closed with `PRODUCER_TRUST_ANCHOR_MISSING` or an explicit anchor mismatch;
   no production producer is fabricated. The test suite injects only a test
   anchor and rejects a complete internally self-signed bundle.
3. Fresh candidate OPEN provenance is bound row-by-row. Candidate
   `source`/`source_ref`/`source_sha256`/`observed_retrieved_at_utc` must agree
   with geometry's OPEN declaration, the retained manifest child, and its
   source identity. A per-ticker binding is supported, while any mismatch
   rejects the whole session before the scorer.

## Preserved integrity boundaries

The whole-session `PopulationScoreGate` remains the only pre-scorer veto. No
frozen scorer, model, formula, weight, feature order, population construction,
counter, PaperState, R2, provider, outcome, scheduler, or production artifact
was changed. No `listed_to` value is rewritten into frozen scoring code.
Cryptographic hashes prove byte identity and provenance binding; they do not by
themselves establish same-basis semantics.

The retained real-evidence outcomes remain unresolved: 44 retained transitions
remain `BASIS_UNKNOWN`/unresolved, and 15 retained forward sessions remain
`SOURCE_CAPTURE_UNRESOLVED`. No historical certificate, backfill, or credit is
created by this remediation.

## Runtime status and next gate

The runtime has no genuine production feature-basis producer trust anchor. A
real production call without that independently reviewed anchor remains
scientifically non-admissible. The next action is independent review of this
candidate and, only if accepted, a separately authorized producer-anchor
configuration and future genuine scheduled proof. Production deployment,
dispatch, provider access, outcome access, and merge remain out of scope.

## Validation target

The candidate is review-ready only with focused calendar, producer-anchor,
OPEN-provenance, and runtime tests; full repository tests; frozen-pin checks;
Python compilation; JSON/YAML parsing; and `git diff --check` all passing.
