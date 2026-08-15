# UI 合同纠偏与回归证据（2026-08-14）

## 结论边界

本轮针对“页面仍像旧版，只换色并增加按钮，没有按开发文档实现”的反馈，修正了已复现的 Web、Web UI Lab 与 Admin 合同偏差。当前工作树通过了本地测试、类型、lint、production build、四档 production 浏览器矩阵与负向响应检查。

这份记录只证明本轮投诉项已经进入可复验状态，不代表整个 P2/P3 已完成，也不代替 `P4-007` 用户逐页浏览与明确批准。正常业务路由没有因为验收而注入 Fixture；后端未接能力继续显示 unavailable/empty，不伪造成功、盘面、订单或支付数据。

## 基线与范围

- Git 基线：`f488fa4d6eaa989b708b14d87b747ee931468829`。
- 工作树在本轮开始前已有大量 staged/unstaged 改动；本轮没有 reset、checkout、提交或覆盖用户已有改动。
- 权威合同：`DESIGN.md` 与 `docs/CHECKLIST.md`。
- 本轮没有改写 `DESIGN.md`；只在 `docs/CHECKLIST.md` 记录真实断点和本证据链接。

## 已修正的偏差

### Web 正式产品树

- 登录态公共头部、OTP 成功跳转、个人中心和私人导航统一进入 `/account/**`。
- 旧 `/app/**` 页面不再承载“先建档，再看盘”的废弃流程；9 条旧路径使用服务端临时重定向进入 `/account/**`、`/bazi`、`/liuyao` 或 `/daily`。
- 游客仍可直接从正式 `/bazi` 等产品入口起盘，档案不是免费起盘前置。

### Web UI Lab

- 55 条 `CHECKLIST` 4.1–4.3 路由模式进入版本化注册表并可从开发态 UI Lab 发现；其中 `/share/[shareId]` 与正式路由参数一致，`/account/data-rights` 已补入账户验收覆盖。
- 产品 Fixture 绑定正式 ViewModel Fixture 注册表；非产品页面使用明确的 typed surface schema。
- 移除五个自绘 preview shell，改为组合正式 `ProductInputForm`、`WorkbenchShell`、`ReadingShell`、账户/Auth/商业/公共内容 Surface 与正式 `Status`。
- `filled` 会真实填入表单初值；loading、unauthorized、failed、ready、free-summary 等状态会替换主体，而不是只改一行提示。
- `/_ui-lab` 在两端 production 均返回 404；正常产品路由禁止导入 Fixture。

### Web 交互与可访问性

- 移动工作台“更多”改为可键盘操作的菜单；未接动作逐项给出原因，不再是永久 disabled 的死按钮。
- 双人合盘接入表单 schema、顶部错误摘要、首错聚焦和方向键/Home/End Tabs。
- 六爻、问事合参要求录入六次过程后才能确认，不再用 disabled 空选择器进入工作台。
- 见相输入现在要求照片本地选择后才可确认；质量检查保持 unavailable 边界，删除会清空文件控件并允许重选；用户补充信息、另行入档同意、相机待接入说明和确认页保存范围均可见，提交值不携带原始 `File`。
- Web UI Lab 新增 15 个见相媒体/生命周期状态：相机权限未询问/允许/拒绝、本地选择、裁切、旋转、质量不合格、重拍、观察失败/处理中、原图过期提示、主动入档、删除中/已删除与原图过期但结果可看；均复用共享 `Status`，不伪造相机、上传或视觉结论。
- 隐私政策与服务条款共用可访问的版本元数据区，明确显示“开发预览 v0.1 / 未生效 / 真实主体与法律审阅完成后发布”，并提供真实登录与价格/交付入口；登录、注册、结账和订单状态也能直接到达两份政策；P2-002 仍不宣称法律或生产完成。
- 帮助与支持页纠正身份流程事实：明确密码主登录、OTP 的注册验证/快捷登录/找回用途，以及 OTP 核验后设置密码并同意政策；移除“无需注册密码”的旧说法。账户页的页头、OTP 快捷入口和设备状态也统一到同一身份合同；P6-001 仍不宣称真实身份服务已接通。
- 关于与边界页移除“页面已预制”内部施工文案，保留真实的品牌、运营主体和团队资料尚未冻结说明；这条文案契约已进入公共页单测和生产路由回归。
- 阅读报告锚点加入 sticky header 对应的 `scroll-margin`。
- 首页深色任务卡正文改用反色 token，修复约 2:1 的低对比级联覆盖。
- 两处表单错误摘要移除多余的 4px 左侧装饰条；整框危险色、标题、`role="alert"`、字段错误和焦点行为保留。

