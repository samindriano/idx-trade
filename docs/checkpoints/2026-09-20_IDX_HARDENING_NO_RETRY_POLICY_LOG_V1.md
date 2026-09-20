# IDX-Trade Hardening No-Retry and Policy-Gap Log V1

## No-retry boundaries

- Do not rerun the old positive partial BUY probe as if it were unresolved;
  remediation must change the quantity state owner.
- Do not patch only `pending_buys`/`pending_sells`; that recreates the known
  ticker-only loss.
- Do not rewrite hashes without binding the actual projected/raw state
  transition.
- Do not add fallback by catching snapshot errors and selecting an arbitrary
  earlier file; recovery must be immutable and fork-safe.
- Do not infer historical plan or residual quantities from current positions.
- Do not use a green historical test that encoded the old contract as proof of
  new semantic completion.

## Explicit policy gaps — not autonomous remediation

- post-entry concentration/rebalancing policy;
- dividend tax/net treatment;
- new Decision thresholds/ranking/admission rules;
- external broker/custodian reconciliation;
- unsupported structural corporate-action admission;
- new alpha/model behavior.

These remain documented blockers unless an existing authoritative project
policy is supplied. This lane records evidence and preserves fail-closed
behavior rather than inventing policy.
