# FateRadar 测试服务器运行手册（TEST_SERVER_RUNBOOK）

## 0. 定位与边界

这台测试服务器（SSH 别名 `fateradar-prod`）只用于**代码联调与验收**。应用上游仍是纯回环环境，但在未备案期间临时增加了一个公网预览入口：

- API 与 Web 仍只监听 `127.0.0.1:8000`、`127.0.0.1:3000`；Nginx 保留 `127.0.0.1:8080` 的 SSH 隧道入口；
- 临时公网预览由 Nginx 监听 `0.0.0.0:18080`，阿里云安全组与 UFW 都允许 `0.0.0.0/0` 访问 TCP 18080，地址为 `http://106.14.10.235:18080`；它没有 TLS，也不受 ICP 域名入口保护；
- 后端固定跑 `MINGLI_ENVIRONMENT=local`，otp / runtime / model 全部为 `fake`，`cookie_secure=false`，不配置任何真实模型 key，不发生任何外部模型调用；
- 支付走项目自带 `FakePaymentGateway`（永远返回 unavailable，不产生真实支付事实），本服务器不验证真实支付/退款；
- **local + Fake 只是代码测试环境，不是 staging，也不是 production**；这里的数据、占位稿、Fake 验证码都不代表真实事实，真实渠道必须等独立 Adapter + Gate 完成后另走正式环境；
- 操作者本机访问：

  ```bash
  ssh -L 18080:127.0.0.1:8080 fateradar-prod
  # 本机打开 http://127.0.0.1:18080
  ```

- 任何网络也可直接打开 `http://106.14.10.235:18080`。这是公开 HTTP 测试入口，只能使用虚构测试数据；完成预览后应按第 8.1 节关闭。

## 1. 固定目录布局

```text
/opt/fateradar/
├── releases/<sha>/        # 每版一个目录，内容 = git archive 源码，只写一次
│   ├── backend/           # 源码 + 该版独立 .venv（uv 管理）
│   ├── web/               # 源码 + 该版独立 node_modules / standalone 产物
│   └── admin/             # 独立 Staff 控制台 + standalone 产物
├── current -> releases/<sha>   # 原子 symlink，唯一可变指针
└── shared/
    ├── backups/           # 迁移前 pg_dump 与归档 sha256 记录
    └── python/            # uv 管理的 Python 3.13 工具链
```

- 运行环境文件只有 `/etc/fateradar/test.env`（root:root 0600），由 systemd 的 `EnvironmentFile=` 读取；**release 目录内不放任何秘密**；
- systemd 单元、Nginx 都只通过 `current` 找路径。换版本 = 换 `current` + 重启，老版本目录原样保留用于回滚。

## 2. 打包、上传与 hash 核对

1. 构建方用 `git archive` 导出指定 commit 源码（backend + web 一起），生成单个归档并给出它的 sha256；
2. 上传到服务器后核对：

   ```bash
   sha256sum /tmp/fateradar-<sha>.tar.gz
   # 必须等于构建方声明的 digest，不一致立即停止，重新取包
   ```

3. 核对通过后解压到 `/opt/fateradar/releases/<sha>/`，把归档 digest 记入 `/opt/fateradar/shared/backups/<sha>-MANIFEST.txt`；
4. 依赖安装和构建完成后先把归档可能带入的本机权限归一化：目录设为
   `0755`、普通文件设为 `0644`，再执行 `chmod -R a-w` 把 release 转为只读；仅把
   `web/.next/standalone/web/.next/cache` 与
   `admin/.next/standalone/admin/.next/cache` 以及 Next standalone 的
   `web/.next/standalone/web/.next/server`、
   `admin/.next/standalone/admin/.next/server` 单独留给 `fateradar` 用户写入。
   `.venv/bin` 内的启动脚本必须恢复为可执行权限。源码、`.venv`、
   `node_modules` 和 standalone 产物后续都不得原地修改。

## 3. Python 环境（uv 0.11.6 + Python 3.13）

