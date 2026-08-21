# 命理产品共同语言

本文只定义全仓库共同语言。产品范围与进度看 `docs/CHECKLIST.md`，视觉看 `DESIGN.md`，算法接入看 `docs/MINGLI_V51_WEB_INTEGRATION.md`。同一个概念不得在页面、API、数据库和后台各叫一套名字。

## 产品与能力

**基础术数产品（Base Art Product）**
用户能独立完成输入、免费确定性盘面和后续深读的产品。固定为八字、紫微、七政、六爻、奇门、大六壬、见相七项。

**跨术产品（Composite Product）**
按照固定组合组织多个基础术数结果的独立产品。2026-08-14 起固定为两个：命盘合参（原三术合参，使用八字、紫微、七政且至少选择两术，可带着具体问题进入，吸收原多盘问答 `canwen` 的流程）；问事合参（固定使用六爻、大六壬、奇门）。多盘问答不再是独立顶级产品，其历史任务、报告与路由重定向不失效。它们不是任意 Provider 选择器。

**双人合盘（Relationship Reading）**
甲乙两个明确 `ProfileVersion` 加关系类型构成的双人、单术产品。八字、紫微、七政各有独立入口；它不属于三术合参。

**内部 Provider（Runtime Provider）**
`mingli-master` Runtime 中的一种确定性能力模块。完整发布物当前有 13 个 Provider；Provider 不等于产品页面，也不会因为 `describe` 可见就自动开放。

**产品能力策略（Product Capability Policy）**
版本化地声明产品、输入合同、所需 Provider、ViewModel、免费范围、深读范围和发布状态。模型不能选择或改变它。

**能力发布状态（Capability Release State）**
固定状态机：`UI_PREBUILT → ADAPTING → INTERNAL_TEST → PUBLIC → PAUSED`。只有 `PUBLIC` 可供普通真实用户运行；`PAUSED` 只阻止新任务，不删除历史交付。

**UI 验收中心（UI Lab）**
仅开发和测试环境开放的 `/_ui-lab`。它使用明确标记的 Fixture 预制所有页面和状态；Fixture 与真实数据共用同一版本化 ViewModel，但绝不进入正常产品路由。

## 人、身份与权限

**用户（User）**
拥有档案、任务、报告、订单和权益的内部账号根，以随机 UUID 标识。手机号、邮箱和第三方 subject 都不是 User 本身。

**游客会话（Guest Session）**
匿名浏览器持有免费任务草稿与短期盘面的关系。注册或登录后可以原地认领；它不是永久匿名账号。

**登录身份（Login Identity）**
绑定到 User 的已验证登录入口，如手机号或邮箱。第一版使用手机号/邮箱加密码主登录，OTP 用于注册验证、快捷登录和找回密码。

**密码凭据（Password Credential）**
User 的不可逆密码哈希及其版本信息。任何页面、日志或管理员都看不到密码明文；后台只能触发重置和撤销会话。

**设备会话（Device Session）**
浏览器或原生设备上的可撤销登录关系。撤销会话不会删除 User 或其他设备。

**公开邀请身份（Referral Public Identity）**
用户主动设置的公开昵称与头像，只用于邀请页和邀请进度。未设置时显示“一位好友”，不得从真实姓名、手机号或邮箱推导。

**员工（Staff User）**
独立 Admin 系统中的管理账号。固定角色为 `support`、`finance`、`ops`、`superadmin`，权限由服务端 RBAC 强制执行。

**授权记录（Consent Record）**
用户对一个确定版本的隐私政策、服务条款、照片用途或他人资料处理作出的同意或撤回事实；保存版本、时间、用途和来源。

## 受测对象与资料

**受测档案（Subject Profile）**
被排盘或见相的人。它与账号所有者分离，可标记本人、伴侣、子女、父母、朋友、客户或自定义关系。

**档案版本（Profile Version）**
受测档案在某一时刻确认的不可变资料快照。修改出生时间、地点、性别或观察资料会产生新版本，不覆盖旧版。

**任务句柄（Task Handle）**
URL 中恢复输入或工作台的不透明标识。出生资料、问题正文、照片地址和 `state_token` 不得出现在 URL。

