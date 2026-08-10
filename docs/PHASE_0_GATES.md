# Phase 0 外部 Gate 台账

更新日期：2026-08-11

进度说明：域名 ICP 备案已于 2026-08-10 正式提交，处于审核中。Mac mini `native-full` 原始五件套已归档并通过独立 verifier；真实 one-shot Runtime startup 已在本机通过；测试服务器已接真实 Runtime + 百炼 DeepSeek 并出现 `accepted`。仍未闭环的是：固定模型质量评测、Task 13 staging 全轨迹、支付/短信/邮件渠道、密钥托管与生产告警。Linux 模拟通道已废止，Mac mini `native-full` 仍是唯一 Runtime Gate。

本台账只记录上线前需要外部确认的事项。`待确认` 不代表失败，但绝不能在没有书面证据时改成已通过。仓库内不得保存密码、私钥、API Key、商户证书或真实 OTP。

Mac mini `native-full` 是唯一强制 Runtime Gate；正常开发、合并、发布和验收不得启动 VZ、Rosetta、QEMU 或 `linux-certify`。

当前代码断点见 [HANDOFF_SNAPSHOT_2026-08-11.md](./HANDOFF_SNAPSHOT_2026-08-11.md) 与 [2026-08-11 真实模型记录](./releases/2026-08-11-dashscope-deepseek-real-model.md)。Phase 2 旧记录 [2026-08-10](./releases/2026-08-10-mingli-v51-web-phase2.md) 仍保留为历史证据。整体仍是 `production blocked`，不构成上线批准；Task 13 与外部 Gate 完成前，`real traffic` 保持 disabled。

| Gate | 当前状态 | 通过证据 | 代码期处理 |
|---|---|---|---|
| 运营主体与经营范围 | 待确认 | 主体证照及适用许可复核记录 | 只保留主体配置占位，不写假备案信息 |
| 域名与 ICP 备案路线 | 申请中 | 域名实名已完成；备案订单已提交，等待管局审核；通过记录待补 | 本地使用 `localhost`，生产域名由环境注入；备案期间仅保留未备案临时预览入口 |
| 公安联网备案 | 待确认 | 网站开通后的备案记录与真实页脚链接 | 页脚保留合规信息区域，不展示虚构编号 |
| 微信支付商户能力 | 待确认 | JSAPI、H5、Native 各产品获批和小额实测 | `PaymentGateway` 仅提供 Fake，不加载 SDK |
| 支付宝商户能力 | 待确认 | 手机/电脑网站支付获批和小额实测 | `PaymentGateway` 仅提供 Fake，不加载 SDK |
| 短信通道与模板 | 待确认 | 供应商、签名、模板、数据位置与防轰炸评审 | 手机 OTP 使用 Fake Adapter；本地目标/游客/网络多层限流不能替代生产 Redis 限流 |
| 邮件通道与模板 | 待确认 | 发信域名、供应商、退信和数据处理评审 | 邮箱 OTP 使用 Fake Adapter；真实发送在共享限流与渠道 Gate 前保持关闭 |
| 模型供应商和数据位置 | 联调已通 / 正式准入待确认 | 本机与测试服务器已通过百炼兼容端点调用 `deepseek-v4-flash`；仍缺 DPA、保存期限、训练退出、预算、固定 Model Profile 质量评测和故障策略书面证据 | 联调可走 `MINGLI_MODEL_ADAPTER=deepseek`；正式放量前保持受限；不运行 Agent |
| mingli-master 5.1 完整发布物 | 本机已核验 / 生产安装待确认 | source commit `494ce0bba174a77800daf9b9c38ce9c9166d9a94`；217 文件 manifest SHA-256 `e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68`；describe digest `7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342`；capability shape SHA-256 `8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60`；本机 one-shot startup 验过 13/13 Provider readiness、55/55 reference pack、1328 evidence index 与 runtime closure | 仅使用签名 217 文件私有 release root；P0 Product Policy 只开放 `bazi`/`fortune`/`liuyao`，不裁剪 Runtime 制品 |
| Mac mini Runtime 原生门禁 | 已通过 | 归档 [docs/releases/evidence/2026-08-09-native-full](./releases/evidence/2026-08-09-native-full/)：`native-full-5.1.json`、`local-native-full-5.1.json`、`native-release-regression.stdout`、`native-release-regression.stderr`、`prepared-inputs.json`；`prepared_inputs_sha256=a4e83f3c225b928a9d9ea8b9ffc56448cb283ed23dd8b4e9f0b7e3831fa77807`；summary `targets=126 modules=93 tests=1584 failed_modules=0 elapsed=434.13s`；独立 `verify_local_full.py` 已通过 | 后续开发、合并、发布只认 Mac mini `native-full`；不得启动 VZ/Rosetta/QEMU/`linux-certify` |
| Runtime 状态与恢复 | 待确认 | 固定安装路径/UID/状态卷、Prepared 与 Accepted token 的备份恢复实测 | 真实 Runtime 可在原生门禁后接入；生产流量仍等待恢复演练 |
| 单模型成稿合同 | 联调已通 / 正式准入待确认 | 测试服务器真实链路已出现 `accepted` 且 generation_attempt 无 guard_errors；仍缺固定盲测与 Guard 红队反例集 | Fake Model 输出不能冒充正式质量评测；Task 13 前不得放量 |
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
