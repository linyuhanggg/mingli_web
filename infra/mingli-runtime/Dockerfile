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
    && for lane in a b; do \
        mkdir -p "/opt/mingli-runtime/sxtwl-source-${lane}"; \
        tar -xzf /opt/mingli-runtime/downloads/sxtwl-2.0.7.tar.gz \
            -C "/opt/mingli-runtime/sxtwl-source-${lane}" \
            --strip-components=1; \
        cd "/opt/mingli-runtime/sxtwl-source-${lane}"; \
        CC=g++ CXX=g++ \
            CFLAGS="-O2 -g0 -ffile-prefix-map=/opt/mingli-runtime/sxtwl-source-${lane}=." \
            CXXFLAGS="-O2 -g0 -ffile-prefix-map=/opt/mingli-runtime/sxtwl-source-${lane}=." \
            /opt/mingli-runtime/build-venv/bin/python setup.py bdist_wheel \
            --dist-dir "/opt/mingli-runtime/wheel-${lane}"; \
    done \
    && cmp /opt/mingli-runtime/wheel-a/sxtwl-2.0.7-cp314-cp314-linux_x86_64.whl \
        /opt/mingli-runtime/wheel-b/sxtwl-2.0.7-cp314-cp314-linux_x86_64.whl \
    && sha256sum /opt/mingli-runtime/wheel-a/sxtwl-2.0.7-cp314-cp314-linux_x86_64.whl \
    && test "$(sha256sum /opt/mingli-runtime/wheel-a/sxtwl-2.0.7-cp314-cp314-linux_x86_64.whl | cut -d' ' -f1)" \
        = "90595ae5a5e311ae019170784c56bff52c176942347836c904e7c8af8d7b5c22" \
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
    && /opt/mingli-runtime/venv/bin/python -I -B -c \
        "import _sxtwl,sxtwl; day=sxtwl.fromSolar(2000,1,1); assert (day.getSolarYear(),day.getSolarMonth(),day.getSolarDay()) == (2000,1,1)" \
    && PYTHONPATH=/opt/mingli-master/scripts python -B -c \
        "import runtime_python; runtime_python.write_installed_runtime_manifest('/opt/mingli-runtime/venv/bin/python'); runtime_python.probe_runtime_identity('/opt/mingli-runtime/venv/bin/python')" \
    && chmod 0444 /opt/mingli-runtime/venv/runtime-integrity.json

FROM python:3.14.6-slim-bookworm@sha256:ff83a535339812dd72e69c93b3c48ddf7c85a324d6330af5797c82a255dbeef4 AS node-bundle

ADD --checksum=sha256:a6e65cc653e40c1653b77742f9185dbce3ff1f99fa2746d211bddb53530ef206 \
    https://nodejs.org/dist/v26.3.0/node-v26.3.0-linux-x64.tar.gz /tmp/node.tar.gz
RUN mkdir -p /opt/node \
    && tar -xzf /tmp/node.tar.gz -C /opt/node --strip-components=1

FROM python:3.14.6-slim-bookworm@sha256:ff83a535339812dd72e69c93b3c48ddf7c85a324d6330af5797c82a255dbeef4 AS git-builder

ENV DEBIAN_FRONTEND=noninteractive \
    SOURCE_DATE_EPOCH=315532800 \
    TZ=UTC

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc make zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

ADD --checksum=sha256:ca0ec03fb2696f552f37135a56a0242fa062bd350cb243dc4a15c86f1cafbc99 \
    https://www.kernel.org/pub/software/scm/git/git-2.39.5.tar.gz \
    /opt/git-build/git-source.tar.gz
COPY verify_release.py git-build-config.json /opt/git-build/

