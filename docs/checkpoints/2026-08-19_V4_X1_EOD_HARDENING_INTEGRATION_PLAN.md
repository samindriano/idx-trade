# V4-X1 EOD Auto-Score — Accepted EOD Hardening Integration Plan

Date: 2026-08-19 Asia/Jakarta

Deployment remains blocked until accepted canonical EOD adversarial hardening `7b21c50d278b13c8e94cdebddd4ca35765d7274e` is integrated into `integration/v4-x1-eod-auto-score-v1`.

The merge base is `b94b272eddede0432e2fbe4acb2915e57a716bcb`.

Integration rule:

- retain V4-X1 morning prior-session catch-up and conservative 18:00 current-day boundary;
- retain the accepted EOD exact requested-session validation and no-progress loop guard;
- adopt accepted `forward_monitoring`, `forward_model_runtime`, IDX provider/session and security-master hardening byte-for-byte from `7b21c50` where the auto-score branch has no competing change;
- retain/add both hardening test families;
- preserve one canonical provider/capture path only;
- create explicit merge ancestry to `7b21c50` after the resolved tree is constructed;
- rerun accepted EOD adversarial tests plus X1 pipeline tests and runtime verification before scheduler deployment.

No Scheduled Task repoint is authorized by this checkpoint.
