# 施工交接快照（2026-08-11）

> 本文是给后续施工会话的准确断点说明。只描述已验证的现状与下一步，不替代任何权威合同。与合同冲突时，以下列合同为准：`docs/MINGLI_V51_WEB_INTEGRATION.md`、`docs/plans/2026-08-09-mingli-v51-web-integration.md`、`docs/adr/`、`docs/PHASE_0_GATES.md`。

## 一、已完成（代码在 `main`）

- Phase 0/1 网站地基、5.1 集成 Task 1–7 / 9–12 代码与测试仍在 `main`。
- **Task 8 已闭环**：`native-full` 五件套已归档到 `docs/releases/evidence/2026-08-09-native-full/`，并经 `verify_local_full.py` 独立通过。
  - `targets=126 modules=93 tests=1584 failed_modules=0 elapsed=434.13s`
  - `prepared_inputs_sha256=a4e83f3c225b928a9d9ea8b9ffc56448cb283ed23dd8b4e9f0b7e3831fa77807`
  - source commit `494ce0bba174a77800daf9b9c38ce9c9166d9a94`
  - release manifest SHA-256 `e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68`
- **真实 Runtime startup 已通过**：本机私有 217 文件 release root + CPython 3.14.6 venv 上，`build_runtime_startup_gate(...).startup()` 返回 `OneShotMingliRuntimeAdapter`；describe 为 13/13，digest 与 capability shape 匹配冻结值。
- 真实 Runtime prepare 冒烟：bazi 缺输入返回 `Stopped(need_input)`；补齐出生时刻/地点/性别后返回 `Prepared` 且持有 `state_token`。fortune 需更严格输入字段，当前 smoke 未强行扩成全链路。
- 测试服务器 `bb742b7` 仍是 `local + Fake` 回环环境，不等于 staging/production。

## 二、未闭环

### 2.1 Task 9–10：默认仍 Fake；真实模型密钥缺失

- Runtime/Model 代码与测试已在；默认配置仍是 `MINGLI_RUNTIME_ADAPTER=fake`、`MINGLI_MODEL_ADAPTER=fake`。
- 本机已具备真实 Runtime 路径，但 **当前环境没有 `DEEPSEEK_API_KEY`**，不能切 `MINGLI_MODEL_ADAPTER=deepseek`，也不能跑真实模型成稿、固定模型评测或 complete 后 Accepted 全链路。
- 生产路径仍要求 `/opt/mingli-master`、`/opt/mingli-runtime`、`/var/lib/mingli` 与 Secret Manager，尚未建立。

### 2.2 Task 13：staging trajectory + 上线前证据

仍缺：

- 真实模型与固定 Model Profile 质量评测；
- Guard 红队、backup/restore、生产告警四类演练；
- 隔离 staging 全轨迹（13 describe → bazi need-input → prepared → model → guard → accepted；fortune 日/周；六爻；follow-up；Guard 连续拒绝 delayed；complete 后 byte-identical replay）；
- 支付/短信/邮件/ICP/公安联网等外部 Gate。

`real traffic` 保持 disabled；production blocked。

## 三、下一步（严格顺序）

1. 注入并轮换 `DEEPSEEK_API_KEY`，补齐三个价格字段后切 `MINGLI_MODEL_ADAPTER=deepseek`。
2. 用真实 Runtime + 真实模型跑最小 prepare → candidate → guard → complete → Accepted 冒烟，再补 fortune/liuyao。
3. 在隔离环境写 Task 13 staging trajectory 证据，更新 `docs/releases/` 与 `PHASE_0_GATES.md`。
4. 外部 Gate 与备案未齐前，不接公网业务流量、不开放真实支付。

## 四、关键事实与禁止项

- Mac mini `native-full` 是唯一 Runtime Gate；不得启动 VZ/Rosetta/QEMU/`linux-certify`。
- 不得修改 5.1 release 文件迁就部署；不得裁剪 13 Provider / 55 古籍 / 1328 证据。
- Runtime release root 只能含签名 217 文件 + manifest，不能夹带 `references/fulltext` 额外文件。
- `state_token`、出生资料、Prompt、支付密钥不得进客户端或日志。
- 仓库不得保存密码/私钥/API Key/商户证书/真实 OTP。
- 本地真实 Runtime 安装目录使用 `~/.local/share/mingli-web-v51/` 或仓库忽略的 `.runtime/`，不提交。
