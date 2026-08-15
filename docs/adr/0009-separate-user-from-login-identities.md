---
status: accepted
date: 2026-08-09
amended_by: 0011-rebuild-the-product-surface-from-main-under-a-ui-first-contract
---

# 将 User 与所有登录身份分离

系统内部用随机 UUID 的 User 作为档案、解读、订单和权益的唯一账号根。手机号、邮箱、微信和 Apple 都建模为可验证、可绑定、可撤销的 Login Identity；浏览器或原生设备登录状态建模为独立 Device Session。

P0 默认支持手机号 OTP 和邮箱 OTP，不把密码作为必做能力；微信 OAuth 在商户配置具备时加入。iOS 上线时增加 Sign in with Apple，并允许用户经过双方重新验证后绑定现有账号。游客只能持有短期 Guest Session 和可认领草稿。

## Consequences

数据库不得把手机号、邮箱、OpenID 或 Apple subject 用作业务外键。Web 会话使用 HttpOnly Secure Cookie 与 CSRF 防护，正式访问令牌不进入 localStorage；iOS 凭据进入 Keychain。身份合并必须验证两个账号、处理订单/订阅冲突并写审计事件，不能仅凭相同邮箱自动合并。