### Admin 信息结构与权限

- 用户、支付、员工、解读、CMS 等代表性路由使用领域专用列；详情、Runtime、Health、Settings 使用独立 surface，不再全部落到同一个五列表壳。
- 同一个 `getAdminRouteAccess` 同时驱动 UI Lab 权限摘要和真实按钮；读权限与 route/operation 写白名单分开。
- 代表性规则：support/users 只读、support/support-cases 可提交；ops/readings 只读、ops/CMS 可写；finance/refunds 可写；PUBLIC/PAUSED 能力仅 superadmin 可写。
- 小于 768px 与 UI Lab 360px container 使用摘要卡表格；列 schema 同时生成桌面表头与移动 `data-label`。
- 批量操作使用真实 `selectedIds`，不再固定取第一条；UI Lab 的伪视口现在能触发容器断点。
- 未知 Admin 路由返回 404；无后端数据时显示 unavailable，不注入 Fixture。
- Admin 写操作 UI Lab 继续区分 `确认` 与 `原因`：前者先展示影响范围并提供独立确认按钮，后者才要求填写审计原因；不改变真实服务端未接入的边界。
- 两端 Next 配置允许 `127.0.0.1` 与 `localhost` 加载开发态 client 资源；避免开发 UI Lab 只剩服务端 HTML、hydration marker 永远停在 `false`。
- Web UI Lab 根节点公开了仅供开发验收使用的 hydration marker；marker 变为 `true` 后，测试才继续切换正式八字表单、768px 内层画布并检查整页无横溢。

## 自动化结果

| 范围 | 命令或检查 | 结果 |
|---|---|---|
| Web 单元/合同 | `cd web && npm test -- --run` | 46 files / 369 tests passed |
| Admin 单元/合同 | `cd admin && npm test -- --run` | 10 files / 58 tests passed |
| Web lint/typecheck | `npm run lint`、`npm run typecheck` | passed |
| Admin lint/typecheck | `npm run lint`、`npm run typecheck` | passed |
| Web production build | `cd web && npm run build` | passed；最终 CSS 修正后再次 passed |
| Admin production build | `cd admin && npm run build` | passed |
| Web production Playwright | `cd web && npm run e2e:smoke -- e2e/route-matrix.spec.ts e2e/accessibility.spec.ts` | 360/768/1024/1440，共 60 passed |
| Web production route matrix after about-copy fix | `cd web && npm run e2e:smoke -- e2e/route-matrix.spec.ts --grep "public and private route matrix"` | 360/768/1024/1440，共 4 passed；后端 8000 未启动时仅记录预期代理拒绝 |
| 政策页浏览器合同 | `BASE_URL=http://127.0.0.1:3001 npx playwright test e2e/route-matrix.spec.ts --grep "policy pages publish"` | 360/768/1024/1440，共 4 passed |
| 认证/购买政策入口浏览器合同 | `BASE_URL=http://127.0.0.1:3001 npx playwright test e2e/route-matrix.spec.ts --grep "auth and commerce routes"` | 360/768/1024/1440，共 4 passed |
| 支持页身份文案浏览器合同 | `BASE_URL=http://127.0.0.1:3001 npx playwright test e2e/route-matrix.spec.ts --grep "support explains"` | 360/768/1024/1440，共 4 passed |
| 账户页身份文案浏览器合同 | `cd web && npm run e2e:smoke -- e2e/route-matrix.spec.ts --grep "account explains"` | 360/768/1024/1440，共 4 passed；本地 backend 8000 未启动时按 unavailable 诚实降级 |
| 见相浏览器回归 | `BASE_URL=http://localhost:3001 npx playwright test e2e/product-journeys.spec.ts --grep "jianxiang keeps"` | 360/768/1024/1440，共 4 passed；本地 backend 8000 未启动，页面按 unavailable 诚实降级 |
| Web 产品旅程浏览器回归 | `cd web && npm run e2e:smoke -- e2e/product-journeys.spec.ts` | 360/768/1024/1440，共 16 passed；本地 backend 8000 未启动，页面按 unavailable 诚实降级 |
| Admin production Playwright | `ADMIN_BASE_URL=http://127.0.0.1:3001 npx playwright test e2e/route-matrix.spec.ts e2e/accessibility.spec.ts e2e/admin-contracts.spec.ts` | 360/768/1024/1440，共 44 passed |
| Web production 全量 Playwright | `cd web && npm run e2e:smoke` | 80 passed、4 skipped；4 个跳过项是显式要求 `UI_LAB_E2E` 的 Web development-only UI Lab；其余包含 4 档可访问性、产品旅程、全路由、负向与 smoke；后端 8000 未启动时按 unavailable 降级 |
| Admin production 全量 Playwright | `cd admin && npm run e2e:smoke` | 48 passed、4 skipped；跳过项是显式要求 `ADMIN_UI_LAB_E2E` 的 development-only UI Lab |
| Web development UI Lab hydration | `npm run dev -- -p 3000`；`BASE_URL=http://127.0.0.1:3000 UI_LAB_E2E=1 npx playwright test e2e/ui-lab-development.spec.ts --project=1440` | 1 passed；确认 127.0.0.1 下客户端已接管，再验证正式八字表单、768px 内层预览和整页无横溢 |
| Admin development UI Lab hydration | `npm run dev -- -p 3001`；`ADMIN_BASE_URL=http://127.0.0.1:3001 ADMIN_UI_LAB_E2E=1 npx playwright test e2e/ui-lab-development.spec.ts --project=1440` | 1 passed；本机 dev origin client 资源可加载，预览宽度/角色/RBAC/写目标交互通过 |
| 文档权威合同 | `uv run --project backend pytest tests/contract/test_document_authority.py -q` | 7 passed |
| 补丁卫生 | staged/unstaged `git diff --check`、冲突标记扫描 | passed |

