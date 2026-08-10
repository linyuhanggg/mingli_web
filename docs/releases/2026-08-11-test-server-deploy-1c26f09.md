# Test Server Deploy: 1c26f09 (2026-08-11)

记录日期：2026-08-11（Asia/Shanghai）

状态：**代码测试服务器升级完成 / real staging blocked / production blocked / real traffic disabled**

结论：本记录是测试服务器（SSH 别名 `fateradar-prod`）的常规代码升级记录，不是上线批准，也不是 production 放量。服务器仍是联调环境：`MINGLI_ENVIRONMENT=local`，OTP 固定 `fake`，Runtime/Model 沿用服务器上既有的 `one-shot` + `deepseek`（DashScope DeepSeek 真实模型联调路径，本轮未改动、未关闭）。公网 18080 入口继续运行，只承载虚构测试数据。本轮部署内容全部来自此前已合入的 web UI 提交，backend / alembic / infra 零改动。

## 1. 部署前后 SHA

- 部署前（服务器 `current`）：`e25183943de346bd365ad66507f15b8a34b06b49`
- 部署后（本机 `main` HEAD，服务器 `current`）：`1c26f0924ce22171b32f0c75a781f7599eec6ed5`
- 中间差异：`e251839` 之后合入 `2dd3bec`（docs: e251839 部署记录）、`0275345`（web: chart workspace shell）、`1c26f09`（web: bazi focusable + conclusion-first + release note）；代码差异仅 web 前端（`chart-workspace-shell`、`bazi-chart` 重构、`focus-detail-drawer`、`time-layer-tabs`、`reading-result` 结论优先 + 对应测试），backend / alembic / infra 零改动
- 部署开始时 `git log -3` 确认 HEAD=`1c26f09`，工作区干净，直接部署 HEAD

## 2. 归档 digest 与路径

- 归档：`fateradar-1c26f0924ce22171b32f0c75a781f7599eec6ed5.tar.gz`（`git archive --format=tar.gz HEAD`，backend + web 一起）
- SHA-256：`0812abbe47a87978dd77480249e34477443708d7776355a8c5064ed48d2177f1`（本机生成与服务器 `sha256sum` 核对一致）
- 服务器路径：`/opt/fateradar/releases/1c26f0924ce22171b32f0c75a781f7599eec6ed5/`
- MANIFEST：`/opt/fateradar/shared/backups/1c26f0924ce22171b32f0c75a781f7599eec6ed5-MANIFEST.txt`
- `current` 原子切换：`ln -s` 到 `current.new` 后 `mv -Tf` 替换，指向新 release

## 3. 构建与依赖（服务器端）

- backend：`UV_PYTHON_INSTALL_DIR=/opt/fateradar/shared/python uv sync --frozen --no-dev --python 3.13`，CPython `3.13.13`，每版独立 `.venv`
- web：`npm ci`（0 vulnerabilities）→ `BACKEND_INTERNAL_URL=http://127.0.0.1:8000 npm run build` → `node scripts/start-standalone.mjs --prepare-only`；Node `22.22.1` / npm `9.2.0`；BUILD_ID `Cjo6cvMq_WsGfw-uOnvMk`，构建产物 19 static + 1 dynamic 路由，含 `/app/bazi`、`/app/readings`、`/app/readings/[readingId]`
- 权限收口：release 目录 `chmod -R a-w`；`web/.next/standalone/.next/cache` 属 `fateradar` 0700 可写（本版构建后该目录不存在，web 单元 `ReadWritePaths` 要求它预先存在；首次 restart 因此触发一次 NAMESPACE 启动失败，按旧版模式手工创建后恢复，最终 NRestarts=0）
- systemd 单元与 nginx 配置新旧 diff 均为空，单元按手册从新 release 安装 + `daemon-reload`

## 4. 数据库与迁移

- 迁移差异：新旧 release 的 `alembic/versions` 完全一致（0001–0007），DB head 已是 `0007_api_idem_verify`，本轮**无迁移执行**
- 切换前备份：`/opt/fateradar/shared/backups/1c26f0924ce22171b32f0c75a781f7599eec6ed5-pre-switch.dump`（`pg_dump -Fc`，329 KB），SHA-256 `3d7cfafb3d48bd059770599f0012ffac9f88029edf05fe04416a2b0eb01a5723` 已记录
- 按手册登记本版 Fake 合同测试 Runtime release（`fateradar-fake-contract` / `test-v1` / source_commit `1c26f09...`，仅允许出现在代码测试库；staging/production 禁止复制该记录）
- 秘密：未读取、未打印 `/etc/fateradar/test.env` 内容，本轮未改动 test.env，release 目录无任何密钥

