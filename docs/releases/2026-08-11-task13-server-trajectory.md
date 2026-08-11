# Task 13 测试服真实轨迹（2026-08-11）

记录日期：2026-08-11（Asia/Shanghai）

状态：**round-4 product 5/5 accepted（测试服）/ production blocked / real traffic disabled**

用户本轮明确：**暂时不管备案和支付**。本记录不评估 ICP/支付 Gate。

## 环境

- 服务器：`fateradar-prod` current `/opt/fateradar/releases/6ec15786ac8ce110bbf698b1c8578518123b1a2a`（代码提交 `6ec1578`；文档收口 `255ee73`）
- `MINGLI_ENVIRONMENT=local`
- OTP：`fake`（development_code `246810`）
- Runtime：`one-shot`（`/opt/fateradar/shared/mingli-master`）
- Model：`deepseek` / `deepseek-v4-flash` / profile `deepseek-v4-flash-p0-v1`
- 入口：回环 `127.0.0.1:8000/3000/8080`，公网预览 `http://106.14.10.235:18080`
- Worker：systemd `fateradar-test-worker.service`（active，轮询间隔 2s，只轮询 reading status）
- 本轮 API 入口用 `http://127.0.0.1:8080/api/v1`（nginx 回环同源，浏览器同路径）
- 身份：`t***@example.com`（虚构邮箱）/ 虚构出生资料（1994-04-30T05:55:00+08:00，福建省福州市），原文不落库不落仓

## 证据文件

- `docs/releases/evidence/2026-08-11-task13-server-trajectory/`（第一轮 curl 版 summary/console/analysis + 第二轮 .py 版 run-summary）
- `docs/releases/evidence/2026-08-11-task13-server-trajectory/run-3-constrained/`（第三轮约束重跑 run-summary）
- 脚本：`scripts/run_server_task13_trajectory.py`（本机 SSH 编排）、`scripts/server_task13_trajectory_payload.py`（服务器执行）、`scripts/run_server_task13_trajectory.sh`（旧版 curl，保留）
- 原始 HTTP 响应只保留在服务器 0700 工作目录，未复制回仓库

## 三轮结果（脱敏）

### 第一轮（旧版 curl，8000 入口）

9 条轨迹全 ok/delayed，0 accepted。作为联调通路验证。

### 第二轮（.py payload，8080 入口）

| 步骤 | 内容 | 结果 | 细节 |
|---|---|---|---|
| S1 | guest session | ok | 201 |
| S2 | email OTP request | ok | 202，development_code 匹配 |
| S3 | email OTP verify | ok | 200，csrf 轮换，device session 建立 |
| S4-S5 | profile draft + confirm（虚构） | ok | 201/201 |
| S6 | preview bazi (career) | **accepted** | 218 chars，poll 15s，version `68ce155a-…`，guard 空 |
| S7 | today fortune | delayed | `scope_mismatch` |
| S8 | week fortune | delayed | `scope_mismatch` |
| S9 | liuyao digital_coin | delayed | 无 waiting_input，直接 delayed |
| S10 | follow-up（新 version） | terminal_stopped | job.status=stopped，prepare 阶段被 Runtime 返回 Stopped，非 need_input |

敏感扫描：1 处命中——`raw_birth_datetime`（字符串 `1994-04-30T05:55:00+08:00`）出现在 preview 那条的 `GET /readings/{id}/result` 的 **fact_panel** 里。

DB 存量：跑前 accepted=6/delayed=10/total=16 → 跑后 accepted=7/delayed=13/terminal_stopped=1/total=21。

### 第三轮（约束重跑，8080 入口）

用 `TASK13_QUERY_PREVIEW/TODAY/WEEK/LIUYAO/FOLLOWUP` 环境变量覆盖 query 文案，约束为"只讲趋势，不写具体公历日期/年份/数字应期"——这是产品级尽力，不是伪造。

| 步骤 | 内容 | 结果 |
|---|---|---|
| S1-S5 | guest / OTP / profile | ok |
| S6 | preview bazi (career) | delayed（version `8debb933-…`） |
| S7 | today | delayed（`4d46a3dc-…`） |
| S8 | week | delayed（`2493f10e-…`） |
| S9 | liuyao digital_coin | delayed（`5f2a6b26-…`，无 waiting_input） |
| S10 | follow-up | skipped（无 accepted 基线） |

敏感扫描：0 处命中。

DB 存量：跑前 accepted=7/delayed=13/total=21 → 跑后 accepted=7/delayed=17/terminal_stopped=1/total=25（增量 = 4 delayed）。

DB guard 证据（只读）：这 4 个版本 guard_errors 全部 `scope_mismatch`（部分含 `required_dimension_missing`），model_receipt 全部 `succeeded`（deepseek-v4-flash-p0-v1，真实模型调用，latency 4-17s，有 token 用量）。

## 根因判断

