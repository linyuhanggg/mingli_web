# mingli_web — 唯一权威开发总纲与进度账本

> 冻结日期：2026-08-13
>
> 当前基线：`main`，权威重建起点 `f488fa4`
>
> 当前阶段：P0 已验证；P1–P5 的本地代码、合同、测试与构建已推进；P2–P4 仍未完成用户逐页验收；P6–P9 仅完成可在本地闭环的基础能力；P10–P12 仍有真实 Runtime、支付、凭据、合规和用户批准门禁。
>
> 当前总判：核心后端可保留；旧产品表现层与旧品牌合同废弃；新 UI 已进入预制与合同整改，但 P2/P3/P4 尚未完成，禁止宣称 UI 已完成
>
> 本文职责：范围、依赖、顺序、进度、门禁、证据、当前断点和下一步

## 0. 权威文件与变更纪律

| 职责 | 唯一文件或目录 | 是否记录进度 |
|---|---|---:|
| 范围、路由、状态、依赖、进度、门禁、证据、下一步 | `docs/CHECKLIST.md` | 是 |
| 视觉、组件、交互、响应式、可访问性 | `DESIGN.md` | 否 |
| 统一领域名词 | `CONTEXT.md` | 否 |
| Runtime、Provider、Orchestrator、Guard、ReadingDocument | `docs/MINGLI_V51_WEB_INTEGRATION.md` | 否 |
| 不可逆架构决定 | `docs/adr/**` | 否 |
| Agent 团队岗位边界、消息协议与安全规则 | `AGENTS.md` | 否 |
| 真实浏览器、机器、测试和发布证据 | `docs/releases/evidence/**` | 只存产物 |

`web/AGENTS.md` 与 `admin/AGENTS.md` 是命中对应目录时的更具体工作规则，不覆盖上表。`docs/CODEX_AGENT_TEAM.md` 只是根 `AGENTS.md` 的使用说明，不是第二份权威；两者冲突时以 `AGENTS.md` 为准。

规则：

1. 不得新增 `HANDOFF*`、`docs/plans/*`、平行 blueprint、第二份 checklist 或施工叙事日志。
2. 新想法进入本文对应 Backlog，不得偷偷改写活跃阶段。
3. 改变已经批准的产品地图、页面层级、固定术数组合或视觉合同，必须先写影响范围、迁移与重新验收项，并由用户明确批准。
4. ADR 保留历史原文；旧决定失效时新增修订 ADR，不伪造历史。
5. 证据目录只存可复验产物。截图、测试和 Git SHA 是证据，不会自动把任务变成完成。
6. 两份参考站实审计永久保留；未来纠错用新的 dated addendum，不覆盖旧证据。
7. §14 只写当前断点与下一步，§15 只写用户明确确认、授权或裁决的冻结决定。施工过程、测试数字和发布记录写进 `docs/releases/evidence/**`，不回填这两节；本文因此不得再退化成只追加的流水账。

## 1. 进度状态与完成定义

### 1.1 状态枚举

| 状态 | 含义 |
|---|---|
| `NOT_STARTED` | 尚未施工 |
| `IN_PROGRESS` | 正在施工，不能对外称完成 |
| `VERIFIED` | 非 UI 治理、文档或取证任务已经完成并通过对应证据检查 |
| `UI_READY` | 路由和全部规定状态可点击，尚未完成真实浏览器门禁 |
| `BROWSER_VERIFIED` | 四档浏览器、键盘、响应式与负向检查有证据 |
| `USER_ACCEPTED` | 用户亲自浏览并明确批准 UI |
| `INTEGRATED` | 已接真实 API/数据/Runtime，合同与自动化通过 |
| `PRODUCTION_VERIFIED` | 真实渠道、恢复、告警、安全和发布演练通过 |
| `BLOCKED` | 有明确外部阻塞，并记录解除条件 |

不得把 `UI_READY`、`BROWSER_VERIFIED`、`INTEGRATED` 混为一谈。算法没接不妨碍 UI 使用明确 Fixture 验收；UI 漂亮也不代表算法、支付或权限接通。

### 1.2 每项证据必须记录

```text
work_item_id
dependency_ids
route_or_surface
required_states
view_model_or_contract_version
fixture_or_real_data_boundary
viewport: 360 / 768 / 1024 / 1440
keyboard_focus_screen_reader_reduced_motion
automated_test_command_and_result
negative_assertions
evidence_path
git_sha
reviewed_at
user_accepted_at
current_status
```

### 1.3 UI 完成硬门槛

一个页面或流程只有同时满足以下条件才能进入 `USER_ACCEPTED`：

- 所有规定路由和状态可从 `/_ui-lab` 发现并点击；
- 360、768、1024、1440 真实浏览器逐路运行并留截图/轨迹；
- 无页面级横向溢出；表单、盘面、菜单、抽屉、弹层、返回和恢复真实可操作；
- 键盘顺序、焦点、Skip Link、错误摘要和 `prefers-reduced-motion` 通过；
- 正常产品路由没有 Fixture、假盘、假支付、假权益或假“成功”；
- 不出现 raw JSON、snake_case、Provider payload、内部 ref、Prompt、`state_token` 或调试文本；
- 不出现旧 FateRadar 名称、墨绿金皮肤或废弃页面层级；
- 用户亲自浏览并明确确认。

DOM 存在、CSS 正则、组件单测、接口绿灯、清单勾选或开发者自评都不能代替上述门槛。

## 2. 当前 main 的保留、重写与取证边界

### 2.1 必须保留

- `backend/app/identity/**`、`profiles/**`、`readings/{models,repository,orchestrator,status,runtime_contracts,model_contracts,narrative_guard,public_copy,candidate_reference_closer,alerts,errors}.py`；
- `backend/worker/**`、真实 Runtime/Model/OTP/Payment Adapter 接口；
- PostgreSQL、网络、安全、观测、持久化、API 错误/依赖/限流/健康基础；
- `backend/alembic/versions/0001` 至当前全部迁移，历史永不重写；
- `contracts/schemas/mingli-command-v2.schema.json`、`mingli-result-v2.schema.json` 与现有协议演进基础；
- `infra/mingli-runtime/**`、Compose、Docker、Nginx、测试服务器与恢复基础；
- Web 的 Cookie/CSRF/401 会话失效、API single-flight、幂等、日期时间、IANA 时区、滚动恢复、reduced-motion 工程原语；
- Admin 独立应用、Staff Session、密码哈希、审计与 API 基础；
- `docs/adr/**` 与 `docs/releases/evidence/**`。

### 2.2 整体重写

- `web/src/app/**`、大部分 `web/src/components/**`、品牌 CSS、旧 metadata/manifest/robots 与旧产品 UI 测试；
- `admin/src/app/**`、`admin/src/components/**` 与后台 CSS；
- `web/src/lib/product-capabilities.ts`、`chart-workspace.ts`、`reading-display.ts`、`fortune-period-markers.ts` 与业务 DTO；
- 后端旧三能力产品策略、旧 preview/today/week/liuyao 请求编译器与产品 API；已有真实 fixture、黄金输入输出和算法映射只作 characterization 保留，旧产品编译器与 endpoint 实现仍重写；
- 正式 Catalog、Billing、Entitlement Ledger、Referral、CMS、Notification、Consent、Data Rights、Export/Share 模块；
- `web/next.config.ts` 的全局 `camera=()`，按见相真实采集需要重做权限策略；
- 用户可见和新部署中的旧品牌名称；机器合同/既有运维标识必须版本化迁移，不能盲改。

### 2.3 旧分支只取证，不整体合并

| 来源 | 可参考内容 | 处理方式 |
|---|---|---|
| `worktree-production-ha-task0` | PostgreSQL NULL owner 幂等唯一约束 | 以新的 Alembic 迁移重新实现，不 cherry-pick 冲突迁移号 |
| 同上 | 同一 SubjectProfile 追加不可变版本 | 按当前 User/ProfileVersion 合同重写 |
| 同上 | 多条核对记录 | 升级为 claim-level VerificationEvent |
| `codex/chart-first-qingnang` | 同步盘面后端与合同 | UI 合同 `USER_ACCEPTED` 后选择性移植 |
| `codex/ui-redesign-test-deploy` | 历史实现差距 | 只查证，不合并 UI |

`.qoder/worktrees/production-ha-task0` 是注册 Git worktree，不属于可删除生成文档。

## 3. 冻结产品地图

### 3.1 产品层

| 组 | 工作名称 | 固定范围 | 免费层 | 深读层 |
|---|---|---|---|---|
| 命盘 | 八字 | 单人本命与时间层 | 完整确定性盘面 + 基础摘要 | 版本化主题深读与追问 |
| 命盘 | 紫微 | 单人十二宫与时间层 | 完整确定性盘面 + 基础摘要 | 版本化主题深读与追问 |
| 命盘 | 七政 | 单人星盘与时间层 | 完整确定性盘面 + 基础摘要 | 版本化主题深读与追问 |
| 事件 | 六爻 | 明确问题与明确起卦 | 完整确定性卦盘 + 基础摘要 | 事件深读与追问 |
| 事件 | 奇门 | 场景、问题、时空 | 完整确定性九宫 + 基础摘要 | 事件深读与追问 |
| 事件 | 大六壬 | 问题、侧重、时空 | 完整确定性课盘 + 基础摘要 | 事件深读与追问 |
| 观照 | 见相 | 面相、手相、体态、综合观照 | 结构化观察与基础摘要 | 见相深读与追问 |
| 单人跨术 | 命盘合参（原三术合参，2026-08-14 起吸收多盘问答 `canwen`） | 八字/紫微/七政，至少选两术，可带具体问题 | 专术精简盘 + 互证/分歧 | 整合深读与同根追问 |
| 事件跨术 | 问事合参 | 六爻/大六壬/奇门固定三术 | 三盘概览与互证 | 整合深读 |
| 双人关系 | 八字/紫微/七政合盘 | 甲乙两个 ProfileVersion + 关系类型 | 双方盘面 + 基础关系结构 | 各术独立关系深读 |
| 留存 | 每日 | 确定性日期事实 + 运营内容 | 免费 | 将来可绑定档案个性化 |
| 工具 | 工具箱六项 | 寻时、同盘、音律、五行、解梦、姓名 | 按能力逐项开放 | 按 ProductVersion 配置 |
| 内容 | 知识库与主创内容 | CMS 内容，算法证据只读 | 免费 | 无假付费门 |

约束：

