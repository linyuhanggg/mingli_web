# P10 八字来源推理工具接入（2026-08-16）

## 结果

八字 Runtime 原本已经有来源规则包绑定的两个确定性推理工具，但主 Provider 只发布了 `interpretive_candidates` 的基础结构，主盘结果没有带出这层算法事实。本轮将它们接入八字主盘的 `interpretive_candidates.reasoning_tools`：

- `strength_evidence`：按月令、根气、印比与压力角色汇总成可追溯的 evidence lean；
- `month_structure_candidate`：按月令主气、十神和透干事实生成格局候选。

两者均保留 Runtime 的 `source_refs`、`fact_refs`、规则工具 digest 和 caveats，前端/ReadingDocument 只消费严格类型合同。它们仍然不是旺衰硬裁定、格局成败裁定、喜忌/用神排序或吉凶结论。

本轮又把主 Provider 的明确问题维度接入已有领域工具：`career/work → domain_work`、`money → domain_finance`、`health → domain_health`、`location → domain_travel`、`relationship → domain_relationship`、`education → domain_education`。没有对应规则的 `state`、`overview`、`timing`、`outcome` 不会被强行映射；五行事实入口请求 `state` 时仍只得到两项通用工具。

## 验证

- 直接 Runtime smoke 成功，返回两个工具；示例四柱得到 `support_lean` 与 `candidate_only`。
- 八字 ViewModel、全图表投影、Runtime contract、寻时合同：`43 passed`。
- 真实公开核心过程：`5 passed`；真实八字全 Provider Worker → Accepted → ReadingDocument：`1 passed`。
- 领域接线后的真实年份层与全 Provider Worker → Accepted → ReadingDocument：`2 passed`；五行 `state` 入口确认不会误注入 `domain_work`。
- `mypy` 受影响图表文件通过；八字和五行 JSON Schema 通过 Draft 2020-12 校验。
- 真实 Worker 黄金样例固定为实际结果 `mixed`，没有用另一组四柱硬写测试期望。

## 边界

本轮接入的是已有 Runtime 规则工具，不把证据倾向升级成硬断法，也没有新增模型猜测。八字完整旺衰/格局/从化/喜忌/用神裁定、各术深读、合参分歧、寻时事件匹配、解梦/姓名正式 Provider 仍保持未完成状态。测试机和 P12 外部门禁不因本轮算法事实接入而自动通过。

本证据不包含个人资料、密码、SMTP 凭据、API key 或状态 token。
