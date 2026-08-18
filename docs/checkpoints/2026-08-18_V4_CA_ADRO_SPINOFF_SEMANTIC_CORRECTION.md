# V4 CA ADRO / AADI Semantic Correction

Date: 2026-08-18
Branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`
Status: `ADRO_REMAINS_FAIL_CLOSED_SPINOFF_PUPS_REVIEW_REQUIRED`

## Correction

The frozen ADRO 2024 `Right Distribution` event must not be classified as a harmless separate-security entitlement merely because KSEI records the distributed security as `ADRO-H`.

The event is part of the 2024 separation/divestment of PT Adaro Andalan Indonesia (AAI, subsequently listed as AADI) from ADRO/AlamTri through a Penawaran Umum oleh Pemegang Saham (PUPS). Official company materials state that ADRO offered up to all AAI shares owned by ADRO to eligible ADRO shareholders. AADI listed on IDX on 5 December 2024.

The PUPS prospectus states that shareholders recorded on 29 November 2024 receive purchase rights, at a ratio of 4,389 ADRO shares to 1,000 purchase rights, and one purchase right may be used to buy one AAI share owned by ADRO. KSEI's ADRO registered-security history records the same event as `Right Distribution (4389 ADRO : 1000 ADRO-H)` with Record Date 29 November 2024 and Distribution Date 2 December 2024.

Because the event removes/offers a major operating asset held by ADRO and creates an entitlement linked to ADRO ownership, it cannot be declared non-blocking without a defensible market-basis transition treatment.

## Repository action

A premature exact-event ADRO non-blocking overlay was started but immediately reverted before any local runtime or continuity replay used it. The temporary ADRO PUPS semantic helper was deleted. The targeted classifier is restored to the prior NISP-only special overlay.

## Current accepted state

The V4 linkage-remediation result remains:

- NISP exact static non-blocking: accepted;
- PANI exact Regular-Market Ex Date: accepted;
- CUAN exact first-new-basis Regular-Market date: accepted;
- ISAT exact first-new-basis Regular-Market date: accepted;
- PTRO exact first-new-basis Regular-Market date: accepted;
- RAJA exact first-new-basis Regular-Market date: accepted;
- ADRO: unresolved / fail closed.

No continuity replay should use a non-blocking ADRO overlay.

## Next question

ADRO needs a separate exact semantic review to determine the defensible Regular-Market entitlement/ex-right boundary for the PUPS/AADI separation. Candidate evidence must come from official PUPS/dividend/KSEI schedules and must not infer the transition from price behavior. Record/Distribution dates alone remain insufficient.
