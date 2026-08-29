# IDX-Trade adversarial challenge checkpoint

This checkpoint is outside the target repository and was created read-only with
respect to IDX-Trade.

Audit epoch:

- `origin/main@adc071d6fd7e8009557bed27b1224217421514ae`
- production E2E implementation `6b6a41114a910287b413a099a36d59c5e057a8f2`
- Research Integrity PR #103 observed head `a1096aa1e0507f63b86a014201033d5c354840f9`
- CA remediation PR #108 observed head `d018ba4dc4d55daa48d9832b65df6d68e469d396`

Scope: static/read-only challenge of A1-A24 plus new materially distinct
findings. No provider, R2, outcome, PaperState, scheduler, counter, secret,
workflow, branch, PR, or target-repository write was performed.

Status: `AUDIT_NOT_SATURATED_CONTINUATION_RECOMMENDED`.

Four hunter ledgers were collected. A separate challenger was attempted twice;
bounded waits did not return a verdict and the worker was stopped. The
classifications in `challenge_ledger.csv` are therefore conservative integrated
adjudications, not independent challenger clearance.

Ontology correction preserved from current evidence: 412 source evidence rows;
389 economic physical events; 155 resolved transitions; 188 unresolved
economic events/transitions; 46 non-basis excluded. These categories must not be
collapsed.