Ubuntu 系统自带 Python 3.14 不符合项目约束（`backend/pyproject.toml` 要求 `>=3.12,<3.14`），不要用系统 Python。用 uv 0.11.6 管理 Python 3.13，每版独立 .venv：

```bash
# 安装并固定 uv 版本（一次）
pipx install uv==0.11.6
# 工具链目录固定到 shared（一次）
export UV_PYTHON_INSTALL_DIR=/opt/fateradar/shared/python
uv python install 3.13

# 每版执行（在 releases/<sha>/backend 内）
cd /opt/fateradar/releases/<sha>/backend
UV_PYTHON_INSTALL_DIR=/opt/fateradar/shared/python \
  uv sync --frozen --no-dev --python 3.13
```

禁止跨版本共享 .venv；升级依赖只允许通过新版本目录完成。

## 4. Web 构建与运行（服务器端构建）

服务器必须先确认 `/usr/bin/node` 存在且 Node >= 22（当前测试机已安装
Node 22.22.1、npm 9.2.0）。每版在服务器上自己装依赖、自己构建，不信任本地产物：

```bash
cd /opt/fateradar/releases/<sha>/web
npm ci
BACKEND_INTERNAL_URL=http://127.0.0.1:8000 npm run build
node scripts/start-standalone.mjs --prepare-only
```

运行入口是构建产出的 `.next/standalone/web/server.js`：

```bash
HOSTNAME=127.0.0.1 PORT=3000 node .next/standalone/web/server.js
```

`BACKEND_INTERNAL_URL` 在构建期写进 Next.js 配置，指向回环 FastAPI。

### 4.1 Admin 构建与运行

Admin 与 Web 使用独立 Next.js standalone 产物和独立 Staff Session。每个 release 在服务器上重新安装并构建：

```bash
cd /opt/fateradar/releases/<sha>/admin
npm ci
BACKEND_INTERNAL_URL=http://127.0.0.1:8000 npm run build
node scripts/start-standalone.mjs --prepare-only
HOSTNAME=127.0.0.1 PORT=3001 node .next/standalone/admin/server.js
```

Admin 只监听 `127.0.0.1:3001`；本手册不授权把它接入临时公网预览。

## 5. 数据库：一个持久 role/db

全服务器只用一个持久数据库 `fateradar_test`（跨 release 保留测试数据），不要每版建库：

```bash
sudo -u postgres psql -c "CREATE ROLE fateradar_test LOGIN;"
sudo -u postgres psql -c "CREATE DATABASE fateradar_test OWNER fateradar_test;"
```

- 密码由服务器端一次性脚本在内存生成，并通过 `psql` 标准输入设置（见第 7 节安全原则）；连接串 `MINGLI_DATABASE_URL` 写在 `/etc/fateradar/test.env` 里，格式 `postgresql+asyncpg://fateradar_test:<password>@127.0.0.1:5432/fateradar_test`；
- 版本切换不换库：新版本迁移直接作用在这个库上；
- 因此**每次迁移前必须先按 release SHA 做 pg_dump**：

  ```bash
  sudo sh -c 'runuser -u postgres -- pg_dump -Fc fateradar_test \
    > /opt/fateradar/shared/backups/<sha>-pre-migration.dump'
  sha256sum /opt/fateradar/shared/backups/<sha>-pre-migration.dump \
    > /opt/fateradar/shared/backups/<sha>-pre-migration.dump.sha256
  ```

  `shared/backups` 默认是 `root:root 0700`，因此恢复演练不能直接让 `postgres` 读取其中的 dump。恢复时由 root 将目标 dump 临时复制到一个唯一路径，设置为 `postgres:postgres 0600`，再以 `runuser -u postgres` 执行 `pg_restore`；核对完成后删除临时副本。不要为了恢复而放宽整个备份目录权限，也不要把 dump 复制进 release。