**盘面任务（Chart Task）**
把某个 ProfileVersion、术数输入或事件输入转成确定性盘面的任务。免费盘面任务与深读任务分开建模。

**盘面快照（Chart Snapshot）**
一个确定输入、Runtime Release 和 ViewModel 版本产生的不可变确定性盘面。档案后续修改不改变旧快照。

**媒体资产（Media Asset）**
见相上传的原图、裁切图、缩略图或标注图。它有明确用途、保存期限、访问授权和删除状态，不是公开 URL。

**结构化观察（Structured Observation）**
视觉观察适配器从图片产生的版本化部位、区域和置信度数据。它不做身份识别，也不直接下命理结论。

## 算法、解读与报告

**命理核心源码工作树（Mingli Core Source Checkout）**
`core/mingli-master` 是从原版仓库 `mingli-master-skill` 移植进本仓库的权威算法源码，随 `mingli_web` 一起版本管理。网站不直接 import 它；开发修改先进入该目录，再经过发布门禁生成 Runtime Release。原版 skill 仓库的 Git 历史仍在 `mingli-master-skill`，不把移植时留下的嵌套 `.git` 当作本仓库历史。

**算法运行时发布物（Runtime Release）**
经过验签和原生全量回归、安装在 `.runtime` 或生产固定路径的完整 `mingli-master` 制品，包含 13 Provider、算法、古籍证据与协议资产。它是源码工作树的生成结果，不是编辑入口；任意工作树或散落目录不是发布物。

**事实简报（Fact Brief）**
Runtime 在写作前提供的不可变闭世界事实、finding、evidence、claim scope、limit 和 request view。模型只能使用本次 Brief，不能另查命理事实。

**解读根（Reading Root）**
同一受测对象、资料版本、术数/盘面和问题范围下的一条连续解读。换人、换资料、换卦、换事件、增加新照片或扩大时间范围会新建 Root。

**解读版本（Reading Version）**
Reading Root 上的一次不可变交付或追问。原报告、追问一、追问二严格线性推进，不从旧版本分叉。

**解读编排器（Reading Orchestrator）**
普通业务代码实现的有限状态机，负责 prepare、模型生成、Guard、complete、恢复和权益核销。它不是 Agent，也不产生命理事实。

**判断候选（Claim Candidate）**
模型基于 Fact Brief 生成的结构化原子短判断。每条绑定 subject、dimension、certainty 和 fact/finding/evidence/limit 引用；它尚未接纳，不能直接交付。

**公开 Runtime Claim Unit（Public Runtime Claim Unit）**
核心 Runtime 在 `Prepared` Brief 中枚举的、带 `public_text` 的公开 finding。它必须绑定本轮的 fact refs 与 `verified_exact` evidence refs，正文是核心确定性投影，不是模型改写，也不是硬裁定。当前八字源码有三个固定单元：`bazi.month-order-state-v1`、`bazi.ziping-pattern-entry-v1`、`bazi.tiaohou-priority-v1`；都保留“未裁定”边界，`hard_verdict` 仍为空。源码有这些单元不等于隐藏签名 V53 Release 已包含它们。

**成稿守门（Narrative Guard）**
在 complete 前执行的确定性校验，检查结构、引用闭合、表达范围、限制、隐私和商品合同。八字深读还要求每个 block 逐字等于一个直接引用的公开来源，并拒绝跨 block 复用同一来源或相同文本。它不是第二个评审模型。

**展示合同（Presentation Contract）**
服务端针对某一产品版本定义的章节、槽位、顺序、数量、字数、固定声明和专用 renderer 合同。模型不生成栏目、按钮或免责声明。

**已接纳正文（Accepted Copy）**
通过 Guard 后首次提交给 Runtime 并原样接纳的不可变文字凭证。Accepted 后不得截断、改写或二次润色。

**结构化解读文档（ReadingDocumentV1）**
与同一次 Accepted Copy 一起固化的不可变报告文档，包含版本化章节、判断卡、依据引用、限制、现实核对入口和展示元数据。Web、PDF、分享与后台消费它，不再拆字符串或猜 JSON。

