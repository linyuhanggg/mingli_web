# FateRadar / mingli_web — 权威进度 Checklist

> **本文是仓库里唯一的进度与门禁清单。**  
> 更新日期：2026-08-12  
> 状态总判：`联调主链路已通` · `production blocked` · `real traffic disabled`  
> 当前施工窗口：**内部 Dogfood（§7）** — 仅你自己；三轨 browser accepted 前不宣布 ready  
> 用户本轮明确：备案与支付暂不推进，但不等于这些 Gate 已通过。

冲突时以**冻结合同**为准，不以本文措辞覆盖合同。本文只回答三件事：现在做到哪、还差什么、证据在哪。

---

## 0. 文档体系（只保留这些）

| 角色 | 路径 | 可否当进度 |
|------|------|------------|
| **进度 / 门禁 / 下一步** | **本文 `docs/CHECKLIST.md`（唯一）** | 是 |
| 共同语言 | `CONTEXT.md` | 否（术语合同） |
| 视觉 | `DESIGN.md` + `design-system/mingli-web/` | 否 |
| 产品方向 | `docs/PRODUCT_DIRECTION.md` | 否 |
| 商业与技术蓝图 | `docs/PRODUCT_BLUEPRINT_WEB_IOS_V2.md` | 否（含 P0 验收 15 条） |
| 算法接入合同 | `docs/MINGLI_V51_WEB_INTEGRATION.md` | 否 |
| 架构决策 | `docs/adr/0001`–`0010` | 否 |
| 机器证据 | `docs/releases/evidence/**` | 否（只读证据，不写叙事日志） |

**禁止再新增：** `HANDOFF_SNAPSHOT_*`、`docs/plans/*`、`docs/releases/*.md` 施工日志。  
施工会话只更新本文对应勾选与「断点」一节；新证据放进 `docs/releases/evidence/<日期>-<主题>/`。

---

## 1. 断点事实（可复验）

| 项 | 当前值 | 备注 |
|----|--------|------|
| 代码权威 | Mac mini `/Volumes/Lexar/code/mingli_web` | **唯一带完整 `.git` 的工作树**；无 remote |
| MacBook 同步副本 | `~/sync/code/mingli_web` | Syncthing 文件镜像，**不要**在此 `git init`；提交请在 Lexar 上做 |
| 基线 HEAD | `8c0c66e` | `feat(platform): 增加管理后台与认证感知命理解读体验` |
| Alembic head | `0009_owner_grants` | 含 admin staff + dogfood capability grants |
| 测试服主机 | `fateradar-prod` / `106.14.10.235:18080` | SSH 别名；**联调机不是 production** |
| 测试服 current（已记录） | `6ec1578` | `local` + fake OTP + one-shot Runtime + deepseek |
| 测试服环境 | 非隔离 staging | 不可当生产放量证据 |
| Runtime 制品 | mingli-master **5.1 完整** | 13 Provider / 55 古籍 / 1328 evidence / 217 文件 manifest |
| Runtime Gate | Mac mini `native-full` **已通过** | 证据见 §6 |

| 模型联调 | DashScope `deepseek-v4-flash` | 本机 + 测试服曾出 `accepted` |
| 产品曝光 | 仅 `bazi` / `fortune` / `liuyao` | 不裁剪 Runtime 制品 |
| 支付 | `FakePaymentGateway` only | 永不产生到账事实 |
| 生产流量 | `MINGLI_REAL_TRAFFIC_ENABLED` fail-closed | 未闭环前禁止放量 |

冻结 Runtime 身份（接入合同摘要，变更必须新 release + 回归）：

- Source commit：`494ce0bba174a77800daf9b9c38ce9c9166d9a94`
- Manifest SHA-256：`e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68`
- Protocol：`mingli-portable-interface-v2`

---

## 2. 已完成（代码 / 联调）

### 2.1 地基与合同

- [x] 网站优先 + 模块化单体（FastAPI + Next + Worker + PostgreSQL）
- [x] 共同语言 / ADR / OpenAPI v1 / JSON Schema（Command/Result/Candidate/Output）
- [x] Guest Session、OTP（fake/local）、Device Session Cookie、CSRF、同源 `/api`
- [x] Profile draft → confirm（不可变版本方向已建）
- [x] Reading API：preview / today / week / liuyao / result / follow-up / verification（整体反馈）
- [x] Reading Orchestrator：prepare → 单模型 → Guard → complete → Accepted
- [x] Runtime Adapter（fake + one-shot 真路径）+ 启动验签门禁
- [x] Model Adapter（fake + deepseek）数据边界测试
- [x] Narrative Guard + `candidate_reference_closer`（解 scope_mismatch 联调）
- [x] `public_fact_panel` 出站脱敏骨架
- [x] 告警骨架（默认关；real traffic 仍 fail-closed）
- [x] Admin 独立应用壳 + staff 鉴权地基（`0008`）；订单/退款 KPI 多为 stub
- [x] 紫微 **UI-only** 参考（不引入紫微算法 / 不整仓替换）
- [x] 结果页结论优先、八字可点选工作台（首页动效草稿不算进度）

