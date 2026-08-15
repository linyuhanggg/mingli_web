# P10 四个核心术数产品输入/API/UI 纵切片

日期：2026-08-15

## 结论

禄命/纳音、太乙、择日、风水已经从“只有核心 Provider/compiler/projector”推进到“本地可选择、可提交、可进入 Reading 结果页”的产品纵切片。实现复用了既有 `RequestCompiler → Runtime → ViewModel` 链路，没有在 Web 或 API 层复制算法。

新增入口：

- 禄命/纳音：`POST /api/v1/readings/luming-nayin`、`/luming-nayin`
- 太乙：`POST /api/v1/readings/taiyi`、`/taiyi`
- 择日：`POST /api/v1/readings/selection`、`/selection`
- 风水：`POST /api/v1/readings/fengshui`、`/fengshui`

四个输入合同都保留时区、地点、坐标、日期范围、硬约束或空间测量等适用边界；结果只消费严格 ViewModel 和已公开事实，不把 Runtime 原始载荷直接送到页面。

## 本轮验证

- `backend/tests/test_readings_api.py`：`53 passed`
- `backend/tests/test_openapi_alignment.py`：`6 passed`
- `tests/contract/test_platform_presentation_contracts.py`：`29 passed`；新增并纳入 `ReadingDocumentV1` 的梅花、禄命/纳音、太乙、择日、风水 ViewModel 合同
- Backend 全量：`854 passed / 104 skipped`
- V51 真实 one-shot 冻结 Runtime：`10 passed / 16 deselected`
- Web 全量：`70 files / 440 tests`
- Web `typecheck`、`lint`、`production build`：通过

## 边界

这是本地技术和产品接线证据，不是 P10/P11/P12 全部完成。四个产品现在已有冻结 ViewModel/ReadingDocument 合同，但仍缺真实 Worker 轨迹、每术黄金样例、完整深读/追问、PNG/PDF、导出服务、真实生产 Runtime admission 和用户逐页批准。结果页也已改为只有合法 `ReadingDocument` 且动作启用时才显示分享/追问入口；没有文档不会伪造交付能力。当前测试环境仍按既有 `local + Fake` 浏览边界使用；上传测试服务器后只供用户验收页面，不等于生产上线。

## 测试服务器发布

本轮已上传并原子切换 `fateradar-prod` 测试验收机：

```text
release: ui-preview-20260815-public-products
archive_sha256: ba6ea69f9d3558ef0cd3f47b2cb4ce13780a57b0e6721bd9ea4ac87c4d2b47e1
database_schema_head: 0035_physiognomy_media
pre_migration_backup: /opt/fateradar/shared/backups/ui-preview-20260815-public-products-pre-migration.dump
pre_migration_backup_sha256: 0b5c4854a63a6058e3d7fa2245edee0437786929d0020669981cb36b6b6d3df4
environment: MINGLI_ENVIRONMENT=local + Fake OTP/Runtime/Model/Payment
```

服务器端 backend import、`alembic check`、Web/Admin production build、standalone 预启动、原子切换、两轮重启复验、API live/ready、Nginx healthz、七个 Web 路由、Admin `/login` 和五个 systemd 服务均通过；服务 `NRestarts=0`。用户可通过 SSH 隧道浏览：

```bash
ssh -L 18080:127.0.0.1:8080 -L 13001:127.0.0.1:3001 fateradar-prod
```

Web：`http://127.0.0.1:18080/luming-nayin`、`/taiyi`、`/selection`、`/fengshui`、`/jianxiang`；Admin：`http://127.0.0.1:13001/login`。服务器也保留临时公网预览 `http://106.14.10.235:18080/`，只使用虚构数据。

本证据不包含个人出生资料、姓名、密码、邮箱凭据、API key 或其他秘密。
