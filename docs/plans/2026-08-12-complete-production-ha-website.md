# FateRadar 完整生产网站与高可用实施计划

> **For Codex/Claude:** REQUIRED SUB-SKILL: use `executing-plans` to implement this plan task-by-task in a dedicated git worktree. Never implement directly on `main`; preserve unrelated user changes and review each checkpoint before continuing.

**Goal:** 把当前已跑通免费命理解读主链路的单机测试候选，建设为功能完整、可收费、可运营、可恢复、可观测，并达到明确 P0 高可用指标的生产网站。

## 执行进度（实时更新，完成一项更新一项）

| Task | 状态 | 证据 / 备注 |
|---|---|---|
| Task 0 固定可信基线 | ✅ 实现完成，待审查合并（分支 `worktree-production-ha-task0` @ d894704） | `make check` 全绿（backend 528 passed/82 skipped 全为已退役 Linux 门禁；web 250；admin 8）；PG 并发门禁实测通过；Alembic 0001→0008 与 0007→head 升级通过。证据 `docs/releases/2026-08-12-production-readiness-baseline.md`。`.qoder/**` 已裁决为生成物，迁移计划 `docs/plans/2026-08-12-qoder-generated-assets-migration.md` 待用户批准后执行 |
| Task 1 完成定义/SLO 合同 | ✅ 实现完成，待审查（同分支） | 新增 `docs/PRODUCTION_READINESS.md`（五状态机+用户可见状态映射）、`docs/operations/SLO.md`（每项含数据来源）、`docs/operations/ERROR_BUDGET.md`、`docs/adr/0011-production-ha-and-degraded-reading.md`；PHASE_0_GATES 增加 owner/证据/复核/回滚表；Blueprint 第 21 节绑定 Feature Complete 语义 |
| Task 2 数据正确性 | 🔶 Step 1–4 完成（幂等 @ d72c302，Profile 语义 @ 064f45a，三条核对 @ 49bee46），Step 5 进行中 | 幂等并发 bug 已修复：RED 复现 → 迁移 `0009_idempotency_owner_uniqueness` 两个 partial unique index → GREEN。Profile 编辑=同 Root 追加不可变版本（`POST /profiles/{id}/versions`），出生合同补齐历法/闰月/时辰准确度/坐标来源精度，真太阳时强制显式坐标。Step 4：核对改为三条 fact_ref 级独立结果（迁移 `0010_verification_results`，服务端按公开事实面板校验 ref，未知/重复→400，未 accepted→409；Web 逐条核对，不足三条不收集；答案不回灌 Prompt）。backend 413 passed（含 PG 门禁）+ web 254 passed + ruff/tsc/eslint/build 全绿；0010 在真 PG 上 upgrade/downgrade/upgrade 往返通过。mypy 有 3 个 HEAD 遗留 error（admin role×2、service horizon×1），与本步无关 |
| Task 3 认证/限流/账户权利 | ⬜ 未开始 | |
| Task 4 商业事实链 | ⬜ 未开始 | |
| Task 5 购买体验/Admin | ⬜ 未开始 | |
| Task 6 Runtime/模型/Guard Gate | ⬜ 未开始 | |
| Task 7 Worker 可恢复 | ⬜ 未开始 | |
| Task 8 密钥/观测/告警 | ⬜ 未开始 | |
| Task 9 CI/CD | ⬜ 未开始（需用户授权建 remote） | |
| Task 10 双可用区基础设施 | ⬜ 未开始（ECS 盘点可先只读执行） | |
| Task 11 备份恢复演练 | ⬜ 未开始 | |
| Task 12 浏览器/a11y/性能/SEO | ⬜ 未开始 | |
| Task 13 灰度与 GA | ⬜ 未开始（外部 Gate 前置） | |

**Architecture:** 保持 Next.js + FastAPI 模块化单体 + PostgreSQL 事实源，不拆微服务、不上 Kubernetes。Web/API 做跨两个可用区的无状态双副本；PostgreSQL 与 Redis 使用托管高可用实例；通用异步任务可横向扩展，mingli-master Runtime 因本地状态合同保持“单活 + 受控热备”，故障时网站、账户、订单继续服务，解读进入可解释的延迟状态。

**Tech Stack:** Next.js 16、React 19、TypeScript、FastAPI、Python 3.12/3.13、SQLAlchemy、Alembic、PostgreSQL 16、Redis/Tair、Nginx/ALB、私有 OSS、阿里云 ECS/RDS/Tair/CloudMonitor/SLS、Terraform/OpenTofu、GitHub Actions（创建正式私有 remote 后）。

---

## 0. 计划状态与事实基线

计划日期：2026-08-12。

仓库固定点：

- `main @ 8c0c66eec6872b8648867edef05f12864762699c`
- 工作区在审计结束时干净；没有 Git remote 或 upstream。
- Alembic head：`0008_admin_staff`。
- 已购买并实际使用一台阿里云上海 ECS：实例 `i-uf67fkafnm3w0abdmz3m`，SSH 别名 `fateradar-prod`，已记录公网入口 `106.14.10.235:18080`；它不是待采购资源。
- 该 ECS 上已有 Nginx、Web、API、Worker、PostgreSQL、systemd release 目录与备份，服务器已记录版本仍为 `6ec1578`，落后于本地 `main`。
- `fateradar.cn` / `www.fateradar.cn` / `api.fateradar.cn` 的 DNS、证书和阿里云 DirectMail 曾完成配置，但 ICP 与生产准入仍未完成。
- nmem 中另有“杭州 u2a 4 核 8GB、100GB、5Mbps、包年”的选型记录，与上海实机部署记录冲突；实际 SKU、可用区、VPC、磁盘、带宽、计费到期日和自动续费状态必须从阿里云只读盘点确认，计划不得拿选型记录冒充资产事实。
- 测试服曾完成 preview / today / week / liuyao / follow-up 5/5 Accepted；这只是测试联调证据。
- Web：31 个测试文件、250 tests 通过；lint、typecheck、production build 通过。
- Backend/contract：520 passed、90 skipped；90 个 skipped 中包含必须在 PostgreSQL 跑的并发与恢复门禁。
- `make check` 当前为红：Ruff 3 项；独立 mypy 另有 6 项，均来自最新平台/admin 基线。
- Admin lint/typecheck/build 通过，但没有测试脚本，也未进入根级 `make check`。
- 最新提交一次纳入了 300+ `.qoder` 文件；实施前必须决定它们是正式知识资产还是生成物，不能默默扩大仓库。

当前代码的生产保护是正确的，但也说明尚未上线：

- production SMTP OTP 因 challenge/限流仍在内存而被拒绝。
- `MINGLI_REAL_TRAFFIC_ENABLED=true` 在 production 会被无条件拒绝。
- 生产 Nginx 的 API 路由仍固定返回 `503 api_not_deployed`。
- 只有单机 test systemd；无正式 CI/CD、多可用区拓扑、真实告警和恢复演练。

