# P10-010B Canwen 共同事实范围投影

日期：2026-08-14

## 这次完成了什么

- 将三术 Runtime Brief 投影为严格 `canwen-view/v1`，不再因为 `capability_ids` 多于一个而直接丢弃结果。
- 互证层只消费 Runtime 已声明的 `dimension_fact_scope`：每个已选术数逐术产生可追溯 `signals`；范围名称属于各 Provider 自己的事实命名，不因名称不同就判为术数分歧。
- V51 的历史快照曾把七政列为缺失；2026-08-15 的 V52 relationship release 已补齐七政跨术范围绑定。三术齐全时只显示“所选术数的计算事实范围均已提供”，不把它升级成实质性共同结论。
- 新增 `/api/v1/readings/canwen`、Reading Service、Web 任务提交和结果页结构化展示。需要使用已确认的 ProfileVersion ID，并至少选择两术。
- Runtime ViewModel dispatch 现在只接受明确的八字主盘 + 紫微/七政组合；六爻/奇门/大六壬等未来多术 Brief 不会被误投影成 Canwen。

## 已验证

- Canwen projector、编译器和 API：与现有回归合计 `128 passed`；Ruff、mypy 通过。
- 真实 V51 三盘 Brief 的 `bazi`、`ziwei`、`xingming` 被成功投影为 `CanwenViewV1`；每个请求维度都保留八字/紫微信号并明确缺少七政跨术范围。
- Web TypeScript 类型检查通过；结果页已注册 `canwen-view/v1`，不再把该 ViewModel 当作未知结果丢弃。

## 2026-08-15 V52 复核

- V52 one-shot Runtime：13/13 Provider admission、217 文件、55 reference pack、1328 evidence；三术 `Prepared` 且每个维度 `missing_art_ids=()`。
- projector 回归覆盖不同 Provider scope 名称不构成分歧；真实三术测试通过。

## 仍未完成

这不是三术完整合参完成证明。还缺 Runtime 对七政的跨术事实范围或等价权威合同、实质性互证/分歧规则、ReadingDocument/深读、真实 Worker、黄金样例、导出分享、用户验收和生产门禁。没有这些条件，页面只显示共同计算范围与缺失能力。

本证据不包含个人出生资料、密码、SMTP 凭据、API key 或其他秘密。
