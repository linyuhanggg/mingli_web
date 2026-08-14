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
| 真实浏览器、机器、测试和发布证据 | `docs/releases/evidence/**` | 只存产物 |

规则：

1. 不得新增 `HANDOFF*`、`docs/plans/*`、平行 blueprint、第二份 checklist 或施工叙事日志。
2. 新想法进入本文对应 Backlog，不得偷偷改写活跃阶段。
3. 改变已经批准的产品地图、页面层级、固定术数组合或视觉合同，必须先写影响范围、迁移与重新验收项，并由用户明确批准。
4. ADR 保留历史原文；旧决定失效时新增修订 ADR，不伪造历史。
5. 证据目录只存可复验产物。截图、测试和 Git SHA 是证据，不会自动把任务变成完成。
6. 两份参考站实审计永久保留；未来纠错用新的 dated addendum，不覆盖旧证据。

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
| `/tools/time-check` | 寻时定盘流程 | index，未接能力诚实标记 |
| `/tools/chart-similarity` | 同盘匹配流程 | index，未接能力诚实标记 |
| `/tools/rhythm` | 本命音律流程 | index，未接能力诚实标记 |
| `/tools/five-elements` | 五行喜忌流程 | index，未接能力诚实标记 |
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
| P10-011 | 见相媒体与结构化视觉观察 Adapter | 私有媒体、质量、审计 | `NOT_STARTED` |
| P10-012 | physiognomy Provider 与四模式 ViewModel | 结构化观察，不直接传图给结论模型 | `IN_PROGRESS` |
| P10-013 | 每日与六工具算法缺口逐项开发 | 每项单独合同/黄金样例/发布状态 | `IN_PROGRESS` |

### P11 — 各术深读、核对、追问、导出与分享

| ID | 任务 | 状态 |
|---|---|---|
| P11-001 | Claim Candidate、Guard 与 PresentationContract | `VERIFIED` |
| P11-002 | AcceptedCopy + ReadingDocumentV1 同步不可变落库 | `IN_PROGRESS` |
| P11-003 | 持久 Job、检查点、断网/换设备恢复与权益占用 | `IN_PROGRESS` |
| P11-004 | claim-level VerificationEvent、独立 ReportFeedback 与复核 | `VERIFIED` |
| P11-005 | 线性 Follow-up、越界 Recast 与次数/期限 | `IN_PROGRESS` |
| P11-006 | 专属 PNG/PDF 导出与短时下载 | `NOT_STARTED` |
| P11-007 | 限时可撤销 ShareSnapshot 与隐私投影 | `VERIFIED` |

### P12 — 生产发布门禁

| ID | 门禁 | 通过标准 | 状态 |
|---|---|---|---|
| P12-001 | Runtime 原生准入 | 本机 APFS 复制版已通过 13 Provider/217 文件/55 资料包/1328 evidence；Mac mini 仍须重跑完整 1584/0 | `IN_PROGRESS` |
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
| P10-010A 三术多盘确定性 Brief 内部切片 | `docs/releases/evidence/2026-08-14-p10-010a-canwen-runtime/README.md` | 八字主盘 + 紫微/七政必选 Runtime comparisons 的编译、真实 13/13 Runtime Prepared 和拒绝边界；不代替 Canwen ViewModel/API/UI、互证分歧规则或生产接线 |
| P10-010B Canwen 共同事实范围投影 | `docs/releases/evidence/2026-08-14-p10-010b-canwen-scope-synthesis/README.md` | `canwen-view/v1`、API/UI 和三术共同事实范围投影；V52 已补七政跨术合同；不代替实质互证分歧、Worker、深读或生产接线 |
| P10-005A Hecan 结构化 Runtime/API/UI 接入 | `docs/releases/evidence/2026-08-15-p10-005a-hecan-structure/README.md` | `hecan_preview`、Hecan product identity、`hecan-view/v1` 和至少两术真实 Runtime 结构范围；不代替三术完整跨术事实、实质互证/分歧、深读、Worker 或生产门禁 |
| P10-009 问事合参三术核心接入 | `docs/releases/evidence/2026-08-14-p10-009-wenshi-runtime/README.md` | 六爻主术 + 奇门/大六壬 required comparisons、Wenshi 产品/三术集合持久化、API/UI 与结构事实投影；不代替实质互证、深读、Worker、ReadingDocument、生产准入或用户批准 |
| P10-013A 梅花时间起卦结构盘内部切片 | `docs/releases/evidence/2026-08-14-p10-013a-meihua-runtime/README.md` | 时间起卦的历史编译、真实 Runtime Prepared 和 `meihua-chart/v1` 结构投影；其余四种起法后续见 P10-013D |
| P10-013B 五个内部 Runtime Provider 核心接线 | `docs/releases/evidence/2026-08-14-p10-013b-runtime-core-providers/README.md` | `luming-nayin`、`taiyi`、`selection`、`fengshui`、`physiognomy` 的 manifest 对齐编译、真实 Runtime Prepared 和严格 ViewModel 投影；不代替公开产品合同、Worker、黄金样例或生产接线 |
| P10-013C 真太阳时与子时 Runtime 合同 | `docs/releases/evidence/2026-08-14-p10-013c-solar-runtime-contract/README.md` | 产品时间/子时别名映射、真太阳时运势坐标接线与 8 项真实 Runtime 回归；不代替合参、公开产品或生产准入 |
| P10-013D 梅花五种起法核心接入 | `docs/releases/evidence/2026-08-14-p10-013d-meihua-casting-methods/README.md` | 五种起法的真实字段编译、API/UI 输入接线、V51 one-shot Provider 和 `meihua-chart/v1` 投影；不代替 Worker、ReadingDocument、深读、生产准入或用户批准 |
| P8-008 未来商业关闭态与合同 | `docs/releases/evidence/2026-08-14-p8-008-future-commerce-closed/README.md` | 定价页与 OpenAPI 明确关闭自动续费、代币余额、充值钱包和点击即付款；不代替未来订阅/充值产品批准或真实支付生产验收 |
| P4-006 通用视觉范围决定 | `docs/releases/evidence/2026-08-14-p4-006-generic-visual-decision/README.md` | 用户确认文本与视觉均为通用表达，不存在必须复刻青囊/METIS 的产品问题；不代替 P4-007 用户浏览批准 |
| P4-007 测试服务器上传 | `docs/releases/evidence/2026-08-14-p4-007-test-server-upload/README.md` | 当前工作树应用快照已上传并切换到 `fateradar-prod` 测试验收机；等待用户逐页浏览批准 |

外部原件仍保留于：

```text
/Users/yuhanglin/.codex/visualizations/2026/08/12/
019ff5b8-ffff-7f42-8629-e68f090ebc05/qingnang-audit.md
/Users/yuhanglin/.codex/visualizations/2026/08/12/
019ff5b8-ffff-7f42-8629-e68f090ebc05/metis-live-audit.md
```

## 14. 当前断点与唯一下一步

P0 已完成治理；P1 基础壳、产品旅程和 Admin 专用壳已通过当前工作树的本地合同与四视口浏览器门禁。P6/P7/P9/P11 已有本地数据与合同基础，P10 已完成六类单术的 Runtime → Reading → ViewModel 技术接线，并新增梅花五种起法、问事合参三术核心接入、八字/紫微/七政双人合盘的双主体结构接线，以及五个内部 Provider 的 manifest 对齐编译 → Runtime prepare → 严格 ViewModel 核心切片；这些都不能替代 UI 逐页验收、真实 Worker 轨迹和用户批准。当前断点仍在 P2–P4：完整 C 端/Admin 状态与视觉审阅必须按本清单完成本地门禁，再由用户逐页批准 P4-007。双人合盘的深读/ReadingDocument/真实 Worker、合参完整互证/分歧、见相媒体 Adapter、其余工具公开产品合同和 P10-013 的完整产品化仍未完成；PNG/PDF renderer、真实支付/模型、Mac mini 完整 native-full、凭据轮换、备份恢复、告警容量、合规备案和最终发布批准仍是外部门禁。

2026-08-14 P4-006 范围决定：用户明确确认当前产品文本与视觉效果均为通用表达，不存在需要复刻青囊/METIS 的视觉问题；P4-006 标记 `VERIFIED`，历史参考截图缺口不再阻塞。P4-007 已进入 `IN_PROGRESS`：测试验收服务器当前为 `ui-preview-20260814-wenshi-d329544b8a91`，Web/Admin 双隧道入口和健康检查已记录，待用户亲自浏览并批准。

2026-08-14 P10-001 本地技术切片：真实 one-shot Runtime 在专用 venv 通过 `describe → prepare`，后端新增严格 `bazi-chart/v1` 投影并由私有结果 API/阅读页优先消费；只读计算事实，不把原始输入带入 ViewModel。公开 `/bazi` 已接入“出生事实 → ProfileVersion → Reading → 私有结果页”，仍未完成深读/导出、真实 Worker 轨迹和四视口用户批准。P10-001、P4-007 和 P12 外部门禁不变。证据：`docs/releases/evidence/2026-08-14-p10-001-local-bazi-view-model/README.md`。

2026-08-14 P10 单术技术补充：紫微、七政、六爻、奇门、大六壬已完成对应 Request Compiler、显式 API、Runtime ViewModel 投影和产品任务入口；合成 Runtime probe 分别返回 30/21/28/24/18 个事实，私有结果页按 `ziwei-chart/v1`、`qizheng-chart/v1`、`liuyao-chart/v1`、`qimen-chart/v1`、`daliuren-chart/v1` 展示。定向 Backend 91 passed、Web 45 passed、OpenAPI/Ruff/mypy/typecheck 通过。P10-002/003/006/007/008 进入 `IN_PROGRESS`，不标记 `VERIFIED`，因为真实 Runtime Worker 轨迹、黄金样例、四视口浏览器证据和用户批准仍缺。证据：`docs/releases/evidence/2026-08-14-p10-single-art-runtime/README.md`。

2026-08-14 P10 单术本地浏览器冒烟：当前工作树启动本机 Web 后，六个单术入口在 360/768/1024/1440 四档视口共 24 个组合均无横向溢出；六个入口均展示 `确定性盘面已接入`、对应表单以及时区/地点输入。此为自动化结构检查，不替代真实 Worker 轨迹、黄金样例、截图归档和用户批准；P10-002/003/006/007/008 继续保持 `IN_PROGRESS`。证据：`docs/releases/evidence/2026-08-14-p10-single-art-runtime/README.md`。

2026-08-14 P10-012 结构化相术投影补充：专用 Runtime 在无个人资料、无原始图片的合成输入上通过 `describe → prepare`，返回可见观察、缺失目标、冲突、来源比较和不确定性事实；后端新增严格 `physiognomy-view/v1` 投影，前端结果页只展示中性结构化观察，不读取 `/input/` 或媒体/来源私有字段。P10-012 进入 `IN_PROGRESS`；P10-011 媒体 Adapter、质量/授权审计、四模式真实链路仍未完成，也不提前标记见相产品可用。证据：`docs/releases/evidence/2026-08-14-p10-single-art-runtime/README.md`。

2026-08-14 P10-010A 三术多盘确定性 Brief 内部切片：新增 `canwen_preview` 编译器，固定八字为主 Provider，把用户选择的紫微/七政明确映射为必选 `ziwei`/`xingming` comparisons；重复、少选、未知或主术顺序错误直接拒绝。合成输入通过冻结 13/13 Runtime 启动门禁并返回 `Prepared`，Brief 实际含 `bazi`、`ziwei`、`xingming` 三组计算事实；默认 Backend 回归 `62 passed/1 skipped`，显式真实 Runtime 回归 `1 passed`。本切片未开放 API/UI，历史边界见 P10-010B。证据：`docs/releases/evidence/2026-08-14-p10-010a-canwen-runtime/README.md`。
2026-08-14 P10-010B Canwen 共同事实范围投影：新增严格 `canwen-view/v1` projector、`/api/v1/readings/canwen`、Reading Service、Web 提交和结果展示；只消费 Runtime 声明的 `dimension_fact_scope`，八字/紫微范围可追溯，七政缺少该跨术合同则进入 `missing_art_ids`，不伪造实质性互证或分歧。当前定向回归合计 `128 passed`，Ruff/mypy/TypeScript 通过；真实三盘 Brief 成功投影为 `CanwenViewV1`，不支持的多术 Brief 不会误投影成 Canwen。P10-010 仍缺七政跨术权威合同、实质性规则、ReadingDocument/深读、Worker、黄金样例和生产门禁。证据：`docs/releases/evidence/2026-08-14-p10-010b-canwen-scope-synthesis/README.md`。

