# Price / Trend / Confirmation State V1 — Test Plan

Focused validation must establish:

1. rising long history -> `UPTREND` + rising MA200 context;
2. falling long history -> `DOWNTREND` + falling MA200 context;
3. flat 80-bar history -> `BASING` while MA200 remains `UNAVAILABLE`;
4. breakout with >=1.5x prior-20 median volume -> `BREAKOUT_CONFIRMED`;
5. same price breakout without volume expansion -> `BREAKOUT_WEAK_VOLUME`;
6. breakout followed by close below its level within five observations ->
   `FAILED_BREAKOUT_RECENT`;
7. source `t` output is byte/field invariant when target `t+1` data is later
   appended or changed;
8. outcome-like columns fail closed;
9. duplicate identities fail closed;
10. insufficient history returns categorical `INDETERMINATE`;
11. no Open column is required;
12. invalid H/L/C geometry fails closed.

Full repository pytest and `git diff --check` remain required at local review.
