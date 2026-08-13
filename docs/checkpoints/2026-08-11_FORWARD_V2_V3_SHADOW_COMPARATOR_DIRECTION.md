# Research checkpoint — V2 + V3-B forward shadow recording

Date: 2026-08-11 (Asia/Jakarta)
Status: `RESEARCH_DIRECTION_RECORDED_NOT_AUTHORIZED`
Branch: `research/idx-ranking-v2-spec-v1`

## Question

Should fresh-forward monitoring record only the final V3-B champion, or also preserve the frozen V2 champion as a forward comparator?

## Recommendation

Keep the scientific roles distinct:

- **V3-B Structure-Lite** remains the sole final historical-development champion and the primary model under the existing exact 100-session fresh-forward verdict contract.
- **V2 HGB_XS_MARKET** remains frozen as the historical upstream champion/baseline. It should not be treated as a second co-champion.
- Before any fresh-forward realized outcome is accessed, it is methodologically useful to record **outcome-blind daily scores/ranks from both frozen models**. This preserves a clean forward comparator for the incremental value added by the eight Structure-Lite features.

Conceptually:

```text
V2 HGB_XS_MARKET        -> frozen shadow comparator
V3-B Structure-Lite     -> frozen primary/final champion

same future signal date
        |
        +-- save V2 score/rank
        +-- save V3-B score/rank
        |
        +-- no realized outcome access yet
```

## Why record both

If only V3-B is recorded, the eventual 100-session result can answer whether V3-B works forward, but it loses the cleanest direct answer to a second question: whether Structure-Lite adds forward value over the V2 information set.

Recording both pre-outcome is cheap and does not require changing either model. The V2 artifact acts as a fixed shadow comparator rather than a candidate that can replace V3-B post hoc.

## Guard against researcher degrees of freedom

The comparator must be frozen now, before any fresh-forward realized outcomes are inspected.

Future evaluation must not:

- choose between V2 and V3-B after seeing the forward block and retroactively redefine the champion;
- tune either model using the forward block;
- alter feature order, model artifacts, score transforms, universe semantics, or ranking logic;
- use V2 performance to rescue a failed V3-B primary verdict;
- shorten or selectively subset the exact 100-session primary block.

The clean interpretation would be:

1. V3-B receives the predeclared **primary independent forward verdict**.
2. V2 is a **secondary fixed comparator** for incremental Structure-Lite attribution.
3. Both daily predictions may be accumulated outcome-blind before maturity/access.

## Boundary

This checkpoint records the methodology direction only. It does not by itself authorize frontend/backend changes or outcome access. If adopted, the forward monitoring contract should be updated explicitly before any realized forward outcome is opened.
