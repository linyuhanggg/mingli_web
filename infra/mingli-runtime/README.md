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

The production image is the default `final` target. It includes the narrowly
built, frozen Git 2.39.5 runtime required by the authoritative release tests;
the Gate never substitutes a mutable distribution Git package. The `audit`
stage adds no bytes. With the pinned containerd image store, Docker resolves
the loaded multi-platform image ID to the exact top-level production OCI index.
The controller gives that immutable index a
second audit tag and rejects the run before starting any container unless the
production, audit, and artifact index digests are identical. The child amd64
manifest and config digests remain separate identities in the OCI closure.

```bash
docker build --target final -t mingli-v51:production /tmp/mingli-v51-linux-context
docker tag mingli-v51:production mingli-v51:audit
```

Both external stages pin the same Python 3.14.6 slim-bookworm Linux amd64
manifest directly in the Dockerfile; no build argument can override it. Node
26.3.0, the manylinux x86_64 PyYAML wheel, the sxtwl source archive and rebuilt
CPython 3.14 wheel, astronomy-engine, cnlunar, vendored iztro, and Git are bound
to the frozen hashes in `dependency-provenance.json` and the generated SBOM.
Git is built twice from the official 2.39.5 source archive with fixed paths,
timestamps, compiler flags, SHA1DC collision detection, the built-in SHA-256
backend, and explicit relative-symlink installation. The two installation
trees must match before one is copied into production. Production then
recomputes the executable, build configuration, license, source archive,
224-entry tree, 144 safe in-tree symlinks, and complete tree digest. A fixed
Git fixture exercises version, init, config, add, commit, status, ls-files,
ls-tree, rev-parse, archive, exec-path, and template discovery.
Node's `libatomic1` dependency is fetched from the timestamped Debian Snapshot
`20250501T000000Z`, not from the mutable mirror pool. Provenance records both
the original Debian pool URL and the pinned snapshot fetch URL; Docker also
checks the exact amd64 `.deb` SHA-256 before installing it and the installed
`libatomic.so.1.2.0` SHA-256 afterward. If Debian Snapshot is unavailable, the
same admitted `.deb` must be served from a controlled read-only artifact
mirror under the same hash; silently falling back to an ordinary mirror is not
an admissible rebuild.

## Mac mini local profiles

The local entry point exposes two separate evidence domains. `native-full`
runs the complete signed 126-target/93-module/1584-test suite as the daily and
merge gate, with a hard 600-second and 10-slot ceiling. `linux-certify` never
uses that native result as Linux evidence. Its first admitted stage is only an
exact VZ+Rosetta identity tracer and therefore publishes
`linux-identity-tracer.json` with status `tracer-passed-not-certified`; it must
not create `release-5.1.json`.

The persisted native SLA envelope deliberately does not call its stored clock
value a total profile duration. `evidence_seal_elapsed_seconds` is measured at
the fixed `post-semantic-verification-pre-evidence-seal` boundary. The final
independent seal validation and atomic directory publication remain inside the
600-second fail-closed deadline, expressed by
`deadline_enforced_through_atomic_publication=true`, but are not folded back
into the self-referential sealed JSON. The live `local_gate.py native-full`
result measures again after validation and atomic publication and reports that
later value as `LocalFullResult.elapsed_seconds`. Aggregators must not present
the persisted evidence-seal value as the complete command wall clock.

`lima-vz-rosetta.yaml` fills to a mountless `vz/aarch64` guest with Rosetta
binfmt, pinned Docker 29.7.2, containerd 2.3.3, and rootlesskit 3.0.2. Validate
and freeze the effective bytes before starting the instance:

```bash
limactl template validate --fill infra/mingli-runtime/lima-vz-rosetta.yaml
limactl template copy --fill infra/mingli-runtime/lima-vz-rosetta.yaml \
  /tmp/mingli-linux-gate-vz-effective.yaml
```

Formal preparation also requires the host command `limactl --version` to emit
exactly `limactl version 2.2.0`; `minimumLimaVersion` in the YAML is not runtime
identity evidence. Build and export the immutable OCI artifact outside the timed
profile with the committed producer:

```bash
python infra/mingli-runtime/prepare_linux_inputs.py \
  --base-prepared-inputs /absolute/path/native-prepared-inputs.json \
  --base-prepared-inputs-sha256 <sha256> \
  --controller-root /absolute/path/mingli_web \
  --release-source /read-only/path/to/mingli-master \
  --effective-config /tmp/mingli-linux-gate-vz-effective.yaml \
  --effective-config-sha256 <sha256> \
  --instance mingli-linux-gate-vz \
  --output-directory /absolute/new/path/linux-prepared
```