- 13 个 Runtime Provider 永远是内部模块，不映射成 13 个产品页或合参选项；
- 三术合参不是双人合盘；复杂“双人多术合参”属于未来独立产品；
- 正式业务第一条完整上线主线是八字，但 P1–P4 必须先把全部 UI 预制并由用户验收；
- 参考站的“术数推演、百宝袋、藏经阁”等品牌词不直接作为显示名；测试版使用“术数、工具、每日、知识库”等中性名称；
- 最终品牌名未冻结，不得擅自命名。

### 3.2 Runtime Provider 到产品的边界

```text
bazi          → 八字、八字合盘、命盘合参中的八字部分
ziwei         → 紫微、紫微合盘、命盘合参中的紫微部分
xingming      → 七政、七政合盘、命盘合参中的七政部分
liuyao        → 六爻、问事合参中的六爻部分
qimen         → 奇门、问事合参中的奇门部分
liuren        → 大六壬、问事合参中的六壬部分
physiognomy   → 见相结构化观察之后的命理事实
fortune 等其余 Provider → 每日、工具或未来产品；必须另有明确产品合同后才开放
```

这是产品映射，不授权浏览器算法，也不表示当前 Provider 已达到所有产品的生产就绪。

## 4. 路由与页面库存

### 4.1 公共与内容路由

| Route | 页面任务 | 索引策略 |
|---|---|---|
| `/` | 任务型首页、七术、跨术、每日、工具和内容入口 | index |
| `/arts` | 完整术数总览与适用边界 | index |
| `/daily` | 每日确定性信息与运营内容 | index |
| `/tools` | 六项工具总览 | index |
| `/tools/time-check` | 寻时定盘流程 | 十二时辰事实与结构化事件证据排序已接；完整古法校时、候选淘汰和结论仍未接 |
| `/tools/chart-similarity` | 八字四柱同盘事实比较 | 两份确认档案 + Runtime 四柱比较 |
| `/tools/rhythm` | 本命音律流程 | index，未接能力诚实标记 |
| `/tools/five-elements` | 五行事实与调候流程（不含旺衰/喜忌/用神结论） | index，已接有界事实切片 |
| `/tools/dream` | 解梦流程 | index，未接能力诚实标记 |
| `/tools/name` | 姓名分析流程 | index，未接能力诚实标记 |
| `/library` | 知识内容索引 | index |
| `/library/[slug]` | 文章/古籍公开内容 | index |
| `/about` | 产品方法与团队边界 | index |
| `/pricing` | 免费范围、真实 Offer 与交付说明 | index |
| `/methodology` | 先算后讲、证据、AI 与边界 | index |
| `/support` | 账号、任务、订单、退款和数据帮助 | index |
| `/privacy` | 版本化隐私政策 | index |
| `/terms` | 版本化服务与付费条款 | index |

### 4.2 产品路由

| Route | 产品 | 必须预制的主要旅程 |
|---|---|---|
| `/bazi` | 八字 | 输入 → 确认 → 免费盘面 → 深读 → 报告 |
| `/bazi/hepan` | 八字合盘 | 甲乙资料 → 关系 → 双盘/关系 → 深读 |
| `/ziwei` | 紫微 | 输入 → 十二宫盘 → 时间层 → 深读 |
| `/ziwei/hepan` | 紫微合盘 | 甲乙资料 → 关系 → 双盘/关系 → 深读 |
| `/qizheng` | 七政 | 输入 → 星盘 → 时间层 → 深读 |
| `/qizheng/hepan` | 七政合盘 | 甲乙资料 → 关系 → 双盘/关系 → 深读 |
| `/liuyao` | 六爻 | 问题 → 起卦方式 → 六次起卦 → 卦盘 → 深读 |
| `/qimen` | 奇门 | 场景 → 问题时空 → 九宫 → 深读 |
| `/daliuren` | 大六壬 | 问题/侧重/时空 → 课盘 → 深读 |
| `/jianxiang` | 见相 | 模式 → 同意 → 拍摄/上传/问卷 → 观察 → 结果 |
| `/hecan` | 命盘合参（原三术合参，吸收多盘问答流程） | 立命 → 至少两术 → 免费互证 → 整合深读；可带具体问题 |
| `/wenshi` | 问事合参 | 同问同刻 → 六爻起卦 → 三盘 → 整合深读 |
| `/canwen` | 历史多盘问答兼容入口 | 永久重定向到 `/hecan`；历史任务、报告和深链继续有效 |
| `/workbench/[handle]` | 不透明任务恢复入口 | 解析 handle 并恢复或重定向到所属产品路由；提交后不统一跳离产品页 |
| `/checkout/[orderId]` | 结账 | 订单快照、活动/退款确认、支付状态 |
| `/share/[shareId]` | 限时分享快照 | 有效、过期、撤销、不存在；noindex |
| `/invite/[code]` | 邀请活动落地页 | 全活动状态与临时归因；noindex |

产品输入不再强迫用户先走“建档 → 档案列表 → 起盘”。档案是复用能力，不是免费起盘前置条件。任务 URL 只带不透明 handle，不带出生资料、问题正文、照片或内部 token。

公共营销、方法与知识内容按路由表允许索引。`/workbench/**`、`/checkout/**`、`/account/**`、`/auth/**` 和所有带个人任务/订单/报告的产品状态必须 `noindex`、`no-store`；Service Worker 不得缓存个人资料、盘面、报告、订单、权益、邀请归因或照片。`/share/**` 仅渲染服务端隐私投影并保持 `noindex`。

### 4.3 Auth 与账户路由

全局登录弹层是主要入口，同时保留以下可深链页面：

```text
/auth/login
/auth/register
/auth/verify
/auth/set-password
/auth/recover
/auth/consent
```

账户区固定为：

```text
/account
/account/profiles
/account/profiles/[profileId]
/account/history
/account/history/[rootId]
/account/orders
/account/entitlements
/account/invitations
/account/notifications
/account/settings
/account/settings/security
/account/settings/preferences
/account/settings/privacy-data
```

报告归属于按 ReadingRoot/Version 组织的历史，不另建报告库。第一版没有积分中心、余额钱包、会员等级或自动续费页。

### 4.4 通用页面状态

每个适用路由必须预制：

```text
initial / input / dirty / validating / submitting / loading / empty / ready
need-input / login-required / locked / unavailable / adapting / maintenance
offline / reconnecting / unauthorized / forbidden
recoverable-error / terminal-error / deleted / expired
```

工作台另外覆盖：

```text
free-chart-ready / unsaved / saved / login-takeover
no-offer / purchase-confirm / payment-pending / payment-success
payment-failed / payment-expired
waiting-input / queued / preparing-facts / generating / validating-copy
delivered / delayed / failed / canceled
followup-available / followup-expired / recast-required
export-queued / export-ready / export-expired / export-failed
share-created / share-expired / share-revoked / share-not-found
```

见相另外覆盖：相机权限未询问/允许/拒绝、上传、裁切、旋转、质量不合格、重拍、观察失败、推演中、原图即将过期、主动入档、删除中、已删除、原图过期但结果可看。

邀请另外覆盖：计划中、进行中、暂停、满额、结束、无效、自邀、临时归因、清除归因、注册锁定、待支付、名额占用、到账、发放、使用、过期、冲正、申诉。

档案与任务版本另外覆盖：他人授权、他人照片授权、未成年人监护确认、资料差异确认、待手动重排、新旧盘并存、合参/合盘版本选择、生成前取消并换版、生成后版本锁定。

## 5. 响应式、工作台与 UI Lab

### 5.1 导航

- 767px 及以下：56px 顶栏 + 固定五项底栏（主页、术数、工具、每日、我的）+ 全屏术数抽屉；
- 768px 及以上：64px 完整顶栏 + 分组 Mega Menu；
- 桌面入口：术数、合参、工具、每日、知识内容、账户；合参下只有命盘合参与问事合参；
- Mega Menu 分命（八字/紫微/七政）、卦（六爻/奇门/大六壬）、相（见相）；跨术产品在独立的合参入口中呈现；
- 导航不能出现 13 Provider。

### 5.2 工作台

- 低于 1024px：盘面在前、阅读在后；
- 1024px 起：盘面约 480–520px，阅读区至少 360px；
- 1280px 起：复杂合参可拆主区/侧区；
- 时间层由每术 ViewModel 声明；不可用层 disabled 并显示原因；
- 移动端必须有粘性章节导航、页签或折叠；
- 盘面提供语义列表/表格替代；
- 免费盘面、深读、支付、任务、报告、追问、导出和分享状态互不冒充。

### 5.3 `/_ui-lab`

- Web 与 Admin 各有验收中心；只在开发/测试环境开放，生产 404；
- 顶部永久标记“UI 演示数据”；
- 所有 Fixture 使用与正式路由相同的版本化 ViewModel 和组件；
- 可按 route、state、viewport、role、capability state 筛选；
- 一键打开 360/768/1024/1440 预览与截图任务；
- UI 完成度与算法接入度分栏，不允许同一勾选覆盖二者。

## 6. 完整 Admin 信息架构

Admin 是独立应用、独立 Staff Session 和服务端 RBAC。固定角色：

| 角色 | 权限边界 |
|---|---|
| `support` | 查完整业务资料、档案、盘面、报告和售后；提交补偿申请，不能直接改账 |
| `finance` | 订单、支付、退款、对账与退款相关补偿 |
| `ops` | CMS、`UI_PREBUILT`/`ADAPTING`/`INTERNAL_TEST` 能力状态、测试权益、允许的任务重试和运营配置 |
| `superadmin` | 员工、角色、系统配置与全部业务；生产不允许 bootstrap 管理员 |

有权限页面完整显示姓名、邮箱、手机号、生辰地点、档案、盘面、订单、支付和权益，不使用星号或二次点击；数据库静态存储继续加密。密码哈希、验证码、Cookie、`state_token`、API Key、数据库口令、Prompt 和系统秘密永不展示。

`PUBLIC` 与 `PAUSED` 会改变真实用户可用性，只能由 `superadmin` 明确确认；`ops` 不能把能力发布给普通用户，也不能暂停公开能力。

