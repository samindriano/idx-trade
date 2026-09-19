# Alpha Stage-A Consumer Audit V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Scope: read-only consumer/path/hash audit; external isolated staging only

## Question

After the Stage-A lineage audit, are current downstream structural artifacts
actually bound to the guarded feature hash, or are old generations being used
silently?

## Result

`PASS_WITH_HISTORICAL_LEGACY_ARTIFACTS_EXPLICIT`

- Current guarded structural outputs contain the active feature hash
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`.
- The old feature hashes appear only inside their historical staging folders:
  `stage-a`, `stage-a-v2`, `stage-a-v3`, and `stage-a-final`.
- No old feature hash was found hard-coded in current `research/*.py` code; the
  consumers accept an explicit `--features` path and record its hash in their
  output where applicable.
- Historical legacy JSON artifacts remain present and must not be mixed with
  guarded outputs by filename alone.

## Historical legacy references found

| Location | Hash | Interpretation |
|---|---|---|
| `stage-a/20260919T` | `074b1a84...` | earliest legacy generation; historical only |
| `stage-a-v2/20260919T-corrected-v2` | `cc65dc6b...` | corrected-v2 historical generation |
| `stage-a-v3/20260919T-corrected-v3` | `1fe49a16...` | historical v3 generation |
| `stage-a-final/20260919T-finalized` | `1fe49a16...` | byte-identical v3 duplicate |

These references occur in the corresponding generation's own manifest,
robustness, or independent-audit JSON. They are not evidence that current
guarded downstream outputs use those generations.

## Current guarded consumers

The guarded staging root contains the active hash in C1/C2/C4 audit, economics,
capacity, corporate-action, identity, H-LIQ, combination, target-firewall,
Stage-A, C3, and structural-lab/robustness outputs. The newly regenerated
`alpha_structural_lab_v2.json` and `alpha_structural_robustness_v2.json` also
contain the same guarded hash.

The consumer audit did not open targets, outcomes, incumbent predictive scores,
providers, cloud/R2, capture, scheduler, or canonical production state.

## Control and implication

The active research rule is now explicit:

1. use the guarded feature hash and manifest as the only current structural
   input;
2. treat all older Stage-A directories as historical lineage, not alternative
   current inputs;
3. require every new artifact to record feature hash, manifest hash, code hash,
   source hashes, and repository head when available;
4. never infer PIT admission, population completeness, or predictive validity
   from a matching artifact hash.

No candidate status changed and no candidate ID was created.
