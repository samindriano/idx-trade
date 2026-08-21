# Decision Economic Comparison V1 — Implementation Notes

Status: IN PROGRESS

Goal: compare naive daily Top10 and frozen Decision V1/V2/V3 economically on the already-consumed 600-session Decision development window. This is intentionally a single lightweight comparison lane after extensive structural research.

Design commitments before observing economic results:

- signal/Decision state is formed at session `t` after EOD;
- target changes are implemented at next official session open `t+1`;
- equal-weight target allocation across held names; unfilled seats remain cash;
- gross and transaction-cost-adjusted results are both reported;
- transaction-cost sensitivity is fixed before execution, not tuned to favor a policy;
- no policy threshold or ranking rule changes are permitted;
- results are development evidence only because the 600 sessions have been heavily inspected during Decision research.

Implementation must fail closed if the execution-price or corporate-action-safe return lineage cannot be tied to already accepted artifacts.