## 1. 本轮范围与默认决策

用户不需要先写专业 PRD。本计划依据以下项目权威文件补齐需求：

- `docs/PRODUCT_DIRECTION.md`
- `docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md`
- `docs/MINGLI_V51_WEB_INTEGRATION.md`
- `docs/PHASE_0_GATES.md`
- `DESIGN.md`
- `design-system/mingli-web/MASTER.md`
- `docs/plans/2026-08-09-mingli-v51-web-integration.md`
- `docs/plans/2026-08-11-admin-console-plan.md`

默认决策：

1. “完整”以 `PRODUCT_BLUEPRINT_WEB_IOS_V2.md` 的 15 条 P0 发布验收为最低合同，不以“页面能打开”冒充完成。
2. 本轮包含免费闭环、账户与数据权利、两种单次付费、退款/对账、运营后台和生产高可用。
3. P1 自动续费、原生 iOS、专业命理师工作台、P0 以外术法产品化不在本轮。
4. 继续保持 13 Provider 完整 Runtime；产品只曝光 bazi / fortune / liuyao。
5. 不自动切换未经固定评测的第二模型。模型故障时排队、退避、熔断并诚实展示延迟。
6. 不宣称“永不宕机”。高可用必须用 SLO、RTO、RPO、故障演练和真实告警证明。
7. 已购上海 ECS 必须先盘点并优先复用，不重复购买同类服务器；短期继续承载测试/预发布，生产角色通过 ADR 决定，可选 ECS-A、Runtime 单活节点或长期 staging。
8. 备案、支付商户、短信通道，以及为补足高可用而新增的 ALB、第二可用区计算、RDS、Tair、OSS 等资源属于外部 Gate；计划可以推进本地实现，但实际开通、付费或改变现有 ECS 用途前需用户授权。

明确非目标：

- Kubernetes、微服务拆分、Kafka、多地域双活。
- 把 Runtime 塞进每个 API 副本或并发运行多个 state root 写者。
- 无限 AI、金币钱包、会员等级、优惠券、自动续费。
- 用客户端回跳当支付到账；用 localStorage 保存凭据或私人事实。
- 复制 Metis 品牌、私有接口或算法。

## 2. 完成状态机

| 状态 | 必须具备 | 明确不能声称 |
|---|---|---|
| Feature Complete | P0 用户旅程、支付、账户权利、后台均有真实代码和自动测试 | 不能称生产就绪 |
| Staging Ready | 独立 staging 数据/密钥/对象桶，真 OTP、真 Runtime、真模型和支付沙箱闭环 | 不能放普通用户流量 |
| Production Ready | 安全、合规、密钥、备份、告警、恢复、压测和回滚 Gate 全绿 | 不能跳过灰度直接全量 |
| Canary | 小范围真实账号/小额订单运行，指标和告警稳定，随时可回滚 | 不能承诺 99.9% 已长期达成 |
| General Availability | 双可用区入口、生产支付和运营闭环启用；连续观测期内无 P0/P1 阻断 | 才可称“完整高可用网站” |

## 3. P0 SLO、RTO、RPO 与容量假设

| 指标 | P0 目标 | 验证方式 |
|---|---:|---|
| 公共网站与非模型 API 月可用性 | 99.9%，计划维护计入 | 外部 HTTP(S) 探针 + SLO 看板 |
| 非模型 API 延迟 | p95 ≤ 500ms，p99 ≤ 1.5s | 服务端 histogram；排除异步生成耗时 |
| Web Core Web Vitals | 移动 p75：LCP ≤ 2.5s、INP ≤ 200ms、CLS ≤ 0.1 | 真实设备 + RUM/Lighthouse CI |
| OTP | 99% 被供应商接受；用户收件 p95 ≤ 30s | Adapter 指标 + 合成登录 |
| 解读任务 | p95 ≤ 5 分钟进入明确终态；p99 ≤ 10 分钟 | 队列年龄与状态时长指标 |
| 单应用节点故障 | 自动摘除并恢复服务 ≤ 2 分钟 | 持续探针中杀一台 ECS |
| 发布回滚 | RTO ≤ 15 分钟 | Canary 回滚演练 |
| PostgreSQL | RPO ≤ 5 分钟；RTO ≤ 60 分钟 | PITR/主备切换/空环境恢复演练 |
| Runtime state | RPO ≤ 5 分钟；RTO ≤ 60 分钟 | Prepared/Accepted token 恢复演练 |
| Redis/Tair | 不保存唯一业务事实；恢复 ≤ 15 分钟 | 主备切换；允许短期 OTP 失效但不得串号 |
| 首版容量门 | 20 req/s 持续、50 req/s 峰值 5 分钟、10 个并发解读提交 | k6/Locust + 资源与队列指标 |

区域级灾难不纳入 P0 可用性承诺；P2 再用跨地域数据库备份、OSS 复制和 DNS 切换覆盖。

## 4. 目标生产拓扑

```text
                         ┌──────────────────────────┐
Internet ─ DNS/TLS/WAF ─┤ ALB（至少两个可用区）   │
                         └────────────┬─────────────┘
                                      │ health: real readiness
                    ┌─────────────────┴─────────────────┐
                    │                                   │
          ECS-A: Nginx/Web/API                ECS-B: Nginx/Web/API
          stateless, AZ-A                     stateless, AZ-B
                    │                                   │
                    └──────────────┬────────────────────┘
                                   │
              ┌────────────────────┼─────────────────────┐
              │                    │                     │
      RDS PostgreSQL HA       Tair/Redis HA        Private OSS
      sole business truth     OTP/rate/cache       export/artifacts
              │
        durable jobs/outbox
              │
    ┌─────────┴─────────┐
    │ Runtime Worker    │  single active writer + fenced warm standby
    │ Model Gateway     │  bounded retry/backoff/circuit breaker
    └─────────┬─────────┘
              │
      backed Runtime state

Admin: private network / VPN / IP allowlist / SSH tunnel only
Logs/Metrics: SLS + CloudMonitor + real on-call routes
```

已有 ECS 不等于已经高可用：单实例故障、单盘故障或所在可用区故障仍会中断全部服务。默认复用策略是先保留现有测试入口，在不重装、不迁移、不改安全组的前提下完成资产盘点；确认其可用区、VPC、容量与生命周期后，再决定把它纳入生产拓扑还是长期保留为 staging。无论采用哪种角色，生产 99.9% 目标仍需要另一个故障域和消除本机 PostgreSQL、进程内 OTP/限流等单点。

