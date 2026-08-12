# Signal-research HLCV contract

This contract is separate from `EXECUTION_GRADE_OHLCV`. It does not weaken or
certify the strict execution-grade DATA GATE.

## Included row

A row is included only when all of the following hold:

- the security is an authoritative point-in-time common share in scope;
- listing existence is `LISTED` on the exact exchange session;
- official IDX execution evidence classifies the exact session as `ACTIVE`;
- High, Low, Close, and Volume are positive and valid;
- the OHLC envelope is valid (`High >= max(Low, Close)` and
  `Low <= min(High, Close)`);
- Regular-Market Value is retained when available;
- official split/reverse-split integrity is verified for the complete window;
- price provenance is explicit and approved.

## Open semantics

Open is optional for signal research. It may be null when no defensible Open
evidence exists. It is never synthesized, forward-filled, replaced with zero,
or inferred from the previous close. `open_available` and
`open_evidence_status` must make the state explicit.

## Unknown semantics

`UNKNOWN` rows are excluded from signal features, labels, liquidity metrics, and
execution paths. They are never relabelled as `ACTIVE`, `NO_TRADE`, or
`SUSPENDED`. The strict execution-grade contract continues to require zero
UNKNOWN sessions.

## Permanent layer distinction

- `EXECUTION_GRADE_OHLCV`: strict raw OHLCV contract; Open required; strict
  1260 remains `FAIL` until its own gate passes.
- `SIGNAL_RESEARCH_HLCV`: ACTIVE-only HLCV research contract; Open nullable;
  certification is valid only with an independent GO diagnostic and manifest.
