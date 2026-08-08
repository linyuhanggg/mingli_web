---
status: accepted
date: 2026-08-09
---

# 用显式 Reading Orchestrator 取代 Agent 循环

网站不运行 Codex/Hermes Agent，也不让大模型自主选择术法、调用工具、查询记忆或决定重试。页面和商品先确定 `bazi`、`fortune` 或 `liuyao`，后端用普通代码编排 mingli-master 5.1 的 `describe → prepare → complete`；获得 Prepared 后，只把闭世界 ReadingBrief 交给一个独立模型生成结构化 Candidate。

Candidate 必须先通过网站自己的确定性 Narrative Guard，合格后才调用 `complete`。因为 5.1 的公开 complete 只验证 token、非空正文和首次原子提交，Guard 是网站责任；一旦返回 Accepted，正文按原字节保存和交付，不再二次改写。

P0 的 Runtime 采用一个持久化、单副本 Worker，在固定安装路径和私有状态卷上调用 JSON Adapter。当前 5.1 状态存储是本地文件模型，且现有依赖锁只验过 macOS arm64；Linux 制品、备份恢复和多进程测试通过前，不得把 Runtime 放进无状态 API 多副本或宣称可水平扩展。

## Consequences

- 正常解读只有一次直接模型调用；有限的同模型重生由代码状态机控制，不构成 Agent loop。
- P0 capability allowlist 固定为 `bazi`、`fortune`、`liuyao`，新增能力需要产品映射和回归，不随 describe 自动开放。
- 模型层可以替换，但 Narrative Policy、Output Contract、模型版本与 Candidate digest 必须留档。
- `state_token` 只在服务端加密保存，不能进入客户端、URL、日志或埋点。
- 无 token 的 `prepare` 不可在结果不明时盲重放；同 token 的 `complete` 可以用完全相同正文恢复重放。
- Linux Runtime Gate、状态盘恢复演练和 Guard 反例测试是上线硬门槛。
- 详细合同以 [MINGLI_V51_WEB_INTEGRATION.md](../MINGLI_V51_WEB_INTEGRATION.md) 为准。
