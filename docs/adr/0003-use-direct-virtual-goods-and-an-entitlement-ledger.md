---
status: superseded
superseded_by: 0008-use-channel-neutral-billing-and-unified-entitlements
---

# 使用虚拟道具直购与追加式权益账本

> 历史说明：微信小程序“道具直购”部分已经由 ADR 0008 取代；追加式权益账本决定继续保留。

小程序数字报告只接入微信小程序虚拟支付的道具直购，不建设代币钱包，也不以一个可变的 paid 布尔值控制访问。支付成功追加 Grant，生成时追加 Reservation，核心返回 Accepted 后追加 Consumption，退款追加 Reversal；所有余额和访问状态都是账本投影。

## Consequences

重复推送、轮询补单、Worker 重试和退款都必须由幂等键安全重放。账本记录只追加不删除，商品版本和订单金额必须按下单时快照保存，客户端回调不能作为到账依据。
