# 命理小程序商业化与算法架构蓝图 v1.1

> 决策日期：2026-08-08  
> 自动续费与模型成本补充：2026-08-09  
> 状态：Superseded；仅保留为“微信小程序优先”阶段的历史决策  
> 取代文档：[PRODUCT_BLUEPRINT_WEB_IOS_V2.md](./PRODUCT_BLUEPRINT_WEB_IOS_V2.md)  
> 说明：命理核心、不可变版本、Accepted 和追加式权益账本由 V2 继续采用；平台、账户与支付实现以 V2 为准  
> 共同语言：[CONTEXT.md](../CONTEXT.md)

## 0. 本文怎么用

本蓝图不是脑暴稿。进入开发后，商品语义、状态边界、核心调用方法和记账原则按本文实施；将来新增术法或商品属于扩展，不得破坏已有合同。

### 冻结的长期合同

1. 小程序是“个人命理档案 + 一事一问 + 事实核对”的普通用户入口。
2. P0 只卖两种单次商品，不做自动续费、代币钱包或复杂会员等级。
3. 虚拟内容只走微信小程序虚拟支付：P0 使用“道具直购”，P1 若启用连续陪伴则使用官方“会员订阅”；不走普通 JSAPI 支付，不引导站外付款。
4. 支付结果、权益、报告交付分别建模；支付成功不等于报告已经生成。
5. 权益使用追加式账本；只在命理核心返回 Accepted 且正文落库时核销。
6. mingli-master 是唯一命理事实、证据和连续状态核心，业务代码不得 import 或复制它。
7. 档案、事实简报、已接纳正文全部不可变版本化。
8. 平台安全与商品结构校验在 complete 前完成；Accepted 后原样交付。
9. 首版采用阿里云上的模块化单体，不提前拆微服务。
10. 免费 Preview 也完整走 prepare → complete → Accepted；付费报告在付款前建立独立的 Prepared 购买目标，不借用未提交的中间态。
11. 用户向本产品购买数字服务权益，不购买模型、Token 或 API Key；用户订阅扣款与本产品向模型/云厂商付费是两条完全独立的账务链。

### 可以配置、但不能改坏合同的项目

- 商品价格可通过新的 Product Version 调整，已下单订单永远保留原价快照。
- 模型厂商、具体模型版本、超时和重试参数可以替换，但不能进入命理核心。
- 展示文案、视觉、首页排序可以迭代，但不能扩大商品承诺或改变权益核销时点。
- 新增术法必须先通过 describe 合同回归，再加入产品允许列表；不能随核心升级自动上线。
- 微信费率、平台类目和外部合规规则属于动态配置与发布门槛，不写死在业务算法中。

## 1. 一页结论

首版商业模式采用“免费建立可信感，按明确结果单次购买”：

| 层级 | 用户得到什么 | 价格 |
|---|---|---:|
| 免费 | 一个本人档案、确定性八字排盘、有限概览、3 条事实核对、每个档案版本 1 次核对后概览、今日/近七日汇总、六爻基础卦象展示 | ¥0 |
| 个人命盘深度解读 | 一份绑定档案版本的八字终身主题报告，永久查看，7 天内 3 次同盘追问 | ¥29.90 |
| 一事一问·六爻 | 一份绑定具体问题和卦象的事件解读，永久查看，72 小时内 2 次同盘追问 | ¥9.90 |

首版不卖：

- 自动续费会员、月卡、年卡；
- 金币、点数、充值余额；
- “改运”“消灾”“保证应验”商品；
- 单独收费的核对反馈；
- 人脸、手相、面相上传测算；
- 真人命理师撮合、课程或实物。

这个结构把用户每次付款对应到一份明确的 Purchase Target，避免“开了会员却不知道买了什么”，也把退款、重试和报告归属变得可审计。

## 2. 微信支付和平台硬边界

### 2.1 支付能力选择

命盘报告、六爻解读、追问额度都属于虚拟商品。P0 使用微信小程序虚拟支付的“道具直购”：

- 小程序端调用 wx.requestVirtualPayment；
- Android、鸿蒙、Windows 路由微信支付；
- iOS 路由 Apple 支付；
- 商品在微信虚拟支付后台配置为道具，业务 Product Version 保存对应平台 Product ID；
- 服务端接收道具发货推送，同时实现 query_order 轮询补偿；
- 不建立代币兑换比例，不调用代币扣减接口。

选择道具直购而不是代币，原因是用户能看到人民币价格、一次购买对应一次交付，退款不需要再对一层虚拟余额做冲正，也不会形成大量未使用余额。

### 2.2 主体与发布门槛

正式收费前必须满足：

1. 小程序主体为已认证的企业、事业单位或个体工商户；
2. 在当前小程序管理后台真实出现并成功开通“虚拟支付”；
3. 使用实际经营内容提交类目和版本审核，不以改名规避审核；
4. 隐私保护指引明确出生日期、出生地、问题文本、保存期限和删除方式；
5. 报告页面显式展示“AI 辅助生成”标识和使用边界；
6. 实际审核通过前，不把任何一类目名称当成已经获准经营的事实。

发布资格是 Gate 0。它可能阻止上线，但不会改变商品、权益和算法架构。

### 2.3 iOS 差异

截至 2026-08-08，iOS 小程序虚拟支付已开放，最低支付金额 1 元，当前 iOS 15 及以上、微信 8.0.68 及以上可用。Apple 支付不支持沙箱，所以必须用现网低价测试商品做一次受控验收。

iOS 退款由用户在 App Store 发起，开发者不能主动替用户发起；系统需要响应退款问询并消费最终退款推送。Android、鸿蒙和 Windows 可按虚拟支付退款接口处理。业务层统一产生 Refund 和 Reversal，渠道 Adapter 分别实现。

### 2.4 结算、费率和现金流

当前官方说明中，Android/鸿蒙/Windows 普通虚拟支付按 T+3 分账；iOS 由 Apple 结算，通常在自然月结束后 45～60 天向腾讯结算，再由腾讯划转到开发者虚拟支付账户。iOS 标准服务费为 17%，2026 年腾讯技术服务费限时减免后当前合计为 12%，但 Apple 政策和平台减免都可能变化。

因此：

- Payment.paid 不能当成银行账户已经可提现；
- 单独保存 Settlement 的预计日期、实际日期、渠道费、净结算和账单批次；
- 经营看板以实际账单为准，订单金额只用于应收预测；
- 单位经济统一按 20% 渠道成本预留，覆盖当前费率变化，不靠限时减免才能盈利；
- 每次发布前重新读取当前费率，更新配置和经营测算，不修改历史 Product Version。

