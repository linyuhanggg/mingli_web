---
kind: dependency_management
name: 多模块仓库依赖管理：uv + npm lockfile + 原生运行时 SBOM 锁定
category: dependency_management
scope:
    - '**'
source_files:
    - backend/pyproject.toml
    - backend/uv.lock
    - backend/.python-version
    - web/package.json
    - web/package-lock.json
    - web/.nvmrc
    - admin/package.json
    - admin/package-lock.json
    - infra/mingli-runtime/requirements-linux-x86_64.lock
    - infra/mingli-runtime/dependency-provenance.json
    - infra/mingli-runtime/emit_sbom.py
---

## 1. 使用的系统/工具

本仓库是一个包含 Python 后端、Next.js Web 前端与管理后台、以及独立 Mingli 原生运行时的多模块项目，各子模块采用各自语言生态的标准依赖管理方式，并通过锁文件与可验证的制品清单保证构建可重现。

- **Python（backend）**：使用 `uv` 作为包管理器与解析器，声明在 `backend/pyproject.toml`，通过 `backend/uv.lock` 锁定所有传递依赖的版本与哈希。Python 版本由 `backend/.python-version` 固定为 `3.12`，并在 pyproject 中限制 `requires-python = ">=3.12,<3.14"`。
- **Node.js（web、admin）**：两个 Next.js 应用分别维护独立的 `package.json` 与 `package-lock.json`，并通过 `.nvmrc`（值为 `24`）与 `engines.node >= 22` 约束 Node 版本。
- **Mingli 原生运行时（infra/mingli-runtime）**：使用基于 `requirements-linux-x86_64.lock` 的 pip 风格锁定文件，并配合 `dependency-provenance.json` 与 `emit_sbom.py` 生成并校验 CycloneDX 格式的 SBOM，确保生产镜像中的 Python 包、系统库、Node、Git 二进制均与预计算摘要一致。

## 2. 关键文件

| 模块 | 关键文件 | 作用 |
|---|---|---|
| backend | `pyproject.toml` | 声明运行时依赖（FastAPI、SQLAlchemy、Alembic、cryptography 等）与 dev 依赖组（pytest、ruff、mypy），并配置 ruff/mypy/pytest 行为 |
| backend | `uv.lock` | uv 生成的完整依赖图锁定文件，记录每个包的来源 registry（`https://pypi.org/simple`）、sdist/wheel URL 与 sha256 |
| backend | `.python-version` | 固定开发/CI Python 版本为 3.12 |
| web | `package.json` | 声明 React 19、Next.js 16、Zod、Radix UI 等依赖，`type: "module"`，Node engines `>=22` |
| web | `package-lock.json` | npm 锁定文件 |
| web | `.nvmrc` | 固定 Node 版本为 24 |
| admin | `package.json` | 精简版 Next.js 管理后台依赖，与 web 保持相同 major 版本对齐 |
| infra/mingli-runtime | `requirements-linux-x86_64.lock` | 仅含 PyYAML、sxtwl、astronomy-engine、cnlunar 四个包，带 `--hash` 校验 |
| infra/mingli-runtime | `dependency-provenance.json` | 记录 base image、git、node、Python distributions、system runtime、vendored 组件的完整来源与 sha256 |
| infra/mingli-runtime | `emit_sbom.py` | 在生产镜像内校验已安装分布与 provenance 的一致性，并输出 CycloneDX SBOM |

## 3. 架构与约定

### 3.1 版本范围策略
- Python 依赖在 `pyproject.toml` 中使用**主版本上限**约束（如 `fastapi>=0.116,<1`、`sqlalchemy[asyncio]>=2.0.41,<3`、`alembic>=1.16,<2`），避免破坏性升级。
- Node 依赖在 `package.json` 中全部使用**精确版本号**（如 `next: 16.3.0`、`react: 19.2.8`、`zod: 4.4.3`），由 `package-lock.json` 锁定。
- 运行时 Python 版本在 `pyproject.toml` 中限制 `<3.14`，而 Mingli 原生运行时镜像实际使用 CPython `3.14.6`（见 `dependency-provenance.json` 与 `emit_sbom.py` 中的断言），两者职责分离：开发环境用 3.12，生产原生运行时用 3.14。

### 3.2 依赖来源与不可变性
- 所有 Python 依赖来自 `https://pypi.org/simple`，无私有 registry 或 `uv` mirror 配置。
- `uv.lock` 同时记录 sdist 与 wheel 的 URL 与 sha256，实现可重建的依赖解析。
- Mingli 原生运行时通过 `requirements-linux-x86_64.lock` 中的 `--hash=` 强制校验包内容；`emit_sbom.py` 进一步对已安装分发的**整个文件系统树**计算 sha256，并与 `dependency-provenance.json` 中的预期值比对，不匹配则抛出 `SbomError`。
- 原生运行时还锁定系统级依赖（Debian `libatomic1` snapshot 时间戳）与 vendored 组件（如 `iztro` npm tarball 的 sha256），形成端到端可审计链。

### 3.3 模块化隔离
- 每个子模块（backend、web、admin、mingli-runtime）独立维护自己的依赖声明与锁文件，不存在跨模块共享的顶层 `package.json` 或 `pyproject.toml`。
- 测试代码通过 pytest 的 `testpaths = ["tests", "../tests/contract"]` 将根级 `tests/contract` 纳入后端测试套件，但依赖仍由 backend 的 `pyproject.toml` 统一管理。

## 4. 约定与约束

- **Python 依赖必须通过 `uv` 更新并重新生成 `uv.lock`**：`pyproject.toml` 中 `[tool.uv] package = false` 表明该目录仅作为依赖解析单元而非发布包，lock 文件是权威来源。
- **Node 版本必须满足 `engines.node >= 22` 且由 `.nvmrc` 指定为 24**，web 与 admin 共用同一 Node 基线。
- **Mingli 原生运行时只允许四个 Python 包**（PyYAML、sxtwl、astronomy-engine、cnlunar），任何新增依赖需同步更新 `requirements-linux-x86_64.lock`、`dependency-provenance.json` 及 `emit_sbom.py` 中的 `distribution_names` 映射。
- **生产镜像完整性校验是强制的**：`emit_sbom.py` 在 Linux x86_64 环境下要求 Python 解释器路径为 `/opt/mingli-runtime/venv/bin/python`、Node 版本严格等于 `v26.3.0`，且 `runtime-integrity.json` 中的 distributions 列表必须与 `verify_release.EXPECTED_DISTRIBUTIONS` 一致，否则中止构建。
- **无私有 PyPI registry 或 npm registry 配置**：所有依赖源均为公共 PyPI 与 npm，未检出 `pip.conf`、`.npmrc`、`uv.toml` 等自定义源配置。
- **无 vendoring 第三方 Python 源码**：Python 依赖全部通过包管理器安装，仅 Mingli 原生运行时通过 `dependency-provenance.json` 的 `vendored` 字段记录 `iztro` 等前端静态资源。
