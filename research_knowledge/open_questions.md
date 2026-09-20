# Open Questions

Each question has an ownerless evidence requirement and a stopping rule.

| ID | Question | Current state | Smallest useful next evidence | Stop/reopen rule |
|---|---|---|---|---|
| Q-001 | What is the final authority for minimum-20 versus min-periods-60? | `POLICY_AUTHORITY_MISSING / PROVENANCE_NARROWED` | Hash-bound policy/contract binding whether the pre-protocol 20-in-60 liquidity rule governs this new candidate protocol | Do not regenerate until resolved |
| Q-002 | Is eligibility distinct from feature warm-up and rolling estimator stability? | `SUPPORTED_PARTIAL / COUNTERFACTUAL CONFIRMED` | The 20-vs-60 replay shows C2 ranks unchanged because feature warm-up remains 60, while C1/C3/C4 change under the mask; no final policy binding | Record ambiguity if no authority; do not mix masks |
| Q-003 | Is the historical population complete and survivorship-safe? | `BLOCKED_BY_PIT` | Daily PIT universe with delisted/relisted/ticker-reuse/issuer identity | No predictive evaluation without it |
| Q-004 | Are price features on a stable CA/issuer basis? | `BLOCKED_BY_DATA` | Event-to-window, issuer/ISIN, effective/knowledge-time basis evidence | No rescale/infer/repair |
| Q-005 | Are source revisions/publication times known? | `BLOCKED_BY_PIT` | Vintage/publication metadata for financial/flow/source archives | No feature admission without it |
| Q-006 | What is executable historical capacity? | `BLOCKED_BY_DATA` | PIT ADV/spread/queue/fill/capacity data | Proxy economics remain proxy-only |
| Q-007 | What common support would C1/C2/C3/C4 use? | `METHODOLOGY_READY` | Policy decision plus admitted population; no target values needed to design | Prepare methodology, do not score outcomes |
| Q-008 | Does verifier logic share buggy producer helpers? | `OPEN_TOOLING_AUDIT` | Synthetic adversarial fixtures and helper dependency inspection | Never use protected outcomes as fixtures |
| Q-009 | Are old PASS outputs hash-bound to current code/policy? | `PARTIALLY_RESOLVED` | Re-run verifier and compare embedded code/contract/packet hashes | Stale output is non-authoritative |
| Q-010 | Are there new local sources with admission-changing semantics? | `LOCAL_SURFACE_CLOSED` | Only a genuinely new artifact/source contract | Do not repeat broad searches |
| Q-011 | Does the verifier catch producer semantic mutations and encoded protected payloads? | `SUPPORTED_LIMITATION / FALSE_GREENS_CONFIRMED` | A reviewed semantic schema allowlist, independent formula challenger, and explicit verifier-version pin | Do not use PASS as semantic proof |
| Q-012 | What native/common support should a future C1-C4 comparison use after policy resolution? | `METHODOLOGY_READY` | Recompute the census after eligibility/source admission | Never compare candidate metrics on silently different support |
| Q-013 | Which historical families still require exact source replay to resolve a disputed classification? | `BOUNDED_REPLAYABILITY_GAP` | A genuinely new artifact or a concrete disputed claim tied to an exact old implementation | Do not recreate old work from curiosity; use the family map and latest PIT/integrity adjudication |
| Q-014 | Does the authority packet enforce nested schema and verifier-version freshness? | `SUPPORTED_LIMITATION / FALSE_GREENS_CONFIRMED` | Reviewed nested schema allowlist and expected verifier code/version hash | Keep protected boundary closed; PASS remains scoped |