The producer records the exact Lima 2.2.0 and Docker identities, controller
commit, persisted build-context bytes, unfiltered OCI archive, and fixed build
and export argv. It revalidates the base manifest, controller inputs, and
effective config after the build. The output directory initially contains only
a hidden pending manifest; independent certifiable loading happens there, and
`prepared-inputs.json` appears only as the final same-directory atomic rename.
Every failure before that admission point removes the entire output directory.
The identity tracer samples `limactl --version` both before and after all VM,
image, container, config, and OCI checks and rejects either endpoint drifting.

The tracer requires the full OCI index whose digest is the final artifact ID,
including its amd64 manifest and attestation manifest. The identity contract
keeps four distinct digests: the top-level index, the `linux/amd64` child
manifest, that manifest's config, and the attestation manifest. It also binds
the ordered compressed-layer digests and the config's ordered RootFS diff IDs.
A platform-filtered `docker save` can flatten the index and discard the
attestation; such an archive is rejected even if its tag and filesystem look
right. The controller must export and import the complete OCI layout. The
tracer re-hashes every blob, verifies the index-to-child-to-config chain and
attestation subject, decompresses every layer to prove its diff ID, then
requires Docker's descriptor/ID and RootFS to match that closure. The probe is
started by the immutable `repository@sha256:<index>` reference, never by the
mutable tag. The probe container uses fixed argv, the
label `io.fateradar.mingli.gate=linux-amd64-identity-tracer`, no network,
Rosetta AOT caching, a read-only root, non-root execution, and strict resource
limits. It verifies x86_64 platform/uname and ELF identity for runtime Python,
Node, Git, sxtwl, and PyYAML, plus real sxtwl execution and the required native
linkage. Only a later full `linux-certify` run through the existing audit and
release verifier may publish Linux release evidence.

The timed certification path consumes the same immutable PreparedInputs file
and never rebuilds the image inside its 600-second window. The OCI archive,
top-level index, child manifests, config, layers, effective Lima configuration,
clean source tree, and external research tree have already been hashed by that
file. After the tracer has loaded and admitted the image, the full controller
can bind it by immutable `repository@sha256:<index>` reference:

```bash
python infra/mingli-runtime/run_lima_gate.py \
  --prepared-inputs /absolute/path/prepared-inputs.json \
  --prepared-inputs-sha256 <sha256-of-prepared-inputs-json> \
  --output /absolute/empty-parent/linux-release
```

Prepared mode rejects mutable `--release-source` and
`--research-repository` arguments. It clones the bound clean source for Matrix
A, overlays every bound and Git-ignored research file into a second checkout,
aliases only the already-loaded exact OCI index, and revalidates both
PreparedInputs and the immutable image identity immediately before atomic
publication. The legacy cold-build form remains available for the slower QEMU
release fallback, but its image build is not part of the prepared local SLA.

## Audit evidence

`run_lima_gate.py` is the mountless host controller. It streams the projected
build context over `limactl shell`, creates uniquely named Docker volumes, and
streams two self-contained exact-commit checkouts into the VM. The first is the
clean matrix source at `/audit-source`. The second is the
fulltext research checkout at `/audit-research`, with all bound Git-ignored
research files added, including exactly 54 primary `fulltext.md` files. Keeping
those roots separate preserves the signed Provider Matrix generator fingerprint
while the complete regression still verifies all 55 reference packs. It never
depends on `/Users` or `/Volumes` being mounted in Lima. Every temporary volume
is initialized as root, then owned by `10001:10001`; all real runtime and audit
commands execute as that non-root identity.

Every container run records the same normalized argv that is actually sent to
Docker. Both lanes require `--platform=linux/amd64`; the pinned VZ lane also
requires `--device=lima-vm.io/rosetta=cached`, while the QEMU fallback forbids
that device. Missing, duplicated, or different platform/device options are
rejected before execution and by the independent release verifier.

The signed V5.1 launcher opens
`/opt/mingli-runtime/.venv.runtime.lock` with `O_RDWR|O_CREAT` on every
invocation. Consequently, containers that call the launcher or
`probe_runtime_identity` require Docker's writable, disposable container
overlay and must not use `--read-only`. They remain offline, run as fixed UID
and GID `10001:10001`, keep the `/opt` image contents root-owned, and use
`--rm`, so overlay changes are discarded when each command exits. Pure
state-root, token-record, source, and archive inspection commands remain
read-only. A production platform that enforces `readOnlyRootFilesystem` must
instead provide a safe writable single-file mount at the exact lock path;
without that mount V5.1 readiness fails closed before `describe`.

`audit_runtime.py` uses two explicit evidence phases:

