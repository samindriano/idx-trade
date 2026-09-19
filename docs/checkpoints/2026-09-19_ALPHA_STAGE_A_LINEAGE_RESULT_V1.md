# Alpha Stage-A Artifact Lineage Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Scope: read-only hash/manifest comparison within the isolated external staging
root

## Conclusion

The external staging root contains several historical Stage-A generations.
They are derived, outcome-blind artifacts—not additional raw data sources.
Two generations are byte-identical despite different manifest repository heads,
and the guarded generation is a distinct later artifact. Only the guarded
generation remains the active documented input for the current structural lane.

No artifact in this lineage audit is PIT admission, population completeness,
corporate-action authority, or predictive evidence.

## Hash and manifest census

| Generation | Feature bytes | Feature SHA-256 | Manifest SHA-256 | Manifest code hash | Manifest repo head | Disposition |
|---|---:|---|---|---|---|---|
| `stage-a/20260919T` | 22,876,940 | `074b1a84c73eb139348d2999416cc2904e0a20b3544c329ca780ff7e2b497169` | `c89588ccd7ab5b9e4159221709f49fd2470961f43d6ab61c9331bf57eb958dc9` | `3a5f018663a4a7848d19daec15a882523027ca4c1ad6cb719911c8c9a41dbc54` | not recorded | legacy historical lineage; do not use as current input |
| `stage-a-v2/20260919T-corrected-v2` | 12,007,088 | `cc65dc6bd5c7b030648f2edf85b8f6f0276d911712d9e0602feaaad200cc0116` | `cc65a7bce490ef6924b6bc6fb6a182a0001fc5ff4fd6c91009fbe92360db54ea` | `663d599f24c2b70ea284a042874ccff3b495d9ccef907049368646faaa4320f1` | `3b0ad3de308d7480125dcb28af548073ad3c0cb9` | superseded corrected-v2 lineage |
| `stage-a-v3/20260919T-corrected-v3` | 11,989,860 | `1fe49a16588f48d3baf8b26dd72281e4b3d19632168d32b8f6c383b93cdabc63` | `f374d6e6e0cfa401f9f8fd669b0c93a7b852d9c82ae558e23bd17ee3e8a97edc` | `4e7fdf28ecf3080f19ed647b7a604cd14c6045a65c39fbdecb3bd39f25413bd3` | `1ebced27e3b73fad6e342c61a6fd35c363c73a4e` | historical v3 lineage |
| `stage-a-final/20260919T-finalized` | 11,989,860 | `1fe49a16588f48d3baf8b26dd72281e4b3d19632168d32b8f6c383b93cdabc63` | `09e81f70ca1558ba6edb1c99756bbce4acf6cc9a49fb59676e4572ad28ea52b5` | `4e7fdf28ecf3080f19ed647b7a604cd14c6045a65c39fbdecb3bd39f25413bd3` | `71ec449432cc788bb45a89939ddb5eda8ea387ad` | byte-identical duplicate of v3; manifest-only distinction |
| `stage-a-final-guarded/20260919T-finalized-guarded` | 11,989,860 | `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4` | `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96` | `62a16137d039c0304e00fbf91de65ed5c70d50952faccf2aff1b0a587f49e59a` | `10939862bc134064a55cd492bc4926e0fa99f281` | **active guarded structural artifact** |

All manifest `stage` values that were present are `A_OUTCOME_BLIND`.
Source hashes for financial, official-session, panel, and tradability-anchor
inputs are retained in the manifests and do not by themselves establish
historical PIT or completeness.

## Findings and controls

1. `stage-a-v3` and `stage-a-final` have identical feature bytes and identical
   code/source lineage, but different manifest hashes and repository heads.
   They are not independent experiments.
2. `stage-a-final-guarded` has a different feature hash and code/repository
   lineage. It is the only generation referenced by the current guarded
   structural checkpoints.
3. The earliest `stage-a` manifest lacks a repository head, so its provenance
   is weaker than later generations.
4. No generation should be substituted silently. Any future structural replay
   must pin the exact feature hash, manifest hash, code hash, source hashes,
   and repository head when available.
5. This audit did not open target/outcome/provider/cloud/capture/scheduler or
   canonical production state.

## Scientific disposition

- The current C1/C2/C4 structural results continue to use the guarded feature
  hash `aaff882f...`.
- No candidate status changed; no new candidate ID was created.
- Duplicate/superseded lineage is now explicit in the data inventory and
  ledger.
- A reviewed immutable event log, population coverage manifest, and
  historical-as-of authority are still required before any protected
  evaluation.
