# 施工交接快照（2026-08-10）

> 本文是给后续施工会话的准确断点说明。只描述已验证的现状与下一步，不替代任何权威合同。与合同冲突时，以下列合同为准：`docs/MINGLI_V51_WEB_INTEGRATION.md`、`docs/plans/2026-08-09-mingli-v51-web-integration.md`、`docs/adr/`、`docs/PHASE_0_GATES.md`。

## 一、已完成（代码全部在 `main`，基线 `bb742b7`）

- Phase 0/1 网站地基（10 Task）：Next.js 公共/私人壳、FastAPI 单体、PostgreSQL、独立 Worker、Guest/Device Session、手机/邮箱 OTP（Fake）、CSRF、同源 `/api`。
- 5.1 集成 Task 1–7：Command/Result/Candidate/Output 四份 JSON Schema、`MingliRuntime`/`NarrativeModel`/`NarrativeGuard` Protocol、三个 Request Compiler、Narrative Guard、Reading Orchestrator 状态机、不可变持久化、Worker 接线。
- 5.1 集成 Task 9–10 代码：one-shot Runtime Adapter（`backend/app/adapters/runtime.py`）、DeepSeek 单模型 Adapter（`backend/app/adapters/model.py`，含回执与敏感日志收敛）。**但两者仍以 Fake 模式运行，未接真实 Runtime/模型。**
- 5.1 集成 Task 11–12：Profile/Reading API（所有权、CSRF、限流、幂等、OpenAPI）与前端 P0 免费流程（八字、今日/近七日、六爻）。
- 门禁机制：Mac mini `native-full` 唯一 Runtime Gate 的脚本与 fail-closed 规则（`infra/mingli-runtime/local_gate.py`、`verify_local_full.py`）。
- 测试：后端/合同 460 passed、Web 85 passed；测试服务器 `bb742b7` 已部署回环 + Fake。

## 二、未闭环（施工会话从这里开始）

### 2.1 Task 8：重跑 `native-full` 并归档原始证据（最高优先）

现状：门禁脚本在，但仓库内**找不到**当次原始五件套，2026-08-09 的 1584/0 结果无法独立复验，不能沿用。

缺失的五件套：`native-full-5.1.json`、`local-native-full-5.1.json`、`native-release-regression.stdout`、`native-release-regression.stderr`、`prepared-inputs.json`。

下一步（严格按合同）：

1. 重新构建并冻结 `prepared-inputs.json`（绑定 217-file release manifest、research root、原生 CPython 3.14.6、`runtime-integrity.json`、跨平台 `requirements-runtime.lock`），计算并记录其 SHA-256；
2. 运行唯一标准命令：
   ```bash
   uv run --project backend python infra/mingli-runtime/local_gate.py native-full \
     --prepared-inputs /abs/prepared-inputs.json \
     --prepared-inputs-sha256 <sha256> \
     --output-parent /abs/new/empty/output-directory
   ```
3. 验收固定为 `targets=126 modules=93 tests=1584 failed_modules=0` 且总墙钟 `<=600s`、`<=10` 槽；
4. 用 `verify_local_full.py` 独立核验五件套；任一缺失/漂移即 RED；
5. 五件套归档进仓库，并在 `docs/PHASE_0_GATES.md` 把「Mac mini Runtime 原生门禁」从待确认改为已通过。

### 2.2 Task 9–10：接真实 Runtime 与真实模型

- Runtime：`MINGLI_RUNTIME_ADAPTER` 切到真实 one-shot，配 `runtime_launcher_path`/`runtime_python_path`/`runtime_release_root`/`runtime_state_root`，启动 describe 验签（13/13 Provider 冻结快照）。P0 产品白名单仍只曝光 `bazi`/`fortune`/`liuyao`，不得裁剪 Runtime 制品。
- 模型：`MINGLI_MODEL_ADAPTER=deepseek`，注入 `DEEPSEEK_API_KEY`（仅运行时/服务器注入，绝不进仓库），并补齐三个必填价格字段 `model_price_snapshot_version`、`model_input_price_microunits_per_million_tokens`、`model_output_price_microunits_per_million_tokens`（CNY）。缺一配置校验直接 RED。
- 用户提供的测试密钥已在会话中明文出现，Phase C 验证完成后应轮换。

### 2.3 Task 13：staging trajectory + 上线前证据

Task 8/9/10 通过后：跑真实 staging 全轨迹（13 provider describe → bazi need-input → prepared → 单模型 → guard → accepted；fortune 日/周；六爻手动/数字；follow-up；Guard 连续拒绝 delayed；complete 后崩溃 byte-identical replay），补齐 `PHASE_0_GATES.md` 其余待确认项。

## 三、关键事实与禁止项（不可违反）

- 冻结 source commit：`494ce0bba174a77800daf9b9c38ce9c9166d9a94`；release manifest SHA-256：`e8d41113…f2bf68`（217 文件）。
- Mac mini `native-full` 是唯一 Runtime Gate；**不得**启动 VZ/Rosetta/QEMU/`linux-certify`/`run_lima_gate.py`。Linux 历史文件仅作 Git 追溯。
- 不得修改 5.1 release 文件迁就部署；不得裁剪 13 Provider/55 古籍/1328 证据；P0 白名单只控曝光不控制品。
- `state_token`、出生资料、Prompt、支付密钥不得进客户端或日志；不在 Guard 前调用 complete；Accepted 后不改文。
- 仓库不得保存密码/私钥/API Key/商户证书/真实 OTP。
- 备案状态：ICP 备案已提交、审核中；备案通过前不接真实公网业务流量。