| 一级组 | Route | 页面 |
|---|---|---|
| 总览 | `/dashboard` | 任务、订单、告警、活动与系统摘要 |
| 用户与数据 | `/users`、`/users/[id]` | User、LoginIdentity、DeviceSession、Consent、完整业务资料 |
|  | `/subjects`、`/subjects/[id]` | SubjectProfile、ProfileVersion、盘面与关系 |
|  | `/data-rights` | 导出、删除、注销、撤销请求队列 |
|  | `/support-cases` | 资料纠正、算法复核、售后与补偿申请 |
| 产品与内容 | `/products`、`/products/[id]/versions` | ProductFamily、ProductVersion、Offer |
|  | `/capabilities` | 固定产品能力状态机、ViewModel/Runtime 版本和验证 |
|  | `/cms/pages`、`/cms/daily`、`/cms/tools` | 页面、每日和工具运营内容 |
|  | `/cms/library`、`/cms/help`、`/cms/policies` | 知识、帮助、隐私与条款版本 |
| 排盘与解读 | `/charts` | 免费盘面任务、版本与失败 |
|  | `/readings`、`/readings/[id]` | ReadingRoot/Version、ReadingDocument、依据与版本 |
|  | `/reading-jobs` | 队列、检查点、延迟、失败与允许重试 |
|  | `/verifications` | claim-level 核对、争议与复核 |
|  | `/runtime`、`/model-profiles` | Runtime Release、Provider、模型与 Guard 状态 |
|  | `/observations` | 见相媒体与结构化观察审计 |
| 商业运营 | `/orders`、`/payments`、`/refunds` | 订单、支付尝试、支付、退款 |
|  | `/entitlements` | 追加式账本和 GRANT/RESERVE/CONSUME/RELEASE/REVERSE/EXPIRE |
|  | `/reconciliation` | 渠道对账、差异与补单 |
|  | `/referrals`、`/referrals/[id]` | 活动版本、白名单、名额、归因、奖励和漏斗 |
|  | `/appeals` | 邀请申诉与双审批纠错 |
| 系统与审计 | `/staff`、`/sessions` | 员工、角色、登录、强退、重置密码 |
|  | `/notifications` | Outbox、投递、退信、重试和偏好 |
|  | `/audit` | 读写审计、对象和原因，不复制秘密 |
|  | `/settings`、`/health` | 环境、集成、发布和健康状态 |

每个 Admin 写操作预制：无权限、只读、确认、原因、保存中、成功、验证失败、版本冲突、对象已变化和审计完成。

CMS 可编辑运营文案、每日、工具说明、知识内容、帮助、公告、FAQ、SEO、发布时间和政策版本；不可编辑确定性盘面、固定合参组合、算法规则、Runtime/Guard 结论、证据包版本和内部 Provider 映射。

## 7. 核心领域与合同

### 7.1 身份与资料

- User 是账号根；LoginIdentity 与 DeviceSession 分离；
- 第一版密码主登录，OTP 用于注册验证、快捷登录和找回密码；
- 注册：手机/邮箱 OTP → 设置密码 → 主动同意当前隐私/条款版本；
- 既有 OTP User 先验证后补密码，不建重复 User；
- 登录成功原地接管游客盘面和 prepared task；身份冲突不自动合并；
- User 与 SubjectProfile 分离；每个 User 最多一个默认本人档案，可保存多个他人档案；
- 保存或使用他人资料前必须由当前用户确认已获授权；他人照片另行确认，未成年人资料/照片需要监护人确认；第一版不要求对方注册，也不主动向对方发送邀请或通知；
- SubjectProfile 不按姓名、生日、手机号或照片自动合并；只有用户在可见差异确认后手动合并；
- 双人合盘关系类型固定为情侣、夫妻、亲子、合伙、职场、朋友，任一资料版本或关系类型变化都创建新任务；
- 成功起盘自动进入历史，但只有主动保存才进入可复用档案库；
- ProfileVersion 不可变，修改先展示差异并新建版本；旧盘、旧订单和旧报告继续引用旧版。
- 新 ProfileVersion 不触发后台批量重算；进入具体术数时提示用户手动免费重排，新旧盘并存；合参和合盘必须明确选择最新版本或保留旧版，不能静默替换；

### 7.2 每术 ViewModel

必须建立独立版本化合同，至少包括：

```text
bazi-chart/v1
ziwei-chart/v1
qizheng-chart/v1
liuyao-chart/v1
qimen-chart/v1
daliuren-chart/v1
physiognomy-view/v1
bazi-relationship/v1
ziwei-relationship/v1
qizheng-relationship/v1
hecan-view/v1
wenshi-view/v1
canwen-view/v1
reading-document/v1
```

Fixture、后端、Web、PDF、分享与 Admin 使用同一合同。禁止 `Record<string, unknown>`、字符串猜测或未知 JSON 回退展示；未知字段只能进入开发诊断。

### 7.3 ReadingDocumentV1

模型不直接生成整篇报告，只产出原子短判断，每条绑定 subject、dimension、certainty 和 fact/finding/evidence/limit refs。服务端 PresentationContract 决定章节、顺序、槽位、数量、字数、固定声明和 renderer。

通用报告壳：盘面主区、一句话回答、主题导航、判断卡、依据抽屉、边界、现实核对、资料纠正、追问、导出、分享和版本信息。各术与合参有专属章节，合参明确展示互证、分歧与缺失，不平均成文章。

AcceptedCopy 继续作为不可变文字凭证；同一次通过 Guard 的 `ReadingDocumentV1` 同步固化。旧报告原样只读，新报告使用新合同。

### 7.4 核对、纠正与追问

- 每条判断追加 VerificationEvent：符合、部分符合、不符合、暂时无法验证，可写现实说明与发生时间；
- 报告末尾独立追加 ReportFeedback：清晰度、帮助程度、是否解决问题；它可用于质量统计，但不替代 VerificationEvent；正文、照片和身份资料未经另行授权不得用于训练；
- 现实核对不自动进入模型、Runtime、后续追问或旧报告；
- 输入错误走 InputCorrection，产生新 ProfileVersion、盘面或事件任务；
- 判断争议可申请复核；员工只能分类、安排新运行或追加补偿，不能改旧报告；
- 追问绑定已交付报告/判断卡，同一 ReadingRoot 严格线性，一次只允许一个活动追问；
- 换人、资料、卦、事件、照片、术数或扩大范围必须 Recast；
- 只有追问 Accepted 才 CONSUME；失败、延迟和补资料不消耗。

### 7.5 深读任务

深读是可离开页面的服务端持久任务：

```text
waiting-input → queued → preparing-facts → generating
→ validating-copy → delivered
                 ↘ delayed / failed / canceled
```

- 幂等创建唯一 ReadingVersion/Job 并 RESERVE；刷新、回跳和连续点击不能重复任务或扣权；
- Worker 在关页、断网、换设备和退出后继续；历史与原 URL 恢复同一工作台；
- 等待补资料最长 7 天，超时取消并 RELEASE；
- 进入生成后不能换资料或前台强停；系统故障可从持久检查点有限重试；
- 进入生成前允许取消：RELEASE 已占权益，并可切换到新 ProfileVersion 重开；进入生成后资料版本锁定，不能静默替换；
- 只有 Accepted 落库才 CONSUME；最终失败 RELEASE；
- 用户界面不暴露 `runtime_unknown` 等内部术语，不伪造百分比。

## 8. 隐私、数据权利、媒体、导出与通知

### 8.1 隐私与条款

- 第一版必须有真实 `/privacy` 与 `/terms`，内容以项目真实数据流、能力、运营主体和渠道为准，不复制参考站具体事实；
- 登录、注册、购买、页脚与政策变更均可到达政策；
- 服务端保存同意版本和时间；重大变更可要求重新确认；
- 条款覆盖七术、合参、见相照片、密码/OTP、档案与历史、AI 深读、后台、单次商品、权益、退款、CMS、数据权利与 AI 标识；
- 生产开放前需要法律复核，测试版也不能使用虚构运营主体或保存期限。

### 8.2 数据权利

- 用户可查看已同意政策版本与时间；
- 导出身份、设备、档案、盘面、报告、追问、核对、订单、支付和权益；
- 可单项删除档案、解读、追问和见相原图；
- 可撤销设备会话；
- 注销需密码 + 绑定手机/邮箱 OTP 双重确认，进入 7 天可撤销冻结期；
- 期满删除/匿名化可删除数据；法定财务与审计最小记录按政策列明期限保留且停止个性化使用；
- Admin 有数据权利队列和执行状态。

### 8.3 见相媒体生命周期

- 游客原图、裁切、缩略和标注最长 24 小时；
- 登录用户默认 7 天；
- 只有再次主动勾选“保存到见相档案”并单独同意才长期保存；
- 长期默认保留结构化观察、结果和处理日志，不建立人脸身份模板、不用于训练；
- 主动删除后在线对象及衍生图 24 小时内清除，备份自然轮转最长 30 天且不可恢复到正常产品；
- 后台只在有效期内按 RBAC 查看完整原图并记录访问审计；
- 视觉观察适配器只产结构化观察，不下命理结论、不做人脸身份识别；physiognomy Provider 才产确定性命理事实。

### 8.4 导出与分享

- 私密导出：单术盘面高清 PNG；盘面 + 解读 PDF；合参、合盘、综合观照用专属模板；
- 导出由服务端绑定不可变版本生成，私有存储，短时授权下载，24 小时删除，可重建；
- 数据权利 ZIP/JSON/CSV 与产品报告导出分开；
- 分享默认关闭；用户创建不可变快照，可选仅盘面、盘面+免费摘要、完整报告；
- 分享默认 7 天，可选 1/7/30 天并随时撤销；
- 分享只显示档案称呼，排除手机号、邮箱、精确地点、订单和账号；创建前列明必要出生信息；
- 见相分享永不包含原图或标注图；追问默认不分享。

### 8.5 通知

- 站内通知持久必达：未读数、筛选、全部已读、删除和原任务跳转；
- 解读完成、需补资料、延迟、最终失败、退款、数据导出和账号安全必须进站内；
- 已验证邮箱默认接收关键业务邮件，普通邮件可关，安全/重置/重大政策保留必要发送；
- 短信主要用于 OTP 与安全；解读短信默认关闭，用户主动开启；
- 邮件/短信只含任务标识和状态，不含生辰、照片、盘面或正文；
- Web Push、微信通知、未来 iOS Push 只预制，适配器完成前不展示启用按钮；
- Outbox 幂等，记录待发、成功、退信、失败、重试和关闭原因。

## 9. 商业、权益与邀请活动

### 9.1 商品与账务

- 所有开放术数的确定性盘面和基础摘要免费且不故意残缺；
- 付费对象是绑定具体盘面的单次深读与规定次数/期限的同盘追问；
- 七个基础术数、三术合参、多盘问答、问事合参分别拥有 ProductFamily；双人合盘按术数独立；
- ProductVersion 冻结交付、币种、价格语义、追问次数/期限和算法/报告版本；价格变化新建版本；
- ProductOffer 是渠道映射；无真实 Offer 时前台显示测试期未开放；
- 第一阶段不做永久专业版、会员等级、金币点数、余额钱包或自动续费；
- 未来订阅合同、周期、商品与权益分离；模型厂商成本不影响用户订阅事实。

