# Policy and External Gate Log V1

Date: 2026-09-21

The candidate preserves fail-closed behavior. This log deliberately does not
turn unresolved policy into implementation decisions.

| Gate | Current local behavior | Status | Required authority |
|---|---|---|---|
| Decision-seat close status/reason | hash-bound caller policy; malformed values typed-fail | POLICY_ACTIVATION_OPEN | authoritative production status/reason policy |
| paired replacement closure | explicit close/relinquish transition; no implicit default | POLICY_ACTIVATION_OPEN | pairing and lifecycle policy |
| expiry/age-out | no autonomous age-out | POLICY_BLOCKED | authoritative expiry policy |
| FULL quantity semantics | preserved as explicit policy input | POLICY_BLOCKED | authoritative quantity policy |
| post-entry concentration overlay | not implemented | POLICY_BLOCKED | separate reviewed policy |
| dividend tax/net | gross semantics retained | POLICY_BLOCKED | authoritative tax/net policy |
| unsupported structural CA | fail closed | EXTERNAL_BLOCKED | external source/authority contract |
| identity authority admission | caller-supplied hash-pinned artifact only | AUTHORITY_OPEN | external PIT identity authority |
| provider/capture evidence | no provider call in this lane | EXTERNAL_BLOCKED | separately authorized operational proof |

## Identity boundary

IDENTITY CONTRACT READY means the candidate validates a versioned,
hash-pinned, session-correct artifact and resolves all required tickers.
IDENTITY AUTHORITY ADMITTED would require a separate authoritative source and
is not claimed here. Chat-2 research, discovery data, and ZAPI are not
silently promoted to production authority.

## Policy rule

If a policy is required for basic runtime adoption, isolate the exact missing
decision and stop at the gate. Do not invent an answer to make the candidate
pass.

