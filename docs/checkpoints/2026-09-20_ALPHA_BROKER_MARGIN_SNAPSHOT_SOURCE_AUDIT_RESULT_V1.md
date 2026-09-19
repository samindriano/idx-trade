# Broker / Margin Snapshot Source Audit Result V1

Status: `PASS_STRUCTURAL_ONLY / SNAPSHOT_ONLY_BLOCKED`

This is a read-only, outcome-blind audit of the locally persisted 2026-07-14
broker/margin snapshot. It does not call Zapi or IDX, access targets or
outcomes, modify canonical data, create a feature or candidate, or change
capture, cloud, telemetry, or production state.

## Structural evidence

- The local manifest declares 73 files. All 73 match their declared byte
  counts and SHA-256 values; no file is missing, escaping, byte-mismatched, or
  hash-mismatched.
- The official and Zapi margin payloads contain 220 rows, and the official and
  Zapi stock payloads contain 965 rows for 2026-07-14. Normalized row counts
  are 220, 965, and 326 for margin, stock, and the official eligible list.
- Zapi-to-official raw parity is exact for all six common margin fields on
  220/220 margin rows and all six common stock fields on 965/965 stock rows.
- The eligible list has 326 tickers. All 220 margin tickers are inside it;
  106 eligible tickers are absent from the margin summary, including 100 with
  positive All Stock activity. The comparison surface has 971 rows.
- The all-six generic metric equality test against All Stock is 0/220. The
  persisted parity decision is `NOT_H2_DECISIVE`.
- The manifest records that the Zapi API key was not written; only presence
  was used. No secret material was read into the audit artifact.

## Admission limits

The official UI/source labels the Margin tab as `IDX Reporting (Regular and
Cash)` and exposes ordinary market fields, not financing-account or
margin-loan fields. Therefore actual H1 margin-financing flow is not proven,
and exact H2-like All Stock filter parity is also not proven. This is a single
date snapshot with no publication/knowledge timestamp, no daily history, and
no PIT admission contract.

The surface remains capability-only and is not admitted for feature
construction, universe masking, candidate evaluation, or protected-packet
expansion. No broker/margin-derived alpha was created.

## Independent gates

- Structural audit: `PASS_STRUCTURAL_ONLY / SNAPSHOT_ONLY_BLOCKED`.
- Independent broker/margin envelope verifier: `PASS`.
- Generic isolated artifact hash contract: `PASS`.
- Outcome-blind research firewall: `PASS`.
- Network/provider/target/outcome/cloud access: none.

## Artifact provenance

- Source manifest SHA-256: `33195286e1fb47d80c96e0ab4dfb84cc85cc6eb2d40787bc7d0488206d8d6664`
- Audit report SHA-256: `0821abe4324dbe8b0dee819e77a90c676aeef3d99b7bf08fdf553dd822398f68`
- Parity summary SHA-256: `851423bc6efceb5e7235d931dbb6b8c259fff769449419c49ee59e53df574042`
- Official parity SHA-256: `c8b2316dbec62198e22d1aabe55b40258a9f8855ba7005a8acd85bae5ddaac78`
- Comparison CSV SHA-256: `adb11f2af8710934b434ed047886d387a8f2c903c63e58f58b22eb28dcdf22dd`
- Audit JSON SHA-256: `8ad62c5170ff7391cd3badee09d31ff0b3bc8485acab2e3297d231bcbd9e362b`
- Independent verifier JSON SHA-256: `5ee0bf41444d316bb608e0882957cd8377075dcde808f5de77430edaed8104e7`
- Hash-contract JSON SHA-256: `116932832f57555a9f373a17a812a117e7d459c4bdd364ba6a30d8a04361892c`
- Firewall JSON SHA-256: `21e1237a6df9fefb9fa231a0b035550c6ad9fb5ac4c8a775834276b3d0723b12`
- Audit script SHA-256: `113314bce2e102f62cdf7382767babccf2cebab07b6ea026dae04c2dca9e7d92`
- Independent verifier script SHA-256: `50df75815f6161da964171d16b2840b8c1578113c96dafc06bf6b811a5c14478`

All derived artifacts are under the isolated staging root
`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`.