### 2.2 Runtime / 模型 / 轨迹证据

- [x] Mac mini `native-full`：1584/0，verifier 通过  
  证据：`docs/releases/evidence/2026-08-09-native-full/`
- [x] 本机 / 测试服真实 Runtime startup（one-shot）
- [x] Task13 测试服产品 5 轨 **accepted**（preview / today / week / liuyao / followup）  
  证据：`docs/releases/evidence/2026-08-11-task13-server-trajectory/run-4-followup-fix/`  
  脚本：`scripts/run_server_task13_trajectory.py` 等  
  **不等于** Task13 合同全闭环，**不等于** production ready

### 2.3 明确未做 / 不做（本阶段）

- [ ] 真实微信支付 / 支付宝 / 权益账本落库核销
- [ ] 备案通过页脚编号、公安联网、经营性许可书面闭环
- [ ] 微服务 / K8s / 多 region 双活
- [ ] Agent loop / 模型自选术法 / 客户端伪造排盘
- [ ] 裁剪 13 Provider 或古籍包

---

## 3. 未完成 Checklist（按优先级）

状态标记：`[ ]` 未做 · `[~]` 部分 · `[x]` 完成  
改状态时同时改 §1 断点与日期。

### A. 可信基线（先做）

- [x] 指明**权威 Git 仓库**位置：Mac mini `/Volumes/Lexar/code/mingli_web`（`main`，无 remote）；MacBook `~/sync/code/mingli_web` 仅为文件同步副本，禁止在此 `git init`
- [x] 根门禁全绿：`make check` 在 Lexar 权威仓通过（2026-08-12；backend ruff/mypy/pytest + web test/lint/typecheck/build）
- [ ] PostgreSQL 上跑通当前因缺 `MINGLI_TEST_POSTGRES_URL` 而 skip 的并发/恢复测试
- [ ] 确认 `0001→0008` 空库升级与旧库升级；应用可启动
- [ ] 仓库噪音策略：`.qoder` 等是资产还是生成物（不得默默膨胀）
- [ ] admin 测试纳入根 `make check`（当前 Makefile 仅 admin-typecheck 可选，未进 check）

### B. 核心算法与产品正确性

- [ ] **同步确定性排盘 API**（只 `prepare` + public fact 投影；不建 Job、不调模型、不核销权益）
- [ ] Brief 缓存（键：Profile Version + capability + dimension + horizon + Runtime digest）
- [ ] 档案语义闭合：农历/闰月/不确定时辰；经纬度失败强制修正；真太阳时用户确认；禁止静默估算
- [ ] 免费 Preview **文案 vs dimension** 对齐（概览 vs 事业）
- [ ] Verification：3 条 **fact_ref 级**独立核对（非仅整单反馈）
- [ ] Reading idempotency：owner 作用域 partial unique index（修 PG NULL 唯一约束坑）
- [ ] Profile 编辑 = 同 Root 下追加 Version（验收编辑路径）
- [ ] `fact_panel` 敏感扫描复验（历史曾透出 raw birth datetime）
- [ ] 固定 Model Profile **质量评测 / 盲测**脚手架与最小样例集
- [ ] Guard **红队集**（含连续拒绝 → delayed；零证据只允许「证据不足」类表述）
- [ ] complete 后 **byte-identical** replay 证明
- [ ] closer 补全率监控（防「乱 claim + 补引用」伪通过）

### C. 生产能力（可不接商户）

- [ ] Redis/Tair：OTP challenge + 限流（替换进程内内存；production SMTP 前置条件）
- [ ] 账户数据权利：导出 / 删除 / 撤设备（生产能力，非占位）
- [ ] Catalog / Order / Entitlement **领域模型预埋**（Fake 支付仍 fail-closed）
- [ ] Admin 接真实解读任务队列；支付/退款可继续 stub 直到商户 Gate
- [ ] Runtime **单活 writer + state volume** 备份/恢复演练
- [ ] 生产告警路由演练：`runtime_unknown` / `delayed` / guard 拒绝 / model cost

### D. 商业与高可用（依赖外部授权 / 采购）

- [ ] 商品目录、下单、支付通知验签、查单补偿、退款、对账
- [ ] 权益占用 → Accepted 核销；退款冲正
- [ ] 多故障域入口（ALB + 双副本无状态 Web/API）；RDS HA；Redis HA
- [ ] CI/CD、密钥托管与轮换、canary / 回滚演练
- [ ] 压测对齐 SLO（见蓝图；解读异步不计入非模型 API p95）

