# Historical Open Capability Audit — Preregistration V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `B_H_MICRO02_OPEN_SOURCE_CAPABILITY_AUDIT`

## Question

How much of the frozen panel's historical `open` field is actually available
for structural research, and what source/provenance limitations prevent it
from being an executable historical Open contract for H-MICRO-02?

This is a data-capability audit, not an alpha test and not a source repair.

## Fixed checks

Using the frozen panel and the existing official-session/tradability-universe
construction, record:

- panel and eligible row/date/ticker counts;
- positive finite `open` coverage and `open_available` consistency;
- coverage by official date and ticker breadth;
- `open_evidence_status` and `price_provenance` composition;
- source transitions across ticker histories;
- positive finite and OHLC-range sanity checks;
- corporate-action and signal-contract metadata distributions.

No missing Open value may be filled, forward-filled, substituted, or promoted.
No outcome, target, provider, cloud, capture, telemetry, canonical dataset, or
protected packet may be accessed.

## Decision boundary

The audit can reclassify the local field from unknown to a more precise
capability status and define what remains missing. It cannot establish
historical available-at timing, source authority, executable fill semantics,
PIT corporate-action correctness, survivorship safety, or predictive value.
H-MICRO-02 cannot become C5 from this audit.

