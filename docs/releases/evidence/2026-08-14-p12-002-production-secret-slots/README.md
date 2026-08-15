# P12-002 生产秘密槽位审计

日期：2026-08-14  
工作项：P12-002 凭据泄露闭环  
状态：`BLOCKED`

## 检查

执行：

```text
python3 scripts/check_production_secrets.py
```

结果：fail-closed。以下生产槽位在当前本地环境缺失：

```text
MINGLI_IDENTITY_HASH_KEY
MINGLI_CONTENT_ENCRYPTION_KEY_B64
MINGLI_CONTENT_ENCRYPTION_KEY_ID
DEEPSEEK_API_KEY
```

检查脚本只输出槽位名称和失败原因，不输出任何秘密值，也不把本地 `.env.example` 当成生产注入证据。

## 已有代码边界

生产配置会拒绝 secure cookie 关闭、本地 identity hash key、本地 content encryption key、fake OTP、fake Runtime、fake Model、Admin bootstrap credentials、非固定 Runtime launcher/Python/release/state 路径，以及未关闭的真实流量闸门。该审计只证明代码会 fail-closed，不证明生产 Secret Manager、轮换、会话失效、主账号 MFA/RAM 最小权限或 debug 关闭已经执行。

## 未覆盖边界

P12-002 仍需在隔离生产或 staging 环境完成真实秘密注入与轮换、旧凭据和会话失效、主账号 MFA/RAM 最小权限、生产 debug 关闭、审计和恢复证据。不能用本地缺失槽位测试替代这些外部门禁。
