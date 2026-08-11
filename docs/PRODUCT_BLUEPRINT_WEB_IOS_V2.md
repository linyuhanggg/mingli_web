# 命理网站商业化、账户与算法架构蓝图 v2.0

> 决策日期：2026-08-09  
> 状态：Accepted，当前权威合同  
> 适用范围：响应式网站 P0、连续服务 P1、原生 iOS P2  
> 取代：[PRODUCT_BLUEPRINT_V1.md](./PRODUCT_BLUEPRINT_V1.md) 中的小程序平台、登录和支付实现  
> 保留：V1 的命理核心、不可变版本、Accepted、权益账本与模型账务边界  
> 上位方向：[PRODUCT_DIRECTION.md](./PRODUCT_DIRECTION.md)  
> 共同语言：[CONTEXT.md](../CONTEXT.md)
> 算法接入细则：[MINGLI_V51_WEB_INTEGRATION.md](./MINGLI_V51_WEB_INTEGRATION.md)

## 0. 本文怎么用

这是一份进入实现后可以直接检查的合同，不是页面脑暴稿。

- 产品、设计、前端、后端、命理运行时和运营统一使用本文术语；
- 历史商品、订单、支付通知、权益事件和 Accepted Copy 不允许覆盖修改；
- 配置项可以换，领域事实不能因为换支付渠道、换模型或做 iOS 而重写；
- 如需改变“冻结合同”，必须新增 ADR，并同时给出数据迁移、回滚和合同测试；
- 外部平台规则会变化，本文把它们建模为发布 Gate，不把今天的审核结论硬编码为永久事实。

## 1. 一页结论

### 1.1 产品

首发产品是移动端优先、桌面端完整可用的响应式网站。首页不是聊天框，而是三个明确入口：建立个人档案、查看今日/近七日、问一件具体事情。

P0 采用“免费建立可信感，按明确结果单次付费”：

| 商品层级 | 用户得到什么 | 价格 |
|---|---|---:|
| 免费 | 一个本人档案、确定性八字排盘、有限概览、3 条事实核对、今日/近七日、六爻基础卦象 | ¥0 |
| 个人命盘深度解读 | 绑定一个档案版本的主题报告，永久查看，7 天内 3 次同盘追问 | ¥29.90 |
| 一事一问·六爻 | 绑定具体问题和卦象的事件报告，永久查看，72 小时内 2 次同盘追问 | ¥9.90 |

P0 不做自动续费、代币余额、永久无限 AI、自带 API Key、真人撮合或“保证应验”。

### 1.2 账户

内部 User UUID 是唯一账号根。P0 支持手机号验证码和邮箱验证码；微信 OAuth 在商户条件具备时增加。未来 iOS 增加 Sign in with Apple。不同身份可以绑定到同一个 User，不能把手机号、邮箱、OpenID 或 Apple subject 当业务主键。

### 1.3 支付

网站按环境选择官方网页支付产品：

- 微信内浏览器：微信 JSAPI 支付；
- 手机普通浏览器：微信 H5 支付和支付宝手机网站支付；
- 桌面浏览器：微信 Native 二维码和支付宝电脑网站支付；
- 原生 iOS：StoreKit 2，不展示站外数字内容购买入口。

所有渠道只负责产生资金事实。业务后端统一建立 Order、Payment、Refund、Subscription Cycle 和 Entitlement Ledger。

### 1.4 算法

mingli-master 负责确定性事实、古籍证据、边界和连续状态；Reading Orchestrator 用普通代码执行固定状态机；一个独立大模型只负责把 Fact Brief 写成结构化自然中文；业务层负责账户、商品、支付、权益、任务与交付。

免费 Preview 和付费报告都是完整的 prepare → candidate → validate → complete → Accepted 流程，但属于不同 Reading Root。

P0 不运行 Agent，不让模型调用工具、选择术法、访问数据库或管理连续状态。正常路径只直接调用一次模型。

### 1.5 技术

- Web：Next.js App Router + TypeScript，具体版本在脚手架建立时锁定；
- API：Python + FastAPI 模块化单体；
- Worker：与 API 共用领域代码，独立进程；
- 数据：PostgreSQL 为事实源，Redis 只做缓存、限流和短租约，私有 OSS 存报告附件；
- 部署：阿里云 ECS 4 核 8G 可承载 P0 Web/API/Worker，不承载大模型推理；
- iOS：后续原生 SwiftUI + StoreKit 2，共用 OpenAPI 和后端领域模型。

## 2. 冻结合同与可配置项

### 2.1 冻结合同

1. 网站优先，原生 iOS 后续；微信小程序不在当前首发路线。
2. User 与登录渠道分离，跨端共享一个账号根。
3. 商品语义与支付渠道分离，同一 Product Family 可有多个 Channel Offer。
4. 支付、权益、生成、交付分离，客户端回跳不作为到账依据。
5. 权益账本只追加；使用时先占用，Accepted 落库时才核销。
6. 档案、Fact Brief 和 Accepted Copy 不可变版本化。
7. mingli-master 是唯一命理事实核心，业务代码不复制或 import 其内部实现。
8. 模型不算盘、不造证据、不决定权益，也不接触支付密钥。
9. Accepted 后原样交付；修复只能产生新的 Reading Version。
10. P0 两种单次商品；P1 订阅只在数据和渠道准入通过后开放。
11. 网站与 iOS 共用商品族和权益语义，但渠道商品 ID、价格和退款规则可以不同。
12. 采用模块化单体和深模块接口，不以页面或支付渠道为边界拆微服务。
13. P0 使用显式 Reading Orchestrator 和单独大模型，不引入 Agent loop；所有自然语言校验在 complete 前完成。
14. Runtime Release 始终完整迁移和验收 5.1 的 13 个 Provider、全部算法、55/55 古籍 reference pack 与 1328 条 evidence index；P0 的三能力 allowlist 只控制产品曝光，不得用于裁剪制品或测试。

### 2.2 可配置项

- 首页素材、文案、卡片排序和视觉动效；
- 新 Product Version 的价格、追问次数和期限；
- Model Gateway 后面的模型供应商、模型版本、超时和重试；
- 支付渠道开关、商户号和路由优先级；
- 新术法的灰度开关，但必须先通过 describe 和合同回归；
- 免费额度和风控阈值，但不能影响已经下单的商品快照。

## 3. Metis 与开源仓库参考结论

### 3.1 可参考的公开事实

截至 2026-08-09 的公开页面与静态前端信号显示：

