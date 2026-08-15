---
status: accepted
date: 2026-08-13
amends:
  - 0006-separate-user-subscriptions-from-model-provider-billing
  - 0008-use-channel-neutral-billing-and-unified-entitlements
  - 0009-separate-user-from-login-identities
  - 0010-replace-agent-loop-with-an-explicit-reading-orchestrator
---

# 从 main 按 UI-first 合同重建完整产品表现层

当前 `main` 是唯一开发基线。保留 Identity、Profile、Reading Root/Version、Orchestrator、Worker、Runtime/Model Adapter、Narrative Guard、迁移历史、合同、网络与基础设施；公共 Web 和独立 Admin 的产品表现层整体重建。旧 UI 分支只用于取证，不整体合并，有价值的后端修正按当前模型和新迁移重新实现。

产品层级由已经登录实测的青囊模式确定，组件、任务页和盘主文辅工作台以 METIS 实站与公开 MIT 组件为表现参考，自有 `mingli-master` 仍是唯一算法与事实权威。用户产品固定为七个基础术数、三种跨术产品和八字/紫微/七政三个双人合盘；13 个 Runtime Provider 永远是内部模块，不映射成 13 个页面。

第一阶段先预制公共站、用户区、全部产品流程和完整后台的全路由、全状态与 360/768/1024/1440 响应式 UI。Fixture 只存在于开发/测试 `/_ui-lab`，正常路由未接算法时显示适配中。真实浏览器逐路验收和用户批准以前，不能以 DOM、CSS 正则、接口测试或 checklist 勾选宣称 UI 完成。需求合同现在已经冻结；具体实现达到 `USER_ACCEPTED` 后，依次接 ViewModel/API、账号档案、商业邀请、Admin 真数据，再逐项接术数算法。

普通用户第一版采用密码主登录、OTP 辅助；注册必须核验手机号/邮箱、设置密码并同意当前政策版本。商品不再固定为旧两种价格；所有开放术数的确定性盘面与基础摘要免费，付费对象是绑定具体盘面的版本化深读与追问。渠道中立 Catalog、Order、Payment、Refund、追加式 Entitlement Ledger 与 Fulfillment 继续有效；第一版不做钱包、积分中心、会员等级和自动续费。

邀请是独立、默认关闭、版本化的活动模块，依赖真实账号、商品版本、服务端支付事实、权益账本与通知。奖励只授予同款 ProductVersion 权益，不复制报告、数据或现金余额。

## Consequences

- `docs/CHECKLIST.md` 成为唯一范围、依赖、进度、门禁和证据账本；不得新建平行计划或产品蓝图。
- `DESIGN.md` 是唯一视觉与响应式合同，旧 FateRadar 名称及墨绿金皮肤退出当前产品。
- ADR 0006、0008 中“首发只售两种固定商品”的部分失效；用户订阅与模型成本分离、渠道中立计费和追加式账本继续有效。
- ADR 0009 中“密码不是必做”的部分失效；User 与 LoginIdentity、DeviceSession 分离的架构继续有效。
- ADR 0010 中“三能力固定产品曝光”的部分失效；完整 Runtime、显式 Orchestrator、闭世界 Brief、Guard-before-complete 和 Accepted 原样交付继续有效。
- 算法缺口必须在自有核心中按确定性规则、证据、黄金样例和 Provider 发布流程开发；通用模型不能补盘面事实。
- 现有迁移永不重写。历史 dogfood grant 在正式账本接管后通过新迁移退出。