### 9.2 订单、支付、退款与权益

```text
Catalog → ProductVersion/Offer → Order → PaymentAttempt → Payment
→ GRANT → RESERVE → CONSUME / RELEASE → Fulfillment
Refund / exceptional correction → REVERSE
unused expiry → EXPIRE
```

- 客户端回跳不是到账；服务端验签通知或主动查单才产生 Payment；
- 写入必须幂等，重复通知、回跳和 Worker 恢复不能重复 GRANT/CONSUME；
- 账本只追加，禁止直接改余额或覆盖历史；
- Admin 发测试/补偿/撤回也只写有原因、有对象、有审计的事件；
- support 只读并提交申请；finance 处理退款相关补偿；ops 管测试权益；superadmin 全权；
- 当前 dogfood owner grants 不是正式账本，正式账本接管后以新迁移退出。

### 9.3 邀请活动模块

邀请是独立 `ReferralCampaign`，默认关闭，支持计划、开始、暂停、结束和不可变规则版本，不是永久分销规则。

冻结规则：

1. 每个 CampaignVersion 只包含发布时明确选择的已售 ProductVersion 白名单；未来版本不自动加入。
2. 引擎有 `inviter_reward` 和 `invitee_reward` 两个槽；首版活动只启用邀请人奖励。
3. 每个受邀新用户在同一活动仅首笔合格、服务端确认支付的购买触发一次；续购和续费不重复。
4. 邀请人获得与受邀人购买相同 ProductVersion 的权益，不获得命盘、报告、个人数据、现金或余额。
5. 赠送权益默认 90 天内开始使用；开始后可跨到期完成，Accepted 报告永久保留，追问期限从 Accepted 另算；未用则 EXPIRE，不转赠、不提现。
6. 未来订阅首个已付款周期可触发一次同内容/同周期赠送权益，但不为邀请人创建自动续费合同。
7. 未来充值只可作为资格事件，奖励映射到商品权益，不复制余额；第一版无充值钱包。
8. 每场活动必须有总奖励上限，可按 ProductVersion 分配；每位邀请人默认最多 10 个不同新用户触发，版本可调整。
9. 注册不占名额；合格订单进入真实支付时原子占用，成功变已承诺，失败/关闭/超时释放；满额必须在付款前说明本单不参加。
10. 邀请 URL `/invite/{code}` 与二维码包含非 PII 公共邀请码，服务端映射活动+邀请人。
11. 邀请链接仅在 ACTIVE 时建立临时归因；默认 30 天且不晚于活动结束。注册确认前最后一个有效邀请生效，用户可清除。
12. 注册事务再次校验后永久锁定；既有账号、重复归因和自邀无效。普通员工不能补绑/换绑；明确技术错误需要独立纠错事件、双审批和审计。
13. 注册绑定和首笔合格支付都必须在活动有效期内；暂停/结束阻止新绑定和新合格支付。
14. 活动订单是数字化、个性化服务；支付并开始履约后不支持七日无理由退款。受邀人须主动、非默认勾选；邀请人也须知情；服务端保存政策/活动/商品版本与确认时间。
15. 服务端确认支付后立即 GRANT，不等待普通退款观察期。重复扣款、未交付/严重不符、平台终止及法律/渠道强制例外仍可退款并 REVERSE。
16. 自邀、旧账号、重复归因、非白名单、达到上限、渠道撤销/虚假交易等确定事实自动拒绝。IP、设备、地址重合只作风险信号，不能单独吞奖励。
17. 确认违规后追加 REVERSE、限制未来参加并审计；不删除已交付报告、不造负余额；提供一次可解释申诉。
18. 前台只有私有进度，无公开排行榜、收益榜、虚假成交滚动或倒计时。邀请人只见公开昵称和阶段，不见金额、支付方式、账号或命理资料。
19. 站内通知必备，邮件默认，短信默认关闭，Push 只预制。后台漏斗必须以注册/订单/支付/权益服务端事实计算，前端埋点不代替财务事实。
20. 邀请不进入全局一级导航；首页邀请卡只在活动 ACTIVE 且当前用户符合资格时出现，暂停/结束后消失，账户中的本人归因、历史奖励、过期和冲正记录继续保留。
21. 每个新 User 全局最多一个 Locked Attribution；一旦在注册事务锁定，后续活动、链接或购买都不能产生第二个锁定归因。

## 10. 算法适配与算法缺口开发顺序

### 10.1 总原则

- 自有 Runtime 是唯一事实源；浏览器、CMS、模型与参考站算法都不能补盘面；
- 先按 UI 冻结每术 ViewModel、PresentationContract 和黄金交互，再适配 Runtime；
- Runtime 已有 Provider 但输出不满足 UI 时，先做事实缺口清单、古籍/规则证据和黄金样例，再在 `mingli-master` 中开发；
- 每个算法缺口开发任务使用 `$mingli-master` 的确定性事实、古籍证据与原子状态方法；
- 无法可靠开发的能力保持 `ADAPTING` 或 `UNAVAILABLE`，不伪造结论；
- 每术必须通过固定输入、边界、跨时区/历法、证据闭合、ViewModel 投影与真实浏览器黄金样例后才能 `PUBLIC`。

### 10.2 顺序与依赖

1. **八字完整闭环**：输入、真太阳时/时间口径、免费盘面、时间层、ReadingDocument、追问、导出、分享、账号、订单和权益；它是第一条生产主线。
2. **紫微与七政**：各自专用盘面和 ViewModel；随后开放各自双人合盘。
3. **三术合参**：至少两术真实就绪可内部测试；三术全就绪才可宣称完整三术结果。
4. **六爻**：明确手工六次值或核心数字投币；禁止偷偷用时间起卦替代。
5. **奇门与大六壬**：各自专用局/课盘与问题时空合同。
6. **问事合参**：六爻、奇门、六壬全部就绪后才可真实运行。
7. **多盘问答**：依赖八字/紫微/七政、ReadingDocument 与线性追问链。
8. **见相**：采集与媒体 → 结构化视觉观察 Adapter → physiognomy Provider → 专用 ViewModel；四模式分别发布。
9. **每日与六工具**：逐项确定真实 Provider/算法、免费边界、黄金样例与商品语义；不得把通用模型当算法。

## 11. 分阶段实施总账

P0–P9 是全局前置顺序：UI 用户验收 → ViewModel/API → 身份档案 → 商业/通知 → 邀请 → Admin/CMS 真数据。它们完成前不得进入术数算法施工。P10–P11 按术数组成垂直切片：先做八字 `P10-001`，随即完成八字所需的 P11 深读/任务/核对/追问/导出/分享，形成第一条完整生产主线；不得等待其余六术和全部工具都完成。随后其他术数按 10.2 顺序逐项复用已经完成的平台能力。每个任务完成时在本节更新状态、证据路径和 Git SHA；不得另建计划文件。

### P0 — 权威清理与唯一基线

| ID | 任务 | 主要文件 | 验证 | 状态 |
|---|---|---|---|---|
| P0-001 | 删除自动生成的旧 FateRadar wiki、旧 design-system 和 harness 产物，加入 tombstone ignore | `.qoder/repowiki/**`、`.qoder/better-harness/**`、`.impeccable/**`、`PRODUCT.md`、`design-system/mingli-web/**`、`.gitignore` | `git status` 精确范围；正式代码/证据未删 | `VERIFIED` |
| P0-002 | 重写唯一权威集合与 README | 本文、`DESIGN.md`、`CONTEXT.md`、`README.md` | 权威合同测试、死引用检查 | `VERIFIED` |
| P0-003 | 保留历史 ADR 原文并追加修订决定 | `docs/adr/0006`、`0008`、`0009`、`0010`、`0011` | ADR 元数据、原文与引用检查 | `VERIFIED` |
| P0-004 | 迁移算法合同的新产品范围与 ReadingDocument | `docs/MINGLI_V51_WEB_INTEGRATION.md` | native policy 合同与旧三能力冲突检查 | `VERIFIED` |
| P0-005 | 原样复制青囊/METIS 审计到证据目录并保留外部原件 | `docs/releases/evidence/2026-08-12-reference-site-audits/**` | 两端文件存在、内容一致 | `VERIFIED` |
| P0-006 | 更新所有旧权威引用并删除两份冲突蓝图 | `web/AGENTS.md`、`admin/AGENTS.md`、`tests/contract/**`、旧产品文档 | 权威合同与原生政策测试通过 | `VERIFIED` |
| P0-007 | 暂存单一“权威重建与旧文档清壳”变更集 | Git index | `git diff --cached --check`、状态摘要 | `VERIFIED` |

P0 出口：权威文件互不冲突、两份实站审计在仓库与原路径都存在、旧蓝图不再被引用、测试通过。P0 只完成治理，不代表任何新 UI 已完成。

### P1 — UI 基础、共享壳与验收中心

| ID | 任务 | 主要文件 | 先写的失败测试/检查 | 状态 |
|---|---|---|---|---|
| P1-001 | 建中性语义 Token、字体与全局基础 | `ui/tokens.css` 是共享源；两端 `globals.css` 只 import 并增加应用层规则 | 两 app build；无旧品牌 token；两端不复制 Token | `VERIFIED` |
| P1-002 | 建 Button/Field/Segmented/Tabs/Dialog/Drawer/Status/Table primitives | `web/src/components/ui/**`、`admin/src/components/ui/**` | 键盘、焦点、44px、reduced-motion 测试 | `VERIFIED` |
| P1-003 | 重建公共 Header、Mega Menu、手机底栏/抽屉、Footer 与私有路由缓存边界 | `web/src/components/shell/**`、metadata、Service Worker | 767/768 导航切换 E2E；私有路由 noindex/no-store 且不进 SW cache；Web `site-shell`/metadata/route-matrix/accessibility 合同 | `VERIFIED` |
| P1-004 | 建产品输入壳、工作台壳、报告壳、任务状态壳 | `web/src/components/task/**`、`workbench/**`、`reading/**` | Web 产品路由合同、P2 交互合同、UI Lab 26 tests、四视口 product-journeys/route-matrix | `VERIFIED` |
| P1-005 | 建 Admin 顶栏、侧栏/抽屉、列表/详情/写操作壳 | `admin/src/components/shell/**`、`admin/src/components/admin/**` | Admin route/catalog/RBAC/UI Lab contracts；四视口 route-matrix/accessibility/admin-contracts | `VERIFIED` |
| P1-006 | 建版本化 UI ViewModel 类型与 Fixture 注册表 | `web/src/view-models/**`、`web/src/fixtures/**` | 禁止未知 JSON/raw fallback 测试 | `VERIFIED` |
| P1-007 | 建 Web/Admin `/_ui-lab`，环境外 404 | `web/src/app/%5Fui-lab/**`、`admin/src/app/%5Fui-lab/**` | dev/test 可见、production 404 | `VERIFIED` |
| P1-008 | 引入真实浏览器工具与证据命名规范 | `web/e2e/**`、`admin/e2e/**`、package scripts | Playwright/Chrome smoke 与截图路径 | `VERIFIED` |

