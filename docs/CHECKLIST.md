# FateRadar / mingli_web — 权威进度 Checklist

> **本文是仓库里唯一的进度与门禁清单。**  
> 更新日期：2026-08-12  
> 状态总判：`联调主链路已通` · `production blocked` · `real traffic disabled`  
> 当前施工窗口：**Chart-first / 青囊对齐（§10）** — 先盘后断；Dogfood 深读链路（§7）保留为副路径  
> 用户本轮明确：备案与支付暂不推进，但不等于这些 Gate 已通过；产品主路径要对齐「青囊式细盘工作台」而非仅 Accepted 长文。

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
| 代码权威 | Mac mini `/Volumes/Lexar/code/mingli_web` | **唯一带完整 `.git` 的工作树**；private remote `origin` → `https://github.com/1960697431/mingli_web.git` |
| MacBook 同步副本 | `~/sync/code/mingli_web` | Syncthing 文件镜像，**不要**在此 `git init`；提交请在 Lexar 上做 |
| 基线 HEAD | `47e18f8` | dogfood 功能提交；其后为 checklist 断点注记 |
| Alembic head | `0009_owner_grants` | 含 admin staff + dogfood capability grants |
| 测试服主机 | `fateradar-prod` / `106.14.10.235:18080` | SSH 别名；**联调机不是 production** |
| 测试服 current（已记录） | `ba4c8f6` | Chart-first Phase 1；`local` + **smtp OTP** + one-shot Runtime + deepseek + dogfood gates on；旧 `0586730` 保留可回滚 |
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

- [x] 指明**权威 Git 仓库**位置：Mac mini `/Volumes/Lexar/code/mingli_web`（`main`，private `origin` → `https://github.com/1960697431/mingli_web.git`）；MacBook `~/sync/code/mingli_web` 仅为文件同步副本，禁止在此 `git init`
- [x] 根门禁全绿：`make check` 在 Lexar 权威仓通过（2026-08-12；backend ruff/mypy/pytest + web test/lint/typecheck/build）
- [ ] PostgreSQL 上跑通当前因缺 `MINGLI_TEST_POSTGRES_URL` 而 skip 的并发/恢复测试
- [ ] 确认 `0001→0008` 空库升级与旧库升级；应用可启动
- [ ] 仓库噪音策略：`.qoder` 等是资产还是生成物（不得默默膨胀）
- [ ] admin 测试纳入根 `make check`（当前 Makefile 仅 admin-typecheck 可选，未进 check）

### B. 核心算法与产品正确性

- [ ] **同步确定性排盘 API**（只 `prepare` + public fact 投影；不建 Job、不调模型、不核销权益）— **主承载见 §10 Chart-first**
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
| Dogfood 三轨 accepted | `docs/releases/evidence/2026-08-12-dogfood-three-track/` |
| Chart-first Phase 0 fact inventory | `docs/releases/evidence/2026-08-12-chart-fact-inventory/` |
| Chart-first Phase 1 本地同步链路 | `docs/releases/evidence/2026-08-12-chart-sync-local/` |
| Chart-first Phase 1 测试服同步链路 | `docs/releases/evidence/2026-08-12-chart-sync-server/` |

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
- [x] private GitHub remote + 基线 push — `origin` `https://github.com/1960697431/mingli_web.git`，`main@9ab5736`
- [x] migration：`owner_capability_grants`（owner user + capability 开关）— `0009_owner_grants`
- [x] Reading：`start_today` / `week` / `liuyao` 前校验 grant；Preview 不拦（`MINGLI_DOGFOOD_ENTITLEMENT_GATES_ENABLED`）
- [x] 日熔断：`MINGLI_DOGFOOD_DAILY_READING_LIMIT`（默认 10）、`MINGLI_DOGFOOD_DAILY_PAID_READING_LIMIT`（默认 6）
- [x] `scripts/dogfood_grant.py` / `scripts/dogfood_delete_user.py`（audit 日志）
- [x] 测试期文案（首页/定价/隐私：无 TLS、无真支付、数据可删将清）
- [x] 功能提交 + 本地 `make check` 绿 — `47e18f8`
- [x] tag → 按 `infra/TEST_SERVER_RUNBOOK.md` 打 tar 部署 — tag `dogfood-20260812-0586730`，current=`0586730`，旧 `7444601` 保留
- [x] `test.env`：`smtp` + `one-shot` + `deepseek` + 日限额 + entitlement gates on
- [x] 服务器 grant `1960697431@qq.com` → today/week/liuyao
- [x] 三条轨迹脚本 accepted（API+Worker）— 证据 `docs/releases/evidence/2026-08-12-dogfood-three-track/`
- [ ] 浏览器三条手点 accepted（UI 手验仍建议补一次）
- [ ] 按邮箱删除脚本演练
- [ ] current 回滚演练（至少指回旧 release 一次）

