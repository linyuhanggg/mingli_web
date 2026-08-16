# P10 八字事业深读交付合同（2026-08-16）

## 结果

本轮把已有 `bazi_deep` 编译动作收成一条明确的交付边界：

- 新增 `bazi-deep-output-v1`，要求事业维度至少三段、最多八段正文，并固定披露与现实判断边界；合同 ID 遵循模型审计允许的安全标识格式。
- 新增 `POST /api/v1/readings/bazi-deep`；它创建 `product_id=bazi-deep` 的 Reading Root，但 Job 初始为 `awaiting_fulfillment`。
- 只有 Commerce 完成 Payment/Fulfillment 绑定、固定 ProductVersion 快照后，Job 才转为 `queued`，Worker 不会抢跑。
- `ReadingJob → ReadingDocumentContext → ReadingDocumentV1` 现在传递商品快照中的追问次数；没有商品快照时，结果文档不会显示“可追问”。
- Web API 客户端与冻结 OpenAPI 已同步该端点和请求合同。

## 验证

- 深读合同、文档动作：`4 passed`
- Worker 等待权益边界：`1 passed`
- Bazi deep 编译器回归：`1 passed`
- 阅读 API：`56 passed`
- OpenAPI 对齐：`6 passed`
- 受影响 Python Ruff、compileall、`git diff --check`：通过

## 尚未完成

这轮没有声称深读正文已经生成，也没有创建真实商品、支付渠道或生产权益。要得到 Accepted 深读，还需要真实 ProductVersion/Offer、支付确认、真实模型输出满足三段合同、Worker/ReadingDocument 黄金样例、Web 购买入口和四视口验收。测试机仍是 `local + Fake`；生产 `443` 仍未切换到当前 Web release。

本证据不包含个人资料、密码、支付凭据、API key 或状态 token。
