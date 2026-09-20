# IDX-Trade Runtime Config / Artifact Identity Audit — V1

Date: 2026-09-20  
Status: `READ-ONLY FORENSICS / NO-GO FOR FULL ARTIFACT-LINEAGE CERTIFICATION`  
Lane: isolated `codex/alpha-available-data-20260919`  
Pinned runtime evidence: `045e25a19d9f71170d2c863e768102937e59ad73`  
Pinned extraction archive SHA-256: `09FA98B475909938430F91987B9180B1050B6F17A82A37D0E9E25C7089ADDEF8`

This checkpoint records a read-only audit of whether the external E2E runtime
configuration and runner identity are bound into the durable prepared and
execution artifacts. It does not modify repository code, runtime config,
canonical data, cloud/capture state, telemetry, counters, or protected
outcomes.

## 1. Scope and evidence boundary

The audit used only the pinned detached runtime extraction under:

`C:\Users\Sam\AppData\Local\Temp\idx-system-045e25a1-dd0f02dcb71f48cf82d2b81e0eead8cf`

The source files are not present in the current alpha-research worktree; the
archive hash above is the evidence locator. No production or live cloud path
was invoked. Synthetic test fixtures, when exercised by the existing test
suite, remained under pytest temporary directories.

## 2. What is correctly pinned

`src/idx_trade/e2e_paper_runtime_config_v1.py` defines a loader that:

- reads `operational/config.json` and its `config.json.sha256` sidecar;
- hashes the exact config bytes before parsing them;
- rejects a sidecar mismatch or caller-supplied expected-config mismatch;
- validates the schema, absolute paths, expected repository/provider commits,
  fixed PREOPEN capture time, CA-source completeness, and `runner_sha256`;
- returns `config_sha256` and `runner_sha256` in `LoadedRuntimeConfig`.

`runtime_config_v2.py` inherits that loader and carries the same config and
runner hashes while adding the separately hash-pinned dual-calendar schedule.
The corresponding loader/guard tests passed:

| Slice | Result |
|---|---:|
| `test_e2e_operational_guard_v1.py` | 8 passed |
| `test_e2e_paper_runtime_config_v1.py` | 11 passed |
| `test_e2e_dual_calendar_runtime_v1.py` | 3 passed |
| Total | **22 passed** |

The operational phase attestation also correctly binds phase, session,
expected branch, expected commit, issue time, immutability, and one-hour
expiry. It does not currently carry the external config SHA or runner SHA.

## 3. Finding: prepared/execution artifacts do not carry full runtime identity

### 3.1 Prepared POST_EOD artifact

`e2e_paper_orchestration_v1.py:991-1110` exposes
`prepare_post_eod(runtime_root, ...)`. Its durable payload binds score
manifest references, runtime snapshot path/SHA/state hash, Decision and
Execution plan hashes, EOD artifact references, CA reconciliation, and
`outcome_access=false`.

It does not bind:

- `config_sha256`;
- `runner_sha256`;
- executable identity or runner path;
- a complete external runtime-config payload/reference;
- an explicit code identity object.

The function receives only `runtime_root` plus already-verified input objects;
it does not receive or load `LoadedRuntimeConfig`.

### 3.2 PREOPEN execution artifact

`e2e_paper_orchestration_v1.py:1195-1540` verifies the prepared payload hash,
score/EOD/Open/CA parents, runtime snapshot parent, and recomputed Decision and
Execution plan hashes. The durable `EXECUTION_COMPLETE` body records prepared,
Open, CA, runtime snapshot, registry, fill, turnover, pending-transition, and
outcome fields.

It likewise does not record or compare `config_sha256`, `runner_sha256`,
executable identity, or a complete runtime-config identity. Therefore a
configuration change that leaves the already-referenced input artifacts and
recomputed plans compatible is not distinguishable from the original run by
the prepared/execution artifact itself.

This is an artifact-lineage gap, not evidence that a live configuration was
changed or that a live execution was contaminated.

## 4. Partial protections that do not close the gap

- `e2e_operational_guard_v1.py:211-345` binds controller phase attestations to
  branch and commit, but not the external config or runner digest.
- `e2e_paper_operational_controller_v1.py` and `_v2.py` attest deployment and
  pass expected branch/commit into child scripts. Their controller status and
  phase handoff therefore provide partial deployment lineage, not a complete
  config-to-artifact binding.
- Cloud-stage validation carries partial `code_identity` (commit, and in the
  CA PREOPEN validator a runner SHA), plus schedule/input hashes. That is not
  equivalent to the full local operational config identity and does not add
  the missing fields to the prepared/execution artifacts.

The existing cloud/prepared finding in the master dossier remains valid, with
this audit adding the exact runtime-config loader-versus-orchestration split.

## 5. Validation result

The existing orchestration regression slice also passed:

| Slice | Result |
|---|---:|
| `test_e2e_paper_orchestration_v1.py` | **27 passed** |

These tests confirm the current bounded parent/hash/restart behavior. They do
not prove full runtime-config identity because the orchestration API and
payload schema do not require it.

One broader integrated replay collection was not counted as a runtime result:
the detached extraction referenced `scripts/run_e2e_paper_production_replay_v1.py`
but did not contain that script. This is a packaging/evidence limitation in
the detached extraction, not a claim about production behavior.

## 6. Verdict

`FAIL — RUNTIME_CONFIG_IDENTITY_NOT_BOUND`

The runtime config loader itself is hash-pinned and tested, and the controller
has partial commit/phase identity. However, the durable prepared and execution
artifacts do not bind the config and runner identity that produced them. Full
system certification therefore remains `NO-GO` on artifact-lineage grounds.

No code/config fix was applied in this lane. A future hardening change would
need explicit authorization and should add the exact config/runner identity to
the phase handoff and both durable artifact schemas, with fail-closed equality
checks at PREOPEN and idempotent replay.

## 7. Relation to the corporate-action frontier

This finding is independent of the already documented CA/dividend chain. The
CA lifecycle and partial-fill/multi-session composition checkpoints remain the
authoritative results for that frontier; this checkpoint only records that the
runtime/config identity around those artifacts is not yet complete.

