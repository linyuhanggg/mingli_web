# P10-013B 五个内部 Runtime Provider 核心接线

日期：2026-08-14

## 这次完成了什么

本切片把冻结 V51 Runtime 中此前只有 Provider、但后端还没有对应输入编译器和结构投影的五个核心模块接上：

- `luming-nayin`：命禄纳音的四柱、纳音、胎元和关系事实；
- `taiyi`：太乙的历法、纪元、周期、盘面、四将、主客、长周期神和范围合同；
- `selection`：择日的事件约束、候选项、淘汰原因、排序和谱系；
- `fengshui`：风水观测的罗盘、建筑年代、形势、理气、布局图、冲突、不确定性和缺失项。
- `physiognomy`：相法的结构化可见观察、缺失目标、冲突和不确定性。

五者均完成了同一条内部链路：

```text
内部 action/query
  → manifest 对齐的 Request Compiler
  → Runtime prepare
  → 严格 ViewModel projector
  → Reading 层可识别的 schema
```

它们仍然是内部 Runtime 模块，不新增五个公开产品页，也没有把没有产品合同的 Provider 伪装成公开 API。项目清单明确规定 13 个 Runtime Provider 不映射成 13 个产品页或合参选项。

## 已验证

- `backend/tests/test_request_compiler.py`、`backend/tests/test_chart_projectors.py`、`backend/tests/test_runtime_process_adapter.py` 定向合成回归：`88 passed / 8 skipped`。
- 冻结 V51 Runtime 的真实 one-shot 回归：五项全部通过：
  `test_frozen_runtime_prepares_and_projects_luming_nayin`、
  `test_frozen_runtime_prepares_and_projects_taiyi`、
  `test_frozen_runtime_prepares_and_projects_selection`、
  `test_frozen_runtime_prepares_and_projects_fengshui_observations`、
  `test_frozen_runtime_prepares_and_projects_physiognomy_observations`，结果为 `5 passed / 19 deselected`。
- `ruff`、源码 `mypy` 和定向 `git diff --check` 通过。
- 五个编译器都按 Runtime manifest 的真实输入槽位组装事实，没有使用一个无法被 Provider 消费的伪嵌套字段；真实 Runtime 均返回 `Prepared`，随后成功投影到各自的 `*-chart/v1` 或 `fengshui-view/v1` 合同。

## 结果边界

- `luming-nayin`、`taiyi` 目前只投影确定性计算事实，不生成吉凶、人生建议或其他解释结论。
- `selection` 只投影 Runtime 当前公开的有界候选、淘汰、排序和谱系依据；候选为空时保留 `no_valid_candidate`，不宣称覆盖所有日期。
- `fengshui` 只投影结构化观测、冲突、不确定性和关键缺失项；没有罗盘/建筑/布局事实时不会补造判断。
- `physiognomy` 只接收调用方已完成的结构化可见观察；这个编译器不接图片、路径、URL 或转写文本，也不会把历史术语变成身份、性格、健康或命运结论。
- 这四个切片没有自动获得公开 API、用户任务页、深读、导出、分享或付费能力；如果将来要公开，必须分别补产品输入合同、ReadingDocument、真实 Worker 轨迹、黄金样例和用户验收。

## 仍未完成

P10-013 仍为 `IN_PROGRESS`。剩余工作不是这五个 Provider 的基本算法接线，而是每日/工具产品缺口、公开产品合同和各自验收证据；相法另外还缺 P10-011 的媒体采集/质量/授权 Adapter。P10 全局仍缺真实 Worker 数据库轨迹、发布版黄金样例、生产 Runtime admission、PNG/PDF、真实支付/凭据和生产上线门禁。没有把本地合成测试或 one-shot Runtime 结果写成生产完成证明。

本证据不包含个人出生资料、密码、邮箱密码、API key 或其他秘密。