- 备份非空且 hash 已记录后，必须从该 release 的 backend 目录加载受保护环境，
  再调用 release 自带的 Alembic；不能用全局命令，也不能让它回退到默认数据库：

  ```bash
  sudo bash -lc '
    set -a
    . /etc/fateradar/test.env
    set +a
    cd /opt/fateradar/releases/<sha>/backend
    test -n "${MINGLI_DATABASE_URL:-}"
    test "${MINGLI_DATABASE_URL##*/}" = "fateradar_test"
    .venv/bin/alembic -c alembic.ini upgrade head
  '
  ```

迁移完成后，local + Fake 环境还要登记一条仅供合同测试使用的 Runtime
Release，否则发起阅读会按设计返回 503。下面这条记录只允许出现在代码测试库：

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 -v release_sha='<sha>' \
  -d fateradar_test <<'SQL'
INSERT INTO runtime_releases (
  id, name, version, source_commit, release_manifest_digest,
  protocol_version, describe_manifest_digest, image_digest, production_ready
)
VALUES (
  gen_random_uuid(), 'fateradar-fake-contract', 'test-v1', :'release_sha',
  rpad(:'release_sha', 64, '0'),
  'mingli-portable-interface-v2', repeat('f', 64), NULL, TRUE
)
ON CONFLICT (release_manifest_digest) DO NOTHING;
SQL
```

这不是正式 Runtime 准入；staging/production 禁止复制这条 Fake 记录。

## 6. 运行环境文件与 systemd 单元

`/etc/fateradar/test.env`（root:root 0600）是唯一运行环境文件，内容按后端 `MINGLI_` 前缀约定，至少包含：

```text
MINGLI_ENVIRONMENT=local
MINGLI_OTP_ADAPTER=fake
MINGLI_FAKE_OTP_CODE=246810
MINGLI_RUNTIME_ADAPTER=fake
MINGLI_MODEL_ADAPTER=fake
MINGLI_COOKIE_SECURE=false
MINGLI_TRUSTED_PROXY_CIDRS=127.0.0.0/8
MINGLI_DATABASE_URL=postgresql+asyncpg://fateradar_test:<password>@127.0.0.1:5432/fateradar_test
MINGLI_IDENTITY_HASH_KEY=<server-generated>
MINGLI_CONTENT_ENCRYPTION_KEY_B64=<server-generated>
MINGLI_CONTENT_ENCRYPTION_KEY_ID=fateradar-test-v1
```

四个 systemd 单元固定为 `fateradar-test-api.service`、`fateradar-test-worker.service`、`fateradar-test-web.service`、`fateradar-test-admin.service`，单元文件在仓库 `infra/systemd/`，**Nginx 用系统 nginx，不是自定义单元**。安装：

```bash
sudo install -o root -g root -m 0644 \
  /opt/fateradar/current/infra/systemd/fateradar-test-api.service \
  /opt/fateradar/current/infra/systemd/fateradar-test-worker.service \
  /opt/fateradar/current/infra/systemd/fateradar-test-web.service \
  /opt/fateradar/current/infra/systemd/fateradar-test-admin.service \
  /etc/systemd/system/
