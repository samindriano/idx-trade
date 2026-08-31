# INC-001 Residual Transition Certification V17

Date: 2026-08-31 Asia/Jakarta  
Repository: `samindriano/idx-trade`  
Review lane: `data/ca-aware-feature-basis-remediation-v1`  
Review HEAD: `13aac8150bda29adac360af8affb3706f0911391`  
Outcome-blind: yes

## Decision

`INC001_RESIDUAL_TRANSITION_CERTIFICATION=COMPLETE_WITH_RESIDUAL_BLOCKERS`

The bounded residual pass admitted only exact, unique, retained first-party
evidence for the first regular/negotiated-market session on the new compatible
raw-price basis. It promoted four existing V16 economic events and left BMRI,
BBRM, and SKRN unresolved. No new event population or cross-source linkage was
created.

## Immutable artifacts

V17 artifact root:

`D:\Documents\Project\idx-ca-economic-event-reconciliation-20260831-v17-residual-certification-final`

V17 `MANIFEST.json` SHA-256:

`8d2139c9388c6b94c4131ca692f0de3add433c294e4a7b20f2db6d7f22b106e8`

Controlling V16 root:

`D:\Documents\Project\idx-ca-economic-event-reconciliation-20260831-v16-composite-policy`

V16 manifest SHA-256: `3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030`

The V17 input binding also retains the prior exact-evidence manifest
`2cb9eba292c8c8a3cda7e61a9b03f604bb28b0d0f01520f33f64e796a3bc69bc` and the
bounded residual-run manifest
`3d4cbae5dfd651eec364350a6155f8b08ba7e6e713a9979f36df7a0493e102c3`.

## Exact bounded result

| Ticker | Controlling V16 event | Evidence result | V17 result |
|---|---|---|---|
| BMRI | `DERIVED-7c3839ed4b2e568421553225b23d3e1f1dd08fa005381d748d1a9ae23f84c3df` | Issuer document HTTP 403; unavailable | `UNRESOLVED` |
| BBRM | `DERIVED-a0a40179e4fb4c7c16dffd4397a0b8b061c2d088e751bab087324a565d9cb3d8` | Annual report found, but no required date/market semantic | `UNRESOLVED` |
| SKRN | `DERIVED-858c23a6bf4ecfe67fa30a03ec2afcd7b13d65c0cfc6836545991cd832d6703f` | Issuer documents unavailable because TLS verification failed | `UNRESOLVED` |
| SMDR | `DERIVED-0664c6817d75837bc3f5989f299ec3e448c7d279c8531e2225c8677e104707f4` | KSEI schedule, PDF p.1, exact date/semantic/mechanics; raw SHA `d786d7d95d9e74eddba1db64a6860f35582f665f2de8329229d31f822fbfe086` | `RESOLVED`, 2023-01-31 |
| DIVA | existing V16 event | prior retained issuer schedule, exact | `RESOLVED`, 2021-09-02 |
| TMAS | existing V16 event | prior retained issuer schedule, exact | `RESOLVED`, 2023-05-23 |
| TUGU | existing V16 event | prior retained annual-report evidence, exact | `RESOLVED`, 2023-05-24 |

The SMDR evidence is linked to the existing V16 IDX stock-split event; the
separate KSEI mandatory row was not relinked. Candidate, listing, record,
distribution, effective, depository, and ZAPI/router dates were not substituted
for the selected transition date.

## Conservation and validation

- V16 to V17: 412 source rows unchanged; 387 economic events unchanged; 46
  non-basis rows unchanged; proven linkages 27 unchanged.
- Resolved/unresolved: `163/178 -> 167/174`; exactly four existing event IDs
  were promoted and four expected ledger rows plus four unresolved removals and
  two affected gap rows changed.
- `validation_report.json`: all internal checks PASS, including V16 binding,
  evidence hashes, exact event IDs, duplicate/missing-target guards,
  fail-closed residuals, population conservation, deterministic serialization,
  and no V16 mutation.
- Corrected independent verifier: `42/42 PASS`; all retained output hashes
  matched the V17 manifest and all seven audit rows marked ZAPI as not retained.
- Targeted CA tests: `25 passed`; full repository pytest: PASS; relevant
  Python compilation: PASS; `git diff --check`: PASS.
- Residual Actions run `33364685031` failed before runner execution with no
  steps/runner assigned and was not rerun.

## Integrity boundary

This is an external, immutable certification artifact. It does not authorize
production admission, historical backfill, or automatic consumption by the
runtime. Population completeness, historical as-of authority, exhaustive
negative authority, unresolved transition semantics, Data/Research admission,
and INC-001 closure remain blocked. No outcomes/targets, Phase-E, fit/refit/
score, market-provider call, counter/PaperState/R2 mutation, production
execution, deployment, or Actions rerun occurred.

## Next decision

Perform one bounded read-only blast-radius audit of the V17 ledger-to-gate and
runtime boundaries. Prove that this external artifact cannot silently alter
the frozen science or production state, and that any future admission still
requires the existing structural, population, temporal, and provenance gates.
