# Admin 平台只读、数据权利与 CMS 审计命令切片

日期：2026-08-14（Asia/Shanghai）  
范围：Admin 设置、健康、订单/支付/退款只读聚合、数据权利队列、客服案件申请与执行入口；本证据只覆盖当前工作树的本地 API/UI 合同，不宣称生产部署、真实支付渠道、合规演练或用户最终批准已经完成。

## 本轮补齐

- 新增 `GET /api/v1/admin/settings`，只返回环境、Cookie 安全开关、OTP/runtime 适配器、会话时长、权益闸门、真实流量和告警开关等非秘密运行事实；不返回数据库连接、身份密钥或其他凭据。
- 新增 `/health` 页面，读取既有 `/api/v1/health/ready`，展示 readiness、版本、环境和依赖状态；上游不可用时保持只读结构和明确 unavailable 文案。
- 新增 `GET /api/v1/admin/commerce/orders`、`/payments`、`/refunds`，按 `finance`/`ops`/`superadmin` 读取安全的本地聚合事实；不返回支付尝试哈希、原始通知或其他敏感载荷。
- 新增 `/orders`、`/payments`、`/refunds` 页面，真实读取上述接口并明确这是只读运营面。
- 新增 `/data-rights` 页面，读取待处理账户关闭队列；`ops`/`superadmin` 可执行已有隐私关闭 API，执行成功后刷新队列。
- 隐私关闭成功路径补写 `privacy.closure.execute` Admin 审计事件，并以回归测试确认已执行关闭会留下目标和状态的安全审计元数据。
- 新增 `support_cases` 持久化与 `GET/POST /api/v1/admin/support-cases`；finance/ops 可读，support/superadmin 可提交带对象、类型、摘要和操作原因的案件申请，创建写入 `support_case.created` 审计；不在客服页直接执行补偿、退款或报告状态修改。
- 新增 `referral_appeals`、风险信号和独立审批事实及 `GET/POST /api/v1/admin/appeals`、风险信号与决定接口；support/superadmin 可提交申诉，ops/superadmin 可记录不改变奖励状态的风险信号，finance/superadmin 的纠错必须由两位不同员工审批，完成后只追加正式权益账本撤销事件并写审计，不删除报告或保存原始 IP/设备/地址值。
- 新增 `/users`、`/users/[id]`、`/subjects`、`/subjects/[id]` 及对应 Admin API；用户页显示脱敏身份、同意、设备会话和 Subject 计数，Subject 页只显示版本/授权元数据。
- 用户与 Subject 响应明确排除密码哈希、设备 token 哈希、ProfileVersion 加密正文、nonce、密钥标识和 fingerprint 等私有材料；支持角色可读取业务资料，但没有页面写命令。
- `/entitlements` 已读取最近追加式账本事件；`finance`/`ops`/`superadmin` 可通过现有 CSRF/RBAC/原因/来源编号写 API 追加发放、补偿或撤回，成功后刷新列表，support 不显示调整命令。
- `/referrals` 与 `/referrals/[id]` 已读取 CampaignVersion、邀请码、临时归因和奖励预留的真实计数/详情；仅 `ops`/`superadmin` 可读，不返回 `visitor_key_hash`，没有虚构申诉或活动写命令。
- `/staff` 已支持 superadmin 创建本地员工账号、停用/恢复、角色调整和密码重置；创建要求原因、CSRF 和有效邮箱，初始密码只写入哈希，响应/审计不含密码，重复邮箱返回 409；当前没有伪造邮件邀请投递。
- 六个 `/cms/**` 路由已读取 `ContentRevisionRecord` 的最新版本索引；按页面、每日、工具、知识、FAQ 和政策前缀筛选，列表不批量返回正文，support 角色不获得 CMS editor 读取权限。
- CMS 索引行现在可按 content key 读取真实修订历史和正文；历史面板已接入草稿编辑、预览、定时、发布、撤回、归档和恢复命令。所有写命令强制填写操作原因，服务端追加 `AdminAuditEvent`，只记录 content key、locale、版本、状态、目标和原因等 allowlist 元数据，不记录正文。
- `/reading-jobs` 已读取 `ReadingJobRecord` 与 `ReadingVersion` 的安全调度元数据；support 可读、finance 被拒绝，响应排除出生输入、horizon/object、output contract、lease 和模型 payload。
- `/charts` 与 `/readings` 已读取 `ReadingVersion` 的能力、版本、状态和维度数量；`/readings/[id]` 进一步展示安全的任务数、核对事件数和文档存在性；support/ops/superadmin 可读，finance 被拒绝，响应排除出生输入、horizon/object、owner 和报告正文。
- `/verifications` 已合并 `ReadingVerification`、`ClaimVerificationEvent` 和 `ReportFeedback` 的只读元数据；区分整体核对、Claim 核对和报告反馈，响应不含用户 note，finance 被拒绝。
- `/runtime` 已读取真实 `RuntimeRelease` 登记的名称、版本、source commit、协议和 production-ready 标记；ops/superadmin 可读，响应和页面不返回 manifest/image digest、Provider 凭据或虚构健康状态。
- `/model-profiles` 已读取真实 `GenerationAttempt.model_receipt` 的 Model/Guard 安全元数据；仅 ops/superadmin 可读，页面不返回 request fingerprint、profile snapshot digest、token 用量、价格明细、出生输入或原始 provider payload。
- `/capabilities` 已读取 V5.1 的 13 条版本化能力策略；`bazi`、`fortune`、`liuyao` 标为 `PUBLIC`，其余 Provider 模块标为 `INTERNAL_TEST`，并展示产品动作映射。该页面只读，不提供能力发布/暂停命令；响应明确标记 `runtime_health=unverified`、`production_ready=false`，不把策略登记冒充 Runtime 健康或生产准入。

