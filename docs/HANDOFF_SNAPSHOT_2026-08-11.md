# 施工交接快照（2026-08-11）

> 本文是给后续施工会话的准确断点说明。只描述已验证的现状与下一步，不替代任何权威合同。与合同冲突时，以下列合同为准：`docs/MINGLI_V51_WEB_INTEGRATION.md`、`docs/plans/2026-08-09-mingli-v51-web-integration.md`、`docs/adr/`、`docs/PHASE_0_GATES.md`。
>
> 最新代码断点：`main @ 0525eb1`（`docs(release): point Task13 trajectory env to 6ec1578 deploy`）。测试服务器 `fateradar-prod` current：`6ec1578`。
>
> 本轮用户明确：**暂时不管备案和支付**；不把外部合规 Gate 当本轮 blocker。

## 一、已完成（代码在 `main`）

- Phase 0/1 网站地基、5.1 集成 Task 1–12 代码与测试在 `main`。
- **Task 8 已闭环**：`native-full` 五件套归档 `docs/releases/evidence/2026-08-09-native-full/`，verifier 通过（1584/0）。
- **真实 Runtime startup 已通过**（本机 + 测试服 one-shot）。
- **真实模型联调已通过**：本机与 `fateradar-prod` 经 DashScope DeepSeek `deepseek-v4-flash` 出现 accepted。
- **紫微 UI-only 计划 Task 0–5/7 完成**（Task 6 跳过：无公开紫微事实）：边界测试、chart-workspace 展示模型、建档口径复述、工作台壳、八字可点选、结论优先、release note。关键提交：`ce72d37` `a882b9c` `4ee83d5` `0275345` `1c26f09` `e07f8b3` `6cc9e45`。
- **Task 13 前置完成**：可复跑脚本 + 本地 13 点轨迹 runner（`e251839`）。
- **测试服已推到 `6ec1578`**：`3446061 → e251839 → 1c26f09 → 3cd39ed → b104245 → 6ec1578`；API/Web/Nginx/18080 健康全绿。环境：`local` + OTP `fake` + Runtime `one-shot` + Model `deepseek`。记录：`docs/releases/2026-08-11-test-server-deploy-6ec1578.md`。
- **Task 13 产品真轨迹 round-4 5/5 accepted**（测试服，不是 production）：
  - `b104245`：`candidate_reference_closer` 补 fact/evidence 引用闭包，解 Guard `scope_mismatch`。
  - `6ec1578`：follow-up prepare 带最近 Accepted `state_token`，`transition=null`，解 `terminal_stopped`。
  - 结果：preview / today / week / liuyao / followup 全 accepted。
  - 证据：`docs/releases/2026-08-11-task13-server-trajectory.md` + `docs/releases/evidence/2026-08-11-task13-server-trajectory/run-4-followup-fix/`。
- **UI 本轮改动范围**：`/app/profile/new`（birth-basis-summary）与结果页（可点八字盘/侧栏详情/结论优先）。**首页未动**。用户若报「UI 没变」，先核 current 版本号、抓 `127.0.0.1:18080` HTML 组件标记、对比旧 release、强制刷新。

## 二、未闭环（本轮仍推进，但不含备案/支付）

### 2.1 Task 9–10 正式准入
- 固定 Model Profile 质量评测 / 盲测未齐。
- Secret Manager 与密钥轮换演练未齐（当前 0600 env 只是联调口径）。

### 2.2 Task 13 剩余放量门槛
- 产品 5 轨 accepted 已有测试服证据；**不等于 Task 13 合同全闭环**。
- 仍缺：Guard 连续拒绝 → delayed 的受控红队集、complete 后 byte-identical replay、state volume backup/restore、生产告警演练。
- 历史缺陷仍记：早期轨迹曾见 `fact_panel` 透出原始出生 datetime，后续需单独修与复验。
- 测试服仍是 `local + fake OTP` 联调环境，不是隔离 staging / production。

### 2.3 本轮明确跳过
- ICP / 公安联网 / 支付商户 / 经营性许可等外部合规与支付通道。

`production blocked / real traffic disabled`（即使跳过备案支付，仍缺评测、红队、密钥托管/告警/恢复等放量 Gate）。

## 三、下一步（严格顺序，跳过备案支付）

1. 固定模型质量评测脚手架 + 最小 Guard 红队集（含 delayed 路径受控留证）。
2. 视需要修 `fact_panel` 原始出生 datetime 泄漏，并补敏感扫描复验。
3. Secret Manager / 告警 / state volume 恢复演练。
4. 以上齐前不放真实业务流量。

## 四、关键事实与禁止项

- Mac mini `native-full` 是唯一 Runtime Gate；不得启动 VZ/Rosetta/QEMU/`linux-certify`。
- 不得裁剪 13 Provider / 55 古籍 / 1328 evidence。
- `state_token`、出生资料、Prompt、支付密钥不得进客户端或日志。
- 仓库不得保存密码/私钥/API Key/商户证书/真实 OTP。
- 测试服务器 `accepted` 只证明联调通路，不等于 production 放量。
- Alembic head：`0007_api_idem_verify`；历史回滚点保留 `c462934`。
- 仓库无 Git remote；部署走独立运维入口，不要假设 `git push` 会发布。

## 五、工作区未提交（不算进度）

截至本文更新时，工作区另有未提交草稿，**未计入当前断点**：

- `design-system/mingli-web/`（Master + home page override）
- `web/src/components/motion-primitives.tsx`、`web/src/components/home-motion.tsx`
- 首页/壳层相关未提交改动：`web/src/app/page.tsx`、`home.module.css`、`globals.css`，以及若干 `*.module.css` / shell / task-card / time-archive 组件

这些是首页动效 / 设计系统草稿，与 Task 13 轨迹无关，后续单独验收再合。