2026-08-14 P10-013A 梅花时间起卦内部切片：新增 `meihua_preview` 编译器，固定使用明确的 `time` 起法，事件时间先按确认时区归一化，再把 `meihua` 送入 Runtime；当时其余四种起法会直接拒绝，不会静默替换成时间起卦。新增严格 `meihua-chart/v1` 投影，只展示本卦、互卦、变卦、动爻、体用结构及 Runtime 的关系事实状态，不生成吉凶结论。后续五种起法核心/API/UI 接入见 P10-013D。证据：`docs/releases/evidence/2026-08-14-p10-013a-meihua-runtime/README.md`。
2026-08-14 P10-013B 五个内部 Runtime Provider 核心接线：新增 `luming-nayin`、`taiyi`、`selection`、`fengshui`、`physiognomy` 的 manifest 对齐 Request Compiler、严格 ViewModel 合同和 Runtime projector。合成定向回归 `88 passed/8 skipped`；冻结 V51 Runtime 真实回归五项 `5 passed/19 deselected`。命禄纳音、太乙只投影确定性事实；择日只投影有界候选/淘汰/排序/谱系；风水只投影观测、冲突、不确定性和缺失项；相法只接收已结构化的可见观察，不接图片或未结构化转写。五者保持内部模块，不新增公开页面或 API，不代替公开产品合同、真实 Worker、黄金样例和生产 admission。证据：`docs/releases/evidence/2026-08-14-p10-013b-runtime-core-providers/README.md`。

2026-08-14 P10-013C 真太阳时与子时 Runtime 合同修复：产品 `solar` 时间口径编译为 `local_apparent_solar-v1`，子时产品别名编译为 Runtime 支持的 `midnight`/`late-zi-next-day`；`fortune` 在真太阳时或经度均时策略下补齐坐标事实，民用时冻结 fixture 不变。Request Compiler `61 passed`；冻结 V51 one-shot 真实回归 `8 passed/16 deselected`；经用户授权的个人资料只做临时本机核验，不写入仓库或证据正文，13 Provider 均返回 `Prepared`。本修复不代替合参跨术事实规则、公开 API/UI、真实 Worker、黄金样例或生产 admission。证据：`docs/releases/evidence/2026-08-14-p10-013c-solar-runtime-contract/README.md`。
2026-08-14 P10-013D 梅花五种起法核心接入：新增数字、声数、观察、完整卦象四种真实 Runtime 字段合同，并同步 `MeihuaStartRequest`、Reading Service、私有 API、Web 输入表单和既有 `meihua-chart/v1` 投影；方法特有字段缺失或越界在编译期拒绝，不静默换成时间起卦。Backend 编译器/API 定向回归 `111 passed`，Web 类型检查通过且相关流程 `19 passed`；冻结 V51 one-shot 梅花时间 + 四种起法 `2 passed/23 deselected`。P10-013 整体仍未完成 Worker、ReadingDocument/深读、导出分享、生产准入和用户批准。证据：`docs/releases/evidence/2026-08-14-p10-013d-meihua-casting-methods/README.md`。

2026-08-14 P4-007/P10-001 测试机发布补充：当前工作树核心接线快照已上传并切换到 `fateradar-prod` 的 `ui-preview-20260814-core-9eb380d1acde`。服务器 Web/Admin build、`fateradar` 用户后端 import preflight、PostgreSQL 迁移前备份、`alembic check`、API live/ready、Web `/`/`/canwen`/`/meihua`/`/account`、Admin `/login` 和五个服务 active 均通过；旧 release 保留可回滚。发布中发现并修正归档目录权限、`.venv/bin` 执行位和 Next `.next/server` 运行写目录，失败切换均自动回滚，不完整 release 未留在 `current`。P4-007 仍等待用户逐页浏览批准；测试机仍为 `local + Fake`，不代表生产或公开上线。证据：`docs/releases/evidence/2026-08-14-p4-007-test-server-upload/README.md`。

2026-08-15 P4-007/P10-009 测试机发布更新：问事合参三术核心接线快照已切换为 `ui-preview-20260814-wenshi-d329544b8a91`，数据库已到 `0033_reading_runtime_caps`；Web `/`/`/wenshi`/`/canwen`/`/meihua`、Admin `/login`、API live/ready、`/api/openapi.json` 的 `startWenshiReading`、临时公网预览和五个服务均通过。此 release 只支持虚构数据的 `local + Fake` 浏览；P4-007 仍等待用户逐页批准，P10-009 仍只完成三术结构事实投影，不代表实质互证/分歧、深读、Worker 或生产准入。证据：`docs/releases/evidence/2026-08-14-p4-007-test-server-upload/README.md`、`docs/releases/evidence/2026-08-14-p10-009-wenshi-runtime/README.md`。
2026-08-15 P10-005A 三术合参结构接入：`/api/v1/readings/hecan`、`hecan_preview` 编译器、独立 `product_id=hecan`、严格 `hecan-view/v1` 投影和 Web 结果展示已接通；Canwen 同时修正为独立 `product_id=canwen`，不再被保存为普通八字。真实 V51 Runtime 的临时本机核验返回 `Prepared` 和 `bazi/ziwei/xingming`；只选八字+紫微时 `career` 范围完整，三术全选时七政跨术范围仍诚实进入 `missing_art_ids`。个人资料未落盘。Hecan 仍只是结构范围切片，不代表完整三术互证/分歧或深读完成。证据：`docs/releases/evidence/2026-08-15-p10-005a-hecan-structure/README.md`。
2026-08-15 P10-005A 复核收口：修正合参结果页按 `product_id`/ViewModel 分派、七政坐标编译门禁、Hecan 两/三术类型、八字主术与 ProfileVersion UUID 表单约束，并在 production/real-traffic settings 下拒绝非 P0 Runtime capability 集合；OpenAPI 补齐 `ReadingResultResponse.view_model`。全量本地门禁为 Backend `807 passed/102 skipped`、Web `435 passed`、Admin `121 passed`，真实 one-shot 临时复核仍为 `Prepared`/结构性缺口诚实暴露。Hecan 仍只是结构范围切片，不代表完整三术互证/分歧或深读完成。证据：`docs/releases/evidence/2026-08-15-p10-005a-hecan-structure/README.md`。
2026-08-15 P10-004 双人合盘接线与架构纠偏：八字/紫微/七政三条双主体 Request Compiler、API、ProfileVersion 双 ID 持久化、关系类型绑定、三种关系 ViewModel、产品内结果路由和授权/未成年人确认已接通；前端完成双方资料、性别、时区、民用时/真太阳时、子时口径和七政坐标采集，并在点击后真实创建两个 ProfileVersion 再启动对应术数任务。关系 ViewModel 现在只接受 Runtime 已计算的 `relationship_signals` 事实，不再由业务后端从四柱、宫位或星体位置重新计算规则；本地 Fake 以同一事实合同验证接线。关系投影/档案/合盘回归 `23 passed`，Web 关系定向回归 `15 passed`，相关 typecheck、Ruff、mypy 通过。真实 one-shot V51 当前只能返回双方独立单盘 `Prepared`，没有 Runtime-native `relationship_signals`，所以真实关系 ViewModel 会保持缺失而不伪造结果。P10-004 仍为 `IN_PROGRESS`：Runtime 原生关系 Provider/postprocessor、新 release/manifest、完整规则、深读/ReadingDocument、Worker 黄金样例、四视口真实浏览器证据、用户批准和生产准入仍缺。个人资料只作临时本机核验，不写入仓库、证据正文或记忆。证据：`docs/releases/evidence/2026-08-15-p10-004-relationship-core/README.md`。
2026-08-15 P4-007 测试机发布更新：当前 `fateradar-prod` 的 `current` 已切换到 `ui-preview-20260815-hecan-fix-fe650e02f303`，归档 SHA 为 `fe650e02f3035abac8a6e2b1167e2944e22bd6be54c3bc169e4a8ab571d68aff`；Web `/`、`/hecan`、`/canwen`、独立 Admin `127.0.0.1:3001/login`、API live/ready、OpenAPI `startHecanReading` 和五个服务均复核通过。仍是 `local + Fake` 测试机，P4-007 等待用户逐页浏览批准，不代表生产、真实支付/模型或公开上线。证据：`docs/releases/evidence/2026-08-14-p4-007-test-server-upload/README.md`。
2026-08-15 P4-007/P10-004 测试机发布更新：当前 `fateradar-prod` 的 `current` 已切换到 `ui-preview-20260815-relationship-021141`，归档 SHA 为 `fb91baed1bff2cd1df5629294eac3e69d5319968ca675eeba2ba5217c61a8cdb`；数据库已到 `0034_reading_relationship`，迁移前 dump 和 manifest SHA 已记录。Web `/bazi/hepan`、`/ziwei/hepan`、`/qizheng/hepan`、Admin `/login`、API live/ready、OpenAPI 三个合盘 operation 和五个服务均复核通过。仍是测试验收机，不代表生产、真实支付/模型或公开上线；P4-007 等待用户逐页浏览批准。证据：`docs/releases/evidence/2026-08-15-p10-004-relationship-core/README.md`。
2026-08-15 P4-007/P10-004 最新测试机发布：当前 `fateradar-prod` 的 `current` 已原子切换到 `ui-preview-20260815-0305`，归档 SHA 为 `be9b191f84dbc7f64555606cf2b206575bcbd426cbfe16996ded5735a87ad134`；数据库仍为 `0034_reading_relationship`，迁移前 dump SHA 为 `9305465f000b87d924c45a293893e4e11d969c3f369ffabe63eee47b3a2bfd84`。本地 Backend `823 passed/102 skipped`、Web `437`、Admin `121`、根合同 `185 passed/82 skipped`、两端 production build 通过；服务器三条合盘路由、Admin `/login`、API live/ready、临时公网预览和五个服务重启复验通过。测试机仍是 `local + Fake`，关系页只消费 Runtime-native `relationship_signals`，当前冻结 V51 尚无该事实；P4-007 仍等待用户逐页浏览批准，P10-004 完整算法仍未完成。证据：`docs/releases/evidence/2026-08-15-p10-004-relationship-core/README.md`、`docs/releases/evidence/2026-08-14-p4-007-test-server-upload/README.md`。
2026-08-15 P10-004 Runtime 原生关系核心补齐：新增 `v52-relationship` release profile 与 217-file manifest admission；合成双主体真实 one-shot Runtime 在 13/13 Provider 门禁后，八字/紫微/七政分别返回 `6/9/30` 条 native relationship signals，并成功投影为 `BaziRelationshipV1`、`ZiweiRelationshipV1`、`QizhengRelationshipV1`。信号只引用 calculated fact refs，后端不复制算法；`scripts/smoke_local_real_relationship_runtime.py` 还固定断言三术黄金 signal ID 集合。P10-004 仍为 `IN_PROGRESS`，因为深读/ReadingDocument、真实 Worker 轨迹、真实服务器 native Runtime、四视口用户批准和生产门禁仍缺。证据：`docs/releases/evidence/2026-08-15-p10-004-relationship-core/README.md`。
2026-08-15 P10-005/P10-010 三术共同事实范围补齐：V52 `xingming` Provider 新增 `dimension_fact_scope` extension output binding，发布清单 SHA 为 `bef3df256ce06a9796d5eaef999d1141873128fe75b06916922ddd7fe9ac5d50`，describe digest 为 `6118c5f525c87b9cbde95b4d51c945be18bfd18fff8e03306da9fa748b87d917`；真实 one-shot 13/13 admission、八字+紫微+七政 Brief 和 projector 回归通过，三术每个维度 `missing_art_ids=()`。同时修正投影器，不再把三个 Provider 的不同 scope 名称误判成分歧。P10-005/P10-010 仍缺权威实质互证/分歧规则、ReadingDocument/深读、Worker、黄金样例、导出分享、用户批准和生产门禁。证据：`docs/releases/evidence/2026-08-14-p10-010b-canwen-scope-synthesis/README.md`、`docs/releases/evidence/2026-08-15-p10-005a-hecan-structure/README.md`。
2026-08-15 P4-007/P10-004 测试服务器发布：当前 `fateradar-prod` 原子切换到 `ui-preview-20260815-relcore-b2f70cbd4bbd`，归档 SHA 为 `b2f70cbd4bbd1f72fc387fcb2b5371cee11cf05006c75c2af286cdc1465f0e25`；数据库仍为 `0034_reading_relationship`，本版 `alembic check` 无新迁移。Web/Admin build、后端 import、API live/ready、Nginx healthz、三条合盘路由、Admin `/login` 和五个服务复验通过。服务器继续使用 `local + Fake`，仅供虚构数据浏览；P4-007 等待用户逐页批准。证据：`docs/releases/evidence/2026-08-15-p10-004-relationship-core/README.md`。

