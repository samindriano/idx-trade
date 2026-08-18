# V4 CA Targeted Schedule Evidence V1 — Preregistration

Status: `FROZEN_LOCAL_EXECUTION_PENDING`

Scientific parent: `data/idx-v4-ca-schedule-event-impact-attribution-v1@a7a3b998930cf0506d3ddc9cbbd21636ba6f3e93`
Scientific/code-test anchor: `5ea347b29d6ce81a1178e9dd2a6d6d37a656ab14`

## Frozen target set

The acquisition population is exactly the seven-event deterministic inclusion-minimal priority subset from Schedule Event Impact Attribution V1. It is not claimed to be the global minimum:

1. NISP — Voluntary Conversion — `10e24d3621e0f5e65833655b2e11938fc53d64e68c03e6c87658eb74bb2ae26b`
2. ISAT — Mandatory Conversion — `1285d019c8831fae39ad2909e699680df9071d5ebc38701a71a5a5dba951c60d`
3. ADRO — Right Distribution — `41c1e8493213d0151799837330c0dc7d8fea633d458c03e40b61ea0247bb9e58`
4. PANI — Right Distribution — `82e09144ecfe0d4375a9260156fe75dd74ed01a2cd72262f55e14cd85ce6ebc7`
5. RAJA — Mandatory Conversion — `072cf4b8b2f7f86f3c7a55a1128c85f338cbe7b41307b57a3240ad94dba0afae`
6. PTRO — Mandatory Conversion — `9b21df59be9d68e088059e2dae04d2d0bd8832d9d1cb5e9dd5a300f05f369610`
7. CUAN — Mandatory Conversion — `6df97832e47c00fc5653e90659f525a5c8258752f9fc2245803498bdeb30b45e`

Selected-subset CSV SHA-256:
`f6650daf7256196f976b0a9d161dbf0cf896d0d349306be4fe4c76b1d2168529`.
Runtime identity is pinned to that exact CSV and the code constants; manual transcription must not override it.

## Evidence policy

### NISP static cash path

Only the selected NISP event may use this path. A freshly captured official KSEI registered-security page must parse under the existing strict six-column CA-table parser and expose exactly one row satisfying all of:

- ticker NISP;
- source-native `Voluntary Conversion`;
- status Active;
- ratio parser status `PARSED_SOURCE_TEXT_ONLY`;
- left security NISP;
- right security one of the frozen currency tokens (expected IDR but no value is assumed);
- immutable selected source-date set exactly `{2024-09-06}` intersects the parsed row's source-native Cum/Record/Distribution identity dates;
- non-empty official source URL and raw-byte SHA.

Record/Distribution is used only for exact event linkage. It is never a market transition date. This path implements the already-accepted security-to-currency Voluntary Conversion non-blocking semantic for one previously blank-ratio event; it is not a generic new rule.

### Six mechanical schedule paths

For ISAT, ADRO, PANI, RAJA, PTRO, and CUAN only:

- official KSEI corporate-action schedule index and documents only;
- category derived from frozen source type;
- source-date months ±2 months, identical to the prior accepted bounded acquisition policy;
- exact ticker in index subject;
- exact parsed ticker;
- compatible family;
- at least one exact Record/Distribution date overlap to the selected immutable source-date set for identity linkage;
- explicit `REGULAR_MARKET_EX_DATE` or `REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE` only;
- transition must be an official session;
- non-empty KSEI reference and raw-byte SHA;
- conflicting exact transitions fail closed.

No Record/Distribution transition fallback, price-jump inference, next-session inference, adjusted-price shortcut, alias remap, mirror, or alternate provider is admitted.

## Continuity replay

After the one acquisition run, run exactly one outcome-blind continuity replay even if some of the seven events remain unresolved, provided the acquisition command itself completed successfully.

The replay must rebuild from the frozen base continuity ledger and combine:

- accepted 598/610 KSEI remediation census;
- accepted residual-document evidence;
- exact targeted evidence from this lane.

It must use `classify_event_with_targeted_evidence`, so newly exact mechanical transitions can become `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION` where appropriate rather than being automatically waived.

Frozen continuity gate remains >=90% for every one of 600 H5, H10, and consensus dates. No threshold, universe, target, or evaluator change.

## Hard boundary

No provider retry after an execution error, no edits after acquisition-result exposure, no 39-event recrawl, no 610-ticker recrawl, no KSEI coverage retry, no cross-source repair, no R5/R10, target/rank, model, prediction, IC/performance/bootstrap, or protected/fresh-forward outcome access.

Passing continuity only authorizes the next separately reviewed V4 target/model historical-development execution step; it is not alpha validation.