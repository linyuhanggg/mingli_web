---
kind: external_dependency
name: SMTP 作为 OTP 邮件投递适配器
slug: smtp
category: external_dependency
category_hints:
    - vendor_identity
    - auth_protocol
scope:
    - '**'
---

OTP 投递支持 `fake | disabled | smtp` 三种适配器，生产可通过 `MINGLI_SMTP_HOST/PORT/USERNAME/PASSWORD/SENDER` 等环境变量配置 SMTP 服务（支持 starttls 或 ssl）。本地默认使用 fake OTP（固定验证码 `246810`），不会发送真实邮件。