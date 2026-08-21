# Decision V4 Refill Decoupling V1 — Preregistration

Date: 2026-08-22 Asia/Jakarta

Status: `PREREGISTERED_NOT_IMPLEMENTED_NOT_REPLAYED`

Rule ID: `V4_X1_DECISION_V4_REFILL_DECOUPLING_V1`

Frozen profile: `docs/specs/decision_v4_refill_decoupling_v1.json`

## Evidence basis

Decision V3 fixed rank-quality and capacity but structurally rejected because churn/holding gates failed. The accepted outcome-blind V3 failure-mechanism diagnosis identified the dominant coupling:

`clustered severe exits -> immediate same-session vacancy refill -> fragile entrant -> later severe exit -> refill again`.

Key diagnosis evidence:

- 373/599 non-bootstrap transitions had at least one severe exit;
- all 373 severe-exit sessions also had vacancy fill;
- 77.8567% of observed replacements occurred on severe-exit sessions;
- high-churn share was 66.4879% on severe-exit sessions versus 19.0265% without severe exit;
- Tier-C next-session severe rate was 38.8693%, Tier-B 30.1527%, Tier-A vacancy 22.9167%, while Tier-A soft replacement was 8.7886%;
- Blocks 3+6 showed the same mechanism at higher intensity rather than a distinct regime mechanism.

Diagnosis manifest SHA-256: `73350606e408f987602575797f67474f83839256debee7e7b74496255beb0cab`.

## Single successor mechanism

All Decision V3 incumbent semantics and rank thresholds remain unchanged, including immediate severe exit at current rank >50, one-session mild grace for 21..50, Tier-D prohibition, target count 10, and soft-replacement gap 5.

The only policy change is **severity-conditioned refill permission**:

- if the current session has at least one `SEVERE_DETERIORATION_EXIT`, vacancy filling is restricted to Tier A (`A_CORE`) only;
- Tier B and Tier C cannot fill vacancies on that severe-exit session;
- if the current session has no severe exit, vacancy priority remains V3 A -> B -> C;
- temporary underfill is explicitly allowed;
- soft replacement remains exactly V3 semantics and is not disabled on severe-exit sessions.

This is intended to decouple clustered severe exits from immediate weak-evidence refill while preserving the V3 quality correction. It does not change the severe threshold, mild threshold, challenger tier definitions, or alpha model.

## Frozen gates

All V3 structural gates are retained unchanged. No gate is relaxed to accommodate the successor:

- mean replacements <=2.25;
- turnover vs naive <=0.50;
- share transitions with >=3 replacements <=0.35;
- median completed holding >=3;
- one-session completed holding share <=0.35;
- mean full-target Top10 overlap >=6;
- mean target rank <=12;
- mean target size >=9;
- share target size 10 >=0.70;
- share target size <=8 <=0.10;
- zero processed targets above rank50;
- zero second-consecutive retained observations rank21..50;
- zero post-bootstrap previous-absent entrants.

## Forbidden rescue variants in the same replay

No alternative refill caps, no threshold sweep, no severe-threshold change, no mild-threshold change, no soft-gap change, no soft-replacement disable, no Tier-D admission, no min-hold, no cooldown, no turnover cap, and no regime-specific rule.

## Authorization boundary

This preregistration does not authorize implementation or historical replay by itself. Independent adversarial preregistration review is required first. A later implementation must be audited before any one-shot structural replay. No returns/PnL/protected-forward outcomes may be accessed.
