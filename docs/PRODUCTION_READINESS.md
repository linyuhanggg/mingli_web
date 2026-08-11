# 生产就绪完成定义合同

版本：v1（2026-08-12 冻结）。权威来源：`docs/plans/2026-08-12-complete-production-ha-website.md` 第 2–4 节。修改本文件等于修改发布合同，必须随 ADR 评审并更新版本号。

## 1. 完成状态机（不得混用）

| 状态 | 必须具备 | 明确不能声称 |
|---|---|---|
| Feature Complete | P0 用户旅程、支付、账户权利、后台均有真实代码和自动测试 | 不能称生产就绪 |
| Staging Ready | 独立 staging 数据/密钥/对象桶，真 OTP、真 Runtime、真模型和支付沙箱闭环 | 不能放普通用户流量 |
| Production Ready | 安全、合规、密钥、备份、告警、恢复、压测和回滚 Gate 全绿 | 不能跳过灰度直接全量 |
| Canary | 小范围真实账号/小额订单运行，指标和告警稳定，随时可回滚 | 不能承诺 99.9% 已长期达成 |
| General Availability | 双可用区入口、生产支付和运营闭环启用；连续观测期内无 P0/P1 阻断 | 只有此时才可称「完整高可用网站」 |

规则：

1. 任何文档、页面、公告、release note 使用的状态词必须能在本表找到对应定义。
2. 状态只能前进；发现新的 P0/P1 缺陷时状态回退并记录原因。
3. 「基本可用」「稳定」「差不多好了」等不可测措辞禁止出现在验收材料中。

## 2. 当前状态认定

截至 2026-08-12：**尚未达到 Feature Complete**。差距：幂等/Profile/核对语义（Task 2）、生产认证与账户权利（Task 3）、商业闭环（Task 4/5）、Guard/评测 Gate（Task 6）尚无代码与测试。Task 0 仅证明既有门禁可信。

## 3. 用户可见状态与内部状态映射（冻结）

| 用户可见 | 内部来源 | 语义 |
|---|---|---|
| `queued` | 任务已入队，等待 Worker 领取 | 正常等待 |
| `waiting_input` | Runtime 要求补充信息 | 需要用户操作 |
| `delayed` | 模型/Runtime 故障退避或 Guard 连续拒绝 | 可解释的延迟，不丢单 |
| `runtime_unknown` | 无 token claim 过期且无 checkpoint | 人工/自动核查中，不重复扣权益 |
| `stopped` | Guard 拒绝且不可继续，或用户主动停止 | 终态，必须给出原因 |
| `accepted` | 已交付的不可变正文 | 终态，原字节可重放 |

约束：Runtime/模型故障只降级解读（进入 `delayed`/`runtime_unknown`），不得拖垮登录、订单、报告读取和退款。

## 4. 合同变更纪律

- 后续任务（Task 2–13）不得修改本文件状态定义而不更新版本与评审记录。
- production fail-closed 逻辑（real-traffic 拒绝、API 503 占位、OTP fail-closed）只能在 Gate 证据齐后经本合同评审解除。
