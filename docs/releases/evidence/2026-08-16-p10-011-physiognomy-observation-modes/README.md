# P10-011 见相四种观照模式与 UI 流程回归

日期：2026-08-16

## 本轮完成

见相输入与 Runtime/Worker/ReadingDocument 现在明确支持四种 `observation_scope`：`face`、`palm`、`posture`、`combined`。

- 手相、体态和综合观照使用各自的区域 taxonomy 与 descriptor 合同，不把面相区域混入其他模式。
- Runtime 按所选 source pack 过滤 active rule，手相/体态不会误带入不属于它们的面相基线规则；综合观照只合并显式选择的区域与规则。
- 非面相模式继续只接收用户已经核对的结构化观察，`assets=[]`；不会读取或猜测原图。
- Web 见相表单提供四种模式、模式对应的观察部位/描述，并保留照片独立同意、选择、质量检查待接入、删除和确认边界。
- 修复缺照片提交时默认聚焦抢回第一个字段的问题；现在会稳定聚焦 `#jianxiang-file`。

## 证据

- `backend/tests/test_physiognomy_media_adapter.py`：`17 passed`。
- V53 真实 one-shot Runtime 模式矩阵：`5 passed, 28 deselected`，覆盖 face/palm/posture/combined 与混用 taxonomy 拒绝。
- V53 真实 Worker → Accepted → typed ReadingDocument 矩阵：`6 passed, 1 skipped`；skip 是本机没有匹配的关系 release，不是失败。
- Web `product-p2-interactions`：`8 passed`；见相浏览器流程在 360/768/1024/1440 四个 viewport：`4 passed`。
- 四个 viewport 的 `/jianxiang` 直接 CSS 检查：文档宽度等于视口宽度；正文/标题为黑/灰；默认浏览器蓝 `rgb(0, 0, 238)` 命中数为 `0`。
- 最终 `make check`：Backend `941 passed, 122 skipped`，Web `72 files / 454 tests`，Admin `33 files / 122 tests`；Backend mypy `142 source files`，两端 lint/typecheck/build 通过。

## 明确边界

这轮完成的是结构化观察模式和本地 UI/Runtime 纵切片，不是完整古法手相、体态或综合断法；没有新增图像识别、模型猜测、身份/健康/财富/寿命结论，也没有把来源候选升级成硬断语。真实生产媒体、生产 Runtime、产品级深读/追问/导出、用户逐页验收和生产外部门禁仍未完成。

本证据对应测试服务器的本地/Fake 运行边界，不代表生产部署；本轮没有上传未提交工作树到服务器。

本证据不包含个人资料、姓名、密码、邮箱凭据、API key 或原始图片。