阿里云能力在新增或变更资源前仍要复核：ALB 官方支持多可用区和健康检查；RDS PostgreSQL 支持高可用/多可用区、自动备份与按时间点恢复；Tair 支持同城多可用区容灾；OSS 支持版本控制和跨区域复制；CloudMonitor 支持可用性探测和电话/短信/邮件/Webhook 报警。

## 5. 里程碑与粗略工期

这是单工程师的数量级估算，不包含 ICP、商户、短信模板等外部审批等待：

| 里程碑 | 主要内容 | 粗略工程量 |
|---|---|---:|
| M0 基线可信 | 当前门禁、PG CI、文档和 generated assets 收口 | 2–3 天 |
| M1 免费闭环完整 | Profile、三项核对、账户权利、真实 OTP | 6–10 天 |
| M2 商业闭环 | Catalog、订单、支付、权益、退款、有限追问 | 10–15 天 |
| M3 运营与质量 | Admin、模型评测、Guard 红队、恢复 | 7–10 天 |
| M4 生产工程 | Worker、密钥、观测、CI/CD、双可用区 | 10–15 天 |
| M5 上线验收 | 安全/性能/容灾/支付小额/灰度 | 5–8 天 + 外部等待 |

总量约 40–60 个专注工程日。可以先交付免费 beta，但不能把 beta 叫完整商业高可用站。

---

## Task 0: 固定可信基线并让根门禁全绿

**Files:**

- Modify: `backend/alembic/env.py`
- Modify: `backend/app/readings/candidate_reference_closer.py`
- Modify: `backend/tests/test_reading_worker.py`
- Modify: `backend/app/admin/repository.py`
- Modify: `backend/app/api/admin.py`
- Modify: `Makefile`
- Modify: `admin/package.json`
- Create: `admin/src/test/admin-auth.test.tsx`
- Create: `docs/releases/2026-08-12-production-readiness-baseline.md`
- Create: `docs/HANDOFF_SNAPSHOT_2026-08-12.md`
- Modify: `README.md`
- Modify: `docs/PHASE_0_GATES.md`
- Review only: `docs/HANDOFF_SNAPSHOT_2026-08-11.md`
- Review only: `.qoder/**`

**Steps:**

1. 创建独立 worktree；记录 `8c0c66e`、工作区、Alembic head、测试服 current 和无 remote 事实。
2. 先重跑 `make check`，保留 Ruff 3 项与 mypy 6 项的失败输出。
3. 只做最小 import/type 修复；不顺带重构业务代码。
4. 为 `admin` 增加 Vitest/testing-library 测试脚本，至少覆盖登录态、401、CSRF 和私人路由。
5. 把 admin test/lint/typecheck/build 纳入根级 `make check`。
6. 在 PostgreSQL 16 上设置 `MINGLI_TEST_POSTGRES_URL`，执行当前 90 个 skipped 中所有 PG 门禁；环境无关 skipped 必须逐项解释。
7. 确认 `0001 → 0008` 空库升级通过，旧 head 数据库升级通过，迁移后应用可启动。
8. 决定 `.qoder` 是正式仓库资产还是生成物：若是生成物，另写非破坏迁移计划并经用户批准后再移出；本任务不删除。
9. 新建 2026-08-12 Handoff，并让 README 指向它；旧日期快照保持历史不改。新快照写准 HEAD、Alembic head、测试服版本和已修/未修事实，消除状态漂移。

**Verify:**

```bash
make check
npm --prefix admin run test
npm --prefix admin run lint
npm --prefix admin run typecheck
npm --prefix admin run build
MINGLI_TEST_POSTGRES_URL='postgresql+asyncpg://…' \
  uv run --project backend pytest backend/tests tests/contract -q
uv run --project backend alembic -c backend/alembic.ini heads
git status --short
```

Expected: 根门禁全绿；关键 PG 测试不再因缺 URL 跳过；文档只报告可复验证据。

**Commit:** `chore: establish production readiness baseline`

## Task 1: 冻结完成定义、SLO 与生产准入合同

**Files:**

- Create: `docs/PRODUCTION_READINESS.md`
- Create: `docs/operations/SLO.md`
- Create: `docs/operations/ERROR_BUDGET.md`
- Create: `docs/adr/0011-production-ha-and-degraded-reading.md`
- Modify: `docs/PHASE_0_GATES.md`
- Modify: `docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md`

**Steps:**

1. 把本计划第 2–4 节写成版本化合同：功能完成、Staging Ready、Production Ready、Canary、GA 五个状态不得混用。
2. 冻结 99.9%、延迟、RTO/RPO、容量和告警响应目标。
3. 明确 Runtime 单活是 P0 合同；Runtime/模型故障只降级解读，不拖垮登录、订单、报告读取和退款。
4. 明确用户可见状态与内部状态映射：queued、waiting_input、delayed、runtime_unknown、stopped、accepted。
5. 给每个外部 Gate 指定 owner、证据路径、复核日期、失败时回滚行为。
6. 评审并签字后才允许后续任务改变 production fail-closed 逻辑。

**Verify:** 文档中的每个 SLO 都有数据来源，每个 Gate 都有机器或人工证据路径，没有“基本可用”“稳定”等不可测措辞。

**Commit:** `docs: freeze production readiness and slo contract`

## Task 2: 修复 P0 数据正确性与产品合同漂移

**Files:**

- Modify: `backend/app/readings/models.py`
- Create: `backend/alembic/versions/0009_idempotency_owner_uniqueness.py`
- Create: `backend/tests/test_reading_idempotency_postgres.py`
- Modify: `backend/tests/test_migrations.py`
- Modify: `backend/app/profiles/models.py`
- Modify: `backend/app/profiles/service.py`
- Modify: `backend/app/api/profiles.py`
- Modify: `contracts/openapi/v1.yaml`
- Modify: `web/src/components/profile-form.tsx`
- Modify: `backend/app/readings/service.py`
- Modify: `web/src/components/readings/verification-form.tsx`
- Modify: `web/src/components/readings/reading-result.tsx`
- Modify: `backend/tests/test_readings_api.py`
- Modify: `web/src/test/reading-result.test.tsx`

**Step 1: 先写 PostgreSQL 并发失败测试** ✅（@ d72c302，`backend/tests/test_reading_idempotency_postgres.py`，user/guest 两例均按预期 RED）

用两个独立 API/数据库会话同时提交同一 owner、同一 `Idempotency-Key`。当前预期应 FAIL：PostgreSQL 的三列 UNIQUE 含一个必然为 NULL 的 owner 列，不能阻止并发重复插入。

**Step 2: 用两个 partial unique index 修复** ✅（@ d72c302，迁移 0009 + 模型元数据同步；GREEN：一个 mapping、一个 Reading Version、两响应 ID 相同；`test_reading_migrations.py` 断言同步更新）

