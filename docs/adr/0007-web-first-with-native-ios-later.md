---
status: accepted
date: 2026-08-09
---

# 网站优先，后续使用原生 iOS

首发客户端改为移动端优先、桌面端完整可用的 Next.js 响应式网站；微信小程序不在当前首发路线。网站通过同源 /api 访问 FastAPI 模块化单体，并提供有限 PWA 能力。后续 iOS 使用 SwiftUI 和共享 OpenAPI/领域后端，不把网站 WebView 当正式 App。

这样可以先通过网页快速验证建档、免费解读、支付和复访闭环，又不会把登录、商品或权益绑定到浏览器。公开营销/方法页面可索引，/app、账户和报告页面 noindex、no-store，Service Worker 不缓存个人数据。

## Consequences

旧小程序骨架仅保留作历史参考，迁移确认前不删除。Web 和未来 iOS 必须复用 User、Profile、Reading、Product Family 和 Entitlement；客户端只负责交互，不能各自保存一套业务事实。iOS 数字内容使用 StoreKit 2，并遵守 App Store 的购买和登录规则。