### 2.5 支付结果的权威性

客户端 success 只说明调起流程返回成功，它可能丢失，也不能证明服务端已到账。到账依据按优先级为：

1. 验签后的虚拟支付发货/支付推送；
2. 服务端 query_order 查询；
3. 平台结算账单对账。

任何一个入口都必须以外部订单号和平台事件 ID 幂等处理。前端不得直接 Grant 权益。

## 3. 免费内容边界

免费不是“把完整报告打码一半”，而是单独、完整、有用的 Preview：

### 3.1 八字免费层

- 建立一个“本人”受测档案；
- 展示时间口径、四柱和会影响结论的基础事实；
- 一条主线概览，不承诺覆盖所有人生领域；
- 3 条核对项：符合、部分符合、不符合、暂时不知道；
- 3 条都完成后，用户可主动生成 1 次“核对后概览”；应用把本次结构化反馈逐条展示给用户确认，再如实转写进 correct 的最新 query，由核心产生新 Brief 后成稿；
- 显示事实简报中的限制，例如出生时刻不确定或运程时间只能给出序列；
- 今日提示按 day horizon 计算；
- “近七日”是 7 个 day 事实快照的汇总视图，不伪造核心不存在的 week horizon。

免费概览可以由确定性模板或受约束的低成本模型生成，并且和付费正文一样，在展示前通过 Preview Contract、内容安全检查和 AI 显式标识，再调用 complete 成为 Accepted。它使用独立的免费 Reading Root 和有限维度；一次核对后概览使用该根最新 Accepted token 与 transition=correct。付费报告不会拿同一个 Prepared token 扩写，因此不存在“先展示一段、付款后换正文”的首次提交冲突。

### 3.2 六爻免费层

- 用户先写清一个具体问题；
- 明确展示六次投掷/数字投币方式、起卦时刻、时区和地点；
- 免费展示本卦、变卦、动爻等基础事实；
- 展示解读将覆盖的维度和已知限制；
- 不在付费前暗示一个恐吓性结论来逼迫购买。

免费卦象概览先完成自己的 Prepared → complete → Accepted。用户主动选择“一事一问·六爻”商品时，应用使用同一份已确认输入在新的付费 Reading Root 中先 prepare；只有这个付费目标返回 Prepared 后才出现购买入口。Stopped.need_input、unsupported、conflict 或 error 都不展示付费按钮。

## 4. P0 商品合同

### 4.1 商品一：个人命盘深度解读

| 字段 | 决定 |
|---|---|
| 内部 SKU | bazi_deep_reading_v1 |
| 首发价格 | 2990 分 |
| Purchase Target | 一个 Prepared 的八字解读 + 一个不可变 Profile Version |
| 核心范围 | capability=bazi，object=natal，horizon=life |
| 默认维度 | overview、state、career、relationship、timing |
| 主交付 | 1 份已接纳正文 |
| 附带权益 | 同根追问 3 次，支付成功后待报告交付激活，Accepted 后 7×24 小时到期 |
| 查看期限 | 正文永久可查看，除非用户删除账号/数据或退款导致访问权益冲正 |

正文合同固定为六部分：

1. 资料与时间口径；
2. 盘面主线；
3. 优势、惯性与需要核对的盲点；
4. 事业与工作倾向；
5. 关系互动倾向；
6. 阶段节律、依据出处与边界。

“健康”不作为首版付费主章节，模型不得给出诊断或治疗意见；“财运”也不写成投资结论。若 Brief 对某一维度没有 Claim Scope，正文必须明确未覆盖，不能用常识补齐。

### 4.2 商品二：一事一问·六爻

| 字段 | 决定 |
|---|---|
| 内部 SKU | liuyao_event_reading_v1 |
| 首发价格 | 990 分 |
| Purchase Target | 一个 Prepared 的六爻解读 + 原始问题 + 起卦记录 |
| 核心范围 | capability=liuyao，object=concrete_event，horizon=instant |
| 主交付 | 1 份已接纳正文 |
| 附带权益 | 同根追问 2 次，Accepted 后 72 小时到期 |
| 查看期限 | 正文永久可查看，除非用户删除账号/数据或退款导致访问权益冲正 |

正文合同固定为五部分：

1. 直接回答当前问题；
2. 卦象中真正影响结论的事实；
3. 成立条件与可能变化；
4. 时间或位置判断，仅在 Brief 支持时出现；
5. 依据、限制和下一步可核对事项。

修改问题对象、换一件事、换术法或重新投掷都属于新的 Reading Root，需要新的 Purchase Target；不能把“追问”当作无限次重新占问。

### 4.3 追问和核对怎么计数

- 点选核对反馈不扣追问次数；
- 用户要求解释正文中的一句话，属于同盘追问；
- 用户补充同一问题的现实进展，仍可同盘追问；
- 用户只提交“不符合”等核对反馈不扣次数；免费概览每个 Profile Version 含 1 次核对后重写，之后或付费正文再要求生成纠正版本时，新版本 Accepted 扣 1 次追问；
- 用户修改出生时间、卦象、起卦时刻或问题对象，属于 Recast；
- Worker、网络或模型失败不扣次数；
- 只有新 Reading Version 返回 Accepted 并落库，才核销一份追问权益；
- 并发点击用 Reservation 保证最多核销一次。

### 4.4 首版不做自动续费，P1 只预留连续陪伴订阅

“模型由平台提供”不等于“用户必须订阅模型”。用户购买的是命理解读和陪伴内容的交付权益，模型调用费是本产品的履约成本。P0 两个深度解读商品继续单次购买、永久查看，不因为以后上线订阅而变成租赁内容。

当前微信会员订阅要求已经接入虚拟支付、完成认证备案、小程序首次发布满 90 天且近 30 天日均 DAU 达到 1 万；订阅不支持沙箱。因此，新小程序不能把自动续费作为首发依赖。P0 先用真实的一次性购买和 7 日复访数据验证留存，达到平台门槛后才允许启用 P1 订阅 Feature Flag。

P1 若通过留存评审，只新增独立的 `mingli_companion_monthly_v1` 连续陪伴商品，不把两种单次深度解读并入会员，也不承诺“无限生成”。每个 Product Version 必须明确当周期内容、次数、有效期和成本上限；首发可先用同合同的“30 天陪伴包”做单次购买验证，再决定是否开放连续扣款。

