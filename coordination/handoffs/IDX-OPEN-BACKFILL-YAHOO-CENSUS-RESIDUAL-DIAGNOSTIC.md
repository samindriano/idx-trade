# Handoff

from: Codex local diagnostic verifier  
to: ChatGPT / MAIN independent reviewer  
task_id: IDX-OPEN-BACKFILL-YAHOO-CENSUS-RESIDUAL-DIAGNOSTIC  
model_used: GPT-5 Codex  
reasoning_level: xhigh  
source_repository: samindriano/idx-trade  
source_commit: `12a84e50597557ded2f5c3a6c0d5645d7a308e2b`  
branch: `data/idx-open-backfill-yahoo-census-v1`  
head_commit: `12a84e50597557ded2f5c3a6c0d5645d7a308e2b`

scope: offline residual breakdown of the completed Yahoo historical Open
census; no refetch, panel write, source-methodology change, or modelling

files_changed:
- `docs/checkpoints/2026-08-11_OPEN_BACKFILL_YAHOO_CENSUS_RESIDUAL_DIAGNOSTIC.md`
- `coordination/handoffs/IDX-OPEN-BACKFILL-YAHOO-CENSUS-RESIDUAL-DIAGNOSTIC.md`

findings:
- residual definition: immutable panel Open null and neither direct nor verified split-scale candidate admissible;
- residual: `49,476` rows / `669` tickers;
- provider/symbol-resolution failure: `2,876` rows across `FREN`, `MASA`, `MFIN`, `RMBA`, `TURI`;
- ordinary provider gaps: `3,840` rows / `53` tickers;
- provider H/L/C mismatch without usable verified factor: `32,103` rows / `624` tickers;
- incomplete official-action evidence: `8,804` rows / `14` tickers;
- verified-factor reconstruction failures: `1,853` rows / `14` tickers;
- FREN is absent from the security master and accounts for `952` residual rows;
- KOCI has one non-residual panel row before its `listed_from` boundary (`2023-10-06` vs `2023-10-07`);
- no residual overlaps a known legal suspension interval;
- no strict full-universe usable window exists for 2022, 2023, or 2024 diagnostics.

decisions_made:
- kept no-factor H/L/C mismatch separate from proven corporate-action mismatch;
- did not remove residual tickers to manufacture a clean universe;
- did not infer ACTIVE from Yahoo/provider rows;
- preserved immutable panel SHA `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

decisions_needed:
- independent review of FREN identity/PIT boundary and KOCI listing boundary;
- separate approval before investigating or repairing the no-factor H/L/C mismatch class.

blocking_risks:
- `49,476` unresolved Open rows remain;
- provider and symbol-resolution errors are not an identity resolution;
- no-factor H/L/C mismatches may be provider scale/semantics or unobserved corporate-action effects;
- candidate completeness percentages are diagnostic, not certification evidence.

validation_run:
- external diagnostic artifacts generated under `D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810`;
- immutable panel re-hash unchanged;
- prior full pytest: `236 passed, 3 warnings`; no source/test changes in this task.

recommended_next_action:
- STOP for independent ChatGPT review; do not promote the derivative, start modelling, rerun Stage 5, or widen the source scope.
