# 0011. 生产高可用拓扑与解读降级合同

日期：2026-08-12
状态：已接受（随生产就绪合同 v1 冻结）

## 背景

现有部署是单机测试服（上海 ECS `i-uf67fkafnm3w0abdmz3m`），所有组件同机：单实例、单盘、单可用区任一故障都会中断全部服务。mingli-master Runtime 持有本地状态卷，其合同要求单一写者；把它复制进每个 API 副本会破坏 Prepared/Accepted token 的 fencing 语义。

## 决定

1. **Web/API 无状态跨双可用区双副本**，经多可用区 ALB 接入；会话与业务事实在 PostgreSQL，OTP/限流在 Tair/Redis。
2. **PostgreSQL 与 Redis 使用托管高可用实例**（RDS 多可用区、Tair 同城容灾），不再自维主备。
3. **Runtime 保持「单活 + 受控热备」**：任何时刻只有一个写者操作 state root；热备通过数据库 lease/fencing token 接管，先完成恢复演练（Task 6/11）再允许自动接管。绝不并发运行多个 state root 写者。
4. **Runtime/模型故障只降级解读**：网站、账户、订单、报告读取、退款继续服务；解读进入 `queued` / `delayed` / `runtime_unknown` 等可解释状态（映射见 `docs/PRODUCTION_READINESS.md` 第 3 节），并在界面上诚实展示延迟。
5. **不宣称「永不宕机」**：高可用以 `docs/operations/SLO.md` 的指标、`docs/operations/ERROR_BUDGET.md` 的预算和真实故障演练证明。
6. **模型故障不自动切换未评测模型**：排队、有界退避、熔断；第二模型必须走与主模型相同的固定评测门禁（Task 6）后才允许启用。

## 后果

- 正面：Runtime 状态合同不被破坏；网站主链路可用性与解读子系统解耦；容量可独立扩展无状态层。
- 代价：Runtime 是单写者，解读吞吐受其限制；故障切换有分钟级空窗，由 `delayed` 状态对用户可见。
- 约束：任何「把 Runtime 塞进 API 副本」或「多活 state root」的提议与本 ADR 冲突，必须先修订本 ADR。

## 备选方案（已否决）

- Kubernetes/微服务拆分：当前团队规模下运维成本超过收益（计划第 1 节明确非目标）。
- 多地域双活：P0 不承诺区域级灾难；P2 再评估跨地域备份与 DNS 切换。
