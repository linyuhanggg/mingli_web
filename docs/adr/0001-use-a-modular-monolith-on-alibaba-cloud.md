---
status: accepted
amended_by: 0007-web-first-with-native-ios-later
---

# 在阿里云采用模块化单体

本 ADR 的客户端部分由 0007 修订：首版客户端改为 Next.js 响应式网站，后续为原生 iOS。后端决定继续有效：Python/FastAPI 模块化单体、同仓库后台 Worker、PostgreSQL、Redis/Tair 和私有 OSS，部署在已确定的阿里云 ECS 上；不采用微服务、CloudBase，也不在业务 ECS 上承载大型模型推理。当前规模下，这能把支付、权益和解读的一致性留在一个事务边界内，同时用深模块 Interface 保留未来拆分空间。

## Consequences

API 与 Worker 共用领域代码和数据库迁移，但以独立进程运行。PostgreSQL 是业务事实源和任务事实源，Redis 只用于缓存、限流与短期租约，不能成为订单、权益或解读的唯一记录。
