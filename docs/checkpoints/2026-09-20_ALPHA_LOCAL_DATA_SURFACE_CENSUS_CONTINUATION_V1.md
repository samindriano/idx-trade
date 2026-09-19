# Local Data Surface Census Continuation V1

Status: `SIX_SURFACES_FOUND / NONE_ADMISSIBLE`

This continuation extends the durable 2026-09-20 local surface census. It is a
read-only inventory of existing local manifests and does not admit a source,
construct a feature, modify canonical data, or access outcomes.

## Newly classified surfaces

| Surface | Evidence and coverage | Classification | Admission blocker |
|---|---|---|---|
| Historical official foreign flow | `idx-trade-foreign-flow-historical-20260814-v1/archive_manifest.json`, SHA `fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334`; 1,288 sessions, 1,129,024 rows, 983 tickers, 2021-04-01–2026-08-13, 727–968 rows/session, unit shares | `PARTIAL / SOURCE_ADMISSION_BLOCKED` | Retrospective acquisition; publication time unknown; T→T+1 is not a public-availability certificate; identity/CA/revision-vintage and panel completeness unresolved |
| Historical listing/delisting lifecycle | `idx-trade-historical-universe-20260811/official_acquisition/acquisition_summary.json`, SHA `ced02fe566be97b68d100ece6a217a8a7a6fe203ed6ea618b1503d956d80c00c`; 962 current rows, 163 delisting records / 159 tickers, activity 1990–2026 | `PARTIAL / IDENTITY_BLOCKED` | No complete daily membership, PIT/publication timestamps, or issuer-transition authority; six conflict tickers and 2,280 ambiguous issue rows |
| LBRE monthly free-float corpus | `idx-lbre-monthly-free-float-history-20260815-v1/artifact_manifest.json`, SHA `e134809a1f1b745daf2f21c33ab7db78c38d1d5d520f5320564359d5b865bd86`; 58,671 manifest artifacts, 27,724 announcements, 25,262 canonical rows, 24,394 admitted, 868 unresolved, 1,021 corrections, 2024-04-30–2026-06-30 | `PARTIAL / SOURCE_REMEDIATION_REQUIRED` | Monthly issuer reports are not a daily population-wide panel; lineage/identity, 2021–2023 coverage, revision, and public-availability contract incomplete |
| Market-wide statutory free-float anchors | `idx-historical-statutory-free-float-snapshot-20260815-v1/artifact_manifest.json`, SHA `7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`; 2025-12-31 has 956 reported / 923 exact-share rows, 2026-03-31 has 956 percentage-only rows | `PARTIAL / SOURCE_REMEDIATION_REQUIRED` | Anchors are not continuous PIT history; percentage-only interval and missing issuer/ISIN/CA linkage prevent admission |
| HSC ownership event ledger | `idx-hsc-full-history-ledger-20260815-v1/AUDIT_MANIFEST.json`, SHA `230fec0544fb7464e63008ee080fda0c8082049626529f0a565376601416b55d`; normalized CSV SHA `afbbb642807e04d6050de3574fec49559eb8fcf2963039a53439e507f067cbd2`; 59 events, 55 active at cutoff, 56 originals, 2 corrections, 1 removal | `PARTIAL / EVENT_ONLY` | Event-level data is not a daily ownership/free-float panel; completeness, issuer continuity, and historical revision coverage unresolved |
| Broker/margin category snapshot | `idx-broker-margin-source-audit-20260813/artifact_manifest_2026-07-14.json`, SHA `33195286e1fb47d80c96e0ab4dfb84cc85cc6eb2d40787bc7d0488206d8d6664`; one date, 220 margin rows, 965 stock rows, 326 eligible, 106 eligible absent; audit SHA `0821abe4324dbe8b0dee819e77a90c676aeef3d99b7bf08fdf553dd822398f68` | `SNAPSHOT_ONLY / BLOCKED` | Semantics are H2-like category view, not financing flow; 0/220 all-six metric equality versus All Stock; no PIT/publication timestamp |

No feature or candidate uses this surface. The exact audit SHA is recorded in
the source audit artifact; this census only classifies its capability.

## Already classified, not new

The acquisition staging root still contains only the four previously audited
manifest families. Guarded Stage-A contains derived artifacts only. The sector
sidecar ZIPs are byte-identical to the official sector archive. Free-float
effective-supply/KSEI, sparse foreign-flow probes, financial/OHLCV/session
inputs, Dataset-Saham-IDX, Zapi/TradingView/Investing probes, market context,
and sector archives are already covered by existing capability checkpoints.

## Decision

These six surfaces increase the future capability map but do not change the
candidate registry, re-entry queue, or protected-evaluation packet. No source
is admissible for alpha feature construction until population completeness,
knowledge/publication time, identity/ISIN continuity, corporate-action basis,
revision/vintage, and missingness contracts are independently established.

Manifest existence and hashes were verified locally. No network, credentials,
provider, cloud, canonical data, target, outcome, or production state was
accessed or modified.
