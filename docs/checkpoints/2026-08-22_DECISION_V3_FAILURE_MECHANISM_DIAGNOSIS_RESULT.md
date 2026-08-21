# Decision V3 Failure-Mechanism Diagnosis V1 — Result

Date: 2026-08-22 Asia/Jakarta

Status: `COMPLETE_OUTCOME_BLIND_DECISION_V3_FAILURE_MECHANISM_DIAGNOSIS`

Parent: `DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_REJECT`

Parent plan digest: `1759d1b21849197257c638f6ac23ae0d3cdd320e34da820b4cc188d533931579`

Diagnosis manifest SHA-256: `73350606e408f987602575797f67474f83839256debee7e7b74496255beb0cab`

## Guard status

All diagnosis guards remained closed: no Decision V3 replay rerun, no alternative rule/threshold simulation, no counterfactual policy simulation, no historical alpha source access, no realized returns/PnL, no protected/fresh-forward outcomes, no model refit/retune, no provider/network access, no successor Decision implementation, and no paper/live activation.

Terminal-observation hardening was active: next-session rates exclude terminal entries and eventual-exit rates use completed spells only.

## Primary findings

### 1. Severe exit is the dominant churn coupling

Across 599 non-bootstrap transitions:

- severe-exit sessions: `373 / 599 = 62.2705%`;
- severe exits total: `1,040`;
- severe-exit sessions with vacancy fill: `373 / 373 = 100%`;
- observed replacements on severe-exit sessions: `1,315`, or `77.8567%` of all observed replacements;
- high-churn share on severe-exit sessions: `66.4879%`;
- high-churn share without severe exit: `19.0265%`;
- sessions with >=2 severe exits: `243`;
- sessions with >=3 severe exits: `157`;
- maximum consecutive severe-exit-session run: `42`.

Interpretation: V3 fixed rank-quality by making >50 an immediate exit, but every severe-exit session was immediately coupled to vacancy refill. The descriptive evidence strongly supports exit-refill coupling as the central structural churn mechanism. This is incidence evidence, not a causal counterfactual estimate.

### 2. Tier C is materially fragile, but not uniquely responsible

Entrant lifecycle:

| Tier | Entries | Median hold | One-session share | Next-session severe | Eventual severe |
| --- | ---: | ---: | ---: | ---: | ---: |
| A vacancy | 721 | 2 | 27.8940% | 22.9167% | 65.4114% |
| B vacancy | 262 | 2 | 34.7328% | 30.1527% | 74.4275% |
| C residual vacancy | 283 | 2 | 41.4894% | 38.8693% | 82.6241% |
| A soft replacement | 422 | 3 | 23.0216% | 8.7886% | 32.1343% |

Tier C is clearly the weakest admission class: `110 / 283` severe-exit next session and `233 / 282` completed spells eventually severe-exit. However Tier B and even Tier A vacancy entrants also show substantial severe-exit incidence. Therefore removing Tier C alone is unlikely to solve the full churn problem.

### 3. Stress blocks 3 and 6 amplify the same mechanism

Blocks 3+6 versus reference blocks 1/2/4/5:

| Metric | Blocks 3+6 | Reference |
| --- | ---: | ---: |
| Mean replacements | 3.87 | 2.2932 |
| High-churn share | 72.50% | 36.5915% |
| Severe-exit-session share | 87.50% | 49.6241% |
| Severe exits / transition | 3.09 | 1.0576 |
| Vacancy fills / transition | 3.56 | 1.3885 |
| Soft replacements / transition | 0.31 | 0.9023 |
| Severe-refill overlap share | 87.50% | 49.6241% |
| Tier-C next-session severe | 43.5644% | 27.1605% |

The stress blocks are not primarily a soft-replacement problem: soft replacements are lower there. They are dominated by clustered severe exits followed by vacancy fills. This supports a common mechanism with higher intensity rather than evidence for a separate regime-specific Decision rule.

### 4. Soft replacement is not the principal V3 failure mechanism

A-soft entrants are the most durable observed admission class: median hold 3 sessions, next-session severe rate 8.7886%, eventual severe rate 32.1343%. Severe-exit sessions overlap with soft replacements on only 101 of 373 severe sessions. Soft replacement may still contribute some churn, but the diagnosis does not support treating it as the primary failure mechanism.

## Scientific conclusion

The minimum evidence-supported successor hypothesis is not "relax the severe threshold" and not "delete Tier C only". The central defect is the coupling:

`clustered mandatory severe exits -> immediate same-session vacancy refill -> fragile entrant -> later severe exit -> refill again`.

Rank-quality and capacity improvements achieved by V3 should be preserved. The next research step should therefore target **exit/refill decoupling with graded refill permissions**, while keeping severe exit itself immediate and keeping the alpha/rank model unchanged.

No successor rule is authorized by this result alone. Any Decision V4 candidate must be separately preregistered before implementation/replay, with exactly one frozen mechanism and no threshold sweep/rescue variants.