### E. 外部 Gate（书面证据；无证据不得勾选通过）

| Gate | 状态 | 通过证据要求 | 代码期处理 |
|------|------|--------------|------------|
| 运营主体与经营范围 | 待确认 | 证照与许可复核 | 不写假备案 |
| 域名 ICP | 申请中（曾提交） | 管局通过记录 | 未通过仅临时预览 |
| 公安联网备案 | 待确认 | 备案号 + 页脚真链 | 不展示虚构编号 |
| 微信支付商户 | 待确认 | JSAPI/H5/Native 小额实测 | 仅 Fake |
| 支付宝商户 | 待确认 | 手机/电脑网站支付实测 | 仅 Fake |
| 短信通道与模板 | 待确认 | 签名/模板/防轰炸 | 手机 OTP Fake |
| 邮件通道与模板 | 待确认 | 发信域/退信/DPA | 邮箱 OTP Fake；SMTP 生产拒绝至 Redis |
| 模型供应商与数据位置 | 联调已通 / 正式准入待确认 | DPA、保存期、训练退出、预算、盲测、故障策略 | 联调 deepseek 可开；放量受限 |
| mingli-master 5.1 完整发布物 | 本机已核验 / 生产安装待确认 | 固定 manifest + describe + 13/55/1328 | 仅签名 release root |
| Mac mini native-full | **已通过** | §6 证据目录 | 唯一 Runtime Gate |
| Runtime 状态与恢复 | 待确认 | token/state 卷备份恢复实测 | 未过不放流量 |
| 单模型成稿正式准入 | 联调已通 / 正式待确认 | 盲测 + Guard 红队 | Fake 不成正式质量 |
| 密钥托管与轮换 | 待确认 | Secret Manager + 演练 | 仅运行时注入 |
| 生产监控与告警 | 待确认 | 四类告警配置与触发演练 | 骨架 ≠ 生产告警 |

---

## 4. 目标状态机（勿混用）

| 状态 | 含义 | 当前 |
|------|------|------|
| Feature Complete | P0 旅程 + 支付 + 账户权利 + 后台有真码与测试 | 否 |
| Staging Ready | 独立 staging、真 OTP/Runtime/模型/支付沙箱 | 否（仅有联调机） |
| Production Ready | 安全/合规/密钥/备份/告警/恢复/压测全绿 | 否 |
| Canary | 小范围真用户与小额订单 | 否 |
| GA | 双故障域 + 生产支付运营 + 观测稳定 | 否 |

测试服 5/5 accepted **只证明联调通路**，最高对应「算法主链路联调通过」，**不**提升上表状态。

---

## 5. 硬规则（摘录，详见合同）

Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。

`slots` 和 `max_slots` 表示 signed runner 的加权调度额度，不是操作系统 PID 数量上限。

1. 核心算、代码编排、单模型写、Guard 在 complete 前守门；**无 Agent**。  
2. Runtime 永远完整 5.1；P0 allowlist 只控产品曝光。  
3. 浏览器只展示 Accepted Copy / 公开 fact 投影；**不**客户端排盘。  
4. `state_token`、出生原文、Prompt、密钥 **不进**客户端与日志。  
5. Fake Payment / Fake Model / Fake Runtime **永不**冒充生产事实。  
6. 仓库不存密码、私钥、API Key、商户证书、真实 OTP。  
7. 生产 Nginx 未准入前 API 保持不可服务；`real traffic` 默认关。

---

## 6. 证据索引（机器产物，保留）

| 主题 | 路径 |
|------|------|
| native-full 五件套 | `docs/releases/evidence/2026-08-09-native-full/` |
| Task13 本地 prep | `docs/releases/evidence/2026-08-11-task13-prep/` |
| Task13 测试服轨迹 | `docs/releases/evidence/2026-08-11-task13-server-trajectory/` |
| Task13 round-4（5/5） | `.../run-4-followup-fix/` |

验签脚本：`scripts/verify_frozen_runtime_release.py`  
密钥检查（不打印密钥）：`scripts/check_production_secrets.py`

---

## 7. Dogfood 窗口（2026-08-12 锁定；施工中）

> **不是** Staging Ready / Production Ready。  
> 总目标：公网联调机上**仅你自己**先跑通内部 dogfood；三条付费向解读均 browser `accepted` 前不宣布 ready。

### 7.1 已锁定合同（grilling）

