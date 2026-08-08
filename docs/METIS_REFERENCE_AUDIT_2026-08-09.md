# Metis紫薇与开源仓库参考审计

> 核验日期：2026-08-09  
> 性质：外部参考快照，不是本项目产品合同  
> 权威取舍：[PRODUCT_BLUEPRINT_WEB_IOS_V2.md](./PRODUCT_BLUEPRINT_WEB_IOS_V2.md)

## 1. 核验范围与限制

本次核验使用了：

- [Metis紫薇](https://metisziwei.com/) 的公开首页、起盘、账户、专业版、支持、隐私和条款页面；
- 公开页面加载的 Next.js HTML 与静态 JavaScript；
- [Renhuai123/ziwei-doushu](https://github.com/Renhuai123/ziwei-doushu) 的 README、LICENSE、目录和部分前端源码；
- 微信支付、支付宝、Apple 与阿里云的官方文档。

当前环境无法完成已登录账户操作，也没有实际发起付款，因此：

- 可以确认公开页面呈现、公开前端包含的能力和 API 路径信号；
- 不能确认 Metis 私有后端的数据表、密钥管理、风控、真实商户审批或支付成功率；
- 不能把静态前端里出现的支付按钮当成当前一定可用；其专业版页面当时明确显示“在线支付暂时不可用”。

## 2. UI 观察

### 2.1 公共首页

- 固定、简洁的顶部导航和大字标；
- 用编号和大场景卡片组织紫微命盘、合盘、命理双子、三纪和学术中心；
- 页面更像编辑型品牌站，不像后台管理系统；
- 移动端菜单使用大字号纵向列表；
- 公共站偏黑白，应用工作区另有深色主题。

### 2.2 起盘页

公开页面包含：

- 姓名可选；
- 公历/农历、出生年月日；
- 出生时辰和“不知道出生时间”；
- 出生地点与真太阳时说明；
- 性别；
- “立即起盘”主按钮；
- “登录后自动保存、换设备也能看；未登录不保存”的提示。

### 2.3 专业版页

- Free 与 Pro 双卡对照；
- 先列价格，再列解读范围、排盘层次和 AI 配额；
- 当前公开价为 168 元一次性买断、永久有效；
- FAQ 明确不会自动续费；
- 页面同时包含付款故障、订单查询、二维码过期和补开通文案；
- App 模式只提示回 App 内开通，网页购买区域被分开处理。

## 3. 账户系统的公开信号

公开账户页在未登录时显示“你还没登录”。隐私政策写明邮箱用于登录验证码和会员服务，静态前端还出现以下能力：

- 手机号和邮箱验证码；
- 邮箱密码登录/修改；
- 绑定手机号、绑定邮箱；
- OAuth provider 列表和社交登录；
- 账号合并；
- 退出登录；
- 账户信息、会员状态、AI 额度和历史；
- App session 与网站 Cookie 会话交换。

可观察到的 API 路径包括：

~~~text
/api/auth/me
/api/auth/send-code
/api/auth/send-email-code
/api/auth/verify-code
/api/auth/login-password
/api/auth/register
/api/auth/bind-phone
/api/auth/bind-email
/api/auth/account-merge
/api/auth/oauth/providers
/api/auth/logout
/api/auth/app-session
~~~

这些路径只说明前端预期的能力，不代表其后台代码已开源或可以复用。

### 本项目吸收的账户原则

- 一个内部 User 可绑定多个登录身份；
- 未登录可以试算，登录后保存和跨设备查看；
- 账户页集中展示身份、历史、订单和数据权利；
- iOS 与网站需要会话桥接，但通过标准授权码和 Keychain/Cookie 完成。

### 本项目不照搬

- P0 不做密码，先用手机号/邮箱 OTP；
- 不把 App 长期 token 放在 localStorage；
- 不按相同邮箱自动合并账号；
- 不把 AI 对话和正式报告只保存在浏览器本地；
- 不让“会员状态”成为唯一权益事实。

## 4. 支付方式的公开信号

静态前端出现的接口包括：

~~~text
/api/pay/status
/api/pay/wechat/create
/api/pay/alipay/create
/api/pay/order-status
/api/pay/reconcile
~~~

对应界面文案表明其设计路径大致为：

- 桌面端生成微信支付二维码；
- 二维码约 5 分钟有效；
- 支付后自动查询并开通，也允许用户点击“我已支付·查询订单”；
- 移动端偏向支付宝跳转；
- 页面含微信、支付宝可用状态检查和客服兜底；
- 一次性买断，不自动续费。

公开隐私政策写的是“网页端订单可能由微信支付处理”，当日专业版页面显示在线支付暂不可用。因此上述内容只能作为交互设计参考，不能据此断言其商户通道当前全部可用。

### 本项目吸收的支付原则

- 付款前登录并绑定清晰商品；
- 桌面端适合二维码，移动端适合 JSAPI/H5/WAP 跳转；
- 支付后显示确认中，提供主动查单和客服路径；
- 二维码失效只失效一次 Attempt，不关闭整个业务 Order；
- 免费与付费权益对比和 FAQ 必须在付款前可见。

### 本项目不照搬

- 不复制其私有 API 名称、商户配置或状态字段；
- 不以“刷新或重新登录就会开通”作为唯一补单方案；
- 不把客户端查询结果直接写成会员成功；
- 不做 168 元永久 Pro + 持续每日 AI 的成本承诺；
- 不使用一个 Pro 布尔值控制全部报告、额度和退款。

## 5. 开源仓库边界

仓库采用 MIT License。README 明确开放：

- 紫微排盘算法、四化、格局知识库；
- 古籍原文数据；
- Next.js 前端、命盘工作区、合盘、知识和古籍页面；
- 响应式与主题设计。

README 同时明确未包含：

- AI 解读 prompt；
- 后端 API；
- 登录、短信、会员和支付；
- 服务端签名、防刷和水印；
- 部署、数据库和运维配置。

仓库根目录也没有账户、支付、数据库迁移或服务端 API 实现。因此它适合作为 UI/排盘参考，不是本项目账户与商业化的基础代码。

若未来实际复用代码，必须保留 MIT LICENSE；若使用其 51.8 万样本数据，按 README 做 attribution，并在引入前验证：许可快照、数据来源、命理体系、性别/健康内容风险和与 mingli-master 的冲突。当前 P0 不引入该数据集。

## 6. 最终采用矩阵

| 参考项 | 决定 | 落地方式 |
|---|---|---|
| 编辑型首页与大卡片 | 采用思路 | 自有品牌、三任务卡 |
| 先试算、后登录保存 | 采用 | Guest Session + 一次性认领 |
| 手机/邮箱归并账号 | 采用模型 | User + Login Identity |
| 密码和全部社交登录 | 暂不采用 | P0 OTP，按需扩展 |
| Free/Pro 双卡 | 采用表达 | Free 与两种单次商品对照 |
| 168 元永久 Pro | 不采用 | 29.90/9.90 明确结果商品 |
| 桌面微信二维码 | 采用 | 官方 Native 支付 Adapter |
| 移动端支付宝 | 采用 | 官方手机网站支付 Adapter |
| 客户端补查订单 | 采用交互 | 后端 reconcile 为准 |
| localStorage 长期 token/对话 | 不采用 | HttpOnly Cookie、服务端历史 |
| WebView 作为正式 iOS | 不采用 | 原生 SwiftUI + StoreKit 2 |
| 开源排盘 UI | 可选择性参考 | 保留 MIT，重新适配本产品流程 |
| 开源样本数据 | P0 不采用 | 另立数据与体系审核 Gate |

## 7. 参考链接

- [Metis紫薇](https://metisziwei.com/)
- [Metis 起盘](https://metisziwei.com/chart)
- [Metis 账户](https://metisziwei.com/account)
- [Metis 专业版](https://metisziwei.com/subscription)
- [Metis 支持中心](https://metisziwei.com/support)
- [Metis 隐私政策](https://metisziwei.com/privacy)
- [Metis 服务条款](https://metisziwei.com/terms)
- [开源仓库](https://github.com/Renhuai123/ziwei-doushu)
