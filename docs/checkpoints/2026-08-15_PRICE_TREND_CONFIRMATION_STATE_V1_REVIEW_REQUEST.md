# Review request — Price / Trend / Confirmation State V1

Independent review should focus on semantic correctness rather than historical
performance.  In particular, verify that:

- prior breakout levels exclude the current bar;
- t -> t+1 assignment is exact and target data is unnecessary;
- rolling evidence never accesses future observations;
- `BASING`, `EARLY_REVERSAL`, `UPTREND`, and `DOWNTREND` precedence is internally
  consistent;
- breakout and volume confirmation remain separate evidence axes;
- the optional MA200 context does not incorrectly gate the main trend state;
- thresholds are clearly descriptive engineering constants, not alpha claims;
- no Open/intraday/outcome/model dependency has entered V1.

No performance test or threshold tuning is authorized during this review.