2026-08-15 P4-007/P10-004 最新测试服务器发布：`fateradar-prod` 的 `current` 已原子切换到 `ui-preview-20260815-crossscope`，归档 SHA 为 `8d0dcf69e330eb291130d5dca2af6d093c7125172080cd04a54cffe8e81ea822`；本地工作树快照在服务器完成 Web/Admin build、standalone 资产准备、目录权限修复、后端 import、`alembic check`、API live/ready、Nginx healthz、三条合盘和三条合参路由、静态资源、Admin `/login` 及五个服务重启复验。服务器仍是 `local + Fake`，仅供虚构数据浏览，不代表 V52 native Runtime 或生产；P4-007 等待用户逐页浏览批准。证据：`docs/releases/evidence/2026-08-15-p10-004-relationship-core/README.md`。

P12 门禁顺序：备案/许可主要约束 P12-007 的中国大陆公开生产上线，不是开发、内网联调、测试服务器浏览、备份恢复演练、告警容量建设、Staff 安全回归或支付沙箱的前置条件。P12-003、P12-005、P12-008 可先做本地/测试演练；P12-004 可先做沙箱，但真实渠道验签、查单、退款和对账要等真实支付凭据与环境；P12-006 可先写草案并做法律复核准备；P12-009 可先做测试旅程，生产旅程要等真实渠道；P12-010 永远最后，在制品上传、外部门禁和用户批准后执行。

2026-08-14 P12-003 备份恢复补充：测试服务器迁移前 PostgreSQL dump 已成功恢复到临时数据库，核对 `0014_reading_delivery`、43 张 public 表和 8 条 Runtime Release 记录后清理；发现并修正 root-only 备份目录不能让 postgres 直接读取的手册缺口。对象存储、Runtime 状态盘、生产恢复和 RTO/RPO 仍未完成。

2026-08-14 P12-009 测试旅程补充：`ui-preview-20260814-e1262c6d3e36` 已切换到 `fateradar-prod`，Fake/虚构账号完成游客、OTP、资料、八字预览、今日、周运、六爻 `digital_coin` 和同盘追问，S1–S10 全部 PASS，敏感扫描 0，`delayed` 存量前后均为 18。此前六爻 `outcome` 的 `required_dimension_missing` 已修复并有回归测试；本证据仍只覆盖测试权益，不代表真实购买/退款/生产发布，因此 P12-009 维持 `IN_PROGRESS`。

2026-08-14 P12-009 最终 release 补充：`ui-preview-20260814-3eaf1511b84a` 已替换为当前测试服务器版本，PostgreSQL 已到 `0032_postgres_schema_alignment`，`alembic check` 通过；同一 Fake/虚构旅程复跑 S1–S10 全部 PASS，敏感扫描 0，`delayed` 存量前后均为 18。仍只覆盖测试权益，不代表真实购买/退款/生产发布，P12-009 维持 `IN_PROGRESS`。

2026-08-14 见相补充：正常 `/jianxiang` 已把照片本地选择、质量待接入、删除/重选、相机待接入、用户补充和另行入档边界写入正式输入合同；Web UI Lab 已登记清单要求的媒体生命周期状态，并有 360/768/1024/1440 浏览器回归。P2-009 仍为 `IN_PROGRESS`，因为真实相机/私有媒体/结构化观察/结果服务和 P4-007 用户批准尚未完成。

2026-08-14 政策补充：正常 `/privacy` 与 `/terms` 已共用可访问的版本元数据区，明确“开发预览 v0.1 / 未生效 / 真实主体与法律审阅完成后发布”，并提供 `/auth/login`、`/pricing` 入口；`/auth/login`、`/auth/register`、`/checkout`、订单状态也可直达两份政策。对应单测 11/11、政策页浏览器 4/4、认证/购买路由浏览器 8/8 通过。P2-002 仍为 `IN_PROGRESS`，因为真实运营主体、政策持久化/重新同意、购买链路与法律复核尚未完成。

2026-08-14 身份文案补充：`/support` 已改为与权威身份合同一致的“密码主登录；OTP 用于注册验证、快捷登录和找回密码；OTP 核验后设置密码并同意当版政策”，并删除“无需注册密码”的冲突说法。对应单测 9/9、四视口浏览器 4/4 通过；P2-001、P2-015、P6-001/P6-002 仍为 `IN_PROGRESS`，因为真实身份服务、ConsentRecord 与重新同意尚未完成。
2026-08-14 身份纵切片补充：新增原子 `POST /api/v1/auth/register`（OTP→密码哈希→privacy/terms 当前 preview 版本 ConsentRecord→新设备会话）、`POST /api/v1/auth/password/recover`（仅已有身份、OTP 找回、重设密码并撤销旧设备会话），并将正式 `/auth/login`、`/auth/register`、`/auth/recover`、`/auth/set-password`、`/auth/consent` 接入真实 API；UI Lab 继续保留只读 fixture。Backend 密码/认证回归 29/29、OpenAPI/schema 合同 25/25、身份定向 Ruff/mypy 通过；Web 认证表单与旧 UI Lab 回归 39/39、typecheck/lint、production build 29/29 通过；standalone 五个认证页面 HTTP 200 且无旧 unavailable 占位文案。P6-001/P6-002 仍保持 `IN_PROGRESS`，因为真实身份供应商、正式运营政策、用户逐页批准和外部环境准入尚未完成。

2026-08-14 账户身份整合补充：`/account` 页头、未登录 OTP 入口和设备会话状态已统一为“密码主登录 + OTP 快捷登录”；页面明确 OTP 的注册验证/快捷登录/找回用途，以及 OTP 核验后设置密码并同意当版政策，移除“首次验证自动注册/已有邮箱直接登录”旧流程。账户契约单测 7/7，Web 全量 46 files / 367 tests，生产构建通过；账户浏览器合同四视口 4/4 通过，本地 backend 未启动时验证 unavailable 诚实降级。P2-015、P2-016、P6-001/P6-002 仍为 `IN_PROGRESS`，因为真实身份服务、ConsentRecord 与重新同意尚未完成。

2026-08-14 公共页补充：`/about` 已移除“页面已预制”内部施工文案，只保留品牌、运营主体和团队资料尚未冻结的真实边界；公共页契约单测 10/10、Web 全量 46 files / 368 tests、production build 通过，四视口全路由矩阵 4/4 通过。P2-001 仍为 `IN_PROGRESS`，因为公共内容的正式主体资料、完整运营内容和 P4-007 用户批准尚未完成。

2026-08-14 验收元数据补充：UI Lab 的 `/share/[shareId]` 参数已与正式页面一致，并补登记已存在的 `/account/data-rights`；冻结路由模式由 54 条修正为 55 条，UI Lab 路由契约单测 10/10 通过。P2-016 与 P4 仍未完成真实数据权利动作和用户逐页批准。

2026-08-14 开发态回归补充：Next Web/Admin 配置已允许 `127.0.0.1` 与 `localhost` 加载开发 client 资源；Web `UI_LAB_E2E=1` 在 `127.0.0.1:3000`、Admin `ADMIN_UI_LAB_E2E=1` 在 `127.0.0.1:3001` 的开发态 UI Lab 各通过 1/1，production UI Lab 仍保持 404。当前 `make check` 为 Backend 607 passed/90 skipped、Web 46 files/369 tests、Admin 10 files/58 tests，lint、typecheck、两端 production build 全通过；Web production Playwright 80 passed/4 development-only skipped，Admin 48 passed/4 development-only skipped。该修复只解决开发验收 hydration，不改变 P4-007 用户批准、P2/P3 真实服务接通或 P12 外部准入状态。

2026-08-14 四视口逐路证据补充：Web/Admin route matrix 增加显式 `ROUTE_EVIDENCE_DIR` 模式；在 standalone 生产构建上逐路访问并保存当前视口 JPEG 与 JSON manifest。Web 66 路由×4 视口共 264 条、Admin 40 路由×4 视口共 160 条，均 HTTP 200、无关键浏览器错误、无横向溢出，截图文件完整，证据对应 HEAD `f488fa4d6eaa989b708b14d87b747ee931468829`。未设置环境变量时不写证据文件。该补充强化 P4-001~P4-005 的本地自动化证据，但 P4-006 仍因缺授权来源截图保持 `NOT_STARTED`，P4-007 仍待用户逐页批准。
2026-08-14 工作台布局断点补充：新增 standalone Playwright 合同，在 768px、1024px、1440px 实际浏览器视口完成八字输入→确认→工作台，断言 768px 为单列、1024px/1440px 为双栏且三档均无横向溢出，结果 `1 passed`。该证据补强 P4-002~P4-004 的布局断言，不替代 P4-006 同视口视觉对照、P4-005 原生缩放/真实读屏或 P4-007 用户批准。

