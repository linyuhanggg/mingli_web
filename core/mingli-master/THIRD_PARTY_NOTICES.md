# Third-Party Notices

Audit date: 2026-08-29
Audit issue: MING-66 atomic OpenCC Runtime closure
Audited candidate source: PR #52 base
`66371c9494aa3141a903a5f8b3e3cabd13536346` plus the six-path Runtime
closure change described by this notice.

This notice covers the application-owned Mingli Runtime surface selected by
`requirements-runtime.lock` and `release/runtime-closure-v1.json`. It is an
engineering compliance record, not legal advice or a release approval.

The distribution-notice status is **CLEAR** for the current Runtime lock.
`release/runtime-closure-v1.json` selects this notice. The complete PyYAML and
sxtwl license texts are reproduced below; the other named artifacts retain
their complete license and attribution files through their selected vendored
files or installed wheel records.

## Admitted current Runtime components

### PyYAML 6.0.3

- Use: YAML support for Runtime manifests and contracts.
- Distribution: unmodified exact-version wheels selected by
  `requirements-runtime.lock`.
- Upstream:
  <https://github.com/yaml/pyyaml/tree/49790e73684bebad1df05ef8d828fa12f685bffb>.
- License: MIT.
- Copyright notices: Copyright (c) 2017-2021 Ingy döt Net; Copyright (c)
  2006-2016 Kirill Simonov.
- Obligation: retain the copyright notices, MIT permission notice, and
  disclaimer in copies or substantial portions. No source offer is required.

The text below is the complete license carried by the reviewed 6.0.3 wheels
and the named upstream commit. It is reproduced in this release-selected
notice:

```text
Copyright (c) 2017-2021 Ingy döt Net
Copyright (c) 2006-2016 Kirill Simonov

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### sxtwl 2.0.7 — KEEP/WRAP

- Use: solar terms, sexagenary calendar, and lunar conversion behind the
  Runtime Provider.
- Distribution: compiled locally without source patches from the exact PyPI
  source archive `sxtwl-2.0.7.tar.gz`.
- Official release: <https://pypi.org/project/sxtwl/2.0.7/>.
- Version-bound upstream commit:
  <https://github.com/yuangu/sxtwl_cpp/tree/98b731a66bfdb1b98de2209b01fc6609351e6a4d>.
- License: BSD-3-Clause.
- Copyright notice: Copyright (c) 2017-2022, 元谷.
- Obligation: source copies retain the copyright, conditions, and disclaimer;
  binary distribution materials reproduce them; neither the copyright holder
  nor contributors may be used for endorsement. No source offer is required.

All 17 authored/package source members in the exact PyPI source archive
directly byte-match the named official upstream commit. Generated package
metadata was excluded from that comparison. The complete license from the
same commit is reproduced in this release-selected notice:

```text
BSD 3-Clause License

Copyright (c) 2017-2022, 元谷
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### OpenCC 1.4.2

- Use: the `t2s` foundation for the product-owned simplified-text canonical.
- Distribution: unmodified binary wheels selected by
  `requirements-runtime.lock` for the three current Runtime targets:
  - `opencc-1.4.2-cp311-cp311-macosx_11_0_arm64.whl`, SHA-256
    `a3bb8d817b8d5500fda9a81e245825d176b087e4d31702dafc2ef83d6ef21b4a`;
  - `opencc-1.4.2-cp314-cp314-macosx_11_0_arm64.whl`, SHA-256
    `2dd2f8c3f7e633d252753c8f69298d5f446e02d62a3cf9c6a3c18683b5346c89`;
  - `opencc-1.4.2-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`,
    SHA-256
    `d054897f2e597d663410b9dc20b9e79d9410a893b9578ef3eaf3f6eef5fbcb52`.
- Official release: <https://pypi.org/project/OpenCC/1.4.2/>.
- Upstream:
  <https://github.com/BYVoid/OpenCC/tree/025f371dc76b598d77384fbdab90c937471844d8>.
- License: Apache-2.0.
- Obligation: retain the Apache-2.0 license and applicable attribution
  materials; mark modified files if any. No source offer is required.

