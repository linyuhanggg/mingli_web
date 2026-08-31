# MING-76 v53 frozen Runtime reproduction evidence

## Result

The frozen tuple requested by MING-76 is not reproducible from source commit
`9c615a70f08d5609af09ead100d2b5d90e558fe8`. No Runtime identity constant was
changed: the Backend gate remains fail-closed pending a new Core release.

Requested tuple:

- source commit: `9c615a70f08d5609af09ead100d2b5d90e558fe8`
- release manifest SHA-256: `d1b49d5842feb5d4143330d1d250af625f42644a930f7d9d9c344c5d0363b090`
- worker SHA-256: `3512987322ef18bb91c4798e77d7ef982d2e7e31ae9e2ddd321d78aa90261b50`
- signed release file count: `218`

## Controlled source reconstruction

An isolated detached worktree was created at the exact source commit. The
fresh-main release builder was then used to calculate the committed Runtime
closure and manifest from that worktree.

Observed result:

```json
{
  "source_commit": "9c615a70f08d5609af09ead100d2b5d90e558fe8",
  "release_file_count": 222,
  "manifest_sha256": "3df0c1dff97fcc64263a80f69f3539c2ceb9f117ceee8441a1b398e3b7c2ec59",
  "runtime_worker_in_manifest": false
}
```

The exact source commit does not contain
`core/mingli-master/scripts/reading_engine/runtime_worker.py`. The worker with
the requested byte digest first exists later in history; the exact bytes are
available at
`a3a29546e8b46b608314118bdd2d5faf80955149:core/mingli-master/scripts/reading_engine/runtime_worker.py`.
Therefore the requested source identity cannot produce the requested worker
identity.

The full controlled install command also failed closed before writing a
release because the old source tree lacks the audit registry required by the
fresh-main source verifier:

```text
release source verification failed: source audit registry could not be loaded: ModuleNotFoundError
```

Historical Backend assertions corroborate the mismatch: commit
`1649dfbde6f0f35854e291ab3e1cf1c14b105e6e` paired the `d1b49d58...` listing
with 223 signed files and 224 physical files, not 218. Fresh main still carries
that v53-specific 223-file expectation alongside the unrelated 218-file v51
default.

## Installed-release and startup evidence

The existing verifier accepts the separately installed legacy release:

```text
source_commit = 663543e65ae037843b03dca1dec9486293affc9d
manifest_sha256 = c451de5e4390c2a264a49aed972057081c61cb74ada160df308ac7a2af993c4b
files = 220
status = ok
```

With the smoke environment explicitly aligned to the live v53 describe and
capability digests, Backend correctly rejects that legacy release:

```text
SMOKE FAIL-CLOSED (runtime): Runtime release manifest digest mismatch
SMOKE_EXIT_CODE=3
```

The smoke wrapper previously stopped even earlier because it required the
signed shell launcher to have an executable bit. Backend deliberately launches
that 0644 file through `/bin/sh`; MING-76 removes only that stale wrapper check
so the smoke reaches the real Runtime identity gate.

## Minimum Core re-sign dependency

Core must provide one clean, committed source tree that:

1. contains the admitted worker bytes in the source commit;
2. declares the intended release closure explicitly (218 files if that count
   remains the project decision, otherwise the project manager must revise the
   frozen count to the controlled generator output);
3. passes the current release source verifier; and
4. is installed through `scripts/release_deploy.py --apply`, producing measured
   source commit, manifest SHA-256, worker SHA-256, signed file count, describe
   digest, and capability-shape digest.

After that release exists, Backend can atomically align `config.py`, the
Runtime adapter, and `verify_frozen_runtime_release.py`, then rerun the real
startup smoke. Pruning four or five files, preserving the old source commit
while overlaying a later worker, or accepting an unsigned worker would invent
a release identity and is intentionally not done here.
