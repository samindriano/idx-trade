# Runtime Contract Forensics — Result V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_READ_ONLY / NO_ADMISSION_CHANGE`

## Executive result

The exact pinned E2E runtime was inspected without executing production or
opening protected evidence. Two earlier concerns were refined:

1. The low-level Decision V2 function accepts any strictly increasing
   `previous_session` date; it does not itself require the immediately
   preceding official session. However, the pinned production controller
   derives the predecessor from the official session sequence and passes that
   exact date to the previous-score resolver. The active controller path is
   therefore adjacency-controlled. The low-level API remains weaker than a
   self-contained contract if called outside that controller.
2. The available frozen panel contains no zero, nonfinite, or negative
   `regular_market_value` in the tested 600-session tail, including fixed
   Top-30 C1-C4 selections. The zero-capacity path is therefore not observed
   in this evidence. A latent boundary risk remains because the direct EOD
   verifier maps a missing/nonfinite value to `0.0`, while the allocator
   interprets zero as capacity zero; upstream forward-input validation rejects
   nonfinite/negative values but allows zero.

A third hardening observation is durable: the runtime has a pinned adapter
config verifier, but no call site was found in the exact runtime outside the
definition/tests, and the E2E execution payload carries rule/data hashes but
not the adapter-config hash. This is a configuration-lineage risk, not proof
of current production drift.

## Exact evidence

### Score adjacency

- `decision_v2_minimal.py:301-309` checks only
  `previous_date < current_date` and shadow-state date equality.
- `e2e_paper_operational_controller_v1.py:500-518` derives the maximum
  official-calendar session strictly before the current session once Decision
  metadata exists; `:1167-1173` passes it to the exact previous-score resolver.
- The resolver then requires the exact expected date and rejects missing,
  ambiguous, or hash-mismatched metadata.
- A first-ever Decision is intentionally allowed to bootstrap mid-calendar
  when no Decision metadata exists. That is a documented exception, not a
  silent gap.

Classification: `ACTIVE_CONTROLLER_ADJACENCY_CONTROLLED /
LOW_LEVEL_API_NOT_SELF_CONTAINED`.

### Market-value denominator behavior

- `forward_ohlcv.py:55-63` rejects nonfinite or negative model-input values,
  but accepts zero.
- `v4_x1_execution_v1_verify.py:203-206` uses a nonnegative finite parser and
  assigns `0.0` when the parsed value is missing/invalid.
- `v4_x1_execution_v1.py:274-278` and `:393-395` clamp the capacity
  denominator at zero; zero can yield `REFERENCE_DAY_CAPACITY_ZERO` or
  `REFERENCE_DAY_CAPACITY_ZERO_PENDING`.

### Configuration lineage

- `v4_x1_execution_v1_decision_v2_config.py:14-53` defines a byte-hash and
  semantic verifier for the Decision V2 adapter config.
- The exact runtime search found the verifier definition and tests, but no
  production call site outside those definitions/tests.
- `e2e_paper_orchestration_v1.py:267-302` serializes Decision/Sizing/
  Execution payload identities, including rule IDs, state hash, EOD model
  input hash, and official calendar hash, but not the adapter-config hash.

## Frozen-panel denominator census

Scope: same hash-pinned structural artifacts used by the prior Rank-to-Open
audit; tail window `2024-01-12` through `2026-07-31` (`600` official sessions).

| Scope | Rows | Positive finite | Zero | Nonfinite | Negative |
|---|---:|---:|---:|---:|---:|
| All joined rows | 503,797 | 503,797 | 0 | 0 | 0 |
| Eligible decision universe | 155,679 | 155,679 | 0 | 0 | 0 |
| C1 Top-30 | 18,000 | 18,000 | 0 | 0 | 0 |
| C2 Top-30 | 18,000 | 18,000 | 0 | 0 | 0 |
| C3 Top-30 | 8,340 | 8,340 | 0 | 0 | 0 |
| C4 Top-30 | 18,000 | 18,000 | 0 | 0 | 0 |

This is a structural panel census, not a production EOD incidence rate and
not executable-capacity proof. It cannot establish whether a future provider
row can be missing, revised, or unavailable at decision time.

## Durable interpretation

- Do not label the prior adjacency concern as a confirmed production failure;
  the active controller supplies the official predecessor correctly.
- Keep the low-level Decision V2 API boundary as a hardening/open question if
  it is ever reused outside the controller.
- Do not claim that invalid market-value denominators affected the frozen
  C1-C4 research: the available census found none.
- Preserve the configuration-lineage gap as a future runtime-hardening item;
  no code change is authorized in this research lane.
- No alpha candidate, Decision V2 policy, sizing math, execution math,
  canonical data, capture, cloud, telemetry, or protected outcome changed.

## Provenance

- Preregistration:
  `docs/checkpoints/2026-09-20_ALPHA_RUNTIME_CONTRACT_FORENSICS_PREREGISTRATION_V1.md`
- Census code: `research/alpha_execution_capacity_denominator_census_v1.py`
- Census result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-capacity-denominator-census\alpha_execution_capacity_denominator_census_v1.json`
- Census result SHA-256:
  `704c68540b750a8ebb831a18444094b2fd362876cac4abaca698de5f20fde2a1`
- Census code SHA-256:
  `fea3b72683ade1e8a0cc5ac72093f4a027ceefa9e36c6e447fd9ceedbe6e0177`
- Runtime ref:
  `045e25a19d9f71170d2c863e768102937e59ad73`
- Feature SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official-session SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