2026-08-14 工具输入预制补充：六个 `/tools/[tool]` 详情页已按各自输入边界显示可访问的只读字段、禁用提交和明确未接入说明；不会收集、保存或生成假结果。Web secondary surface 单测 15/15、六工具四视口开发态与 standalone 生产态浏览器合同均 4/4，Web production build 通过。P2-013 仍为 `IN_PROGRESS`，因为每项工具的正式输入/Provider/ViewModel/黄金样例和 P4-007 用户批准尚未完成。
2026-08-14 无障碍回归补充：Web `e2e/accessibility.spec.ts` 四视口 20/20、Admin 同文件四视口 20/20 通过，覆盖键盘导航与焦点恢复、跳过链接、主 landmark、表单错误聚焦、reduced motion、200%/400% 等价视口无横向溢出。运行时后端 API 未启动产生的代理连接拒绝仍按既有 unavailable 合同降级，不计为浏览器错误；该结果不替代 P4-006 来源截图比对、P4-007 用户批准或 P12 外部准入。
2026-08-14 知识库索引补充：正常 `/library` 空态已预制可访问的搜索框、主题筛选和禁用筛选按钮；没有已发布内容时控件不提交、不请求数据，并明确“发布内容后可用”。新增 secondary surface 单测 16/16、Web 全量 46 files / 376 tests、Web standalone 四视口路由矩阵 4/4、production build 与全仓库 `make check` 通过。P2-014 仍为 `IN_PROGRESS`，因为真实 CMS 索引/文章投影、搜索筛选行为、来源展示和 P4-007 用户批准尚未完成。
2026-08-14 当前工作树 production 浏览器回归：Web `npm run e2e:smoke` 为 `84 passed / 4 skipped`，Admin 为 `48 passed / 4 skipped`；覆盖四档视口、产品旅程、全路由矩阵、键盘/焦点、私有响应头、工具只读提交边界和 production UI Lab 负向。4 个 skip 都是明确要求开发环境的 UI Lab 用例；Admin 运行时未启动 Backend 8000 的代理拒绝仍按 unavailable 合同降级，不计为浏览器错误。该结果强化 P4-001～P4-005 的当前工作树证据，但不改变 P4-006/P4-007 或 P12 外部门禁状态。
2026-08-14 P12-008 本地安全回归：Web 私有 metadata/Service Worker/robots 合同 4 files / 30 tests 通过；Backend Admin Auth、CSRF、敏感 payload 与账户响应头 15/15 通过。没有发现私有响应可缓存/可索引、Service Worker 缓存个人/API 路径、缺 CSRF 写入或敏感字段泄露回归。P12-008 仍为 `IN_PROGRESS`，因为真实媒体授权、完整 Staff/RBAC/审计闭环和生产秘密治理尚未完成。
2026-08-14 当前工作树 Admin unavailable 边界补充：`adminFetch` 对 5xx 与网络拒绝统一返回“运营平台暂时不可用；当前页面保留只读结构”，不渲染代理层状态码或上游错误标题；新增 API 回归 2/2、Admin 全量 11 files / 60 tests、standalone build 和四视口逐路矩阵 4/4 通过。P12-008 的本地错误边界证据增强，但真实 Staff/RBAC/审计、媒体授权和生产秘密治理仍未完成；P4-006/P4-007 仍不改变。
2026-08-14 Web API 分层补充：`web/src/lib/api/client.ts` 收拢 fetch/CSRF/错误/幂等基础设施，`contracts.ts` 收拢业务 DTO，`account.ts` 与 `readings.ts` 分别承载业务调用，`web/src/lib/api.ts` 保留原公共出口；新增基础 transport 边界测试 2/2，Web 全量 47 files / 378 tests、typecheck、lint、production build 全通过。P5-004 已 `VERIFIED`；未新增后端接口或改变现有 API 合同。
2026-08-14 Admin 部署合同补充：新增 `infra/docker/admin.Dockerfile`、Compose `admin` 服务（回环 3001）、`fateradar-test-admin.service` 和测试服务器构建/启动/回滚文档；发现并移除干净 release 中不存在的 `admin/public` unconditional COPY；部署合同测试 3/3、基础设施进程边界合同 4/4，随后全局 `make check` 为 Backend 607 passed/90 skipped、Web 48 files / 381 tests、Admin 11 files / 60 tests，lint、typecheck、两端 production build 全通过；standalone build 与 nested `server.js` `/login` HTTP 200 检查也通过。P3-012 的 Admin 本地门禁与部署产物已补齐，但 Docker 构建和测试服务器真实部署尚未执行，故仍保持 `IN_PROGRESS`；没有新增公网 Admin 入口。
2026-08-14 测试服务器只读核对：现有 API、Worker、Web、Nginx 单元均为 enabled/active，当前 release 为 `ui-preview-20260814-011642`；`fateradar-test-admin.service` 不存在，Admin standalone `server.js` 不存在，回环 `127.0.0.1:3001/login` 无监听。该核对未执行安装、重启、切换 release 或读取秘密，确认 P3-012 的远端部署证据仍缺失；公共 Web 入口保持未接 Admin。
2026-08-14 干净 release 输入审计：本机未安装 Docker CLI，未执行镜像构建；当前工作树的 `ui/` 与 `infra/docker/admin.Dockerfile` 尚未进入 `HEAD`，因此不能把本地 Admin build 结果宣称为干净 Git archive 可构建结果。工作树合同测试仍为部署 3/3、基础设施 4/4，standalone 输出布局已核对；P3-012 继续等待提交后的 Docker 构建和测试服务器真实部署。
2026-08-14 P12-001 native-full 复核：本机为原生 arm64、CPython 3.14.6，`mingli-master` 仍有 runtime lock、研究资料和 217-file release manifest；但旧 `prepared-inputs.json` 绑定的 `/tmp/mingli-native-full.CmHIoq` 已不存在，`scripts/run_test_suite.py` 也不在仓库 Git 历史、当前 skill release closure 或本机归档中。独立 `verify_local_full.py` 对 2026-08-09 目录复验失败，原因是历史 release manifest 绑定已与当前 manifest 不一致。没有用普通业务测试或自写 runner 替代签名 gate，因此 P12-001 仍为 `IN_PROGRESS`，需要恢复原 runner、匹配的 release manifest 与完整 PreparedInputs 后才能重跑 1584/0。

2026-08-14 P6-007 幂等约束补充：新增 `0015_idem_owner_indexes` 迁移，移除 nullable owner 三列复合唯一约束，改为 user/guest 两个 partial unique index；SQLAlchemy 模型同步，SQLite migration/invariant 回归 29/29，user/guest 重复插入均拒绝。新增两个真实 PostgreSQL 独立事务并发用例，但本机未设置 `MINGLI_TEST_POSTGRES_URL`，因此按既有外部门禁规则为 skipped，P6-007 保持 `IN_PROGRESS`，不把本地 SQLite 结果替代 PostgreSQL 验收。最终 `make check`：Backend 611 passed/92 skipped、Ruff、mypy 101 files、Web 53 files/387 tests、Admin 11 files/60 tests，lint/typecheck/两端 production build 全通过；认证六路 standalone HTTP 200 且无旧占位文案。

2026-08-14 P6-007 PostgreSQL 复验：本机测试数据库已可用，设置 `MINGLI_TEST_POSTGRES_URL` 后完整 `backend/tests/test_reading_worker.py` 为 `17 passed`。其中 worker claim 竞争和 user/guest 幂等键并发插入均通过，随机 schema 在 fixture 结束后删除。P6-007 已具备清单要求的真实 PostgreSQL 并发证据，状态更新为 `VERIFIED`；生产数据库迁移、备份恢复和 P12 环境准入仍不由该证据覆盖。证据：`docs/releases/evidence/2026-08-14-p6-007-postgres/README.md`。

2026-08-14 政策与档案纵切片补充：后端新增单一 `CURRENT_POLICY_VERSION`/允许 policy key 校验；过期注册或重新同意会在消费 OTP/写入 ConsentRecord 前拒绝。新增 `0016_profile_version_auth`，同一 `SubjectProfile` 可追加不可变版本；他人授权、未成年人监护确认、版本差异确认写入独立不可变事实表，版本历史只返回安全元数据；越权/缺确认/敏感 payload 泄露回归通过。新增 profiles/migration/OpenAPI 定向 21/21，最终 `make check` 为 Backend 617 passed/92 skipped、mypy 102 files、Web 53 files/387 tests、Admin 11 files/60 tests，lint/typecheck/两端 production build 全通过。P6-002、P6-004、P6-005 仍为 `IN_PROGRESS`，因为正式政策/法律、完整照片授权与用户逐页验收，以及真实 PostgreSQL/生产准入尚未完成。

2026-08-14 P7-007 通知纵切片补充：新增 `notification_preferences` 与 `0017_notification_preferences`，默认只开站内、关闭邮件/短信；Outbox 按用户渠道偏好闸门控制，关闭渠道不入队，打开后携带明确 channel 并保留 dedupe；新增账户 GET/PUT 偏好 API、CSRF/私有响应头、真实设置页和账户导出字段。服务、API、迁移、数据权利和前端表单回归通过；最终 `make check` 为 Backend 619 passed/92 skipped、mypy 103 files、Web 54 files/388 tests、Admin 11 files/60 tests，lint/typecheck/两端 production build 全通过。P7-007 仍为 `IN_PROGRESS`，因为真实邮件/SMS 供应商、投递 worker、退信/重试、通知运营后台和外部生产准入尚未完成。
2026-08-14 P7-005 Admin 权益调整补充：新增 `/api/v1/admin/entitlements/events` 查询与写入接口；`grant`、`compensate`、按状态撤回（`RELEASE`/`EXPIRE`/`REVERSE`）均只追加正式账本事件，相同来源幂等重放，写操作要求 Admin CSRF 与 finance/ops/superadmin，且每个新事件写入 `AdminAuditEvent`。定向测试与 OpenAPI 对齐 `7 passed`，随后全量 `make check` 为 Backend 622 passed/92 skipped、Ruff、mypy 103 files、Web 54 files/388 tests、Admin 11 files/60 tests，lint/typecheck/两端 production build 全通过。P7-005 标记 `VERIFIED`；真实支付、生产数据库和 Admin 页面完整接线仍由其他清单项覆盖。
2026-08-14 P7-007 通知 Outbox 投递补充：新增 `0018_notification_delivery_state` 与 `NotificationWorker`；Outbox 现在记录尝试次数、processing lease 和 fencing token，成功进入 `sent`，失败按最大尝试次数重试，超限进入 `failed`，旧 claim 不能覆盖新 claim。新增 worker/迁移/commerce 回归，定向 worker 测试 `4 passed`、迁移/模型/账本/通知回归 `12 passed`，Ruff/mypy 通过。P7-007 继续保持 `IN_PROGRESS`，因为真实邮件/SMS 供应商、退信处理、运营后台和生产 worker/SLO 尚未接入。
2026-08-14 P7-007 Admin 接线补充：新增 `/api/v1/admin/notifications` 状态列表和 `/{id}/retry` 重排接口；仅 `superadmin` 可读写，写入要求 Admin CSRF、操作原因和 `notification.retry` 审计，响应不含通知 payload。`/notifications` 页面已接真实 Outbox 状态、错误摘要和失败重试原因表单；Admin 定向 UI `2 passed`、API/OpenAPI `7 passed`、lint/typecheck 通过。P7-007、P3-010、P9-005 继续 `IN_PROGRESS`，因为真实供应商、退信处理、worker 部署、Admin 运营策略和生产 SLO/告警仍未完成。

2026-08-14 P7-006 支付对账补充：新增 `0019_payment_reconciliation`、已验签通知收据、对账批次/明细与规范化渠道快照；重复事件不重复创建 Payment/GRANT，支付/退款按自然号对账并记录本地独有、渠道独有、金额/币种/状态差异、退款无支付和聚合超额退款。定向支付/迁移/模型/商业回归 `14 passed`、Ruff、mypy 通过；真实渠道验签/查单、日对账下载、定时 Worker、Admin 差异处理和生产凭据仍缺，P7-006 保持 `IN_PROGRESS`，P12-004 不变。
2026-08-14 P7-006 Admin 接线补充：新增 `/api/v1/admin/reconciliation` 列表、`/runs` 执行、`/runs/{id}` 差异详情；`finance`/`ops`/`superadmin` 读取，写入要求 Admin CSRF、操作原因并追加 `payment.reconciliation.run` 审计。`/reconciliation` 页面已接真实批次、差异抽屉和结构化支付/退款快照表单，明确仅接受已验签归一化快照；Admin 定向 2/2、API/OpenAPI 定向 7 passed、lint/typecheck 通过。P7-006、P3-008、P9-005 继续 `IN_PROGRESS`，因为真实渠道验签/查单/账单下载、定时 Worker、补单/双人处理、生产凭据和 P12-004 仍未完成。
2026-08-14 P7-004 付费交付补充：新增 `0020_fulfillment` 与 `FulfillmentRecord`；已确认 Payment 才能为订单权益创建一次 Fulfillment/RESERVE，Reading Job 绑定与重放幂等，只有真实 AcceptedCopy + ReadingDocumentV1 才 CONSUME，终态失败只 RELEASE 且不重复改写原因。随后新增 `0021_fulfillment_scope`，将幂等键修正为订单作用域，避免独立订单互相冲突。Fulfillment 定向行为、模型、迁移回归 `9 passed`，Ruff/mypy 与 fresh upgrade/autogenerate check 通过；真实支付/Worker/API/生产接线仍缺，P7-004 保持 `IN_PROGRESS`。
2026-08-14 P11-005 追问合同补充：`ReadingRoot` 新增 ProductVersion 快照、次数、期限和窗口起点；正式绑定 Fulfillment 时冻结商品语义，Follow-up 仅允许当前 ReadingRoot 最新 Accepted 版本，活动子版本禁止分叉，Accepted 追问按快照次数计数，窗口过期拒绝，免费预览无快照的既有测试行为保持不变。API/Reading 定向回归 `71 passed`；真实权益 CONSUME、Recast 结构化输入、PNG/PDF 和生产接线仍缺，P11-005 保持 `IN_PROGRESS`。
2026-08-14 P7-002 支付尝试边界补充：`confirm_payment` 现在要求确认渠道与 `PaymentAttempt` 一致；同一尝试只接受一个交易事实，同交易号重放返回原 Payment，不同交易号拒绝且不追加 GRANT；已到账订单拒绝迟到尝试；退款流水号不能错绑另一笔 Payment；新增 `0023_payment_attempt_unique` 约束并通过 fresh SQLite upgrade/autogenerate check。Commerce/对账定向回归 `10 passed`、迁移回归 `2 passed`、Ruff/mypy 通过；真实渠道验签、查单、生产到账和 P12-004 仍缺，P7-002 保持 `IN_PROGRESS`。
2026-08-14 P4-001～P4-005 状态校准：当前工作树的 Web 66 路由×4 视口、Admin 40 路由×4 视口、产品旅程、键盘/焦点、200/400% 等价视口、reduced-motion、无横溢和 unavailable 负向合同均已有自动化证据，五项更新为 `BROWSER_VERIFIED`。这不代替 P4-006 授权参考截图并排审阅，也不代替 P4-007 用户逐页批准；P2/P3/P4 总阶段仍未完成。

