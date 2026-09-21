# IDX-Trade Immutable Shadow Input Manifest V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **PRE-COPY CANDIDATE MANIFEST ONLY / SHADOW COPY NOT EXECUTED**

This record binds the exact files considered for a future isolated shadow copy.
It is not an attestation that the files were copied, and it is not permission
to read or write the active runtime.

## Candidate input files

| Class | Source path | Bytes | Last-write UTC | SHA-256 |
|---|---|---:|---|---|
| active config | `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1\operational\config.json` | 1,729 | `2026-09-20T02:12:39.4852425Z` | `fff7af72d7c761218385faadba11bb09408110c76b9fbaa43e121d5ec9bfb3e0` |
| config sidecar | `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1\operational\config.json.sha256` | 65 | `2026-09-20T02:12:53.4672837Z` | `1e9dd3cba267b3a1f9b5e4122375a2ff3d0be2bdd60bdc601e930df8934b2c0d` |
| latest operational metadata | `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1\operational\latest.json` | 1,556 | `2026-09-21T02:22:04.2991527Z` | `52fcba8be3f9eb3dc7f8830f64ccbfa783f3aa60000f1635e4d722e2b82c517c` |
| latest OfficialOpen metadata | `C:\Users\Sam\AppData\Local\IDXTrade\e2e_baseline_paper_v1\official_open\latest_capture.json` | 301 | `2026-09-21T02:22:04.2641472Z` | `c955e693aeaa51908ac19c1da2376e04d5b82d3752569e722b3e27b455a09f17` |
| session manifest | `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-16\manifest.json` | 5,021 | `2026-09-17T11:31:13.9095005Z` | `27912cb5b6a8e04608e0a44bf2e9f8eb8e207cf0492585d1eb9421a2340d7119` |
| session manifest | `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\sessions\2026-09-17\manifest.json` | 5,021 | `2026-09-17T11:32:03.6231511Z` | `e4174f611ab75e51a9f31d2f5924ad62e123c6bdc68b0c163e468fa45602252` |
| EOD latest metadata | `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\eod_automation\v4_x1_pipeline\latest.json` | 1,136 | `2026-09-20T13:30:04.5877414Z` | `a5533d53b8f581502e5e3395e22cda339c31cd630f3bfc3816b04e9977dececf` |
| EOD selected run metadata | `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\eod_automation\v4_x1_pipeline\runs\20260917T133006Z-ea2849b3.json` | 4,896 | `2026-09-17T13:30:12.1990123Z` | `d8df519ec312416bec6b685111047b446eb5c9bf898dc3c89fc3513da18902644` |

## Stability status

The table is a first hash snapshot. A second independent read was not
performed for this packet, and no destination copy was made. Therefore the
manifest is **not yet immutable shadow-input evidence**.

The next authorized step must hash the selected source files twice, require
identical bytes/metadata, copy only to a new isolated shadow root, and hash
the copies. Any source change must invalidate this manifest rather than being
silently refreshed.

## Input policy

The active `latest.json` and OfficialOpen record are diagnostic metadata only;
they must not be promoted to state. Session inputs may be considered for
historical replay only after an interface-level compatibility check. Provider,
outcome, counter, synthetic-test, and Cloudflare handoff paths are excluded.
