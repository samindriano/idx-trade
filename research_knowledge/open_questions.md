# Open Questions

Each question has an ownerless evidence requirement and a stopping rule.

| ID | Question | Current state | Smallest useful next evidence | Stop/reopen rule |
|---|---|---|---|---|
| Q-001 | What is the final authority for minimum-20 versus min-periods-60? | `POLICY_AUTHORITY_MISSING` | Hash-bound policy/contract/issue history binding semantics | Do not regenerate until resolved |
| Q-002 | Is eligibility distinct from feature warm-up and rolling estimator stability? | `SUPPORTED_PARTIAL` | Protocol plus code lineage show 60 lookback/20 minimum and separate security-master warm-up, but no final binding | Record ambiguity if no authority |
| Q-003 | Is the historical population complete and survivorship-safe? | `BLOCKED_BY_PIT` | Daily PIT universe with delisted/relisted/ticker-reuse/issuer identity | No predictive evaluation without it |
| Q-004 | Are price features on a stable CA/issuer basis? | `BLOCKED_BY_DATA` | Event-to-window, issuer/ISIN, effective/knowledge-time basis evidence | No rescale/infer/repair |
| Q-005 | Are source revisions/publication times known? | `BLOCKED_BY_PIT` | Vintage/publication metadata for financial/flow/source archives | No feature admission without it |
| Q-006 | What is executable historical capacity? | `BLOCKED_BY_DATA` | PIT ADV/spread/queue/fill/capacity data | Proxy economics remain proxy-only |
| Q-007 | What common support would C1/C2/C3/C4 use? | `METHODOLOGY_READY` | Policy decision plus admitted population; no target values needed to design | Prepare methodology, do not score outcomes |
| Q-008 | Does verifier logic share buggy producer helpers? | `OPEN_TOOLING_AUDIT` | Synthetic adversarial fixtures and helper dependency inspection | Never use protected outcomes as fixtures |
| Q-009 | Are old PASS outputs hash-bound to current code/policy? | `PARTIALLY_RESOLVED` | Re-run verifier and compare embedded code/contract/packet hashes | Stale output is non-authoritative |
| Q-010 | Are there new local sources with admission-changing semantics? | `LOCAL_SURFACE_CLOSED` | Only a genuinely new artifact/source contract | Do not repeat broad searches |