2026-08-14 P7-001 Catalog 补充：新增 `CatalogService`，覆盖 ProductFamily、草稿 ProductVersion、渠道 ProductOffer 的创建，以及启用 Offer 才能发布、版本退役后保留快照并拒绝新增 Offer、Offer 独立启停等本地生命周期边界；Catalog/Commerce 定向回归 `17 passed`，迁移回归 `2 passed`，Ruff/mypy 通过，临时 SQLite upgrade 到 `0023_payment_attempt_unique` 后 `alembic check` 无新操作。P7-001 仍为 `IN_PROGRESS`，因为 Admin/API、权限审计、真实发布审批、支付映射和生产接线尚未完成。

2026-08-14 P7-001 Admin 接线补充：新增 `/api/v1/admin/catalog` 及商品族、版本、Offer 创建/发布/退役/启停接口；`ops`/`superadmin`、Admin CSRF 和必填操作原因由服务端校验，每个写操作追加 `AdminAuditEvent`。新增 Admin Catalog 定向 API/OpenAPI 回归 `7 passed`；Admin 商品列表与版本详情读取真实 Catalog 响应，9 个 UI 定向测试、lint、typecheck 通过，真实页面写表单仍保持只读。P7-001、P3-004、P9-005 继续保持 `IN_PROGRESS`，因为完整报价操作 UI、真实审批、支付渠道映射和生产接线尚未完成。
2026-08-14 P7-001 Admin 命令面补充：Admin `/products` 与 `/products/[id]/versions` 在真实 `ops`/`superadmin` 会话下新增商品族、版本、报价创建，以及版本发布/退役、报价启停命令；统一要求操作原因，复用服务端 CSRF/RBAC/状态校验和 `AdminAuditEvent`，成功后重新读取 Catalog。Admin 全量 `11 files / 62 tests`、lint、typecheck、production build 通过；此前 7 项 Admin Catalog API/OpenAPI、9 项商品视图/命令 UI 定向回归继续通过。P7-001、P3-004、P9-005 继续保持 `IN_PROGRESS`，因为真实发布审批、支付渠道映射、生产接线和 P4/P12 外部门禁尚未完成。
2026-08-14 P12-008/P9-004 Staff 管理补充：新增 Admin `/api/v1/admin/sessions` 脱敏列表与强退、`/staff` 员工列表、状态停用/恢复、角色调整和 `password-reset`；写入统一要求 superadmin、CSRF、非空原因，停用/角色/密码变更撤销目标会话并写审计，密码不进入响应或事件。Staff/Session/OpenAPI 回归 `16 passed`，Admin 相关页面 `11 passed`，正式 mypy `112 source files`、Ruff、Admin eslint/typecheck 通过。P3-010、P9-004、P12-008 仍为 `IN_PROGRESS`，因为员工创建/邀请、系统设置/健康面、真实媒体授权、生产秘密治理和外部准入尚未完成。
2026-08-14 Admin 平台切片补充：新增 `/api/v1/admin/settings`、`/health` readiness 面、订单/支付/退款只读聚合与 `/data-rights` 待处理关闭队列；隐私关闭成功路径补写 `privacy.closure.execute` 审计。新增设置、健康、Commerce、数据权利 Admin 页面和 API 回归；全局 Backend `660 passed/92 skipped`、mypy `114 source files`、Admin `20 files/81 tests`、lint/typecheck/build 全通过。P3-003、P3-008、P3-010、P9-005、P12-008 继续 `IN_PROGRESS`，因为完整用户/Subject 聚合、真实支付/对账/供应商、员工运营、生产秘密/媒体授权和外部准入仍缺。
2026-08-14 P3-003 身份资料切片补充：新增 `/api/v1/admin/users`、`/users/{id}`、`/subjects`、`/subjects/{id}`，支持角色读取脱敏 User/Identity/Device/Consent/Subject/ProfileVersion 授权元数据；不返回密码哈希、token 哈希或加密资料正文。新增 API/OpenAPI `7 passed`、Admin 身份与路由 `10 passed`，全局 Backend `662 passed/92 skipped`、mypy `115 source files`、Admin `21 files/84 tests`、lint/typecheck/build 全通过。P3-003、P9-005、P12-008 继续 `IN_PROGRESS`，因为客服案件模型、用户/Subject 写服务、员工邀请、生产秘密/媒体授权和外部准入仍缺。
2026-08-14 P7-003/P9-005 权益账本 Admin 接线补充：新增 `/api/v1/admin/entitlements/events/recent` 最近事件聚合；`/entitlements` 展示正式 GRANT/RESERVE/CONSUME/RELEASE/REVERSE/EXPIRE 事实，finance/ops/superadmin 可复用既有带 CSRF、原因、来源编号和幂等约束的追加 API，support 无调整命令。新增 API/OpenAPI `10 passed`、Admin 权益与路由 `10 passed`，全局 Backend `664 passed/92 skipped`、mypy `115 source files`、Admin `22 files/86 tests`、lint/typecheck/build 全通过。P7-003 仍受生产账本接管/部署门禁约束，P9-005 仍因邀请、客服案件、算法相关页和真实生产接线未完成。
2026-08-14 P3-009/P9-005 邀请活动 Admin 只读补充：新增 `/api/v1/admin/referrals` 与 `/{campaign_id}`，展示 CampaignVersion、邀请码、临时归因、RewardReservation 的真实计数和详情；仅 `ops`/`superadmin` 可读取，响应不含 `visitor_key_hash`，没有虚构申诉或活动写命令。`/referrals` 与 `/referrals/[id]` 已接真实 API；API/OpenAPI 与 Admin 定向回归通过，随后全局 Backend `666 passed/92 skipped`、mypy `116 source files`、Admin `23 files/88 tests`、lint/typecheck/build 全通过。P3-009/P9-005 仍为 `IN_PROGRESS`，因为 Appeal/CMS/算法相关页和生产邀请/权益接线仍缺。
2026-08-14 P9-004 员工账号创建补充：`POST /api/v1/admin/staff` 新增本地员工账号创建；仅 `superadmin` + Admin CSRF 可执行，要求邮箱、显示名称、角色、初始密码和审计原因，密码只存哈希，响应/审计不回显密码，大小写不敏感重复邮箱返回 409。`/staff` 增加创建表单并成功刷新目录、清空密码；不伪造邮件邀请投递。Staff API/UI/OpenAPI 定向回归通过，随后全局 Backend `667 passed/92 skipped`、Ruff、mypy `116 source files`、Admin `23 files/89 tests`、lint/typecheck/build 全通过。P9-004、P3-010、P12-008 仍为 `IN_PROGRESS`，因为邮件邀请、完整员工运营、生产秘密治理、媒体授权和外部准入仍缺。
2026-08-14 P3-005/P9-002 CMS 索引补充：新增 `GET /api/v1/admin/cms`，按 locale、prefix、limit 返回每个 content key 的最新修订元数据，不批量返回正文；六个 `/cms/**` Admin 路由已接入真实索引，support 角色保持无 CMS editor 读取权限。内容/API/OpenAPI 定向回归 `10 passed`，Admin CMS 与路由回归 `10 passed`，随后全局 Backend `668 passed/92 skipped`、Ruff、mypy `116 source files`、Admin `24 files/91 tests`、lint/typecheck/build 全通过。P3-005、P9-002、P9-005 仍为 `IN_PROGRESS`，因为正文编辑/内容投影、SEO/公告完整接线、算法相关页和真实生产运营仍缺。
2026-08-14 P3-006/P9-005 解读任务 Admin 只读补充：新增 `GET /api/v1/admin/reading-jobs`，从 `ReadingJobRecord` 与 `ReadingVersion` 返回能力、版本、盘面态、任务态、语言和调度元数据；support 可读，finance 被拒绝，响应不含出生输入、horizon/object、output contract、lease 或模型 payload。新增 API/OpenAPI `6 passed`、Admin 任务页与路由 `10 passed`，随后全局 Backend `669 passed/92 skipped`、Ruff、mypy `117 source files`、Admin `25 files/93 tests`、lint/typecheck/build 全通过。P3-006、P9-005 仍为 `IN_PROGRESS`，因为盘面/报告/核对/见相完整聚合、重试策略和生产 Worker/Runtime 接线仍缺。
2026-08-14 P3-006/P11-004 核对 Admin 只读补充：新增 `GET /api/v1/admin/verifications`，合并 `ReadingVerification`、`ClaimVerificationEvent` 与 `ReportFeedback`，按来源返回结果、Claim、操作人和时间；响应不含 note，support/ops/superadmin 可读，finance 被拒绝。新增 API/OpenAPI `6 passed`、Admin 核对页与路由 `10 passed`，随后全局 Backend `670 passed/92 skipped`、Ruff、mypy `118 source files`、Admin `26 files/95 tests`、lint/typecheck/build 全通过。P3-006/P9-005 仍为 `IN_PROGRESS`，因为盘面/报告详情、见相观察、客服/申诉和生产运营接线仍缺。
2026-08-14 P3-006/P9-005 盘面详情与 Runtime Admin 只读补充：新增 `GET /api/v1/admin/readings`、`GET /api/v1/admin/readings/{reading_version_id}` 和 `GET /api/v1/admin/runtime-releases`；`/charts`、`/readings` 展示 ReadingVersion 的能力/版本/状态/维度数，`/readings/[id]` 展示真实任务数、核对事件数和文档存在性，`/runtime` 展示真实 RuntimeRelease 的名称/版本/source commit/协议/production-ready 标记。读取接口均按角色限制，响应不含出生输入、horizon/object、owner、报告正文、manifest/image digest 或 Provider 凭据。新增 API/OpenAPI `7 passed`、Admin 详情/运行时与路由定向回归通过，随后全局 Backend `673 passed/92 skipped`、Ruff、mypy `119 source files`、Admin `29 files/101 tests`、lint/typecheck/build 全通过。P3-006/P9-005 仍为 `IN_PROGRESS`，因为见相观察、客服/申诉、Provider/Worker 生产接线和外部准入仍缺。
2026-08-14 P3-005/P9-002 CMS 历史只读补充：CMS 六个索引页面的 content key 行现在可调用既有 `/api/v1/admin/cms/{content_key}/history`，展示真实修订态、责任人、时间和正文；support 仍被服务端拒绝，页面不提供未审计的编辑/发布命令。Admin CMS 定向回归 `3 passed`，随后 Admin 全量 `29 files/102 tests`、lint、typecheck、production build 通过。P3-005/P9-002 仍为 `IN_PROGRESS`，因为正文编辑、发布命令审计、内容投影和 SEO/公告完整接线仍缺。
2026-08-14 P3-006/P9-005 盘面详情与 Runtime Admin 只读补充：新增 `GET /api/v1/admin/readings`、`GET /api/v1/admin/readings/{reading_version_id}` 和 `GET /api/v1/admin/runtime-releases`；`/charts`、`/readings` 展示 ReadingVersion 的能力/版本/状态/维度数，`/readings/[id]` 展示真实任务数、核对事件数和文档存在性，`/runtime` 展示真实 RuntimeRelease 的名称/版本/source commit/协议/production-ready 标记。读取接口均按角色限制，响应不含出生输入、horizon/object、owner、报告正文、manifest/image digest 或 Provider 凭据。新增 API/OpenAPI `7 passed`、Admin 详情/运行时与路由定向回归通过，随后全局 Backend `673 passed/92 skipped`、Ruff、mypy `119 source files`、Admin `29 files/102 tests`、lint/typecheck/build 全通过。P3-006/P9-005 仍为 `IN_PROGRESS`，因为见相观察、客服/申诉、Provider/Worker 生产接线和外部准入仍缺。