P1 出口：共享壳与所有通用状态可在 UI Lab 使用；不需要真实算法，但 Fixture 显著标记。

### P2 — 完整 C 端 UI 预制

| ID | 范围 | Route/文件族 | 必须覆盖 | 状态 |
|---|---|---|---|---|
| P2-001 | 首页与公共内容 | `/`、`/arts`、`/about`、`/pricing`、`/methodology`、`/support` | 导航、任务卡、免费/付费边界、空/错/维护 | `IN_PROGRESS` |
| P2-002 | 政策 | `/privacy`、`/terms` | 正式可用初版、版本/生效时间、登录/购买链接 | `IN_PROGRESS` |
| P2-003 | 八字与八字合盘 | `/bazi`、`/bazi/hepan` | 输入、盘面、时间层、合盘、深读到分享全态 | `IN_PROGRESS` |
| P2-004 | 紫微与紫微合盘 | `/ziwei`、`/ziwei/hepan` | 十二宫、时间层、双人页签、全态 | `IN_PROGRESS` |
| P2-005 | 七政与七政合盘 | `/qizheng`、`/qizheng/hepan` | 星盘、时间层、双人页签、全态 | `IN_PROGRESS` |
| P2-006 | 六爻 | `/liuyao` | 问题、起卦、六次过程、卦盘、深读全态 | `IN_PROGRESS` |
| P2-007 | 奇门 | `/qimen` | 场景、问题时空、九宫、深读全态 | `IN_PROGRESS` |
| P2-008 | 大六壬 | `/daliuren` | 问题/侧重/时空、四课三传、深读全态 | `IN_PROGRESS` |
| P2-009 | 见相四模式 | `/jianxiang` | 权限、上传、质量、观察、保存/删除、结果全态 | `IN_PROGRESS` |
| P2-010 | 命盘合参 | `/hecan` | 立命、至少两术、具体问题、互证/分歧、整合深读 | `IN_PROGRESS` |
| P2-011 | 问事合参 | `/wenshi` | 同问同刻、六爻起卦、三盘、整合深读 | `IN_PROGRESS` |
| P2-012 | 历史多盘问答兼容入口 | `/canwen` → `/hecan` | 重定向、历史任务/报告不失效、命盘合参带问题流程 | `IN_PROGRESS` |
| P2-013 | 每日与工具 | `/daily`、`/tools/**` | 六工具输入、适配中/免费/Offer/失败状态 | `IN_PROGRESS` |
| P2-014 | 知识内容 | `/library`、`/library/[slug]` | 索引、搜索/筛选、文章、来源、空/错 | `IN_PROGRESS` |
| P2-015 | Auth | 全局弹层、`/auth/**` | 密码/OTP/注册/恢复/同意/冲突/接管全态 | `IN_PROGRESS` |
| P2-016 | Account | `/account/**` | 档案、他人/照片/未成年人确认、手动合并、重排版本、历史、订单权益、邀请、通知、设置/数据权利 | `IN_PROGRESS` |
| P2-017 | 商业与分享 | `/checkout/**`、`/share/**` | 订单/支付/退款、导出/分享、跨设备恢复 | `IN_PROGRESS` |
| P2-018 | 邀请 | `/invite/[code]` | 全活动状态、归因、清除、注册、退款确认 | `IN_PROGRESS` |

P2 出口：所有 C 端路由和规定状态达到 `UI_READY`，正常路由未接能力显示适配中。

### P3 — 完整 Admin UI 预制

| ID | 范围 | Route | 状态 |
|---|---|---|---|
| P3-001 | Admin 登录、环境和总览 | `/login`、`/dashboard` | `IN_PROGRESS` |
| P3-002 | 用户、身份、设备、同意 | `/users/**` | `IN_PROGRESS` |
| P3-003 | Subject、ProfileVersion、数据权利、客服案件 | `/subjects/**`、`/data-rights`、`/support-cases` | `IN_PROGRESS` |
| P3-004 | 商品、报价、能力发布 | `/products/**`、`/capabilities` | `IN_PROGRESS` |
| P3-005 | CMS 与政策版本 | `/cms/**` | `IN_PROGRESS` |
| P3-006 | 盘面、报告、任务、核对、见相观察 | `/charts`、`/readings/**`、`/reading-jobs`、`/verifications`、`/observations` | `IN_PROGRESS` |
| P3-007 | Runtime、Provider、Model、Guard | `/runtime`、`/model-profiles` | `IN_PROGRESS` |
| P3-008 | 订单、支付、退款、对账、权益 | `/orders`、`/payments`、`/refunds`、`/reconciliation`、`/entitlements` | `IN_PROGRESS` |
| P3-009 | 邀请活动、漏斗、名额、申诉 | `/referrals/**`、`/appeals` | `IN_PROGRESS` |
| P3-010 | 员工、会话、通知、审计、系统 | `/staff`、`/sessions`、`/notifications`、`/audit`、`/settings`、`/health` | `IN_PROGRESS` |
| P3-011 | 四角色权限与写操作状态矩阵 | 全 Admin UI Lab | `IN_PROGRESS` |
| P3-012 | Admin lint/test/typecheck/build 纳入 `make check` 与部署 | `admin/package.json`、`Makefile`、`infra/**` | `IN_PROGRESS` |

P3 出口：六组全部页面、四角色、完整业务明文/系统秘密隐藏和写操作状态达到 `UI_READY`。

### P4 — 真实浏览器与用户 UI 验收

| ID | 任务 | 证据 | 状态 |
|---|---|---|---|
| P4-001 | 360 全路由旅程、截图、无横溢 | `docs/releases/evidence/2026-08-14-route-acceptance-working-tree/README.md`、当前 Web/Admin smoke | `BROWSER_VERIFIED` |
| P4-002 | 768 全路由旅程、导航切换、工作台单列 | `docs/releases/evidence/2026-08-14-route-acceptance-working-tree/README.md`、工作台断点合同 | `BROWSER_VERIFIED` |
| P4-003 | 1024 全路由旅程、工作台双栏与 Admin | `docs/releases/evidence/2026-08-14-route-acceptance-working-tree/README.md`、工作台断点合同 | `BROWSER_VERIFIED` |
| P4-004 | 1440 全路由旅程、最大宽和复杂合参 | `docs/releases/evidence/2026-08-14-route-acceptance-working-tree/README.md`、当前 Web/Admin smoke | `BROWSER_VERIFIED` |
| P4-005 | 键盘、焦点、读屏语义、200/400% zoom、reduced-motion | `docs/releases/evidence/2026-08-13-accessibility/**`、当前工作树 accessibility 合同 | `BROWSER_VERIFIED` |
| P4-006 | 通用视觉范围决定；不要求青囊/METIS 像素复刻 | `docs/releases/evidence/2026-08-14-p4-006-generic-visual-decision/README.md` | `VERIFIED` |
| P4-007 | 用户亲自浏览并批准公共/产品/账户/Admin | `docs/releases/evidence/2026-08-14-p4-007-test-server-upload/README.md` | `IN_PROGRESS` |

P4 是不可跳过门禁。P4-007 未完成前，不得进入“UI 已完成”的表述；只允许只读代码/数据调研，不得实施会约束或改写未批准页面合同的后端产品功能。

### P5 — ViewModel、API 与后端产品合同

| ID | 任务 | 主要文件 | 状态 |
|---|---|---|---|
| P5-001 | 为七术、合盘、三跨术发布 JSON Schema | `contracts/schemas/views/**` | `VERIFIED` |
| P5-002 | 发布 `reading-document-v1` 与 PresentationContract | `contracts/schemas/reading-document-v1.schema.json`、后端 contracts | `VERIFIED` |
| P5-003 | 重写 OpenAPI 路由、错误、幂等和任务恢复 | `contracts/openapi/v1.yaml`、`admin-v1.yaml` | `VERIFIED` |
| P5-004 | 拆分 Web API 基础与业务 DTO | `web/src/lib/api/**`、`web/src/test/api-module-boundaries.test.ts` | `VERIFIED` |
| P5-005 | 实现每术服务端 ViewModel projector | `backend/app/charts/**`、`backend/app/readings/presentation/**` | `VERIFIED` |
| P5-006 | 禁止 raw JSON/unknown fallback 的合同测试 | `web/src/**/*.test.*`、`tests/contract/**` | `VERIFIED` |
| P5-007 | 选择性重做同步盘面 API，不合并旧 UI 分支 | `backend/app/charts/**` | `NOT_STARTED` |

### P6 — 身份、档案、政策与数据权利真接线

| ID | 任务 | 核心验收 | 状态 |
|---|---|---|---|
| P6-001 | 密码哈希、密码登录、OTP 快捷、找回和会话撤销 | 密码永不明文；身份冲突不自动合并 | `IN_PROGRESS` |
| P6-002 | 政策版本、ConsentRecord 与重新同意 | 注册/购买/重大变更都有版本事实 | `IN_PROGRESS` |
| P6-003 | Guest → User 原地接管 | 不重填、不重复起盘、幂等认领 | `VERIFIED` |
| P6-004 | 同一 SubjectProfile 追加不可变 ProfileVersion 与他人资料授权 | 不自动合并；差异确认；他人/照片/未成年人确认；重做旧 worktree 成果 | `IN_PROGRESS` |
| P6-005 | 历史按 ChartTask/ReadingRoot/Version 投影 | 旧版与当前版均可查 | `IN_PROGRESS` |
| P6-006 | 导出、单项删除、设备撤销、注销 7 天撤销期 | 用户与 Admin 队列闭环 | `VERIFIED` |
| P6-007 | 修复 nullable owner 幂等唯一约束 | PostgreSQL 真实并发测试；新增迁移 | `VERIFIED` |

### P7 — Catalog、支付、正式权益、通知与平台交付

P7 依赖 P5 与 P6 全部 `INTEGRATED`，先建立不依赖某一术数的真实平台能力。