**现实核对事件（Verification Event）**
用户对一条判断追加“符合、部分符合、不符合、暂时无法验证”及现实说明的事件。它不修改盘面、Brief、Accepted Copy 或后续模型输入。

**报告整体反馈（Report Feedback）**
用户在报告末尾对清晰度、帮助程度和是否解决问题作出的独立评价。它用于产品质量统计，不替代逐条 Verification Event；未经另行授权，报告正文、照片和身份资料不得因此进入训练。

**资料纠正（Input Correction）**
用户指出出生资料、卦象、关系、照片观察等输入错误。它产生新 ProfileVersion、盘面或任务；不能靠改旧报告处理。

**同盘追问（Follow-up）**
绑定已交付报告或判断卡、保持同一对象/版本/术数/盘面和允许时间范围的线性续问。只有追问 Accepted 才消耗一次追问权益。

**重新起盘（Recast）**
因资料、卦局、事件、照片、术数或问题范围变化而创建的新任务与 Reading Root。

## 商品、支付与权益

**商品族（Product Family）**
跨渠道稳定的一种数字交付语义，例如“八字单盘深度解读”。它不是页面卡片、会员布尔值或渠道 SKU。

**商品版本（Product Version）**
某次发布的不可变交付、价格语义、追问次数/期限和使用范围快照。价格或交付改变时新增版本。

**渠道报价（Product Offer）**
ProductVersion 在某个支付渠道上的可售映射，包含渠道 SKU、币种、展示价格和启用状态。

**购买目标（Purchase Target）**
订单绑定的具体 Chart Snapshot、ProfileVersion、ReadingRoot 或其他交付目标，防止一次购买解锁任意内容。

**订单（Order）**
用户购买某 ProductVersion 和 PurchaseTarget 的意图；它不等于支付或交付。

八字深读公共 checkout 只接受本人 `reading_version_id`。服务端必须确认该 Reading Version 属于当前登录 User、产品族是 `bazi-deep`、只有一个启用中的 Offer，并由服务端从 Reading Root 生成 Purchase Target；客户端不能提交任意 `offer_id` 或目标引用来换绑其他结果。

**支付尝试（Payment Attempt）**
订单通过一个渠道发起的一次结账尝试。失败或超时可重试，但不能重复授予权益。

**支付（Payment）**
服务端通过验签通知或主动查单确认的资金事实。客户端跳转或“支付成功”页面不是到账依据。

当前实现的 Fake gateway 只返回 `unavailable`，不能伪造支付成功；由于还没有能证明订单与回调 payload 绑定的安全支付 Provider 回调，真实线上付款暂时关闭。测试中的本地 `verified` confirmation 只证明后端状态合同，不是线上收款能力。

**退款（Refund）**
支付渠道确认的资金返还。它追加权益冲正，不删除订单、支付或历史报告。

**订阅合同（Subscription Contract）**
未来用户明确签署的周期扣款关系；第一版不开放自动续费。模型厂商账务与用户订阅完全分离。

**订阅周期（Subscription Cycle）**
订阅合同下经渠道确认付款的一次独立周期。每个周期独立授予有明确有效期的权益。

**权益（Entitlement）**
支付、活动、测试或售后赋予用户的可交付能力，包含来源、范围、次数、目标和有效期。

**权益账本事件（Entitlement Event）**
只追加的 `GRANT → RESERVE → CONSUME / RELEASE / REVERSE / EXPIRE` 事件。余额与可访问状态由投影得出，不允许直接改余额或覆盖历史。

**交付（Fulfillment）**
购买目标获得可访问的 Accepted Copy、ReadingDocumentV1 及商品承诺内追问权益。支付成功不等于交付完成。

`delivery_state` 是给本人看的交付投影：`payment_required → queued → processing → delivered`，失败时进入明确的延迟/恢复状态。它不把内部 `ReadingJob` 状态泄露给 Web，也不允许页面靠猜测“等待支付”或无限轮询。

## 邀请活动

