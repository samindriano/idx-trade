# Stockbit Stream R2 Retention V1

Status: `LONG_TERM_POLICY_READY_REMOTE_APPLY_PENDING`

## Decision

The previous policy deleted:

- `stockbit-stream-v2/raw/` after 180 days;
- `stockbit-stream-v2/normalized/` after 180 days.

That bounded forward-audit retention is not suitable for the intended
prospective Stockbit research archive. The new policy retains all four
research prefixes indefinitely:

- `stockbit-stream-v2/raw/`;
- `stockbit-stream-v2/normalized/`;
- `stockbit-stream-v2/manifests/`;
- `stockbit-stream-v2/universe_inputs/`.

No replacement delete rule is generated. The two retired project-owned rule
IDs are explicitly pinned in the config and may be removed only when their
complete old 180-day definitions match exactly.

## Implementation and safety

The capture path, 08:47 / 12:07 / 16:47 schedule, top-200 universe policy,
historical artifacts, models, counters, and outcomes are unchanged.

The lifecycle utility is removal-only for the two exact project-owned rules:

- `stockbit-v2-raw-delete-180d`;
- `stockbit-v2-normalized-delete-180d`.

Before a PUT it GETs the current lifecycle configuration, preserves every
unrelated rule verbatim, and fails closed on missing/duplicate rule IDs,
changed fields on a retired rule, or an unowned object-delete rule targeting a
Stockbit research prefix. After PUT it GET-verifies the complete merged rule
set. It never lists, reads, deletes, or overwrites an R2 object.

The existing unrelated `Default Multipart Abort Rule` must remain unchanged.
The project-owned GitHub secret is used only by the manual lifecycle workflow;
secret values are never printed or committed.

## Activation

Remote activation is intentionally pending until this branch is merged and
the new removal-only workflow is dispatched once. The activation result must
record the workflow run, merged lifecycle payload SHA-256, exact remaining
rules, and proof that both retired IDs are absent.

## Validation

The focused retention suite covers indefinite policy generation, protected
prefixes, dry-run network freedom, missing credentials, exact retired-rule
removal, unrelated-rule preservation, ownership conflicts, duplicate IDs, and
post-apply verification. Full repository validation remains subject to the
known unrelated storage revision-conflict test.

## Cost and future optimization

Storage-tier migration is deliberately deferred. If growth later becomes
material, a separate reviewed task may move old raw objects to a cheaper tier;
automatic deletion is not an acceptable substitute for the research archive.
