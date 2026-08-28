# MING-66 License and NOTICE Admission Audit

Audit date: 2026-08-28
Base: `origin/main@fdfbee2ead72145e1c67daad6eba7f63cf4b60e6`
Base tree: `e36435068294f9501cc06eb882fd3ddbffa01542`
Machine-readable twin: `license-notice-audit.json`

This is an engineering compliance audit, not legal advice. It does not change
Provider selection, Canonical Facts authority, dependency locks, or Runtime
code.

## Result

**Overall gate: HOLD.** Five reviewed items are ALLOW in their stated scope,
four are HOLD, and none are REJECT. The current Runtime dependency surface has
three release blockers: PyYAML lacks a repository-local license copy, sxtwl's
exact sdist has no license file or version-bound upstream ref, and zhconv has
unclosed GPLv2+/MediaWiki-data obligations. In addition,
`THIRD_PARTY_NOTICES.md` is not yet selected by the current release closure.

This HOLD does not reverse the product decision to KEEP/WRAP sxtwl,
astronomy-engine, and vendored iztro. It blocks treating the present
distribution evidence as complete.

| Component | Current role | Actual Runtime distribution | License | Decision | NOTICE |
| --- | --- | ---: | --- | --- | --- |
| PyYAML 6.0.3 | YAML support | yes | MIT | HOLD | blocker entry only |
| sxtwl 2.0.7 | Bazi/calendar engine | yes | package says BSD; upstream current tree BSD-3-Clause | HOLD / KEEP-WRAP | blocker entry only |
| astronomy-engine 2.1.19 | ephemeris engine | yes | MIT | ALLOW / KEEP-WRAP | included |
| cnlunar 0.2.4 | Xieji almanac implementation | yes | MIT | ALLOW | included |
| iztro 2.5.8 | Ziwei engine | yes | MIT | ALLOW / KEEP-WRAP | included |
| look-fate/liuren-ts-lib transmission table 8e9a7b53245c8ae19fa12773087e1f90b3376d5e | audit witness | yes | Apache-2.0 | ALLOW | included |
| lunar-python 1.4.8 | repository-only comparator | no | MIT | ALLOW, comparator scope only | excluded |
| zhconv 1.4.3 | text conversion | yes | GPLv2+ package; MIT code + GPLv2+ data terms | HOLD | blocker entry only |
| lunar-javascript 1.7.7 | independently discovered candidate | no | MIT | HOLD, pre-admission | excluded |

Counts and every field below are mirrored in the JSON file.

## Scope reconciliation

The current application-owned Runtime surface was derived from:

- `core/mingli-master/requirements-runtime.lock`, SHA-256
  `d3e7afd811a151d8443e6aacd8fc48ea263c1f21cb5de6d34520c6b9b2c5ee35`;
- `core/mingli-master/release/runtime-closure-v1.json`, SHA-256
  `6a4917f2e3e867d2d5801b75905d181acc377158533816c481cbac3836fd4230`;
- vendored provenance and license files under `core/mingli-master/vendor/**`;
- the released Da Liu Ren table, Apache license, and local notice under
  `core/mingli-master/scripts/data/**`.

The lock names PyYAML, sxtwl, astronomy-engine, cnlunar, and zhconv. The
release closure additionally ships vendored iztro and the Da Liu Ren audit
table. `lunar-python` is absent from both and its provenance explicitly limits
it to frozen comparison evidence. Build-only packages are removed before
Runtime handoff. Host/base-image components are governed by their own SBOM;
`infra/mingli-runtime/README.md` marks the former Linux image flow historical.

## Component evidence

### PyYAML 6.0.3 — HOLD

- Purpose: parse structured Runtime manifests and contracts.
- Official release: <https://pypi.org/project/PyYAML/6.0.3/>
- Upstream ref: <https://github.com/yaml/pyyaml/tree/6.0.3>, commit
  `49790e73684bebad1df05ef8d828fa12f685bffb`.
- Locked artifacts:
  - CPython 3.11 macOS arm64 wheel:
    `652cb6edd41e718550aad172851962662ff2681490a8a711af6a4d288dd96824`;
  - CPython 3.14 macOS arm64 wheel:
    `34d5fcd24b8445fadc33f9cf348c1047101756fd760b4dacb5c3e99755703310`;
  - CPython 3.14 Linux x86_64 wheel:
    `c458b6d084f9b935061bc36216e8a69a7e293a2f1e68bf956dcd9e6cbcd143f5`.