### 7.3 本窗口明确不做

真微信/支付宝、用户兑码页、Admin 权益 UI、Redis 挑战存储生产化、Guard 红队全套、质量盲测全套、Brief 缓存、系统化档案语义全量、`MINGLI_REAL_TRAFFIC_ENABLED=true`。  
（**同步排盘 API** 已从 dogfood「不做」中移出，改由 §10 Chart-first 窗口承接。）

---

## 8. 推荐施工顺序

### 8.1 已基本完成：Dogfood 深读链路（§7）

文档收口 → entitlement/gates → GitHub → 部署 `0586730` → grant → 三轨 API accepted。  
剩余：浏览器手点、delete 演练、回滚演练（不阻塞 §10）。

### 8.2 当前优先：Chart-first / 青囊对齐（§10）

1. **产品合同锁定**（先盘后断；不抄品牌资产）  
2. **Phase 0 探测**：Runtime prepare 实际投影出哪些 public facts（密度上限）  
3. **Phase 1 MVP**：同步排盘 API + 免费细盘页（四柱+明细+已有 workspace）  
4. **Phase 2**：结果页信息架构改为盘主文辅；深度解读降为 CTA  
5. **Phase 3**：判读层（旺衰/格局/用神/大运流年）按 fact 增量展示 + 分层解锁  
6. 档案语义（真太阳时/农历等）与 §10 表单高级项并联，不另开大叙事  

当前停在 **Phase 1 测试服已部署并通过机器验收，用户浏览器手点与 2 秒级体感仍待验收**；Phase 2–4 未获追加授权，不施工。

### 8.3 其后（原路线）

1. A 可信基线剩余项  
2. B 评测 / Guard 红队 / fact_panel 复验  
3. C Redis / 恢复 / 告警  
4. 外部 Gate / 支付后再 D  

---

## 9. 变更记录

| 日期 | 变更 |
|------|------|
| 2026-08-12 | 初版：合并原 HANDOFF、PHASE_0_GATES、plans/releases 叙事日志中的有效断点与门禁；删除工作日志类 md，证据目录保留 |
| 2026-08-12 | 权威 Git 定位到 Mac mini Lexar；`make check` 全绿；修 401 身份刷新单飞；MacBook 误 init 的空 `.git` 已删 |
| 2026-08-12 | 锁定内部 dogfood 窗口合同（§7）；推荐顺序改为 dogfood 优先（§8） |
| 2026-08-12 | dogfood 最小集落地：`0009_owner_grants`、付费向 grant 闸、日熔断、ops 脚本、测试期文案；`make check` 绿 |
| 2026-08-12 | 授权后创建 private GitHub `1960697431/mingli_web` 并 push |
| 2026-08-12 | 授权部署 dogfood：`0586730` current；smtp/one-shot/deepseek/gates；三轨 API accepted |
| 2026-08-12 | **产品转向 Chart-first / 青囊对齐（§10）**：主路径改为同步细盘工作台；异步解读为副路径；禁止新开 plans 叙事文件，进度只改本文 |
| 2026-08-12 | §10 Phase 0 库存冻结、Phase 1 本地代码验收完成：同步 API + 同页细盘 + 现有 preview CTA；`make check` 绿；测试服手验、生产单写者接线与 p95 验收仍未完成 |
| 2026-08-12 | 授权部署 Chart-first Phase 1：测试服 current=`ba4c8f6`；公网/二次重启/真实同步机器验收通过；单样本 `3005.09ms`，2 秒级手点与 p95 仍未通过 |

---

## 10. Chart-first / 青囊对齐窗口（2026-08-12 锁定方案）

> **目标体验（对标青囊信息架构，不抄资产）：**  
> 录入 → **即时细盘工作台** →（可选）登录/权益解锁判读 →（可选）异步 AI/Accepted 深读。  
> **不是** Staging/Production Ready。  
> 冻结合同仍有效：Runtime 完整 5.1；浏览器不排盘；Fake 不冒充生产；进度只改本文。

### 10.1 产品合同（已定）

| 项 | 决定 |
|----|------|
| 主路径 | **先盘后断**：同步确定性细盘为默认成功体验 |
| 副路径 | 现有 dogfood 异步 Reading（preview/today/week/liuyao）保留为「深度解读」 |
| 对标对象 | 青囊 `/bazi` 信息架构与交互层级（细盘密度、分层解锁） |
| 禁止 | 抄青囊品牌/文案/皮肤/插画；客户端 JS 排盘；裁剪 5.1；为像而先做同盘灯/积分皮肤 |
| 与 §7 关系 | Dogfood 不回滚；§10 不依赖浏览器手点三轨完成 |
| 文档 | **不**新增 `docs/plans/*`；勾选与断点只改本文；证据进 `docs/releases/evidence/` |

