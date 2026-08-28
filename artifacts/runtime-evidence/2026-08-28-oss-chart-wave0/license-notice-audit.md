# MING-66 License and NOTICE Admission Audit

Audit date: 2026-08-28
Base: `origin/main@fdfbee2ead72145e1c67daad6eba7f63cf4b60e6`
Base tree: `e36435068294f9501cc06eb882fd3ddbffa01542`
Machine-readable twin: `license-notice-audit.json`

This is an engineering compliance audit, not legal advice. It does not change
Provider selection, Canonical Facts authority, dependency locks, or Runtime
code.

License admission in this report is based on exact version, official source,
distribution form and modification status, repository-local LICENSE path and
direct text review, plus attribution/NOTICE/source obligations. It does not add
an integrity-digest field or self-check. Existing Runtime Release signing and
integrity controls remain unchanged and are outside MING-66.

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

- `core/mingli-master/requirements-runtime.lock`;
- `core/mingli-master/release/runtime-closure-v1.json`;
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
- Exact-version artifacts: CPython 3.11 macOS arm64, CPython 3.14 macOS
  arm64, and CPython 3.14 Linux x86_64 wheels selected by the Runtime lock.
- All three wheels contain `pyyaml-6.0.3.dist-info/licenses/LICENSE`; direct
  review shows the MIT permission and warranty-disclaimer text.
- Distribution/modification: exact wheel, unmodified.
- Obligations: preserve the copyright, MIT permission notice, and disclaimer;
  no source offer.
- HOLD reason: there is no repository-local license path and the release
  closure does not select one. This fails the explicit local-license gate even
  though each wheel carries the correct bytes.

### sxtwl 2.0.7 — HOLD / KEEP-WRAP

- Purpose: solar terms, sexagenary calendar, and lunar conversion.
- Official release: <https://pypi.org/project/sxtwl/2.0.7/>
- Artifact: exact-version PyPI sdist `sxtwl-2.0.7.tar.gz`.
- Distribution/modification: the exact sdist is compiled locally without a
  source patch; the historical Linux gate records a reproducible custom wheel
  but is not the current authority.
- Package evidence: `PKG-INFO` says `License: BSD`; the sdist contains no
  LICENSE, COPYING, or NOTICE member and no `License-File` metadata.
- Upstream: <https://github.com/yuangu/sxtwl_cpp>. The reviewed current master
  commit `7598b0601a76cfdaa9266257b1b5690720c1e2ce` carries a complete
  BSD-3-Clause text with its copyright, three conditions, non-endorsement
  clause, and disclaimer.
- Conflict/gap: upstream has no `2.0.7` tag, so the current license text is not
  a version-bound source for the locked sdist.
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
- Artifacts: `astronomy_engine-2.1.19-py3-none-any.whl` and official
  `astronomy-engine-2.1.19.tar.gz` source provenance.