### 4.5 自动续费的固定业务规则

1. 用户先明确签署渠道订阅合同；签约成功只建立 Subscription Contract，只有渠道确认当期扣款成功才授予当期权益。
2. 每次续费都形成一个不可变 Subscription Cycle，并关联一笔续费 Order、Payment 和一组新的 Ledger GRANT；外部续费订单号是幂等键，重复通知不得重复发权益。
3. 退订表示“当前周期结束后不再续费”，不会提前收回已经付款的本期权益；到期后不再产生新 GRANT。退款才按渠道最终结果追加 REVERSE。
4. 一个用户对同一订阅商品同一时间最多有一个有效合同。权益可跨设备读取，但续费和退订仍由原签约渠道管理；旧合同结束前不得在另一端重复签约。
5. Android/鸿蒙由服务端按平台规则发送预扣费通知并在规定日期提交扣款；iOS 由 Apple 自动扣款，服务端只能接收扣款结果，不能自行发起苹果续费。
6. 客户端 API 的 success、签约回调和扣款回调不可互相替代。回调丢失时分别用合同查询和订单查询补齐；最终以验签后的渠道通知/查询结果为准。
7. 商品涨价必须发布新的 Product Version，并按渠道规则重新披露或签约；禁止静默修改已有合同价格、周期或权益。

订阅合同状态固定为 `sign_pending → active → cancel_at_period_end → ended`，异常撤销为 `revoked`；订阅周期状态固定为 `due → charge_pending → paid → granted`，失败为 `failed`，退款为 `refund_pending → refunded`。合同状态不充当权益余额，周期状态也不充当报告交付状态。

## 5. 定价与成本护栏

### 5.1 价格版本

- 首发价在“上线后 60 天或累计 500 个已支付订单，以先到者为准”的验证周期内不变；
- 之后调价必须创建新的 Product Version，不覆盖旧版本；
- 订单保存 SKU、商品版本、平台 Product ID、人民币分值、币种、权益合同摘要和购买目标摘要；
- 客户端传来的金额只用于展示比对，服务端以 Product Version 为准；
- P0 不做优惠券、拼团、分销、返现或邀请解锁，先获得干净的转化与退款数据。

### 5.2 单位经济护栏

费率会随平台和年份变化，系统记录实际结算值，经营测算按 20% 渠道成本做保守预留：

| 商品 | 售价 | 20% 渠道预留后 | 模型+审核目标 | 单笔硬上限 |
|---|---:|---:|---:|---:|
| 个人命盘深度解读 | ¥29.90 | ¥23.92 | ≤ ¥3.00（含附带追问平均摊销） | ¥4.50 |
| 一事一问·六爻 | ¥9.90 | ¥7.92 | ≤ ¥0.80（含附带追问平均摊销） | ¥1.50 |

护栏不含税费、固定服务器成本和人工售后。若连续 100 单的变量生成成本超过净结算收入 12%，触发告警；达到 20% 时暂停高成本模型并切换已验收的低成本 Adapter，而不是偷偷缩减商品内容。

免费今日内容只按用户主动打开生成，同一 Profile Version + 日期全日缓存；目标平均成本不超过 ¥0.05/次，不做后台给所有注册用户批量生成。

### 5.3 自带模型的付款和欠费护栏

首版“自带模型”指服务端持有阿里云百炼等模型厂商的 API 凭据并承担费用，小程序端永远不出现厂商 Key、余额或模型选择。模型厂商账单不按某个用户的续费周期逐笔充值：

- API 模型默认按量后付费，产品账户开启自动销账、可用额度预警和自动充值；自动充值使用独立的企业支付方式，并同时设置日预算、月预算和异常消费告警；
- 每个 Generation Job 仍有模型成本硬上限，达到上限先切换已验收的低成本 Adapter，再进入事实模板或 retryable_failure，不能无限重试；
- 若改为自托管开源模型，模型权重本身没有“续费”，需要自动续费的是 ECS/GPU、数据库、缓存和 OSS 等云资源；资源续费仍与用户会员完全分账；
- 模型账户欠费、限流或厂商故障时，Job 进入可重试状态并 RELEASE 本次 Reservation，不核销用户的报告/追问权益，不改变其订阅合同，也不要求用户再次付款；
- 已经 Accepted 的报告永久从本地业务库交付，不依赖模型厂商在线，模型停服不得影响用户查看旧报告。

## 6. 订单、支付、权益、交付和结算

### 6.1 五个对象不能混为一个状态

| 对象 | 回答的问题 | 主要状态 |
|---|---|---|
| Order | 用户想买哪一版商品、对应哪份内容 | created、closed |
| Payment | 钱是否由渠道确认 | pending、paid、refund_pending、refunded、failed |
| Entitlement | 用户现在可以生成、追问或查看什么 | available、reserved、consumed、reversed、expired |
| Reading Delivery | 正文生成到哪一步 | locked、queued、generating、accepted、visible、retryable_failure |
| Settlement | 平台实际结算了多少钱 | expected、settled、variance、held |

用户界面的“已购买”“生成中”“已完成”“已退款”是这些对象的投影，不反过来作为事实源。

### 6.2 订单幂等

同一用户、同一 Product Version、同一 Purchase Target：

- 已有未过期 pending 订单时复用该订单；
- 已 paid 但未 accepted 时返回“生成中”，不再创建订单；
- 已 delivered 时直接打开原报告；
- 已 refunded 时若用户再次购买，创建新订单和新商品交付链，但仍指向原事实简报或由用户主动重新准备；
- 订单默认 15 分钟支付有效，过期后关闭；未付款的付费 Purchase Target 保留 30 天供重新下单，之后清理其独立 runtime namespace。Profile Version 修改不会覆盖旧目标，用户付款前必须再次确认买的是旧版还是新版资料。

### 6.3 权益账本

Entitlement Ledger 只追加以下事实：

| 事件 | 含义 |
|---|---|
| GRANT | 支付或售后授予一份能力 |
| RESERVE | 某个 Job 临时占用一份能力 |
| RELEASE | Job 未完成，释放占用 |
| CONSUME | Accepted 落库后核销 |
| REVERSE | 退款或撤销使相关 Grant 失效 |
| EXPIRE | 到期后不再可用 |

每条记录包含 user_id、order_id、grant_id、scope、quantity、expires_at、idempotency_key、reason 和发生时间。管理员不能直接改“余额”，只能追加有理由、有操作者、有审计编号的事件。