迁移删除旧约束，建立：

```sql
CREATE UNIQUE INDEX uq_reading_idem_user_key
ON reading_idempotency_keys (key_hash, owner_user_id)
WHERE owner_user_id IS NOT NULL;

CREATE UNIQUE INDEX uq_reading_idem_guest_key
ON reading_idempotency_keys (key_hash, owner_guest_session_id)
WHERE owner_guest_session_id IS NOT NULL;
```

模型元数据必须与迁移一致。并发测试最终断言：一个 mapping、一个 Reading Version、两个响应 ID 相同。

**Step 3: 修正 Profile Root/Version 语义** ✅（@ 064f45a，新增 `POST /profiles/{profile_id}/versions` 编辑=同 Root 追加不可变版本；出生合同补齐历法/闰月/时辰准确度/坐标来源/精度；真太阳时必须显式坐标不静默估算；Web 表单编辑模式 + 档案页“修改资料”入口；backend 398 + web 253 全绿）

“编辑档案”必须在同一 Profile Root 下追加不可变 Profile Version；“新增档案”才创建新 Root。补齐公历/农历、闰月、不确定时辰、出生地坐标来源/精度和真太阳时确认合同。经纬度解析失败必须显式要求用户修正，不能静默估算。

**Step 4: 落地三条独立现实核对** ✅（@ 49bee46；`VerificationRequest.results` 恰好三条 `{fact_ref, outcome}`；服务端按公开事实面板校验（未知/重复 ref→400 "Invalid verification request"，未 accepted→409）；迁移 `0010_verification_results` 将 `outcome` 列改为 `results` JSON，whitelist 上移到 API 合同；openapi 对齐测试冻结新形状；Web 按事实逐条核对、不足三条明示不收集；核对答案不回灌 Prompt，修正仍走同 Root 的 correct/追问新 Brief）

把当前一次整体反馈改为三个 `fact_ref` 级独立结果；仍然禁止把用户核对答案倒灌到原解读 Prompt。修正后若要生成新正文，必须走同 Root 的明确 `correct` 流程和新 Brief。

**Step 5: 冻结免费解读范围**

解决页面承诺“八字概览”而正文固定“事业/工作”的漂移：要么产品文案明确为事业概览，要么扩展并通过对应模型评测；不能两边各说一套。

**Verify:**

```bash
MINGLI_TEST_POSTGRES_URL='postgresql+asyncpg://…' \
  uv run --project backend pytest \
  backend/tests/test_reading_idempotency_postgres.py \
  backend/tests/test_readings_api.py \
  backend/tests/test_migrations.py -q
npm --prefix web test -- reading-result.test.tsx profile-form.test.tsx
```

**Commits:**

- `fix: enforce owner scoped reading idempotency`
- `feat: preserve profile roots across immutable versions`
- `feat: capture three independent reading verifications`

## Task 3: 把认证、限流与账户数据权利做成生产能力

**Files:**

- Create: `backend/app/identity/ports.py`
- Create: `backend/app/adapters/redis_otp.py`
- Create: `backend/app/adapters/redis_rate_limit.py`
- Modify: `backend/app/identity/otp.py`
- Modify: `backend/app/identity/service.py`
- Modify: `backend/app/readings/rate_limit.py`
- Modify: `backend/app/api/rate_guard.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`
- Modify: `backend/pyproject.toml`
- Modify: `infra/compose.local.yml`
- Create: `backend/tests/test_redis_otp_store.py`
- Create: `backend/tests/test_redis_rate_limit.py`
- Create: `backend/alembic/versions/0010_account_rights_and_consent.py`
- Modify: `backend/app/identity/models.py`
- Modify: `backend/app/identity/repository.py`
- Modify: `backend/app/api/account.py`
- Modify: `contracts/openapi/v1.yaml`
- Modify: `web/src/components/account-center.tsx`
- Create: `backend/app/accounts/exports.py`
- Create: `backend/app/accounts/deletion.py`

**Steps:**

1. 用端口抽象替换进程内 OTP challenge 与所有 guest/OTP/profile/reading/admin 限流；local/test 可继续用内存 Fake，staging/production 强制 Redis/Tair。
2. Redis key 使用 HMAC 后的 destination/owner 标识，设置 TTL、原子自增/消费、尝试次数和冷却；不得保存明文邮箱、手机号或验证码日志。
3. 写跨两个 API 实例测试：A 发码、B 验证；任一实例重启后 challenge 仍可验证；总限流不能翻倍。
4. Redis 不可用时真实 OTP fail closed；已登录会话和报告读取仍应依赖 PostgreSQL 正常工作。
5. 接入生产邮件 OTP 与手机号 OTP adapter；供应商凭据只从 Secret Manager/运行环境注入。若手机号通道未获批，最终 P0 必须通过 ADR 明确降级，不得只在 UI 灰掉后称完成。
6. 增加设备会话列表、选择性撤销、近期重新验证、手机/邮箱身份绑定；两个 User 的合并必须验证双方控制权并写审计。
7. 增加 consent record、数据导出任务、删除请求和保留期清理；导出文件进入私有 OSS，短时签名 URL，过期自动删除。
8. `/account` 展示真实设备、身份、导出、删除、订单入口，不显示假数据。

**Verify:**

```bash
uv run --project backend pytest \
  backend/tests/test_redis_otp_store.py \
  backend/tests/test_redis_rate_limit.py \
  backend/tests/test_auth.py -q
npm --prefix web test -- account-experience.test.tsx api-session.test.ts
```

Expected: 双实例认证和限流闭合；生产 OTP 不再依赖本机内存；用户能撤销其他设备并发起导出/删除。

**Commits:**

- `feat: share otp and abuse state through redis`
- `feat: add account sessions consent export and deletion`
- `feat: enable gated production otp adapters`

## Task 4: 建立商品、订单、支付、权益与退款事实链

**Files:**

- Create: `backend/alembic/versions/0011_commerce_core.py`
- Create: `backend/app/catalog/models.py`
- Create: `backend/app/catalog/repository.py`
- Create: `backend/app/catalog/service.py`
- Create: `backend/app/billing/models.py`
- Create: `backend/app/billing/repository.py`
- Create: `backend/app/billing/service.py`
- Create: `backend/app/entitlements/models.py`
- Create: `backend/app/entitlements/ledger.py`
- Create: `backend/app/fulfillment/service.py`
- Modify: `backend/app/adapters/payment.py`
- Create: `backend/app/adapters/wechat_payment.py`
- Create: `backend/app/adapters/alipay_payment.py`
- Create: `backend/app/api/catalog.py`
- Create: `backend/app/api/orders.py`
- Create: `backend/app/api/payment_callbacks.py`
- Create: `backend/app/api/refunds.py`
- Modify: `backend/app/api/router.py`
- Modify: `contracts/openapi/v1.yaml`
- Create: `tests/contract/test_commerce_contract.py`
- Create: `backend/tests/test_entitlement_ledger.py`
- Create: `backend/tests/test_payment_inbox.py`
- Create: `backend/tests/test_refund_idempotency.py`

