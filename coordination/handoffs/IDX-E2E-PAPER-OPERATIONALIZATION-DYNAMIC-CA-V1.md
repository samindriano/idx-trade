# Handoff

from: Codex
to: MAIN / ChatGPT reviewer
task_id: IDX-E2E-PAPER-OPERATIONALIZATION-DYNAMIC-CA-V1
model_used: GPT-5.6
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: 86c608e95404fcf59b367a63b919a0656971fb97
branch: integration/idx-e2e-baseline-paper-v1
head_commit: 86c608e95404fcf59b367a63b919a0656971fb97

## scope

Outcome-blind operationalization of per-window official IDX CA phase capture
for the existing E2E PAPER controller. No changes to frozen science, labels,
targets, models, outcomes, or existing local schedulers.

## files_changed

- `src/idx_trade/e2e_paper_operational_controller_v1.py`
- `src/idx_trade/e2e_paper_runtime_config_v1.py`
- `src/idx_trade/forward_ca_attestation_v1.py`
- `scripts/capture_forward_ca_idx_bei.py`
- `tests/test_capture_forward_ca_idx_bei.py`
- `tests/test_e2e_paper_operational_controller_v1.py`
- `tests/test_e2e_paper_runtime_config_v1.py`
- `docs/checkpoints/2026-08-23_E2E_OPERATIONALIZATION_DYNAMIC_CA_V1.md`

## findings

The prior static CA pointer could not safely support unattended multi-day
operation: the attestation window and required ticker set change per decision
session. The controller now resolves or captures
`<ca_attestation_root>/attestations/<session>_<phase>.json`, binds its actual
path/SHA into the durable phase sidecar, and passes that exact path to the
existing POST_EOD/PREOPEN consumers.

The collector uses the pinned provider checkout and captures the three already
accepted official IDX source legs. It does not parse or promote events and it
does not access outcomes. Failed captures remain inspectable under an external
`.partial.*` directory; final output is published only after manifest
verification. The V1.2 builder rejects a stable but non-frozen calendar schema
fingerprint and atomically publishes its output.

The remediation adds exact `through_session_date` to the durable CA sidecar,
and makes the phase directory/attestation publication recoverable through a
hash-pinned `PUBLISH.json` marker. Recovery is accepted only when the current
phase/from/through/ticker invocation matches the recovered manifest and the
real execution-consumer V1.2 verifier passes.

## decisions_made

- Static attestation configs remain valid for existing replay/bootstrap paths.
- New live configs must declare the three dynamic CA fields together; static
  and dynamic CA sources cannot be mixed.
- The execution consumer's existing V1.2 verifier is reused before a dynamic
  attestation is reused or passed downstream.
- `TEAM_STATUS.md` is untouched on this branch per the MAIN-only rule.

## blocking_risks

- No real provider capture was run in this remediation increment.
- External dynamic config exists outside Git, but must be repinned after the
  final branch tip. `IDXTrade-E2E-Paper` is not installed: the legitimate
  registration attempt failed with `Access is denied` / `0x80070005`.
- First weekday same-session proof is still pending and must not be claimed
  from weekend/no-session behavior.

## validation_run

- `python -m pytest -q --basetemp <external-temp-root>`: PASS.
- Focused CA capture/controller/attestation remediation tests: 24 passed.
- Focused scheduler contract tests: 20 passed.
- `python -m py_compile` on changed modules/scripts: PASS.
- `git diff --check`: PASS.

## recommended_next_action

Independent review of commit `86c608e95404fcf59b367a63b919a0656971fb97` is
PASS for the prior P1 remediation. Next, repin the external dynamic runtime
config to the final repository HEAD, obtain one legitimate administrator-
approved registration path, install only the new `IDXTrade-E2E-Paper` task,
run one weekend/no-session smoke without provider capture, and wait for the
first weekday cycle.