2026-08-14 P3-007/P9-005 Model/Guard Admin 只读补充：新增 `GET /api/v1/admin/model-profiles` 与 `/model-profiles`，从真实 `GenerationAttempt.model_receipt` 展示 profile、provider、模型版本、调用结果、Guard 错误数、延迟和安全版本元数据；仅 `ops`/`superadmin` 可读，响应与页面排除 request fingerprint、profile snapshot digest、token/价格明细、出生输入和原始 provider payload。API/OpenAPI 定向 `7 passed`、Admin Model/Guard 与路由定向 `10 passed`，随后全局 Backend `675 passed/92 skipped`、Ruff、mypy `120 source files`、Admin `30 files/104 tests`、lint、typecheck、production build 全通过。P3-007/P9-005 仍为 `IN_PROGRESS`，因为真实 Provider/Worker 生产配置、Guard 红队、完整运营策略和外部准入仍缺。
2026-08-14 P3-007/P9-005 能力策略 Admin 只读补充：新增 `GET /api/v1/admin/capabilities` 与 `/capabilities`，从 V5.1 的 13 条版本化策略展示能力标签、产品动作和发布态；仅 `ops`/`superadmin` 可读，P0 的八字/今日运势/六爻为 `PUBLIC`，其余 Provider 模块为 `INTERNAL_TEST`，响应不含凭据并明确 `runtime_health=unverified`、`production_ready=false`。API/OpenAPI 定向 `7 passed`、Admin 能力策略与路由定向 `10 passed`，Admin 四视口 route matrix `16 passed`；随后全量 Backend `677 passed/92 skipped`、Ruff、mypy `121 source files`、Web `54 files/388 tests`、Admin `31 files/106 tests`、lint/typecheck/build 全通过。P3-007/P9-005 仍为 `IN_PROGRESS`，因为没有能力发布写命令，也没有完成真实 Provider/Worker、Runtime 健康、Guard 红队、生产准入和外部验收。
2026-08-14 P3-003/P9-005 客服案件申请补充：新增 `support_cases` 与 0024 迁移、`GET/POST /api/v1/admin/support-cases` 及 `/support-cases`；finance/ops 可读，support/superadmin 可提交带对象、类型、摘要和操作原因的申请，创建只写 `support_case.created` 审计，不直接执行补偿/退款/报告修改。API/OpenAPI 定向 `8 passed`、Admin 页面与路由定向 `17 passed`，临时 SQLite 从空库升级到 Alembic head 且 `alembic check` 无新操作，Admin 四视口 route matrix `16 passed`；随后全量 Backend `680 passed/92 skipped`、Ruff、mypy `124 source files`、Web `54 files/388 tests`、Admin `32 files/108 tests`、lint/typecheck/build 全通过。P3-003/P9-005 仍为 `IN_PROGRESS`，因为案件处理/补偿闭环、客服与申诉运营、真实生产接线和外部验收仍缺。
2026-08-14 P3-009/P8-006/P9-005 申诉纠错纵切片补充：新增 `referral_appeals`、`referral_risk_signals`、`referral_appeal_approvals` 与 0025 迁移，提供 `GET/POST /api/v1/admin/appeals`、风险信号记录和决定接口；support/superadmin 可提交，ops/superadmin 可记录不改变奖励状态的 IP/设备/地址重合类型信号，finance/superadmin 的 `correction` 必须由两位不同员工审批，第二位完成后只通过正式追加式权益账本撤销事件并写 `referral.appeal.*` 审计。重复申诉、同人二次审批、越权和无已提交奖励均拒绝；不保存原始识别值、不删除报告。申诉 API/OpenAPI 定向 `7 passed`、Admin UI/路由 `17 passed`，临时 SQLite 从空库升级到 `0025_referral_appeals` 且 `alembic check` 无新操作，Admin 四视口 route matrix `16 passed`；随后全量 Backend `682 passed/92 skipped`、Ruff、mypy `125 source files`、Web `54 files/388 tests`、Admin `33 files/110 tests`、lint/typecheck/build 全通过。P8-006/P3-009/P9-005 仍为 `IN_PROGRESS`，因为确定性拒绝接入、未来参与限制、完整活动写服务、真实生产接线与外部验收仍缺。

2026-08-14 P3-005/P9-002 CMS 审计命令补充：`POST /api/v1/admin/cms` 创建草稿与 `PATCH /api/v1/admin/cms/{revision_id}` 编辑草稿，以及预览、定时、发布、撤回、归档、恢复命令均要求非空操作原因；服务端只向 `AdminAuditEvent` 写入 allowlist 的 content key、locale、revision、state、target id、操作者和原因，不写入正文。Admin CMS 历史面板已按修订状态展示可用命令、原因表单、成功/错误/不可用状态；命令完成后历史刷新失败会明确提示，不冒充干净成功。CMS/API/OpenAPI 定向 `12 passed`，Admin CMS/路由定向 `20 passed`，全局 `make check` 为 Backend `684 passed/92 skipped`、Ruff、mypy `125 source files`、Web `54 files/388 tests`、Admin `33 files/112 tests`，lint/typecheck/两端 production build 全通过；Admin route matrix `16 passed`、accessibility `20 passed`。P3-005/P9-002 仍为 `IN_PROGRESS`，因为每日/工具/知识/帮助/公告/FAQ/SEO 全内容投影、生产发布接线、P4-006/P4-007 与外部准入尚未完成。

2026-08-14 P2-014/P3-005/P9-002 公共内容投影补充：新增只读 `GET /api/v1/content` 与 `GET /api/v1/content/{content_key}`，仅从已发布修订返回正文和公开元数据；更新草稿不会遮蔽上一版已发布内容，未发布内容返回 404，不泄露作者、状态或操作原因。`/library`、`/library/[slug]` 和 `/daily` 已消费真实投影，API 不可用或无内容时保持原有明确空态；文章加载后不再显示“不可查看”的矛盾标题。公共 API/OpenAPI 定向回归与 Web 公共内容回归通过，最终全局 `make check` 为 Backend `686 passed/92 skipped`、Ruff、mypy `126 source files`、Web `54 files/390 tests`、Admin `33 files/112 tests`，lint/typecheck/两端 production build 全通过；Web route/accessibility `64 passed`、Admin `36 passed`。P2-014/P3-005/P9-002 仍为 `IN_PROGRESS`，因为搜索/主题筛选、来源字段、每日/工具/帮助/公告/FAQ/SEO 的完整内容模型与生产发布接线，以及 P4-006/P4-007/P12 外部门禁尚未完成。

2026-08-14 P2-014/P3-005/P9-002 内容元数据与搜索筛选切片：新增 `0026_content_metadata`，为 CMS 修订增加标题、摘要、主题、来源标题和来源链接；公开 `GET /api/v1/content` 支持 `q` 与 `topic`，只在已发布投影上检索；Admin CMS 索引、历史和草稿编辑会携带这些字段，编辑仍要求操作原因并写入受限审计元数据；Web `/library`、文章和每日内容在有已发布结果后启用真实搜索/主题筛选、来源展示和空结果语义，初始无数据时继续保持明确禁用态。定向 Backend 内容/迁移 `17 passed`、OpenAPI `8 passed`、Web secondary surface `23 passed`、Admin CMS `6 passed`；随后完整 `make check` 为 Backend `687 passed/92 skipped`、Ruff、mypy `126 source files`、Web `54 files / 395 tests`、Admin `33 files / 113 tests`，两端 lint/typecheck/production build 全通过；当前工作树四视口证据为 Web `64 passed`、Admin route/accessibility `36 passed`，证据目录为 `web-content-metadata` 与 `admin-content-metadata-smoke`，均标记 `automated-only`。P2-014/P3-005/P9-002 仍为 `IN_PROGRESS`，因为每日/工具/帮助/公告/FAQ/SEO 的完整内容模型、生产发布和用户验收尚未完成；本轮额外的 Admin live-contract 用例因后端 8000 未启动而未计入绿灯。

2026-08-14 P3-005/P9-002 CMS 创建草稿补充：Admin CMS 对 `ops`/`superadmin` 开放带命名空间校验的创建草稿表单，支持标题、摘要、主题、来源标题、来源链接、正文和必填操作原因；创建调用真实 `POST /api/v1/admin/cms`，成功后重新读取当前索引，列表刷新失败会明确提示，不冒充成功；support 不显示写表单。Admin CMS 定向 `7 passed`、全量 `33 files / 114 tests`，lint/typecheck/production build 通过；当前工作树 Admin route/accessibility 四视口 `36 passed`，证据目录为 `admin-cms-create-smoke`，仍标记 `automated-only`。P3-005/P9-002 仍为 `IN_PROGRESS`，因为公告/FAQ/SEO 等完整内容分类、政策版本接线、生产发布与用户逐页验收仍未完成。
2026-08-14 P2-014/P3-005/P9-002 公共编辑页与 SEO 接线补充：新增 `PublicCmsProjection`，`/support` 读取 `faq` 帮助索引，`/privacy`/`/terms` 读取 `policy.privacy`/`policy.terms`，`/about`/`/methodology` 读取 `page.about`/`page.methodology`，首页读取 `notice` 公告索引；没有已发布内容或后端不可用时保留原静态边界文案并显示明确 empty/unavailable，不伪造 CMS 成功。服务端 `generateMetadata` 读取已发布 `seo.*` 的 title/summary，404、缺字段和网络失败回退静态 metadata，正文不进入 head。新增 CMS 投影/页面接线/SEO 定向 `14 passed`，Web 全量 `57 files / 405 tests`、lint/typecheck/production build 与全仓 `make check` 通过；当前工作树 Web 四视口 route/accessibility `64 passed`，证据目录为 `web-editorial-cms-smoke`，仍标记 `automated-only`。P2-014/P3-005/P9-002 仍为 `IN_PROGRESS`：完整公告/FAQ/SEO 运营分类、所有内容类型的生产发布与真实数据、P4-006/P4-007 和 P12 外部门禁尚未完成。
2026-08-14 P3-010/P9-005 Admin 总览聚合补充：`GET /api/v1/admin/overview` 不再返回占位零值，改从持久化 Refund、ReadingJob、今日失败 PaymentAttempt 和 PaymentReconciliationRun 差异事实聚合 KPI/工作队列；空库也明确返回 `is_stub=false`，旧 stub 负向 UI 边界仍保留。Backend Admin Auth/Overview/OpenAPI 定向 `12 passed`，Ruff/mypy 通过；Admin 总览组件 `2 passed`。计数不推断缺失行、不把 unavailable 适配器转成业务事实；P3-010/P9-005 仍为 `IN_PROGRESS`，因为完整员工运营、其他平台写服务、真实 Provider/Worker/支付生产接线、生产秘密与外部验收尚未完成。
2026-08-14 P3-005/P9-002 CMS 命名空间补充：服务端 `ContentService` 统一限制 `home.*`、`page.*`、`notice[.*]`、`seo.*`、`daily[.*]`、`tools.*`、`library.*`、`faq[.*]`、`policy.*`，页面面板也在调用前拒绝未登记 key；已有历史 `home.hero`、`daily`、`faq` 等 key 保持可用。新增未知命名空间 API/UI 负向回归；CMS 后端 `14 passed`、Admin CMS/route `16 passed`、Ruff/mypy/typecheck 通过。随后全仓 `make check` 为 Backend `689 passed/92 skipped`、Web `57 files / 405 tests`、Admin `33 files / 116 tests`，Ruff/mypy/lint/typecheck/两端 production build 全通过。P3-005/P9-002 仍为 `IN_PROGRESS`，因为真实内容分类运营、生产发布、政策版本和用户验收仍缺。

