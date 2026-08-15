# Repository Hygiene V1 — Dry-Run Cleanup Plan

## Scope and safety

This is an audit-only snapshot generated from the fully fetched/pruned local `origin` refs. It makes no branch deletion, tag creation, PR closure, history rewrite, or force-push. Remote branch inventory count: **158**; unique branch names: **158**; generated CSV rows: **158**; main HEAD: `8d250f2a6c12ffee930ac90d38ac528e12a230da`.

GitHub PR/Issue metadata could not be authenticated in this environment (`gh` returned HTTP 401; the public Issue #30 URL was not retrievable). The CSV therefore records `UNAVAILABLE_GITHUB_AUTH` rather than inferring PR numbers or states.

## Classification summary

| Classification | Count |
|---|---:|
| `KEEP` | 61 |
| `ARCHIVE_TAG_THEN_DELETE_BRANCH` | 30 |
| `DELETE_SAFE` | 2 |
| `ABANDONED_NO_DECISION` | 49 |
| `NEEDS_MANUAL_REVIEW` | 16 |

## Proposed archive tags — not created

- `codex/idx-eod-adversarial-tests-v1` → `archive/codex-idx-eod-adversarial-tests-v1-f6a50cfcba36` (`f6a50cfcba3611c89bd71ee1b6b12d9da3dee51a`)
- `codex/scientific-integrity-audit-v1` → `archive/codex-scientific-integrity-audit-v1-1a3d785b10e3` (`1a3d785b10e33af1f6f723fb4a23cf8a61980b0a`)
- `data/broker-margin-source-audit-v0` → `archive/data-broker-margin-source-audit-v0-c7fcec2a5fc5` (`c7fcec2a5fc58e503cf1ea5fbff9e890dcf827ae`)
- `data/financial-pit-adapter-census-v1` → `archive/data-financial-pit-adapter-census-v1-d1cb537e844f` (`d1cb537e844fb8da83551ba462c80c8debb623d4`)
- `data/financial-pit-fact-extraction-hardening-v1` → `archive/data-financial-pit-fact-extraction-hardening-v1-baf0334a1dd6` (`baf0334a1dd6a31e9d88ae978630ec864bfb3410`)
- `data/financial-pit-fact-schema-v1` → `archive/data-financial-pit-fact-schema-v1-4013f90a56ed` (`4013f90a56edc6d8409e6a7514a9170d5f301aff`)
- `data/financial-pit-feature-contract-v1` → `archive/data-financial-pit-feature-contract-v1-6b510d8d254d` (`6b510d8d254dd47973e749ffeae7cf1569069395`)
- `data/financial-pit-feature-materialization-v1` → `archive/data-financial-pit-feature-materialization-v1-7b5ed76c934b` (`7b5ed76c934b32cc7d995cc93870ac16d797e9e4`)
- `data/financial-pit-marketwide-fact-extraction-census-v1` → `archive/data-financial-pit-marketwide-fact-extraction-census-v1-419f0be54a7b` (`419f0be54a7b08ee958c52b8a727be9423286d96`)
- `data/financial-pit-offline-scope-reclassification-v1` → `archive/data-financial-pit-offline-scope-reclassification-v1-45d36eda095e` (`45d36eda095ea975182565804baaf899a9706c58`)
- `data/financial-pit-period-boundary-remediation-v1` → `archive/data-financial-pit-period-boundary-remediation-v1-09e8e8eba738` (`09e8e8eba738e4dcea3c871f0eda83b53cc07c42`)
- `data/financial-pit-revision-lineage-v1` → `archive/data-financial-pit-revision-lineage-v1-58e5e26de464` (`58e5e26de4646794a38e844decf54890696375c5`)
- `data/financial-pit-scientific-notation-remediation-v1` → `archive/data-financial-pit-scientific-notation-remediation-v1-98f409cda994` (`98f409cda9943cc06747e875153c231d950a3221`)
- `data/financial-pit-statement-scope-v1` → `archive/data-financial-pit-statement-scope-v1-e4537c16c501` (`e4537c16c5011d8cafc55bc72e8f04017b874baf`)
- `data/financial-pit-template-drift-audit-v1` → `archive/data-financial-pit-template-drift-audit-v1-f2238f35546d` (`f2238f35546db0934e7ce1203cefc57fa05eec86`)
- `data/financial-pit-v1` → `archive/data-financial-pit-v1-25eaa67a7f54` (`25eaa67a7f5446234db470756fe8b5c12cbb7696`)
- `data/idx-direct-endpoint-audit-v1` → `archive/data-idx-direct-endpoint-audit-v1-87e6947c0121` (`87e6947c0121aba52111d3dc633e05448f6da644`)
- `data/investing-intraday-admission-pilot-v1` → `archive/data-investing-intraday-admission-pilot-v1-5ef879266b4b` (`5ef879266b4b7b88b614ac43b68e73165cab6678`)
- `data/investing-intraday-depth-audit-v1` → `archive/data-investing-intraday-depth-audit-v1-b80bd94daf26` (`b80bd94daf26436092bd5e070c5b4bc70b2a2037`)
- `research/idx-expected-payoff-v0-feasibility` → `archive/research-idx-expected-payoff-v0-feasibility-ecec6835eaee` (`ecec6835eaee70f47a8a1c1b43fc2d14a4c34709`)
- `research/idx-expected-payoff-v1` → `archive/research-idx-expected-payoff-v1-73b75af23222` (`73b75af2322214138e55293a4bb2cb8ed4362c15`)
- `research/idx-reliability-uncertainty-v0` → `archive/research-idx-reliability-uncertainty-v0-a99d53de91df` (`a99d53de91dfc44f9688ba7adead5206d7c7929d`)
- `review/idx-corporate-action-pit-availability-acceptance-v1` → `archive/review-idx-corporate-action-pit-availability-acceptance-v1-c556b0cb607f` (`c556b0cb607f579cfb1071417f3455b3f06db3d7`)
- `review/idx-financial-pit-adapter-census-acceptance-v1` → `archive/review-idx-financial-pit-adapter-census-acceptance-v1-8675b0bc0532` (`8675b0bc05327779a3f39d4b1a3f90b2bfcda551`)
- `review/idx-financial-pit-marketwide-census-acceptance-v1` → `archive/review-idx-financial-pit-marketwide-census-acceptance-v1-4c68b5a3259e` (`4c68b5a3259e89782f6263857630089b93ed04e8`)
- `review/idx-financial-pit-offline-reclassification-acceptance-v1` → `archive/review-idx-financial-pit-offline-reclassification-acceptance-v1-7c94bc8a8737` (`7c94bc8a87374a75fc73687c04c4f8b5b7146595`)
- `review/idx-financial-pit-revision-lineage-acceptance-v1` → `archive/review-idx-financial-pit-revision-lineage-acceptance-v1-903e843f3f53` (`903e843f3f53c14e7bdc7fb1e3d959f2cfe62a66`)
- `review/idx-financial-pit-template-drift-acceptance-v1` → `archive/review-idx-financial-pit-template-drift-acceptance-v1-22774855350d` (`22774855350d5a75b1b568d59b38f0d7205908aa`)
- `review/idx-pit-safe-replay-acceptance-v1` → `archive/review-idx-pit-safe-replay-acceptance-v1-2a70031a73b5` (`2a70031a73b59d60d894d9c9644d143230d52b2d`)
- `review/idx-v2-open-alpha-historical-acceptance-v1` → `archive/review-idx-v2-open-alpha-historical-acceptance-v1-480218599940` (`4802185999409fc3f5db7ae4d6474eef1a6de92d`)

## Proposed DELETE_SAFE candidates — not deleted

- `orchestra-global-policy-rollout` at `21caec5f0eb49b1ad44ac39206f3c8c28a0cea93` — HEAD is fully reachable from main and no tracked scientific decision reference was found.
- `tmp-ignore` at `21caec5f0eb49b1ad44ac39206f3c8c28a0cea93` — HEAD is fully reachable from main and no tracked scientific decision reference was found.

## Proposed stale PR closures — not performed

No PR closure is proposed as an executable action because authenticated PR metadata is unavailable. After an authenticated lookup, review only the non-KEEP candidates above; preserve any PR carrying an unresolved scientific decision or active handoff.

## Manual-review queue

- `data/idx-free-float-effective-supply-v1` at `69cdd303ad937e6bc90d930955f751f1a2686ab0` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: coordination/TEAM_STATUS.md:272; coordination/TEAM_STATUS.md:285; coordination/TEAM_STATUS.md:297; origin/main:coordination/TEAM_STATUS.md.
- `data/idx-historical-statutory-free-float-snapshot-v1` at `4762f4751cb4cc30d348704c7e19e65c47b7a329` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: coordination/TEAM_STATUS.md:510; coordination/TEAM_STATUS.md:523; origin/main:coordination/TEAM_STATUS.md.
- `data/idx-hsc-full-history-ledger-v1` at `b86e3f4906edcc57f8d5f579906321e44d12be06` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: coordination/TEAM_STATUS.md:425; coordination/TEAM_STATUS.md:453; origin/main:coordination/TEAM_STATUS.md.
- `data/idx-lbre-lineage-parser-remediation-v1` at `a42715f027fceb0c7cd24f68e65c9e91b7bfa049` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: coordination/TEAM_STATUS.md:549; coordination/TEAM_STATUS.md:610; origin/main:coordination/TEAM_STATUS.md.
- `data/idx-lbre-monthly-free-float-history-v1` at `f6537c09b5121cc8b185df4fd9d672e305a879d1` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: coordination/TEAM_STATUS.md:638; origin/main:coordination/TEAM_STATUS.md.
- `data/idx-ownership-hsc-source-remediation-v1` at `505448a5bf24545f3538045daaa6b86968e6c6fc` — Lineage or retention decision remains ambiguous. References: coordination/TEAM_STATUS.md:389; coordination/TEAM_STATUS.md:400; origin/main:coordination/TEAM_STATUS.md.
- `data/idx-statutory-free-float-reconstruction-v1` at `9eb73df879d44456adfc8d5f717e6c75be5d07a0` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: coordination/TEAM_STATUS.md:474; coordination/TEAM_STATUS.md:486; origin/main:coordination/TEAM_STATUS.md.
- `data/tradingview-intraday-independent-activity-resolution-v1` at `c943a76fd56872d981a87519c2eb7072c413322c` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: origin/main:coordination/TEAM_STATUS.md.
- `integration/canonical-eod-calendar-parent-attestation-v1` at `32c30d17c7a2d1d5f434f9f6df0c7fb88e2b13ae` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: coordination/TEAM_STATUS.md:577; origin/main:coordination/TEAM_STATUS.md.
- `research/idx-joint-setup-readiness-state-v1` at `0bed7e105ee58a62e0edf89e5148ca2789381929` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: coordination/TEAM_STATUS.md:650; origin/main:coordination/TEAM_STATUS.md.
- `research/idx-stage4-v1` at `899bbf3bb5987e9d345f4c8692a7656fe03a3b0e` — Lineage or retention decision remains ambiguous. References: coordination/TEAM_STATUS.md:59; origin/main:coordination/TEAM_STATUS.md.
- `research/idx-stage4b-calibration-v1` at `f3209705ec4e5fe85e5e5b38035f6d2adf6d31c9` — Lineage or retention decision remains ambiguous. References: coordination/TEAM_STATUS.md:59; origin/main:coordination/TEAM_STATUS.md.
- `research/idx-stage5-ranking-holdout-v1` at `8223899b4bae9b1225334b92908e85689ab8232f` — Lineage or retention decision remains ambiguous. References: coordination/TEAM_STATUS.md:59; origin/main:coordination/TEAM_STATUS.md.
- `review/idx-corporate-action-idx-publication-linkage-v1` at `981e1586038d91392ac0397b12391a1cd37f010f` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: origin/main:coordination/TEAM_STATUS.md.
- `review/idx-corporate-action-pit-availability-provenance-acceptance-v1` at `4f776a8f34eda012d4368287fe37699d4c8dc0dc` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: origin/main:coordination/TEAM_STATUS.md.
- `review/idx-financial-pit-feature-contract-acceptance-v1` at `6b510d8d254dd47973e749ffeae7cf1569069395` — Scientific/documented branch is not reachable from main; deletion would risk losing a provenance anchor. References: origin/main:coordination/TEAM_STATUS.md.

## Interpretation rules applied

- Active, automated, review, waiting, blocked, planned, and parked lanes remain `KEEP`.
- A failed experiment is not deleted merely because it failed; a scientific branch is archive-tag eligible only when its exact HEAD/decision is retained or the status explicitly marks it DONE.
- Fully merged temporary/engineering branches with no tracked decision reference are `DELETE_SAFE`.
- Unreachable or ambiguous scientific lineage is `NEEDS_MANUAL_REVIEW`; `ABANDONED_NO_DECISION` is a classification, not permission to delete without review.
- `main` is retained and is used as a successor when it contains a branch HEAD.
