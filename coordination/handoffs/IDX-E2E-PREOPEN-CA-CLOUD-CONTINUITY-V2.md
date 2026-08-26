# IDX E2E PREOPEN_CA Cloud Continuity V2 Handoff

Corrected successor branch: `fix/e2e-preopen-ca-cloud-continuity-v2`
Accepted base: `6a906c5ea8681e07b8e9c47a256f85144c34951e`

The earlier draft PR #100 is not an acceptable implementation base because it was created from `main`, which carries the production launcher but not the authoritative E2E implementation tree. Treat PR #100 as superseded once this corrected lane is validated.

Current acceptance sequence:
1. exact-head full CI;
2. targeted PREOPEN_CA checkpoint/lineage audit;
3. synthetic fresh-runner D POST_EOD -> E PREOPEN_CA -> E PREOPEN replay;
4. merge-ref CI;
5. only after explicit authorization, merge to integration;
6. separate main activation PR for V3 runner pin and PREOPEN_CA schedule.

Production must remain on V2 until the separate activation step. Genuine future-session proof remains required before LIVE_ACCEPTED or Windows fallback retirement.