2026-08-14 P3-003/P9-005 客服案件分类补充：`/api/v1/admin/support-cases` 与 Admin 表单新增 `profile_correction`（资料纠正）、`algorithm_review`（算法复核）、`after_sales`（售后）和 `compensation`（补偿）四类运营队列，保留原有账户、交付、账务、解读、邀请和其他分类；新增后端持久化/权限/审计回归 `20 passed`、Admin UI `3 passed`、OpenAPI 对齐和 TypeScript 检查通过。案件仍只提交申请，不直接修改 ProfileVersion、报告、账本或退款；P3-003/P9-005 继续等待案件处理/补偿闭环、真实生产接线和外部验收。

2026-08-14 P3-003/P6-004 Admin 资料事实补充：`/api/v1/admin/subjects/{id}` 现在通过既有 EnvelopeCipher 解密并返回授权员工所需的出生时间、时区、地点、性别、时间口径、子时口径和坐标事实；响应不含密文、nonce、fingerprint、密钥材料或照片正文，解密/校验失败明确返回 unavailable。Admin Subject 详情同时展示版本授权和业务资料；后端身份/OpenAPI `7 passed`、Admin UI `3 passed`、Ruff/mypy/typecheck 通过。P3-003/P6-004 仍等待盘面/关系/数据权利完整聚合、生产秘密治理和用户验收。

2026-08-14 P3-002/P3-003/P6-001 身份目标加密补充：`LoginIdentity` 新增四个可为空的加密存储字段与 0027 迁移；OTP 验证、注册、密码登录成功和找回密码成功时按 `login-identity:<id>` 写入规范化邮箱/手机号，Admin 用户详情只输出授权解密的 `destination`，历史没有原文的身份返回 `null`，账户公共响应继续只返回掩码。认证/Admin/Email journey `24 passed`、OpenAPI 对齐 `13 passed`、迁移/配置 `13 passed`、Admin UI `3 passed`，Ruff/mypy/typecheck 通过；既有生产身份历史需在真实用户再次成功认证后补齐原文，不能从掩码反推。
2026-08-14 P3-003/P3-005/P3-006/P9-002/P9-005 Admin 结构合同收口：真实身份、商业、员工、报告和 CMS 页面在 unavailable 时保留无假记录的详情/列表骨架；用户列包含身份、会话、同意，支付列包含支付尝试、订单、渠道、到账事实，员工列包含员工、角色、会话，报告列包含任务根、版本、阶段、受测对象，CMS 列包含内容、版本、发布态。运行时、健康和设置面在依赖不可用时仍保留专用标题与明确状态。Admin 浏览器合同四视口 `48 passed / 4 skipped`；随后全仓 `make check` 为 Backend `693 passed/92 skipped`、mypy `126 source files`、Web `57 files/405 tests`、Admin `33 files/119 tests`，Ruff、lint、typecheck、两端 production build 全通过。P3/P9 仍为 `IN_PROGRESS`，因为真实生产接线、完整员工/客服/报告运营、P4 用户逐页批准与 P12 外部门禁尚未完成。
2026-08-14 P3-005/P9-002 CMS 页面范围修正：`/cms/pages` 不再用无筛选索引把 daily/tools/library/faq/policy 内容混进页面面板；Admin 现在分别读取并合并 `home.*`、`page.*`、`notice`/`notice.*`、`seo.*` 四个已登记命名空间，创建草稿和创建后的刷新复用同一范围，单前缀的每日/工具/知识/帮助/政策面板保持原行为。新增页面范围合同测试；Admin CMS `9 passed`、typecheck、lint 通过。P3-005/P9-002 继续 `IN_PROGRESS`，因为真实运营内容、政策版本、生产发布和外部验收仍未完成。
2026-08-14 P8-001/P8-002 邀请状态边界补充：ReferralService 现在拒绝无总奖励上限或倒置活动窗口的版本，状态只能按 draft→scheduled/active/ended、scheduled→active/paused/ended、active/paused→active/ended 推进，ended 不可重开；临时归因有效期取 30 天与活动结束时间的较早值。Referral service/policy 定向 `8 passed`。P8-001/P8-002 仍为 `IN_PROGRESS`，因为产品级奖励槽、支付占用、首笔触发、前台归因/进度、通知和生产邀请接线仍缺。

2026-08-14 P8-003 产品奖励槽与支付占用补充：新增 `0028_referral_reward_slots` 与 `ReferralRewardSlot`，Campaign 只能在草稿态配置已发布/active ProductVersion 的 `inviter_reward`/`invitee_reward` 槽；奖励预留必须带 ProductVersion，按活动总额、商品槽名额和每邀请人默认 10 个不同新用户计数，并可绑定 pending `PaymentAttempt` 校验订单归属/商品一致性。失败支付可按尝试释放预留，活动行锁串行化名额判断；旧历史预留的商品/支付字段保持 nullable，Admin 详情与 OpenAPI 只读返回槽、商品和支付占用事实，不把未确认支付显示为成功。Referral/Persistence/Admin/OpenAPI 定向 `19 passed`，fresh SQLite upgrade/head 与 `alembic check` 通过；全仓 `make check` 为 Backend `697 passed/92 skipped`、mypy `126 source files`、Web `57 files/405 tests`、Admin `33 files/120 tests`，两端 lint/typecheck/production build 全通过；Admin 浏览器 smoke `48 passed/4 skipped`。P8-003 仍为 `IN_PROGRESS`，因为真实 PostgreSQL 并发/生产数据库、支付渠道确认、首笔 GRANT/EXPIRE/REVERSE、活动写服务和外部验收尚未完成。
2026-08-14 P8-004 首笔触发与退款闭环补充：`create_payment_attempt` 接受可选 `referral_attribution_id`，在 pending PaymentAttempt 建立后同事务占用活动奖励槽；已验签失败通知释放占用。`confirm_payment` 对同一支付尝试立即提交邀请人权益 `GRANT`，重放不重复发放；奖励提交、自然到期和退款关闭会向邀请双方写入只含状态/渠道的幂等站内通知；90 天任务只过期未消费的可用量，已消费/已保留量不误过期；活动结束后的迟到确认释放预留而不发奖励；退款按 `RELEASE`/`EXPIRE`/`REVERSE` 顺序关闭绑定奖励并阻止再次触发。Commerce/Referral/迁移/Admin 定向回归 `26 passed`，Ruff/mypy 通过；随后全仓 `make check` 为 Backend `700 passed/92 skipped`、mypy `126 source files`、Web `57 files/405 tests`、Admin `33 files/120 tests`，两端 lint/typecheck/production build 全通过。P8-004 仍为 `IN_PROGRESS`，因为真实支付渠道查单/回调、超时 Worker、活动前台确认/退款确认、真实生产数据库与外部验收仍缺。
2026-08-14 P8-005 活动退款确认补充：新增 `0029_refund_confirmation` 与 `ReferralRefundConfirmation`，在退款前固定 `Order`、`Payment`、`RewardReservation`、`CampaignVersion`、`ProductVersion`、受邀用户、当前政策版本、确认时间和可选会话；绑定活动奖励的普通退款没有这条主动确认会在修改 Payment/Order/Refund 前拒绝，确认记录可幂等复用并在最终 Refund 时校验全部绑定事实。Commerce/迁移定向回归通过，Ruff/mypy 通过。P8-005 仍为 `IN_PROGRESS`，因为公共确认 API/前台退款 UI、渠道强制退款例外、双方真实通知投递和生产支付接线尚未完成。
2026-08-14 P8-005 Admin 证据补充：财务只读 `/api/v1/admin/commerce/refunds` 现在左连接 `ReferralRefundConfirmation`，返回确认记录 ID、政策版本和接受时间；没有确认的普通退款返回空值，不改变退款权限或写入路径。新增 Admin API/UI 回归，覆盖绑定事实、非敏感字段和表格展示；全仓 `make check` 为 Backend `700 passed/92 skipped`、mypy `126 source files`、Web `57 files/405 tests`、Admin `33 files/121 tests`，两端 lint/typecheck/production build 全通过；Admin Playwright smoke `48 passed/4 skipped`。P8-005 仍为 `IN_PROGRESS`，因为公共确认 API/前台退款 UI、渠道强制退款例外、双方真实通知投递、真实支付接线与 P4-007 外部验收尚未完成。

2026-08-14 P3-009/P8-001/P8-006 Referral 写服务与未来限制补充：Admin 新增带 CSRF、操作原因和审计的 `POST /api/v1/admin/referrals` 活动创建、`/{campaign_id}/codes` 活动码、`/{campaign_id}/reward-slots` 商品奖励槽和 `/{campaign_id}/state` 状态命令；活动版本、公开码、active ProductVersion、状态机转移和重复提交均在服务端确定性校验。新增 `0030_referral_restrictions` 与 `referral_participation_restrictions`，双人 correction 完成后限制本次邀请双方的未来 referral 参与，锁定归因和支付前奖励预留都会拒绝受限 User；申诉 Admin 只返回受限双方 UUID 数量事实，不返回风险原值或限制原因。冻结 Admin OpenAPI、Backend/Admin 回归、Ruff、mypy 和空库迁移均通过。P3-009/P8-001/P8-006 仍为 `IN_PROGRESS`，因为前台归因/进度、真实生产活动写入、真实支付/通知、运营完整接线和外部验收仍缺；Admin 邀请页继续只读，不在 P4-007 前新增未批准页面合同。

2026-08-14 P6-005 历史路由真接线补充：正式 `/account/history` 和 `/account/history/{reading_version_id}` 不再固定渲染登录占位，而是先复用账户会话门控，再分别接入已有的 `GET /api/v1/readings` 版本摘要和 `ReadingResult` 私有详情；未登录时不发历史请求，列表链接使用账户历史路由，详情仍由服务端所有权校验。Web 历史路由/历史组件/私有表面定向回归 `25 passed`，typecheck、lint 通过。P6-005 仍为 `IN_PROGRESS`，因为完整 ChartTask/ReadingRoot/Version 聚合、真实用户历史数据、导出/删除关联和 P4/P12 外部准入尚未完成。

2026-08-14 P6-004 账户档案入口真接线补充：正式 `/account/profiles` 与 `/account/profiles/{profile_id}` 复用账户会话门控，分别接入已有的 ProfileSummary 列表和 ProfileVersion 历史 API；详情只展示版本号/确认时间，未登录不请求档案，服务端所有权失败保持错误态，不根据 URL 猜测出生资料。历史/档案/私有表面组合回归 `28 passed`，Web 全量 `59 files / 411 tests`、typecheck、lint、production build 通过。P6-004 仍为 `IN_PROGRESS`，因为照片与他人资料的完整用户授权、资料编辑/删除关联、真实生产秘密治理和 P4/P12 外部准入尚未完成。

2026-08-14 P6-006/P7-008 数据权利与分享入口补充：正式 `/account/settings/privacy-data` 接入已有账户导出和 7 天注销/撤销 API；导出只触发 JSON 下载，不把完整 payload 放入 DOM，注销提交需要确认并显示服务端 `cancel_until`。正式 `/share/{token}` 接入短时加密分享快照 API，只展示 ReadingDocumentV1 的公开摘要、判断、依据和边界，过期/撤销 token 保持不可用；本轮又把 accepted ReadingResult 的分享创建与撤销动作接入已有 owner-scoped API，默认明确发送 24 小时 TTL。P7-008 仍为 `NOT_STARTED`，因为私有媒体/对象存储、短时下载与导出完整合同、真实生产授权和外部验收仍缺；P6-006 的后端与账户入口不替代生产数据权利队列验收。