### 6.4 一次购买的权益展开

支付确认时只 GRANT 一份“针对 Purchase Target 的正文生成权”。免费核对后重写额度也使用同一个 Ledger，由系统按 Profile Version GRANT 1 份 preview_revision 权益，不与付费余额混写。Worker 开始时 RESERVE，Accepted 后在同一个 PostgreSQL 事务中：

1. 保存 Accepted Copy；
2. CONSUME 正文生成权；
3. GRANT 正文访问权；
4. GRANT 商品承诺的 Follow-up 数量和有效期；
5. 写入 outbox 交付事件。

这样支付后生成失败，用户仍持有可重试的生成权；报告没有生成就不会扣掉。

### 6.5 退款与访问

- 重复支付：对重复订单自动进入退款流程；
- Accepted 前发生退款：取消 Job，释放 Reservation，REVERSE 生成权；
- Accepted 后渠道退款成功：REVERSE 正文访问权和未使用追问权，用户端不再展示付费正文；内部不可变正文仅用于最小化审计和争议处理；
- 退款不删除 Order、Payment、Ledger 或 Accepted 历史；
- Android/鸿蒙/Windows 的确定性系统交付失败超过 24 小时，可由服务端启动退款；
- iOS 无法由开发者主动发起退款，系统标记 refund_recommended，展示 App Store 路径，并在退款问询中提供真实交付状态；
- “觉得不准”不由算法自动判定退款，进入人工售后；平台最终退款结果始终服从渠道事件。

### 6.6 一个续费周期的权益展开

收到并验签渠道的续费成功事件后，在同一个 PostgreSQL 事务中：

1. 以渠道续费订单号幂等写入 Payment Event；
2. 创建或补齐该周期的 Renewal Order 快照，将 Subscription Cycle 标记为 paid；
3. 按该周期绑定的 Product Version 追加一组 GRANT，并让所有 Grant 的来源指向 cycle_id；
4. 将 Subscription Cycle 标记为 granted，写入 outbox 通知；
5. 后续每次生成仍单独 RESERVE，只有 Accepted 后才 CONSUME。

事务或通知中断时重放同一个外部续费订单号，不新建周期、不重复授予。扣款失败只把本周期标为 failed；当前已付周期继续到 `period_end`，之后没有新权益。模型厂商故障发生在履约侧，不得把已付款周期改成 failed。

## 7. 总体程序架构

~~~mermaid
flowchart TB
    MP["原生微信小程序\nTypeScript + WXML/WXSS"] --> API["FastAPI 业务 API\n模块化单体"]
    API --> DB[("PostgreSQL\n业务事实与任务事实")]
    API --> REDIS[("Redis/Tair\n缓存、限流、短租约")]
    API --> OSS[("私有 OSS\n用户主动导出的文件")]
    API --> OUTBOX["Transactional Outbox"]
    OUTBOX --> WORKER["同仓库 Worker\n租约式 Job 执行"]

    API --> PAYPORT["Payment Interface"]
    PAYPORT --> WXPAY["微信虚拟支付 Adapter"]

    WORKER --> RUNTIMEPORT["Mingli Runtime Interface"]
    RUNTIMEPORT --> JSONPROC["mingli-master JSON Adapter\n单次隔离进程"]
    JSONPROC --> RSTATE[("按 Reading Root 隔离的\n私有运行时状态卷")]

    WORKER --> NARRATIVEPORT["Narrative Interface"]
    NARRATIVEPORT --> MODEL["阿里云百炼国内模型 Adapter"]
    WORKER --> SAFETYPORT["Safety Interface"]
    SAFETYPORT --> SAFETY["本地规则 + 国内内容安全 Adapter"]
~~~

### 7.1 技术基线

- 小程序：微信原生框架，业务代码改为 TypeScript；
- API/Worker：Python、FastAPI、SQLAlchemy 2、Alembic；具体 Python minor 在实现时由容器与 lockfile 固定，命理运行时使用自己独立验签的解释器；
- 数据库：PostgreSQL；
- 缓存：Redis/Tair；
- 文件：私有 OSS，只存用户主动导出的 PDF/图片和必要售后凭证；
- 部署：阿里云 ECS 4C8G 起步，API 与 Worker 独立进程，Nginx/SLB 终止 TLS；
- 任务：PostgreSQL generation_jobs + lease + SELECT FOR UPDATE SKIP LOCKED，不把 Celery/Redis 队列作为唯一事实源；
- 协议：OpenAPI 生成小程序 TypeScript 客户端，禁止手写两套字段名；
- 形态：单仓库模块化单体，未来只有在真实容量或团队边界出现后才拆服务。

### 7.2 目标目录

~~~text
mingli_web/
  miniprogram/            # 微信原生 TypeScript 客户端
  server/
    app/                  # FastAPI 入口
    modules/              # 按领域 Module 分包
    worker/               # 任务租约与执行器
    adapters/             # 微信支付、模型、安全、JSON Runtime
    migrations/           # Alembic
    tests/
  contracts/              # OpenAPI 与产品/成稿 JSON Schema
  infra/                  # 部署、备份、监控
  docs/
  CONTEXT.md
~~~

当前根目录示例小程序会在正式实现第一阶段迁入 miniprogram，不在方向阶段边写边搬。

## 8. Module、Interface、Seam 与 Adapter

### 8.1 领域 Module

| Module | 拥有的数据 | 对外 Interface |
|---|---|---|
| Identity & Consent | User、Consent Record、账号删除请求 | establish_user、record_consent、request_deletion |
| Profile | Subject Profile、Profile Version | create_profile、create_version、get_version |
| Reading | Reading Root/Version、Brief、Accepted、Verification | begin、supply、continue、correct、get_reading |
| Billing | Product Version、Order、Payment、Refund、Settlement | quote、start_order、accept_notification、reconcile、request_refund |
| Entitlement | Ledger、Reservation 和余额投影 | grant、reserve、consume、release、reverse |
| Narrative | Drafting Packet、Candidate、Prompt Contract | compose、repair、render |
| Safety | 输入和 Candidate 的平台安全决定 | check_input、check_candidate |
| Delivery | Generation Job、lease、outbox | enqueue、claim、finish、retry |
| Audit & Reconciliation | 外部事件、结算差异、操作记录 | record_event、reconcile_day |

模块之间通过小 Interface 和同库事务协作，不允许页面 Controller 直接修改多个 Module 的表。

### 8.2 外部 Seam

