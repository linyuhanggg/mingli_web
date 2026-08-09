# syntax=docker/dockerfile:1.7

# Do not replace these literals with a build ARG.  The Linux Gate admits this
# exact amd64 manifest, and allowing callers to override it would make the
# resulting report describe a different base than the bytes that were built.
FROM python:3.14.6-slim-bookworm@sha256:ff83a535339812dd72e69c93b3c48ddf7c85a324d6330af5797c82a255dbeef4 AS dependency-builder

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SOURCE_DATE_EPOCH=315532800 \
    TZ=UTC

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

COPY verify_release.py /opt/mingli-runtime/verify_release.py
COPY release/ /opt/mingli-master/
COPY requirements-linux-x86_64.lock /opt/mingli-runtime/requirements-linux-x86_64.lock
COPY dependency-provenance.json /opt/mingli-runtime/dependency-provenance.json

RUN python /opt/mingli-runtime/verify_release.py \
        --release-only \
        --release-root /opt/mingli-master

RUN python -m venv --copies /opt/mingli-runtime/build-venv \
    && /opt/mingli-runtime/build-venv/bin/python -m pip install \
        --require-hashes \
        --no-compile \
        --only-binary=:all: \
        --requirement /opt/mingli-master/requirements-runtime-build.lock \
    && mkdir -p /opt/mingli-runtime/downloads /opt/mingli-runtime/wheel-a \
        /opt/mingli-runtime/wheel-b /opt/mingli-runtime/wheelhouse \
    && /opt/mingli-runtime/build-venv/bin/python -m pip download \
        --require-hashes \
        --no-deps \
        --only-binary=PyYAML,astronomy-engine,cnlunar \
        --no-binary=sxtwl \
        --dest /opt/mingli-runtime/downloads \
        --requirement /opt/mingli-runtime/requirements-linux-x86_64.lock \
    && test "$(sha256sum /opt/mingli-runtime/downloads/sxtwl-2.0.7.tar.gz | cut -d' ' -f1)" \
        = "38b24472389f7f6f3521c2c99e4b5e86c0184c7d6eb02e5409c239d21f0a6512" \
    && mkdir -p /opt/mingli-runtime/sxtwl-source \
    && tar -xzf /opt/mingli-runtime/downloads/sxtwl-2.0.7.tar.gz \
        -C /opt/mingli-runtime/sxtwl-source --strip-components=1 \
    && cd /opt/mingli-runtime/sxtwl-source \
    && CFLAGS="-O2 -g0 -ffile-prefix-map=/opt/mingli-runtime=." \
        CXXFLAGS="-O2 -g0 -ffile-prefix-map=/opt/mingli-runtime=." \
        /opt/mingli-runtime/build-venv/bin/python setup.py bdist_wheel \
        --dist-dir /opt/mingli-runtime/wheel-a \
    && rm -rf build \
    && CFLAGS="-O2 -g0 -ffile-prefix-map=/opt/mingli-runtime=." \
        CXXFLAGS="-O2 -g0 -ffile-prefix-map=/opt/mingli-runtime=." \
        /opt/mingli-runtime/build-venv/bin/python setup.py bdist_wheel \
        --dist-dir /opt/mingli-runtime/wheel-b \
    && cmp /opt/mingli-runtime/wheel-a/sxtwl-2.0.7-cp314-cp314-linux_x86_64.whl \
        /opt/mingli-runtime/wheel-b/sxtwl-2.0.7-cp314-cp314-linux_x86_64.whl \
    && test "$(sha256sum /opt/mingli-runtime/wheel-a/sxtwl-2.0.7-cp314-cp314-linux_x86_64.whl | cut -d' ' -f1)" \
        = "bd03d0b56d81112d87ad340a3d65458059497dc33496b1938fb23056dfe8ba80" \
    && cp /opt/mingli-runtime/downloads/*.whl /opt/mingli-runtime/wheelhouse/ \
    && cp /opt/mingli-runtime/wheel-a/*.whl /opt/mingli-runtime/wheelhouse/ \
    && python -m venv --copies /opt/mingli-runtime/venv \
    && /opt/mingli-runtime/venv/bin/python -m pip install \
        --require-hashes \
        --no-index \
        --find-links /opt/mingli-runtime/wheelhouse \
        --only-binary=:all: \
        --no-compile \
        --requirement /opt/mingli-runtime/requirements-linux-x86_64.lock \
    && /opt/mingli-runtime/venv/bin/python -m pip uninstall --yes \
        pip setuptools wheel packaging \
    && find /opt/mingli-runtime/venv -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find /opt/mingli-runtime/venv -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete \
    && test -x /opt/mingli-runtime/venv/bin/python \
    && test ! -L /opt/mingli-runtime/venv/bin/python \
    && PYTHONPATH=/opt/mingli-master/scripts python -B -c \
        "import runtime_python; runtime_python.write_installed_runtime_manifest('/opt/mingli-runtime/venv/bin/python'); runtime_python.probe_runtime_identity('/opt/mingli-runtime/venv/bin/python')" \
    && chmod 0444 /opt/mingli-runtime/venv/runtime-integrity.json

FROM python:3.14.6-slim-bookworm@sha256:ff83a535339812dd72e69c93b3c48ddf7c85a324d6330af5797c82a255dbeef4 AS node-bundle

ADD --checksum=sha256:a6e65cc653e40c1653b77742f9185dbce3ff1f99fa2746d211bddb53530ef206 \
    https://nodejs.org/dist/v26.3.0/node-v26.3.0-linux-x64.tar.gz /tmp/node.tar.gz
RUN mkdir -p /opt/node \
    && tar -xzf /tmp/node.tar.gz -C /opt/node --strip-components=1

FROM python:3.14.6-slim-bookworm@sha256:ff83a535339812dd72e69c93b3c48ddf7c85a324d6330af5797c82a255dbeef4 AS production

ARG RUNTIME_UID=10001
ARG RUNTIME_GID=10001

ENV HOME=/nonexistent \
    MINGLI_PYTHON=/opt/mingli-runtime/venv/bin/python \
    MINGLI_STORE_ROOT=/var/lib/mingli \
    PATH=/opt/node/bin:/opt/mingli-runtime/venv/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC

ADD --checksum=sha256:fbd4e154a6b444229ea002cc209df099209c0adc09102e5fd21239a3d2b55e2d \
    https://snapshot.debian.org/archive/debian/20250501T000000Z/pool/main/g/gcc-12/libatomic1_12.2.0-14+deb12u1_amd64.deb \
    /opt/mingli-runtime/artifacts/libatomic1_12.2.0-14+deb12u1_amd64.deb

RUN test "$(dpkg-deb -f /opt/mingli-runtime/artifacts/libatomic1_12.2.0-14+deb12u1_amd64.deb Package)" = "libatomic1" \
    && test "$(dpkg-deb -f /opt/mingli-runtime/artifacts/libatomic1_12.2.0-14+deb12u1_amd64.deb Version)" = "12.2.0-14+deb12u1" \
    && test "$(dpkg-deb -f /opt/mingli-runtime/artifacts/libatomic1_12.2.0-14+deb12u1_amd64.deb Architecture)" = "amd64" \
    && env PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        /usr/bin/dpkg --install \
        /opt/mingli-runtime/artifacts/libatomic1_12.2.0-14+deb12u1_amd64.deb \
    && test "$(readlink /usr/lib/x86_64-linux-gnu/libatomic.so.1)" = "libatomic.so.1.2.0" \
    && test "$(sha256sum /usr/lib/x86_64-linux-gnu/libatomic.so.1.2.0 | cut -d' ' -f1)" \
        = "107ab9f7661a1c47cddfb5cd1def99ec537a50a9a537fbe38cdde1b34b8ba280" \
    && chmod 0444 /opt/mingli-runtime/artifacts/libatomic1_12.2.0-14+deb12u1_amd64.deb

RUN /usr/sbin/groupadd --gid ${RUNTIME_GID} mingli \
    && /usr/sbin/useradd --uid ${RUNTIME_UID} --gid ${RUNTIME_GID} \
        --home-dir /nonexistent --shell /usr/sbin/nologin mingli \
    && install -d -o ${RUNTIME_UID} -g ${RUNTIME_GID} -m 0700 /var/lib/mingli \
    && install -d -o root -g root -m 0755 /opt/mingli-runtime

COPY --from=dependency-builder /opt/mingli-master/ /opt/mingli-master/
COPY --from=dependency-builder /opt/mingli-runtime/venv/ /opt/mingli-runtime/venv/
COPY --from=dependency-builder /opt/mingli-runtime/.venv.runtime.lock /opt/mingli-runtime/.venv.runtime.lock
COPY --from=node-bundle /opt/node/ /opt/node/
COPY audit_runtime.py emit_sbom.py verify_release.py dependency-provenance.json \
    context-provenance.json /opt/mingli-runtime/

RUN chown ${RUNTIME_UID}:${RUNTIME_GID} /opt/mingli-runtime/.venv.runtime.lock \
    && chmod 0600 /opt/mingli-runtime/.venv.runtime.lock \
    && chmod 0555 /opt/mingli-runtime/audit_runtime.py \
        /opt/mingli-runtime/emit_sbom.py \
        /opt/mingli-runtime/verify_release.py \
    && find /opt/mingli-master -type d -exec chmod 0555 {} + \
    && test "$(/opt/node/bin/node --version)" = "v26.3.0" \
    && ! /usr/bin/ldd /opt/node/bin/node | grep -q "not found" \
    && python /opt/mingli-runtime/verify_release.py \
        --release-root /opt/mingli-master \
        --runtime-python /opt/mingli-runtime/venv/bin/python \
        --node /opt/node/bin/node \
        --state-root /var/lib/mingli

USER 10001:10001
WORKDIR /opt/mingli-master

ENTRYPOINT ["/opt/mingli-master/scripts/run_reading_transaction.sh"]

# The authoritative 1584-test source suite contains repository/privacy/release
# tests that invoke git(1).  Keep that tool in a derived audit target instead
# of widening the production runtime image.  The Gate records both image IDs
# and proves that /opt/mingli-master, the venv and Node tree are inherited from
# the admitted production stage without mutation.
FROM production AS audit

USER 0:0
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
USER 10001:10001

# Make the default build target the git-free production image.
FROM production AS final
