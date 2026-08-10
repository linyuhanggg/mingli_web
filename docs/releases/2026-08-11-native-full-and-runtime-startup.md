# Mingli V5.1：Task 8 原生门禁归档与真实 Runtime Startup

记录日期：2026-08-11（Asia/Shanghai）

状态：**Task 8 已闭环 / 真实 Runtime startup 本机通过 / 真实模型与 staging 仍 blocked / production blocked / real traffic disabled**

结论：本记录不是上线批准。它把此前缺失的 Mac mini `native-full` 原始证据固定进仓库，并确认本机可用的签名 Runtime 安装能通过 one-shot startup gate。默认业务路径仍是 Fake；没有注入的 DeepSeek 密钥前，不得宣称真实成稿链路已通。

## 1. Task 8 证据

归档目录：

`docs/releases/evidence/2026-08-09-native-full/`

| 文件 | 作用 |
|---|---|
| `native-full-5.1.json` | 原生门禁权威报告 |
| `local-native-full-5.1.json` | 本地 SLA envelope |
| `native-release-regression.stdout` | 原始 suite 输出 |
| `native-release-regression.stderr` | 原始 suite 错误流（本轮为空） |
| `prepared-inputs.json` | 冻结 PreparedInputs |

关键摘要：

- `profile=native-full`，`status=passed`
- `targets=126`，`modules=93`，`tests=1584`，`failed_modules=0`
- suite `elapsed=434.13s`，command `elapsed≈434.24s`，evidence seal `≈434.59s`（均 `<600s`）
- `slots=10`
- `prepared_inputs_sha256=a4e83f3c225b928a9d9ea8b9ffc56448cb283ed23dd8b4e9f0b7e3831fa77807`
- source commit `494ce0bba174a77800daf9b9c38ce9c9166d9a94`
- release manifest SHA-256 `e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68`

独立核验命令与结果：

```bash
uv run --project backend python infra/mingli-runtime/verify_local_full.py   --profile-report docs/releases/evidence/2026-08-09-native-full/native-full-5.1.json   --local-summary docs/releases/evidence/2026-08-09-native-full/local-native-full-5.1.json   --prepared-inputs-sha256 a4e83f3c225b928a9d9ea8b9ffc56448cb283ed23dd8b4e9f0b7e3831fa77807
```

结果：exit 0，输出确认 `profile=native-full` 与同一 `prepared_inputs_sha256`。

## 2. 真实 Runtime startup

本机建立仅含 217 签名文件的私有 release root（无 `references/fulltext` 额外文件），并绑定：

- launcher：`<release>/scripts/run_reading_transaction.sh`
- python：`/Users/yuhanglin/.local/share/mingli-master/venv/bin/python`（CPython 3.14.6）
- state root：私有可写目录（mode 不含 group/world write）
- expected describe digest：`7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342`
- expected capability shape：`8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60`

实跑：

```text
build_runtime_startup_gate(settings).startup()
-> STARTUP_OK OneShotMingliRuntimeAdapter
```

补充 prepare 冒烟：

- 缺出生资料：`Stopped(need_input)`
- 仅出生时刻：继续 `need_input`（地点/性别）
- 出生时刻 + 上海 + 男：`Prepared`，`state_token` 存在，brief 含 `facts/evidence/findings/claim_scopes/limits`

fortune 因输入合同更严（`birth_datetime`/`timezone`/`reference_datetime` 等），本轮 smoke 未强行扩全量。

本地 release 安装路径使用 `~/.local/share/mingli-web-v51/` 或仓库忽略的 `.runtime/`，**不进 Git**。

## 3. 明确仍未完成

- 当前 shell 无 `DEEPSEEK_API_KEY`，不能切真实模型 adapter。
- 未跑真实 model → Narrative Guard → complete → Accepted。
- 未跑 Task 13 staging trajectory、固定模型评测、Guard 红队、state volume backup/restore、生产告警演练。
- 支付、短信、邮件、ICP/公安联网等外部 Gate 仍待确认。
- 回环测试服务器仍是 `local + Fake`，不能冒充 staging。

## 4. 发布决定

- 允许：把 Task 8 记为已通过；允许后续在本机/测试机接真实 Runtime。
- 不允许：开放真实公网流量；把 Fake 服务器叫 staging；在无密钥、无模型评测、无 staging 轨迹时宣称“正式版已上线”。

下一断点见 [HANDOFF_SNAPSHOT_2026-08-11.md](../HANDOFF_SNAPSHOT_2026-08-11.md)。
