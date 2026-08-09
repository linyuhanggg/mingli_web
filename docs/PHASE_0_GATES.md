# Phase 0 外部 Gate 台账

更新日期：2026-08-10

本台账只记录上线前需要外部确认的事项。`待确认` 不代表失败，但绝不能在没有书面证据时改成已通过。仓库内不得保存密码、私钥、API Key、商户证书或真实 OTP。

Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。

当前第一版代码候选及缺口见 [2026-08-10 Phase 2 发布证据记录](./releases/2026-08-10-mingli-v51-web-phase2.md)。该记录为 `production blocked`，不构成上线批准；原始证据补齐前所有生产相关 Gate 均保持待确认，`real traffic` 保持 disabled。

| Gate | 当前状态 | 通过证据 | 代码期处理 |
|---|---|---|---|
| 运营主体与经营范围 | 待确认 | 主体证照及适用许可复核记录 | 只保留主体配置占位，不写假备案信息 |
| 域名与 ICP 备案路线 | 待确认 | 域名实名、备案订单和通过记录 | 本地使用 `localhost`，生产域名由环境注入 |
| 公安联网备案 | 待确认 | 网站开通后的备案记录与真实页脚链接 | 页脚保留合规信息区域，不展示虚构编号 |
| 微信支付商户能力 | 待确认 | JSAPI、H5、Native 各产品获批和小额实测 | `PaymentGateway` 仅提供 Fake，不加载 SDK |
| 支付宝商户能力 | 待确认 | 手机/电脑网站支付获批和小额实测 | `PaymentGateway` 仅提供 Fake，不加载 SDK |
| 短信通道与模板 | 待确认 | 供应商、签名、模板、数据位置与防轰炸评审 | 手机 OTP 使用 Fake Adapter；本地目标/游客/网络多层限流不能替代生产 Redis 限流 |
| 邮件通道与模板 | 待确认 | 发信域名、供应商、退信和数据处理评审 | 邮箱 OTP 使用 Fake Adapter；真实发送在共享限流与渠道 Gate 前保持关闭 |
| 模型供应商和数据位置 | 待确认 | DPA、保存期限、训练退出、预算、固定 Model Profile 和故障策略 | `ModelGateway` 使用结构化 Fake；不运行 Agent |
| mingli-master 5.1 完整发布物 | 待确认 | source commit、217 文件 manifest、协议版本、describe digest、13/13 Provider readiness、55/55 古籍 reference pack、1328 条 evidence index 与 runtime closure | Fake Runtime 描述完整 13 项；Product Policy 另行只开放 P0 三项 |
| Mac mini Runtime 原生门禁 | 待确认 | 当次 `native-full` 报告、原始 stdout/stderr、PreparedInputs 摘要及独立 verifier；要求 126 targets、93 modules、1584 tests、0 failed 且低于 600 秒 | 门禁机制已存在，但当前仓库缺少可独立复验的原始归档；不再要求 Linux 模拟报告 |
| Runtime 状态与恢复 | 待确认 | 固定安装路径/UID/状态卷、Prepared 与 Accepted token 的备份恢复实测 | 真实 Runtime 可在原生门禁后接入；生产流量仍等待恢复演练 |
| 单模型成稿合同 | 待确认 | Narrative Policy、Candidate Schema、Narrative Guard 反例集和固定盲测通过 | Fake Model 输出不能进入 complete 或成为 Accepted |
| 生产密钥托管与轮换 | 待确认 | Secret Manager、最小权限、轮换和演练记录 | 只接受运行时注入；示例值均为非密钥 |
| 生产监控与告警 | 待确认 | `runtime_unknown`、`delayed`、Narrative Guard rejection、model cost 四类告警配置、路由和触发演练 | 状态与成本记录不能替代生产告警；未通过前不得开放流量 |

## Phase 1 可以继续的前提

- 本地开发和自动化测试只使用 Fake Adapter 与脱敏夹具。
- 数据库迁移以 PostgreSQL 为目标；测试数据库不承载生产事实。
- 所有外部 Gate 保持关闭，不以页面入口或占位配置冒充渠道已经开通。
- 私人页面、API、Cookie 和日志的安全边界先于真实渠道接入建立。

## Runtime 恢复边界

Worker 每次事务只推进一个持久化阶段：Prepare 后提交 Prepared、一次模型尝试后提交 attempt（成功时与 exact completion intent 原子提交）、Complete 后提交 Accepted。已提交的 token、attempt 和 completion intent 可在租约重领后恢复。Complete 传输未知必须携带非零 `retry_not_before`，不能立即重领形成热循环。

无 token `prepare` 仍有不可消除的提交前窗口：Runtime 可能已经创建 Root，而宿主在响应到达或 Prepared 提交前崩溃，留下孤儿 Runtime Root。此处不宣称 exactly-once，也不自动重放无 token Prepare。无 token 的 `INPUT_READY` claim 若过期且没有 checkpoint，领取层会保守地标记 `runtime_unknown` 并拒绝重领，即使实际崩溃发生在调用前。带 token 的 `INPUT_READY` 按 5.1 收敛协议轮换 fencing token 后可安全重领，并原样重放加密 Prepare；WorkSource 只读取持久化的 `prepare_has_state_token`，不解密 token。上线前必须落实调用超时、Runtime 单副本、孤儿审计与清理手册。