| ID | 任务 | 状态 |
|---|---|---|
| P7-001 | ProductFamily/ProductVersion/ProductOffer 管理 | `IN_PROGRESS` |
| P7-002 | Order/PaymentAttempt/Payment/Refund 与服务端到账 | `IN_PROGRESS` |
| P7-003 | GRANT/RESERVE/CONSUME/RELEASE/REVERSE/EXPIRE 正式账本 | `VERIFIED` |
| P7-004 | Payment、Job、Accepted 与 Fulfillment 幂等接口 | `IN_PROGRESS` |
| P7-005 | Admin 发放/补偿/撤回与完整轨迹 | `VERIFIED` |
| P7-006 | 渠道对账、差异、重复通知、退款例外 | `IN_PROGRESS` |
| P7-007 | 站内通知、邮件、短信偏好与 Outbox | `IN_PROGRESS` |
| P7-008 | 私有媒体、短时下载、导出与分享基础设施 | `NOT_STARTED` |
| P7-009 | 正式账本接管后退役 dogfood grant | `NOT_STARTED` |

### P8 — 邀请活动真接线

P8 依赖 P6 身份与 P7 Catalog/Payment/Ledger/Notification 全部 `INTEGRATED`。

| ID | 任务 | 状态 |
|---|---|---|
| P8-001 | CampaignVersion、奖励槽、白名单、日程与状态机 | `IN_PROGRESS` |
| P8-002 | 邀请码、临时归因、最后有效链接、清除与全局唯一注册锁定 | `IN_PROGRESS` |
| P8-003 | 总名额、ProductVersion 名额、个人 10 人默认上限和支付占用 | `IN_PROGRESS` |
| P8-004 | 首笔一次触发、即时 GRANT、90 天 EXPIRE 与例外 REVERSE | `IN_PROGRESS` |
| P8-005 | 活动订单主动退款确认、服务端证据与双方告知 | `IN_PROGRESS` |
| P8-006 | 确定拒绝、风险信号、申诉和双审批纠错 | `IN_PROGRESS` |
| P8-007 | 前台私有进度、关键通知和后台事实漏斗 | `IN_PROGRESS` |
| P8-008 | 订阅首期/充值资格的关闭态与未来合同测试 | `IN_PROGRESS` |

### P9 — CMS、Admin 真数据与运营闭环

| ID | 任务 | 状态 |
|---|---|---|
| P9-001 | CMS 草稿/预览/定时/发布/撤回/归档/历史恢复 | `VERIFIED` |
| P9-002 | 每日、工具、知识、帮助、公告、FAQ、SEO 真接线 | `IN_PROGRESS` |
| P9-003 | 算法事实只读区与运营文案编辑区分离 | `NOT_STARTED` |
| P9-004 | Staff 管理、四角色 RBAC、强退、重置与审计 | `IN_PROGRESS` |
| P9-005 | Admin 六组接真实平台聚合/写服务；算法相关页绑定 Capability/Runtime 状态而非 stub | `IN_PROGRESS` |

### P10 — 免费确定性盘面与算法适配

P10 依赖 P5–P9 全部 `INTEGRATED`。每术完成后直接进入该术的 P11 垂直闭环，不等待 P10 整阶段完成。

本轮新增的 Wenshi 合参证据桥把 Runtime 已有的六爻候选池、`useful_spirit_selection` 候选链/旺衰证据与奇门来源谓词接到三术信号层；`convergence`/`disagreements` 仍为空，不能记为选择用神、三术互证、分歧裁决或正式深读完成。证据：`docs/releases/evidence/2026-08-17-p10-core-algorithm-coverage/README.md`。

六爻求财现已完成一段受限正式裁决：`HJC-R009` 先定妻财角色，盘面仅有一个可见妻财候选时可定位具体爻位；多个可见候选、只有伏神/变爻时继续 fail-closed，不套固定排序。旺衰救应、成败应期和问事合参结论仍未完成，P10-006/P10-009 保持 `IN_PROGRESS`。证据：`docs/releases/evidence/2026-08-17-p10-core-algorithm-coverage/README.md`。

本轮继续补齐 Canwen/HeCan 证据桥：八字 `interpretive_candidates`、紫微/星命 `source_conditioned_patterns` 已进入三术信号层并保留 fact refs；仍不形成跨术结论、分歧裁决或正式深读。证据：`docs/releases/evidence/2026-08-17-p10-core-algorithm-coverage/README.md`。

| ID | 任务 | 发布依赖 | 状态 |
|---|---|---|---|
| P10-001 | 八字输入、时间口径、盘面 ViewModel 与免费摘要 | Runtime 黄金样例；`docs/releases/evidence/2026-08-14-p10-001-local-bazi-view-model/README.md` | `IN_PROGRESS` |
| P10-002 | 紫微盘面与时间层 | 专用 Provider/VM/黄金样例 | `IN_PROGRESS` |
| P10-003 | 七政盘面与时间层 | 专用 Provider/VM/黄金样例 | `IN_PROGRESS` |
| P10-004 | 八字/紫微/七政双人合盘 | 对应单术就绪 | `IN_PROGRESS` |
| P10-005 | 三术合参互证/分歧 | 至少两术内部测，三术才完整公开 | `IN_PROGRESS` |
| P10-006 | 六爻起卦与卦盘 | 手工值/核心数字投币合同 | `IN_PROGRESS` |
| P10-007 | 奇门九宫 | 问题/场景/时空黄金样例 | `IN_PROGRESS` |
| P10-008 | 大六壬课盘 | 问题/侧重/时空黄金样例 | `IN_PROGRESS` |
| P10-009 | 问事合参 | 六爻+奇门+六壬全部就绪 | `IN_PROGRESS` |
| P10-010 | 多盘问答的确定性 Brief | 三命术+ReadingDocument | `IN_PROGRESS` |
| P10-011 | 见相媒体与结构化视觉观察 Adapter | 私有媒体、质量、审计 | `IN_PROGRESS` |
| P10-012 | physiognomy Provider 与四模式 ViewModel | 结构化观察，不直接传图给结论模型 | `IN_PROGRESS` |
| P10-013 | 每日与剩余工具（寻时定盘事实、解梦、姓名分析）算法缺口逐项开发 | 每项单独合同/黄金样例/发布状态 | `IN_PROGRESS` |

### P11 — 各术深读、核对、追问、导出与分享

| ID | 任务 | 状态 |
|---|---|---|
| P11-001 | Claim Candidate、Guard 与 PresentationContract | `VERIFIED` |
| P11-002 | AcceptedCopy + ReadingDocumentV1 同步不可变落库 | `IN_PROGRESS` |
| P11-003 | 持久 Job、检查点、断网/换设备恢复与权益占用 | `IN_PROGRESS` |
| P11-004 | claim-level VerificationEvent、独立 ReportFeedback 与复核 | `VERIFIED` |
| P11-005 | 线性 Follow-up、越界 Recast 与次数/期限 | `IN_PROGRESS` |
| P11-006 | 专属 PNG/PDF 导出与短时下载 | `IN_PROGRESS` |
| P11-007 | 限时可撤销 ShareSnapshot 与隐私投影 | `VERIFIED` |

### P12 — 生产发布门禁

| ID | 门禁 | 通过标准 | 状态 |
|---|---|---|---|
| P12-001 | Runtime 原生准入 | 本机 V53 APFS 复制版已通过 14 Provider/220 signed release files/55 资料包/1328 evidence/220 closure；Mac mini native-full 仍须重跑完整 1584/0 | `IN_PROGRESS` |
| P12-002 | 凭据泄露闭环 | 关闭生产 debug；轮换 DB/API/Bot/AccessKey；失效会话；主账号 MFA/RAM 最小权限 | `BLOCKED` |
| P12-003 | 数据与恢复 | PostgreSQL/对象存储/Runtime 状态盘备份恢复演练 | `IN_PROGRESS` |
| P12-004 | 支付与对账 | 真实渠道验签、查单、重复通知、退款和日对账 | `NOT_STARTED` |
| P12-005 | 告警与容量 | API/Worker/Runtime/支付/通知 SLO、告警、队列与压测 | `NOT_STARTED` |
| P12-006 | 隐私、条款与合规 | 真实运营主体与处理活动、法律复核、数据权利演练、AI 标识 | `NOT_STARTED` |
| P12-007 | 中国大陆公开上线条件 | 所需许可/备案/内容治理逐项确认；测试内网不冒充公开上线 | `NOT_STARTED` |
| P12-008 | 安全与权限 | Staff RBAC、会话、审计、秘密、媒体授权、私有路由 noindex/no-store/SW 不缓存与负向测试 | `IN_PROGRESS` |
| P12-009 | 全旅程生产演练 | 游客→盘面→登录接管→购买→交付→追问→退款/邀请例外 | `IN_PROGRESS` |
| P12-010 | 用户最终验收与发布回滚 | 当前 Git SHA/制品/证据、回滚与禁流量开关确认 | `NOT_STARTED` |

Runtime 固定政策：Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。

`slots` 和 `max_slots` 表示 signed runner 的加权调度额度，不是操作系统 PID 数量上限。

## 12. 测试策略与命令

每次运行检查前必须先说明：该检查会发现什么失败，失败后会改变什么。无明确答案就不运行。

### 文档治理

```bash
uv run --project backend pytest \
  tests/contract/test_document_authority.py \
  tests/contract/test_native_release_policy.py -q

uv run --project backend pytest \
  tests/contract/test_document_authority.py -q

git diff --check
```

### UI 与合同

```bash
npm --prefix web test
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
npm --prefix admin test
npm --prefix admin run lint
npm --prefix admin run typecheck
npm --prefix admin run build
```

P1 必须补 Admin test 和浏览器 E2E scripts；在此之前缺少命令本身就是未完成，不得从清单删除。

### 后端与跨模块

```bash
uv run --project backend pytest backend/tests tests/contract -q
uv run --project backend ruff check --config backend/pyproject.toml backend tests
uv run --project backend mypy --config-file backend/pyproject.toml backend/app backend/worker
```

大范围全套测试只在影响面需要时运行；单个阶段先跑能发现该阶段具体失败的最小集合。

## 13. 证据索引

