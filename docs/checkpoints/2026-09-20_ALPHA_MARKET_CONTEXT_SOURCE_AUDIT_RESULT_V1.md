# Alpha Market-Context / Breadth Source Audit — 2026-09-20

## Scope and disposition

This was a read-only audit in the isolated branch
`codex/alpha-available-data-20260919`. It inspected the already persisted local
market-index/breadth archive at
`D:/Documents/Project/idx-trade-market-index-breadth-20260812` and the frozen
Stage-A panel only. No network/provider call, protected label/return access,
model fit, IC/OOS evaluation, candidate creation, or canonical-data write was
performed.

Disposition: `PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`.

The archive is useful as a source-capability and arithmetic cross-check, but it
is not a complete PIT-admissible daily feature source. It therefore creates no
new alpha candidate and does not change the protected C1–C4 packet.

## Evidence and reproducibility

Builder: `research/alpha_market_context_source_audit_v1.py`

Verifier: `research/verify_alpha_market_context_source_audit_v1.py`

The builder and verifier both compile successfully. The independent verifier
returned `PASS` for the staged audit JSON. The target/privacy firewall returned
`PASS` for the scripts and staged outputs. A follow-up v5 adds an explicit
builder hash and hashes for the panel plus all 18 rich/digital source files;
the generic artifact hash-contract verifier returned `PASS` for all 19 inputs.

Staged audit:
`D:/Documents/Project/idx-alpha-available-data-staging-20260919/stage-a-final-guarded/20260919T-finalized-guarded/alpha_market_context_source_audit_v1_v4.json`

Staged verification:
`D:/Documents/Project/idx-alpha-available-data-staging-20260919/stage-a-final-guarded/20260919T-finalized-guarded/alpha_market_context_source_audit_v1_v4_verification.json`

Staged firewall result:
`D:/Documents/Project/idx-alpha-available-data-staging-20260919/stage-a-final-guarded/20260919T-finalized-guarded/alpha_market_context_source_audit_v1_firewall.json`

Hash-bound follow-up artifacts:

- audit v5:
  `D:/Documents/Project/idx-alpha-available-data-staging-20260919/stage-a-final-guarded/20260919T-finalized-guarded/alpha_market_context_source_audit_v1_v5.json`
- structural verification v5:
  `D:/Documents/Project/idx-alpha-available-data-staging-20260919/stage-a-final-guarded/20260919T-finalized-guarded/alpha_market_context_source_audit_v1_v5_verification.json`
- hash-contract verification v5:
  `D:/Documents/Project/idx-alpha-available-data-staging-20260919/stage-a-final-guarded/20260919T-finalized-guarded/alpha_market_context_source_audit_v1_v5_hash_contract.json`
- v5 firewall:
  `D:/Documents/Project/idx-alpha-available-data-staging-20260919/stage-a-final-guarded/20260919T-finalized-guarded/alpha_market_context_source_audit_v1_v5_firewall.json`

Recorded SHA-256 values:

| Artifact | SHA-256 |
|---|---|
| audit JSON v4 | `1a21fbe44a936383a55e3ba5fe10754db200010b6e80909961d8a923734eff82` |
| verifier JSON v4 | `17c6962aca961ae9dabdb77c2d19635bda81c85bb27105c4c437c5d284507332` |
| firewall JSON | `ea8e46c0292587bc2fb0f9d882dcf553db5f7020a411a6328be64f220daa4512` |
| audit JSON v5 | `49c15bf1f98195992f0892d3bada98d92b304eb5566f00bc4c3dad2651c2339b` |
| v5 structural verification | `3aee48c8bf5358d26c1bc299430351013c6c08fb5c139ad6250c02df2ab988df` |
| v5 hash-contract verification | `0af2d8a8c13ca9f5265dc3a66aca81714b2f12e009f4f02e31da0b88c39a3ed2` |
| v5 firewall | `a53e6760a3e1f637019301b31d5962168828e91d43593cbb4c4a352634435242` |
| builder v5 | `bd5836292588e3052276a09ca6b6d469393a258b6aa452b46c038edb4d024426` |
| verifier | `7f46e1d1e6fca907fde9deb43758f1e18e96ec6fa3530071c6eaa74f0ca239df` |

## Rich daily archive checks

The direct JSON and Zapi JSON copies were compared field-by-field for all
registered fields on all three sampled dates. Index and stock parity was exact;
no duplicate stock codes were found in the samples.

| Date | Index rows | Stock rows | Panel overlap | Zero-volume stock rows | Market-total reconciliation |
|---|---:|---:|---:|---:|---|
| 2021-01-04 | 36 | 717 | outside frozen horizon | 81 | localized source arithmetic discrepancy |
| 2024-06-21 | 44 | 930 | 825/825 = 100% | 105 | exact |
| 2026-07-31 | 45 | 963 | 830/830 = 100% | 133 | exact |

For 2021-01-04, the composite market totals do not equal the sum of the
regular and non-regular components in the local archive. The absolute
differences are volume `15,329,700` (about `0.0713%`), value
`2,933,457,900` (about `0.0202%`), and frequency `1,840` (about `0.1526%`).
This is recorded as a localized source/arithmetic exception, not silently
repaired or treated as a feature-ready condition.

## Digital archive coverage

The digital archive contains only the following sampled monthly blocks:

| Block | Market daily rows | Index series / rows |
|---|---:|---:|
| 2017-01 | 21 | 10 / 210 |
| 2024-10 | 23 | 46 / 1,058 |
| 2026-07 | 23 | 46 / 1,035 |

This is sparse sample coverage, not a continuous daily history over the frozen
panel. Digital market totals also show scale/rounding behavior in the 2026-07
sample, so they were not admitted as an alternative candidate source.

## PIT and admission conclusion

The archive can support future source-capability work for market breadth,
market participation, and index-context representations. It currently lacks
the continuous daily population, publication/available-at contract, revision
policy, identity-transition authority, and corporate-action semantics required
for PIT-safe feature admission.

| Item | Result |
|---|---|
| Structural parity of paired local sources | PASS on 3 sampled dates |
| Arithmetic reconciliation | PASS on 2024/2026; explicit 2021 exception |
| Continuous PIT daily coverage | NOT ESTABLISHED |
| Feature/candidate admission | CLOSED |
| Protected packet / incumbent model | UNCHANGED |

The next safe step, if new authoritative history and vintage metadata become
available, is a separate market-context specification and coverage audit. No
forward fill, panel substitution, model score, OOS claim, or production
promotion is authorized by this result.