sudo systemctl daemon-reload
```

要点（以仓库文件为准）：

- 四个单元都用 `User=fateradar` / `Group=fateradar`，`WorkingDirectory` 经 `current` 指向本版，自带 `ProtectSystem=strict` 等加固；
- API：`ExecStart=/opt/fateradar/current/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`，读取 `EnvironmentFile=/etc/fateradar/test.env`；
- Worker：`ExecStart=.../.venv/bin/python -m worker.main --poll-interval 2`，同样读 `test.env`；**固定单副本**，任务抢占靠 Postgres 行锁，禁止模板扩容；
- Web：`WorkingDirectory=/opt/fateradar/current/web/.next/standalone/web`，`ExecStart=/usr/bin/node server.js`，`HOSTNAME=127.0.0.1`、`PORT=3000`、`NODE_ENV=production` 由单元自带，不需要 secrets；`BACKEND_INTERNAL_URL` 构建期已内联。
- Admin：`WorkingDirectory=/opt/fateradar/current/admin/.next/standalone/admin`，`ExecStart=/usr/bin/node server.js`，`HOSTNAME=127.0.0.1`、`PORT=3001`、`NODE_ENV=production` 由单元自带；仅允许回环访问，不进入公共 Web 预览。

## 7. 秘密管理原则（服务器端生成、不落命令行、不打印）

- 所有秘密（DB 密码、`MINGLI_IDENTITY_HASH_KEY`、`MINGLI_CONTENT_ENCRYPTION_KEY_B64`）只由服务器上的一次性 root 脚本用安全随机数生成；脚本在内存中拼好 SQL，通过标准输入交给 `psql`，再原子写入 root:root 0600 的 `/etc/fateradar/test.env`；
- 设置 DB 密码时**不要**用 `cat`/命令替换把密码塞进 `psql` 命令行（会暴露在 `ps` 里），不要生成会残留秘密的临时 SQL 文件，也不要打印随机值；
- `test.env` 靠 `EnvironmentFile=` 由 systemd 自己读取，值不会出现在进程 argv 里，`systemctl show -p Environment` 也看不到文件内容；
- 禁止 `cat /etc/fateradar/test.env`、禁止把 secret 写进日志、聊天、CI 输出；仓库 `.env.example` 只放 local 占位值，真实秘密永不入库；
- 换版本不换秘密；只有需要轮换时才重新生成并同步 `ALTER ROLE` + `test.env` + 重启。

## 8. Nginx：回环入口安装

```bash
sudo install -m 0644 /opt/fateradar/current/infra/nginx/fateradar-test-loopback.conf \
  /etc/nginx/sites-available/fateradar-test-loopback.conf
sudo ln -sfn /etc/nginx/sites-available/fateradar-test-loopback.conf \
  /etc/nginx/sites-enabled/fateradar-test-loopback.conf
sudo nginx -t
sudo systemctl reload nginx
```

- 本回环配置只监听 `127.0.0.1:8080`，自身不修改现有公网 fateradar 配置、域名、TLS/letsencrypt 或 UFW；临时公网入口单独按第 8.1 节管理；
- `/api/` 反代 `127.0.0.1:8000`（no-store），其余反代 `127.0.0.1:3000`，`/healthz` 由 Nginx 自己返回。

### 8.1 未备案期间的临时公网预览

当前经操作人明确授权，临时公开 TCP 18080：

```bash
sudo install -m 0644 /opt/fateradar/current/infra/nginx/fateradar-test-public-preview.conf \
  /etc/nginx/sites-available/fateradar-test-public-preview.conf
sudo ln -sfn /etc/nginx/sites-available/fateradar-test-public-preview.conf \
  /etc/nginx/sites-enabled/fateradar-test-public-preview.conf
sudo ufw allow 18080/tcp comment 'FateRadar public test preview'
sudo nginx -t
sudo systemctl reload nginx
```

阿里云安全组 `sg-uf6askrnpezdd7reh6yl` 同步配置入方向 `0.0.0.0/0`、自定义 TCP、端口 `18080/18080`。上线验收：

```bash
curl -fsS http://106.14.10.235:18080/healthz
curl -fsS http://106.14.10.235:18080/api/v1/health/live
curl -fsS -o /dev/null -w '%{http_code}\n' http://106.14.10.235:18080/
```

关闭入口时，在阿里云控制台删除上述安全组规则，并执行：

```bash
sudo ufw --force delete allow 18080/tcp
sudo rm -f /etc/nginx/sites-enabled/fateradar-test-public-preview.conf
sudo rm -f /etc/nginx/sites-available/fateradar-test-public-preview.conf
sudo nginx -t
sudo systemctl reload nginx
```

关闭公网入口不会影响 `127.0.0.1:8080` 的 SSH 隧道方式。

## 9. 启动与健康检查

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fateradar-test-api fateradar-test-worker fateradar-test-web fateradar-test-admin
```

验收覆盖五层（API live/ready、Web、Admin、回环 Nginx、四个 systemd 单元）：

