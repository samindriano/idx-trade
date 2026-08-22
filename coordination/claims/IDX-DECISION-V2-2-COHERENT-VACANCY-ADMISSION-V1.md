# IDX Decision V2.2 Coherent Vacancy Admission

Date: 2026-08-22 Asia/Jakarta

Status: `ACTIVE`

Owner: `ChatGPT/Decision-V2.2`

Branch: `research/idx-decision-v2-2-coherent-vacancy-admission-v1`

Purpose: evaluate exactly one minimal calibration of frozen Decision V2 on the already-consumed 600-session Decision development window after V2.1 severe-exit acceleration was rejected economically.

Single rule change: preserve exact V2 exit/patience logic, previous-rank confirmation, temporary underfill, and ordinary soft replacement. For **vacancy fills only**, a V2-qualified challenger (current consensus Top10, previous consensus <=20) may fill cash only when its current H5 and H10 alpha-head ranks are both <=20. Head ranks are derived deterministically from the already-persisted V4-X1 `alpha_h5` and `alpha_h10` columns. A qualified challenger blocked from vacancy fill remains eligible for the original V2 soft-replacement stage; no blanket admission veto is introduced.

The `<=20` coherence boundary reuses V2's frozen retention/acceptable-zone semantic threshold; it is not searched or tuned. No alternative V2.2 variants, no threshold sweep, no exit changes, no alpha refit/rescore, no provider/network calls, no protected/fresh-forward access, and no executable historical NAV/PnL claim.