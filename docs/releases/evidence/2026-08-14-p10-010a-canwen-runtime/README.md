# P10-010A 三术多盘确定性 Brief 内部切片

日期：2026-08-14

## 这次实际接入的内容

- 新增内部 action `canwen_preview`，固定八字作为主 Provider。
- 产品术数 ID 到 Runtime capability ID 的映射固定为：`bazi → bazi`、`ziwei → ziwei`、`qizheng → xingming`。
- 用户选择的第二、第三术数进入 `intent.comparisons`，且 requirement 固定为 `required`。缺少任一必选比较时，不能悄悄返回八字单盘。
- 复用同一份已确认出生资料给三个 Provider；八字使用 `birth_datetime_or_four_pillars`，紫微和七政使用 `birth_datetime`、性别、时区、地点，七政继续要求已确认经纬度和来源。
- 这一段只生成确定性 Runtime Brief，不开放 API/UI，不写 `CanwenViewV1`，不把事实并集猜成“互证”或“分歧”。

## 证据

- 编译器 fixture：`backend/tests/fixtures/mingli/canwen-prepare.json`
- 编译器与拒绝边界：`backend/tests/test_request_compiler.py`
- 可选冻结 Runtime 回归：`backend/tests/test_runtime_process_adapter.py`
- 真实合成输入通过 `describe → prepare`，启动门禁为 13/13 Provider、217 文件、55 资料包、1328 evidence；返回 `Prepared`。
- Brief 的 `request_view.capability_ids` 为 `bazi`、`ziwei`、`xingming`，计算事实实际来自三个对应系统，事实数量为 61。
- 默认定向回归：`62 passed, 1 skipped`；Ruff 通过。
- 显式真实 Runtime 回归：`MINGLI_RUN_REAL_RUNTIME_TESTS=1 ...::test_frozen_runtime_prepares_the_canwen_three_art_brief`，`1 passed`。

## 仍未完成

P10-010 仍是 `IN_PROGRESS`。还缺：由 Runtime 权威事实产生的互证/分歧规则、`canwen-view/v1` 与 `reading-document/v1` 的真实投影、服务/API、前端多盘任务、真实 Worker 轨迹、黄金样例、导出/分享和用户验收。当前切片明确保持内部不可用态。
