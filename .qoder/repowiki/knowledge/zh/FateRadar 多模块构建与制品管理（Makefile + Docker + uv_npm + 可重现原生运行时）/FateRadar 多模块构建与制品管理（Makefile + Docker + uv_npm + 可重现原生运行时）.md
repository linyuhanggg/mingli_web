---
kind: build_system
name: FateRadar 多模块构建与制品管理（Makefile + Docker + uv/npm + 可重现原生运行时）
category: build_system
scope:
    - '**'
source_files:
    - Makefile
    - backend/pyproject.toml
    - backend/uv.lock
    - backend/.python-version
    - web/package.json
    - web/.nvmrc
    - web/vitest.config.ts
    - admin/package.json
    - infra/docker/backend.Dockerfile
    - infra/docker/web.Dockerfile
    - infra/compose.local.yml
    - infra/nginx/app.conf
    - infra/mingli-runtime/Dockerfile
    - infra/mingli-runtime/verify_release.py
    - backend/alembic.ini
    - backend/alembic/versions/0001_identity_foundation.py
    - contracts/openapi/v1.yaml
    - contracts/schemas/mingli-result-v2.schema.json
    - scripts/verify_frozen_runtime_release.py
---

## 1. 使用的系统与工具

仓库采用**多语言、多进程单体**的构建体系，围绕三个核心工件组织：
- **后端服务**：FastAPI HTTP 进程 + 独立 Worker 进程，Python 3.12，依赖管理使用 `uv`（`pyproject.toml` + `uv.lock`），迁移使用 Alembic。
- **Web 前端与管理后台**：两个独立的 Next.js App Router 应用（`web/`、`admin/`），Node ≥22（`.nvmrc` 锁定为 24），通过 `npm ci` / `next build` 生成 standalone 产物。
- **Mingli 原生运行时**：`infra/mingli-runtime/` 下的自包含 Python+Node+Git 镜像，用于执行命理解读任务，具备严格的二进制级可重现构建。

顶层入口是根目录的 `Makefile`，提供 `install`、`test`、`check`、`build`、`migrate`、`worker-once`、`backend-check`、`web-check`、`admin-typecheck` 等统一命令，屏蔽各子项目的工具差异。

## 2. 关键文件

| 作用 | 路径 |
|---|---|
| 顶层开发/构建入口 | `Makefile` |
| 后端依赖与质量门 | `backend/pyproject.toml`、`backend/uv.lock`、`backend/.python-version` |
| Web 前端脚本与依赖 | `web/package.json`、`web/vitest.config.ts`、`web/.nvmrc` |
| 管理后台脚本与依赖 | `admin/package.json` |
| 后端容器镜像 | `infra/docker/backend.Dockerfile` |
| Web 容器镜像（Next standalone） | `infra/docker/web.Dockerfile` |
| 本地 Compose 环境 | `infra/compose.local.yml` |
| Nginx 边缘配置 | `infra/nginx/*.conf` |
| 原生运行时可重现镜像 | `infra/mingli-runtime/Dockerfile` |
| 数据库迁移 | `backend/alembic.ini` + `backend/alembic/versions/*` |
| 契约定义（OpenAPI/JSON Schema） | `contracts/openapi/*.yaml`、`contracts/schemas/*.schema.json` |
| 发布/门禁脚本 | `scripts/verify_frozen_runtime_release.py`、`infra/mingli-runtime/verify_release.py` |

## 3. 架构与约定

### 3.1 分层构建
- **开发层**：`make install` 调用 `uv sync --project backend --group dev` 安装后端依赖，再分别 `npm install --prefix web` 和 `--prefix admin` 安装前端依赖。测试通过 `pytest`（后端）与 `vitest run`（前端）执行。
- **检查层**：`make check` 串联 `backend-check`（ruff + mypy）、`web-check`（eslint + tsc）、`build`（`next build`），作为提交前质量门。
- **部署层**：Docker 镜像基于多阶段构建。后端镜像以 `ghcr.io/astral-sh/uv:0.11.6` 预装 uv，再以 `python:3.12.12-slim` 运行；Web 镜像先 `node:24-alpine` 安装依赖并 `next build`，最终只拷贝 `.next/standalone`、静态资源与 public 目录，以非 root 用户 `nextjs` 启动。