**Domain invariants:**

1. 金额为整数最小币种；订单冻结 Product Version、Offer、Prepared Target 和交付规则。
2. 客户端回跳永远不算到账；只有验签通知或服务端主动查单可确认支付。
3. `channel + transaction_id` 唯一；通知进入 Inbox 幂等处理。
4. 成功支付在同事务追加 Payment Event、Entitlement GRANT 和 Outbox。
5. 生成前 RESERVE；Accepted 与 CONSUME 同一业务收敛；失败 RELEASE；退款 REVERSE。
6. 已支付但模型失败时不扣权益、不改成未支付；用户可继续生成或按政策退款。
7. 追问权限同时校验 User、Root、Subject、商品范围、次数和有效期：八字 7 天 3 次，六爻 72 小时 2 次。
8. 重复回调、查单补偿、并发 Worker、重复退款不能双重授予或双重冲正。

**TDD sequence:**

1. 先用 Fake Payment 写失败合同测试。
2. 落地 Catalog/Order/Payment/Entitlement/Refund 表和约束。
3. 让 Fake 全链路通过，再接渠道 adapter。
4. 每个真实 adapter 只解析/验证渠道事实，领域状态机留在 service。
5. 在沙箱/受控小额环境分别验证签名失败、重复通知、金额不符、主动查单和退款。

**Verify:**

```bash
uv run --project backend pytest \
  backend/tests/test_entitlement_ledger.py \
  backend/tests/test_payment_inbox.py \
  backend/tests/test_refund_idempotency.py \
  tests/contract/test_commerce_contract.py -q
```

**Commits:**

- `feat: add immutable product and order facts`
- `feat: add entitlement ledger and fulfillment state machine`
- `feat: add idempotent payment and refund adapters`

## Task 5: 完成购买体验、有限追问与可操作 Admin

**Files:**

- Modify: `web/src/app/pricing/page.tsx`
- Create: `web/src/app/checkout/[orderId]/page.tsx`
- Create: `web/src/app/account/orders/page.tsx`
- Create: `web/src/components/checkout/checkout-flow.tsx`
- Create: `web/src/components/checkout/payment-status.tsx`
- Create: `web/src/components/checkout/refund-request.tsx`
- Modify: `web/src/components/readings/follow-up-form.tsx`
- Modify: `web/src/lib/api.ts`
- Modify: `contracts/openapi/admin-v1.yaml`
- Modify: `backend/app/api/admin.py`
- Modify: `backend/app/admin/repository.py`
- Modify: `backend/app/admin/service.py`
- Modify: `admin/src/app/users/page.tsx`
- Modify: `admin/src/app/orders/page.tsx`
- Modify: `admin/src/app/refunds/page.tsx`
- Modify: `admin/src/app/readings/page.tsx`
- Modify: `admin/src/app/audit/page.tsx`
- Create: `admin/src/app/reconcile/page.tsx`
- Create: `backend/tests/test_admin_authorization.py`
- Create: `backend/tests/test_admin_refunds.py`
- Create: `admin/src/test/admin-workflows.test.tsx`

**Steps:**

1. 价格页读取服务端 Product Offer，不把渠道能力和价格硬编码成业务事实。
2. 下单前展示 Prepared Target 摘要、价格、交付、追问次数/期限、退款规则与 AI 标识。
3. 桌面支持二维码，移动端使用全屏支付步骤；回跳页始终显示“正在确认”，轮询本后端订单。
4. 支付后进入真实订单/报告状态；未完成权益不得被前端假装已消费。
5. 追问 UI 显示剩余次数和截止时间，越权/过期返回可理解的服务端错误。
6. Admin 接真实用户、订单、支付、退款、解读、审计与对账查询，默认脱敏、分页和筛选。
7. Admin 写操作增加 RBAC、MFA、近期验证、幂等键、二次确认和 append-only 审计。
8. Admin 生产入口只允许私网/VPN/IP allowlist/SSH tunnel；未做到前禁止公网开放。

**Verify:**

```bash
npm --prefix web test
npm --prefix admin run test
uv run --project backend pytest \
  backend/tests/test_admin_authorization.py \
  backend/tests/test_admin_refunds.py -q
```

Expected: 用户能购买、确认到账、查看订单/报告、受限追问和申请退款；运营可查单、退款、重试、对账且每次写操作可审计。

**Commits:**

- `feat: add honest web checkout and order history`
- `feat: enforce purchased follow up limits`
- `feat: connect admin operations to real domain facts`

## Task 6: 关闭 Runtime、模型、Guard 与敏感数据生产 Gate

**Files:**

- Create: `evals/model-profile-v1/cases.jsonl`
- Create: `evals/model-profile-v1/rubric.md`
- Create: `evals/guard-redteam-v1/cases.jsonl`
- Create: `scripts/run_model_evaluation.py`
- Create: `scripts/run_guard_redteam.py`
- Modify: `scripts/task13_trajectory_runner.py`
- Modify: `scripts/verify_frozen_runtime_release.py`
- Modify: `backend/tests/test_narrative_guard.py`
- Modify: `backend/tests/test_reading_orchestrator_recovery.py`
- Create: `backend/tests/test_sensitive_observability.py`
- Create: `docs/operations/RUNTIME_STATE_RECOVERY.md`
- Create: `docs/releases/2026-XX-XX-model-eval-and-guard-redteam.md`
- Modify: `docs/PHASE_0_GATES.md`

**Steps:**

1. 固定盲测集，覆盖 bazi/fortune/liuyao、need-input、事实/证据引用、certainty ceiling、limits 和敏感场景。
2. 固定模型 profile、Prompt/contract digest、温度、token 上限、模型 ID 和价格快照；结果变更必须重新评测。
3. Guard 红队至少覆盖伪造古籍、越界事实、缺引用、提示注入、医疗/法律/投资确定性、敏感信息回显和连续拒绝进入 delayed。
4. 验证 complete 后进程崩溃仍 byte-identical replay，不产生第二份 Accepted。
5. 在隔离 staging 恢复 Runtime state volume，使用旧 Prepared/Accepted token 继续/重放。
6. 扫描 API、浏览器存储、日志、错误平台、指标 labels 和非加密数据库列，禁止 state_token、原始出生资料、完整 Prompt、模型/支付凭据泄漏。
7. 只有固定 profile 通过阈值才允许生产；第二模型也必须走同一门禁，禁止临时自动切换。

**Verify:**

