---
status: accepted
date: 2026-08-09
supersedes: 0003-use-direct-virtual-goods-and-an-entitlement-ledger
---

# 使用渠道中立的计费层与统一权益账本

业务商品由 Product Family、不可变 Product Version 和渠道 Product Offer 三层表示。P0 网站按环境接入微信 JSAPI/H5/Native 与支付宝手机/电脑网站支付；未来 iOS 接入 StoreKit 2。各渠道只产生支付、退款或订阅周期事实，所有访问和次数统一由追加式 Entitlement Ledger 投影。

P0 仍只卖个人命盘深度解读和一事一问·六爻两种单次商品。P1 订阅的表和接口可预留，但只有渠道周期扣款资质、留存和单位经济性通过后才对外启用。每次成功周期独立授予当期权益，取消续费不提前收回已付周期。

## Consequences

Payment Gateway、Recurring Gateway 和未来 App Store Adapter 都隐藏在 Billing Module 后面。客户端回跳不作为到账依据；验签通知或服务端查单才可生成 GRANT。生成先 RESERVE，只有 Accepted Copy 与交付落库时 CONSUME；失败 RELEASE，退款 REVERSE。网站与 App Store 的渠道价格和商品 ID 可以不同，但商品语义和访问投影必须一致。
