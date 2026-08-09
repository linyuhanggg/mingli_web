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

`run_lima_gate.py` is the mountless host controller. It streams the projected
build context over `limactl shell`, creates uniquely named Docker volumes, and
streams a self-contained clean Git checkout plus the 54 ignored fulltexts into
the VM. It never depends on `/Users` or `/Volumes` being mounted in Lima. Every
temporary volume is initialized as root, then owned by `10001:10001`; all real
runtime and audit commands execute as that non-root identity.

`audit_runtime.py` uses two explicit evidence phases:

1. `--production-audit` runs directly in the Git-free production image. It
   recomputes the SBOM and runtime inventory, runs the live 13-Provider matrix
   twice, characterization twice, P0 trajectories, and the malformed/tamper/
   launcher-timeout/concurrency/token-replay probes. Every command record is
   bound to the production OCI config digest.
2. `--finalize-audit` runs in the derived audit image. It verifies and copies
   the production evidence bundle, binds the clean source commit to all 217
   signed files, runs only the Git-dependent 126-target/93-module/1584-test
   suite, and produces the final report.

Both phases independently hash `/opt/mingli-master`,
`/opt/mingli-runtime/venv`, and `/opt/node`; the Gate requires byte-for-byte
identical machine output before admitting the derived audit result. The audit
phase requires:

- a clean, read-only checkout of source commit `494ce0...` at `/audit-source`;
- a blank writable output mount at `/audit-output`;
- a CycloneDX SBOM generated for the production image;
- sanitized backup/restore evidence produced with the production image;
- the production OCI config digest and the derived audit image ID.

Both phases write exact command argv, executing image ID, exit code,
stdout/stderr bytes, and hashes. `verify_release.py` independently rehashes
every referenced file before `release-5.1.json` is written.

The Gate intentionally remains RED while `release-5.1.json`, `sbom.cdx.json`,
or referenced audit evidence is absent. Do not hand-create those files.

## Persistent state and restore constraints

The production state base is `/var/lib/mingli`, owned by UID/GID `10001:10001`
with mode `0700`. Backup must be taken from a quiesced single Runtime replica.
The drill uses one source volume and two separately created, proven-empty
destination volumes:

1. capture a Prepared snapshot and restore it into the first blank volume;
2. replay the same Prepare plus the restored token and prove the Prepared
   bytes, brief, and token are identical;
3. Complete that restored Prepared, then use its Accepted token with a new
   query to create and Complete a real version-2 follow-up; the child token
   record must bind version 2, its parent fingerprint, and the original
   `prior_answer` byte digest;
4. independently Complete the source Prepared, capture the Accepted snapshot,
   restore it into the second blank volume, and replay the original
   byte-identical Complete;
5. compare only the original/restored/replayed Accepted public-copy and command
   digests. The child follow-up copy is deliberately excluded from this
   byte-identity assertion.

Raw state tokens never enter committed logs. Runtime results are sanitized to
SHA-256 token fingerprints. Snapshot archives used during the drill are sealed
with a one-time pad; only ciphertext is retained and the pad is destroyed after
the restore succeeds. The verifier rehashes the retained snapshot ciphertext,
sanitized transcripts, and command logs and checks their exact relationships.