All three wheels identify `OpenCC` version 1.4.2 and carry byte-identical
`opencc-1.4.2.dist-info/licenses/LICENSE` and
`opencc-1.4.2.dist-info/licenses/AUTHORS` members. Their LICENSE SHA-256 is
`b534e465949558eec2597b04f5092b5e161236a68dfbfd04d547592ac3964308` and
their AUTHORS SHA-256 is
`c9c94437ca9b62a1eb2a5c15b08f833964dc7489855fbc87d37168150dd7912a`;
both match the official `ver.1.4.2` tag's dereferenced commit above. AUTHORS
names Carbo Kuo as author and Peng Huang, Kefu Chai, LI Daobing, Asias,
Peng Wu, Xiaojun Ma, 佛振, and Frank Lin as contributors. Neither the reviewed
tag nor any of the three wheels contains a `NOTICE` file, so there is no
upstream NOTICE payload to reproduce. The wheels are unmodified.

### Astronomy Engine 2.1.19

- Use: ephemeris calculations behind the Runtime Provider.
- Distribution: unmodified
  `astronomy_engine-2.1.19-py3-none-any.whl`.
- Upstream: <https://github.com/cosinekitty/astronomy/tree/v2.1.19>.
- License: MIT.
- Distributed license: `vendor/astronomy-engine-2.1.19/LICENSE`.
- Copyright notice carried by the wheel: Copyright (c) 2019-2022 Don Cross.
- Obligation: retain the copyright notice, MIT permission notice, and
  disclaimer in copies or substantial portions. No source offer is required.

The local license body contains the full MIT permission and
warranty-disclaimer text and the 2019-2022 Don Cross copyright notice carried
by the wheel. The `v2.1.19` repository root uses a 2019-2023 copyright year;
both texts state MIT. This notice records the distributed artifact's exact
notice and does not hide the text variance.

### cnlunar 0.2.4

- Use: selected Xieji almanac tables behind the Runtime Provider.
- Distribution: unmodified `cnlunar-0.2.4-py3-none-any.whl`.
- Upstream: <https://github.com/OPN48/cnlunar/tree/0.2.4>.
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
- Upstream: <https://github.com/SylarLong/iztro/tree/2.5.8>.
- Vendored file: `vendor/iztro-2.5.8/iztro.min.js`, sourced from the named
  package member without modification.
- License: MIT.
- Distributed license: `vendor/iztro-2.5.8/LICENSE`.
- Copyright notice: Copyright (c) 2023 All Contributors.
- Obligation: retain the copyright notice, MIT permission notice, and
  disclaimer in copies or substantial portions. No source offer is required.

The local license body contains the full MIT permission and
warranty-disclaimer text with the 2023 All Contributors copyright notice.
Direct content review also confirms that the vendored JavaScript and license
match the named npm package members.

### look-fate/liuren-ts-lib transmission table

- Use: audit-only Da Liu Ren 60 x 12 transmission witness; it does not select
  or override Runtime facts.
- Upstream:
  <https://github.com/look-fate/liuren-ts-lib/tree/8e9a7b53245c8ae19fa12773087e1f90b3376d5e>.
- Distribution: unmodified `src/sanchuan.json` from commit
  `8e9a7b53245c8ae19fa12773087e1f90b3376d5e`.
- Vendored file: `scripts/data/liuren-720-transmissions.json`.
- License: Apache-2.0.
- Distributed license: `scripts/data/LICENSE.Apache-2.0.txt`.
- Attribution record: `scripts/data/LIUREN-720-NOTICE.md`.
- Obligation: distribute the Apache-2.0 license; mark modified files if any;
  preserve applicable attribution notices. No source offer is required.

The local license contains the complete Apache License 2.0 text. The reviewed
upstream tree has no `NOTICE` file, and the vendored table is unmodified, so
there is no upstream NOTICE payload or modification notice to add. The local
attribution record states the project, source member, exact commit, audit-only
use, and unmodified status.

## Scope boundaries

- `vendor/lunar-python-1.4.8` is a repository-only engineering comparator and
  is absent from both the Runtime lock and release closure, so it is not a
  distributed Runtime component and is not included above.
- Proposed candidates such as `lunar-javascript` are not dependencies and
  must not be added to this notice before their own lock, license, coverage,
  and golden-difference gates pass.
- Build-only packages removed before Runtime handoff, host language runtimes,
  and base-image operating-system packages belong to their build/container
  SBOM and distribution notices. The retired `infra/mingli-runtime` image path
  is not treated as the current application dependency authority here.