### 3.2 本地运行编排
`infra/compose.local.yml` 定义 `postgres`、`redis`、`api`、`worker`、`web`、`edge` 六个服务，通过 `depends_on` 与 `healthcheck` 保证启动顺序，`edge` 用 nginx 将流量转发到 api:8000 与 web:3000。

### 3.3 数据库迁移
通过 `make migrate` 调用 `uv run --project backend alembic -c backend/alembic.ini upgrade head`，迁移脚本集中在 `backend/alembic/versions/`，按 `0001_*` 至 `0008_*` 顺序编号。

### 3.4 可重现的原生运行时构建
`infra/mingli-runtime/Dockerfile` 是仓库中最严格的构建系统：
- 所有基础镜像与外部下载均使用 `@sha256:` 或 `--checksum=` 锁定。
- 通过双 lane（a/b）并行编译 sxtwl 源码 wheel 并比对 sha256，确保跨次构建一致。
- 从源码编译 git 2.39.5，禁用 curl/expat/gettext/openssl/perl/python/tcltk 等可选组件，并通过 `nm` 校验符号。
- 设置 `SOURCE_DATE_EPOCH=315532800` 与 `-fdebug-prefix-map` 实现时间戳与路径去敏感化。
- 构建完成后运行 `verify_release.py` 校验 runtime manifest、git/node 版本、libatomic 二进制哈希。
- 最终镜像默认 target 为 `production`，并以 `audit` 别名暴露同一镜像供审计。

### 3.5 契约优先
`contracts/openapi/` 中的 `v1.yaml`、`admin-v1.yaml`、`internal-model-v1.yaml` 以及 `contracts/schemas/` 中的 JSON Schema 是前后端与原生运行时之间的契约中心。根级 `tests/contract/` 下包含 OpenAPI 对齐、Schema 校验、原生发布策略等契约测试，由 `make backend-test` 一并执行。

## 4. 约定与约束

- **Python 版本**：后端要求 `>=3.12,<3.14`（`pyproject.toml`），开发环境通过 `backend/.python-version` 锁定 3.12；原生运行时镜像固定使用 `python:3.14.6-slim-bookworm@sha256:...`。
- **Node 版本**：Web 与 Admin 通过 `engines.node >=22` 与 `.nvmrc 24` 共同锁定，Docker 镜像使用 `node:24-alpine`。
- **依赖锁定**：后端使用 `uv.lock`，Web/Admin 使用 `package-lock.json`，原生运行时使用 `requirements-linux-x86_64.lock` 与 `requirements-runtime-build.lock`，全部通过 `--frozen` / `--require-hashes` / `pip download --no-deps` 等方式强制不可变。
- **构建可重现性**：原生运行时 Dockerfile 中禁止 ARG 覆盖基础镜像、对 sxtwl wheel 与 libatomic deb 做 sha256 断言、对编译产物做双 lane 一致性比对——这是该仓库对“构建必须可重现”这一约束的最强体现。
- **最小权限运行**：Web 镜像创建 `nextjs` 用户并 `USER nextjs`；原生运行时镜像创建 `mingli` 用户（UID/GID 10001）并以只读方式挂载 artifacts。
- **环境变量隔离**：生产镜像通过 `ENV` 注入 `BACKEND_INTERNAL_URL`、`NEXT_TELEMETRY_DISABLED`、`NODE_ENV=production` 等；Compose 通过 `${VAR:-default}` 模式提供本地默认值。
- **质量门统一入口**：所有 lint/type/test/build 都通过 `Makefile` 暴露的 phony target 调用，避免开发者直接拼凑各子项目命令。
- **无 CI 流水线**：仓库未包含 GitHub Actions / GitLab CI 等 CI 配置文件，持续集成逻辑不在本仓库内维护（可能位于托管平台或外部脚本）。