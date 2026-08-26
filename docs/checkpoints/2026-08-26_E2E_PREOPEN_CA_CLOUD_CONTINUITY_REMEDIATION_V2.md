# E2E PREOPEN_CA Cloud Continuity Remediation V2

Date: 2026-08-26 Asia/Jakarta

## Corrected lineage

This successor is based exactly on accepted E2E implementation:

`6a906c5ea8681e07b8e9c47a256f85144c34951e`

The earlier draft PR #100 was accidentally based on `main`, which only carries the production launcher and does not contain the authoritative E2E implementation modules. Its first collection failure therefore was not merely an import-style problem. This V2 remediation is built on the accepted integration lineage instead of retargeting a diverged branch.

## Scope

- add durable operational `PREOPEN_CA` checkpoint before 09:02 WIB;
- bind fresh PREOPEN CA acquisition on execution day E to prepared D->E lineage;
- use D `POST_EOD` journal as immutable parent;
- preserve D->E CA reconciliation scope;
- restore checkpoint on a fresh E PREOPEN runner before Official Open execution;
- preserve same-session PREOPEN/POST_EOD terminal snapshot precedence;
- preserve original immutable T0 session across later POST_EOD sessions.

## Additional hardening

- checkpoint snapshot metadata must bind the actual snapshot SHA;
- checkpoint result child must carry all no-outcome/no-PaperState/no-order/no-fill guards as false;
- code identity binds repo, exact commit, and runner SHA;
- one-shot session iterables are materialized once before parent snapshot lookup;
- divergent immutable checkpoint reruns fail closed.

## Boundaries

No model/refit/rescore/science change. No outcome/protected-forward access. No Decision/Sizing/Execution policy change. No retroactive execution. No production workflow/schedule change. No live provider/R2 write from tests. Production remains pinned to `6a906c...` and V2 until this successor passes exact-head and merge-ref review and a separate activation PR is explicitly authorized.