## 5. 服务与健康验收

四层验收全部通过；随后按手册人工 restart 三服务并复跑，通过：

| 检查项 | 结果 |
|---|---|
| Nginx 回环 `127.0.0.1:8080/healthz` | 200 `{"status":"ok"}` |
| 公网预览 `106.14.10.235:18080/healthz` | 200 `{"status":"ok"}` |
| API live `/api/v1/health/live` | 200 `{"status":"ok","service":"api"}` |
| API ready `/api/v1/health/ready` | 200 `{"status":"ok","service":"database"}` |
| Web 首页（回环） | 200 |
| Web `/app/bazi` | 200 |
| 公网 Web `106.14.10.235:18080/` | 200 |
| systemd `fateradar-test-api/worker/web`、nginx、postgresql | 全部 active |
| `NRestarts`（三服务，重启复验后） | 0 / 0 / 0，无 crash loop |

部署过程一次异常及处置：首次 restart 时 `fateradar-test-web` 因 `.next/cache` 目录不存在（`ProtectSystem=strict` 下 `ReadWritePaths` 挂载失败，status 226/NAMESPACE）启动失败一次；root 手工创建 `web/.next/standalone/.next/cache` 并 chown `fateradar`、chmod 0700 后恢复，后续两次重启（含复验轮）均稳定 active，`NRestarts` 最终为 0。该目录已由单元 `ExecStartPre` 每次启动兜底重建/修正权限。

环境适配器（非秘密键，沿用上一版记录）：`MINGLI_ENVIRONMENT=local`、`MINGLI_OTP_ADAPTER=fake`、`MINGLI_RUNTIME_ADAPTER=one-shot`、`MINGLI_MODEL_ADAPTER=deepseek`、`MINGLI_COOKIE_SECURE=false`。服务器既有真实 Runtime/Model 联调配置本轮未改动、未关闭。

## 6. 回滚点

- 旧版目录原样保留：`/opt/fateradar/releases/e25183943de346bd365ad66507f15b8a34b06b49/`
- 数据库备份：`/opt/fateradar/shared/backups/1c26f0924ce22171b32f0c75a781f7599eec6ed5-pre-switch.dump`（本轮无迁移，DB 实际未变化）
- 回滚步骤（后续版本回滚流程，见 `infra/TEST_SERVER_RUNBOOK.md` §11）：停三服务 → 需要时 `pg_restore --clean --if-exists` 恢复 dump → `ln -s` 旧版到 `current.new` 后 `mv -Tf` 替换 → 启动三服务 → 复跑 §9 全部验收。本次部署全程 `current` 原子替换，无失败中断，未触发回滚

## 7. production blocked / 还差什么

本记录不是上线批准。以下仍未补齐，缺一不可放量：

- 隔离 staging 全轨迹证据（fortune day/week、liuyao manual/digital、follow-up、真实模型 Guard 拒绝 delayed、complete 后 byte-identical replay）
- Guard 红队、state volume backup/restore 实战、四类生产告警演练
- Runtime/Model 凭据进 Secret Manager 与轮换演练（`/etc/fateradar/test.env` 0600 只是联调口径）
- 固定 Model Profile 质量评测与盲测
- 支付 / 短信 / 邮件 / ICP / 公安联网等外部 Gate
- 公网 18080 是无 TLS 测试入口，只放虚构数据，预览完成需按 §8.1 关闭

`real staging blocked / production blocked / real traffic disabled`。

## 8. 禁止项复查

- 未改动 `/etc/fateradar/test.env`；未读取/打印任何秘密；未执行 `git reset --hard`
- 未关闭或改动服务器既有 Runtime/Model 配置；nginx 配置新旧 diff 为空，未改动
- 18080 公网入口未在本轮变更（保持运行状态如实记录）
- 本轮部署内容即此前已合入的 web UI 提交（chart workspace shell、bazi 结论优先阅读），部署过程未修改业务代码