### 10.2 现状差距（相对青囊免费层）

| 能力 | 青囊（观察） | 本仓现状 | 差距 |
|------|--------------|----------|------|
| 入口 CTA | 开启推演（免费）即时出盘 | `/app/bazi` → 选已确认档案 → 同步出盘 | 本地 MVP 已改正；测试服手验未做 |
| 同步排盘 API | 前端算/或登录 engine | 已有 `POST /api/v1/charts/bazi/sync` + 结构化 input 续排 | 生产单写者接线、缓存与 p95 验收未做 |
| 四柱主舞台 | 四列干支+十神 | `/app/bazi` 同页复用可点选 `BaziChart` / workspace | Phase 1 已闭合 |
| 明细矩阵 | 藏干/纳音/空亡/地势/自坐/神煞 | 已展示藏干、十神、纳音、五行库存、局部神煞；四项诚实标未投影 | 空亡/地势/自坐/三宫等待 Runtime 新投影 |
| 图示 Tab | 命局/干支/宫位/六亲/五行 | 五行计数已产品化；无关系图，三宫未投影 | Phase 2–3 |
| 高级起盘 | 真太阳时、夜子时 | Profile 有字段；表单未当主路径 | 与档案语义并联 |
| 分层解锁 | 细盘免费 / 判读登录 / AI 积分 | grant 只挡 today/week/liuyao | 可复用 entitlement |
| 深读 | 积分 AI | 细盘 CTA 已接现有事业 preview → Accepted/Guard 链路 | Phase 1 已闭合；原 entitlement 不拆 |

### 10.3 架构原则（实现时不得违反）

1. **Sync Chart** = 一次 Runtime `prepare` + `project_public_fact_panel`；**不**建 Web Reading Root/Job；**不**调 Model；**不**核销权益。Runtime 自身按 5.1 协议建立的隔离 prepare 状态不属于 Web Reading。
2. 若 prepare 返回 `need_input`，产品必须收集结构化字段，由服务端在同一隔离 state root 内带私有 token 续 prepare（浏览器只持 opaque handle；禁止无 token 自动重放）。
3. 浏览器只渲染服务端 public facts；缺字段显示「暂无/未投影」，**禁止**前端发明十神/大运。  
4. 深度解读继续走现有 Orchestrator；从细盘页 CTA 带上 `profile_version_id` / chart handle。  
5. OpenAPI + JSON Schema + 后端测试 + web 合同测试同步改。
6. **窄例外只限 local/test Phase 1**：API 可为每次 sync 使用独立、可销毁、`0700` 临时 state root；不得写 Worker 的持久 state root。`need_input` handle / 幂等结果 TTL 为 10 分钟，过期清理 lease 与 token；进程重启须用户显式重排，不宣称 HA。
7. `production` 对上述临时-root 工厂 fail closed；接入单活 Runtime / fenced hot standby 与 Brief 缓存并完成性能决策前，不部署本功能。本地单样本 `933.77ms`、测试服单样本 `3005.09ms` 均不等于 p95≤500ms 验收；测试服样本也未达到 2 秒级目标。

### 10.4 分期与勾选

**Phase 0 — 探测（先于产品 UI 大改）**

- [x] 用 one-shot Runtime 对标准档案跑 `compile_bazi_prepare` + prepare，导出 **脱敏** fact 种类清单（ref/kind/display 形态）
- [x] 对照青囊免费层字段：四柱、十神、藏干、纳音、空亡、地势、自坐、神煞、三宫、五行 — 标记 **已有 / 可映射 / 5.1 未投影**
- [x] 结论写入证据目录 `docs/releases/evidence/2026-08-12-chart-fact-inventory/`（无 token、无生日原文）
- [x] 据此冻结 MVP 展示范围（只承诺「已有投影」，不承诺青囊全字段 Day1）

Phase 0 冻结结论（机器清单与字段依据见上述 evidence）：

| 青囊字段 | 5.1 状态 | Phase 1 决定 |
|----------|----------|--------------|
| 四柱、十神、藏干、纳音 | **已有** | 进入四柱主舞台 / 明细矩阵 |
| 神煞 | **可映射**：`shensha_auxiliary.calculated_items` | 只显 Runtime 已匹配项，不扩写断语 |
| 五行 | **可映射**：`element_inventory` | 只显出现次数与原 scope，不据此断旺衰 / 用神 |
| 空亡、地势、自坐、三宫 | **5.1 未投影** | 诚实显示未投影；浏览器不推导 |

MVP 另展示已投影的 `day_master` / `month_command` 摘要并复用可点选 `BaziChart`；`luck_cycles` 与 `interpretive_candidates` 虽已投影，分别留给 Phase 3 时间层 / 判读层，本阶段不抢跑。

