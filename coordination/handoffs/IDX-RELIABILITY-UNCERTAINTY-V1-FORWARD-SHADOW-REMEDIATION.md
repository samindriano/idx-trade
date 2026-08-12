# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-RELIABILITY-UNCERTAINTY-V1-FORWARD-SHADOW-REMEDIATION
model_used: Luna xhigh root / workers
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `4af006d`
branch: `research/idx-reliability-uncertainty-v1-forward-shadow`
scope: Address the ChatGPT review without changing the frozen Reliability V1 formula or the accepted 2026-08-12 sidecar.
files_changed: `src/idx_trade/forward_model_runtime.py`, `src/idx_trade/reliability_v1_forward_shadow.py`, `tests/test_reliability_v1_forward_shadow.py`, remediation checkpoint, remediation handoff

## Findings

- O2.1 `FileNotFoundError` no longer prevents Reliability from running after
  an accepted O2 artifact is available.
- Existing sidecar reuse now revalidates the sidecar's exact O2 source
  artifact and session-manifest hashes, paths, model/feature pins, formula,
  protected flags, and locked outcome state before returning it.
- Source artifact and source session-manifest revisions after sidecar
  creation fail closed without rewriting the sidecar.
- Tie ordering and tied percentile ranks follow the frozen deterministic
  semantics.

## Existing artifact verification

2026-08-12 Reliability artifact and manifest remained unchanged:

- artifact SHA: `76e5b79843e043fd3bff45d67a2a38b260abe7e5690a567c7fb569628be4422e`
- manifest SHA: `910cfc49a338e9f02211480b5af484eb6173a2c186a9ce598ec39d1220f20dbb`
- rows: `836`; `AVAILABLE`: `806`; O2-unscored: `30`

## Validation

Focused tests: `16 passed`.  
Full pytest: `278 passed, 0 failed, 3 warnings, 16.59s`.

## Decisions and stop boundary

The frozen formula and 2026-08-12 sidecar remain intact. No provider,
recapture, O2 rescore/refit, Reliability recomputation, outcome, tier,
filter, model-fit, independent-counter, or forward-outcome-marker access was
performed. Coordination status remains `REVIEW`.

recommended_next_action: ChatGPT re-review of this bounded remediation. Do not authorize Reliability outcome evaluation or filtering from this handoff.