| 证据 | 路径 | 用途 |
|---|---|---|
| 青囊登录态产品/流程/响应式审计 | `docs/releases/evidence/2026-08-12-reference-site-audits/qingnang-authenticated-product-audit.md` | 产品地图、入口、免费盘面和断点依据 |
| METIS 生产/开源/响应式审计 | `docs/releases/evidence/2026-08-12-reference-site-audits/metis-live-responsive-ui-audit.md` | 表单、工作台、组件、开源边界依据 |
| 原生 Runtime | `docs/releases/evidence/2026-08-09-native-full/**` | 历史 Runtime 门禁证据 |
| Task 13 历史轨迹 | `docs/releases/evidence/2026-08-11-task13-*/**` | 旧后端/API 工作证据，不是新 UI 完成证据 |
| Dogfood 三轨 | `docs/releases/evidence/2026-08-12-dogfood-three-track/**` | 历史测试证据，不是正式商业账本 |
| UI 合同纠偏与回归 | `docs/releases/evidence/2026-08-14-ui-contract-correction/README.md` | 用户反馈后的旧产品树、两端 UI Lab、Web 交互、Admin 专用信息结构与四档 production 回归；不代替 P4-007 用户批准 |
| 四视口逐路浏览器验收 | `docs/releases/evidence/2026-08-14-route-acceptance/README.md` | Web 66 路由×4 视口、Admin 40 路由×4 视口的 standalone 生产证据；不代替 P4-006 来源截图比对或 P4-007 用户批准 |
| 当前工作树四视口逐路验收 | `docs/releases/evidence/2026-08-14-route-acceptance-working-tree/README.md` | 当前未提交工作树的 Web/Admin 逐路截图、manifest 完整性和 Admin unavailable 文案边界；仅 automated-only，不代替 P4-006/P4-007 |
| 2026-08-19 G6 / §18 全站验收 | `docs/releases/evidence/2026-08-19-route-acceptance/README.md` | 当前工作树 Web 71 + Admin 40 路由四视口、七态 Fixture 专项、工作台列宽与真实签名 Runtime `/bazi` owner result；机器证据就绪，不代替 P4-007 用户逐页批准 |
| P7-001 Catalog 生命周期基础 | `docs/releases/evidence/2026-08-14-p7-001-catalog/README.md` | ProductFamily/ProductVersion/ProductOffer 本地创建、发布、退役和 Offer 开关边界；不代替 Admin/API、真实支付或生产发布 |
| P7-005 Admin 权益调整 | `docs/releases/evidence/2026-08-14-p7-005-admin-entitlements/README.md` | Admin session/CSRF/角色门禁、账本生命周期、幂等重放和完整审计；不代替真实支付/生产发布或 P3/P9 Admin 页面接线 |
| P7-004 付费交付幂等边界 | `docs/releases/evidence/2026-08-14-p7-004-fulfillment/README.md` | 已确认 Payment → RESERVE → Reading Job → Accepted/Document → CONSUME/RELEASE 的本地服务与迁移回归；不代替真实支付渠道、Worker 编排、API/生产接线 |
| P7-002 支付尝试确认边界 | `docs/releases/evidence/2026-08-14-p7-002-payment-attempt-boundary/README.md` | 支付尝试渠道绑定、单次确认、数据库唯一约束和重复回调本地回归；不代替真实支付适配器、渠道验签或生产到账 |
| P7-006 支付对账本地闭环 | `docs/releases/evidence/2026-08-14-p7-006-payment-reconciliation/README.md` | 已验签通知收据、重复事件幂等、对账批次/差异和退款聚合超额分类；真实渠道、定时任务、Admin 处理和 P12-004 仍未完成 |
| P7-007 通知 Outbox 投递状态 | `docs/releases/evidence/2026-08-14-p7-007-notification-worker/README.md` | Outbox claim lease、fencing token、失败重试、终态失败和可注入 worker；真实供应商/退信/部署仍未完成 |
| P12-008 Staff 会话与审计本地证据 | `docs/releases/evidence/2026-08-14-p12-008-admin-security/README.md` | Staff Session 脱敏查询、superadmin+CSRF 强退、审计和 Admin 页面；生产秘密、媒体授权与完整员工管理仍未完成 |
| P12-002 生产秘密槽位审计 | `docs/releases/evidence/2026-08-14-p12-002-production-secret-slots/README.md` | 只记录 fail-closed 槽位检查结果，不记录秘密值；未声称 Secret Manager、轮换或生产注入已经完成 |
| P12-003 测试 PostgreSQL 备份恢复 | `docs/releases/evidence/2026-08-14-p12-003-test-backup-restore/README.md` | 测试库迁移前 dump 已恢复到临时库并清理；对象存储、Runtime 状态盘和生产恢复仍缺 |
| P12-009 测试服务器全旅程 | `docs/releases/evidence/2026-08-14-p12-009-test-trajectory/README.md` | Fake/虚构数据下游客→登录→预览→测试权益→三类阅读→追问全 accepted；不代替真实支付、退款、合规或生产演练 |
| Admin 平台只读与数据权利切片 | `docs/releases/evidence/2026-08-14-admin-platform-surfaces/README.md` | 设置、健康、订单/支付/退款、用户/Subject、权益、邀请、员工、CMS、解读任务真实读取与受控命令；不代替真实支付、生产部署、邮件邀请、合规或用户批准 |
| P11-005 追问合同本地边界 | `docs/releases/evidence/2026-08-14-p11-005-follow-up-contract/README.md` | ProductVersion 快照的次数/期限、严格线性和活动子版本拒绝；不代替真实权益消费、Recast 输入契约、PNG/PDF 或生产接线 |
| P11-002 AcceptedCopy → ReadingDocument 构建接线 | `docs/releases/evidence/2026-08-15-p11-002-reading-document-builder/README.md` | Accepted 后同事务读取成功 Candidate、投影类型化 ViewModel 并不可变保存 ReadingDocument；不代替所有产品合同、真实生产 Worker、PNG/PDF 或 P12 门禁 |
| P11-007 本地 Fulfillment 创建与绑定 API | `docs/releases/evidence/2026-08-15-p11-007-fulfillment-binding-api/README.md` | 已确认 Payment 到 owner-scoped Reading Job 的本地 API、幂等、CSRF 和终止态边界；不代替真实支付、生产账本、Worker 或发布门禁 |
| P10-010A 三术多盘确定性 Brief 内部切片 | `docs/releases/evidence/2026-08-14-p10-010a-canwen-runtime/README.md` | 八字主盘 + 紫微/七政必选 Runtime comparisons 的编译、真实 13/13 Runtime Prepared 和拒绝边界；不代替 Canwen ViewModel/API/UI、互证分歧规则或生产接线 |
| P10-010B Canwen 共同事实范围投影 | `docs/releases/evidence/2026-08-14-p10-010b-canwen-scope-synthesis/README.md` | `canwen-view/v1`、API/UI 和三术共同事实范围投影；V52 已补七政跨术合同；不代替实质互证分歧、Worker、深读或生产接线 |
| P10-005A Hecan 结构化 Runtime/API/UI 接入 | `docs/releases/evidence/2026-08-15-p10-005a-hecan-structure/README.md` | `hecan_preview`、Hecan product identity、`hecan-view/v1` 和至少两术真实 Runtime 结构范围；不代替三术完整跨术事实、实质互证/分歧、深读、Worker 或生产门禁 |
| P10-009 问事合参三术核心接入 | `docs/releases/evidence/2026-08-14-p10-009-wenshi-runtime/README.md` | 六爻主术 + 奇门/大六壬 required comparisons、Wenshi 产品/三术集合持久化、API/UI 与结构事实投影；不代替实质互证、深读、Worker、ReadingDocument、生产准入或用户批准 |
| P10-013A 梅花时间起卦结构盘内部切片 | `docs/releases/evidence/2026-08-14-p10-013a-meihua-runtime/README.md` | 时间起卦的历史编译、真实 Runtime Prepared 和 `meihua-chart/v1` 结构投影；其余四种起法后续见 P10-013D |
| P10-013B 五个内部 Runtime Provider 核心接线 | `docs/releases/evidence/2026-08-14-p10-013b-runtime-core-providers/README.md` | `luming-nayin`、`taiyi`、`selection`、`fengshui`、`physiognomy` 的 manifest 对齐编译、真实 Runtime Prepared 和严格 ViewModel 投影；不代替公开产品合同、Worker、黄金样例或生产接线 |
| P10-013C 真太阳时与子时 Runtime 合同 | `docs/releases/evidence/2026-08-14-p10-013c-solar-runtime-contract/README.md` | 产品时间/子时别名映射、真太阳时运势坐标接线与 8 项真实 Runtime 回归；不代替合参、公开产品或生产准入 |
| P10-013D 梅花五种起法核心接入 | `docs/releases/evidence/2026-08-14-p10-013d-meihua-casting-methods/README.md` | 五种起法的真实字段编译、API/UI 输入接线、V51 one-shot Provider 和 `meihua-chart/v1` 投影；不代替 Worker、ReadingDocument、深读、生产准入或用户批准 |
| P10-013E 本命音律纳音事实工具 | `docs/releases/evidence/2026-08-15-p10-013e-rhythm-runtime/README.md` | `rhythm_preview`、独立 `rhythm-facts-view/v1`、真实 Worker/ReadingDocument、私有 API、工具输入和 Runtime Chart 接线；不代替完整音律解释、姓名学或 P12 生产门禁 |
| P10 核心 Runtime 版本矩阵复核 | `docs/releases/evidence/2026-08-15-p10-core-runtime-matrix/README.md` | V51/V52 真实 one-shot 已复核 13 Provider 的 Provider→Prepared→Worker→Accepted→ReadingDocument 边界；V52 另通过八字/紫微/七政关系 Worker；不代替各产品公开合同、深读或生产准入 |
| P10 核心 ViewModel Web 结果层接线 | `docs/releases/evidence/2026-08-15-p10-core-runtime-matrix/README.md` | 已注册并分派核心术数 ViewModel，以 Runtime calculated facts 渲染；对应产品输入/API/UI 已接入本地纵切片；Web `70 files / 441 tests`、typecheck、lint、build 通过；不代表完整深读/生产准入 |
| P10-011 见相媒体 Adapter 与结构化观察边界 | `docs/releases/evidence/2026-08-15-p10-011-physiognomy-media-adapter/README.md` | 本地私有媒体生命周期、质量/授权门禁、审计脱敏、HTTP/数据库/前端 File 上传和冻结 physio 输入已通过；生产对象存储和外部验收仍缺 |
| P8-008 未来商业关闭态与合同 | `docs/releases/evidence/2026-08-14-p8-008-future-commerce-closed/README.md` | 定价页与 OpenAPI 明确关闭自动续费、代币余额、充值钱包和点击即付款；不代替未来订阅/充值产品批准或真实支付生产验收 |
| P4-006 通用视觉范围决定 | `docs/releases/evidence/2026-08-14-p4-006-generic-visual-decision/README.md` | 用户确认文本与视觉均为通用表达，不存在必须复刻青囊/METIS 的产品问题；不代替 P4-007 用户浏览批准 |
| P4-007 测试服务器上传 | `docs/releases/evidence/2026-08-14-p4-007-test-server-upload/README.md` | 当前工作树应用快照已上传并切换到 `fateradar-prod` 测试验收机；等待用户逐页浏览批准 |
| 绑定清单可复原基线 | `docs/releases/evidence/2026-08-18-binding-manifest-baselines/` | `classical-evidence-bindings-v1.json` 施工前/交付态与自动备份；用于哈希核对和回滚，不代表 Runtime 已发布 |

