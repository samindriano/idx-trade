# O2 Forward Tracking Comparators

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-forward-v1`
Decision: `O2_PRIMARY_TRACKED_WITH_V3B_V2_AND_RANDOM_COMPARATORS`

## Tracking hierarchy

The user approved the forward-monitoring comparison set as follows:

1. `O2-GEOMETRY-FULL3-V1-CANDIDATE-001` is the primary tracked alpha challenger.
2. Canonical `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` remains the incumbent paired comparator and is not displaced before the protected forward gate is evaluated.
3. The accepted V2 historical model is retained as a legacy model comparator for context.
4. A random baseline is retained as a sanity-floor comparator.

## Random baseline reproducibility rule

The random comparator must be deterministic and reproducible across reruns. It must not draw a fresh random ordering each time. Its score/rank should be derived from a frozen seed or stable hash of immutable session/ticker identity so that the same official session produces the same random baseline.

The random baseline is descriptive only and must not influence model tuning, eligibility, counter progression, or the protected outcome-access boundary.

## Forward-evaluation boundary

- O2 remains the primary model being tested prospectively.
- V3-B, V2, and random are comparators; they do not create separate opportunities to peek at protected outcomes.
- No model promotion is implied by this tracking hierarchy.
- The official O2 100-session gate and no-outcome-peeking rules remain unchanged.
- Comparator scoring should use the same eligible rows wherever an apples-to-apples comparison is required; any population difference must be explicitly reported rather than silently mixed.

This checkpoint records monitoring/evaluation intent only. It does not authorize scoring before the first post-freeze official session and certified post-close snapshot are available.