**邀请活动版本（Referral Campaign Version）**
一个默认关闭、可定时开始/暂停/结束的不可变活动规则快照，明确 ProductVersion 白名单、总名额、个人上限、奖励槽和条款版本。

**邀请码（Invitation Code）**
邀请链接 `/invite/{code}` 中不含 PII 的公开代码，服务端映射到活动和邀请人。二维码和手工码使用同一代码。

**临时归因（Temporary Attribution）**
游客在注册前打开有效邀请产生的可清除关系。多个链接以注册确认前最后一个有效邀请为准。

**锁定归因（Locked Attribution）**
创建正式账号时再次校验并永久锁定的邀请关系。每个新 User 全局最多一个 Locked Attribution；它不因后续活动、链接或购买而换绑。既有账号、自邀和重复归因不成立；普通员工不能换绑。

**奖励名额占用（Reward Reservation）**
合格订单进入真实支付时原子占用的活动名额。失败、关闭或超时释放，支付成功转为已承诺奖励。

**邀请奖励（Referral Reward）**
向邀请人授予与受邀人首笔合格购买相同 ProductVersion 的权益。奖励不是现金、余额、报告或受邀人数据。

**邀请申诉（Referral Appeal）**
对拒绝或冲正提供的一次可解释复核入口。确定违规只追加 REVERSE 和未来限制，不删除已交付报告或制造负余额。

## 内容、通知与证据

**运营内容（CMS Content）**
首页、每日、工具说明、知识内容、帮助、公告、FAQ 和政策文本的版本化可发布内容。CMS 不得编辑盘面事实、算法规则、Provider 映射或 Guard 结论。

**站内通知（In-app Notification）**
持久、可读状态、可跳回原任务的主通知渠道。邮件默认承载关键状态，短信主要用于 OTP 与安全，其他推送只在适配器完成后开放。

**证据产物（Evidence Artifact）**
真实浏览器截图、轨迹、测试报告或发布报告。它证明某次验收发生过，但不能单独替代用户批准或产品完成定义。

**逐字核验引文（Verified Exact Citation）**
Runtime 从已核验古籍来源原样投影的引文。只有 evidence 节点及其每条 citation 都标记 `verified_exact`，并同时携带来源、定位锚点和非空逐字正文（核心来源记录为 `verbatim_quote`，公共合同为 `verbatim_excerpt`）时，Web 才能称为“原文”或“可核验”；rule assertion、摘要、改写、单独的 legacy `excerpt` 和只有来源名的记录都不属于逐字核验引文。多条引文必须全部保留，任一条不完整则该 evidence 对外 fail closed。

**有效排盘时刻（Effective Chart Datetime）**
Runtime 按已声明的时间策略、经度修正、均时差、历法边界和子时策略算出的排盘时刻，不是浏览器从出生输入自行换算的显示值。`changed_pillars=[]` 表示 Runtime 已比较且四柱未变；字段缺失表示该 Runtime 没提供比较结果，二者不能混用。完整有效时刻只属于本人 owner 范围的结果，不自动获得分享授权。

**分享隐私投影（Share-safe Projection）**
从本人完整 `ReadingDocumentV1` 生成的最小邀请快照，只保留分享页实际消费的摘要、判断、依据、边界和版本信息，不携带原始资料、完整 ViewModel 或精确有效排盘时刻。Bearer 分享令牌授予的是这份投影的读取权，不是本人结果文档的读取权。

## 禁止混用

- 不说“13 个术数页面”；说“7 个基础术数产品、固定跨术产品和 13 个内部 Provider”。
- 不说“AI 算命结果”；区分确定性盘面、Claim Candidate、Accepted Copy 和 ReadingDocumentV1。
- 不说“改报告”；区分 Verification、Input Correction、Follow-up 和 Recast。
- 不说“支付成功就扣次数”；区分 Payment、GRANT、RESERVE、CONSUME 与 Fulfillment。
- 不说“会员余额”或“积分”；第一版没有钱包、积分中心、会员等级或自动续费。
- 不说“后台看明文密码”；完整业务信息可显示，系统秘密永远不显示。
- 不用 `branch relations`、`luck cycles`、Provider payload 或任何 raw JSON 充当用户界面。
