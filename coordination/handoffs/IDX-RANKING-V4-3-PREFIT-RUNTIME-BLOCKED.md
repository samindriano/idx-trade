# Handoff: Ranking V4-3 prefit runtime blocked

from: Codex
to: ChatGPT independent review
task_id: IDX-RANKING-V4-3-PREFIT-RUNTIME-BLOCKED
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `2c50e4a24e42593360f5ef6e87b28abe4768b5db`
branch: `research/idx-ranking-v4-3-prefit-runtime-v1`
head_commit: `pending result commit`
scope: Outcome-blind prefit runtime preflight only; capture was blocked before environment access.
files_changed:
  - `coordination/handoffs/IDX-RANKING-V4-3-PREFIT-RUNTIME-V1.md`
  - `docs/checkpoints/2026-08-17_RANKING_V4_3_PREFIT_RUNTIME_BLOCKED.md`
  - `coordination/handoffs/IDX-RANKING-V4-3-PREFIT-RUNTIME-BLOCKED.md`
findings:
  - Focused tests: `8 passed, 1 failed`.
  - Failure: protocol expects `835da85549b1d6874cb2ab49a029b9f4358fdf28cb8379b3f9df105835b05849` for `config/ranking_v4_3_preregistration.json`, while the exact HEAD bytes hash to `3a54dcf0266f8a2808b8c1d73dda41a32baea368e6b48aac21e9fa073f6824ed`.
  - Compile and `git diff --check` passed.
  - Requested external output directory was absent; no capture artifacts exist.
decisions_made:
  - Failed closed before capture because the user prohibited changing the frozen configuration/protocol.
  - No scientific or runtime semantics were changed.
decisions_needed:
  - Resolve the stale protocol byte pin under a separately reviewed correction before rerunning capture.
blocking_risks:
  - A manifest captured while the protocol's required artifact identity is inconsistent would not be reproducible.
validation_run:
  - `python -m pytest tests/test_ranking_v4_3_preregistration.py tests/test_ranking_v4_3_prefit_runtime.py` — `8 passed, 1 failed`.
  - `python -m py_compile scripts/capture_v4_3_prefit_environment.py` — PASS.
  - `git diff --check` — PASS.
recommended_next_action: ChatGPT review of the protocol/preregistration SHA mismatch; do not alter config or run V4 targets/models in this lane.
