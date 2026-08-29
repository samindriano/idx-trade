# V4-X1 Path-A Population Gate Activation / Provenance V1

Date: 2026-08-29 Asia/Jakarta  
Activation branch base: `origin/main@bee0a4f95eff5d319467abfc339f9845a8996c8f`  
Approved implementation commit: `6b6a41114a910287b413a099a36d59c5e057a8f2`  

## Change boundary

This narrow activation changes exactly one production implementation pin in
`.github/workflows/e2e-paper-cloud-orchestration.yml`:

```text
old: E2E_CLOUD_IMPLEMENTATION_REF=cb7573422097aef2f34ad41d53ccd95f6231a67a
new: E2E_CLOUD_IMPLEMENTATION_REF=6b6a41114a910287b413a099a36d59c5e057a8f2
```

The workflow contract remains unchanged: schedules, run-name and token
semantics, PREOPEN_CA/PREOPEN/POST_EOD concurrency groups, the `/tmp` provider
checkout and provider commit, R2 configuration and prefixes, Official Open
pin, `trigger_slot` validation, the V3 runner invocation, and the secrets/env
contract are preserved byte-for-byte.

No additional entrypoint or orchestration layer is introduced. Production
already runs `run_e2e_paper_cloud_v3.py`, which delegates POST_EOD and PREOPEN
behavior through V2 and then V1.

## Scientific and runtime boundary

The approved implementation is activated under the
`PRESERVE_FROZEN_SCIENCE_DECOUPLE_RUNTIME` boundary. The runtime population
gate and evidence bootstrap may protect admission, but they must not alter the
frozen V4-X1 scorer population or frozen scientific semantics.

The activation preserves:

- Security Master continuity for legally listed baseline identity;
- the Path-A population gate before canonical scoring;
- the tradability runtime bootstrap after Security Master refresh and before
  canonical EOD;
- exact integrity of all 17 frozen implementation pins;
- no propagation or rewrite of current `listed_to` into the frozen scorer;
- fail-closed behavior for ambiguous, malformed, missing, or conflicting
  runtime evidence.

## Operational safety and acceptance

No manual rerun or backfill of a prior session is authorized by this change.
No provider, outcome, counter, PaperState, R2, Cloudflare, Windows Task, or
secret/token action is part of activation preparation.

The 2026-08-27 prospective POST_EOD remains failed and unsalvaged. A future
genuine scheduled POST_EOD on the repinned production workflow is still
required for live acceptance proof; this activation branch is not itself
production proof.

`coordination/TEAM_STATUS.md` is MAIN-owned and is intentionally unchanged on
this activation branch. The final main-owned coordination update belongs to
the reviewed merge/integration step.