```bash
uv run --project backend python scripts/run_model_evaluation.py --profile model-profile-v1
uv run --project backend python scripts/run_guard_redteam.py --suite guard-redteam-v1
uv run --project backend pytest \
  backend/tests/test_narrative_guard.py \
  backend/tests/test_reading_orchestrator_recovery.py \
  backend/tests/test_sensitive_observability.py -q
```

**Commit:** `test: close model guard runtime and privacy gates`

## Task 7: 让 Worker 可恢复、可退避且不持有长事务

**Files:**

- Create: `backend/alembic/versions/0012_worker_health_and_failures.py`
- Modify: `backend/app/readings/models.py`
- Modify: `backend/worker/main.py`
- Modify: `backend/worker/readings.py`
- Modify: `backend/app/readings/orchestrator.py`
- Modify: `backend/app/adapters/model.py`
- Modify: `backend/app/readings/alerts.py`
- Modify: `backend/tests/test_reading_worker.py`
- Modify: `backend/tests/test_reading_orchestrator_recovery.py`
- Create: `backend/tests/test_worker_failover_postgres.py`

**Steps:**

1. 先写测试证明当前 transaction/row lock 包住 Runtime/Model 外部调用。
2. 重构为短事务 checkpoint：claim+commit → 外部调用 → 重新开事务、校验 fencing token、持久化结果。任何旧 Worker 都不能提交新 lease 的结果。
3. 增加 Worker heartbeat、attempt count、sanitized failure code、next retry、dead-letter/quarantine 和最老队列年龄。
4. 捕获单任务异常并收敛任务状态，不能让一个坏任务杀死整个 Worker 进程。
5. 429/5xx/网络错误尊重 `Retry-After`；采用 bounded exponential backoff + jitter + circuit breaker。
6. tokened Runtime retry 也必须有最大频率、总时限和告警，不能每 5 秒无限热循环。
7. 普通通知/导出/对账 Worker 可多副本；Runtime Worker 保持单活，热备通过数据库 lease/fencing 接管，绝不同时写 state root。

**Verify:**

```bash
MINGLI_TEST_POSTGRES_URL='postgresql+asyncpg://…' \
  uv run --project backend pytest \
  backend/tests/test_reading_worker.py \
  backend/tests/test_reading_orchestrator_recovery.py \
  backend/tests/test_worker_failover_postgres.py -q
```

Expected: 在 Prepare、Model、Complete 三个断点杀进程均可收敛；无重复 Accepted；外部慢调用期间不长期占数据库事务。

**Commit:** `refactor: make reading workers recoverable and bounded`

## Task 8: 密钥轮换、安全闭环与真实可观测性

**Files:**

- Create: `backend/app/security/keyring.py`
- Modify: `backend/app/security/envelope.py`
- Modify: `backend/app/config.py`
- Create: `backend/alembic/versions/0013_key_versioning.py`
- Modify: `backend/app/identity/models.py`
- Modify: `backend/app/identity/repository.py`
- Create: `scripts/rotate_content_keys.py`
- Modify: `scripts/check_production_secrets.py`
- Create: `backend/tests/test_key_rotation.py`
- Create: `backend/app/metrics.py`
- Modify: `backend/app/observability.py`
- Modify: `backend/app/readings/alerts.py`
- Modify: `backend/app/api/health.py`
- Create: `backend/app/api/internal_health.py`
- Modify: `backend/app/database.py`
- Create: `backend/tests/test_metrics_privacy.py`
- Create: `backend/tests/test_database_pool_config.py`
- Create: `docs/operations/ON_CALL.md`
- Create: `docs/operations/SECRET_ROTATION.md`

**Steps:**

1. 内容密钥采用一个 active write key + 多个 read-only old keys；逐批重加密，旧数据在轮换期间仍可读。
2. 身份 HMAC 增加版本；查询尝试允许的当前/旧 key，命中旧版后惰性迁移。不能直接换环境变量导致老账号失联。
3. 关闭既有凭据泄露 P0：轮换 DB、旧 API/Bot、会话和云 AccessKey；旧值失效；查最后使用；主账号开 MFA；RAM 最小权限。不得用已泄露密钥做连通测试。
4. Secret Manager 注入只读、最小权限凭据；启动检查不打印 secret。
5. 暴露低基数、无 PII 指标：HTTP、OTP、队列、Worker heartbeat、Reading 状态、模型错误/延迟/成本、Runtime retry、支付/退款/对账。
6. 禁止邮箱、手机号、出生资料、Prompt、token、完整动态 URL 进入 metric label、日志或错误事件。
7. Readiness 至少验证 PostgreSQL、Redis、Alembic head；Worker heartbeat 单独检查。Liveness 不依赖下游。
8. 设置数据库 pool size、overflow、connect/statement timeout、application name；总连接预算按 API/Worker 实例数计算。
9. 四类业务告警必须有真实通知路由和演练：runtime_unknown、delayed、Guard rejection、model cost/error；再加登录异常、支付回调失败、队列年龄、备份失败和 SLO burn rate。

**Verify:** 密钥轮换前后旧数据和旧账号均可读；secret scan 无未处置结果；报警在 5 分钟内送达并由值班人确认；指标无敏感 label。

**Commits:**

- `feat: support versioned content and identity keys`
- `feat: add privacy safe metrics health and alerting`
- `security: close leaked credential incident`

## Task 9: 建立强制 PostgreSQL CI、不可变制品与分阶段部署

**Files:**

- Create after remote approval: `.github/workflows/ci.yml`
- Create after remote approval: `.github/workflows/release.yml`
- Create after remote approval: `.github/workflows/deploy-staging.yml`
- Create after remote approval: `.github/workflows/deploy-production.yml`
- Create: `.github/dependabot.yml`
- Modify: `Makefile`
- Modify: `backend/pyproject.toml`
- Modify: `web/package.json`
- Modify: `admin/package.json`
- Create: `scripts/ops/verify_artifact.py`
- Create: `scripts/ops/smoke_release.py`
- Create: `docs/operations/DEPLOY_ROLLBACK.md`

**Steps:**

1. 用户授权后创建/连接私有 Git remote；保护 `main`，要求 PR、review 和必需 checks。当前没有 remote，不能假装 CI 已存在。
2. CI 启动 PostgreSQL 16 和 Redis 7，运行全部 backend/contract/Web/Admin tests、lint、typecheck、build、Alembic 空库升级和 PG 并发测试；关键 suite 零 skip。
3. 加 secret scan、依赖/SBOM、容器和许可证扫描；release 输出不可变 artifact digest 与 provenance。
4. 同一 artifact 从 staging 晋级 production，服务器不重新拼装另一份源码/依赖。
5. 数据库迁移采用 expand/contract，应用 N/N-1 兼容；禁止把“整库自动 downgrade”当生产回滚默认方案。
6. Staging 自动部署；production 需要人工批准、canary、健康与业务 smoke 后再加权。
7. 回滚在 15 分钟内切回旧 artifact；数据库使用向前兼容修复或明确恢复步骤。