1. `--production-audit` runs directly in the final deployable production image. It
   recomputes the SBOM and runtime inventory, runs the complete
   126-target/93-module/1584-test regression once, treats its real
   `CanonicalMatrixSnapshotTests` target as Matrix A, runs one independent
   standalone Matrix B, runs characterization twice, P0 trajectories, the
   fixed Git fixture, and the malformed/tamper/launcher-timeout/concurrency/
   token-replay probes. Every command record is bound to the production OCI
   index digest.
2. `--finalize-audit` runs under the audit tag for that exact same OCI index.
   It verifies and copies the production evidence bundle, binds the clean
   source commit to all 217 signed files, independently consumes the original
   regression and Matrix B command bytes from that same run, and produces the
   report. It does not launch a second regression.

Both phases independently hash four trees: `/opt/mingli-master`,
`/opt/mingli-runtime/venv`, `/opt/node`, and `/opt/git`. They also run
normalized dynamic-linkage inspection for five native targets: Git, runtime
CPython, the sxtwl native extension, the installed PyYAML C extension, and
Node. Every resolved system-library path and file SHA-256 must be identical.
The 1584-test result is admitted only when its command record is bound directly
to the final artifact digest. The audit phase requires:

- a clean, read-only checkout of source commit `494ce0...` at `/audit-source`;
- a separate read-only checkout of the same commit plus the 54 ignored
  fulltexts at `/audit-research`;
- a blank writable output mount at `/audit-output`;
- a CycloneDX SBOM generated for the production image;
- sanitized backup/restore evidence produced with the production image;
- one top-level OCI index digest shared by the production tag, audit tag, command
  records, release-regression section, and final artifact.

Both phases write exact command argv, executing image ID, exit code,
stdout/stderr bytes, hashes, elapsed seconds, and the fixed timeout budget.
The QEMU fallback gives the standalone Provider Matrix B and the complete
regression separate 10,800-second budgets. The production-audit watchdog is
32,400 seconds, longer than both long commands plus inventory, P0, probe, SBOM,
Git, and identity work. The finalizer has a separate 7,200-second watchdog for
source binding, tree/native equivalence, backup evidence, and report
verification only. A command timeout remains a RED capacity result and is
never reported as an algorithm pass; a non-zero command exit remains an
algorithm/Gate failure. `verify_release.py` independently rehashes every
referenced file and validates the recorded elapsed/budget pairs before
`release-5.1.json` is written.

The Gate intentionally remains RED while `release-5.1.json`, `sbom.cdx.json`,
or referenced audit evidence is absent. Do not hand-create those files.

## Persistent state and restore constraints

The production state base is `/var/lib/mingli`, owned by UID/GID `10001:10001`
with mode `0700`. Backup must be taken from a quiesced single Runtime replica.
The drill uses one source volume and two separately created, proven-empty
destination volumes:

1. run a source `describe`, obtain a `Stopped.need_input` token from an
   intentionally incomplete root Prepare, promote it with one fixed
   supplemental Prepare, capture that Prepared snapshot, and restore it into
   the first blank volume;
2. run `describe` in that restored environment and require the protocol,
   manifest digest, all 13 capability records, and raw output bytes to match
   the source result;
3. replay the exact same supplemental Prepare plus the restored token and
   prove the Prepared bytes, brief, and token are identical;
4. Complete that restored Prepared, then use its Accepted token with a new
   query to create and Complete a real version-2 follow-up; the child token
   record must bind version 2, its parent fingerprint, and the original
   `prior_answer` byte digest;
5. independently Complete the source Prepared, capture the Accepted snapshot,
   restore it into the second blank volume, repeat the exact `describe`
   validation, and replay the original byte-identical Complete;
6. compare only the original/restored/replayed Accepted public-copy and command
   digests. The child follow-up copy is deliberately excluded from this
   byte-identity assertion.

The restore target must keep the absolute path `/var/lib/mingli`, numeric
UID/GID `10001:10001`, and directory mode `0700`, on a local POSIX filesystem
that preserves private ownership, regular files, atomic rename, fsync, and
file-lock semantics. The machine evidence records `st_dev` and `st_ino` for
the source and both proven-empty restore volumes and requires all three
observed `(device, inode)` pairs to be distinct. Those numeric device and inode values may change
during a real restore; they are evidence that fresh volume
roots were used, not values that must be copied from the source. Path,
ownership, mode, content bytes, and filesystem semantics are the invariants.

Raw state tokens never enter committed logs. Runtime results are sanitized to
SHA-256 token fingerprints. Snapshot archives used during the drill are sealed
with a one-time pad; only ciphertext is retained and the pad is destroyed after
the restore succeeds. The verifier rehashes the retained snapshot ciphertext,
sanitized transcripts, and command logs and checks their exact relationships.
