# P10-011 见相媒体 Adapter 与结构化观察边界

日期：2026-08-15

## 已完成

后端新增 [physiognomy media adapter](/Volumes/Lexar/code/mingli_web/backend/app/media/physiognomy.py)，目前锁定以下行为：

- 只接受 JPEG、PNG、HEIC；大小上限 10 MiB，宽高至少 640px。
- 未取得独立照片处理同意时，任何字节都不会写入私有媒体存储。
- 访客原图保留 24 小时，登录用户保留 7 天；删除和过期都会清除原始字节。
- 文件名、原图路径、对象键不会进入 Runtime 或安全审计事件。
- 当前 Runtime 只支持 `face` scope；手相、体态、综合观照会明确返回 unavailable，不会静默冒充面相。
- 适配器生成冻结的 `mingli-physiognomy-input-v1`：`requested_targets`、`observations`、质量哨兵、确认观察 ID、来源策略齐全，`assets` 保持为空。
- 本地产品纵切片已接通媒体上传/删除 HTTP、数据库媒体记录、私有本地存储、前端 File 选择和结构化观察提交；原图不进入 Runtime，读取入口只提交已确认的观察事实。

## 证据

- `backend/tests/test_physiognomy_media_adapter.py`：`13 passed`。
- 新模块 Ruff 与 mypy 通过。
- 合成输入经测试机现有 one-shot Runtime 实际执行并返回 `Prepared`；返回事实含 `normalized_visible_observations`、缺失目标、不确定性、来源分层和证据，未读取原图。
- `backend/tests/test_runtime_process_adapter.py` 与 `backend/tests/test_chart_projectors.py`：`36 passed, 10 skipped`。跳过项是本机未注入 native Runtime 路径，不是算法失败。

## 仍未完成

这不是 P10-011 的最终完成证据。生产对象存储、生产媒体清理/告警、真实 Worker/ReadingDocument、完整深读/导出和用户逐页批准仍需独立验收。当前 Web 会在明确同意后上传到本地测试环境的私有媒体存储，并允许提交前删除；不代表生产照片保存已完成。

## 2026-08-16 来源约束型 face 投影切片

见相 face 的 ViewModel 现在保留 Runtime 已公开的 `missing_targets`、`uncertainties`、`observation_conflicts`、`cross_capture_variations`、`source_comparison` 和来源规则数量；Web 展示来源层、保留的分歧、资料缺口与不确定性，Admin 只显示来源/分歧/规则数量聚合，不解密或返回原始观察输入。来源层仍强制 `verdict_prohibited`，页面明确不作身份、健康、财富、寿命或性格断语。

定向回归：后端 `test_chart_projectors.py -k physiognomy` 为 `2 passed`，运行时/文档合同 `11 passed`、`test_reading_document_builder.py` 为 `1 passed`；Web 结果层 `36 passed`，Admin 见相详情 `3 passed`，两端 typecheck/lint 通过。该切片仍不是最终闭环：真实 native Runtime、真实 Worker/数据库 Accepted→ReadingDocument、生产模型和用户验收仍缺，手相/体态/综合模式继续保持 unavailable。

本证据不包含个人资料、姓名、密码、邮箱凭据、API key 或原始图片。
