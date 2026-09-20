# Formula Mutation Challenger Result V1

Date: 2026-09-20 (Asia/Jakarta)  
Experiment: `TOOLING-040`  
Status: `PASS_SEMANTIC_MUTATIONS_DETECTED`

## Question and boundary

Does the current independent C1/C2/C4 constructor replay detect plausible
semantic formula or mask mutations when challenged by an independently written
reference implementation?

The experiment uses only a temporary synthetic fixture: three tickers, 150
official business sessions, and 450 panel rows. It does not read admitted
panel data, providers, cloud state, protected outcomes, or production state.
It does not modify the replay, packet verifier, firewall, or canonical data.

## Design

The challenger independently constructs the session grid, 60-session
eligibility, causal rolling inputs, C1/C2/C4 scores, and average-tie ranks. It
first writes the independent baseline into a temporary feature artifact and
requires the existing constructor replay to pass. It then runs five predefined
mutations, preserving all trials:

1. C1 beta denominator changed from market variance to stock variance;
2. C1 market timing changed from prior market return to current market return;
3. C2 logarithm removed from abnormal turnover;
4. C4 reversal sign flipped;
5. one eligible mask entry flipped to ineligible.

## Result

- Baseline: PASS, 450/450 keys and all score/rank checks aligned.
- Trial count: 6 total (one baseline plus five mutations).
- All five mutations were detected by at least one score, rank, or eligibility
  check.
- The result is scoped semantic sensitivity evidence, not proof of formula
  correctness on the admitted panel.

## Red-team and limitations

The initial 72-session fixture was insufficient: C1 had no finite support
because it needs the 60-session eligibility warm-up plus a 60-observation beta
window. That harness limitation was corrected before the accepted run by using
150 sessions. The accepted output therefore records 150 sessions, not the
initial insufficient fixture.

Synthetic mutation detection cannot establish PIT, issuer continuity,
corporate-action basis, executable capacity, or predictive validity. It also
does not prove that every possible semantic mutation is detected.

## Disposition

`SUPPORTED_SCOPED`: the constructor replay is demonstrably sensitive to these
five declared semantic mutations on an independent synthetic fixture. Keep the
existing distinction between implementation reproducibility and scientific
validity. Reopen only with a policy-authorized structural fixture, a reviewed
oracle, or a new producer/verifier semantic contract.

Evidence:

- `research/alpha_formula_mutation_challenger_v1.py`
- `research_knowledge/formula_mutation_challenger_v1.json`
- external result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_formula_mutation_challenger_v1.json`
- code SHA-256:
  `86c6fd1d9ad18cdb2b29f110a5a6f7b522cd4a3c2eebcbdd3251f67f2409d434`
- external result SHA-256:
  `044d92db4c49e0c9744127fcfca6d30820dd80f358f7a43254acd8f33c5d6ce5`
