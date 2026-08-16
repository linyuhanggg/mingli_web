# P11-006 专属 PNG/PDF 导出与短时下载（2026-08-15）

## 状态

`IN_PROGRESS`。本轮完成本地/测试栈的产品报告导出闭环，不把本地加密数据库 artifact 冒充生产对象存储、异步队列或正式 CDN 授权。

## 已完成

- `ReadingDocumentV1.actions.export` 在 Accepted 文档构建时启用；没有合法 ReadingDocument 的结果不会出现导出入口。
- 新增 `POST /api/v1/readings/{reading_version_id}/export`，只接受当前 owner、Accepted 版本和 `png`/`pdf` 两种固定格式。
- PNG 使用 Pillow，PDF 使用 ReportLab；内容绑定不可变 `ReadingDocumentV1`，包含摘要、判断、依据、边界和版本，不把 Runtime 私有输入或原始 payload 写入报告。
- 产物以 EnvelopeCipher 加密保存于 `reading_export_artifacts`，下载 token 只保存哈希，下载响应 `private, no-store, noindex`。
- TTL 固定在 5 分钟至 24 小时；过期/撤销 artifact 可清理，过期后不能下载，重新创建会生成新的 token。
- 新增 `/api/v1/exports/{token}` 二进制下载路径和结果页 PNG/PDF 按钮；账户数据权利 JSON 导出仍与产品报告分开。

## 证据

- 后端导出服务测试覆盖 PNG/PDF 文件头、加密读回、过期拒绝、清理和重建。
- Reading migration/OpenAPI/导出 API 相关后端回归：`50 passed`；Ruff 和 mypy 通过。
- 本轮完整 Backend 回归：`867 passed, 107 skipped`；mypy `141 source files`。
- Web typecheck、lint、Vitest：`70 files / 441 tests passed`。
- 代表性报告 PNG 为 1600×1164，PDF 为 1 页；Poppler 渲染复核通过，中文字体、标题层级、边界和正文无裁切或重叠。

## 仍缺

- 生产对象存储或等价专用 artifact 存储、异步导出 Worker、并发/容量限制、下载审计和后台清理调度。
- 合参、合盘、见相等产品的最终专属版式与黄金样例逐术复核；当前 renderer 是通用产品报告模板。
- 测试服务器真实 Runtime Worker、用户逐页浏览批准，以及 P12 生产秘密、支付、备份、告警、合规和公开上线门禁。