**Phase 1 — MVP（可给熟人看盘）**

- [x] API：`POST /api/v1/charts/bazi/sync` + `POST /api/v1/charts/bazi/sync/{chart_handle}/input`
  - 输入：已冻结为仅已确认 `profile_version_id`；不接受一次性 birth payload
  - 输出：`fact_panel`（public）+ 可选 `chart_view` 摘要；无 `accepted_copy`  
  - 鉴权：Guest 或 User + CSRF；**不**走 paid grant  
  - 限流：独立 write limiter（防刷 Runtime）  
- [x] 服务：复用 `compile_bazi_prepare` + Runtime adapter；**禁止**入队 Worker
- [x] Web：`/app/bazi` 已改为「选档案 → 同步看盘」；同页展示抬头 + 四柱卡 + 明细矩阵 + 现有 `BaziChart` workspace
- [x] CTA：「进入事业深度解读」→ 现有 `startPreviewReading` 异步链路
- [x] 测试：API 合同（无 Web Reading/Job、Model 与 entitlement 调用即失败）；web 组件测；`make check`（backend 541 passed / 90 skipped；web 262 passed；ruff/mypy/lint/typecheck/build 绿）
- [ ] 测试服部署后手点：2 秒级出盘体感（已部署并完成机器同步；单样本 `3005.09ms`，待用户浏览器手点且当前未达 2 秒）

Phase 1 当前结论：**本地代码验收与测试服机器验收完成，用户浏览器体感验收未完成**。本地单样本为 `933.77ms`；测试服真实 one-shot 单次同步为 `200/ready`、14 类 public facts、`3005.09ms`，Web Reading Root / Job / GenerationAttempt / AcceptedCopy 均为 0；证据见 `docs/releases/evidence/2026-08-12-chart-sync-local/` 与 `docs/releases/evidence/2026-08-12-chart-sync-server/`。production 单写者接线与 p95 仍待决，本阶段不宣布 Staging / Production Ready，也不进入 Phase 2–4。

**Phase 2 — 信息架构（盘主文辅）**

- [ ] `reading-result`：首屏盘面工作台，Accepted 文稿下沉  
- [ ] 细盘页与解读结果页共享盘面组件（DRY）  
- [ ] Preview 文案 vs dimension 对齐（挂钩 §3-B）  

**Phase 3 — 判读层（登录/权益）**

- [ ] 按 Phase 0 库存展示旺衰/格局/用神等（有则显、无则诚实空）  
- [ ] 大运/流年层：仅当 public facts 含时间层数据；`chart-workspace` 已有 decadal/yearly 位  
- [ ] 解锁：复用 `owner_capability_grants` 或新 capability（如 `bazi_judgment`）；未解锁 CTA 登录/申请开通  
- [ ] AI 深读继续走 Reading + grant，不与 sync chart 混事务  

**Phase 4 — 档案语义并联（不挡 MVP）**

- [ ] 真太阳时：用户确认，禁止静默估算（§3-B）  
- [ ] 农历/闰月/不确定时辰  
- [ ] 表单高级项与 Profile confirm 字段对齐  

### 10.5 建议任务切片（给执行会话）

> 执行时用 TDD：红 → 绿 → 提交；每切片可独立 revert。

1. **Fact inventory 脚本**（只读 Runtime，写 evidence）  
2. **Sync API 失败测试** → 最小 handler → 绿 → commit  
3. **OpenAPI/Schema** 对齐 → contract test  
4. **Web API client + `/app/bazi` 同步流** → 组件测 → commit  
5. **盘面展示增强**（在 inventory 允许范围内加行列）→ commit  
6. **深度解读 CTA 接线** → 手动/ e2e 冒烟  
7. **Reading 结果页改序**（Phase 2）  
8. **部署测试服 + 手验清单**  

### 10.6 明确不做（本窗口）

- 青囊同盘灯、三色皮肤体系、积分商城  
- 合盘页完整对标（可列 P1 以后）  
- 客户端排盘库  
- 为细盘引入第二套命理核心  
- 未完成 Phase 0 就承诺「十神神煞全有」  

### 10.7 成功标准（MVP 可宣布）

- 选已确认档案 → 同步 API → 页面展示至少：**四柱 + 日主/月令类摘要 + 可点选工作台**（字段以 inventory 为准）  
- 网络面板确认：**无** model 调用、**无** reading job 或 job 不进入 generating  
- 从细盘一键进入现有 preview 深读仍可用  
- `make check` 绿；CHECKLIST §10.4 Phase 1 勾完  

机器验收已证明同步接口不建 Reading/Job；深读副路径仍由既有合同与回归覆盖，`make check` 已绿。测试服浏览器手点与 2 秒级体感仍未通过，因此只宣布 Phase 1 **测试服机器验收**，不宣布完整环境验收。

---