| 项 | 决定 |
|----|------|
| 入口 | 裸公网 `http://106.14.10.235:18080`（无 TLS；联调机） |
| 登录 | **SMTP 邮箱 OTP only**（不留固定码 `246810` 公网后门） |
| 支付 | **无真支付**；产品文案诚实写「测试期 / 支付未接入」 |
| 付费向开通 | **运营脚本后门**（无用户兑码页、无 Admin 权益 UI） |
| 权益形态 | `today` / `week` / `liuyao` **能力开关、不限次**；**Preview 免 grant** |
| 验收 | today + week + liuyao：**轨迹脚本绿 + 浏览器各手点到 `accepted`**；**无降级宣布** |
| 范围 | 放行最小集 + **只修挡路 bug**；不系统做 §3-B 前半 / 红队 / Redis 生产化 |
| 数据 | 允许真实生辰；**按人可删 + 窗口结束默认全清**；文案写明测试期与无 TLS |
| 用户 | **第一周仅你**；拉人是全绿后的下一闸 |
| Git | **先文档收口提交，再 dogfood 功能提交**；private GitHub + tag/sha；`.qoder` 不进包 |
| 运行合同 | 测试服 `one-shot` + `deepseek` + `smtp`；日熔断 env 可配，默认 **总 10 / 付费向 6**（含 preview 计入总顶） |
| 脚本 | `scripts/dogfood_*.py` 进仓；**仅测试服 SSH** + release venv + `/etc/fateradar/test.env` |
| 回滚 | GitHub tag 锚点；服务器 `releases/<sha>`；失败 **current 指回旧目录**；DB **只加法前进、不 down** |

### 7.2 Dogfood 工程勾选

- [x] 文档收口提交（本文 + 删旧叙事 md + README 指向）— `cbe95d9`
- [ ] private GitHub remote + 基线 push（**需授权**）
- [x] migration：`owner_capability_grants`（owner user + capability 开关）— `0009_owner_grants`
- [x] Reading：`start_today` / `week` / `liuyao` 前校验 grant；Preview 不拦（`MINGLI_DOGFOOD_ENTITLEMENT_GATES_ENABLED`）
- [x] 日熔断：`MINGLI_DOGFOOD_DAILY_READING_LIMIT`（默认 10）、`MINGLI_DOGFOOD_DAILY_PAID_READING_LIMIT`（默认 6）
- [x] `scripts/dogfood_grant.py` / `scripts/dogfood_delete_user.py`（audit 日志）
- [x] 测试期文案（首页/定价/隐私：无 TLS、无真支付、数据可删将清）
- [x] 功能实现本地 `make check` 绿（提交后回写 sha）
- [ ] tag → 按 `infra/TEST_SERVER_RUNBOOK.md` 打 tar 部署（**需授权**）
- [ ] `test.env`：`smtp` + `one-shot` + `deepseek` + 日限额 + entitlement gates on
- [ ] 服务器 grant 你的邮箱
- [ ] 三条轨迹脚本 accepted
- [ ] 浏览器三条手点 accepted
- [ ] 按邮箱删除脚本演练
- [ ] current 回滚演练（至少指回旧 release 一次）

### 7.3 本窗口明确不做

真微信/支付宝、用户兑码页、Admin 权益 UI、Redis 挑战存储生产化、Guard 红队全套、质量盲测全套、同步排盘 API、Brief 缓存、系统化档案语义、`MINGLI_REAL_TRAFFIC_ENABLED=true`。

---

## 8. 推荐施工顺序

### 8.1 当前窗口（Dogfood，优先）

1. 文档收口提交  
2. entitlement + 校验 + 日熔断 + dogfood 脚本 + 文案  
3. 测试与 `make check`  
4. （授权后）GitHub → 部署 → grant → 三轨验收  

### 8.2 Dogfood 全绿之后（原路线，仍有效）

1. **A 可信基线**（PG 并发测试、迁移升级确认、admin 进 check）  
2. **B 同步排盘 + 档案语义 + 文案/核对/idempotency**  
3. **B 评测 + Guard 红队 + fact_panel 复验**  
4. **C Redis OTP/限流 + Runtime 恢复演练 + 告警**  
5. 外部 Gate / 支付授权后再做 **D**  
6. 再决策是否拉 1–3 名熟人 dogfood（新闸，不默认打开）

---

## 9. 变更记录

| 日期 | 变更 |
|------|------|
| 2026-08-12 | 初版：合并原 HANDOFF、PHASE_0_GATES、plans/releases 叙事日志中的有效断点与门禁；删除工作日志类 md，证据目录保留 |
| 2026-08-12 | 权威 Git 定位到 Mac mini Lexar；`make check` 全绿；修 401 身份刷新单飞；MacBook 误 init 的空 `.git` 已删 |
| 2026-08-12 | 锁定内部 dogfood 窗口合同（§7）；推荐顺序改为 dogfood 优先（§8） |
