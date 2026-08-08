# Phase 0 外部 Gate 台账

更新日期：2026-08-09

本台账只记录上线前需要外部确认的事项。`待确认` 不代表失败，但绝不能在没有书面证据时改成已通过。仓库内不得保存密码、私钥、API Key、商户证书或真实 OTP。

| Gate | 当前状态 | 通过证据 | 代码期处理 |
|---|---|---|---|
| 运营主体与经营范围 | 待确认 | 主体证照及适用许可复核记录 | 只保留主体配置占位，不写假备案信息 |
| 域名与 ICP 备案路线 | 待确认 | 域名实名、备案订单和通过记录 | 本地使用 `localhost`，生产域名由环境注入 |
| 公安联网备案 | 待确认 | 网站开通后的备案记录与真实页脚链接 | 页脚保留合规信息区域，不展示虚构编号 |
| 微信支付商户能力 | 待确认 | JSAPI、H5、Native 各产品获批和小额实测 | `PaymentGateway` 仅提供 Fake，不加载 SDK |
| 支付宝商户能力 | 待确认 | 手机/电脑网站支付获批和小额实测 | `PaymentGateway` 仅提供 Fake，不加载 SDK |
| 短信通道与模板 | 待确认 | 供应商、签名、模板、数据位置与防轰炸评审 | 手机 OTP 使用 Fake Adapter |
| 邮件通道与模板 | 待确认 | 发信域名、供应商、退信和数据处理评审 | 邮箱 OTP 使用 Fake Adapter |
| 模型供应商和数据位置 | 待确认 | DPA、保存期限、训练退出、预算、固定 Model Profile 和故障策略 | `ModelGateway` 使用结构化 Fake；不运行 Agent |
| mingli-master 5.1 发布物 | 待确认 | source commit、217 文件 manifest、协议版本、describe digest 与 bazi/fortune/liuyao allowlist | `RuntimeAdapter` 使用固定 Fake 能力 |
| Linux Runtime 制品 | 待确认 | Linux x86_64 wheel/hash 审计、runtime-integrity、SBOM、镜像 digest 和三能力黄金回归 | 不把现有 macOS arm64 依赖锁用于生产 |
| Runtime 状态与恢复 | 待确认 | 固定安装路径/UID/状态卷、Prepared 与 Accepted token 的备份恢复实测 | 真实 Runtime 保持关闭，开发只用 Fake |
| 单模型成稿合同 | 待确认 | Narrative Policy、Candidate Schema、Narrative Guard 反例集和固定盲测通过 | Fake Model 输出不能进入 complete 或成为 Accepted |
| 生产密钥托管与轮换 | 待确认 | Secret Manager、最小权限、轮换和演练记录 | 只接受运行时注入；示例值均为非密钥 |

## Phase 1 可以继续的前提

- 本地开发和自动化测试只使用 Fake Adapter 与脱敏夹具。
- 数据库迁移以 PostgreSQL 为目标；测试数据库不承载生产事实。
- 所有外部 Gate 保持关闭，不以页面入口或占位配置冒充渠道已经开通。
- 私人页面、API、Cookie 和日志的安全边界先于真实渠道接入建立。
