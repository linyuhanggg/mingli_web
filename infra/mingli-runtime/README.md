# Mingli V5.1 Linux Runtime Gate

This directory contains the reproducible Gate for the complete, unmodified
Mingli V5.1 portable release. It is not a three-Provider runtime. The image
must contain the exact 217-file signed projection, all 13 Providers, 55/55
reference packs, and all 1328 evidence-index records. Product exposure of
`bazi`, `fortune`, and `liuyao` is a separate policy recorded in the report.

## Build context

Never build from the installed Skill directory directly. It includes
local-only fulltexts and may contain other host files. Generate a new context
outside this repository:

```bash
python infra/mingli-runtime/build_context.py \
  --source-root /read-only/path/to/mingli-master \
  --destination /tmp/mingli-v51-linux-context
```

The projector verifies the source manifest first, copies only the 217 named
files with their signed modes, copies the manifest, rejects cache/symlink/path
escape artifacts, and verifies the completed projection again. It refuses to
replace an existing destination.

The production image is the default `final` target and contains no Git client.
The authoritative 1584-test suite includes repository privacy, archive, release
deployment, and version tests which invoke `git(1)`. Build the derived `audit`
target only for the Gate. It inherits the production runtime trees, adds Git,
and is never the deployable image.

```bash
docker build --target final -t mingli-v51:production /tmp/mingli-v51-linux-context
docker build --target audit -t mingli-v51:audit /tmp/mingli-v51-linux-context
```

Both external stages pin the same Python 3.14.6 slim-bookworm Linux amd64
manifest directly in the Dockerfile; no build argument can override it. Node
26.3.0, the manylinux x86_64 PyYAML wheel, the sxtwl source archive and rebuilt
CPython 3.14 wheel, astronomy-engine, cnlunar, and vendored iztro are bound to
the frozen hashes in `dependency-provenance.json` and the generated SBOM.

## Audit evidence

`audit_runtime.py` is the single in-image report generator. It requires:

- a clean, read-only checkout of source commit `494ce0...` at `/audit-source`;
- a blank writable output mount at `/audit-output`;
- a CycloneDX SBOM generated for the production image;
- sanitized backup/restore evidence produced with the production image;
- the production OCI config digest and the derived audit image ID.

It re-runs runtime inventory verification, the live 13-Provider matrix twice,
machine characterization twice, the exact 126-target/93-module/1584-test
release suite, fixed P0 trajectories, and malformed/tamper/timeout/concurrency/
token-replay probes. It writes command argv, exit code, stdout/stderr bytes and
hashes. `verify_release.py` then independently rehashes every referenced file
before `release-5.1.json` is written.

The Gate intentionally remains RED while `release-5.1.json`, `sbom.cdx.json`,
or referenced audit evidence is absent. Do not hand-create those files.

## Persistent state and restore constraints

The production state base is `/var/lib/mingli`, owned by UID/GID `10001:10001`
with mode `0700`. Backup must be taken from a quiesced single Runtime replica.
The drill uses one source volume and two separately created, proven-empty
destination volumes:

1. capture a Prepared snapshot, restore it into the first blank volume, issue a
   tokened follow-up, and complete that follow-up;
2. complete the source Prepared token, capture the Accepted snapshot, restore
   it into the second blank volume, and replay the byte-identical Complete;
3. compare token fingerprints, command digests, and public-copy byte digests.

Raw state tokens never enter committed logs. Runtime results are sanitized to
SHA-256 token fingerprints. Snapshot archives used during the drill are sealed
with a one-time pad; only ciphertext is retained and the pad is destroyed after
the restore succeeds. The verifier rehashes the retained snapshot ciphertext,
sanitized transcripts, and command logs and checks their exact relationships.
