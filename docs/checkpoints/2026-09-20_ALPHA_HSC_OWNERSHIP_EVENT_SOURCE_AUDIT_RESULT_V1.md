# HSC Ownership Event Source Audit Result V1

Status: `PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`

This is a read-only, outcome-blind audit of the locally persisted HSC
ownership event ledger. It does not call IDX, open targets or outcomes,
modify canonical data, create a feature or candidate, or change capture,
cloud, telemetry, or production state.

## Structural evidence

- The `HSC_FULL_HISTORY_LEDGER_V1` manifest declares 137 artifacts: seven
  audit files, four normalized files, eight official metadata captures, and
  118 official PDF files.
- All 137 declared artifacts match their manifest byte counts and SHA-256
  values; no missing, escaping, byte-mismatched, or hash-mismatched artifact
  was found.
- The normalized ledger contains 59 unique event IDs and matches its JSON
  representation exactly. Required fields, ticker/date/timestamp formats,
  concentration ranges, provenance hashes, and revision links pass.
- Revision counts are 56 `ORIGINAL`, two `CORRECTION`, and one `REMOVAL`.
  Methodology counts are 17 `HSC_2026_INITIAL` and 42
  `HSC_2026_PRICE_IMPACT_REVISION`.
- The preserved replay checkpoints all pass. The effective cutoff target is
  55 tickers; the raw status rows still contain the removed LUCY event, so
  effective membership is taken from the manifest/replay target rather than
  from a naive `status=HSC_ACTIVE` row filter.
- Current and July target files match the manifest targets exactly (55 and 51
  tickers respectively). Two duplicate announcement keys are expected
  original/correction pairs, not duplicate event IDs.

## Admission limits

The source is an event ledger, not a population-wide daily ownership panel.
It does not establish complete issuer coverage, issuer/ISIN continuity,
corporate-action linkage, complete revision/vintage history, or a
public-availability/available-at contract. The bounded negative search remains
limited to the preserved official metadata captures; it is not evidence that
no later event exists.

Therefore the source remains capability-only and is not admitted for feature
construction, universe masking, candidate evaluation, or protected-packet
expansion. No ownership-derived alpha was created.

## Independent gates

- Structural audit: `PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`.
- Independent HSC envelope verifier: `PASS`.
- Generic isolated artifact hash contract: `PASS`.
- Outcome-blind research firewall: `PASS`.
- Network/provider/target/outcome/cloud access: none.

## Artifact provenance

- Source manifest SHA-256: `230fec0544fb7464e63008ee080fda0c8082049626529f0a565376601416b55d`
- Normalized CSV SHA-256: `afbbb642807e04d6050de3574fec49559eb8fcf2963039a53439e507f067cbd2`
- Normalized JSON SHA-256: `9033c801c042d6a10bf2a308513c8120ca8dd9585e85a95ae419a78ec874daa0`
- Audit JSON SHA-256: `cd57f1c922140b187e6c3736d8c2445666c8c4235bcbc9fed48062ec608b08f3`
- Independent verifier JSON SHA-256: `31566526ce2a3246ec1dac57a7ae2810a96052e9c2026d66960f18ad97648bab`
- Hash-contract JSON SHA-256: `13f579f1ecd8e8837eb948d5fc8315c7c0c826ba9148f326261a6c58beaaa2ed`
- Firewall JSON SHA-256: `4a4605ac80e65d280dbae211a077a57defc61340aa0ab07e7b5def514519af2f`
- Audit script SHA-256: `aa859e5349118a820a4c1abbea23044a9b80b5764844a9a9cf45f7db0fa0ede0`
- Independent verifier script SHA-256: `80bfddba658958623d13b2defec7c76ae8e4ca31521e5a39501ac33a1643a7d8`

All derived artifacts are under the isolated staging root
`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`.