**MingliRuntime Interface**

~~~text
execute(runtime_namespace, Command) -> Result
~~~

- 生产 Adapter：启动固定的 runtime_launcher，stdin 写一个 Command JSON，stdout 读取一个 Result JSON；
- 测试 Adapter：FakeMingliRuntime，按测试夹具返回四类 Result；
- Adapter 校验进程退出、单行 JSON、protocol_version、manifest_digest、Result kind 和超时；
- stderr 只进入脱敏诊断，严禁记录出生资料、问题正文和 state_token。

**Payment Interface**

~~~text
start_virtual_payment(OrderSnapshot) -> ClientPaymentParameters
verify_notification(HttpRequest) -> PaymentEvent
query_order(ExternalOrderRef) -> PaymentEvent
start_refund(RefundRequest) -> RefundState
~~~

- 生产 Adapter：WeChatVirtualPaymentAdapter；
- 测试 Adapter：FakePaymentAdapter；
- iOS 的主动退款不受支持时，Adapter 返回明确的 channel_action_required，不伪造成功。

**Narrative Interface**

~~~text
compose(DraftingPacket, Budget) -> NarrativeCandidate
~~~

- 首个生产 Adapter：阿里云百炼国内模型；
- 备用 Adapter：经过同一合同测试的低成本国内模型；
- 测试 Adapter：固定结构 Candidate；
- 模型 Adapter 只负责表达，不得读取数据库、支付状态或运行时 token。

**Safety Interface**

~~~text
check_input(InputEnvelope) -> SafetyDecision
check_candidate(NarrativeCandidate) -> SafetyDecision
~~~

- 本地确定性规则检查明确禁语、联系方式、PII 外泄和高风险决策语句；
- 外部内容安全 Adapter 处理开放文本；
- Safety 只能决定是否重写/停止，不得改盘或新增命理事实。

## 9. 数据模型与不可变约束

### 9.1 核心表

| 表 | 关键内容 | 不可变/唯一约束 |
|---|---|---|
| users | 微信身份映射、账号状态 | OpenID 映射唯一且加密保护 |
| subject_profiles | 受测档案身份与归属 | 只引用当前版本，不覆盖历史 |
| profile_versions | 规范化出生资料、时区、时间口径、摘要 | (profile_id, version_no) 唯一，写入后不更新 |
| consent_records | 同意/撤回、政策版本、用途 | 只追加 |
| reading_roots | user、capability、object、runtime_namespace、source_preview_root | 一个根只属于一个用户；免费根和付费根分离 |
| reading_versions | root、version、delivery_tier、query、intent、core_phase、加密 token | (root_id, version_no) 唯一 |
| brief_snapshots | Prepared.brief、digest、manifest_digest | 一个版本最多一份，不覆盖 |
| accepted_copies | Accepted.public_copy、digest、AI 标识版本 | 一个 Reading Version 最多一份；免费与付费用 delivery_tier 区分 |
| verifications | claim_ref、用户选择、补充说明 | 独立于 Brief 与 Accepted |
| generation_jobs | lease、attempt、budget、状态 | purchase_target + entitlement 唯一活动 Job |
| product_versions | SKU、金额、交付合同、平台 Product ID | 发布后不可编辑 |
| orders | 商品与目标快照、金额、外部单号 | 外部订单号唯一 |
| payment_events | 验签后原始事件摘要 | platform_event_id 唯一 |
| subscription_contracts | 用户、商品版本族、签约渠道、外部合同号、状态、当前周期边界 | 渠道 + 外部合同号唯一；同用户同商品族最多一个有效合同 |
| subscription_cycles | 合同、周期起止、续费订单、扣款与授予状态 | 合同 + 外部续费订单号唯一，写入后不覆盖历史 |
| settlement_records | 平台账单批次、渠道费、净额、预计/实际入账 | 渠道 + 账单行标识唯一 |
| entitlement_events | Grant/Reserve/Consume/Release/Reverse/Expire | idempotency_key 唯一，只追加 |
| refund_cases | 渠道、原因、问询、最终结果 | 外部退款号唯一 |
| outbox_events | 待交付领域事件 | event_id 唯一 |

### 9.2 数据规则

- 金额只用整数“分”，不使用浮点数；
- 所有服务端时间存 UTC；出生本地时间、IANA 时区和时间口径分别存；
- Profile Version 的 canonical digest 是 Reading 的输入依据；
- state_token 使用 KMS/应用数据密钥做信封加密，永不返回小程序；
- Brief、Accepted 和支付事件保存 SHA-256，便于重放比对；
- JSON 只保存外部协议快照和可审计结构，不用一个大 JSON 代替关系与约束；
- 拒绝的模型 Candidate 最长保留 24 小时用于排障，然后清除正文，仅保留错误码、digest、耗时和成本；
- 日志不写出生日期、详细地点、问题原文、模型全文、支付密钥或 runtime token。

### 9.3 运行时租户隔离

每个 Reading Root 在应用层先生成随机 runtime_namespace_id。MingliRuntime Adapter 将它映射到私有、分片的 MINGLI_STORE_ROOT：

~~~text
/var/lib/mingli-runtime/roots/ab/cd/{runtime_namespace_id}/
~~~

后端在调用前同时校验 user_id、reading_root_id 和 namespace 所有权。即使某个不透明 token 泄露到另一个账号，也无法切换到同一 namespace。运行时卷每日加密备份；业务数据库不尝试伪造核心内部存储。

## 10. 算法执行链

### 10.1 部署时的能力发现

1. 每次发布候选版本启动时调用一次 describe；
2. 校验 protocol_version 为当前已支持版本；
3. 保存 manifest_digest 和能力目录快照；
4. 合同测试确认 bazi、liuyao 的对象、维度、horizon 和必填字段仍兼容；
5. 只有产品 allowlist 内的能力可对用户开放；
6. manifest_digest 意外变化时阻断发布，不在生产中动态“猜着兼容”。

本轮已用安装制品真实执行 describe：protocol_version 为 mingli-portable-interface-v2，manifest_digest 为 7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342；bazi 与 liuyao 的对象、horizon 和必填输入与本蓝图一致。该摘要是首个合同夹具，不代表未来核心不能升级；升级必须先生成新夹具并跑完回归。

### 10.2 免费概览到付费交付