- 首页采用编辑型大标题、固定导航、编号模块和大场景卡片；
- 起盘可以先填写资料，登录后才跨设备保存；
- 账户公开呈现手机号、邮箱、验证码、密码和身份绑定；
- 专业版页采用 Free/Pro 对照、一次性买断和清晰 FAQ；
- 前端包含微信 Native 二维码、支付宝、订单查询和补开通路径；
- 当前公开页面同时提示在线支付可能暂时不可用，因此不能把“页面出现入口”当成支付已经稳定开通；
- App 分支隐藏网页购买路径，说明其产品也在处理 Apple 数字内容规则。

### 3.2 开源边界

[ziwei-doushu](https://github.com/Renhuai123/ziwei-doushu) 的 README 明确写明：排盘算法、知识库和前端可用，后端 API、用户系统、短信、会员、支付、安全和部署不在开源范围内。

因此本项目可以：

- 参考其移动适配、出生表单、排盘工作区和设计 token；
- 在实际复制 MIT 代码时保留 LICENSE 和版权声明；
- 如使用其样本数据，按其 README 做来源标注并先审核体系一致性。

本项目不会：

- 复制 METIS 品牌、图片、文案、私有 API 或支付参数；
- 把其 51.8 万样本直接灌入 mingli-master 或模型训练；
- 假设公开前端中的账户、支付实现就是完整且安全的后台合同；
- 复制把长期凭据保存在 localStorage 的做法。

### 3.3 我们吸收后的 UI 原则

1. 首页先展示三种真实任务，再讲技术和术语；
2. 游客先体验，保存、追问和付款前再登录；
3. 价格页并排展示“免费能做什么”和“这次付款具体得到什么”；
4. 结果页先结论、再原因、再边界、再核对和来源；
5. 视觉用自有深墨绿、米白、低饱和金色，不复制黑白 METIS 品牌；
6. 动效只帮助理解层级，不能阻塞起盘、付款和无障碍访问。

## 4. 产品表面与路由

### 4.1 公共表面

| 路由 | 核心内容 | 缓存/索引 |
|---|---|---|
| / | 价值、三任务、方法、示例、价格入口 | SSR，可 CDN，可索引 |
| /pricing | 免费与单次商品、追问、售后 | SSR，可索引 |
| /methodology | 计算、证据、AI 边界、版本说明 | SSR，可索引 |
| /support | 账号、付款、报告、删除与联系 | SSR，可索引 |
| /privacy | 信息处理、第三方、保存和权利 | SSR，可索引 |
| /terms | 服务、付费、AI 标识与争议处理 | SSR，可索引 |

### 4.2 私人应用表面

| 路由 | 任务 | 登录要求 |
|---|---|---|
| /app | 今日、近七日、继续和待核对 | 登录后完整 |
| /app/profile/new | 建档与资料确认 | 试算可游客，保存需登录 |
| /app/profiles | 档案及版本 | 必须 |
| /app/ask/liuyao | 问题、摇卦、录卦 | 基础可游客，保存需登录 |
| /app/readings | 历史、生成状态和报告 | 必须 |
| /app/readings/:id | 已接纳正文、核对和追问 | 必须且鉴权 |
| /account | 身份、设备、订单、数据权利 | 必须 |

私人表面统一：noindex、Cache-Control: private, no-store、禁止公共 CDN 缓存、禁止在 URL 和埋点中出现出生资料或问题正文。

### 4.3 响应式规则

- 360px 起可完成所有核心流程；
- 手机单列，结果内容优先；桌面端允许左侧任务导航、中央正文、右侧依据；
- 付款弹层在手机改为全屏步骤页，桌面可用二维码弹层；
- 表单错误就近显示，并提供页面级错误摘要；
- 点击目标至少 44 × 44px；键盘可完成登录、建档和支付选择；
- 支持 prefers-reduced-motion；不依赖颜色单独表达状态。

## 5. 账户与身份

### 5.1 核心对象

**User**：内部 UUID，拥有档案、解读、订单和权益。

**Login Identity**：一个已验证登录入口，字段包括 provider、provider_subject、verified_at、status。provider_subject 在业务查询需要时加密或哈希处理。

**Device Session**：某台设备的一次可撤销登录关系，不等同于 User。

**Guest Session**：短期匿名会话，只能持有未确认草稿和免费试算关联。

### 5.2 P0 登录能力

| 方式 | P0 | 说明 |
|---|---|---|
| 中国大陆手机号 OTP | 必做 | 主入口，限流、防短信轰炸 |
| 邮箱 OTP | 必做 | 备用和海外号码兜底 |
| 微信网页 OAuth | 条件开放 | 商户和开放平台配置通过后启用 |
| 密码 | 不做 | 后续按真实需求新增身份类型 |
| Sign in with Apple | iOS 阶段 | 与已有 User 安全绑定 |

登录页面先让用户选择手机号或邮箱，不把注册和登录拆成两个令人困惑的入口：验证码验证成功后，无 User 就创建，有 User 就登录。

### 5.3 游客认领

1. 浏览器创建随机 Guest Session Cookie；
2. 游客提交资料后，服务端建立最长 24 小时的加密草稿；
3. 草稿不进入正式 Profile Version，也不跨设备承诺保存；
4. 用户登录后，通过一次性 claim token 把草稿归入 User；
5. claim 必须幂等，一个草稿只能归属一个 User；
6. 未认领草稿到期删除，日志不保留正文。

### 5.4 Web 会话

- 会话 Cookie 使用 HttpOnly、Secure、SameSite=Lax 或更严格策略；
- 状态修改请求使用 CSRF token 或严格同源双重保护；
- 服务端只保存 refresh/session token 的哈希；
- 登录、换绑、合并、撤销和删除账号写审计事件；
- 高风险操作要求近期重新验证；
- localStorage 只允许保存无敏感偏好，如主题和语言。

### 5.5 iOS 会话

- 原生客户端通过一次性授权码换取设备会话；
- refresh token 只保存在 Keychain；
- Universal Link/OAuth 回调必须绑定 state、nonce 和 PKCE；
- App 删除不等于账号删除；账号删除由统一后端流程执行。

### 5.6 身份绑定与合并

绑定新身份要求当前会话重新验证，再验证新身份。若新身份已属于另一个 User，不能自动合并：

1. 验证两个账号的控制权；
2. 展示档案、订单和订阅冲突摘要；
3. 选择保留的 User 根；
4. 在事务中迁移归属并写不可变审计事件；
5. 对重复有效订阅停止自动合并，转人工售后。

## 6. 商品目录

### 6.1 三层目录模型

**Product Family**：跨渠道稳定的商品语义，例如 BAZI_DEEP_READING。

**Product Version**：某一时点的价格、交付、追问和有效期快照。一旦被订单引用就不可修改。

**Product Offer**：面向特定渠道的可售映射，例如 WEB_CNY、IOS_APPSTORE_CHN；保存渠道商品 ID、展示价格、币种、税费和启用状态。

这样以后接 iOS 时不需要把 Apple product_id 塞进业务商品，也不要求网站与 App Store 价格完全相同。

### 6.2 P0 商品版本

#### BAZI_DEEP_READING_V1

- 标价：人民币 29.90 元；
- Purchase Target：一个 Prepared 的档案版本和 Fact Brief；
- 交付：主题深度报告；
- 查看：Accepted 后永久；
- 追问：同一 Reading Root 下 3 次，Accepted 起 7 × 24 小时内有效；
- 新出生资料、新术法或新问题范围不属于追问。

#### LIUYAO_ONE_QUESTION_V1

- 标价：人民币 9.90 元；
- Purchase Target：明确问题、卦象、起卦方式与时刻形成的 Prepared 目标；
- 交付：事件解读；
- 查看：Accepted 后永久；
- 追问：同一 Reading Root 下 2 次，Accepted 起 72 小时内有效；
- 换问题、换卦或重新起卦必须建立新的购买目标。

### 6.3 免费能力

- 每个 User 一个本人 Subject Profile；
- 每个 Profile Version 一次原始免费 Preview；
- 完成 3 条核对后，每个 Profile Version 一次核对后 Preview；
- 今日/近七日为轻量摘要，不承诺逐日深度报告；
- 六爻免费展示基础卦象和起卦记录，不交付完整事件分析；
- 免费频率限制属于 Abuse Policy，不用“金币”展示给用户。

### 6.4 明确不卖

- 永久无限 AI；
- 用户自带模型 Key；
- 模型 Token 或充值余额；
- 准确率保证、改运、消灾、择股、诊断或治疗；
- P0 自动续费；
- 付费后仍不清楚能得到什么的笼统会员。

如果未来出售永久功能，只能覆盖无持续推理成本的静态能力或已生成内容访问，不能承诺无限期新增模型计算。

## 7. 网站支付

### 7.1 环境路由

| 环境 | 首选 | 备选 |
|---|---|---|
| 微信内置浏览器 | 微信 JSAPI | 提示在其他浏览器使用支付宝 |
| 手机普通浏览器 | 支付宝手机网站支付 | 微信 H5 支付 |
| 桌面浏览器 | 微信 Native 二维码 | 支付宝电脑网站支付 |
| iOS 原生 App | StoreKit 2 | 无站外数字内容购买按钮 |

支付方式是否显示由服务端 Payment Capability 配置决定，前端不能仅凭 User-Agent 假装某渠道可用。

### 7.2 下单前提

1. 用户已登录；
2. Product Version 仍可售；
3. Purchase Target 已 Prepared，摘要和哈希已展示给用户确认；
4. 用户明确看到价格、交付、查看期限、追问次数、退款规则和 AI 标识；
5. 后端按 User + Product Version + Target + Idempotency Key 建立 Order；
6. 金额用整数最小币种存储，例如 2990 分，禁止浮点计算。

### 7.3 真实支付判定

前端回跳、JSAPI success、二维码关闭或“我已付款”只改变界面提示。到账必须来自：

- 验签通过的支付通知；或
- 后端主动查询渠道后得到的确定成功状态。

通知处理必须验证签名、商户号、应用 ID、订单号、金额、币种和渠道交易号。channel + transaction_id 建唯一约束，重复通知安全重放。

### 7.4 支付与交付时序

~~~text
Prepared Target
  → Order CREATED
  → Payment Attempt PENDING
  → 渠道确认 SUCCEEDED
  → 同事务记录 Payment Event + Entitlement GRANT + Outbox
  → Worker RESERVE
  → 生成与校验
  → Accepted Copy 落库 + CONSUME + Fulfillment DELIVERED
~~~

支付成功但模型暂时失败时，订单仍是已付款，权益不得核销。系统自动重试；超过时限后释放占用，并向用户提供继续生成或按售后政策退款的入口。

### 7.5 二维码与移动跳转

- 二维码由服务端订单生成，默认 5 分钟失效，失效只关闭本次 Payment Attempt；
- 重新生成二维码建立新 Attempt，但继续绑定同一 Order；
- 桌面页面轮询本后端 Order 状态，不直接轮询渠道；
- 支付宝/微信回跳页只展示“正在确认”，直到后端状态落定；
- 不在二维码、return_url 或渠道备注中放出生信息、问题正文或姓名。

### 7.6 退款

Refund 是独立资金事实：

1. 后台或用户申请建立 Refund Request；
2. 按交付状态、渠道规则和已公示政策审批；
3. 渠道确认后追加 Refund 和 Entitlement REVERSE；
4. 内部订单、支付、报告与审计记录不删除；
5. 用户访问权按冲正后的投影计算，已经下载的内容无法技术性收回；
6. 不在服务条款里用一句“虚拟商品一概不退”代替真实法律和渠道审核。

## 8. 自动续费与自有模型

### 8.1 两条完全不同的账务链

**用户账务链**：支付渠道向用户扣款，产生 Payment 或 Subscription Cycle，再授予 Entitlement。

**企业成本链**：公司向模型 API、GPU、ECS、短信、邮件、OSS 等供应商付款，由云账户自动充值、资源自动续费、预算和告警保障。

自有模型不会让网站自动获得扣用户钱的能力，也不会让 Apple 放弃内购要求。

### 8.2 P1 订阅模型

P1 只考虑一个“连续陪伴”Product Family，必须持续提供可感知的新价值，例如周期内容、阶段复盘和当期追问额度。价格在留存和成本数据出来前不冻结。

领域对象分开：

- Subscription Contract：渠道签约关系；
- Subscription Cycle：一次已确认付款的计费周期；
- Cycle Entitlement：该周期新授予的额度和有效期；
- Cancellation：阻止未来续费，不回收已付周期；
- Refund/Reversal：渠道确认退款后的反向事实。

签约成功不等于首期扣款成功；合同 active 不等于当前一定有权益；只有成功 Cycle 才授予当期权益。

### 8.3 网站周期扣款

- 微信委托/周期扣款与支付宝周期扣款都以商户实际获批为 Gate；
- 签约、解约、扣款、补扣、查询和通知分别实现；
- 每个渠道周期号和商户周期号都有唯一约束；
- 扣款失败不创建权益，重试由渠道规则和用户授权范围控制；
- 用户在账户页能看到当前渠道、下次日期、取消方式和已有周期。

### 8.4 iOS 自动续期订阅

- 使用 StoreKit 2 展示和购买；
- App Store Server API 与 Server Notifications V2 同步交易；
- originalTransactionId 归入一个 Subscription Contract；
- 每个 verified transaction 形成不可变 Cycle；
- 退款、撤销、Billing Retry、Grace Period 按 Apple 已验证状态投影；
- App 内不放网页购买按钮，也不用客服文案暗示站外更便宜。

P0 的两种单次报告在 iOS 中映射为可重复购买的 Consumable IAP，而不是只能买一次的 Non-consumable：同一用户可能为不同档案或不同问题购买多份报告。购买前先建立内部 Order 和 Prepared Target；购买时用 appAccountToken 关联 User，服务端再以已验证 transaction_id、product_id 和未使用 Order 完成绑定。每个交易只能授予一次权益。Consumable 本身不能靠 StoreKit“恢复购买”，永久报告访问由本产品账号下的服务器历史恢复。

### 8.5 防止跨端重复订阅

1. 同一 User、同一 Subscription Group 建“最多一个可续费合同”的业务约束；
2. 创建新签约前查询已有合同并引导到原渠道管理；
3. 并发仍可能发生，因此最终以唯一冲突记录转人工处理；
4. 网站购买的数字内容可在 iOS 查看，但 iOS 中提供的同类解锁也必须配置相应 IAP；
5. 不把 Apple 商品价格强行等同于网站价格，Product Offer 独立版本化。

### 8.6 模型供应自动续费

- 外部模型 API：企业账户开自动充值上限、日/月预算和余额告警；
- 自托管模型：GPU/推理服务单独部署并设置资源续费、容量和故障告警；
- 4 核 8G 业务 ECS 不承担大型模型推理；
- 模型欠费、限流或宕机触发备用适配器或延迟交付，不改用户订单和订阅事实；
- 历史 Accepted Copy 不依赖模型在线即可查看。

## 9. 深模块架构

系统是一个部署简单、内部边界严格的模块化单体。模块提供小接口，隐藏复杂状态机和表结构。

~~~mermaid
flowchart LR
    W["Next.js 网站"] --> A["FastAPI /api/v1"]
    I["未来 SwiftUI iOS"] --> A
    A --> ID["Identity"]
    A --> PR["Profiles"]
    A --> RD["Readings"]
    A --> BL["Billing"]
    BL --> EN["Entitlement Ledger"]
    RD --> EN
    A --> DB["PostgreSQL"]
    RD --> Q["Outbox / Worker"]
    Q --> OR["Reading Orchestrator"]
    OR --> MR["Mingli Runtime Adapter"]
    OR --> MG["Standalone Model"]
    MG --> NG["Narrative Guard"]
    NG --> OR
    Q --> OS["Private OSS"]
    A --> R["Redis"]
    BL --> WX["WeChat Pay"]
    BL --> AP["Alipay"]
    BL --> AS["Future App Store"]
~~~

### 9.1 Identity Module

负责 User、Login Identity、Guest Session、Device Session、绑定、合并、撤销和账号删除编排。对外只暴露验证身份、签发/撤销会话和解析当前 User 的接口。

### 9.2 Profile Module

负责 Subject Profile、不可变 Profile Version、资料规范化、Consent Record 和游客草稿认领。它不计算命理结果。

### 9.3 Catalog Module

负责 Product Family、Product Version、Product Offer、可售条件和展示快照。价格变化只能新增版本。

### 9.4 Billing Module

负责 Order、Payment Attempt、Payment Event、Refund、Subscription Contract/Cycle 和渠道适配器。它不生成报告，也不直接改“会员布尔值”。

Payment Gateway 最小接口：

- create_checkout(order, offer, environment)
- verify_notification(raw_request)
- query_payment(attempt)
- request_refund(payment, amount, reason)
- query_refund(refund)

未来周期支付在独立 Recurring Gateway 接口增加 sign、charge_cycle、cancel、query_contract，避免让一次支付接口长成万能类。

### 9.5 Entitlement Module

负责 GRANT、RESERVE、RELEASE、CONSUME、REVERSE、EXPIRE 追加事件和当前投影。它通过 Purchase Target、scope、quantity、valid_from 和 valid_until 判断是否可用。

### 9.6 Reading Module

负责 Reading Root/Version、Fact Brief、生成任务、核对反馈、同盘追问、Fulfillment 和 Accepted Copy。内部 Reading Orchestrator 以显式代码状态机编排运行时、模型、Guard 和权益，但不读取支付渠道细节，也不是 Agent。

### 9.7 Mingli Runtime Module

只通过固定 JSON 进程协议调用 mingli-master 的 describe、prepare、complete；校验协议版本、输出种类、digest、超时和状态命名空间。P0 由一个固定路径、私有状态卷的 Runtime Worker 持有真实状态，API 多副本不得各自运行一份核心。提供 Fake Runtime 做合同测试。

### 9.8 Model Gateway

输入固定 Narrative Request，输出结构化 Candidate Copy。它只是直接模型 API 适配层，不提供工具、记忆、规划或自主循环；统一处理超时、预算、模型标识和有限重试。用户不能提供 API Key。

### 9.9 Narrative Guard

以普通代码验证 Candidate schema、subject/dimension、fact/finding/evidence 引用闭合、certainty ceiling、limits、商品长度与平台边界。当前 5.1 的 complete 只验证 token、非空正文和首次原子提交，所以 Guard 是 complete 前的强制网站责任，不是第二个评审模型。

### 9.10 Compliance/Audit Module

集中处理 Consent、AI 标识、敏感字段脱敏、数据导出/删除、审计事件和内容风险标签。它不能在 Accepted 后偷偷改正文；风险校验必须在 complete 前完成。

## 10. 仓库与部署边界

目标目录在实施时建立：

~~~text
web/                     Next.js 应用
backend/app/             FastAPI 与领域模块
backend/worker/          异步任务入口
contracts/openapi/       Web、iOS、服务端共享接口合同
contracts/schemas/       Fact Brief、Candidate、Accepted 等 JSON Schema
infra/                   部署模板、反向代理和观测配置
tests/contract/          跨模块、支付、运行时合同测试
~~~

旧小程序骨架已在 Git 提交 `15cbc95` 中完整保全；迁移确认后从当前工作树移除，不沿用为网站架构。

### 10.1 生产拓扑

- Nginx/负载入口：TLS、静态缓存、限速、同源反向代理；
- Next.js Node 进程：公共 SSR 与私人应用壳；
- FastAPI：/api/v1；
- Worker：读取 PostgreSQL Outbox/任务表并执行生成、补单、通知和导出；
- Runtime Worker：P0 单副本、固定非 root UID、固定安装路径和独立持久云盘，串行调用 5.1 JSON Adapter；
- PostgreSQL：唯一业务事实源；
- Redis/Tair：缓存、限流、OTP、短租约，不保存唯一业务事实；
- 私有 OSS：导出文件和需要对象存储的报告附件；
- 外部 Model Gateway：P0 不与业务 ECS 同机部署大模型。

Web 与 API 对用户保持同一站点域名，减少 CORS、Cookie 和支付回调复杂度。内部可以是不同进程和端口。

### 10.2 环境

- local：Fake Payment、Fake Model、Fake Mingli Runtime 可独立跑；
- staging：独立数据库、独立对象桶、渠道沙箱或受控小额实测；
- production：独立密钥、商户号、域名和日志索引；
- 生产数据不能复制到测试环境，问题复现使用脱敏夹具。

## 11. 数据模型

### 11.1 身份与隐私

- users
- login_identities
- device_sessions
- guest_sessions
- consent_records
- account_merge_events
- data_export_jobs
- deletion_requests

### 11.2 档案与解读

- subject_profiles
- profile_versions
- reading_roots
- reading_versions
- fact_briefs
- generation_attempts
- accepted_copies
- verifications
- followups
- fulfillment_jobs

### 11.3 商品、资金与权益

- product_families
- product_versions
- product_offers
- orders
- payment_attempts
- payment_events
- refunds
- subscription_contracts
- subscription_cycles
- entitlement_events
- entitlement_projections

### 11.4 运行与审计

- model_runs
- runtime_releases
- runtime_invocations
- outbox_events
- inbox_events
- audit_events

### 11.5 关键约束

1. login_identities(provider, provider_subject) 唯一；
2. accepted_copies(reading_version_id) 最多一条；
3. payment_events(channel, channel_transaction_id) 唯一；
4. subscription_cycles(channel, channel_cycle_id) 唯一；
5. orders 的 product_version_id 和 target_digest 不可变；
6. entitlement_events 只插入不更新，projection 可重建；
7. 金额为整数最小币种并保存 currency；
8. 所有外部通知同时保存原始摘要、验签结果和处理结果，不在普通日志打印敏感原文；
9. Profile Version、Fact Brief、Accepted Copy 保存内容 digest 与生成版本；
10. 软删除不能替代符合法律和审计要求的数据删除/最小保留流程。

## 12. 状态机

### 12.1 Order

~~~text
CREATED → PAYMENT_PENDING → PAID
   └──────────────→ CLOSED
PAID → REFUND_PENDING → PARTIALLY_REFUNDED | REFUNDED
~~~

Order 不包含“报告生成成功”状态。Fulfillment 单独表示交付。

### 12.2 Payment Attempt

~~~text
CREATED → PENDING → SUCCEEDED
                 ├→ FAILED
                 └→ EXPIRED/CLOSED
~~~

同一 Order 可以有多个 Attempt，但只能按真实成功金额授予一次对应权益。

### 12.3 Reading Version

~~~text
DRAFT → PREPARED → GENERATING → VALIDATING → COMPLETING → ACCEPTED
                       └→ RETRYABLE_FAILED
                       └→ TERMINAL_FAILED
~~~

只有 ACCEPTED 能产生交付和 Consumption。任何失败都不能假装“部分成功”。

### 12.4 Fulfillment

~~~text
PENDING → PROCESSING → DELIVERED
                    └→ RETRYABLE_FAILED
                    └→ MANUAL_REVIEW
~~~

### 12.5 Entitlement

事件固定为：GRANT、RESERVE、RELEASE、CONSUME、REVERSE、EXPIRE。余额和是否可访问均由事件投影，不存一个可随意修改的 paid/member 布尔值。

## 13. 命理算法与成稿链

### 13.1 输入规范化

原始输入与规范化结果都保存，但分开字段：

- 原始公历/农历选择、闰月选择和用户输入；
- IANA timezone 与 UTC 时刻；
- 出生地文本、坐标、坐标来源和精度；
- 是否使用真太阳时、使用的经度和校正结果；
- 不确定时辰的明确状态，不能默认为“确定的子时”；
- 历法与规范化器版本；
- 用户最后确认的展示摘要和 digest。

前端可以解释口径，但不能自行产生业务唯一的四柱或卦象事实。权威规范化和计算发生在服务端确定性层。

### 13.2 Capability 发现

部署或升级时调用 mingli-master describe，保存：

- 协议版本；
- 可用 Capability；
- 每项输入 schema；
- 输出种类；
- 核心 release digest。

产品只开放 allowlist 中、通过黄金样例和回归测试的 Capability。核心新增能力不能自动出现在网站。

Runtime 制品与准入范围固定为完整 13 项：`bazi`、`fengshui`、`fortune`、`liuren`、`liuyao`、`luming-nayin`、`meihua`、`physiognomy`、`qimen`、`selection`、`taiyi`、`xingming`、`ziwei`。部署必须同时验证 13/13 Provider readiness、完整 manifest、55/55 古籍 reference pack、1328 条 evidence index 和 release 全量回归；未开放的十项也不得从镜像或验收中移除。

Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。

P0 产品 allowlist 另行固定为 `bazi`、`fortune`、`liuyao`：本命与深度解读走 bazi，今日/近七日走 fortune，一事一问走 liuyao。术法由页面和 Product 映射决定，不增加模型路由调用。其余十项是“已安装并通过 Runtime 准入、尚未建立产品入口”，后续补齐表单、输出合同、合规与产品回归即可灰度开启，不需要重做核心迁移。

### 13.3 Prepare

Reading Module 将不可变 Profile Version 或六爻输入交给 Runtime Adapter。prepare 返回：

- Fact Brief；
- 可表达事实与限制；
- 命中古籍证据；
- 不透明连续状态；
- digest 和协议元数据。

业务侧加密保存连续状态，只把必要 Fact Brief 发送给 Model Gateway，不把用户全量账号信息放进模型请求。

完整古籍与 evidence index 留在核心侧：Provider 先按本次计算结果和问题范围筛选证据，再把命中的 evidence 投影进 Fact Brief。模型不能浏览整库、不能自由检索未命中资料，也不能补造出处；古籍零命中必须保持零。

`Stopped.need_input` 按结构化 `input_request` 补资料并复用同一 token；`unsupported/conflict/error` 不通过换术法或改语义盲重试。不带 token 的 prepare 会创建新 Reading Root，结果不明时不得自动重放。

### 13.4 Candidate 生成

Narrative Request 固定包含：

- 版本化 Narrative Policy；
- Product Output Contract 的长度、语言和结构上限；
- Prepared 返回的完整 Fact Brief；
- 严格 Candidate JSON Schema。

模型不能访问工具、网络、RAG、数据库、账户资料、`state_token` 或环境记忆。续问需要的最近正文只使用 Brief 自带的 `prior_answer`。Candidate 以自然段 block 加 subject/dimension/kind/certainty 和 fact/finding/evidence/limit refs 返回；block 是内部校验轨迹，不是强制可见标题。只有用户明确选择的报告商品才能要求固定章节。

### 13.5 Complete 前校验

校验顺序固定：

1. JSON/schema 完整；
2. subject、dimension、kind 与 claim scope 一致；
3. fact/finding/evidence 引用存在且闭合；无命中时不得生成伪出处；
4. certainty 不超过 ceiling，所需 limits 使用核心公开文本；
5. 商品承诺的章节、长度和追问边界；
6. 不泄露内部 Provider、规则 ID、token、prompt 或置信字段；
7. 医疗、法律、投资、心理和重大人生决策边界；
8. 隐私、辱骂、仇恨、自伤等内容安全；
9. AI 生成/辅助标识元数据。

5.1 的公开 complete 不会替网站复核这些自然语言条件，只会检查 token、非空与首次提交。P0 失败时最多用同一 Brief、同一模型重生一次；仍失败则延迟交付，不换术法、不重新起盘、不用模板生成付费 Accepted。

### 13.6 Complete 与 Accepted

校验合格后才调用 complete。核心返回 Accepted 后：

1. 在同一业务事务中保存 Accepted Copy、内容 digest 和交付元数据；
2. 追加 Entitlement CONSUME；
3. 更新 Fulfillment 为 DELIVERED；
4. 写 Outbox 通知事件；
5. 后续 API 原样返回 Accepted 内容，不二次改写。

如果核心已经 Accepted 而业务事务在落库前崩溃，Worker 以同一 token 和完全相同的 public_copy 重放 complete，取回第一次 Accepted 后再落库与核销，不能重新生成一稿。

### 13.7 核对反馈

Verification 只记录符合、部分符合、不符合、不知道及可选说明。它不能改 Profile Version、Fact Brief 或 Accepted Copy。

用户要求依据反馈调整表达时：

- 在同一 Reading Root 新建 Reading Version；
- Runtime prepare 产生新的 Brief/digest；
- 反馈作为受控结构输入，不把用户说明直接拼进系统提示词；
- 旧版本仍可审计和查看。

### 13.8 同盘追问

追问必须同时满足：

- 同一 User 有访问权；
- 同一 Reading Root、Capability 和 Subject；
- 问题仍在原购买范围；
- 有未过期 Follow-up Entitlement；
- 最近版本已 Accepted。

换出生资料、换卦、换事件主题或要求新时间范围时，界面明确提示 Recast，并建立新的免费或付费目标，不能偷偷消耗追问。

## 14. 模型策略

### 14.1 自有模型接入

“自有”可以是公司控制的 API、微调模型或独立推理服务。P0 以一次普通服务端请求直接调用，不运行 Agent SDK。统一通过 Model Gateway：

- 输入输出 schema 固定；
- 服务端保存供应商、模型、版本、请求 digest、延迟、成本和错误类别；
- 密钥只在服务端 Secret Manager/环境注入；
- Web 和 iOS 永远不知道模型密钥；
- 自托管推理与业务 API 独立扩缩容。

### 14.2 失败与回退

1. 主模型正常生成一次；
2. schema 或 Guard 失败时，用同一 Brief、同一模型最多重生一次；
3. 仍失败则延迟交付并保留/释放权益 Reservation；
4. 备用模型只有完成独立评测并发布新 Model Profile 后才能启用。

P0 不用模板生成付费 Accepted Copy，也不在后台静默切换供应商。没有任何候选稿通过校验时，宁可延迟，也不能把未校验文字标为 Accepted。

### 14.3 成本控制

- 为每个 Product Version 配置最大模型预算和最大尝试次数；
- 相同 Fact Brief 可缓存候选辅助结果，但不能跨 User 泄露正文；
- Accepted Copy 永久直接读数据库/对象存储，不重复调用模型；
- 免费能力有匿名和账号级限流；
- 成本异常只触发熔断和排队，不篡改已售商品。

## 15. API 合同

OpenAPI 以 /api/v1 开始。下面冻结资源语义，具体字段在实现前由 schema 文件锁定。

### 15.1 身份

- POST /api/v1/auth/otp/request
- POST /api/v1/auth/otp/verify
- POST /api/v1/auth/logout
- GET /api/v1/account
- GET /api/v1/account/sessions
- DELETE /api/v1/account/sessions/:id
- POST /api/v1/account/identities/bind
- POST /api/v1/account/merge

### 15.2 档案

- POST /api/v1/guest-sessions
- POST /api/v1/profile-drafts
- POST /api/v1/profile-drafts/:id/claim
- POST /api/v1/profiles
- GET /api/v1/profiles
- GET /api/v1/profiles/:id/versions
- POST /api/v1/profiles/:id/versions

### 15.3 解读

- POST /api/v1/readings/preview
- POST /api/v1/readings/prepare-purchase
- GET /api/v1/readings/:id
- GET /api/v1/readings/:id/status
- POST /api/v1/readings/:id/verifications
- POST /api/v1/readings/:id/followups

### 15.4 订单与支付

- POST /api/v1/orders
- GET /api/v1/orders/:id
- POST /api/v1/orders/:id/checkout
- POST /api/v1/orders/:id/reconcile
- POST /api/v1/payments/wechat/notify
- POST /api/v1/payments/alipay/notify
- POST /api/v1/apple/notifications
- POST /api/v1/refund-requests

所有会产生写入或外部副作用的用户请求必须支持 Idempotency-Key。Webhook 使用渠道事件唯一键进入 Inbox，业务事件通过 Outbox 发布。

## 16. 隐私与安全

### 16.1 数据分类

出生日期、时间、地点、性别、问题正文、联系方式、命理解读和核对反馈统一按高敏感业务数据保护，即使某个单独字段在法律定义下未必属于敏感个人信息。

### 16.2 存储与传输

- 全站 HTTPS，HSTS 在域名验证后启用；
- 联系方式、出生资料、问题正文和运行时连续状态字段级加密；
- 数据库、备份和对象存储加密；
- 报告下载需当前授权或短时单用途签名；
- 日志、埋点、错误追踪默认脱敏，不记录 OTP、Cookie、模型 Key、完整出生资料和正文；
- 密钥不进仓库、不进客户端 bundle、不进聊天和工单。

### 16.3 Web 防护

- CSP、frame-ancestors、Referrer-Policy、Permissions-Policy；
- Cookie 会话 + CSRF 防护；
- OTP、登录、起盘、免费生成和支付查询分层限流；
- 防短信/邮件轰炸、撞库、二维码枚举和 IDOR；
- 所有资源按 User 授权，不能只凭可猜 ID；
- Service Worker 只缓存公共壳和静态资源，不缓存 /api、私人 HTML、报告或账户页。

### 16.4 数据权利

账户页提供：

- 查看已绑定身份和设备；
- 导出档案、解读和核对记录；
- 删除单个档案；
- 发起账号删除；
- 撤回非必要同意；
- 联系人工处理更正、退款和争议。

财务和安全审计所需的最小记录按法定义务单独保留并去标识化，不能用“用户删号”直接删除对账事实，也不能借审计之名无限期保留全部出生资料。

### 16.5 模型数据

- 默认只传本次生成需要的 Fact Brief 和问题，不传真实姓名、联系方式和订单信息；
- 若模型服务可能跨境，必须在供应商接入前完成数据地图、合同、保存期限和同意/其他合法基础审查；
- 供应商不得把请求用于训练的要求应写入合同或选择相应配置；
- 缓存键包含租户/访问边界，禁止仅按命盘内容做跨用户可读缓存。

## 17. 网站与 iOS 的合规 Gate

这些项目会随政策和主体变化，作为上线前动态清单，不由业务代码猜测。

### Gate A：网站主体与备案

- 中国大陆服务器提供公开网站前完成 ICP 备案；
- 付费经营使用合适的企业或个体工商户主体，不以个人备案承担商业网站；
- 网站开通后按要求完成公安联网备案并在页脚展示真实链接；
- 在线交易或其他经营范围是否需要增值电信许可，由上线时的主体、业务和所在地主管部门确认；
- 域名、服务器、备案主体、支付商户和隐私政策主体保持一致或有可解释关系。

### Gate B：支付商户

- 微信 JSAPI/Native/H5 与支付宝电脑/手机网站支付真实获批；
- 生产商户号、应用 ID、回调域名和证书配置完成；
- 沙箱与受控小额实测通过创建、支付、重复通知、查询、关闭和退款；
- 周期扣款未获批时，对外 UI 和商品目录均关闭订阅。

### Gate C：AI 与内容

- 页面显著标识 AI 生成或辅助生成；
- 服务条款写明传统文化参考边界；
- 高风险问题有阻断/劝阻和专业求助提示；
- 对外分享保留必要 AI 标识；
- 模型供应商、数据位置和保存期限与隐私政策一致。

### Gate D：iOS

- 数字内容和功能使用 IAP；
- 网站已购内容若在 App 使用，同类内容在 App 内也有对应 IAP；
- 不在 App 内引导站外购买，除非上线时明确符合 Apple 允许的 storefront/entitlement 条件；
- 有第三方/社交登录时提供符合 4.8 的等价登录方式，计划使用 Sign in with Apple；
- 支持恢复购买、管理订阅、账号删除和隐私清单；
- App Store Server Notifications 的退款、撤销和续期回归通过。

## 18. 可观测性与财务对账

### 18.1 业务指标

- 首页到开始建档；
- 建档开始到资料确认；
- 免费 Preview Accepted 率和耗时；
- 核对完成率，而不是对外宣传“准确率”；
- Prepared Target 到下单、支付和交付；
- 付费后首次 Accepted 时间；
- 追问使用、退款、投诉和复访。

### 18.2 技术指标

- API p50/p95/p99；
- Worker 队列深度和最老任务年龄；
- Runtime prepare/complete 成功率；
- Model Gateway 按模型的延迟、错误、重试、校验通过率和成本；
- Payment 通知延迟、补单数量、金额差异和重复事件；
- Entitlement Reservation 超时和投影重建差异。

### 18.3 每日对账

每日按渠道账单核对：

- 渠道成功金额与本地 Payment；
- 退款金额与 Refund；
- 成功支付与 GRANT；
- Accepted 与 CONSUME；
- 永久访问权益与交付对象；
- 不一致进入人工队列，不用脚本直接改历史记录。

## 19. 测试合同

### 19.1 确定性与算法

- 历法、时区、真太阳时、闰月和未知时辰黄金样例；
- 同一输入、同一核心版本产生同一 Fact Brief digest；
- 完整 13-Provider describe/readiness 冻结快照与 Product allowlist 分层回归；
- Mac mini 原生 CPython 3.14.6、Node.js/iztro 依赖、Runtime Release 验签和启动 describe；
- 13 个 Provider characterization/smoke matrix 与 release 全量回归；
- 55/55 古籍 reference pack、1328 条 evidence index 的完整性与引用闭合；
- bazi/fortune/liuyao 准确 Request Compiler 夹具；
- 古籍零命中保持零；
- 追问产生新 digest 且复用同一 Reading Root；
- 换资料、换卦和换问题正确识别为 Recast；
- Runtime 状态盘备份恢复与旧 token 重放。

### 19.2 模型与 Accepted

- Candidate schema、subject/dimension、fact/finding/evidence/limit 闭合测试；
- 模型幻觉证据被 complete 前拦截；
- 单模型一次成功、一次有限重生和延迟交付；
- Accepted 后 API 原样返回；
- 并发 complete 只有一个首次 Accepted 胜出。

### 19.3 支付与权益

- 相同 Idempotency-Key 不重复下单；
- 重复、乱序和伪造通知；
- 客户端回跳但渠道未付款；
- 渠道已付款但通知丢失，查询补单；
- 多 Payment Attempt 只有一次 GRANT；
- Worker 崩溃后 Reservation 恢复；
- Accepted 与 CONSUME 原子一致；
- 退款与 REVERSE 可重放；
- 订阅重复周期通知不重复授予。

### 19.4 Web E2E

- 360px 手机、平板和桌面；
- 游客试算 → OTP 登录 → 草稿认领；
- 微信内、普通手机和桌面支付路由；
- 付款等待、超时、补查和失败恢复；
- 删除、导出、撤销设备；
- 键盘、读屏标签、对比度和 reduced motion；
- Service Worker 不缓存私人响应。

### 19.5 iOS 阶段

- StoreKit 配置和沙箱购买；
- 恢复购买；
- 续期、取消、Billing Retry、Grace、退款和撤销；
- Apple 登录与已有手机号/邮箱账号绑定；
- 网站已购内容可读且 App 内无站外购买引导。

## 20. 实施顺序

### Phase 0：立项与外部 Gate

- 确认运营主体、域名、备案路线和支付申请；
- 确认模型供应商、数据位置和预算；
- 归档精确 mingli-master 5.1 release、source commit、manifest 和测试源码；
- 建立并审计 Mac mini 原生 Runtime、固定状态路径和恢复手册；
- 建立版本控制，给旧小程序骨架做历史提交；
- 冻结 OpenAPI/JSON Schema 的第一版命名。

### Phase 1：网站壳与身份

- 建立 web、backend、contracts、infra；
- 公共首页、价格、方法、支持、隐私和条款；
- Guest Session、手机号/邮箱 OTP、Device Session；
- noindex、缓存、安全头和基础观测。

### Phase 2：免费闭环

- Profile Draft/Version；
- 完整 13-Provider Runtime Release 的单副本 Worker、describe/prepare/complete 与 Reading Orchestrator；
- P0 Product Capability Policy 只曝光 bazi/fortune/liuyao；
- 单独模型 Candidate Schema、Narrative Guard 和 Accepted 崩溃恢复；
- 免费 Preview、3 条 Verification；
- 今日/近七日；
- 六爻基础起卦；
- 历史和数据删除/导出。

### Phase 3：单次付费

- Catalog、Order、Payment、Refund；
- 微信 JSAPI/Native/H5 与支付宝电脑/手机网站适配器；
- Entitlement Ledger、Outbox/Inbox；
- 两种付费 Reading 和追问；
- 每日对账和售后台。

### Phase 4：生产验收

- 备案、公安、隐私、支付商户和 AI 标识 Gate；
- 安全测试、压力测试、备份恢复和灾难演练；
- 小范围真实用户与小额支付；
- 指标、成本和投诉复盘后公开发布。

### Phase 5：P1 连续服务

- 先验证复访和持续价值；
- 申请并验证网站周期扣款；
- 灰度 Subscription Contract/Cycle；
- 不达留存或成本门槛就保持单次付费。

### Phase 6：原生 iOS

- SwiftUI 客户端和共享 OpenAPI；
- Sign in with Apple；
- StoreKit 2 商品、通知和恢复购买；
- 跨端账号/权益回归；
- TestFlight 与 App Review Gate。

## 21. P0 发布验收

> 状态映射（2026-08-12 起生效，见 `docs/PRODUCTION_READINESS.md`）：本节 15 条全部通过 = **Feature Complete**，只代表功能完整；对外上线另需 Production Ready（全部 Gate 绿）、Canary 与 General Availability 三个阶段。任何材料不得用「第一版完成」暗示已上线或已达 99.9%。

以下全部通过才算第一版完成：

1. 手机和桌面均可完成建档、登录、免费解读、支付、查看和追问；
2. 游客草稿认领幂等且不串号；
3. 账户凭据不在 localStorage；
4. 私人页面 noindex/no-store，Service Worker 不缓存个人数据；
5. 订单绑定 Prepared Target，付款后不能换目标；
6. 支付通知验签、查单补偿和每日对账通过；
7. 重复通知、并发 Worker 和退款不破坏权益账本；
8. 模型失败不核销，Accepted 后原样交付；
9. 档案、Fact Brief、Accepted Copy 可按版本复现；
10. 数据导出、删除、撤销设备和人工支持可用；
11. 备案、支付、隐私、条款、AI 标识和经营许可检查有书面证据；
12. 备份恢复、日志脱敏、密钥轮换和告警演练通过；
13. Mac mini `native-full` 完成 Runtime Release 逐文件验签，13/13 Provider、全部依赖、55/55 古籍 reference pack、1328 条 evidence index 和 1584/0 全量回归；P0 三能力端到端黄金回归另行通过；
14. `state_token` 未进入客户端或日志，状态卷恢复后旧 token 可继续/重放；
15. 正常路径只有一次模型调用，Guard 前不 complete，Accepted 后字节不变。

## 22. 外部依据快照

以下链接用于说明 2026-08-09 做决策时的公开依据；正式上线前仍需重新核验。

### 参考产品

- [Metis紫薇首页](https://metisziwei.com/)
- [Metis 起盘页](https://metisziwei.com/chart)
- [Metis 账户页](https://metisziwei.com/account)
- [Metis 专业版](https://metisziwei.com/subscription)
- [Metis 隐私政策](https://metisziwei.com/privacy)
- [Renhuai123/ziwei-doushu](https://github.com/Renhuai123/ziwei-doushu)

### 网站支付

- [微信支付产品文档](https://pay.weixin.qq.com/doc/v2)
- [微信网页支付能力](https://pay.weixin.qq.com/static/partner_ability/web_payment.shtml)
- [微信 JSAPI 支付结果说明](https://pay.weixin.qq.com/doc/v3/merchant/4012791857)
- [支付宝手机网站支付](https://opendocs.alipay.com/open/203/105285)
- [支付宝电脑网站支付](https://opendocs.alipay.com/open/270/105899)
- [支付宝周期扣款](https://opendocs.alipay.com/open/20190319114403226822)

### 网站与 App 合规

- [阿里云 ICP 备案服务器要求](https://help.aliyun.com/zh/icp-filing/basic-icp-service/user-guide/icp-filing-server-access-information-check)
- [阿里云网站备案与公安联网备案说明](https://help.aliyun.com/zh/document_detail/3043304.html)
- [阿里云 App 备案说明](https://help.aliyun.com/zh/icp-filing/basic-icp-service/getting-started/quick-sta-rt-for-icp-filing-for-personal-app)
- [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Apple StoreKit](https://developer.apple.com/storekit/)

## 23. 最终取舍

Metis 值得参考的是“先给用户一个好用的网页入口、账号保存历史、用清晰价格页完成转化”；不值得复制的是把持续模型成本装进永久无限承诺，或让浏览器本地状态承担跨端事实。

本项目的长期护城河不是某个页面，也不是某个模型，而是：可复现的确定性事实、可核对的边界、不可变解读历史、渠道中立的权益账本，以及网站和 iOS 都能复用的深模块接口。