RUN set -eu; \
    for lane in a b; do \
        mkdir -p "/opt/git-build/source-${lane}" \
            "/opt/git-build/install-${lane}"; \
        tar -xzf /opt/git-build/git-source.tar.gz \
            -C "/opt/git-build/source-${lane}" --strip-components=1; \
        cd "/opt/git-build/source-${lane}"; \
        SOURCE_DATE_EPOCH=315532800 make -j6 \
            prefix=/opt/git \
            CC=gcc \
            CFLAGS="-O2 -g0 -ffile-prefix-map=/opt/git-build/source-${lane}=. -fdebug-prefix-map=/opt/git-build/source-${lane}=." \
            LDFLAGS="-Wl,--build-id=none" \
            BLK_SHA256=YesPlease \
            NO_CURL=YesPlease \
            NO_EXPAT=YesPlease \
            NO_GETTEXT=YesPlease \
            INSTALL_SYMLINKS=YesPlease \
            NO_OPENSSL=YesPlease \
            NO_PERL=YesPlease \
            NO_PYTHON=YesPlease \
            NO_TCLTK=YesPlease \
            all; \
        /usr/bin/nm git | grep -q ' SHA1DCInit$'; \
        /usr/bin/nm git | grep -q ' blk_SHA256_Init$'; \
        SOURCE_DATE_EPOCH=315532800 make \
            prefix=/opt/git \
            CC=gcc \
            CFLAGS="-O2 -g0 -ffile-prefix-map=/opt/git-build/source-${lane}=. -fdebug-prefix-map=/opt/git-build/source-${lane}=." \
            LDFLAGS="-Wl,--build-id=none" \
            BLK_SHA256=YesPlease \
            NO_CURL=YesPlease \
            NO_EXPAT=YesPlease \
            NO_GETTEXT=YesPlease \
            INSTALL_SYMLINKS=YesPlease \
            NO_OPENSSL=YesPlease \
            NO_PERL=YesPlease \
            NO_PYTHON=YesPlease \
            NO_TCLTK=YesPlease \
            DESTDIR="/opt/git-build/install-${lane}" \
            install; \
        install -m 0444 COPYING \
            "/opt/git-build/install-${lane}/opt/git/COPYING"; \
        install -m 0444 /opt/git-build/git-build-config.json \
            "/opt/git-build/install-${lane}/opt/git/build-config.json"; \
    done \
    && PYTHONPATH=/opt/git-build python -B -c \
        "import json; from pathlib import Path; import verify_release; roots=[Path('/opt/git-build/install-a/opt/git'),Path('/opt/git-build/install-b/opt/git')]; records=[verify_release.runtime_tree_digest(root) for root in roots]; assert records[0]['entry_count']==records[1]['entry_count']; assert records[0]['sha256']==records[1]['sha256']; result={'binary_sha256':verify_release.sha256_file(roots[0]/'bin/git'),'license_sha256':verify_release.sha256_file(roots[0]/'COPYING'),'tree':records[0]}; print(json.dumps(result,sort_keys=True,separators=(',',':')))"

FROM python:3.14.6-slim-bookworm@sha256:ff83a535339812dd72e69c93b3c48ddf7c85a324d6330af5797c82a255dbeef4 AS production

ARG RUNTIME_UID=10001
ARG RUNTIME_GID=10001

ENV HOME=/nonexistent \
    GIT_CONFIG_GLOBAL=/dev/null \
    GIT_CONFIG_NOSYSTEM=1 \
    MINGLI_PYTHON=/opt/mingli-runtime/venv/bin/python \
    MINGLI_STORE_ROOT=/var/lib/mingli \
    PATH=/opt/git/bin:/opt/node/bin:/opt/mingli-runtime/venv/bin:/usr/local/bin:/usr/bin:/bin \
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
COPY --from=git-builder /opt/git-build/install-a/opt/git/ /opt/git/
COPY --from=git-builder /opt/git-build/git-source.tar.gz \
    /opt/mingli-runtime/artifacts/git-2.39.5.tar.gz
COPY audit_runtime.py emit_sbom.py verify_release.py dependency-provenance.json \
    context-provenance.json /opt/mingli-runtime/

RUN chown ${RUNTIME_UID}:${RUNTIME_GID} /opt/mingli-runtime/.venv.runtime.lock \
    && chmod 0600 /opt/mingli-runtime/.venv.runtime.lock \
    && chmod 0555 /opt/mingli-runtime/audit_runtime.py \
        /opt/mingli-runtime/emit_sbom.py \
        /opt/mingli-runtime/verify_release.py \
    && find /opt/mingli-master -type d -exec chmod 0555 {} + \
    && test "$(/opt/git/bin/git --version)" = "git version 2.39.5" \
    && test "$(sha256sum /opt/git/COPYING | cut -d' ' -f1)" \
        = "5b2198d1645f767585e8a88ac0499b04472164c0d2da22e75ecf97ef443ab32e" \
    && chmod 0444 /opt/mingli-runtime/artifacts/git-2.39.5.tar.gz \
    && test "$(/opt/node/bin/node --version)" = "v26.3.0" \
    && ! /usr/bin/ldd /opt/node/bin/node | grep -q "not found" \
    && python /opt/mingli-runtime/verify_release.py \
        --release-root /opt/mingli-master \
        --runtime-python /opt/mingli-runtime/venv/bin/python \
        --node /opt/node/bin/node \
        --git /opt/git/bin/git \
        --state-root /var/lib/mingli

USER 10001:10001
WORKDIR /opt/mingli-master

ENTRYPOINT ["/opt/mingli-master/scripts/run_reading_transaction.sh"]

# The audit name is an alias for the exact deployable production filesystem.
# The complete 1584-test suite must execute in the same artifact image ID.
FROM production AS audit

# Make the default build target the admitted production image.
FROM production AS final
