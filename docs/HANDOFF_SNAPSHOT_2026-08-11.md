# 施工交接快照（2026-08-11）

> 本文是给后续施工会话的准确断点说明。只描述已验证的现状与下一步，不替代任何权威合同。与合同冲突时，以下列合同为准：`docs/MINGLI_V51_WEB_INTEGRATION.md`、`docs/plans/2026-08-09-mingli-v51-web-integration.md`、`docs/adr/`、`docs/PHASE_0_GATES.md`。
>
> 最新代码断点：`main @ 3446061`（`fix(web): send career dimension for free bazi preview`）。

## 一、已完成（代码在 `main`）

- Phase 0/1 网站地基、5.1 集成 Task 1–7 / 9–12 代码与测试仍在 `main`。
- **Task 8 已闭环**：`native-full` 五件套已归档到 `docs/releases/evidence/2026-08-09-native-full/`，并经 `verify_local_full.py` 独立通过。
  - `targets=126 modules=93 tests=1584 failed_modules=0 elapsed=434.13s`
  - `prepared_inputs_sha256=a4e83f3c225b928a9d9ea8b9ffc56448cb283ed23dd8b4e9f0b7e3831fa77807`
  - source commit `494ce0bba174a77800daf9b9c38ce9c9166d9a94`
  - release manifest SHA-256 `e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68`
- **真实 Runtime startup 已通过**：本机私有 217 文件 release root + CPython 3.14.6 venv 上，`build_runtime_startup_gate(...).startup()` 返回 `OneShotMingliRuntimeAdapter`；describe 为 13/13，digest 与 capability shape 匹配冻结值。
- **真实模型冒烟已通过（本机 + 测试服务器）**：
  - P0 模型默认走阿里云百炼兼容模式：`https://dashscope.aliyuncs.com/compatible-mode/v1`
  - 冻结模型 `deepseek-v4-flash` / profile `deepseek-v4-flash-p0-v1`
  - 本机：Runtime prepare + 真实 generate 返回 Candidate blocks
  - 测试服务器 `fateradar-prod`：Worker 接真实 Runtime + 真实 DashScope DeepSeek；E2E 已出现 `accepted` 且 generation_attempt 无 guard_errors
  - 相关提交：`cb01d65`、`aff23aa`、`5b5ceb7`、`3d065b4`、`9623ee3`
  - 证据记录：`docs/releases/2026-08-11-dashscope-deepseek-real-model.md`
- **产品侧后续增量已合入**：
  - 邮箱优先 onboarding、设备会话控制、解读历史
  - 除首页外 UI 修正
  - 八字盘面工作区 / 档案入口：`6f77658`
  - 免费八字 preview 默认 `career` 维度，避免 Guard 必需维度缺失：`3446061`
- 密钥边界：`DEEPSEEK_API_KEY` 只注入本机 `~/.config/mingli/local-real-model.env`（600）或服务器 `/etc/fateradar/test.env`（0600）；仓库不存密钥。

## 二、未闭环

### 2.1 Task 9–10：代码与联调已通，但还不是正式准入

- Runtime / Model Adapter 代码已在；本机与测试服务器都能跑真实路径。
- 仍缺固定 Model Profile 质量评测、正式模型盲测、密钥托管/轮换演练。
- 默认仓库配置仍可回退 Fake；测试服务器联调时 OTP 可暂回 `fake`，不能把这当成 production 口径。
- 生产路径 `/opt/mingli-master`、`/opt/mingli-runtime`、`/var/lib/mingli` 与 Secret Manager 仍未作为 production Gate 通过。

### 2.2 Task 13：staging trajectory + 上线前证据

仍缺：

- 隔离 staging 全轨迹证据（13 describe → bazi need-input → prepared → model → guard → accepted；fortune 日/周；六爻手动/数字；follow-up；Guard 连续拒绝 delayed；complete 后 byte-identical replay）；
- Guard 红队、state volume backup/restore、生产告警四类演练；
- 支付 / 短信 / 邮件 / ICP / 公安联网等外部 Gate。

`real staging blocked / production blocked / real traffic disabled`。

## 三、下一步（严格顺序）

1. 把当前真实 Runtime + 真实模型路径固化成可复跑脚本，补齐固定 Model Profile 质量评测。
2. 跑 Task 13 staging trajectory，把 fortune / liuyao / follow-up / delayed / replay 证据写进 `docs/releases/`。
3. 同步推进密钥托管、告警、恢复演练与外部合规 Gate。
4. 备案与支付未齐前，不接公网业务流量、不开放真实支付。

## 四、关键事实与禁止项

- Mac mini `native-full` 是唯一 Runtime Gate；不得启动 VZ/Rosetta/QEMU/`linux-certify`。
- 不得修改 5.1 release 文件迁就部署；不得裁剪 13 Provider / 55 古籍 / 1328 证据。
- Runtime release root 只能含签名 217 文件 + manifest，不能夹带 `references/fulltext` 额外文件。
- `state_token`、出生资料、Prompt、支付密钥不得进客户端或日志。
- 仓库不得保存密码/私钥/API Key/商户证书/真实 OTP。
- 本地真实 Runtime 安装目录使用 `~/.local/share/mingli-web-v51/` 或仓库忽略的 `.runtime/`，不提交。
- 测试服务器出现 `accepted` 只证明联调通路，不等于 Task 13 完成，更不等于可放量。