~~~mermaid
sequenceDiagram
    participant U as 用户
    participant A as Reading Application
    participant S as Safety
    participant R as Mingli JSON Runtime
    participant B as Billing/Entitlement
    participant N as Narrative
    participant D as PostgreSQL

    U->>A: 提交结构化资料/具体问题
    A->>S: 输入安全检查
    S-->>A: allow / stop
    A->>R: prepare 免费范围（无 token）
    alt need_input
        R-->>A: Stopped + input_request + token
        A-->>U: 只补真正缺失资料
    else 免费 prepared
        R-->>A: Prepared Free Brief + token
        A->>N: 生成有限 Preview Candidate
        N->>S: Preview 合同与安全检查
        N->>R: complete 免费 public_copy
        R-->>N: Accepted Preview
        A->>D: 保存免费 Brief 与 Accepted
        A-->>U: 原样展示免费 Preview
        U->>A: 主动选择付费商品并确认资料
        A->>R: prepare 付费范围（新根、无 token）
        R-->>A: Prepared Paid Brief + token
        A->>D: 保存付费 Purchase Target
        A-->>U: 展示价格与交付合同
        U->>B: 购买道具
        B->>D: Payment paid + GRANT generation
        B->>D: enqueue Generation Job
        N->>D: RESERVE generation
        N->>N: 按 Paid Brief 生成结构化 Candidate
        N->>S: 商品/事实/隐私/安全合同
        S-->>N: pass 或 repair
        N->>R: complete(exact public_copy)
        R-->>N: Accepted
        N->>D: Accepted + CONSUME + access/follow-up GRANT
        A-->>U: 原样交付 Accepted Copy
    end
~~~

### 10.3 prepare 输入规则

**八字免费概览**

- 使用独立的免费 Reading Root；
- capability_id 为 bazi，object_id 为 natal，horizon.kind_id 为 life；
- dimension_ids 只选择 overview 和 state；
- Candidate 通过 Preview Contract 后调用 complete，形成免费 Accepted。

**八字首份深度解读**

- 用户选择商品后建立新的付费 Reading Root，不携带免费 token；
- capability_id 明确为 bazi；
- object_id 为 natal；
- horizon.kind_id 为 life；
- dimension_ids 只提交 overview、state、career、relationship、timing；
- facts 来自已确认的 Profile Version；
- query 保留用户实际选择的解读范围，不额外发明“财富、疾病、灾祸”等主题。
- 如果用户希望付费报告参考此前核对，他必须在购买目标生成前确认一份可见的核对摘要；应用只把他刚确认的原意转写为本轮 query，Narrative 仍然只看到核心返回的新 Brief。

**六爻免费概览与付费一问**

- capability_id 明确为 liuyao；
- object_id 为 concrete_event；
- horizon.kind_id 为 instant；
- facts 必须含 cast、event_datetime、timezone 和 location；
- query 保留用户原问题，界面引导其一次只问一件具体事；
- 免费根只请求基础 state 范围并 complete；用户选择商品后，用同一输入在新付费根 prepare outcome、timing 等所选范围；
- 系统不得因缺资料静默换成梅花、奇门或其他能力。

入口已经确定术法，因此 P0 不需要关键词路由器。自然语言只负责保留问题和选择维度，不负责决定算法。

免费根与付费根都绑定同一个 Profile/Input digest 和同一个 manifest_digest。付费 Prepared 中与免费 Brief 重叠的 Public Fact 若出现矛盾，系统将其视为合同故障，禁止创建订单并进入人工排查；不能让用户付款后才看到两套盘。

### 10.4 四类 Result 的业务映射

| Result | 业务动作 |
|---|---|
| Described | 缓存能力目录，不创建 Reading |
| Stopped.need_input | 保存加密 token，按 input_request 补资料，不收费 |
| Stopped.unsupported/conflict/error | 原样展示安全说明，记录诊断，不收费、不重试换术 |
| Prepared（免费根） | 保存 Brief，生成 Preview Candidate，通过校验后立即 complete |
| Prepared（付费根） | 保存 Brief Snapshot 和购买目标，允许创建订单 |
| Accepted（免费根） | 原样展示 Preview，不产生付费 Consumption |
| Accepted（付费根/追问） | 校验返回正文与提交正文逐字一致，落库并核销对应权益 |

Prepared 的 Brief 是成稿唯一事实来源。付款前后、模型修复和重试都不能再次调用其他术法来“补一个更好听的结果”。

### 10.5 Drafting Packet

Narrative Module 收到的不是数据库全量上下文，而是最小 Drafting Packet：

~~~text
product_contract_version
reading_version_id
question
request_view
facts[]
findings[]
evidence[]
claim_scopes[]
limits[]
prior_accepted_copy?       # 仅同盘追问
ai_label_policy
~~~

不得加入：

- 用户未在本轮明确提供的宿主记忆；
- 未经过本轮核心 prepare、没有进入 Brief 的核对反馈或现实资料；
- 订单金额、用户付费等级或“高价用户写得更肯定”指令；
- Provider 私有 calculation；
- runtime token、文件路径、模型 API Key；
- 为了写满章节而推测的事实。

### 10.6 结构化 Candidate

模型先返回机器可验的 NarrativeCandidate，而不是直接返回最终长文：

~~~text
sections[]:
  section_id
  blocks[]
  fact_refs[]
  finding_refs[]
  evidence_refs[]
  limit_refs[]
global_limits[]
~~~

Validator 依次检查：

1. Product Contract 要求的章节是否齐全；
2. 所有引用是否存在于同一 Brief；
3. 每个命理判断是否落在对应 Claim Scope；
4. certainty 不超过 Brief 的 ceiling；
5. 没有把“不支持/资料不足”改写成确定结论；
6. 没有暴露他人资料、联系方式、内部 ID 或 token；
7. 没有医疗诊断、投资指令、恐吓、诅咒、保证应验或付费化解；
8. 显式 AI 标识和使用边界已进入最终正文；
9. 渲染后的 public_copy 非空且能稳定复现。

### 10.7 失败、修复和降级

单个 Job 最多执行：

1. 主模型首稿 1 次；
2. 带 Validator Findings 的定向修复最多 2 次；
3. 备用模型重写 1 次；
4. 仍失败则用经过验收的事实模板渲染。

模板也必须满足商品章节和引用合同。若模板无法满足，Job 进入 retryable_failure，RELEASE 权益，不调用 complete。任何修复都复用同一 Brief；严禁用重新 prepare 或换术来掩盖成稿失败。

### 10.8 complete 和首次提交胜出

调用 complete 前，Worker 保存 Candidate digest 和将要提交的 exact public_copy。调用后：

