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
  `astronomy_engine-2.1.19-py3-none-any.whl`.
- Upstream: <https://github.com/cosinekitty/astronomy/tree/v2.1.19>
- License: MIT.
- Distributed license: `vendor/astronomy-engine-2.1.19/LICENSE`.
- Copyright notice carried by the wheel: Copyright (c) 2019-2022 Don Cross.
- Obligation: retain the copyright notice, MIT permission notice, and
  disclaimer in copies or substantial portions. No source offer is required.

The local license body contains the full MIT permission and warranty-disclaimer
text and the 2019-2022 Don Cross copyright notice carried by the wheel. The
`v2.1.19` repository root uses a 2019-2023 copyright year; both texts state MIT.
This notice records the distributed artifact's exact notice and does not hide
the text variance.

### cnlunar 0.2.4

- Use: selected Xieji almanac tables behind the Runtime Provider.
- Distribution: unmodified `cnlunar-0.2.4-py3-none-any.whl`.
- Upstream: <https://github.com/OPN48/cnlunar/tree/0.2.4>
- License: MIT.
- Distributed license: `vendor/cnlunar-0.2.4/LICENSE`.
- Copyright notice: Copyright (c) 2025 OPN48.
- Obligation: retain the copyright notice, MIT permission notice, and
  disclaimer in copies or substantial portions. No source offer is required.

The local license body and the wheel license both contain the full MIT
permission and warranty-disclaimer text with the 2025 OPN48 copyright notice.

### iztro 2.5.8

- Use: Ziwei chart engine behind the Runtime Provider.
- Distribution: unmodified `package/dist/iztro.min.js` from the npm artifact
  `iztro-2.5.8.tgz`.
- Upstream: <https://github.com/SylarLong/iztro/tree/2.5.8>
- Vendored file: `vendor/iztro-2.5.8/iztro.min.js`, sourced from the named
  package member without modification.
- License: MIT.
- Distributed license: `vendor/iztro-2.5.8/LICENSE`.
- Copyright notice: Copyright (c) 2023 All Contributors.
- Obligation: retain the copyright notice, MIT permission notice, and
  disclaimer in copies or substantial portions. No source offer is required.

The local license body contains the full MIT permission and warranty-disclaimer
text with the 2023 All Contributors copyright notice. Direct content review
also confirms that the vendored JavaScript and license match the named npm
package members.

### look-fate/liuren-ts-lib transmission table

- Use: audit-only Da Liu Ren 60 x 12 transmission witness; it does not select
  or override Runtime facts.
- Upstream: <https://github.com/look-fate/liuren-ts-lib/tree/8e9a7b53245c8ae19fa12773087e1f90b3376d5e>
- Distribution: unmodified `src/sanchuan.json` from commit
  `8e9a7b53245c8ae19fa12773087e1f90b3376d5e`.
- Vendored file: `scripts/data/liuren-720-transmissions.json`.
- License: Apache-2.0.
- Distributed license: `scripts/data/LICENSE.Apache-2.0.txt`.
- Attribution record: `scripts/data/LIUREN-720-NOTICE.md`.
- Obligation: distribute the Apache-2.0 license; mark modified files if any;
  preserve applicable attribution notices. The reviewed upstream tree has no
  `NOTICE` file, and the vendored table is unmodified, so there is no upstream
  NOTICE payload or modification notice to add. No source offer is required.

The local license contains the complete Apache License 2.0 text. The local
attribution record states the upstream project, source member, exact commit,
audit-only use, and unmodified status.

## Current distribution blockers

These components are named by the current Runtime lock but are not admitted by
this notice. A release containing them remains on HOLD.

### PyYAML 6.0.3 — HOLD

The three exact-version wheels each contain
`pyyaml-6.0.3.dist-info/licenses/LICENSE`; direct review shows the MIT
permission and warranty-disclaimer text. The repository has no local copy of
that license, so the MING-66 local-license traceability gate is not closed.
Vendor the complete reviewed license under an approved path, add it to the
release closure, and retain its copyright and MIT notice before changing this
result to ALLOW.

### sxtwl 2.0.7 — HOLD / KEEP-WRAP

The exact `sxtwl-2.0.7.tar.gz` PyPI sdist declares only the generic label
`BSD`, contains no LICENSE/COPYING/NOTICE file, and has no upstream `2.0.7` tag
that binds it to a complete BSD-3-Clause license text. The current upstream
repository carries a BSD-3-Clause text, but a current-branch document cannot
substitute for release-bound evidence. Keep the existing engine architecture;
do not replace it merely because this legal evidence is incomplete. Before the
next distribution, bind the sdist to an exact upstream commit or
maintainer-authenticated source, vendor the corresponding complete license,
retain the BSD copyright/conditions/disclaimer, and add it to the release
closure.

### zhconv 1.4.3 — HOLD

The exact `zhconv-1.4.3.tar.gz` sdist declares GPLv2+. Direct review of its
`LICENSE` member shows the MIT code notice, while `LICENSE.data` carries the
MediaWiki-derived GPLv2+-related data terms. The repository has neither local
license file, a corresponding-source/source-offer procedure, nor a recorded
product compatibility decision for this copyleft payload. Resolve those
obligations or replace the dependency through a separately reviewed task before
distribution.

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