```bash
# Nginx 回环层
curl -fsS http://127.0.0.1:8080/healthz
# 临时公网层
curl -fsS http://106.14.10.235:18080/healthz
# API 存活 / 就绪（经回环入口）
curl -fsS http://127.0.0.1:8080/api/v1/health/live
curl -fsS http://127.0.0.1:8080/api/v1/health/ready
# Web 首页
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/
# Admin 登录页（回环直连）
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3001/login
# systemd 单元状态
sudo systemctl is-active fateradar-test-api fateradar-test-worker fateradar-test-web fateradar-test-admin nginx
```

任一失败即视为部署失败，进入回滚。**全部通过后重启一次所有单元，再复跑一遍上面的检查**，确认开机自启路径可靠。

Next standalone 收到 systemd 的 SIGTERM 时会按其信号约定退出 `143`；人工
`restart` 的停止阶段可能因此留下 `Failed with result 'exit-code'`，随后正常
启动。只有出现 `Scheduled restart`、`NRestarts` 增长或健康检查失败才算崩溃；
如需消除这条停止噪音，可在 Web 单元后续加入 `SuccessExitStatus=143`。

## 10. Fake OTP 与 E2E 验收

- 环境固定 `MINGLI_ENVIRONMENT=local` + `MINGLI_OTP_ADAPTER=fake`，验证码 `246810`；
- 执行前确认第 5 节的 Fake Runtime 测试记录已登记；
- E2E 冒烟：登录页输入一个纯虚构测试邮箱 → 使用页面在 local + Fake 环境显示的 `246810` 完成首次注册/登录 → 建立虚构档案 → 走一次完整阅读流程 → 从解读历史重新打开结果 → 退出当前设备；
- 支付只验证流程形状（FakePaymentGateway 返回 unavailable），不验证真实支付/退款；
- 验收只证明代码路径可用，Fake 响应不代表真实渠道行为。

## 11. 回滚

### 首次部署回滚（没有可用的旧版本）

```bash
sudo systemctl stop fateradar-test-api fateradar-test-worker fateradar-test-web fateradar-test-admin
sudo rm /opt/fateradar/current
```

- 此时 `/healthz` 仍应返回 200（Nginx 自己回答，不依赖上游）；API 的 live/ready 应失败或 502，Web 页面不可达——这是预期状态；
- 全新库 `fateradar_test` 若刚建，直接删掉重建即可，无需恢复备份；
- 保留 releases 目录供排障，确认问题后手工清理。

### 后续版本回滚（恢复备份 + 原子切 current）

```bash
sudo systemctl stop fateradar-test-api fateradar-test-worker fateradar-test-web fateradar-test-admin
# 1) 把持久库恢复到该 release 迁移前状态
sudo -u postgres pg_restore -d fateradar_test --clean --if-exists \
  /opt/fateradar/shared/backups/<旧sha>-pre-migration.dump
# 2) 原子切回旧版本
ln -s /opt/fateradar/releases/<旧sha> /opt/fateradar/current.new
mv -Tf /opt/fateradar/current.new /opt/fateradar/current
# 3) 重启并复跑第 9 节全部检查 + 第 10 节 Fake OTP 冒烟
sudo systemctl start fateradar-test-api fateradar-test-worker fateradar-test-web fateradar-test-admin
```

- 新版本目录先保留，确认稳定后再清理；
- 回滚后必须重新执行完整验收（含重启复验）。

## 12. 红线清单

- API 与 Web 只监听回环；临时公网只允许经 Nginx 的 18080 入口，绝不直接暴露 8000/3000；
- 18080 是无 TLS 的全网公开测试入口，只放虚构测试数据，预览完成后按第 8.1 节关闭；
- 不打印秘密，秘密不入库、不上传、不塞进命令行；
- 不跳过归档 sha256 核对；
- 用 uv 0.11.6 + Python 3.13，不用系统 Python 3.14；
- 不共享 .venv / node_modules，数据库只用 `fateradar_test` 一个持久库；
- 迁移前必须 pg_dump，`current` 只能原子替换；
- 本服务器**只是代码测试**：local + Fake，不是 staging/production，不验证真实支付，不产生真实事实。