- All three exact wheels contain
  `pyyaml-6.0.3.dist-info/licenses/LICENSE`, SHA-256
  `8d3928f9dc4490fd635707cb88eb26bd764102a7282954307d3e5167a577e8a4`.
- Distribution/modification: exact wheel, unmodified.
- Obligations: preserve the copyright, MIT permission notice, and disclaimer;
  no source offer.
- HOLD reason: there is no repository-local license path and the release
  closure does not select one. This fails the explicit local-license gate even
  though each wheel carries the correct bytes.

### sxtwl 2.0.7 — HOLD / KEEP-WRAP

- Purpose: solar terms, sexagenary calendar, and lunar conversion.
- Official release: <https://pypi.org/project/sxtwl/2.0.7/>
- Artifact: `sxtwl-2.0.7.tar.gz`, SHA-256
  `38b24472389f7f6f3521c2c99e4b5e86c0184c7d6eb02e5409c239d21f0a6512`.
- Distribution/modification: the exact sdist is compiled locally without a
  source patch; the historical Linux gate records a reproducible custom wheel
  but is not the current authority.
- Package evidence: `PKG-INFO` says `License: BSD`; the sdist contains no
  LICENSE, COPYING, or NOTICE member and no `License-File` metadata.
- Upstream: <https://github.com/yuangu/sxtwl_cpp>. The reviewed current master
  commit `7598b0601a76cfdaa9266257b1b5690720c1e2ce` carries BSD-3-Clause license
  bytes with SHA-256
  `f90cebec40217aac9f464602fbbff397b7cd6bf580c34c0cc377638886202523`.
- Conflict/gap: upstream has no `2.0.7` tag, so the current license bytes are
  not a version-bound full-text source for the locked sdist.
- Obligations if admitted: preserve the copyright, three BSD conditions, and
  disclaimer in source and binary distribution materials; do not imply
  endorsement; no source offer.
- Unblock: bind the sdist to an exact authenticated upstream source, vendor
  the corresponding license under an approved path, and add it to the release
  closure. Architectural status remains KEEP/WRAP.

### astronomy-engine 2.1.19 — ALLOW / KEEP-WRAP

- Purpose: versioned ephemeris calculations.
- Official release: <https://pypi.org/project/astronomy-engine/2.1.19/>
- Upstream ref: <https://github.com/cosinekitty/astronomy/tree/v2.1.19>,
  annotated tag object `03084ee684bdcc490273fe85f9df4f1c8fb66199`, commit
  `61dc07020aaa6885d2c7f688a4d82beaf6edb9ef`.
- Installed wheel SHA-256:
  `232ba7dd2bbf42225c48be6721b676e8c6c079dbd4588d2781dfa68adcb6f67f`;
  official sdist SHA-256:
  `95b797b87b659adc0602a6a205143ce5a10451664e80650bb7cd8ba3c8f1f02b`.