不是 Runtime 挂了，也不是 API 起不来。模型能生成，但 **Narrative Guard 以 `scope_mismatch` 为主拒绝 Candidate**：

- 模型 blocks 引用了 claim_scope 外的 fact/evidence，或跨 subject/dimension 拼装
- 少数伴随 `invented_specific` / `required_dimension_missing`
- 两次失败后状态机正确进入 `delayed`，未 complete

两个关键负证据：

1. **prompt 约束不解决 Guard 拒绝**：第二轮同 query 的 preview 一次 accepted、一次 delayed，第三轮约束文案反而全 delayed——模型固定质量不稳是主因，不是 query 措辞。
2. **follow-up 无 accepted 基线即 terminal_stopped**：两条 follow-up 轨迹都未产出新 accepted version（第二轮 baseline 是 terminal_stopped，第三轮 skipped），Task 13 的 follow-up 真轨迹仍未达成。

`fact_panel` 泄漏根因（如实记录，不擅改代码）：`backend/app/readings/service.py:334` 把 Runtime 生成的 `prepare.brief` 直接透传成 `fact_panel`；runtime 侧 `_public_facts()`（`/opt/fateradar/shared/mingli-master/scripts/reading_engine/providers.py` 约 1336 行）把 input fields（含 `birth_datetime`）投影为公开 fact `fact:{subject}/input/{field_id}`，`display_text` 为 `{label}：{value}`。按验收标准算泄漏（原始出生 datetime 出现在 result 响应里），需后续修复。

这证明：

1. 真链路可复跑（登录、建档、起单、prepare、model、guard、delayed/accepted）
2. 固定模型质量仍不稳，不能放量
3. Guard 拒绝路径是真实的、可留证的（guard_errors + model_receipt 双证据）

## 仍 blocked（跳过备案/支付后；以 Round 4 为准）

- Round 1–3 的 partial 结论已被 Round 4 覆盖：产品 5 轨 accepted 证据已齐（见下方 Round 4）
- Guard 红队集（人为构造的越界/幻觉样本）未做
- complete 后 byte-identical replay、state volume 恢复演练未齐
- Secret Manager 迁移、生产告警未齐
- 早期轨迹曾记录 fact_panel 泄漏原始 birth datetime，需单独修与复验
- 因此：`production blocked / real traffic disabled`

## Round 1–3 结论（历史，已被 Round 4 覆盖）

代码与测试服已能跑真 Runtime + 真模型产品链路；**Round 1–3 记为 partial**：

- 联调通路成立（guest/OTP/profile 全 PASS，起单/轮询/状态机正确）
- delayed 路径被真实触发并留证（guard_errors + model_receipt 双证据）
- 当时仅 preview 出现过 accepted，today/week/liuyao/follow-up 未稳
- 发现 fact_panel 泄漏原始出生 datetime 的缺陷

Round 4 之后产品 5 轨已 accepted，但放量 Gate 仍未齐。下一轮重点：Guard 红队集、固定模型评测、fact_panel 泄漏修复、Secret Manager。

## Round 4（b104245 reference closer + 6ec1578 follow-up token 修复）

部署：

1. `b104245` 上线 `candidate_reference_closer` 后，真实 Runtime+模型路径上 preview/today/week/liuyao 已能 accepted。
2. follow-up 仍 `terminal_stopped`：prepare 使用了错误的 `transition=correct` 且未带 Accepted token。
3. `6ec1578` 修复 follow-up 合同并部署到测试服；新轨迹目录 `/tmp/task13-server-trajectory-v3/`，本地证据目录 `docs/releases/evidence/2026-08-11-task13-server-trajectory/run-4-followup-fix/`。

验收目标：

- guest/login/profile ok
- preview / today / week / liuyao / followup 全部 accepted
- 敏感扫描不落密钥/cookie
- 仍不宣称 production ready


### Round 4 结果（`/tmp/task13-server-trajectory-v3` → `run-4-followup-fix`）

| 步骤 | 内容 | 结果 |
|---|---|---|
| S1-S5 | guest / OTP / profile | ok |
| S6 | preview bazi (career) | **accepted** |
| S7 | today fortune | **accepted** |
| S8 | week fortune | **accepted** |
| S9 | liuyao digital_coin | **accepted** |
| S10 | follow-up | **accepted** |
| list | readings list | ok |

证据：`docs/releases/evidence/2026-08-11-task13-server-trajectory/run-4-followup-fix/`

说明：这是测试服 `local + fake OTP + one-shot Runtime + deepseek` 的真实路径通过，不是 production 放量批准。

## Round 4 结论

- 测试服 current `6ec1578` 上，preview / today / week / liuyao / followup **5/5 accepted**
- 关键修复：`b104245` candidate reference closer；`6ec1578` follow-up accepted token prepare
- 这是联调环境真实路径通过，**不是** production 放量批准
- Task 13 合同剩余：固定评测、Guard 红队、replay/恢复/告警、敏感边界复验