**Verify:** PR 无法绕过 PG、admin、secret 和 artifact checks；部署记录可从 commit → artifact digest → staging → production 完整追溯。

**Commit:** `ci: enforce postgres release and deployment gates`

## Task 10: 落地最小双可用区生产基础设施

**Files:**

- Create: `docs/operations/EXISTING_CLOUD_INVENTORY.md`
- Create: `docs/adr/0012-existing-ecs-role.md`（原计划的 0010 已被占用，改为 0012）
- Create: `infra/terraform/production/versions.tf`
- Create: `infra/terraform/production/network.tf`
- Create: `infra/terraform/production/alb.tf`
- Create: `infra/terraform/production/compute.tf`
- Create: `infra/terraform/production/rds.tf`
- Create: `infra/terraform/production/redis.tf`
- Create: `infra/terraform/production/storage.tf`
- Create: `infra/terraform/production/observability.tf`
- Create: `infra/terraform/production/variables.tf`
- Create: `infra/terraform/production/outputs.tf`
- Create: `infra/nginx/fateradar-origin.conf`
- Create: `infra/systemd/fateradar-api.service`
- Create: `infra/systemd/fateradar-web.service`
- Create: `infra/systemd/fateradar-worker.service`
- Create: `infra/systemd/fateradar-admin.service`
- Create: `infra/fateradar-production.env.example`
- Modify: `infra/docker/backend.Dockerfile`
- Modify: `infra/docker/web.Dockerfile`
- Create: `docs/operations/PRODUCTION_ARCHITECTURE.md`

**Steps:**

1. 对现有 ECS 做只读资产盘点：实例 ID、地域/可用区、VPC/vSwitch、规格、CPU/内存、系统盘/数据盘与加密、EIP/带宽、计费到期/续费、快照、安全组、RAM 角色、当前端口、服务和备份；以云控制台/实例元数据为权威，明确纠正 nmem 冲突记录。
2. 用 ADR 固定现有 ECS 的复用角色。默认不原地重装或直接把测试机改成生产：若故障域、规格、镜像和容量合格，可在有回滚证据后复用为 ECS-A 或 Runtime 单活节点；否则保留为 staging/运维跳板，并写明成本与退出条件。
3. 只对“现有资产之外的缺口”输出 Terraform/OpenTofu plan 和增量月成本估算；用户批准后才创建付费资源。现有实例纳入 IaC 时先评估 import，不重复创建同名/同用途 ECS。
4. 建或复用 VPC，并补齐两个可用区/交换机、安全组和最小 RAM 角色；禁止为了套模板无依据迁移现有实例。
5. 建多可用区 ALB，后端至少两个独立故障域中的 Web/API 副本；若现有 ECS 合格，它可以计作其中一个。健康检查命中真实 Web/API readiness，不能打 Nginx 自己永远 200 的假 `/healthz`。
6. Web/API 节点无状态；Cookie/session 事实在 PostgreSQL，OTP/限流在 Tair。
7. 建 RDS PostgreSQL 高可用/多可用区，开启自动备份、日志备份/PITR、加密和最小白名单；迁移现有 ECS 本机 PostgreSQL 前必须先做双份备份与恢复验证。
8. 建 Tair/Redis 高可用多可用区；它不保存唯一订单、权益或报告事实。
9. 建私有 OSS，启用版本控制、服务端加密、生命周期和访问日志；生产数据不复制到测试。
10. Runtime 使用固定非 root UID、签名 release、单活持久状态盘和 fenced warm standby；先完成恢复演练，再允许自动接管。
11. Admin 只走私网/VPN/IP allowlist/SSH tunnel；不和公网 C 端入口共享匿名访问面。
12. 把 `fateradar-tls.conf` 的静态/API 503 占位替换为真实 origin 配置；API/Web 仍只监听内网/回环。

**Verify:**

- 资产清单能从阿里云事实证明现有 ECS 的规格、故障域、到期日和最终角色；没有重复采购或未审阅的原地重装。
- Terraform plan 无未审阅公网入口和明文 secret。
- 杀掉 ECS-A，持续探针 ≤ 2 分钟恢复且会话/订单不丢。
- ALB 不向不 ready 实例发流量。
- API/Web 端口不能从公网直接访问。
- Admin 公网无法访问。

**Commit:** `infra: define multi az production topology`

## Task 11: 建立可证明的备份、恢复与灾难演练

**Files:**

- Create: `docs/operations/BACKUP_RESTORE.md`
- Create: `docs/operations/DISASTER_RECOVERY.md`
- Create: `scripts/ops/verify_restore.py`
- Create: `scripts/ops/verify_runtime_state_restore.py`
- Modify: `infra/TEST_SERVER_RUNBOOK.md`
- Modify: `docs/PHASE_0_GATES.md`

**Steps:**

1. 定义 PostgreSQL 自动备份、日志/PITR、保留期、加密、跨账号/跨地域副本和备份失败告警。
2. Runtime state 每 5 分钟以内形成可恢复点；备份必须与 key versions、release digest 和 state-root identity 关联。
3. OSS 打开版本控制；重要导出/制品按需要做跨账号或跨地域隔离复制。
4. 在全新隔离环境恢复 PostgreSQL、Runtime state 和允许的旧 key versions。
5. 验证 Alembic head、表行数/约束、敏感数据可解密、Prepared 可续跑、Accepted 原字节重放。
6. 记录真实 RPO/RTO，而不是只勾“备份存在”。上线前至少完整演练一次；上线后每季度恢复演练。
7. 备份与生产账号/区域解耦；同一磁盘上的 pre-migration dump 只算临时回滚材料，不算灾备。

**Verify:** 空白环境恢复达到 PostgreSQL 与 Runtime state 的 RPO ≤ 5 分钟、RTO ≤ 60 分钟；演练证据可定位且不含秘密。

**Commit:** `ops: prove database and runtime disaster recovery`

## Task 12: 补齐真实浏览器、无障碍、性能、SEO 与 PWA 基础

**Files:**

- Create: `web/src/app/sitemap.ts`
- Modify: `web/src/app/manifest.ts`
- Modify: `web/src/app/layout.tsx`
- Modify: `web/src/app/globals.css`
- Modify: `web/src/components/readings/liuyao-hexagram.module.css`
- Modify: `web/src/components/readings/time-layer-tabs.module.css`
- Create: `web/public/icon-192.png`
- Create: `web/public/icon-512.png`
- Create: `web/public/og-default.png`
- Create: `web/e2e/core-journeys.spec.ts`
- Create: `web/e2e/accessibility.spec.ts`
- Create: `web/e2e/payment.spec.ts`
- Create: `web/lighthouse-budget.json`
- Modify: `web/package.json`

