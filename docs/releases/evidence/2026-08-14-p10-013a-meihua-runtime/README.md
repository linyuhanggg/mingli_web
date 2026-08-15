# P10-013A 梅花时间起卦结构盘内部切片

日期：2026-08-14

## 这次完成了什么

- 在产品能力政策中登记内部动作 `meihua_preview`，固定对象为 `concrete_event`、时限为 `instant`。
- 新增 `compile_meihua_prepare`：要求明确 `casting_method="time"`，并把事件时间按确认时区归一化后送入 Runtime。
- 新增严格 `meihua-chart/v1` 合同和投影：本卦、互卦、变卦、动爻、体用结构；体用关系保留 Runtime 的 `calculated_relation_not_verdict` 边界。
- 投影只读取计算事实，不读取 `/input/` 事实，也不把来源摘要、digest 或关系事实改写成吉凶结论。

## 已验证

- 冻结 Runtime 启动门禁：13/13 Provider、217 文件、55 资料包、1328 evidence。
- 合成编译器、投影和拒绝边界：Backend 定向 `77 passed / 2 skipped`。
- 真实冻结 Runtime：`test_frozen_runtime_prepares_and_projects_the_meihua_time_plate` `1 passed`。
- 真实结果的 `request_view.capability_ids` 为 `meihua`，并返回本卦计算事实，成功投影为 `meihua-chart/v1`。
- `ruff`、相关源码 `mypy`、`git diff --check` 通过。

## 明确未完成

本文件记录的是时间起卦的历史切片；其余四种起法的后续核心/API/UI 接入见 `P10-013D` 证据。

这不是梅花产品完成证明。该切片提交时以下仍未接入：

- 数字起卦、声数起卦、观察起卦、提供完整卦象四种输入合同；
- 公开 API、任务页、真实 Worker 全旅程、ReadingDocument、深读、追问、导出和分享；
- 生产 Runtime admission、真实凭据、支付、合规和公开上线。

P10-013 和整体 P10 仍为 `IN_PROGRESS`。
