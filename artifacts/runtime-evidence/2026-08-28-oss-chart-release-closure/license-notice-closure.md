# MING-66 Runtime license/NOTICE release closure

Review date: 2026-08-28

Source parent: `origin/main@fc88198956f9d8a911e81a43a733b1b6e2dd78e0`

## Result

**Overall Runtime distribution gate: HOLD.** Three of the four assigned
closure items are CLEAR. The only remaining blocker is the project-level
compatibility decision for importing the GPLv2+-declared `zhconv==1.4.3`
package in process.

| Item | Result | Direct evidence |
| --- | --- | --- |
| PyYAML 6.0.3 local license and closure | CLEAR | Complete reviewed MIT text is stored at `vendor/pyyaml-6.0.3/LICENSE`, selected by the release closure, and named by the notice. |
| sxtwl 2.0.7 version-bound license | CLEAR | Every one of the 17 authored/package source members in the exact PyPI sdist directly byte-matches official upstream commit `98b731a66bfdb1b98de2209b01fc6609351e6a4d`; that commit carries the BSD-3-Clause text now stored locally and selected by the closure. |
| zhconv 1.4.3 obligations | HOLD | Local MIT and MediaWiki/GPLv2+ texts plus source delivery are closed. No current project distribution-license decision establishes compatibility for the in-process GPLv2+ import. |
| `THIRD_PARTY_NOTICES.md` release selection | CLEAR | The live release closure selects the notice, all referenced licenses, and the zhconv source-compliance procedure. |

## sxtwl binding

PyPI identifies `sxtwl-2.0.7.tar.gz` as the 2.0.7 source distribution and
links the project to `yuangu/sxtwl_cpp`. The source archive was uploaded at
2024-09-05T16:04:41Z. Upstream commit
`98b731a66bfdb1b98de2209b01fc6609351e6a4d`, recorded minutes later, directly
matches all 17 authored/package members shipped in that archive:
`MANIFEST.in`, `README.md`, `setup.py`, `sxtwl.py`, `sxtwl_wrap.cxx`, and the
12 compiled/header members selected from `src/`. Generated `PKG-INFO`,
`egg-info`, and `setup.cfg` were not treated as authored source evidence.

The same official upstream commit carries the complete BSD-3-Clause license with
Copyright (c) 2017-2022, 元谷. This is the version-bound source/license evidence
that the earlier audit lacked. No license checksum was added.

## zhconv boundary

PyPI publishes only `zhconv-1.4.3.tar.gz` for 1.4.3. The current provisioner
therefore obtains the complete source form, including `LICENSE`,
`LICENSE.data`, Python sources, and `zhcdict.json`; the Runtime applies no
patch. `vendor/zhconv-1.4.3/SOURCE_COMPLIANCE.md` records that current delivery
path and the condition that any later built-tree redistribution must accompany
equivalent source access.

That closes local-license and source-availability evidence. It does not answer
the separate compatibility question created by importing a package whose
official metadata declares GPLv2+. No repository-wide distribution license or
accountable compatibility decision was found. The honest result is HOLD until
that decision is recorded or the dependency is replaced in a separate task.

## Scope

No Provider, Canonical Facts, dependency version, dependency lock, or business
code changed. No deployment or 18080 update occurred. No license hash,
checksum, or fingerprint was added.
