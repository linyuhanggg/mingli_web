# Third-Party Notices

Audit date: 2026-08-28
Audit issue: MING-66
Audited source: `origin/main@fdfbee2ead72145e1c67daad6eba7f63cf4b60e6`

This notice covers the application-owned Mingli Runtime surface selected by
`requirements-runtime.lock` and `release/runtime-closure-v1.json`. It is an
engineering compliance record, not legal advice.

Release status is **HOLD**. The admitted notices below are complete for their
named artifacts, but the current dependency set also contains the unresolved
items listed under "Current distribution blockers". This file is not a release
approval, and `release/runtime-closure-v1.json` does not yet include it.

## Admitted current Runtime components

### Astronomy Engine 2.1.19

- Use: ephemeris calculations behind the Runtime Provider.
- Distribution: unmodified
  `astronomy_engine-2.1.19-py3-none-any.whl`, SHA-256
  `232ba7dd2bbf42225c48be6721b676e8c6c079dbd4588d2781dfa68adcb6f67f`.
- Upstream: <https://github.com/cosinekitty/astronomy/tree/v2.1.19>
- License: MIT.
- Distributed license: `vendor/astronomy-engine-2.1.19/LICENSE`, SHA-256
  `b4d9dd0fd80fce3879c4cd9e3754364f74fc5ec046f33276475ba3876785c8b7`.
- Copyright notice carried by the wheel: Copyright (c) 2019-2022 Don Cross.
- Obligation: retain the copyright notice, MIT permission notice, and
  disclaimer in copies or substantial portions. No source offer is required.

The exact wheel carries the same license bytes as the local file. The
`v2.1.19` repository root uses a 2019-2023 copyright year, while the published
wheel and PyPI release page use 2019-2022; both state MIT. This notice records
the distributed artifact's exact notice and does not hide the byte variance.

### cnlunar 0.2.4

- Use: selected Xieji almanac tables behind the Runtime Provider.
- Distribution: unmodified `cnlunar-0.2.4-py3-none-any.whl`, SHA-256
  `19689288604e86a3ef48dba23d39d6a7efbd5efabcb3923d4d656319762af4ea`.
- Upstream: <https://github.com/OPN48/cnlunar/tree/0.2.4>
- License: MIT.
- Distributed license: `vendor/cnlunar-0.2.4/LICENSE`, SHA-256
  `8bc77e1f9ab5c48cfc9e532b5eb30ff02c67cdc14af27b88b9c1ae815f1364bc`.
- Copyright notice: Copyright (c) 2025 OPN48.
- Obligation: retain the copyright notice, MIT permission notice, and
  disclaimer in copies or substantial portions. No source offer is required.

The local license is byte-identical to the license in the hash-locked wheel.

### iztro 2.5.8

- Use: Ziwei chart engine behind the Runtime Provider.
- Distribution: unmodified `package/dist/iztro.min.js` from the npm artifact
  `iztro-2.5.8.tgz`.
- Upstream: <https://github.com/SylarLong/iztro/tree/2.5.8>
- npm artifact SHA-256:
  `8293c6a587de521b0713e45826745ba4b7482fc507bd2da43fc820cadf06deca`.
- Vendored file: `vendor/iztro-2.5.8/iztro.min.js`, SHA-256
  `4b8eca323e5d4291471567c62255a2166471c55c77ebe8f0d2d38240e69d12b1`.
- License: MIT.
- Distributed license: `vendor/iztro-2.5.8/LICENSE`, SHA-256
  `e6c7b6e313cbda3135b41bccc66c98be132cb8319d0d465903d17e669e748b36`.
- Copyright notice: Copyright (c) 2023 All Contributors.
- Obligation: retain the copyright notice, MIT permission notice, and
  disclaimer in copies or substantial portions. No source offer is required.

Both the vendored JavaScript and license are byte-identical to the named npm
artifact members.

### look-fate/liuren-ts-lib transmission table

- Use: audit-only Da Liu Ren 60 x 12 transmission witness; it does not select
  or override Runtime facts.
