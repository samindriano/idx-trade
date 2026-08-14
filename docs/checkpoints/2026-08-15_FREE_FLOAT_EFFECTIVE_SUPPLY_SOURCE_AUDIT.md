# Free Float / Effective Supply V1 — Bounded Source Audit

Date: 2026-08-15 Asia/Jakarta
Branch: `data/idx-free-float-effective-supply-v1`
Prepared parent: `36a874da865b9d7f4e03b14f284b047e77bd8cc2`
Final documentation HEAD: `5c0ba33`

## Scope and verdict

This checkpoint records a bounded live-source audit only. It does not derive
`true_free_float_pct`, `effective_free_float_pct`, a supply-tightness score,
Foreign Flow features, model inputs, or outcomes.

Final verdict: `SOURCE_REMEDIATION_REQUIRED`.

The bounded evidence is useful for later ownership-concentration work, but it
does not yet establish a canonical historical free-float/effective-supply
source. Missing official attachment bytes and one independent mirror
reconciliation conflict are preserved as blockers rather than repaired.

## Tests

- Focused:
  `python -m pytest tests/test_idx_ownership_provider.py tests/test_ksei_ownership_provider.py -q`
  — `10 passed`.
- Full:
  `python -m pytest -q` — `49 passed, 1 failed, 0 warnings`.
- `git diff --check` — pass.

The single full-suite failure is pre-existing and outside this lane:
`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`.
The test expects one conflict, while the current storage implementation
reports two independent conflicts (`raw_close` and
`vendor_adj_close`). No storage change was made on this branch.

## A. Official IDX Company Profile Detail

The existing provider/parser was used with a `curl_cffi` Chrome-impersonated
session after the ordinary `requests` transport received HTTP 403 at the IDX
home/session bootstrap. The successful endpoint was:

`GET https://www.idx.co.id/primary/ListedCompany/GetCompanyProfilesDetail`

with `KodeEmiten=<ticker>` and `language=id-id`.

Adversarial sample from the canonical security master:

| Ticker | Role | Raw bytes | Raw SHA-256 | Parsed holder rows |
|---|---|---:|---|---:|
| DCII | concentrated/current | 6,077 | `75ece0f06378996d96f08d6c34b061d2e49dfa8b68cb6217bd45f4f6ae8ce820` | 7 |
| BBCA | liquid large-cap control | 27,321 | `45f83601da1ea4162fe70909ff647a331941e85d7bd62c77fd21454d11e17557` | 20 |
| BAIK | current newer/illiquid control | 4,100 | `6c18444c33953850cfcffa73c4e56610b5721b53b25b4fb4aee6924b7f62d107` | 7 |
| WBSA | newer listing, validated current master | 4,595 | `5bd19d86216bd20f38379317688ebbf0d38dcba8fb842f048b0b48fd4b2f7e7e` | 10 |
| RLCO | newer listing, validated current master | 3,825 | `3eb29909094123b23829b7a3c0aed178bd5b0583759866bc524fd0c18c2a040a` | 6 |

All five payloads had the same top-level object/list schema. `PemegangSaham`
contained exactly:

`Jumlah`, `Kategori`, `Nama`, `Pengendali`, `Persentase`.

The complete bounded payload inventory found no explicit reported free-float,
public-shares, public-ownership, or shares-outstanding field. The only
similarly named profile value, `Profiles[0].EfekEmiten_Saham`, is a boolean
indicating that the issuer is a stock security. Named holders, controller
flags, treasury shares, and `Masyarakat Warkat`/`Masyarakat Non Warkat` rows
were retained as observed ownership facts; no complement calculation was
performed.

The successful profile manifest is outside Git:

`D:\Documents\Project\idx-trade-free-float-effective-supply-20260815-v1\idx_company_profile_manifest_final.json`

SHA-256:
`3dc3a504c203cef3ba5c07822af81683eaa5cb32a59e6282838eb07f42775ef5`.

## B. Official KSEI BalanceposEfek

The official holding-composition archive page was acquired and inspected:

`https://web.ksei.co.id/archive_download/holding_composition`

The visible archive range was monthly from `2026-01-30` through
`2026-07-31`. Three authorized snapshots were downloaded:

