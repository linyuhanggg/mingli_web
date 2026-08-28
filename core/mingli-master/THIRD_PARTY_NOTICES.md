# Third-Party Notices

Audit date: 2026-08-28
Audit issue: MING-66 and release-closure follow-up
Closure source parent: `origin/main@fc88198956f9d8a911e81a43a733b1b6e2dd78e0`

This notice covers the application-owned Mingli Runtime surface selected by
`requirements-runtime.lock` and `release/runtime-closure-v1.json`. It is an
engineering compliance record, not legal advice.

Release status is **HOLD**. PyYAML and sxtwl now have complete local,
release-selected license evidence. The remaining blocker is the project-level
distribution-license compatibility decision for the GPLv2+-declared zhconv
package. `release/runtime-closure-v1.json` selects this notice, every local
license named below, and the zhconv source-compliance procedure. This file is
an engineering record, not release approval or legal advice.

## Admitted current Runtime components

### PyYAML 6.0.3

- Use: YAML support for Runtime manifests and contracts.
- Distribution: unmodified exact-version wheels selected by
  `requirements-runtime.lock`.
- Upstream:
  <https://github.com/yaml/pyyaml/tree/49790e73684bebad1df05ef8d828fa12f685bffb>
- License: MIT.
- Distributed license: `vendor/pyyaml-6.0.3/LICENSE`.
- Copyright notices: Copyright (c) 2017-2021 Ingy döt Net; Copyright (c)
  2006-2016 Kirill Simonov.
- Obligation: retain the copyright notices, MIT permission notice, and
  disclaimer in copies or substantial portions. No source offer is required.

The local license is the complete text carried by the reviewed upstream commit
and by the exact-version wheel license members. It is selected by the Runtime
release closure.

### sxtwl 2.0.7 — KEEP/WRAP

- Use: solar terms, sexagenary calendar, and lunar conversion behind the
  Runtime Provider.
- Distribution: compiled locally without source patches from the exact PyPI
  source archive `sxtwl-2.0.7.tar.gz`.
- Official release: <https://pypi.org/project/sxtwl/2.0.7/>
- Version-bound upstream commit:
  <https://github.com/yuangu/sxtwl_cpp/tree/98b731a66bfdb1b98de2209b01fc6609351e6a4d>
- License: BSD-3-Clause.
- Distributed license: `vendor/sxtwl-2.0.7/LICENSE`.
- Copyright notice: Copyright (c) 2017-2022, 元谷.
- Obligation: source copies retain the copyright, conditions, and disclaimer;
  binary distribution materials reproduce them; neither the copyright holder
  nor contributors may be used for endorsement. No source offer is required.

All 17 authored/package source members in the exact PyPI source archive
directly byte-match the named official upstream commit. Generated package
metadata was not used for that comparison. The same commit carries the full
BSD-3-Clause text stored locally and selected by the release closure. This
closes the version-binding gap without changing the KEEP/WRAP architecture.

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

The current Runtime lock has one unresolved compatibility decision. A release
containing this dependency remains on HOLD.

### zhconv 1.4.3 — HOLD

The exact `zhconv-1.4.3.tar.gz` source distribution declares GPLv2+. Direct
review of its `LICENSE` member shows the MIT code notice, while `LICENSE.data`
carries the MediaWiki-derived GPLv2+-related data terms. Both complete texts
are stored under `vendor/zhconv-1.4.3/` and selected by the release closure.

PyPI publishes only that source archive for version 1.4.3, and the current
provisioner obtains it without source patches. The source archive contains the
licenses, Python sources, and `zhcdict.json` data; the current source-delivery
procedure is recorded in `vendor/zhconv-1.4.3/SOURCE_COMPLIANCE.md` and selected
by the release closure.

The remaining HOLD is narrower: no current project-wide distribution-license
decision establishes compatibility for importing this GPLv2+-declared package
in process. Engineering evidence cannot silently choose the product's license
terms. Record an accountable compatibility decision, or replace the dependency
through a separately reviewed task, before Runtime distribution.

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
