# P12-009 测试服务器全旅程证据

日期：2026-08-14（Asia/Shanghai）  
环境：`fateradar-prod`，`local + Fake`，不是 staging/production  
Release：`ui-preview-20260814-3eaf1511b84a`  
归档 SHA-256：`3eaf1511b84a83721478e7da177c71f72d4557714c6e514f0df0955b0fdf8bc4`  
数据库：`0032_postgres_schema_alignment`；迁移前备份已记录，`alembic check` 通过

## 本轮结果

使用虚构 `example.com` 邮箱、虚构出生资料和 Fake OTP。最终 schema 对齐 release 上复跑；登录后由现有
`dogfood_grant.py` 以运营者测试身份发放 `today/week/liuyao` 能力；没有真实支付、
真实模型或真实个人信息。

| 步骤 | 结果 |
|---|---|
| S1 游客会话 | PASS |
| S2 邮箱 OTP 请求 | PASS |
| S3 OTP 验证 | PASS |
| S4–S5 资料草稿/确认 | PASS |
| S6 八字预览 | PASS / accepted |
| S7 今日 | PASS / accepted |
| S8 周运 | PASS / accepted |
| S9 六爻 digital_coin | PASS / accepted |
| S10 同盘追问 | PASS / accepted |

原始响应只留在服务器临时 0700 目录，运行结束已清理。回传的脱敏
`run-summary.json` 记录 `exit_code=0`、`hard_failure=false`、敏感扫描 0；
`delayed` 存量运行前后均为 18，没有把旧积压伪装成零。

最终 release 复跑时间为 2026-08-14 18:00（Asia/Shanghai）；S1–S10 仍全部通过，
并确认 0032 迁移没有破坏 Runtime 合同或 Worker 闭环。

## 本轮修复

六爻 `outcome` 请求此前错误复用了固定要求 `career` 的 Output Contract，Fake Worker
两次 Guard 后报 `required_dimension_missing` 并进入 `delayed`。现在 Job 创建时冻结
本次请求维度，Fake Runtime/Model 也保持多维 brief 闭合；新增 API 回归覆盖
`liuyao + outcome -> accepted`。

## 边界

这证明的是测试服务器的游客→登录→资料→预览→运营测试权益→交付→追问链路。
它不证明真实支付、退款、邀请例外、真实 SMTP/模型、生产备份、合规备案或公开上线；
P12-009 仍保持 `IN_PROGRESS`，生产旅程要等 P12-002/P12-004/P12-006/P12-007 等
外部门禁完成后再跑。
