# Statutory Free-Float Snapshot Source Audit Result V1

Status: `PASS_STRUCTURAL_ONLY / SOURCE_REMEDIATION_REQUIRED`

This is a read-only audit of the local statutory free-float snapshot and its
embedded LBRE side surface. It does not call the provider, open targets or
outcomes, mutate source/canonical data, or create a feature, universe mask, or
candidate.

## Structural evidence

- The snapshot manifest contains 2,145 new artifacts. All declared files
  match their manifest bytes and SHA-256 values.
- All seven explicitly reused parent-source entries also match their recorded
  hashes.
- The unified normalized CSV contains 1,882 rows with valid required fields,
  dates, and nonnegative numeric values.
- The 2025-12-31 market-wide anchor reports 956 rows, of which 923 contain
  exact free-float shares; 33 reported rows lack explicit shares.
- The 2026-03-31 market-wide anchor reports 956 percentage-only rows and zero
  exact-share rows.
- The embedded 2026 LBRE side surface contains 1,050 exact parsed rows,
  1,015 exact rows at the 2026-06-30 target position, 957 admitted lineage
  rows, 93 excluded lineage rows, and 18 parse-unresolved announcements.
- The independent verifier, generic artifact hash contract, and
  outcome-blind target/privacy firewall all return `PASS`.

## Admission limits

- Two market-wide anchors do not establish continuous historical free-float
  history or a daily population panel.
- The 2025 anchor has 33 missing explicit-share rows; the 2026 anchor is
  percentage-only and cannot be treated as an exact-share transition.
- The embedded LBRE lineage excludes 93 rows across unresolved-no-original,
  multiple-original, and invalid-contract-chain reasons.
- No complete issuer/ISIN transition chain, corporate-action linkage,
  revision-completeness certificate, or public-availability/PIT contract is
  established.

## Decision

The snapshot is a useful market-anchor capability and a precise statement of
what is missing, but remains `PARTIAL / SOURCE_REMEDIATION_REQUIRED`. It must
not be used for daily universe masks, free-float features, corporate-action
repair, or protected evaluation until continuous coverage, lineage, identity,
and PIT/public-availability contracts are independently admitted.

## Artifact provenance

- Artifact manifest SHA-256: `7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e`
- Unified CSV SHA-256: `30dfeb43a1545330a0e54a8a8896a2fd26b8cfa66c5fece2ba6c9aa8cdf21aa8`
- Anchor summary SHA-256: `c580b43f6b507ddae2b20e76be4b148d12b14ced027f84deb54da0802694a1d6`
- LBRE census summary SHA-256: `288cdabca1d3fc1119756d75c437178975626e83547f32c4d270492dc45155ef`
- LBRE lineage SHA-256: `70f21ac0d6e599f755144a2ffbad5980155ae558c9843bfcab551608365da38a`
- LBRE parse audit SHA-256: `bbd08f2fd1d86b99cd5de5b0dbbd42122e44e688ef3735abd5bfa674fb1eeb56`
- Quarterly target audit SHA-256: `1022ac34ae30aa15642e5637a1f094b828cd8fc55f3d8b78c4ebb01e8ed892c1`
- Audit JSON SHA-256: `0fdd29f85395583e35820e178f8675d6e9b9bfb13db2032013ee1fbe0d5fdc4f`
- Independent verification JSON SHA-256: `9d1099b2b10ca9cc8c92acd293460ea09ac41a4d641dcd1350e3e5bf33aaea3e`
- Hash-contract JSON SHA-256: `32d671aff4cf0c8e833d18b0631cc07fccbda1691dd19b6d2c31af98d0e517dc`
- Privacy/target firewall JSON SHA-256: `81177f6991735f623b88ef5e36e242d9251261cf73a762477dcf0946d1952063`
- Builder SHA-256: `6093c404d233a8ee7d27129e6c7dec771d41910328544f6b5bd52f7794d4ebfa`
- Independent verifier SHA-256: `ba1c6c80c436da6c86d182f0d10582c48a423d8e39f479be9906e85b1f2df240`

No target, outcome, incumbent, provider, network, cloud, canonical, capture,
or production state was accessed or modified.