| Snapshot | Rows / unique codes | ZIP SHA-256 | Member SHA-256 |
|---|---:|---|---|
| 2026-02-27 | 3,680 / 3,680 | `8313d6e0719b3e1efd7d3189307fdc7f088c7ad5716a2aabcc92ae692b57587c` | `f954b8bc7bbfb8b843e6c93bfc62b45ab96e032346aece920b85328253a6c5da` |
| 2026-05-29 | 3,712 / 3,712 | `c487ac486bf1f22302a8eb942c6a27ccd4ac000d56b89fecb89651c406eaa992` | `3cebeba23641f0f62b3a1c4b0239cb6a884e819502a037bb8400cfad94e1d8ba` |
| 2026-07-31 | 3,802 / 3,802 | `16b4c8629e76b34d764c0513fd802201bfc421a2d9bf6059128903e80d89fa15` | `502bfe2476d98686b25ea14a2278cd5c7d2105f6276766daa1be059abbebc30a` |

Each ZIP contained one UTF-8-with-BOM, pipe-delimited text member. The
embedded `Date` matched the requested snapshot. The schema has local and
foreign investor-category balances, including two distinct columns both
labelled `Total` (local total and foreign total). Rows are aggregate
security/instrument composition records, not named-holder records. The
bounded sample had no duplicate security codes. Equity rows were 1,002,
1,002, and 1,007 respectively; the remaining rows were non-equity
instruments.

This source is therefore useful as a distinct aggregate local/foreign
holding-composition family, but it is not promoted as statutory free float,
effective free float, or named-holder concentration.

The KSEI capture manifest is outside Git:

`D:\Documents\Project\idx-trade-free-float-effective-supply-20260815-v1\ksei_balanceposefek_manifest.json`

SHA-256:
`c7c54173b3c82c2aef08f2d33b9b116a555bda67b9f8e4a969ac3f9400411bfd`.

## C. Official monthly >=1% named-holder publication

An official KSEI/IDX press release dated 2026-03-03 confirms that ownership
information above 1% is to be provided by KSEI and published on the IDX
website monthly. The preserved PDF is:

`D:\Documents\Project\idx-trade-free-float-effective-supply-20260815-v1\ksei_press_1pct.pdf`

SHA-256:
`6cff6a57dbe5ec4c214b1d7b81dd8718819d0ebcb1fcf05bd13bd1da5317b994`.

The bounded official IDX `ListedCompany/GetAnnouncement` probes for launch,
May, and latest windows returned non-JSON HTTP 503 responses. Six attempts are
preserved under:

`D:\Documents\Project\idx-trade-free-float-effective-supply-20260815-v1\idx_gt1_announcement_search`

The search manifest SHA-256 is
`5e57c3c04ba0670ac7b52819951620cc854374914b747e4e82733d11704ec132`.

Because the official attachment bytes and their `FullSavePath` linkage were
not recovered in this bounded run, official named-holder historical depth
remains unresolved. The current Company Profile endpoint is not a historical
series and is not backdated.

The public `nichsedge/idx-bei` mirror was audited only as reference/schema
evidence:

- embedded date: `27-Feb-2026`;
- rows: 7,257;
- columns include `INVESTOR_TYPE`;
- raw SHA-256:
  `cec36c69fc84d04c10d275d0a14227a3d51d95afefc3d792c9c68c89edf47c68`;
- parser correctly failed closed on one `MAYA` row because
  `HOLDINGS_SCRIPLESS + HOLDINGS_SCRIP` did not equal
  `TOTAL_HOLDING_SHARES`.

The mirror filename was not used as an as-of date, and the mirror was not
promoted as canonical.

## External evidence manifest

All live raw files and normalized sample artifacts remain outside Git under:

`D:\Documents\Project\idx-trade-free-float-effective-supply-20260815-v1`

Consolidated manifest:

`D:\Documents\Project\idx-trade-free-float-effective-supply-20260815-v1\AUDIT_MANIFEST.json`

SHA-256:
`344b59cd84da8adc8866cb3e47f942a6ea92c1b32a6fb763d74b2a54647fed94`.

## Decision

`SOURCE_REMEDIATION_REQUIRED`.

The next useful step is recovery and byte/hash verification of the official
IDX monthly >=1% attachment and its announcement linkage, not free-float
calculation. No ownership concentration contract is frozen by this
checkpoint.
