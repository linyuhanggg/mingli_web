# 2026-08-11：fact_panel 脱敏与运维门禁骨架

## 关闭的问题

1. **fact_panel 出生时间泄漏**：GET result 不再透传 `fact:.../input/birth_datetime` 等敏感输入事实。
2. **follow-up token 合同**：保持 Accepted token + `transition=null`，并补非 Accepted 拒绝测试。
3. **生产门禁骨架**：告警 sink、real_traffic fail-closed、Guard 红队用例扩展、密钥注入检查脚本。
4. **release 验签源钉死**：`scripts/verify_frozen_runtime_release.py` 只认 217 文件签名 release。
5. **P0 vs Runtime 边界**：文档明确 Runtime 完整、产品白名单裁剪。

## 仍需外部人工 Gate（代码不能硬过）

- ICP / 公安联网备案
- 支付渠道与短信邮件通道
- Secret Manager 与密钥轮换演练
- 生产告警路由到真实值班通道
- 固定模型质量盲测与完整 Task13 放量审批

`production blocked` / `real traffic disabled` 仍然成立。
