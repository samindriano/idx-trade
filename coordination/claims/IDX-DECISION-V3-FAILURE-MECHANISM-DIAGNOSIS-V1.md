# IDX Decision V3 Failure-Mechanism Diagnosis V1 — Claim

Date: 2026-08-22 Asia/Jakarta

Status: `ACTIVE`

Owner: `ChatGPT/Decision-V3-Failure-Mechanism-Diagnosis-V1`

Branch: `research/idx-decision-v3-failure-mechanism-diagnosis-v1`

Parent frozen result: `DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_REJECT`.

Parent plan digest: `1759d1b21849197257c638f6ac23ae0d3cdd320e34da820b4cc188d533931579`.

Frozen diagnosis contract: `docs/specs/decision_v3_failure_mechanism_diagnosis_v1.json`.

Canonical contract SHA-256: `3a72bf9de9edd7181f15d9cd6bf50d590828407704ded426cb13586f3a89fd03`.

Scope is outcome-blind descriptive diagnosis only:

- severe-exit clustering;
- mandatory-exit ↔ vacancy-refill coupling;
- Tier A/B/C/A-soft entrant lifecycle comparison;
- Block 3/6 mechanism consistency versus the remaining four blocks.

The diagnosis must use only the immutable V3 structural replay artifacts and must not rerun Decision V3, access the historical alpha parquet, simulate alternative policies/thresholds/counterfactuals, inspect returns/PnL/outcomes, refit models, call providers/network, implement a successor Decision, or activate paper/live behavior.

Implementation and tests may be prepared on this branch. Local diagnosis execution remains unauthorized until a separate adversarial implementation/contract audit accepts the exact runner lineage.
