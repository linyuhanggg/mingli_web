---
status: accepted
---

# 仅通过 JSON Adapter 调用命理核心

业务后端不得 import、复制或改写 mingli-master；生产环境只通过它固定的单次进程协议 describe、prepare、complete 调用 JSON Adapter。每个解读根拥有独立运行时状态命名空间，业务侧只保存加密后的不透明连续状态；这样核心可独立升级和验签，模型、支付与任何客户端宿主都不会污染确定性算法。

## Consequences

运行时 Adapter 必须校验协议版本、输出种类和超时，并提供一个 Fake Adapter 做合同测试。新增 Provider 不会自动出现在产品中，只有 describe 摘要通过回归并进入产品允许列表后才能开放。