Web 完整测试第一次并行整合时出现一次 OTP 交互失败（找不到“六位验证码”）；根因是测试只等待 disabled 的邮箱字段出现，没有等待安全会话 bootstrap 完成。补充状态等待后，账户体验整文件 11/11、Web 完整套件 369/369 通过；没有改动 OTP 产品状态逻辑。

## Production 负向检查

- Web 与 Admin CSP 的 `script-src` 在 production 不含 `unsafe-eval`。
- Web `/app/bazi` 返回 `307`，`Location: /bazi`。
- Web `/account` 返回 `Cache-Control: private, no-store, max-age=0`、`X-Robots-Tag: noindex, nofollow, noarchive`，HTML 同时含 robots noindex meta。
- Web `/_ui-lab`、Admin `/_ui-lab`、Admin 未知路由均返回 404。
- 开发态 Web/Admin `/_ui-lab` 在 `127.0.0.1` host 下均可完成 hydration；production 仍返回 404。
- 浏览器测试期间后端 8000 未启动，账户/Admin 探测出现预期的代理连接拒绝；页面必须诚实降级，CSS/JS、路由、布局和断言均通过。

## 静态 UI 检测

按流程仅运行一次聚合 UI detector。它只报告两个 warning：任务表单和合盘表单错误摘要的 `border-left-width: 4px`。两处已人工确认是重复装饰并移除；最终 Web production build 通过。检测器没有反复重跑，避免把扫描循环冒充产品验收。

## 独立终审

同一位首轮 UI 审查者在所有修复与聚合回归完成后，对原始 finding 做了只读复核，没有修改文件，也没有启动新的广泛截图轮次：

- 原始 4 项 P1 全部 PASS：旧 `/app` 产品树、Web UI Lab 正式组件/状态合同、Admin 专用 surface、Admin 同源 RBAC。
- 原始 9 项 P2 全部 PASS：首页黑卡对比度、移动 More、合盘 Tabs、合盘空表、六次过程、Reading 锚点、Admin UI Lab container、360 摘要表、选择集写操作对象。
- 定向回归：Web 6 个文件 / 47 tests passed；Admin 6 个文件 / 24 tests passed；合计 71/71。
- 总裁决：未发现仍可触发的高/中优先级 UI 阻断；本轮代码问题可判解决。P4 的真实设备观感、文案主观接受度和最终产品验收仍需用户亲自确认。

## 尚未完成

- `P4-007`：需要用户亲自浏览公共页、各产品、账户与 Admin 后明确批准。
- P2/P3 中要求的全部深链、全部状态、真实后端数据和真实业务动作仍按 `docs/CHECKLIST.md` 保持 `IN_PROGRESS`。
- 真实算法 ViewModel、支付渠道、通知、完整 Admin 聚合 API、生产凭据/备份/告警/合规和发布批准不属于本轮 UI 纠偏的完成声明。