- Upstream: <https://github.com/look-fate/liuren-ts-lib/tree/8e9a7b53245c8ae19fa12773087e1f90b3376d5e>
- Distribution: unmodified `src/sanchuan.json` from commit
  `8e9a7b53245c8ae19fa12773087e1f90b3376d5e`.
- Vendored file: `scripts/data/liuren-720-transmissions.json`, SHA-256
  `f4e77cce9d72c000aae228d1d07ed1ca9361baf3fbbad9f41f5fbe4ca346483b`.
- License: Apache-2.0.
- Distributed license: `scripts/data/LICENSE.Apache-2.0.txt`, SHA-256
  `26049b4e4af10b0c5ad392100980605ce14ef532d22197ab621fe605156adf75`.
- Attribution record: `scripts/data/LIUREN-720-NOTICE.md`, SHA-256
  `2199bf8ae17dd13919efce112183c4001f23222b5e1e79e1101185533212d327`.
- Obligation: distribute the Apache-2.0 license; mark modified files if any;
  preserve applicable attribution notices. The reviewed upstream tree has no
  `NOTICE` file, and the vendored table is byte-identical, so there is no
  upstream NOTICE payload or modification notice to add. No source offer is
  required.

## Current distribution blockers

These components are named by the current Runtime lock but are not admitted by
this notice. A release containing them remains on HOLD.

### PyYAML 6.0.3 — HOLD

The three hash-locked wheels each contain
`pyyaml-6.0.3.dist-info/licenses/LICENSE` with SHA-256
`8d3928f9dc4490fd635707cb88eb26bd764102a7282954307d3e5167a577e8a4`
and declare MIT. The repository has no local copy of that license, so the
MING-66 local-license traceability gate is not closed. Vendor the exact license
under an approved path, add it to the release closure, and retain its copyright
and MIT notice before changing this result to ALLOW.

### sxtwl 2.0.7 — HOLD / KEEP-WRAP

The hash-locked PyPI sdist
`38b24472389f7f6f3521c2c99e4b5e86c0184c7d6eb02e5409c239d21f0a6512`
declares only the generic label `BSD`, contains no LICENSE/COPYING/NOTICE file,
and has no upstream `2.0.7` tag that binds it to exact BSD-3-Clause license
bytes. The current upstream repository is BSD-3-Clause, but current-branch
license bytes cannot substitute for release-bound evidence. Keep the existing
engine architecture; do not replace it merely because this legal evidence is
incomplete. Before the next distribution, bind the sdist to an exact upstream
commit or maintainer-authenticated source, vendor the corresponding license,
retain the BSD copyright/conditions/disclaimer, and add it to the release
closure.

### zhconv 1.4.3 — HOLD

The hash-locked sdist
`ad42d9057ca0605f8e41d62b67ca797f879f58193ee6840562c51459b2698c45`
declares GPLv2+. It contains an MIT code license (`LICENSE`, SHA-256
`03321beb8e1d0b1ac0ef01174b9c207d7c3f43d401ba49c2ea803b518c341607`)
and MediaWiki-derived data terms (`LICENSE.data`, SHA-256
`ee56fcd554ea3522420571898a8c63ff6193d78111c07b63599f36e338376237`).
The repository has neither local license file, a corresponding-source/source-
offer procedure, nor a recorded product compatibility decision for this
copyleft payload. Resolve those obligations or replace the dependency through
a separately reviewed task before distribution.

## Scope boundaries

- `vendor/lunar-python-1.4.8` is a repository-only engineering comparator and
  is absent from both the Runtime lock and release closure, so it is not a
  distributed Runtime component and is not included above.
- Proposed candidates such as `lunar-javascript` are not dependencies and must
  not be added to this notice before their own lock, local-license, coverage,
  and golden-difference gates pass.
- Build-only packages removed before Runtime handoff, host language runtimes,
  and base-image operating-system packages belong to their build/container
  SBOM and distribution notices. The retired `infra/mingli-runtime` image path
  is not treated as the current application dependency authority here.