- Distribution/modification: exact wheel, unmodified.
- License: MIT. Local path
  `core/mingli-master/vendor/astronomy-engine-2.1.19/LICENSE`, SHA-256
  `b4d9dd0fd80fce3879c4cd9e3754364f74fc5ec046f33276475ba3876785c8b7`.
  It is byte-identical to the wheel member. The tag-root license differs only
  in copyright year (2019-2023 versus the distributed wheel's 2019-2022); SPDX
  and terms are both MIT, and the NOTICE records the variance.
- Obligations: preserve copyright/license/disclaimer; no source offer or
  separate upstream NOTICE.

### cnlunar 0.2.4 — ALLOW

- Purpose: selected Xieji almanac implementation.
- Official release: <https://pypi.org/project/cnlunar/0.2.4/>
- Upstream ref: <https://github.com/OPN48/cnlunar/tree/0.2.4>, annotated tag
  object `b3e1cb1e78a62431405d90a685671c7dd4a3f990`, commit
  `71e448a3ad4fa17bb731a57637ee0728e6f53d37`.
- Wheel SHA-256:
  `19689288604e86a3ef48dba23d39d6a7efbd5efabcb3923d4d656319762af4ea`;
  sdist SHA-256:
  `a270238a657744dbc477cb48207b4dffe7c03100b327c81ae4622055d593463f`.
- Distribution/modification: exact wheel, unmodified; runtime verifies the
  seven reviewed module hashes from provenance.
- License: MIT. Local path `core/mingli-master/vendor/cnlunar-0.2.4/LICENSE`,
  SHA-256
  `8bc77e1f9ab5c48cfc9e532b5eb30ff02c67cdc14af27b88b9c1ae815f1364bc`;
  byte-identical to both the wheel license and tagged upstream license.
- Obligations: preserve copyright/license/disclaimer; no source offer or
  separate upstream NOTICE.

### iztro 2.5.8 — ALLOW / KEEP-WRAP

- Purpose: Ziwei chart engine.
- Official package metadata: <https://registry.npmjs.org/iztro/2.5.8>
- Upstream ref: <https://github.com/SylarLong/iztro/tree/2.5.8>, commit
  `9d39f1743bf31c2b3c635c9b9556215d9c90ee2c`.
- npm tarball SHA-256:
  `8293c6a587de521b0713e45826745ba4b7482fc507bd2da43fc820cadf06deca`.
- Distribution/modification: `vendor/iztro-2.5.8/iztro.min.js` is
  byte-identical to `package/dist/iztro.min.js`; SHA-256
  `4b8eca323e5d4291471567c62255a2166471c55c77ebe8f0d2d38240e69d12b1`.
- License: MIT. Local path `core/mingli-master/vendor/iztro-2.5.8/LICENSE`,
  SHA-256
  `e6c7b6e313cbda3135b41bccc66c98be132cb8319d0d465903d17e669e748b36`;
  byte-identical to the npm member and tagged upstream file.
- Obligations: preserve copyright/license/disclaimer; no source offer or
  separate upstream NOTICE.

### look-fate/liuren-ts-lib transmission table 8e9a7b53245c8ae19fa12773087e1f90b3376d5e — ALLOW

- Purpose: deterministic audit witness only.
- Upstream ref: <https://github.com/look-fate/liuren-ts-lib/tree/8e9a7b53245c8ae19fa12773087e1f90b3376d5e>.
- Distribution/modification: local
  `core/mingli-master/scripts/data/liuren-720-transmissions.json` is
  byte-identical to upstream `src/sanchuan.json` at that commit; SHA-256
  `f4e77cce9d72c000aae228d1d07ed1ca9361baf3fbbad9f41f5fbe4ca346483b`.
- License: Apache-2.0. Local path
  `core/mingli-master/scripts/data/LICENSE.Apache-2.0.txt`, SHA-256
  `26049b4e4af10b0c5ad392100980605ce14ef532d22197ab621fe605156adf75`.
- Local attribution: `core/mingli-master/scripts/data/LIUREN-720-NOTICE.md`,
  SHA-256
  `2199bf8ae17dd13919efce112183c4001f23222b5e1e79e1101185533212d327`.
- Obligations: ship Apache-2.0; mark modifications; preserve applicable
  upstream NOTICE text. The reviewed upstream tree has no NOTICE and the file
  is unmodified, so no source offer or modification notice is required.

### lunar-python 1.4.8 — ALLOW, comparator scope only

- Purpose: frozen independent engineering comparator; not a Runtime dependency
  or classical authority.
- Official release: <https://pypi.org/project/lunar-python/1.4.8/>
- Upstream ref: <https://github.com/6tail/lunar-python/tree/v1.4.8>, commit
  `000c8a3d74eed098d6256a28fdd51b869324c559`.
- Sdist SHA-256:
  `3aa11cc73c25e70ddf0ba5bdac7398c03acc9491a3aa512a91c9642973b669d6`.
- Distribution/modification: implementation is not shipped in the Runtime;
  the repository stores license/provenance and an implementation digest for
  comparison. The local license adds one terminal LF and is otherwise
  identical to the sdist/tag license.
- License: MIT. Local path
  `core/mingli-master/vendor/lunar-python-1.4.8/LICENSE`, SHA-256
  `097ec7989106eb9a27b6eff71dbaf1cd6bb04a9b35b6c94b54fff0829a041a8c`;
  exact upstream/sdist license hash before the terminal LF is
  `a9d04f47f0615c0ce48bdbe2ff58d5c174279d9f20f044ef29249632302a4ab3`.
- Obligations: retain copyright/license/disclaimer if code is later shipped;
  no source offer. This ALLOW does not approve promotion into the Runtime.

### zhconv 1.4.3 — HOLD

- Purpose: simplified/traditional text conversion.
- Official release: <https://pypi.org/project/zhconv/1.4.3/>
- Upstream ref: <https://github.com/gumblex/zhconv/tree/v1.4.3>, annotated tag
  object `bbc9d85702c2e0be0f3acd10a161b9eaafa38b5a`, commit
  `0f066eb3df92f73714eedf36f287839e993fa922`.
- Sdist SHA-256:
  `ad42d9057ca0605f8e41d62b67ca797f879f58193ee6840562c51459b2698c45`.
- Distribution/modification: installed from the exact sdist without source
  patches; its MediaWiki-derived JSON data is part of the package.
- License evidence: package metadata says GPLv2+. `LICENSE` contains the MIT
  code notice, SHA-256
  `03321beb8e1d0b1ac0ef01174b9c207d7c3f43d401ba49c2ea803b518c341607`;
  `LICENSE.data` carries MediaWiki GPLv2+-related terms, SHA-256
  `ee56fcd554ea3522420571898a8c63ff6193d78111c07b63599f36e338376237`.
- Obligations: preserve both notices; provide GPLv2+ license and complete
  corresponding source/source-offer compliance as applicable; preserve
  derivative-data attribution and compatible licensing. Exact obligations
  need project legal policy confirmation.
- HOLD reason: no repository-local license files, no source-offer procedure,
  and no recorded compatibility decision for distributing this payload with
  the product.

### lunar-javascript 1.7.7 — HOLD, proposed candidate

- Discovery basis: independent official npm/GitHub review; not found in the
  Runtime lock or release closure.
- Proposed use: possible calendar/Bazi mechanical-engine candidate only; it
  must remain behind a Provider/Adapter if ever admitted.
- Official package metadata:
  <https://registry.npmjs.org/lunar-javascript/1.7.7>
- Upstream ref: <https://github.com/6tail/lunar-javascript/tree/v1.7.7>, commit
  `4c45a59f79b856125516f31aefa8295035c16afd`.
- npm tarball SHA-256:
  `d1359ab9ca4913d1db3978a42ddfc290eb8ea9de54ce043f5b1f718ff71eea36`.
- License: MIT; package/upstream LICENSE SHA-256
  `d9210caf1844dcf410095cea464b79800aad30dbd49df092076b9f0ddc015404`.
- Distribution/modification: not distributed and not modified.
- HOLD reason: no approved dependency lock, repository-local license,
  Provider coverage matrix, or legal golden-difference evidence. It must not
  appear in the current NOTICE and is not approved as a replacement.

## Admission gate for every future candidate

Before a candidate enters a dependency lock, all of the following must pass:

1. Exact package version, immutable artifact hash, official registry/repository
   URL, and exact upstream tag/commit are recorded.
2. SPDX expression and complete license/NOTICE bytes are present under an
   approved repository-local path with SHA-256; metadata-only license labels
   are insufficient.
3. Distribution form and modifications are explicit. Binary/source notice,
   attribution, modification-marking, patent, copyleft, corresponding-source,
   and source-offer obligations are recorded and operationally owned.
4. The dependency is present in the machine audit and NOTICE iff it is actually
   distributed. Candidate and comparator entries cannot masquerade as Runtime
   dependencies.
5. The release closure includes `THIRD_PARTY_NOTICES.md` and every required
   local license/NOTICE file. A test rejects an actual dependency missing from
   the audit or any ALLOW entry missing its exact local license/hash.
6. License admission does not approve replacement. Provider coverage, policy
   normalization, Canonical Facts isolation, and lawful golden-difference
   evidence must independently pass.

## Required follow-up before release

- Add approved repository-local license files for PyYAML, sxtwl, and zhconv.
- Resolve sxtwl's exact source-to-license binding without replacing the
  KEEP/WRAP engine by default.
- Obtain a project compatibility decision and source-compliance procedure for
  zhconv, or replace it through a separately reviewed dependency task.
- Add this notice and required licenses to the Runtime release closure, then
  enforce Markdown/JSON/dependency parity in a focused gate.

REJECT items: none.