外部原件仍保留于：

```text
/Users/yuhanglin/.codex/visualizations/2026/08/12/
019ff5b8-ffff-7f42-8629-e68f090ebc05/qingnang-audit.md
/Users/yuhanglin/.codex/visualizations/2026/08/12/
019ff5b8-ffff-7f42-8629-e68f090ebc05/metis-live-audit.md
```

## 14. 当前断点与唯一下一步

本节只回答两个问题：现在卡在哪，下一步做什么。施工流水不再写入本节，历史条目已按原文归档到 `docs/releases/evidence/ledger-archive/`。

### 14.1 唯一全局门禁：P4-007 用户逐页批准

P2 的 18 项与 P3 的 12 项全部停在 `IN_PROGRESS`，原因不是缺证据，而是缺 P4-007。P4 是不可跳过门禁：它未完成前不得出现「UI 已完成」的表述，也不得实施会约束或改写未批准页面合同的后端产品功能。

机器侧能做的部分已经做完：

- 全站四视口逐路证据：Web 71 + Admin 40 路由 × 4 视口共 444 条正常路由视图，最大页面溢出 `0px`，唯一 h1、Skip Link 首焦点、reduced motion 内容保留均通过，Fixture / raw JSON / snake_case / 旧品牌四类禁项均 0 失败。证据：`docs/releases/evidence/2026-08-19-route-acceptance/README.md`。
- 逐页人工验收清单：按公共站、产品录入、工作台与结果、账户区、Admin 五族覆盖 Web 71 + Admin 40，合计 111 条正常路由；每条给出路由、当前构建关键变化、实际 1440 截图路径、判断问题和空白结论栏，114 个截图/文档链接实测均存在，禁用验收标记 0，没有代填结论。清单：`docs/releases/evidence/2026-08-19-route-acceptance/USER-ACCEPTANCE-CHECKLIST.md`。

**下一步只有一个动作：用户按该清单逐页浏览并逐条给出结论。** 清单之外的任何自动化、DOM 断言、组件单测或接口绿灯都不能推进 P4-007（依据 §1.3）。

### 14.2 等待用户裁决或授权的三项

这三项不由施工方推进，也不因时间推移自动解除。

| 编号 | 事项 | 现状与依据 |
|---|---|---|
| D-1 | 2026-08-19 测试服务器发布的授权归属 | 当轮施工提示词红线明确写「不 push、不上传测试机、不部署」，但发布确已发生并原子切换 `/opt/fateradar/current`，而本机当日 codex 会话记录为空。旧 release 与切换前环境备份均保留，未修改生产、未 push。归属确认前只记录事实，不判定违规，也不据此推进 P4-007。证据：`docs/releases/evidence/2026-08-19-bazi-test-server-upload/README.md` |
| D-2 | `/liuyao`、`/meihua` 的能力档位 | 两者仍为 B 档且 `user_decision_pending=True`（`backend/app/readings/capability_policy.py`），需用户裁定是否开放 |
| D-3 | P10-001 的 V53 重签授权 | 第 4 个 Claim Unit `bazi.day-master-root-support-v1` 只存在于 core 源码，当前签名制品只发出 3 个。重签必然改变 manifest digest，describe 很可能变，capability shape 须按实测重算、禁止猜哈希；新树必须放新目录，回滚点为保持现行 `.runtime/v53-time-check-release` 不动。证据：`artifacts/runtime-evidence/2026-08-19-v53-resign-impact.md` |

### 14.3 剩余产品断点

平台层与算法层已推得很深：13 个 V51 Provider 完成真实 `Provider → Prepared → Worker → Accepted → typed ReadingDocument` 闭环，V53 寻时定盘通过 14 能力真实矩阵，V52 完成八字/紫微/七政关系 Worker 闭环。以下是仍未完成的产品能力，不受 P4-007 阻塞的部分可以并行推进：

- 寻时定盘的完整古法校时、候选淘汰与结论规则（事实层与结构化事件证据排序已通过，完整定盘未接）
- 解梦、姓名分析两项工具的正式来源规则与 Provider（当前无正式输入/输出合同与规则包）
- 三术合参的实质互证与分歧裁决（`convergence` / `disagreements` 仍为空，当前只有信号层与范围投影）
- 见相的手相、体态、综合三模式（当前只支持 `face` scope）
- 各术深读、追问、导出在真实产品与真实 Worker 上的完整交付

### 14.4 外部门禁

P12 门禁顺序：备案/许可主要约束 P12-007 的中国大陆公开生产上线，不是开发、内网联调、测试服务器浏览、备份恢复演练、告警容量建设、Staff 安全回归或支付沙箱的前置条件。P12-003、P12-005、P12-008 可先做本地/测试演练；P12-004 可先做沙箱，但真实渠道验签、查单、退款和对账要等真实支付凭据与环境；P12-006 可先写草案并做法律复核准备；P12-009 可先做测试旅程，生产旅程要等真实渠道；P12-010 永远最后，在制品上传、外部门禁和用户批准后执行。

真实模型、Mac mini 完整 native-full、凭据轮换、备份恢复、告警容量、合规备案和最终发布批准仍是外部门禁，不由本仓库工作解除。

### 14.5 当前工作树状态

主工作树很脏：约 425 个未提交改动（web / artifacts / backend / admin 为主），其中 Codex 团队配置 `AGENTS.md`、`.codex/agents/`、`.codex/team-registry.md` 尚未纳入版本库。这不改变任何任务状态，但意味着「当前构建」只存在于本机；引用工作树证据时必须同时记录该事实，且不得把来源不明的历史改动顺手打包进新事件。

### 14.6 历史流水

2026-08-13 至 2026-08-19 的施工流水共约 310 条，已按原文逐字迁出，未作改写、摘要或删除：

| 归档 | 内容 |
|---|---|
| `docs/releases/evidence/ledger-archive/2026-08-14--2026-08-17-breakpoint-log.md` | 原 §14 的 144 条日期流水段落 |
| `docs/releases/evidence/ledger-archive/2026-08-13--2026-08-19-change-log.md` | 原 §15 的 158 行施工状态行，外加原 §14 中 10 行缺表头的表格行 |

归档是历史证据，不是权威。其中的历史结论可能已被后续工作推翻，纠错请按 §0 规则 4 新增 dated addendum，不覆盖原文。

## 15. 变更记录

本表只记录用户明确确认、明确授权或明确裁决的冻结决定。施工与证据状态记录不进入本表，写入对应阶段的状态字段与证据目录即可。

| 日期 | 变更 | 批准 |
|---|---|---|
| 2026-08-13 | 结束完整 `grill-me`；冻结自有算法 + 青囊产品模式 + METIS 表现层、UI-first、完整 Admin、密码、商业、邀请和唯一文档纪律 | 用户明确确认 |
| 2026-08-13 | `main` 冻结为唯一开发基线；旧 UI 分支只取证，不整体合并 | 用户明确确认 |
| 2026-08-13 | 旧 FateRadar 名称与墨绿金视觉退出当前产品 | 用户明确确认 |
| 2026-08-14 | 用户判定现行中性视觉「整体廉价/乱」，经 `grill-me` 逐题确认后批准方向 C「现代 SaaS 锐感」全站换皮（决策记录与审计：`docs/redesign/2026-08-14-*.md`）。影响范围：`DESIGN.md` §2/§3/§4/§6.1/§6.3/§8.3/§8.5/§10 修订；首页改「价值主张 + 任务入口」混合结构；多盘问答（`canwen`）并入命盘合参，原路由保留重定向、历史任务与报告不失效；`/account` 重建为消费 App 式「我的」页；字阶冻结收口。迁移与重新验收：全部公共页、产品流、工作台、账户区、Admin 需按新合同重走 360/768/1024/1440 真实浏览器验收并逐页由用户批准；既有 P2/P3/P4/P4-007 验收状态不自动继承，逐项重验 | 用户明确确认 |
| 2026-08-18 | G1 可核验性路线用户裁决：选定 **C + B，不做 A**。补充实测事实（原调查遗漏）：签名 release 的 `references/index/evidence-rules.jsonl` 已自带逐字原文——1328 条规则下 478 条 `classical_sources` 条目**全部**带 `verbatim_quote` 与 `verbatim_quote_sha256`（覆盖率 100%），`verbatim_quote_sha256` 实测等于 `sha256(verbatim_quote.encode("utf-8"))`，条目另带 `path` / `sha256` / `anchor` 锁定语料文件版本与行号；本轮 7 条页面引文在 release 自带记录中逐字命中 `7/7`。故可核验链条拆为四步，**第 1–3 步仅凭签名 release 即可完成，只有第 4 步（原文确在该书该行）需要外置 fulltext**。路线 C 即新增仅依赖 release 的核验模式（按 `evidence_ref` 反查规则记录，逐字比对 `excerpt`↔`verbatim_quote`、`locator`↔`anchor`、校验哈希，任一不满足 fail closed）。不做 A 的理由是授权而非体积：54 部全文中含已标点整理的简体本，标点整理本通常另有著作权，授权未确认前不得固化进签名制品；C 已取得 A 的大部分实用价值，日后确认授权可增量补做。决策与依据记入 `artifacts/runtime-evidence/2026-08-18-g1-self-verification-investigation/README.md` 的 dated addendum，未覆盖原调查记录。 | 已裁决，待施工 |
| 2026-08-19 | 项目经理审美裁定写入 `DESIGN.md` §2.1。方向 C 不变；收紧廉价感禁则、首页玻璃隔离、结果页证据优先、主操作走黑按钮。影响：只收紧视觉合同，不改产品地图/路由/品牌名。前端按新 §2.1 实现，不擅自改合同。P2/P3/P4-007 验收不自动继承，仍须用户逐页批准。 | 用户明确授权项目经理为好看改 UI 文档 |

历史施工状态行见 `docs/releases/evidence/ledger-archive/2026-08-13--2026-08-19-change-log.md`。
