# Joint Setup Readiness State V1.1 — Real-Parent Domain Remediation

Status: `JOINT_REAL_PARENT_DOMAIN_COMPATIBLE`

Branch: `research/idx-joint-setup-readiness-state-v1-1-domain-remediation`

Parent contract: `research/idx-joint-setup-readiness-state-v1@3ad481cc4b371f5022742101a12f6b9d603481a4`

Acceptance review: `review/idx-joint-setup-readiness-state-v1-acceptance@d906caa03dc6c41c62d346c7f185a5bd8cb6e0c3`

## Scope

This lane changes only the applicability domain of the accepted joint
contract. The accepted Foreign Flow and Price State parent modules, formulas,
thresholds, and V1 classifier mapping remain unchanged. No joint runtime
artifact was written. The contract-only V1.1 implementation uses the Price
State key set as the authoritative applicability domain:

* every Price State `(ticker, feature_session)` must exist exactly once in
  Foreign Flow;
* a missing Foreign Flow key required by Price State fails closed;
* Foreign-Flow-only keys are allowed, excluded from the output, and retained
  as exact domain provenance;
* the join is performed only after the subset/duplicate checks, so an inner
  join cannot silently drop a required Price key;
* source session remains `2026-08-12` and feature session remains the next
  official session `2026-08-13`.

## Immutable real-parent audit

Runtime root:
`D:\Documents\Project\idx-trade-data-gate-20260808v`

Foreign Flow Setup State parent:

* artifact:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective\foreign_flow_representation_v2\2026-08-13\idx_foreign_flow_setup.parquet`
* artifact SHA-256:
  `b8791011659b33c62cf0890340e86de4abfb397eaa1b99c3639a6c240b682284`
* manifest:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective\foreign_flow_representation_v2\2026-08-13\idx_foreign_flow_setup.manifest.json`
* manifest SHA-256:
  `3c94eede15c35e4997643ef931538779940d6839136f7afca4b819402f17caed`
* status: `FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_READY`
* rows/keys: `963 / 963`
* representation artifact SHA-256:
  `3622b23886cfb47b9e7b0c1d137cba33ac9f0767f390a35439a504d7672d9e13`
* representation manifest SHA-256:
  `4095fbfd39a9ef9459bfa68f6ea8560449683133b882671d3176eb070bcbb51d`

Price State parent:

* artifact:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective\price_trend_confirmation_state_v1\2026-08-13\price_trend_confirmation_state_v1.parquet`
* artifact SHA-256:
  `8dab4a1d532c42cb46f9a9b86c5f853f99f00e13677222c7ae1e1ab0ca1901af`
* manifest:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective\price_trend_confirmation_state_v1\2026-08-13\price_trend_confirmation_state_v1.manifest.json`
* manifest SHA-256:
  `aad51b933ba8a8868c050e17fec52330a3b6c66002ba29d0ddd4ba84949cbd6f`
* status: `PRICE_TREND_CONFIRMATION_STATE_V1_FORWARD_READY`
* rows/keys: `836 / 836`
* accepted context-anchor attestation SHA-256:
  `ec8783b231eabecb0c61d89413b5f0a9216355949815744fa9bec40bf03cd312`

Calendar used for the read-only audit:

* path:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\context_bridge\calendar\ranges\2026-07-31_2026-08-13\exchange_sessions.csv`
* bridge calendar SHA-256:
  `51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`
* combined session-set SHA recorded by the accepted parent context:
  `dd51d3dbcb29915ff80612d84a912da237331e979ee3847bd8fd4984ead413dd`

Both parent artifacts were read-only. Their declared artifact hashes matched
the current bytes. Both contain one feature session, `2026-08-13`, sourced
from `2026-08-12`; duplicate parent keys were zero and joined source-session
mismatches were zero.

## Exact domain reconciliation

| Domain | Key count |
|---|---:|
| Foreign Flow | 963 |
| Price State authoritative domain | 836 |
| overlap | 836 |
| Price-only | 0 |
| Foreign-Flow-only excluded | 127 |

Price-only identities: `[]`.

All excluded Foreign-Flow-only identities below have
`feature_session=2026-08-13`:

```text
ABBA, ADCP, AKKU, ALMI, ALTO, ARKA, ARMY, ARTI, BAJA, BATA, BBMD, BEBS,
BHAT, BIKA, BIKE, BIMA, BKDP, BOSS, BTEL, CANI, CBMF, CMPP, CNKO, CNTB,
COWL, CPRI, CRAB, DEAL, DIGI, DPNS, DUCK, EDGE, ENVY, ETWA, FASW, FIMP,
FOOD, GAMA, GLOB, GOLL, GTBO, HILL, HITS, HKMU, HOME, HOTL, IBFN, IBST,
IIKP, INAF, INCF, INDX, INRU, INTA, IPPE, JMAS, JSKY, KARW, KAYU, KBRI,
KIAS, KOIN, LCGP, LCKM, LMAS, LMSH, MABA, MAGP, MARI, MDRN, MENN, META,
MFMI, MKNT, MREI, MTFN, MTPS, MTRA, MTSM, MYTX, NUSA, OCAP, PLAS, PLIN,
PMMP, POLL, POLY, POOL, POSA, PTDU, PTMR, PURE, RAFI, RDTX, RIMO, SBAT,
SCPI, SIMA, SKYB, SMCB, SMRU, SOSS, SOUL, SRIL, SUGI, SUPR, SWAT, TAYS,
TDPM, TECH, TELE, TGRA, TIRT, TOPS, TOYS, TRAM, TRIL, TRIO, TRUE, UNIT,
UNSP, WICO, WIKA, WSBP, WSKT, ZBRA, ZINC
```

The V1.1 builder returned an in-memory output of exactly 836 rows and 836
unique keys. It did not write a joint runtime artifact.

## In-memory contract verification

* joint state distribution: `IGNORE=697`, `WATCH=84`, `READY=54`,
  `ENTRY_ELIGIBLE=1`;
* source-session mismatch: `0`;
* protected flags: `outcome_blind=true`, `model_fitted=false`,
  `model_scoring=false`, `trade_recommendation=false` for every output row;
* V1.1 contract fingerprint:
  `c1bd084dfe54dacd447ee15915e5210e539cfc99b19f42f1543bfa3f1801d5de`;
* accepted V1 fingerprint remains unchanged and is referenced by the V1.1
  fingerprint; no V1 contract artifact was overwritten.

## Validation and boundaries

Focused V1 + V1.1 tests: `22 passed`.

Full pytest: `61 passed, 1 failed, 62 collected`. The only failure is the
pre-existing unrelated
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`:
the current storage contract reports independent `raw_close` and
`vendor_adj_close` conflicts (2), while this old test expects 1. Storage was
not changed.

`git diff --check`: PASS.

No provider/network calls, scheduler/counter/O2 changes, model/scoring,
outcome access, trade recommendation, or Repository Hygiene work occurred.
