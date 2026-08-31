# INC-001 Residual Transition Certification V17 Handoff

Date: 2026-08-31 Asia/Jakarta
Lane: `data/ca-aware-feature-basis-remediation-v1`
HEAD: `13aac8150bda29adac360af8affb3706f0911391`

## Decision

`INC001_RESIDUAL_TRANSITION_CERTIFICATION=COMPLETE_WITH_RESIDUAL_BLOCKERS`

V17 promotes only DIVA, SMDR, TMAS, and TUGU from exact existing V16 event
IDs. BMRI, BBRM, and SKRN remain `UNRESOLVED`. Counts are conserved:
412 source rows, 387 events, 46 non-basis rows, 27 proven linkages, and
resolved/unresolved `163/178 -> 167/174`.

## Evidence binding

Primary V17 artifact:

`D:\Documents\Project\idx-ca-economic-event-reconciliation-20260831-v17-residual-certification-final`

Manifest SHA-256:
`8d2139c9388c6b94c4131ca692f0de3add433c294e4a7b20f2db6d7f22b106e8`

Controlling V16 manifest SHA-256:
`3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030`

Residual official-document manifest SHA-256:
`3d4cbae5dfd651eec364350a6155f8b08ba7e6e713a9979f36df7a0493e102c3`

The corrected independent verifier returned `42/42 PASS`; targeted CA tests
returned `25 passed`; full pytest and relevant compilation passed. V16 was not
written.

## Guardrails and remaining blockers

The selected semantic is only the explicit first regular/negotiated-market
trading session on the new raw-price basis. ZAPI/router, listing, record,
distribution, effective, candidate, and depository dates are not transition
authority. No population completeness, historical as-of, exhaustive negative
authority, Data/Research admission, or INC-001 closure claim is made.

No outcomes/targets, Phase-E, fit/refit/score, market-provider acquisition,
counter/PaperState/R2, production execution, deployment, backfill, or Actions
rerun occurred. The failed residual Actions run was not retried because it had
no runner execution.

## Handoff boundary

The next bounded action is a read-only promotion blast-radius audit. It must
not modify frozen science, runtime behavior, V16, production state, or the
canonical source population.