2026-08-14 P7-007 站内通知用户投影补充：新增 `0031_notification_in_app_state`，为 NotificationOutbox 持久化 `read_at`/`deleted_at` 与 owner/time 索引；新增当前账户的站内列表、未读筛选、单条已读、全部已读和软删除 API。响应只返回固定标题、摘要、时间、已读状态和已知原任务入口，email/sms、别的用户、payload、kind、投递错误均不进入用户响应，跨用户命令统一返回 404。Web `/account/notifications` 已接会话门控和真实 API，未登录不读取列表。后端通知/commerce/身份定向 `21 passed`、OpenAPI `5 passed`、Web 通知/路由 `7 passed`，fresh SQLite upgrade/head 与 `alembic check` 通过；随后后端全量 `710 passed/92 skipped`、Web 全量 `62 files/417 tests`、Admin `33 files/121 tests`，两端 lint/typecheck/build 通过。P7-007 仍为 `IN_PROGRESS`，因为真实 SMTP/SMS/站内投递部署、退信、全业务事件覆盖、生产 SLO/告警和外部验收尚未完成。

2026-08-14 P6-001/P6-005/P7-001/P7-002/P8-007 账户事实读面补充：新增 owner-scoped `GET /api/v1/account/orders`、`/account/entitlements` 和 `/account/referrals`，订单只返回商品/金额/订单与履约状态，权益从持久化追加式事件按合法顺序重新投影，邀请只返回当前账户自己的活动进度、邀请码和奖励状态；跨用户、source ref、支付标识、奖励数量和内部 owner UUID 不进入用户响应。Web `/account/orders`、`/account/entitlements`、`/account/invitations`、`/account/invites` 已接会话门控和真实 API，`/account/settings/security` 调用既有撤销全部会话命令，`/account/settings` 展示已有安全/通知/数据权利入口，旧 `/account/data-rights` 复用真实数据权利表面；未登录不读取，账户页面不生成余额或公开归因。账户 Commerce/Referral/OpenAPI 定向 `7 passed`，Web 定向 `14 passed`；随后 Backend 全量 `714 passed/92 skipped`、mypy `130 source files`、Web 全量 `67 files/427 tests`、Admin `33 files/121 tests`，两端 lint/typecheck/production build 通过。证据：`docs/releases/evidence/2026-08-14-account-surfaces/README.md`。该时点 P8-007 仍为 `NOT_STARTED`，随后已由公开邀请归因切片推进为 `IN_PROGRESS`；P7-001/P7-002 仍为 `IN_PROGRESS`，P6-001/P6-005 仍受真实身份/完整历史与生产外部验收约束。
2026-08-14 P6-005 Root/Version 历史投影补充：新增设备会话专用 `GET /api/v1/account/history`，从真实 `ReadingRoot`/`ReadingVersion` 按当前用户分组并按版本倒序返回安全摘要；响应排除 `prior_answer`、`input_request` 和运行时私有载荷，跨用户 Root 不进入结果。正式 `/account/history` 仅登录后改读该投影，旧访客 `/api/v1/readings` 平列表保持不变。后端历史与 OpenAPI 定向 `11 passed`，Web 账户历史/私有表面/兼容历史 `25 passed`；证据：`docs/releases/evidence/2026-08-14-p6-005-history-projection/README.md`。P6-005 仍为 `IN_PROGRESS`，因为 ChartTask 生产聚合、真实账户数据、导出/删除关联和 P4/P12 外部门禁未完成。
2026-08-14 P11-005 Recast 补充：新增 owner-scoped `POST /api/v1/readings/{reading_version_id}/recast`，请求按 `action` 判别 profile/日运/周运/六爻换事件结构；源版本必须属于当前账户、已 Accepted 且有 AcceptedCopy，成功后总是创建独立 ReadingRoot，Follow-up 仍严格留在原 Root。Recast 复用既有确定性编译器，幂等重放返回同一版本，跨 owner 返回 404，未交付源返回 409，周运按 `near_seven` 付费闸门校验；OpenAPI、Web API 客户端和测试已同步。定向 Recast/OpenAPI `16 passed`，dogfood 周运闸门 `1 passed`，Web API `5 passed`；证据：`docs/releases/evidence/2026-08-14-p11-005-follow-up-contract/README.md`。P11-005 仍为 `IN_PROGRESS`，因为真实权益 CONSUME/Fulfillment Worker、未发布术数能力、PNG/PDF 和生产支付/发布门禁尚未完成。

2026-08-14 P8-007 公开邀请归因纵切片补充：公开 `/invite/{code}` 现在读取服务端活动状态并区分 planned、active、paused、full、ended；活动中的访客可通过带 guest CSRF 的接口记录或幂等清除临时归因，公开响应不返回 inviter、visitor hash 或内部 UUID。首次 OTP 注册只在同一访客会话中锁定最后一个仍有效的邀请码；既有账户、自邀、无效/暂停/结束活动不会写入永久归因。Admin 活动事实漏斗补充临时归因数量，账户通知/邀请私有读面继续只按 owner 返回。Backend 公开归因/身份/Referral/Admin/OpenAPI 定向 `52 passed`，公开契约 `10 passed`，Admin Referral `2 passed`，Web 邀请页面 `3 passed`；随后标准 `make check` 为 Backend `728 passed/92 skipped`、Web `68 files/431 tests`、Admin `33 files/121 tests`，Ruff、mypy、两端 lint/typecheck/production build 全通过；证据：`docs/releases/evidence/2026-08-14-p8-007-public-invite/README.md`。P8-007 仍为 `IN_PROGRESS`：本地 API/UI/静态合同已闭环，但生产身份会话、支付奖励确认、通知投递/Worker、活动运营数据库、P4-007 用户验收及 P12 外部门禁仍未完成。
2026-08-14 P8-008 未来商业关闭态补充：新增 OpenAPI 负向合同，锁定 Web 与 Admin 公开接口不出现 subscription、wallet、topup 或 recharge 路径；定价页明确当前不开放自动续费、代币余额、充值钱包或永久无限 AI，按钮点击不会被写成已付款。Web 定价页测试同步断言完整关闭态，未新增订阅、充值或余额 API。P8-008 定向 OpenAPI/未来商业合同 `11 passed`，Web 定价页 `10 passed`，随后完整 `make check` 为 Backend `729 passed/92 skipped`、Web `68 files/431 tests`、Admin `33 files/121 tests`，Ruff、mypy、两端 lint/typecheck/production build 全通过；治理合同 `11 passed`，证据：`docs/releases/evidence/2026-08-14-p8-008-future-commerce-closed/README.md`。P8-008 仍为 `IN_PROGRESS`：这是有意保持关闭的本地合同切片，不代表未来订阅/充值资格、真实支付适配器、生产账务或用户批准已经完成。
2026-08-14 P12-002 生产秘密槽位审计补充：执行 `python3 scripts/check_production_secrets.py`，fail-closed 报告 `MINGLI_IDENTITY_HASH_KEY`、`MINGLI_CONTENT_ENCRYPTION_KEY_B64`、`MINGLI_CONTENT_ENCRYPTION_KEY_ID`、`DEEPSEEK_API_KEY` 四个生产槽位缺失；脚本不打印秘密值，也不声称云 Secret Manager 已接通。生产配置代码仍会拒绝 secure cookie 关闭、本地 hash/content key、fake OTP/Runtime/Model、bootstrap credentials 和未固定 Runtime 路径。证据：`docs/releases/evidence/2026-08-14-p12-002-production-secret-slots/README.md`。P12-002 继续 `BLOCKED`，因为真实注入、轮换、会话失效、主账号 MFA/RAM 最小权限和生产 debug 关闭仍需外部环境执行与证据。

## 15. 变更记录

| 日期 | 变更 | 批准 |
|---|---|---|
| 2026-08-13 | 结束完整 `grill-me`；冻结自有算法 + 青囊产品模式 + METIS 表现层、UI-first、完整 Admin、密码、商业、邀请和唯一文档纪律 | 用户明确确认 |
| 2026-08-13 | `main` 冻结为唯一开发基线；旧 UI 分支只取证，不整体合并 | 用户明确确认 |
| 2026-08-13 | 旧 FateRadar 名称与墨绿金视觉退出当前产品 | 用户明确确认 |
| 2026-08-13 | 批量推进 P1–P9 的本地可闭环项；完成 4 档 Web/Admin smoke、OpenAPI/Presentation 合同、密码与 ConsentRecord、商品/账本/邀请/CMS 持久化基础；生产门禁与用户逐页批准保持未完成 | 待用户验收 |
| 2026-08-13 | 用户指出 UI 仍像旧版且只换色加按钮；退役旧 `/app/**` 产品树，重做两端 UI Lab/专用页面合同并修移动、表单、键盘和 RBAC 偏差；P2/P3/P4 不提前报完成 | 待用户验收 |
| 2026-08-14 | 用户判定现行中性视觉「整体廉价/乱」，经 `grill-me` 逐题确认后批准方向 C「现代 SaaS 锐感」全站换皮（决策记录与审计：`docs/redesign/2026-08-14-*.md`）。影响范围：`DESIGN.md` §2/§3/§4/§6.1/§6.3/§8.3/§8.5/§10 修订；首页改「价值主张 + 任务入口」混合结构；多盘问答（`canwen`）并入命盘合参，原路由保留重定向、历史任务与报告不失效；`/account` 重建为消费 App 式「我的」页；字阶冻结收口。迁移与重新验收：全部公共页、产品流、工作台、账户区、Admin 需按新合同重走 360/768/1024/1440 真实浏览器验收并逐页由用户批准；既有 P2/P3/P4/P4-007 验收状态不自动继承，逐项重验 | 用户明确确认 |
| 2026-08-14 | 阶段 1 基础层：共享 token/base、字阶收口、Web/Admin primitives 与方向 C 基础浏览器审计；32/32 四视口抽样、字阶违规 0，证据与报告见 `docs/redesign/2026-08-14-phase1-report.md`、`web/e2e/screenshots/audit-2026-08-14/phase1/` | 证据就绪，待用户验收 |
| 2026-08-15 | 阶段 2 公共壳、新首页与营销页族完成本地门禁；web `439 tests`、admin `121 tests`、两端 lint/typecheck/build 全绿；系统 Chrome 16 路由 × 4 视口 `64/64`，截图与报告见 `docs/redesign/2026-08-14-phase2-report.md`、`web/e2e/screenshots/audit-2026-08-14/phase2/`；Button `asChild` 单元素数组运行时回归已修复 | 证据就绪，待用户验收 |
| 2026-08-15 | 阶段 3 账户区重建为「我的」：身份/游客边界、六个既有入口、最近交付与待处理事项完成；web `439 tests`、admin `121 tests`、两端 lint/typecheck/build 全绿；系统 Chrome 8 路由 × 4 视口 `32/32`，证据与报告见 `docs/redesign/2026-08-14-phase3-report.md`、`web/e2e/screenshots/audit-2026-08-14/phase3/` | 证据就绪，待用户验收 |
| 2026-08-15 | 阶段 4 七个单术入口、工作台、报告/状态、命盘合参与问事合参完成真实浏览器复核；web `439 tests`、admin `121 tests`、两端 lint/typecheck/build 全绿；系统 Chrome 11 路由 × 4 视口 `44/44`，证据与报告见 `docs/redesign/2026-08-14-phase4-report.md`、`web/e2e/screenshots/audit-2026-08-14/phase4/` | 证据就绪，待用户验收 |
| 2026-08-15 | 阶段 5 Admin token/壳对齐：顶栏收口为移动 56px/桌面 64px，1024px 起 240px 侧栏；Admin `121 tests`、lint/typecheck/build 全绿；系统 Chrome 41 路由 × 4 视口 `164/164`，证据与报告见 `docs/redesign/2026-08-14-phase5-report.md`、`admin/e2e/screenshots/audit-2026-08-14/phase5/` | 证据就绪，待用户验收 |
