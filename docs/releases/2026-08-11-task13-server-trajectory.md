# Task 13 测试服真实轨迹（2026-08-11）

记录日期：2026-08-11（Asia/Shanghai）

状态：**测试服真实 HTTP + Worker + 真 Runtime/真模型轨迹已复跑 / 本轮产品轨多数 delayed / production blocked / real traffic disabled**

用户本轮明确：**暂时不管备案和支付**。本记录不评估 ICP/支付 Gate。

## 环境

- 服务器：`fateradar-prod` current `1c26f09`
- `MINGLI_ENVIRONMENT=local`
- OTP：`fake`（development_code `246810`）
- Runtime：`one-shot`（`/opt/fateradar/shared/mingli-master`）
- Model：`deepseek` / `deepseek-v4-flash` / profile `deepseek-v4-flash-p0-v1`
- 入口：回环 `127.0.0.1:8000/3000/8080`，公网预览 `http://106.14.10.235:18080`

## 本轮做了什么

1. 固化服务器轨迹脚本：
   - `scripts/run_server_task13_trajectory.py`
   - `scripts/run_server_task13_trajectory.sh`
   - （并行会话另有）`scripts/server_task13_trajectory_payload.py`
2. 在服务器上以虚构邮箱/出生资料走：
   guest → OTP 登录 → 建档 → preview / today / week / liuyao
3. Worker 日志显示模型调用 `outcome=succeeded`（真实 deepseek）
4. 证据目录：`docs/releases/evidence/2026-08-11-task13-server-trajectory/`

## 结果（脱敏）

本轮自动化 summary（见 evidence/summary.json）：

| 轨迹 | 结果 |
|---|---|
| guest / login / profile | ok |
| preview | delayed（2 次 attempt，`guard_errors=["scope_mismatch"]`） |
| today | delayed（`scope_mismatch`） |
| week | delayed（`scope_mismatch`） |
| liuyao | 走过 waiting_input 供 cast 后 delayed（`scope_mismatch`） |
| follow-up | skipped（本轮无 accepted 基线） |
| list 敏感扫描 | ok |

同服务器历史里已有真模型 accepted 样本（不构成本轮全量 Task 13 完成）：

- bazi accepted + deepseek-v4-flash，guard 空
- fortune accepted + deepseek-v4-flash，guard 空

## 根因判断

不是 Runtime 挂了，也不是 API 起不来。模型能生成，但 **Narrative Guard 以 `scope_mismatch` 为主拒绝 Candidate**：

- 模型 blocks 引用了 claim_scope 外的 fact/evidence，或跨 subject/dimension 拼装
- 少数伴随 `invented_specific` / `required_dimension_missing`
- 两次失败后状态机正确进入 `delayed`，未 complete

这证明：

1. 真链路可复跑（登录、建档、起单、prepare、model、guard、delayed/accepted）
2. 固定模型质量仍不稳，不能放量

## 仍 blocked（跳过备案/支付后）

- Task 13 完整真轨迹：fortune/liuyao/follow-up 稳定 accepted 证据不足
- Guard 红队集与模型质量评测未齐
- Secret Manager / 告警 / state volume 恢复演练未齐
- 因此：`production blocked / real traffic disabled`

## 结论

代码与测试服已能跑真 Runtime + 真模型产品链路；**本轮 Task 13 记为 partial**：

- 联调通路成立
- delayed 路径被真实触发并留证
- 但因模型 scope 合规不稳，不能宣称 Task 13 完成，更不能上正式流量
