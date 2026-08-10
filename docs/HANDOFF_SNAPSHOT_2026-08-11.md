# 施工交接快照（2026-08-11）

> 本文是给后续施工会话的准确断点说明。只描述已验证的现状与下一步，不替代任何权威合同。与合同冲突时，以下列合同为准：`docs/MINGLI_V51_WEB_INTEGRATION.md`、`docs/plans/2026-08-09-mingli-v51-web-integration.md`、`docs/adr/`、`docs/PHASE_0_GATES.md`。
>
> 最新代码断点：`main @ 3af1f16`（`docs: test server deploy record 1c26f09`）。测试服务器 `fateradar-prod` current：`1c26f09`。
>
> 本轮用户明确：**暂时不管备案和支付**；不把外部合规 Gate 当本轮 blocker。

## 一、已完成（代码在 `main`）

- Phase 0/1 网站地基、5.1 集成 Task 1–12 代码与测试在 `main`。
- **Task 8 已闭环**：`native-full` 五件套归档 `docs/releases/evidence/2026-08-09-native-full/`，verifier 通过（1584/0）。
- **真实 Runtime startup 已通过**（本机 + 测试服 one-shot）。
- **真实模型联调已通过**：本机与 `fateradar-prod` 经 DashScope DeepSeek `deepseek-v4-flash` 出现 accepted。
- **紫微 UI-only 计划 Task 0–5/7 完成**（Task 6 跳过：无公开紫微事实）：边界测试、chart-workspace 展示模型、建档口径复述、工作台壳、八字可点选、结论优先、release note。关键提交：`ce72d37` `a882b9c` `4ee83d5` `0275345` `1c26f09`。
- **Task 13 前置完成**：可复跑脚本 + 本地 13 点轨迹 runner（`e251839`）。
- **测试服部署完成**：`3446061 → e251839 → 1c26f09`；API/Web/Nginx/18080 健康全绿。环境：`local` + OTP `fake` + Runtime `one-shot` + Model `deepseek`。记录：`docs/releases/2026-08-11-test-server-deploy-1c26f09.md`。

## 二、未闭环（本轮仍推进，但不含备案/支付）

### 2.1 Task 9–10 正式准入
- 固定 Model Profile 质量评测 / 盲测未齐。
- Secret Manager 与密钥轮换演练未齐（当前 0600 env 只是联调口径）。

### 2.2 Task 13 真实轨迹
- 隔离/测试服**完整**真实轨迹证据仍在补：fortune 日/周、六爻、follow-up、Guard 连续拒绝 delayed、complete 后 byte-identical replay。
- Guard 红队、state volume backup/restore 实战、生产告警四类演练未齐。

### 2.3 本轮明确跳过
- ICP / 公安联网 / 支付商户 / 经营性许可等外部合规与支付通道。

`real staging 未完成 / production blocked / real traffic disabled`（即使跳过备案支付，仍缺 Task 13 真轨迹与运维/评测 Gate）。

## 三、下一步（严格顺序，跳过备案支付）

1. 服务器真实轨迹已 partial 归档（多数 delayed=scope_mismatch）；下一步修模型/prompt/评测以稳住 accepted，并补 follow-up/replay 证据。
2. 补固定模型质量评测脚手架与 Guard 红队最小集。
3. 密钥托管/告警/恢复演练。
4. 以上齐前不放真实业务流量。

## 四、关键事实与禁止项

- Mac mini `native-full` 是唯一 Runtime Gate；不得启动 VZ/Rosetta/QEMU/`linux-certify`。
- 不得裁剪 13 Provider / 55 古籍 / 1328 evidence。
- `state_token`、出生资料、Prompt、支付密钥不得进客户端或日志。
- 仓库不得保存密码/私钥/API Key/商户证书/真实 OTP。
- 测试服务器 `accepted` 只证明联调通路，不等于 production 放量。
