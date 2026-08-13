# Handoff
from: DATA
to: MAIN / ChatGPT reviewer
task_id: IDX-DATA-005-OPEN-HLC-DIAGNOSTIC
model_used: GPT-5 Codex with four bounded local read-only cache workers
reasoning_level: xhigh
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: d4517c61216d8efcae7b61225e03c7670e5cd5b9
branch: data/idx-data-002c
head_commit: d4517c61216d8efcae7b61225e03c7670e5cd5b9
scope: Decompose preserved 1260 unresolved ACTIVE price pairs into Open versus HLC gaps and evaluate a hypothetical signal-research HLCV contract.
files_changed: docs/PROJECT_LEDGER.md; docs/PROJECT_CONTEXT_MASTER.md; docs/checkpoints/2026-08-09_1260_OPEN_GAP_DOMINANT_DIAGNOSTIC.md; coordination/handoffs/IDX-DATA-005-OPEN-HLC-DIAGNOSTIC-DATA.md
findings: Full pytest 157 passed. All 6,716 unresolved pairs are OPEN_ONLY_MISSING; HLC_MISSING, OPEN_AND_HLC_MISSING, and OTHER are zero. Affected known Regular-Market Value is 66,890,258,565,100. Under the hypothetical Open-optional HLCV contract, 979/979 required common stocks, 981,940/981,940 ACTIVE rows, and 100 percent known Regular-Market Value are eligible; no unsupported ticker remains.
decisions_made: Keep strict execution-grade Open requirement and strict 504/1260 NO-GO unchanged. Classify the evidence as OPEN_GAP_DOMINANT. Do not synthesize Open or change the production gate.
decisions_needed: Independent review must decide whether a separately versioned signal-research HLCV contract is warranted; no contract change is authorized by this handoff.
blocking_risks: Execution-grade historical Open evidence remains unresolved for 6,716 pairs. Existing strict tradability and price-semantics blockers remain in the 62 failed-ticker registry. Signal-research eligibility is diagnostic only and is not certification.
validation_run: python -m pytest -q tests -> 157 passed, 0 failed; read-only diagnostic runtime `...\\research_feasibility_1260_20260809\\diagnostic_open_hlc_1260_20260809\\run_diagnostic.py` -> exit 0.
recommended_next_action: Push this checkpoint for ChatGPT review. Do not model, run IDX-VAL-002, start 252/1260, synthesize Open, weaken the gate, or merge to main.