## 可复现检查

```text
uv run --project backend pytest \
  backend/tests/test_admin_settings.py \
  backend/tests/test_admin_commerce_read.py \
  backend/tests/test_data_rights.py \
  backend/tests/test_admin_support_cases.py \
  backend/tests/test_admin_appeals.py \
  backend/tests/test_admin_identity_read.py \
  backend/tests/test_admin_entitlements.py \
  backend/tests/test_admin_referrals_read.py \
  backend/tests/test_admin_staff.py \
  backend/tests/test_content_service.py \
  backend/tests/test_admin_reading_jobs.py \
  backend/tests/test_admin_readings.py \
  backend/tests/test_admin_verifications.py \
  backend/tests/test_admin_runtime.py \
  backend/tests/test_admin_model_profiles.py \
  backend/tests/test_admin_capabilities.py \
  backend/tests/test_openapi_alignment.py -q

pnpm exec vitest run \
  src/components/admin-settings-surface.test.tsx \
  src/components/admin-health-surface.test.tsx \
  src/components/admin-commerce-surface.test.tsx \
  src/components/admin-data-rights-surface.test.tsx \
  src/components/admin-support-cases-surface.test.tsx \
  src/components/admin-appeals-surface.test.tsx \
  src/components/admin-identity-surface.test.tsx \
  src/components/admin-entitlements-surface.test.tsx \
  src/components/admin-referrals-surface.test.tsx \
  src/components/admin-staff-surface.test.tsx \
  src/components/admin-cms-surface.test.tsx \
  src/components/admin-reading-jobs-surface.test.tsx \
  src/components/admin-readings-surface.test.tsx \
  src/components/admin-reading-detail-surface.test.tsx \
  src/components/admin-verifications-surface.test.tsx \
  src/components/admin-runtime-surface.test.tsx \
  src/components/admin-model-profiles-surface.test.tsx \
  src/components/admin-capabilities-surface.test.tsx \
  src/test/admin-route-catalog.test.ts

make backend-check
make admin-check
```

本轮全局结果：Backend `686 passed, 92 skipped`，Ruff 与 mypy `126 source files` 通过；Web `54 files / 390 tests` 通过；Admin `33 files / 112 tests`，lint、typecheck、production build 通过。`0025_referral_appeals` 从空 SQLite 升级到 head 且 `alembic check` 无新操作，Admin 四视口 route matrix `16 passed`、accessibility `20 passed`；后端未启动时 `/capabilities`、`/support-cases`、`/appeals` 与 CMS 路由保持明确 unavailable 状态。

## 边界

P3-003、P3-005、P3-006、P3-007、P3-008、P3-010、P8-006、P9-002、P9-004、P9-005 与 P12-008 仍保持 `IN_PROGRESS`：客服案件的完整处理/补偿闭环、邀请活动完整写服务、确定性拒绝/未来限制/申诉运营和生产接线、CMS 全内容类型与内容投影/生产发布接线、盘面/报告详情/核对/见相完整聚合、Model/Provider/Guard 的生产配置与运营闭环、员工邮件邀请与完整角色运营、用户/Subject 写服务、真实支付与渠道对账、供应商投递、Provider/Worker 生产接线、生产秘密治理、媒体授权、备份恢复、告警容量和外部准入尚未完成。当前申诉切片只覆盖可解释申诉、风险信号记录和双审批纠错，不等于完整 P8-006。能力策略页只证明静态只读映射；Runtime 健康、能力发布、生产准入、真实 Provider/Worker 与 Guard 红队仍未完成。P4-006/P4-007 也不由本证据覆盖。