- Distribution/modification: exact wheel, unmodified.
- License: MIT. Local path
  `core/mingli-master/vendor/astronomy-engine-2.1.19/LICENSE`. Direct text
  review confirms the full MIT permission and disclaimer with Copyright (c)
  2019-2022 Don Cross, matching the wheel member. The tag-root license differs
  only in copyright year (2019-2023 versus the distributed wheel's 2019-2022);
  SPDX and terms are both MIT, and the NOTICE records the variance.
- Obligations: preserve copyright/license/disclaimer; no source offer or
  separate upstream NOTICE.

### cnlunar 0.2.4 — ALLOW

- Purpose: selected Xieji almanac implementation.
- Official release: <https://pypi.org/project/cnlunar/0.2.4/>
- Upstream ref: <https://github.com/OPN48/cnlunar/tree/0.2.4>, annotated tag
  object `b3e1cb1e78a62431405d90a685671c7dd4a3f990`, commit
  `71e448a3ad4fa17bb731a57637ee0728e6f53d37`.
- Artifacts: `cnlunar-0.2.4-py3-none-any.whl` and official
  `cnlunar-0.2.4.tar.gz` source provenance.
- Distribution/modification: exact wheel, unmodified.
- License: MIT. Local path `core/mingli-master/vendor/cnlunar-0.2.4/LICENSE`,
  whose body contains the full MIT permission and disclaimer with Copyright
  (c) 2025 OPN48; the wheel member and tagged upstream file carry the same
  text.
- Obligations: preserve copyright/license/disclaimer; no source offer or
  separate upstream NOTICE.

### iztro 2.5.8 — ALLOW / KEEP-WRAP

- Purpose: Ziwei chart engine.
- Official package metadata: <https://registry.npmjs.org/iztro/2.5.8>
- Upstream ref: <https://github.com/SylarLong/iztro/tree/2.5.8>, commit
  `9d39f1743bf31c2b3c635c9b9556215d9c90ee2c`.
- Distribution/modification: `vendor/iztro-2.5.8/iztro.min.js` is
  sourced from `package/dist/iztro.min.js` without modification.
- License: MIT. Local path `core/mingli-master/vendor/iztro-2.5.8/LICENSE`,
  whose body contains the full MIT permission and disclaimer with Copyright
  (c) 2023 All Contributors; the npm member and tagged upstream file carry the
  same text.
- Obligations: preserve copyright/license/disclaimer; no source offer or
  separate upstream NOTICE.

### look-fate/liuren-ts-lib transmission table 8e9a7b53245c8ae19fa12773087e1f90b3376d5e — ALLOW

- Purpose: deterministic audit witness only.
- Upstream ref: <https://github.com/look-fate/liuren-ts-lib/tree/8e9a7b53245c8ae19fa12773087e1f90b3376d5e>.
- Distribution/modification: local
  `core/mingli-master/scripts/data/liuren-720-transmissions.json` is
  sourced from upstream `src/sanchuan.json` at that commit without
  modification.
- License: Apache-2.0. Local path
  `core/mingli-master/scripts/data/LICENSE.Apache-2.0.txt`; direct review
  confirms the complete Apache License 2.0 text.
- Local attribution: `core/mingli-master/scripts/data/LIUREN-720-NOTICE.md`;
  its body records the upstream project, source member, exact commit,
  audit-only use, and unmodified status.
- Obligations: ship Apache-2.0; mark modifications; preserve applicable
  upstream NOTICE text. The reviewed upstream tree has no NOTICE and the file
  is unmodified, so no source offer or modification notice is required.

### lunar-python 1.4.8 — ALLOW, comparator scope only

- Purpose: frozen independent engineering comparator; not a Runtime dependency
  or classical authority.
- Official release: <https://pypi.org/project/lunar-python/1.4.8/>
- Upstream ref: <https://github.com/6tail/lunar-python/tree/v1.4.8>, commit
  `000c8a3d74eed098d6256a28fdd51b869324c559`.
- Artifact: exact-version PyPI sdist `lunar_python-1.4.8.tar.gz`.
- Distribution/modification: implementation is not shipped in the Runtime;
  the repository stores license/provenance and comparator evidence. The local
  license adds one terminal LF and otherwise carries the same text as the
  sdist/tag license.
- License: MIT. Local path
  `core/mingli-master/vendor/lunar-python-1.4.8/LICENSE`; direct text review
  confirms the full MIT permission and disclaimer with Copyright (c) 2020
  6tail.
- Obligations: retain copyright/license/disclaimer if code is later shipped;
  no source offer. This ALLOW does not approve promotion into the Runtime.

### zhconv 1.4.3 — HOLD

- Purpose: simplified/traditional text conversion.
- Official release: <https://pypi.org/project/zhconv/1.4.3/>
- Upstream ref: <https://github.com/gumblex/zhconv/tree/v1.4.3>, annotated tag
  object `bbc9d85702c2e0be0f3acd10a161b9eaafa38b5a`, commit
  `0f066eb3df92f73714eedf36f287839e993fa922`.
- Artifact: exact-version PyPI sdist `zhconv-1.4.3.tar.gz`.
- Distribution/modification: installed from the exact sdist without source
  patches; its MediaWiki-derived JSON data is part of the package.
- License evidence: package metadata says GPLv2+. Direct review of `LICENSE`
  shows the MIT code notice; `LICENSE.data` carries MediaWiki-derived
  GPLv2+-related data terms. Neither file has a repository-local path.
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
- Artifact: exact-version npm package `lunar-javascript-1.7.7.tgz`.
- License: MIT; direct review of the package/upstream LICENSE confirms the MIT
  permission and warranty-disclaimer text, but there is no approved
  repository-local path.
- Distribution/modification: not distributed and not modified.
- HOLD reason: no approved dependency lock, repository-local license,
  Provider coverage matrix, or legal golden-difference evidence. It must not
  appear in the current NOTICE and is not approved as a replacement.

## Admission gate for every future candidate

Before a candidate enters a dependency lock, all of the following must pass:

1. Exact package version, official registry/repository URL, and exact upstream
   tag/commit are recorded.
2. SPDX expression and complete license/NOTICE text are present under an
   approved repository-local path; direct review records the copyright,
   permission/conditions, disclaimer, and any separate NOTICE. Metadata-only
   license labels are insufficient.
3. Distribution form and modifications are explicit. Binary/source notice,
   attribution, modification-marking, patent, copyleft, corresponding-source,
   and source-offer obligations are recorded and operationally owned.
4. The dependency is present in the machine audit and NOTICE iff it is actually
   distributed. Candidate and comparator entries cannot masquerade as Runtime
   dependencies.
5. The release closure includes `THIRD_PARTY_NOTICES.md` and every required
   local license/NOTICE file. A test rejects an actual dependency missing from
   the audit or any ALLOW entry missing its exact local license path, reviewed
   text, and obligations.
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