**Steps:**

1. 增加真实 Playwright E2E：游客建档→Accepted→登录认领→跨设备查看；支付沙箱→到账→报告→追问→退款；过期会话恢复。
2. 增加 axe serious/critical 零违规、键盘、焦点、200% 缩放、屏幕阅读器手工清单和 360/768/1024/1440 视觉验收。
3. 修复 `--ink-500` 在米白背景的小字对比度；状态不能只靠颜色。
4. 增加页面级错误摘要；保留就地错误和首错聚焦。
5. 把全局 `0.01ms` 动画粗暴覆盖改为组件级 reduced-motion 行为。
6. 对约 203MB CJK 字体资源做子集/加载策略和真实网络测量，不靠构建目录大小猜单页传输量。
7. 补 sitemap、canonical、OpenGraph、结构化数据、manifest icons；sitemap 只含公共页面。
8. 私人路由继续强制 noindex/no-store；Service Worker 不缓存私人 API/HTML。
9. 添加匿名示例结果，但只用脱敏固定夹具，不能伪装真实用户或动态算法结果。

**Verify:**

```bash
npm --prefix web run test
npm --prefix web run e2e
npm --prefix web run lighthouse
npm --prefix web run build
```

Expected: Core Web Vitals 预算、a11y、响应式、sitemap/OG/PWA 合同全绿。

**Commit:** `feat: harden web accessibility performance and discovery`

## Task 13: 生产 Gate、灰度与正式完成验收

**Files:**

- Modify: `backend/app/config.py`
- Modify: `infra/nginx/fateradar-tls.conf`
- Modify: `docs/PHASE_0_GATES.md`
- Modify: `README.md`
- Create: `docs/releases/2026-XX-XX-production-canary.md`
- Create: `docs/releases/2026-XX-XX-general-availability.md`

**Preconditions:**

1. ICP、公安联网、隐私/条款/AI 标识、经营许可判断有书面证据。
2. 支付商户、短信/邮件通道、模型数据处理和正式域名/TLS Gate 通过。
3. 已知泄露凭据全部轮换，旧值失效，会话失效，访问审计完成。
4. Task 0–12 机器门禁全绿；没有未处置 P0/P1 缺陷。

**Steps:**

1. 先关闭测试公网 18080：阿里云安全组、UFW、Nginx 三处全部删除并留证。
2. 在 production-like staging 跑完整回归、PG 并发、真实 Runtime/模型、支付沙箱/小额、备份恢复、告警、压测和节点故障演练。
3. 只有 Gate 证据通过后，才修改 `config.py` 的无条件 real-traffic 拒绝；保留双重 fail-closed（environment + explicit traffic flag + alert/secret/runtime readiness）。
4. 以 allowlist/小比例 ALB 权重开启 canary；顺序建议：内部账号 → 10 个受控用户 → 10% → 50% → 100%。
5. 任一阈值触发立即回滚：5xx/SLO burn、支付不一致、重复权益、Accepted 不一致、敏感泄漏、队列年龄或告警失联。
6. 实测回滚 ≤ 15 分钟；实测数据库/Runtime 恢复达到 RPO/RTO。
7. Canary 连续稳定至少 7 天；GA 后继续观察完整 30 天 SLO，首月结束做成本、投诉、质量和事故复盘。
8. 最后更新 README、Gate 台账和 GA release；只有此时才把项目状态写为“完整高可用网站已上线”。

**Final verification:**

```bash
make check
npm --prefix web run e2e
npm --prefix admin run test
uv run --project backend python scripts/run_model_evaluation.py --profile model-profile-v1
uv run --project backend python scripts/run_guard_redteam.py --suite guard-redteam-v1
uv run --project backend python scripts/ops/smoke_release.py --environment production
uv run --project backend python scripts/ops/verify_restore.py --evidence-dir '<redacted-path>'
```

Expected: 所有 Gate 有可复验证据；生产流量开关不再靠口头批准；回滚和恢复均达到目标。

**Commit:** `release: approve fateradar production general availability`

---

## 6. 每个 Task 的统一执行纪律

1. 每个 Task 开始前在独立 worktree 创建更细的 2–5 分钟步骤清单。
2. 先写失败测试，再写最小实现，再跑聚焦测试和全门禁。
3. 数据库变更坚持 expand/contract；每个 migration 都有 PostgreSQL upgrade 测试。
4. 不把当前用户或其他线程的未提交改动塞进任务提交。
5. 每个外部副作用（remote、云资源、商户、DNS、Secret Manager、真实流量）执行前再次确认权限和成本。
6. 每个阶段只记录原始证据；计划勾选、服务进程 active、页面能打开都不等于验收完成。
7. 任何新 P0/P1 数据损坏、重复扣款、串号、错误排盘、空 Accepted 或敏感泄漏立即停止放量。

## 7. 官方云能力参考（已有资源盘点及增购前复核）

- [阿里云 ALB：多可用区与健康检查](https://help.aliyun.com/zh/slb/application-load-balancer/what-is-alb)
- [阿里云 RDS PostgreSQL：自动备份与按时间点恢复](https://help.aliyun.com/zh/rds/apsaradb-rds-for-postgresql/back-up-an-apsaradb-rds-for-postgresql-instance)
- [阿里云 RDS PostgreSQL：多可用区恢复](https://help.aliyun.com/zh/rds/apsaradb-rds-for-postgresql/restore-the-data-of-an-apsaradb-rds-for-postgresql-instance-across-regions)
- [阿里云 Tair：高可用与多可用区容灾](https://help.aliyun.com/zh/redis/product-overview/disaster-recovery)
- [阿里云 OSS：版本控制与跨区域复制](https://help.aliyun.com/zh/oss/user-guide/data-protection-overview)
- [阿里云 CloudMonitor：可用性监控与报警](https://help.aliyun.com/zh/cms/cloudmonitor-1-0/user-guide/create-an-availability-monitoring-task)

## 8. 执行交接

Plan complete and saved to `docs/plans/2026-08-12-complete-production-ha-website.md`.

执行方式：

1. **Subagent-Driven（本会话）**：从 Task 0 开始，每个 Task 使用独立 worktree/子代理，完成后审查再进入下一项。
2. **Parallel Session（独立会话）**：新会话加载 `executing-plans`，按里程碑批量执行，并在 M0–M5 检查点回到主会话复核。

服务器已经买好并在用，不再把“购买首台服务器”列为任务。执行第一步是并行完成现有 ECS 的只读资产盘点，以及让 Task 0 全绿并关闭 PostgreSQL 幂等并发漏洞；任何原地重装、用途切换或增购高可用资源都另行确认。