- Accepted：返回文本必须与提交文本逐字一致；
- 网络中断：用相同 token 和相同 public_copy 重试；
- 核心已经接纳但数据库事务失败：再次 complete 会返回第一次接纳的正文，随后补做数据库事务；
- 任何不同正文并发提交都不能覆盖第一次结果；
- Accepted 后不再过一层模型、不再删句、不再重新做命理正确性判断。

### 10.9 同盘追问、纠正与重新起盘

- Follow-up 使用最新 Accepted token，transition 为空；
- 核对反馈本身独立保存，不进入 Drafting Packet，也不自动触发重写；
- 免费概览的 3 条核对完成后，系统可按 Profile Version GRANT 1 次 preview_revision；用户确认反馈摘要并主动生成时，把该摘要如实作为下一轮 query，用免费根最新 Accepted token 和 transition=correct 重新 prepare，Accepted 后核销 preview_revision；
- 用户对付费正文指出表达与现实不符并明确要求调整时，同样以最新问题、最新 Accepted token 和 transition=correct 重新 prepare；只有核心返回的新 Brief 可以用于新 Reading Version，Accepted 后核销 1 次 Follow-up；
- 用户改出生时间、换卦、换人、换术或换问题对象时，应用创建新 Reading Root，并在新的 runtime namespace 中以无 state_token 的 prepare 开始；只用 recast_of_root_id 记录来源关系；
- P0 不跨 runtime namespace 调用 transition=restart；Recast 不算网络重试，也不能免费反复直到得到满意答案；
- 每个版本仍走 Prepared → Candidate → complete → Accepted 全链。

## 11. 应用状态与恢复

核心自己的合法 phase 只有 pending_input、prepared、accepted。应用层不篡改它，而是分别记录：

| 维度 | 状态 |
|---|---|
| Calculation | collecting、waiting_input、prepared、accepted、stopped |
| Billing | free、unpaid、paid、refunded |
| Subscription Contract | none、sign_pending、active、cancel_at_period_end、ended、revoked |
| Subscription Cycle | none、due、charge_pending、paid、granted、failed、refund_pending、refunded |
| Entitlement | unavailable、available、reserved、consumed、reversed、expired |
| Delivery | locked、queued、generating、visible、retryable_failure |

前端每次进入报告页都 GET 当前投影，不能依据本地按钮回调自己推进状态。

Worker 使用 5 分钟 lease 和心跳。崩溃后 lease 到期可被另一 Worker 接手；每一步以 job_id、reading_version_id 和 ledger idempotency_key 重放。重试不新建 Reading Root、不新建订单、不重复扣权益。

## 12. 内容安全、隐私与 AI 标识

### 12.1 输入前

- 先检查自由问题文本，再调用 prepare；
- 命中违法、有害、自伤、医疗急症或明确金融指令场景时，给适当边界提示，不让模型继续放大；
- 安全模块不分析或修改四柱、卦象等结构化事实。

### 12.2 成稿前

- Candidate 先做本地规则，再做外部内容安全；
- 被拒绝的 Candidate 可以重写，但不能改变 Brief；
- 所有由模型参与生成的免费或付费正文顶部都显示“AI 辅助生成”；
- 正文底部说明“基于传统命理规则与所填资料生成，仅供传统文化研究和自我观察，不替代医疗、法律、投资等专业意见”；
- 分享卡只从 Accepted 的用户主动选择摘要生成，默认隐藏姓名、出生日期、地点、四柱和问题原文。

### 12.3 用户数据

- 出生资料仅在用户触发建档时收集；
- 默认手选城市，不提前申请定位；
- 真太阳时需要坐标时单独解释用途并征得同意；
- 用户可以导出和删除档案、解读、追问与核对；
- 财务法定义务所需最小订单记录与可识别命理资料分离保存；
- 账号删除后，runtime namespace 进入延迟清除队列，清除动作可审计且不可恢复。

## 13. 关键失败场景验收

| 场景 | 必须得到的结果 |
|---|---|
| 用户连点两次购买 | 复用 pending 订单；最多一笔有效支付 |
| 客户端 success 丢失 | 推送或 query_order 补齐 Payment，用户最终得到权益 |
| 同一支付推送 15 次 | 一条 Payment 事实、一份 Generation Grant |
| 支付成功后 Worker 崩溃 | lease 到期续跑，权益仍为 reserved/available，不重复扣 |
| 模型首稿含恐吓语 | complete 前拦截并修复；核心事实不重算 |
| 核心 Accepted 后数据库断线 | 相同 token 重放得到第一次正文，补落库和核销 |
| 两个 Worker 同时 complete | 首次正文胜出，数据库只保存一个 Accepted |
| 生成最终失败 | RELEASE 权益，报告显示可重试，不显示“已使用” |
| 用户付款后修改出生时间 | 原订单仍绑定旧 Profile Version；新资料需新目标并明确确认 |
| 追问换成另一件事 | Scope Guard 拒绝沿用，创建新 Reading Root |
| Accepted 后退款 | 追加 Reversal，撤销访问，不删除内部历史 |
| 用户删除账号 | 删除命理可识别资料与运行时 namespace；保留最小法定财务记录 |
| describe manifest 变化 | 发布被合同测试阻断，不把新能力自动暴露给用户 |
| 续费成功通知重复 15 次 | 一个 Subscription Cycle、一笔 Payment、一次当期 GRANT |
| 用户退订但本周期未结束 | 标记 cancel_at_period_end，本期权益继续到期，不再创建下一周期 GRANT |
| 同一用户在另一端再次签约 | 查询到有效旧合同并阻止重复签约，提示到原渠道管理 |
| 模型账户欠费或厂商限流 | RELEASE 本次占用并排队重试/降级；不扣用户权益、不改变订阅状态 |

## 14. 测试与发布门槛

### 14.1 自动测试

- Domain 单元测试：Profile Version、Scope Guard、Ledger 投影、退款冲正；
- Runtime 合同测试：四类 Result、非空 Stopped、prepare/complete 重放、Accepted 首次提交胜出；
- Payment 合同测试：验签失败、重复推送、推送丢失、query 补单、退款推送；
- Subscription 合同测试：签约/解约、周期扣款、跨端去重、价格版本、重复续费通知、周期到期；
- Narrative 合同测试：未知 fact_ref、超出 certainty、缺章节、PII、恐吓和高风险建议；
- 数据库并发测试：两个 Worker、两个支付通知、Reservation lease 过期；
- 属性测试：账本不产生重复 Consumption，反复重放投影不变；
- 时间测试：UTC、Asia/Shanghai、子时策略、真太阳时字段和 Profile digest；
- 隐私测试：日志、错误追踪、导出和删除。

