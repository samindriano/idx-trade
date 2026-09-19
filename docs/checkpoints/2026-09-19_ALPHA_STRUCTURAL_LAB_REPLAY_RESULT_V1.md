# Alpha Structural Lab — Independent Source Replay V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Evidence baseline commit: `126614b6e8d075d9df463ffa741c9170fb5f87e3`  
Verifier: `research/verify_alpha_structural_lab_v2.py`
Verifier SHA-256: `9a377cbb251dcf0811d9108668446e13379d5e9f94db460d70255145e43e453f`

## Verdict

`PASS_INDEPENDENT_SOURCE_REPLAY`

The verifier does not import or call the structural-lab builder. It re-reads the
declared feature, panel, and official-session inputs and independently
recomputes the complete candidate metric maps and pairwise orthogonality maps
present in the staged artifact.

## Exact evidence

Staged input/output directory:

`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`

| Artifact | SHA-256 |
|---|---|
| Guarded features | `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4` |
| Frozen panel | `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e` |
| Official sessions | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| Structural-lab builder | `715e1d96c83d8facf6f9a893f7dfbedcfbe5e192d69e50e3f6943c8fd66c7cf0` |
| Audited lab artifact (`alpha_structural_lab_v2.json`) | `30899d21d4cdc4940e0a926e5e7d73a66603f78bc4d8731df9c2be9cc08ed323` |
| Independent replay report | `364ea5159c432c989e3982b3e3fc1817c510613085b4b8aacdf54fb522c750c3` |

Replay report:

`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_structural_lab_independent_replay_v2.json`

Checks all passed:

- builder hash matches the artifact;
- feature, panel, and session hashes match;
- candidate IDs exactly match C1/C2/C3/C4;
- Top-K set exactly matches 10/20/30/50;
- frozen session count is 600;
- candidate coverage/distribution/rank-displacement/liquidity maps match;
- every Top-K turnover, overlap, entry/exit, persistence, concentration,
  liquidity, state, and block map matches;
- all six pairwise daily-correlation and Top-K-overlap maps match;
- `mismatch_count = 0`.

## Scientific interpretation

This closes the specific verifier weakness identified in the prior review: the
old verifier accepted artifact-envelope/range/hash claims without recomputing
the lab metrics. The old verifier remains historical tooling; this v2 replay is
the authoritative structural-lab verification for the current staged artifact.

The result is still structural only. It does not prove:

- historical PIT/as-of authority;
- population completeness or survivorship safety;
- issuer/ISIN continuity beyond the existing bounded mapping;
- corporate-action price-basis correctness;
- ADV, spread, queue, fill probability, or executable capacity;
- predictive value, IC/ICIR/OOS performance, or superiority to the incumbent.

The artifact's access flags remain metadata claims rather than process-level
proof. The verifier itself performed no target, outcome, incumbent-score,
provider, network, cloud, capture, scheduler, or telemetry access.

Additional verifier limitations retained explicitly:

- supplied score/rank columns are replayed as inputs; rank semantics are not
  reconstructed from raw price fields;
- official sessions are deduplicated/sorted before selecting the trailing 600,
  so this replay does not certify the upstream session source itself;
- Top-K selection follows the builder's `rank.notna()` behavior, while coverage
  separately treats infinities as non-finite;
- market-state rolling uses the available grouped dates rather than an
  independently reindexed full 600-session grid;
- liquidity remains a `regular_market_value` proxy, not executable capacity.

## Disposition impact

No candidate disposition changes. C1/C2/C4 remain `FUTURE_RESEARCH`, C3 remains
`BLOCKED`, and H-LIQ-01 remains
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`. No C5, `READY`, or
`RESEARCH_SURVIVOR` entry is created.

## Tests

- `python -m py_compile research/verify_alpha_structural_lab_v2.py` — PASS
- source replay command against the guarded inputs — PASS
- output mismatch count — `0`
- protected target/outcome access — not performed
