# Stockbit Stream R2 Retention V1

Status: `STOCKBIT_STREAM_LONG_TERM_RETENTION_ACTIVE`

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

Remote activation completed after the policy change was merged to `main`:

- workflow run: `32626013468`
- workflow URL: `https://github.com/samindriano/idx-trade/actions/runs/32626013468`
- workflow checkout: `300ebf15f2e7cc53a0147cb3bb247fb9a87980e3`
- result: `APPLIED_AND_VERIFIED`
- final merged lifecycle payload SHA-256:
  `1ec643ae14dc9dfcd6b76afb410d1c6caea3caa9668717c77a05f3f0e9653d80`

The exact project-owned rules `stockbit-v2-raw-delete-180d` and
`stockbit-v2-normalized-delete-180d` are absent after verification. There is
no remaining object-delete lifecycle rule for `raw/` or `normalized/`.
The unrelated `Default Multipart Abort Rule` remains preserved verbatim; it
does not delete completed Stockbit research objects.

No R2 object was listed, read, deleted, or overwritten by the workflow. The
change only replaced the bucket lifecycle configuration, so existing archive
objects remain available and future automatic expiry is disabled.

## Validation

The focused retention suite covers indefinite policy generation, protected
prefixes, dry-run network freedom, missing credentials, exact retired-rule
removal, unrelated-rule preservation, ownership conflicts, duplicate IDs, and
post-apply verification. The focused suite passed; full repository validation
retains the known unrelated storage revision-conflict failure.

## Cost and future optimization

Storage-tier migration is deliberately deferred. If growth later becomes
material, a separate reviewed task may move old raw objects to a cheaper tier;
automatic deletion is not an acceptable substitute for the research archive.