### 14.2 上线 Gate

1. 当前主体和真实业务类目完成小程序备案/审核预检；
2. 虚拟支付开通成功，平台道具审核通过；
3. Android/鸿蒙/Windows 沙箱完成支付、发货、查询和退款闭环；
4. iOS 现网低价测试完成一次购买、到账、查询和退款问询演练；
5. 当前 mingli-master describe digest 被锁定并通过 bazi/liuyao 合同测试；
6. 20 组八字和 20 组六爻固定输入能稳定重放，盘面事实不随模型变化；
7. 10 个盲测案例验证正文只使用 Brief 事实，不把现实答案倒灌回计算；
8. 断网、进程崩溃、重复推送和数据库重试演练全部通过；
9. 用户导出、删除、退款和投诉入口真实可用；
10. 任何对外“准确率”宣传都必须有前瞻、盲法、可复核样本；P0 默认不宣传百分比。

## 15. 监控和经营指标

### 15.1 技术指标

- prepare 成功率、need_input 率和各字段缺失率；
- Prepared 到 Preview 延迟；
- 支付确认到 Grant 延迟；
- Grant 到 Accepted 的 P50/P95；
- Candidate 首次通过率、修复次数、模板降级率；
- Runtime error/conflict、Job 重试和 lease 接管次数；
- 推送与 query_order 的差异数；
- 重复支付、退款和投诉处理时长；
- manifest_digest、product_contract_version、prompt_contract_version 分布。

### 15.2 产品指标

- 建档完成率；
- 3 条核对完成率和“暂时不知道”占比；
- Preview 到付款转化率，分别统计两种商品；
- 付费报告完成率；
- 追问使用率与到期未使用率；
- 7 日复访率；
- 技术原因退款率、主观售后退款率和重复支付率；
- 每单净结算、模型成本和人工售后成本。

指标用于发现流程问题，不把核对反馈汇总成未经验证的“命理准确率”。

## 16. 变更纪律

以下任何变化都必须写新 ADR，并提升相关合同版本：

- 改用代币、订阅或站外支付；
- 改变 Accepted 后还能否重写；
- 改变权益核销时点；
- 允许业务层直接 import 命理核心；
- 把档案或报告改成覆盖更新；
- 让模型自行选择术法或重新计算盘面；
- 将 PostgreSQL 之外的缓存/队列变成唯一业务事实源；
- 拆分服务导致支付、权益和 Accepted 不再能可靠补偿。

普通调价、换模型 Adapter、调整展示顺序和新增通过合同的商品，不修改旧版本，只创建新 Product/Prompt/Policy Version。

## 17. 实施顺序

### Phase 0：资格与合同

- 在小程序后台确认主体、类目、虚拟支付入口；
- 配置两个开发版道具；
- 锁定 describe digest；
- 建 OpenAPI、Product Contract 和 NarrativeCandidate Schema。

### Phase 1：免费闭环

- 迁移原生 TypeScript 小程序骨架；
- 完成 User、Consent、Profile Version；
- 完成 Runtime Process Adapter；
- 跑通 bazi/liuyao prepare、need_input、Brief、Preview；
- 完成历史记录、核对、导出和删除。

### Phase 2：支付与权益

- Product Version、Order、Payment Event；
- 虚拟支付调起、推送、query_order 和每日对账；
- Entitlement Ledger、Reservation 和重复推送测试。

### Phase 3：付费生成

- Drafting Packet、Narrative Adapter、Candidate Validator；
- Worker lease、修复、备用模型和模板降级；
- complete、Accepted 落库、核销和原样交付。

### Phase 4：追问、退款与发布

- Scope Guard、Follow-up、correct 和 Recast；
- Android 退款、iOS 退款问询、Reversal；
- 故障演练、真实设备验收、灰度发布。

### Phase 5：留存验证后的订阅（不阻塞 P0）

- 达到平台准入门槛并完成会员自动续费协议、商品和交互审核；
- 建 Subscription Contract/Cycle、跨端唯一约束和周期对账；
- Android/鸿蒙预扣费通知与扣款编排、iOS Apple 订阅通知与查询；
- 先用单次 30 天陪伴包验证成本和使用率，再通过 Feature Flag 灰度连续包月；
- 上线前在正式环境以最低风险账号完成签约、首扣、续扣、退订、退款和重复通知演练。

## 18. 参考依据

- [微信小程序虚拟支付](https://developers.weixin.qq.com/miniprogram/dev/platform-capabilities/business-capabilities/virtual-payment.html)
- [微信小程序虚拟支付 iOS 接入](https://developers.weixin.qq.com/miniprogram/dev/platform-capabilities/business-capabilities/virtual-payment/ios.html)
- [微信会员订阅：安卓/鸿蒙](https://developers.weixin.qq.com/miniprogram/dev/platform-capabilities/business-capabilities/vips.html)
- [微信会员订阅：iOS](https://developers.weixin.qq.com/miniprogram/dev/platform-capabilities/business-capabilities/vip.html)
- [阿里云百炼账单查询与成本管理](https://help.aliyun.com/zh/model-studio/bill-query-and-cost-management)
- [阿里云自动充值](https://help.aliyun.com/zh/user-center/use-alipay-online-banking-to-recharge-online)
- [阿里云 ECS 自动续费](https://help.aliyun.com/zh/ecs/enable-auto-renewal-for-an-instance-1)
- [微信小程序平台运营规范](https://developers.weixin.qq.com/miniprogram/product)
- [小程序开放的服务类目](https://developers.weixin.qq.com/miniprogram/product/material.html)
- [人工智能生成合成内容标识办法](https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm)
- 本地 mingli-master：JSON Adapter、ReadingInterface、interface_contracts、TurnEngine、StateTokenStore
- 本地「既济·源」：初步判断、现实核对、报告锁定、连续追问和事实纠正流程
- [FateTell 产品与商业模式访谈](https://news.qq.com/rain/a/20250617A08F8O00)，仅作为“按次 + 订阅”市场信号，不作为本项目定价证据

平台文档会动态更新。每次正式发布前重新核验支付、类目、费率和内容规范，但核验结果通过 Adapter 与配置进入系统，不推翻本蓝图的领域合同。
