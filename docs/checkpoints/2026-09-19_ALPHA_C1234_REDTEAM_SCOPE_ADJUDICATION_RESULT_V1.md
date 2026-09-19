# C1/C2/C4 Red-Team Scope Adjudication — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_NARROW_STRUCTURAL / SCOPE_LIMITATION_RECORDED`

## Question

Does the current C1/C2/C4 adversarial replay independently rebuild the entire
feature/eligibility construction, or does it only independently validate the
stored artifact and selected structural invariants?

This is a read-only audit of the existing red-team tooling. It does not open
targets, rerun protected evaluation, modify candidate artifacts, or change the
protected C1-C4 packet.

## Findings

The current v2 verifier provides useful narrow structural evidence:

- C1 support: `295,243` finite eligible rows; C2: `310,761`; C4: `310,323`.
- Feature/panel keys, duplicate keys, official dates, chronology, listing
  intervals, finite score/rank masks, and rank bounds pass the registered
  checks.
- Deterministic score-descending/ticker-ascending selection is present.
- The corrected key-aligned lookback replay covers `600` dates and reports C1
  `57.2333%/52.0389%`, C2 `65.3167%/60.1389%`, and C4
  `44.7611%/45.4111%` for the registered variants.

The scope limitation is material: `research/verify_alpha_c1234_adversarial_audit_v2.py`
reopens and checks stored feature values, panel keys, dates, listing intervals,
and artifact declarations, but it does not independently rerun the feature
constructor or rebuild eligibility from raw inputs. The robustness replay also
compares recomputed values only on the intersection where both stored and
recomputed values are finite. A finite-mask mismatch could therefore pass
without being a full-construction certification.

## Adjudication

| Claim | Result |
|---|---|
| Stored artifact/schema/key/calendar/rank invariants | `PASS — narrow structural` |
| Deterministic ranking contract | `PASS` |
| Corrected temporal replay arithmetic | `PASS — artifact/structural replay` |
| Full independent feature-constructor rebuild | `UNKNOWN / NOT PROVEN` |
| Independent eligibility reconstruction | `UNKNOWN / NOT PROVEN` |
| PIT/CA/identity/survivorship authority | `UNKNOWN / BLOCKED` |
| Predictive/OOS/IC/ICIR evidence | `NOT RUN / PROTECTED` |

Current language claiming an “independent source-recomputing replay” for the
full C1/C2/C4 construction is too broad. The correct wording is:
`independent artifact/structural replay with explicit construction-scope
limitation`. This does not invalidate the narrow structural checks, but it
prevents a false-green interpretation of full causal reconstruction.

## Disposition

Keep C1/C2/C4 as `FUTURE_RESEARCH`; do not promote, refit, expand the packet,
or open targets. A future stronger verifier may independently reconstruct the
feature constructor and eligibility masks, but that is a separate tooling task
and is not required to reinterpret the current evidence as predictive.

## Reproducibility

- Verifier: `research/verify_alpha_c1234_adversarial_audit_v2.py`; SHA-256
  `807ad882a45aea24ce7e72dc68c642a29512fe79b5d29e0f88be88ccb4be3f46`.
- Independent replay output SHA-256:
  `0f147bf0babbeb854f16a328b748eab13d85dbb56e5f48e6590cda5b6a04a2e8`.
- Key-aligned robustness output SHA-256:
  `64d03527b7bb504dee34e854ed9123f03fb55c557a455462eef46a928c823444`.
- Audited C1/C2/C4 artifact SHA-256:
  `6bfcba7070be218d288a0cf894f8d7e54b170bf624966e38a758061ed7d6dae8`.

No target, outcome, provider, cloud, incumbent, canonical, capture, scheduler,
telemetry, or production state was accessed or modified.
