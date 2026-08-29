# Read-only synthetic reproducers

These are instructions and observations only; no reproducer was written into
the target repository and no provider, R2, secret, outcome, PaperState,
scheduler, or counter was accessed.

1. A9: `bool("False") is True`; pass a nonempty string as the value received by
   `data_gate.py` and observe that the gate's local boolean conversion does not
   reject its type. Falsifier: every canonical caller validates strict booleans
   before this function and the contract enforces that boundary.
2. A10: parse `listed_to="not-a-date"` through the generic
   `security_master.py` helper. The generic interval becomes open-ended; the
   pinned Path-A validator at `6b6a411` rejects malformed intervals. Falsifier:
   prove the generic helper is unreachable from every accepted production path.
3. A11: feed two same-date OHLCV rows with different closes to the generic
   normalizer. `keep="last"` leaves one row without a conflict record.
4. A12/A13: include a Saturday or pre-listing row in an otherwise complete
   synthetic frame and compare generic coverage/warmup with official-session
   filtered behavior.
5. A15/A16/A17: construct synthetic score/target/ledger frames preserving
   accepted metadata while changing unbound target values or including a
   non-evaluable row. The gate shape checks do not establish causal generation;
   the pure metric engine consumes its supplied alpha frame.
6. A21: compare `gh workflow list --all` with `git ls-tree -r origin/main
   .github/workflows`; at the audit epoch the result was `registered=23,
   tree=10`, and `gh workflow view` could not find each absent file on the
   default ref. This proves divergence, not harmful execution.
7. A25/A30: compare current Phase-B support counts and frozen verdict in the
   PR #108 R3 handoff. The old 56,602 overlay is explicitly
   `NOT_APPLICABLE_UNPROVEN_ON_CURRENT_SUPPORT`; current admission remains FAIL.
