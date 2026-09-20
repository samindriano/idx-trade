# Packet Nested Schema Challenger Result V1

Date: 2026-09-20 (Asia/Jakarta)  
Experiment: `TOOLING-041`  
Status: `PASS_NESTED_ALLOWLIST_CHALLENGE`

## Question and boundary

Does a draft strict nested schema allowlist catch unknown or missing nested
authority-packet fields that the current packet verifier accepts?

This is a research-only proposal. The current verifier is not modified. The
challenger reads the existing outcome-blind authority packet structure and
applies temporary synthetic mutations only. It does not read protected
outcomes, providers, cloud state, canonical data, capture, telemetry, or
production state.

## Design

The draft allowlist pins the current packet's top-level keys and known nested
keys, including candidate-specific `required` fields, eligibility provenance
rows, taxonomy entries, and H-EXC subform names. Six cases are tested:

1. baseline packet;
2. unknown nested field under candidate C1;
3. unknown top-level field;
4. unknown field under bounded admission;
5. unknown field in an eligibility provenance row;
6. missing C3 `revision_vintage` required field.

The current verifier result is recorded alongside the draft strict result.

## Result

- Baseline: strict PASS and current verifier PASS.
- Strict allowlist: all five mutations FAIL.
- Current verifier: unknown top-level field FAILS, but the four nested/missing
  mutations PASS.
- Trial count: 6.

This confirms a concrete nested-schema false-green surface and provides a
research-only allowlist shape. It does not authorize integration or claim that
key allowlisting solves value semantics or verifier freshness.

## Red-team and limitations

The first draft of this challenger was itself too strict: it treated every
candidate's required fields as the union of all candidates and treated H-EXC
subforms as objects. That draft failed its baseline. The schema was corrected
against the actual packet structure before the accepted run. This correction is
recorded as harness development, not evidence against the production verifier.

The accepted allowlist remains reviewed only within this isolated lane. It does
not validate value types/ranges, semantic meaning, serialization freshness, or
the expected verifier code/version contract.

## Disposition

`SUPPORTED_SCOPED`: the current verifier's nested permissiveness is confirmed
by synthetic fixtures, and a draft strict schema catches the declared cases.
Keep it separate from the production verifier until independently reviewed and
explicitly adopted. The protected boundary remains closed.

Evidence:

- `research/alpha_packet_nested_schema_challenger_v1.py`
- `research_knowledge/packet_nested_schema_challenger_v1.json`
- external result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_packet_nested_schema_challenger_v1.json`
- code SHA-256:
  `b3a621052952dda41619a55e4939f90f7c964882367eae3a2b5ce3eb2caf27a1`
- external result SHA-256:
  `2e1a8ef14427bd8226a16c160bc70f7e72aefb943fb59ec621310069d2163429`
