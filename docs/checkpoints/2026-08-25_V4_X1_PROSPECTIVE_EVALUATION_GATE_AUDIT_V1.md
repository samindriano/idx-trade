# V4-X1 Prospective Evaluation Gate V1 — Audit Remediation Checkpoint

Date: 2026-08-25 (Asia/Jakarta)

Status: `PROSPECTIVE_EVALUATION_GATE_V1_AUDITED_CANONICAL_TARGET_IDENTITY_BLOCKED`

## Scope

This checkpoint records an outcome-blind audit and hardening pass over the
V4-X1 prospective-evaluation access boundary. It does not open protected
outcomes, call the real protected loader, write the real access marker, alter
the forward counter, or change the model/Decision/Sizing/Execution contracts.

The branch remains an isolated draft-PR review lane. `coordination/TEAM_STATUS.md`
was not edited because MAIN owns that file.

## Canonical identity finding

The canonical V4-X1 prospective target is not uniquely provable from the
retained pre-outcome lineage. The following non-equivalent historical
identities were observed:

- common-support Spearman: `0.097554036`;
- separate frozen-evaluator headline: `0.09805414600339561`;
- comparison mean: `0.099248615`;
- requested exact value `0.0980538834688018`: not found across the audited
  retained refs.

Because the target identity, target definition, and target provenance cannot
be bound to one exact canonical source, the gate remains fail-closed. No H5,
H10, or H20 target inference is allowed as a substitute.

## Frozen machine contracts

- Contract: `config/v4_x1_prospective_evaluation_contract_v1.json`
- Contract SHA-256: `6d64c76dc60ef04f02e9a811e920e7351c00b94aaa2cc834f6019d4a648cb8ac`
- Code-pin manifest:
  `config/v4_x1_prospective_evaluation_code_pin_v1.json`
- Code-pin manifest SHA-256: `08acb91d9bdde214856ed19fc86a70b5b10c81efe749b375448942b873d9b2cd`
- Evaluator implementation pin: `b4acde477f2d4e895c0e38ddccde94d6d783f43c`
- Gate source pin: `32bf47b86623b7ba0b551179c931ec0e45cec55e`
- Protocol commit: `ed719dd67ae93b6b20f02579df80fd67eec331dd`
- Protocol Git blob: `f76af5733db3c6a2c7a99b1e80268004ece1e616`

The code-pin validator now binds the supplied evaluator and gate paths to the
modules actually executing the validation. It also verifies exact Git blob
hashes, model identity, contract hash, and 40-hex source-commit identities.

## Remediation completed

- preflight-only CLI emits explicit no-access booleans and blocks unresolved
  canonical target identity;
- preflight-only CLI cannot claim readiness without a complete, hashed input
  bundle; when supplied, the bundle reuses the same pure session/counter/
  target/PaperState/benchmark/access-audit validators without loading outcomes;
- real mode requires explicit authorization, a resolved target, exact 100/100
  maturity, the audited code-pin manifest, and exact target-source binding;
- a future resolved target must carry an exact construction-code path, SHA-256,
  and source-commit pin bound identically in the frozen contract and attestation;
- score artifacts require the exact schema `date/session_date`, `ticker`,
  `alpha_consensus`; extra neutral or outcome-like columns are rejected;
- score manifests reject unknown top-level fields and recursively reject
  outcome-like metadata keys, including nested values;
- session inventory, execution, and order frames require exact 100-session
  coverage and unique session keys;
- PaperState detailed transition evidence, material-drag status, and rule id
  are required for the protected path;
- non-finite bootstrap replicates are retained as
  `INCONCLUSIVE_STATISTICS` and cannot produce a positive verdict;
- immutable JSON publication uses fsync + no-overwrite hard-link publication;
  temporary/orphan files and partial prior state fail closed;
- every verified pre-access byte source is rehashed immediately before marker
  publication, so post-validation replacement is fail-closed (Windows directory
  fsync remains unavailable; file fsync and no-overwrite publication remain);
- fresh-process A/B/C synthetic coverage proves durable completion reuse and
  identical immutable hashes without re-calling the loader.
- explicit transaction-stage fault tests cover all 11 before/after boundaries,
  and two simultaneous first-run processes prove only one loader/result wins.

## Validation

Focused gate/evaluator/preflight tests:

```text
python -m pytest -q tests/test_prospective_evaluation_gate_v1.py \
  tests/test_prospective_evaluation_v1.py \
  tests/test_prospective_evaluation_preflight_v1.py
82 passed
```

Additional checks:

- `python -m py_compile` for the gate, evaluator, and preflight CLI: PASS;
- `git diff --check`: PASS before publication;
- full repository pytest: `158 passed`, exit code `0` on the final executable state;
- no provider/network call and no protected artifact was loaded.
- independent adversarial re-review: PASS; no remaining P0/P1 findings;
  specifically confirmed independent CLI pin-before-import and target-construction
  inclusion in the final pre-marker rehash.

Final executable/code identity:

- branch HEAD: `916ae24d2f77a1bbc37e3fdf664bf1f68e63eaab`;
- code-pin manifest SHA-256:
  `ee260b46f9150f150e3280bc142370baf23615efc6fea90198382f470fc3f46a`;
- gate source commit: `ff05f3a8c6f398217c6eba395fca5ea11ad3dacb`;
- gate Git blob: `499deedd5c4549285adb12bed68f427bf60d2bc8`;
- frozen contract SHA-256 remains
  `6d64c76dc60ef04f02e9a811e920e7351c00b94aaa2cc834f6019d4a648cb8ac`.

## Boundary flags

```text
PROSPECTIVE_OUTCOMES_ACCESSED=false
REAL_PROTECTED_LOADER_CALLED=false
REAL_OUTCOME_ACCESS_MARKER_WRITTEN=false
FORWARD_COUNTER_CHANGED=false
MODEL_CHANGED=false
DECISION_CHANGED=false
SIZING_CHANGED=false
EXECUTION_CHANGED=false
SCHEDULER_CHANGED=false
```

## Next action

MAIN/ChatGPT review must first resolve and freeze one canonical target
identity, including exact target definition, horizon, transform, source
manifest, and hashes. Only then may a separately authorized real 100/100 run
be considered. This branch does not authorize that run.
